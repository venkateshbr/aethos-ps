"""Synthetic Telegram transport contract, without external network access."""
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import get_service_role_client
from fastapi import FastAPI

pytestmark = pytest.mark.unit
BASE = "/api/v1/telegram"
SECRET = "synthetic_" + "a" * 40
HEADERS = {"X-Telegram-Bot-Api-Secret-Token": SECRET}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_service_role_client] = lambda: None
    monkeypatch.setitem(settings.__dict__, "telegram_erp_enabled", False)
    monkeypatch.setitem(settings.__dict__, "telegram_erp_webhook_secret", SECRET)
    return TestClient(app)


def update(text: str = "/id", **fields: Any) -> dict:
    return {"update_id": 31, "message": {
        "chat": {"id": 2001, "type": "private"}, "from": {"id": 2001, "is_bot": False},
        "text": text, "date": int(time.time()), **fields,
    }}


def test_disabled_then_authenticated_private_id(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.post(f"{BASE}/webhook", headers=HEADERS, json=update()).status_code == 404
    monkeypatch.setitem(settings.__dict__, "telegram_erp_enabled", True)
    assert client.post(f"{BASE}/webhook", json=update()).status_code == 401
    response = client.post(f"{BASE}/webhook", headers=HEADERS, json=update())
    assert response.status_code == 200
    assert response.json() == {"method": "sendMessage", "chat_id": 2001,
                               "text": "Your Telegram sender ID is 2001.", "protect_content": True}


@pytest.mark.parametrize("body", [
    {"update_id": 31, "channel_post": {"text": "/id"}},
    update(chat={"id": -2001, "type": "supergroup"}),
    update(chat={"id": 2002, "type": "private"}),
    update(date=1),
    update(forward_origin={"type": "hidden_user"}),
])
def test_ignored_update_never_replies(client: TestClient, monkeypatch: pytest.MonkeyPatch, body: dict) -> None:
    monkeypatch.setitem(settings.__dict__, "telegram_erp_enabled", True)
    response = client.post(f"{BASE}/webhook", headers=HEADERS, json=body)
    assert response.status_code == 200
    assert response.json() == {}


def test_link_requires_erp_session(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(settings.__dict__, "telegram_erp_enabled", True)
    assert client.post(f"{BASE}/link", json={"sender_id": 2001}).status_code == 401
    assert client.delete(f"{BASE}/link").status_code == 401
