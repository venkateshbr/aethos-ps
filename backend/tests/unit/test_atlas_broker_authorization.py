"""Offline contract checks for broker authorization; no ERP handlers run."""

import re
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import atlas_tools
from app.services.agent_run_ledger import AgentRunLedger
from app.services.atlas_context import AtlasToolContext
from app.services.security_service import SecurityService

pytestmark = pytest.mark.unit

_RISK_GRANT = {
    "read_only": "atlas.tools.read",
    "draft": "atlas.tools.execute_draft",
    "write_low_risk": "atlas.tools.execute_draft",
    "accounting": "atlas.tools.execute_draft",
    "write_money_in": "atlas.tools.execute_money_in",
    "write_money_out": "atlas.tools.execute_money_out",
}


@pytest.fixture
def broker(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    context = AtlasToolContext(
        "tenant-unit", "user-unit", "thread-unit", "atlas_tools:read", 0, "nonce"
    )
    monkeypatch.setattr(atlas_tools, "verify_atlas_context_ref", lambda *args, **kwargs: context)
    lookup = AsyncMock()
    monkeypatch.setattr(SecurityService, "effective_permissions", lookup)
    start = AsyncMock(return_value="run-unit")
    record = AsyncMock()
    monkeypatch.setattr(AgentRunLedger, "start_run", start)
    monkeypatch.setattr(AgentRunLedger, "record_tool_invocation", record)
    monkeypatch.setattr(AgentRunLedger, "complete_run", AsyncMock())
    db = MagicMock()
    controls = db.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute
    controls.return_value.data = []
    return SimpleNamespace(
        context=context, db=db, lookup=lookup, record=record, start=start, controls=controls
    )


def _permissions(role: str, grants: list[str], *, locked: bool = False) -> SimpleNamespace:
    return SimpleNamespace(legacy_role=role, privilege_codes=grants, must_change_password=locked)


def _mock_handler(monkeypatch: pytest.MonkeyPatch, tool_name: str) -> AsyncMock:
    handler = AsyncMock(return_value={"mock": True})
    entry = atlas_tools._TOOL_DISPATCH[tool_name]
    monkeypatch.setitem(atlas_tools._TOOL_DISPATCH, tool_name, replace(entry, handler=handler))
    return handler


async def _execute(broker: SimpleNamespace, tool_name: str) -> atlas_tools.AtlasToolExecuteResponse:
    return await atlas_tools.execute_atlas_tool(
        atlas_tools.AtlasToolExecuteRequest(context_ref="unit-context", tool_name=tool_name),
        _auth=None,
        db=broker.db,
    )


@pytest.mark.parametrize("role", ["viewer", "member", "manager", "admin"])
@pytest.mark.parametrize("tool_name", tuple(atlas_tools._TOOL_DISPATCH))
async def test_catalog_requires_explicit_permission(
    monkeypatch: pytest.MonkeyPatch, broker: SimpleNamespace, role: str, tool_name: str
) -> None:
    broker.lookup.return_value = _permissions(
        role, list(atlas_tools._TOOL_DISPATCH[tool_name].privileges)
    )
    handler = _mock_handler(monkeypatch, tool_name)
    with pytest.raises(HTTPException) as exc:
        await _execute(broker, tool_name)
    assert exc.value.status_code == 403
    handler.assert_not_awaited()
    broker.lookup.assert_awaited_once_with(broker.context.user_id)
    assert broker.record.await_args.kwargs["status"] == "skipped"


@pytest.mark.parametrize("tool_name", tuple(atlas_tools._TOOL_DISPATCH))
async def test_catalog_dispatches_only_with_domain_and_risk_grants(
    monkeypatch: pytest.MonkeyPatch, broker: SimpleNamespace, tool_name: str
) -> None:
    tool = atlas_tools._TOOL_DISPATCH[tool_name]
    base = _RISK_GRANT[tool.risk_class]
    handler = _mock_handler(monkeypatch, tool_name)
    broker.lookup.return_value = _permissions("admin", [base])
    with pytest.raises(HTTPException) as exc:
        await _execute(broker, tool_name)
    assert exc.value.status_code == 403
    handler.assert_not_awaited()

    broker.lookup.return_value = _permissions("admin", [base, *tool.privileges])
    response = await _execute(broker, tool_name)
    assert response.result == {"mock": True}
    handler.assert_awaited_once_with(broker.db, broker.context, {})
    assert broker.record.await_args.kwargs["status"] == "succeeded"
    assert broker.record.await_args.kwargs["input_payload"] is None
    assert broker.record.await_args.kwargs["output_payload"] is None


@pytest.mark.parametrize(
    "row",
    [
        {"is_enabled": False},
        {"circuit_open_until": "2099-01-01T00:00:00+00:00"},
        {"is_enabled": True, "level": 1},
    ],
)
async def test_manual_journal_review_respects_action_controls(
    monkeypatch: pytest.MonkeyPatch, broker: SimpleNamespace, row: dict
) -> None:
    tool_name = "aethos.r2r.prepare_manual_journal_review"
    handler = _mock_handler(monkeypatch, tool_name)
    broker.lookup.return_value = _permissions(
        "admin", ["atlas.tools.execute_draft", "accounting.journal_prepare"]
    )
    broker.controls.return_value.data = [{"action_type": "draft_journal", **row}]
    with pytest.raises(HTTPException) as exc:
        await _execute(broker, tool_name)
    assert exc.value.status_code == 403
    handler.assert_not_awaited()


@pytest.mark.parametrize(
    "failure, expected",
    [
        (HTTPException(404), 403),
        (RuntimeError("lookup unavailable"), 503),
    ],
)
async def test_membership_lookup_failure_never_dispatches(
    monkeypatch: pytest.MonkeyPatch, broker: SimpleNamespace, failure: Exception, expected: int
) -> None:
    tool_name = "aethos.engagements.list"
    handler = _mock_handler(monkeypatch, tool_name)
    broker.lookup.side_effect = failure
    with pytest.raises(HTTPException) as exc:
        await _execute(broker, tool_name)
    assert exc.value.status_code == expected
    handler.assert_not_awaited()


# Independent contract: AR, AP, WIP and active engagements are all-or-nothing.
_SNAPSHOT_GRANTS = {
    "atlas.tools.read",
    "reports.read",
    "invoices.read",
    "bills.read",
    "accounting.read",
    "engagements.read",
    "time_entries.read",
}


@pytest.mark.parametrize("missing", sorted(_SNAPSHOT_GRANTS))
async def test_snapshot_requires_each_component_grant(
    monkeypatch: pytest.MonkeyPatch, broker: SimpleNamespace, missing: str
) -> None:
    name = "aethos.finance_ops.snapshot"
    handler = _mock_handler(monkeypatch, name)
    broker.lookup.return_value = _permissions("manager", sorted(_SNAPSHOT_GRANTS - {missing}))
    with pytest.raises(HTTPException) as exc:
        await _execute(broker, name)
    assert exc.value.status_code == 403
    handler.assert_not_awaited()


@pytest.fixture
def finance_seed() -> dict[str, set[str]]:
    migration = (
        Path(__file__).resolve().parents[2]
        / "supabase/migrations/0096_dynamics_style_security_catalog.sql"
    )
    pairs = set(re.findall(r"\('([a-z_]+)', '([a-z._]+)'\)", migration.read_text()))
    return {
        role: {
            privilege
            for key, duty in pairs
            if key == role
            for duty_key, privilege in pairs
            if duty_key == duty and "." in privilege
        }
        for role in ("executive_viewer", "finance_approver", "finance_ops_manager")
    }


@pytest.mark.parametrize(
    ("seed_role", "membership_role", "manager_access"),
    [
        ("executive_viewer", "viewer", False),
        ("finance_approver", "approver", False),
        ("finance_ops_manager", "manager", True),
    ],
)
async def test_seeded_finance_roles_keep_snapshot_but_control_room_is_manager_only(
    monkeypatch: pytest.MonkeyPatch,
    broker: SimpleNamespace,
    finance_seed: dict[str, set[str]],
    seed_role: str,
    membership_role: str,
    manager_access: bool,
) -> None:
    grants = finance_seed[seed_role]
    assert _SNAPSHOT_GRANTS | {"inbox.read", "agent.autonomy.read"} <= grants
    broker.lookup.return_value = _permissions(membership_role, sorted(grants))
    snapshot = "aethos.finance_ops.snapshot"
    _mock_handler(monkeypatch, snapshot)
    assert (await _execute(broker, snapshot)).result == {"mock": True}

    control_room = "aethos.finance_ops.control_room"
    handler = _mock_handler(monkeypatch, control_room)
    if manager_access:
        assert (await _execute(broker, control_room)).result == {"mock": True}
        handler.assert_awaited_once()
    else:
        with pytest.raises(HTTPException) as exc:
            await _execute(broker, control_room)
        assert exc.value.status_code == 403
        handler.assert_not_awaited()


async def test_configuration_telemetry_preserves_nested_control_room_role_gate(
    monkeypatch: pytest.MonkeyPatch, broker: SimpleNamespace
) -> None:
    name = "aethos.configuration_telemetry.read_pack"
    handler = _mock_handler(monkeypatch, name)
    grants = _SNAPSHOT_GRANTS | {
        "inbox.read",
        "agent.autonomy.read",
        "settings.manage",
        "ai.settings.read",
    }
    broker.lookup.return_value = _permissions("viewer", sorted(grants))
    with pytest.raises(HTTPException) as exc:
        await _execute(broker, name)
    assert exc.value.status_code == 403
    handler.assert_not_awaited()
