"""API contract tests for the internal Atlas tool broker."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import atlas_tools
from app.core.db import get_service_role_client
from app.main import app
from app.services import atlas_context

pytestmark = pytest.mark.unit

TENANT_ID = "tenant-from-context"
USER_ID = "user-1"
THREAD_ID = "thread-1"
BROKER_TOKEN = "broker-token"
SIGNING_SECRET = "context-secret"


class _ForbiddenDb:
    def table(self, name: str) -> None:
        raise AssertionError(f"unexpected direct DB access to {name}")


class _EngagementResult:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return self.payload


def _context_ref(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", SIGNING_SECRET)
    return atlas_context.create_atlas_context_ref(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        thread_id=THREAD_ID,
    )


def _install_broker_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(atlas_tools.settings, "aethos_hermes_tool_token", BROKER_TOKEN)
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()


def test_atlas_tool_broker_requires_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atlas_tools.settings, "aethos_hermes_tool_token", "")
    app.dependency_overrides[get_service_role_client] = lambda: _ForbiddenDb()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                json={
                    "context_ref": "invalid",
                    "tool_name": "aethos.finance.ar_aging",
                    "arguments": {},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


def test_atlas_tool_broker_rejects_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": "Bearer wrong-token"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.finance.ar_aging",
                    "arguments": {},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_atlas_tool_broker_rejects_invalid_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": "not-a-context",
                    "tool_name": "aethos.finance.ar_aging",
                    "arguments": {},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400


def test_atlas_tool_broker_lists_engagements_with_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _EngagementService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        async def list_engagements(
            self,
            *,
            status: str | None,
            client_id: str | None,
            limit: int,
            offset: int,
        ) -> list[_EngagementResult]:
            calls.append(
                {
                    "status": status,
                    "client_id": client_id,
                    "limit": limit,
                    "offset": offset,
                }
            )
            return [
                _EngagementResult(
                    {
                        "id": "eng-1",
                        "tenant_id": TENANT_ID,
                        "name": "Nexus mixed billing",
                    }
                )
            ]

    monkeypatch.setattr(atlas_tools, "EngagementService", _EngagementService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.engagements.list",
                    "arguments": {
                        "status": "active",
                        "client_id": "client-1",
                        "limit": 5,
                        "offset": 2,
                        "tenant_id": "tenant-model-tried-to-pass",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {
        "status": "active",
        "client_id": "client-1",
        "limit": 5,
        "offset": 2,
    }
    assert response.json()["result"][0]["id"] == "eng-1"


def test_atlas_tool_broker_finance_snapshot_uses_report_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    report_tenants: list[str] = []

    class _ReportsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            report_tenants.append(tenant_id)

        def ar_aging(self) -> dict[str, str]:
            return {"total": "100.00"}

        def ap_aging(self) -> dict[str, str]:
            return {"total": "40.00"}

        def wip(self, *, engagement_id: str | None = None) -> list[dict[str, str | None]]:
            return [{"engagement_id": engagement_id, "wip_value": "25.00"}]

    class _EngagementService:
        def __init__(self, db: object, tenant_id: str) -> None:
            assert tenant_id == TENANT_ID

        async def list_engagements(
            self,
            *,
            status: str | None,
            client_id: str | None,
            limit: int,
            offset: int,
        ) -> list[_EngagementResult]:
            assert status == "active"
            assert client_id is None
            assert limit == 2
            assert offset == 0
            return [_EngagementResult({"id": "eng-active", "tenant_id": TENANT_ID})]

    monkeypatch.setattr(atlas_tools, "ReportsService", _ReportsService)
    monkeypatch.setattr(atlas_tools, "EngagementService", _EngagementService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.finance_ops.snapshot",
                    "arguments": {"engagement_limit": 2},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["ar_aging"]["total"] == "100.00"
    assert result["ap_aging"]["total"] == "40.00"
    assert result["wip"][0]["wip_value"] == "25.00"
    assert result["active_engagements"][0]["id"] == "eng-active"
    assert report_tenants == [TENANT_ID, TENANT_ID, TENANT_ID]


def test_atlas_tool_broker_finance_ops_control_room_uses_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _AgentsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        def get_finance_ops_control_room(
            self,
            *,
            workflow_limit: int,
            task_limit: int,
        ) -> dict[str, Any]:
            calls.append({"workflow_limit": workflow_limit, "task_limit": task_limit})
            return {
                "tenant_id": TENANT_ID,
                "latest_scheduled_run": {"status": "waiting_on_human"},
                "open_action_plans": [{"id": "task-plan"}],
            }

    monkeypatch.setattr(atlas_tools, "AgentsService", _AgentsService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.finance_ops.control_room",
                    "arguments": {
                        "workflow_limit": 4,
                        "task_limit": 3,
                        "tenant_id": "tenant-model-tried-to-pass",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {"workflow_limit": 4, "task_limit": 3}
    assert response.json()["result"]["open_action_plans"][0]["id"] == "task-plan"


def test_atlas_tool_broker_approval_controls_uses_context_user_and_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _AgentsService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        def get_approval_controls_read_pack(
            self,
            *,
            user_id: str,
            inbox_limit: int,
        ) -> dict[str, Any]:
            calls.append({"user_id": user_id, "inbox_limit": inbox_limit})
            return {
                "tenant_id": TENANT_ID,
                "current_user_role": "manager",
                "pending_high_risk_inbox": [{"id": "task-owner-pay"}],
            }

    monkeypatch.setattr(atlas_tools, "AgentsService", _AgentsService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.approval_controls.read_pack",
                    "arguments": {
                        "inbox_limit": 7,
                        "tenant_id": "tenant-model-tried-to-pass",
                        "user_id": "user-model-tried-to-pass",
                        "role": "owner",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {"user_id": USER_ID, "inbox_limit": 7}
    assert response.json()["result"]["pending_high_risk_inbox"][0]["id"] == "task-owner-pay"


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_method", "expected_kwargs"),
    [
        (
            "aethos.documents.intake_read_pack",
            {"filename": "nexus_engagement_letter.pdf", "limit": 3},
            "document_intake_read_pack",
            {"document_id": None, "filename": "nexus_engagement_letter.pdf", "limit": 3},
        ),
        (
            "aethos.documents.audit_read_pack",
            {"limit": 12},
            "documents_audit_read_pack",
            {"limit": 12},
        ),
        (
            "aethos.engagements.structure_read_pack",
            {"client_name": "Nexus", "limit": 6},
            "engagement_structure_read_pack",
            {"client_name": "Nexus", "engagement_name": None, "limit": 6},
        ),
        (
            "aethos.delivery.resource_read_pack",
            {"employee_name": "Alice Chen", "client_name": "Nexus", "period": "June 2026"},
            "resource_delivery_read_pack",
            {
                "employee_name": "Alice Chen",
                "project_name": None,
                "client_name": "Nexus",
                "period": "2026-06",
                "limit": 100,
            },
        ),
        (
            "aethos.r2r.accounting_decision_trail_read_pack",
            {"limit": 9},
            "accounting_decision_trail_read_pack",
            {"limit": 9},
        ),
    ],
)
def test_atlas_tool_broker_new_read_packs_use_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    arguments: dict[str, Any],
    expected_method: str,
    expected_kwargs: dict[str, Any],
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _AtlasReadPackService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        def document_intake_read_pack(self, **kwargs: Any) -> dict[str, Any]:
            calls.append({"method": "document_intake_read_pack", "kwargs": kwargs})
            return {"tenant_id": TENANT_ID, "documents": [{"id": "doc-1"}]}

        def documents_audit_read_pack(self, **kwargs: Any) -> dict[str, Any]:
            calls.append({"method": "documents_audit_read_pack", "kwargs": kwargs})
            return {"tenant_id": TENANT_ID, "documents": [{"id": "doc-audit"}]}

        def engagement_structure_read_pack(self, **kwargs: Any) -> dict[str, Any]:
            calls.append({"method": "engagement_structure_read_pack", "kwargs": kwargs})
            return {"tenant_id": TENANT_ID, "engagements": [{"id": "eng-1"}]}

        def resource_delivery_read_pack(self, **kwargs: Any) -> dict[str, Any]:
            calls.append({"method": "resource_delivery_read_pack", "kwargs": kwargs})
            return {"tenant_id": TENANT_ID, "summary": {"approved_hours": "9.0"}}

        def accounting_decision_trail_read_pack(self, **kwargs: Any) -> dict[str, Any]:
            calls.append({"method": "accounting_decision_trail_read_pack", "kwargs": kwargs})
            return {"tenant_id": TENANT_ID, "latest_decisions": [{"id": "task-1"}]}

    monkeypatch.setattr(atlas_tools, "AtlasReadPackService", _AtlasReadPackService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": tool_name,
                    "arguments": {
                        **arguments,
                        "tenant_id": "tenant-model-tried-to-pass",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {"method": expected_method, "kwargs": expected_kwargs}
    assert response.json()["result"]["tenant_id"] == TENANT_ID


def test_atlas_tool_broker_operational_health_read_pack_uses_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _AtlasReadPackService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        def operational_health_read_pack(self) -> dict[str, Any]:
            calls.append({"method": "operational_health_read_pack"})
            return {
                "tenant_id": TENANT_ID,
                "status": "ok",
                "safety_contract": {"exposes_secrets": False},
            }

    monkeypatch.setattr(atlas_tools, "AtlasReadPackService", _AtlasReadPackService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.operational_health.read_pack",
                    "arguments": {"tenant_id": "tenant-model-tried-to-pass"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {"method": "operational_health_read_pack"}
    assert response.json()["result"]["safety_contract"]["exposes_secrets"] is False


def test_atlas_tool_broker_creates_engagement_review_without_internal_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    def _resolve_client(db: object, tenant_id: str, client_name: str) -> dict[str, str]:
        calls.append(
            {"method": "_resolve_client", "tenant_id": tenant_id, "client_name": client_name}
        )
        return {"id": "client-nexus", "name": "Nexus Capital Partners LP"}

    async def _write_agent_suggestion(**kwargs: Any) -> dict[str, str]:
        calls.append(
            {
                "method": "write_agent_suggestion",
                "tenant_id": kwargs["deps"].tenant_id,
                "user_id": kwargs["deps"].user_id,
                "agent_name": kwargs["agent_name"],
                "action_type": kwargs["action_type"],
                "output": kwargs["output"],
                "related_entity_id": kwargs["related_entity_id"],
            }
        )
        return {"id": "suggestion-eng"}

    monkeypatch.setattr(atlas_tools, "_resolve_client", _resolve_client)
    monkeypatch.setattr(atlas_tools, "write_agent_suggestion", _write_agent_suggestion)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.engagements.create_review",
                    "arguments": {
                        "client_name": "Nexus",
                        "engagement_name": "Nexus - Corporation Tax Return FY2025",
                        "currency": "GBP",
                        "fixed_fee_amount": "18500",
                        "cap_amount": "22000",
                        "description": "Corporation tax return with capped advisory overrun",
                        "tenant_id": "tenant-model-tried-to-pass",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0] == {
        "method": "_resolve_client",
        "tenant_id": TENANT_ID,
        "client_name": "Nexus",
    }
    assert calls[1]["tenant_id"] == TENANT_ID
    assert calls[1]["user_id"] == USER_ID
    assert calls[1]["agent_name"] == "engagement_letter_agent"
    assert calls[1]["action_type"] == "create_engagement_draft"
    assert calls[1]["related_entity_id"] == "client-nexus"
    output = calls[1]["output"]
    assert output["client_id"] == "client-nexus"
    assert output["billing_arrangement"] == "capped_tm"
    assert output["service_line"] == "tax"
    assert output["fixed_fee_amount"] == "18500.00"
    assert output["cap_amount"] == "22000.00"
    result = response.json()["result"]
    assert result["requires_review"] is True
    assert result["review_path"] == "/app/inbox"


def test_atlas_tool_broker_o2c_collections_read_pack_uses_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _O2CReadService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        def collections_read_pack(
            self,
            *,
            invoice_id: str | None,
            invoice_number: str | None,
            client_id: str | None,
            client_name: str | None,
            status: str | None,
            limit: int,
        ) -> dict[str, Any]:
            calls.append(
                {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "client_id": client_id,
                    "client_name": client_name,
                    "status": status,
                    "limit": limit,
                }
            )
            return {
                "tenant_id": TENANT_ID,
                "invoices": [{"id": "inv-overdue", "invoice_state": "overdue"}],
            }

    monkeypatch.setattr(atlas_tools, "O2CReadService", _O2CReadService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.o2c.collections_read_pack",
                    "arguments": {
                        "invoice_number": "INV-1001",
                        "client_name": "Northstar",
                        "status": "sent",
                        "limit": 6,
                        "tenant_id": "tenant-model-tried-to-pass",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {
        "invoice_id": None,
        "invoice_number": "INV-1001",
        "client_id": None,
        "client_name": "Northstar",
        "status": "sent",
        "limit": 6,
    }
    assert response.json()["result"]["invoices"][0]["id"] == "inv-overdue"


def test_atlas_tool_broker_p2p_payment_risk_read_pack_uses_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _P2PReadService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        def payment_risk_read_pack(
            self,
            *,
            bill_id: str | None,
            bill_number: str | None,
            vendor_id: str | None,
            vendor_name: str | None,
            status: str | None,
            due_within_days: int,
            limit: int,
        ) -> dict[str, Any]:
            calls.append(
                {
                    "bill_id": bill_id,
                    "bill_number": bill_number,
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "status": status,
                    "due_within_days": due_within_days,
                    "limit": limit,
                }
            )
            return {
                "tenant_id": TENANT_ID,
                "bills": [{"id": "bill-ready", "payment_readiness": "ready"}],
            }

    monkeypatch.setattr(atlas_tools, "P2PReadService", _P2PReadService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.p2p.payment_risk_read_pack",
                    "arguments": {
                        "bill_number": "BILL-1001",
                        "vendor_name": "Forster",
                        "status": "approved",
                        "due_within_days": 14,
                        "limit": 8,
                        "tenant_id": "tenant-model-tried-to-pass",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {
        "bill_id": None,
        "bill_number": "BILL-1001",
        "vendor_id": None,
        "vendor_name": "Forster",
        "status": "approved",
        "due_within_days": 14,
        "limit": 8,
    }
    assert response.json()["result"]["bills"][0]["id"] == "bill-ready"


def test_atlas_tool_broker_r2r_management_pack_uses_context_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _R2RReadService:
        def __init__(self, db: object, tenant_id: str) -> None:
            calls.append({"db": db, "tenant_id": tenant_id})

        def management_pack_read_pack(
            self,
            *,
            period: str,
            comparison_period: str | None,
            limit: int,
        ) -> dict[str, Any]:
            calls.append(
                {
                    "period": period,
                    "comparison_period": comparison_period,
                    "limit": limit,
                }
            )
            return {
                "tenant_id": TENANT_ID,
                "period": period,
                "comparison_period": comparison_period,
                "close_status": {"status": "locked"},
            }

    monkeypatch.setattr(atlas_tools, "R2RReadService", _R2RReadService)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.r2r.management_pack_read_pack",
                    "arguments": {
                        "period": "June 2026",
                        "comparison_period": "2026-05-31",
                        "limit": 7,
                        "tenant_id": "tenant-model-tried-to-pass",
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[1] == {
        "period": "2026-06",
        "comparison_period": "2026-05",
        "limit": 7,
    }
    assert response.json()["result"]["close_status"]["status"] == "locked"


def test_atlas_tool_broker_creates_finance_ops_action_plan_through_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _CopilotAgent:
        def __init__(self, deps: object) -> None:
            calls.append(
                {
                    "tenant_id": deps.tenant_id,
                    "user_id": deps.user_id,
                    "db_client": deps.db_client,
                }
            )

        async def _execute_tool_with_policy(
            self,
            tool_name: str,
            tool_input: dict[str, Any],
        ) -> dict[str, Any]:
            calls.append({"tool_name": tool_name, "tool_input": tool_input})
            return {
                "requires_review": True,
                "suggestion_id": "suggestion-1",
                "message": "Created an Inbox review task before applying this change.",
            }

    monkeypatch.setattr(atlas_tools, "CopilotAgent", _CopilotAgent)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.finance_ops.create_action_plan",
                    "arguments": {"period": "2026-06", "limit": 3},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0]["tenant_id"] == TENANT_ID
    assert calls[0]["user_id"] == USER_ID
    assert calls[1] == {
        "tool_name": "create_finance_ops_action_plan",
        "tool_input": {"limit": 3, "period": "2026-06"},
    }
    assert response.json()["result"]["requires_review"] is True


@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_tool", "expected_input"),
    [
        (
            "aethos.o2c.draft_invoice",
            {
                "engagement_name": "Nexus Advisory",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
            },
            "draft_invoice",
            {
                "engagement_name": "Nexus Advisory",
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
            },
        ),
        (
            "aethos.collections.draft_reminders",
            {"minimum_days_overdue": 15, "tone": "firm", "limit": 4},
            "draft_collection_reminders",
            {"minimum_days_overdue": 15, "tone": "firm", "limit": 4},
        ),
        (
            "aethos.time.log_entry",
            {
                "project_name": "Nexus CFO Advisory",
                "hours": "4.5",
                "date": "2026-06-29",
                "description": "Board pack review and cash flow modelling",
            },
            "log_time_entry",
            {
                "project_name": "Nexus CFO Advisory",
                "hours": "4.5",
                "date": "2026-06-29",
                "description": "Board pack review and cash flow modelling",
                "billable": True,
            },
        ),
        (
            "aethos.p2p.propose_bill_payment_batch",
            {"due_within_days": 10, "bank_account_label": "Operating"},
            "propose_bill_payment_batch",
            {"due_within_days": 10, "bank_account_label": "Operating"},
        ),
        (
            "aethos.r2r.prepare_month_end_close",
            {"period": "2026-06"},
            "prepare_month_end_close",
            {"period": "2026-06"},
        ),
        (
            "aethos.r2r.prepare_year_end_close",
            {"year": 2026},
            "prepare_year_end_close",
            {"year": 2026},
        ),
        (
            "aethos.r2r.generate_financial_statement_package",
            {
                "period_start": "2026-04",
                "period_end": "2026-06",
                "comparison_period_start": "2025-04",
                "comparison_period_end": "2025-06",
            },
            "generate_financial_statement_package",
            {
                "period_start": "2026-04",
                "period_end": "2026-06",
                "comparison_period_start": "2025-04",
                "comparison_period_end": "2025-06",
            },
        ),
        (
            "aethos.r2r.generate_financial_statement_package",
            {
                "period_start": "June 2026",
                "period_end": "2026-06-30",
                "comparison_period_start": "May 2026",
                "comparison_period_end": "2026-05-31",
            },
            "generate_financial_statement_package",
            {
                "period_start": "2026-06",
                "period_end": "2026-06",
                "comparison_period_start": "2026-05",
                "comparison_period_end": "2026-05",
            },
        ),
    ],
)
def test_atlas_tool_broker_routes_current_copilot_workflows_through_policy(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    arguments: dict[str, Any],
    expected_tool: str,
    expected_input: dict[str, Any],
) -> None:
    context_ref = _context_ref(monkeypatch)
    calls: list[dict[str, Any]] = []

    class _CopilotAgent:
        def __init__(self, deps: object) -> None:
            calls.append({"tenant_id": deps.tenant_id, "user_id": deps.user_id})

        async def _execute_tool_with_policy(
            self,
            tool_name: str,
            tool_input: dict[str, Any],
        ) -> dict[str, Any]:
            calls.append({"tool_name": tool_name, "tool_input": tool_input})
            return {"requires_review": True, "tool_name": tool_name}

    monkeypatch.setattr(atlas_tools, "CopilotAgent", _CopilotAgent)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert calls[0] == {"tenant_id": TENANT_ID, "user_id": USER_ID}
    assert calls[1] == {"tool_name": expected_tool, "tool_input": expected_input}
    assert response.json()["result"]["requires_review"] is True


def test_atlas_tool_broker_rejects_unknown_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context_ref = _context_ref(monkeypatch)
    _install_broker_overrides(monkeypatch)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/atlas-tools/execute",
                headers={"Authorization": f"Bearer {BROKER_TOKEN}"},
                json={
                    "context_ref": context_ref,
                    "tool_name": "aethos.unsafe.write",
                    "arguments": {},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
