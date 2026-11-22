"""Loopback-only PostgreSQL/PostgREST regression (see docs/test/e2e_telegram_erp.md)."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from postgrest import SyncPostgrestClient

from app.api.v1.endpoints import atlas_tools
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import get_service_role_client
from app.services.security_service import SecurityService

BASE = "/api/v1/telegram"
SECRET = "synthetic_telegram_test_only_0123456789"
JWT_SECRET = "synthetic_jwt_key_for_fixture_only_0123456789abcdef"


def identifier(n: int) -> str:
    return f"00000000-0000-0000-0000-{n:012d}"


def bearer(subject: int, role: str = "authenticated") -> str:
    token = jwt.encode(
        {"sub": identifier(subject), "role": role, "exp": int(time.time()) + 300},
        JWT_SECRET,
        algorithm="HS256",
    )
    return f"Bearer {token}"


def test_synthetic_two_tenant_telegram_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    port = os.getenv("TELEGRAM_TEST_POSTGREST_PORT")
    if not port:
        pytest.skip("requires the isolated Telegram test stack")
    url = f"http://127.0.0.1:{int(port)}"
    # Confirm the fixture schema and IDs exist before any write. Never load
    # Supabase credentials or create clients from the application's environment.
    db = SyncPostgrestClient(url, headers={"Authorization": bearer(21, "service_role")})
    assert db.from_("tenant_users").select("id").eq("id", identifier(11)).execute().data
    for role in ("anon", "authenticated"):
        for table in ("telegram_erp_links", "telegram_erp_deliveries"):
            assert httpx.get(
                f"{url}/{table}", headers={"Authorization": bearer(21, role)}
            ).status_code in {401, 403}

    monkeypatch.setattr(settings, "telegram_erp_enabled", True)
    monkeypatch.setattr(settings, "telegram_erp_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "supabase_jwt_secret", JWT_SECRET)
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_service_role_client] = lambda: db
    # Test the real read path. Stub the final proposal-producing tool only;
    # exercise forced Inbox routing separately in the Copilot policy suite.
    draft_tool = AsyncMock(
        return_value={
            "requires_review": True,
            "suggestion_id": identifier(51),
            "internal_payload": "never echo",
        }
    )
    monkeypatch.setitem(atlas_tools._TOOL_DISPATCH, "aethos.o2c.draft_invoice", draft_tool)
    monkeypatch.setattr(
        SecurityService,
        "effective_permissions",
        AsyncMock(
            return_value=SimpleNamespace(privilege_codes=["invoices.draft"]),
        ),
    )
    client = TestClient(app)

    def auth(who: int, tenant: int) -> dict[str, str]:
        return {"Authorization": bearer(who), "X-Tenant-ID": identifier(tenant)}

    def dm(sender: int, delivery: int, text: str) -> dict:
        response = client.post(
            f"{BASE}/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
            json={
                "update_id": delivery,
                "message": {
                    "text": text,
                    "date": int(time.time()),
                    "from": {"id": sender, "is_bot": False},
                    "chat": {"id": sender, "type": "private"},
                },
            },
        )
        assert response.status_code == 200
        return response.json()

    def issue(who: int, tenant: int, sender: int) -> str:
        response = client.post(
            f"{BASE}/link", headers=auth(who, tenant), json={"sender_id": sender}
        )
        assert response.status_code == 201
        assert response.headers["Cache-Control"] == "no-store"
        return response.json()["start_payload"]

    assert (
        client.post(f"{BASE}/link", headers=auth(21, 2), json={"sender_id": 3001}).status_code
        == 404
    )
    start_a = issue(21, 1, 3001)
    start_b = issue(22, 2, 3002)
    assert "unavailable" in dm(3002, 1, f"/start {start_a}")["text"]
    assert "linked" in dm(3001, 2, f"/start {start_a}")["text"]
    assert "unavailable" in dm(3001, 3, f"/start {start_a}")["text"]
    assert "linked" in dm(3002, 4, f"/start {start_b}")["text"]
    assert "125.00" in dm(3001, 5, "/ar")["text"]
    assert "987.00" in dm(3002, 6, "/ar")["text"]
    assert dm(3001, 5, "/ar") == {}
    assert "Use Nous" in dm(3001, 7, "post and pay all invoices")["text"]
    draft = f"/draft {identifier(61)} 2020-01-01 2020-01-31"
    preview = dm(3001, 8, draft)["text"]
    token = preview.split("/confirm ")[1].split()[0]
    assert dm(3001, 8, draft) == {}
    assert "invalid" in dm(3002, 9, f"/confirm {token}")["text"]
    draft_tool.assert_not_awaited()
    with ThreadPoolExecutor(max_workers=2) as executor:
        one = executor.submit(dm, 3001, 10, f"/confirm {token}")
        two = executor.submit(dm, 3001, 11, f"/confirm {token}")
        replies = [one.result()["text"], two.result()["text"]]
    assert sum("queued" in reply for reply in replies) == 1
    assert all("never echo" not in reply for reply in replies)
    draft_tool.assert_awaited_once()
    _, ctx, args = draft_tool.await_args.args
    assert (ctx.tenant_id, ctx.user_id, ctx.scope) == (
        identifier(1),
        identifier(21),
        "telegram:confirmed_invoice_review",
    )
    assert args == {
        "engagement_id": identifier(61),
        "period_start": "2020-01-01",
        "period_end": "2020-01-31",
    }
    assert {
        row["tenant_id"] for row in db.from_("chat_threads").select("tenant_id").execute().data
    } == {identifier(1), identifier(2)}
    assert (
        len(
            db.from_("telegram_erp_deliveries")
            .select("update_id")
            .eq("outcome", "queued")
            .execute()
            .data
        )
        == 1
    )

    token = dm(3001, 12, draft)["text"].split("/confirm ")[1].split()[0]
    past = (datetime.now(UTC) - timedelta(seconds=2)).isoformat()
    db.from_("telegram_erp_deliveries").update({"confirmation_expires_at": past}).eq(
        "update_id", 12
    ).execute()
    assert "expired" in dm(3001, 13, f"/confirm {token}")["text"]
    db.from_("tenant_users").update({"deleted_at": past}).eq("id", identifier(12)).execute()
    assert "unavailable" in dm(3002, 14, "/ar")["text"]
    assert client.delete(f"{BASE}/link", headers=auth(22, 1)).status_code == 204
    assert "125.00" in dm(3001, 15, "/ar")["text"]  # cross-tenant unlink was a no-op
    assert client.delete(f"{BASE}/link", headers=auth(21, 1)).status_code == 204
    assert "No active ERP link" in dm(3001, 16, "/ar")["text"]
    draft_tool.assert_awaited_once()
