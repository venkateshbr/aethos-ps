"""Offline contract checks for broker authorization; no ERP handlers run."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import atlas_tools
from app.services.atlas_context import AtlasToolContext
from app.services.security_service import SecurityService

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("role", ["viewer", "member", "manager", "admin"])
@pytest.mark.parametrize("tool_name", tuple(atlas_tools._TOOL_DISPATCH))
async def test_catalog_requires_explicit_permission(monkeypatch, role, tool_name):
    context = AtlasToolContext("tenant-unit", "user-unit", "thread-unit", "atlas_tools:read", 0, "nonce")
    monkeypatch.setattr(atlas_tools, "verify_atlas_context_ref", lambda *args, **kwargs: context)
    lookup = AsyncMock(return_value=SimpleNamespace(legacy_role=role, privilege_codes=[]))
    monkeypatch.setattr(SecurityService, "effective_permissions", lookup)
    handler = AsyncMock(return_value={"mock": True})
    entry = atlas_tools._TOOL_DISPATCH[tool_name]
    # Accommodate both the original callable and the classified entry during RED.
    if callable(entry):
        replacement = handler
    else:
        from dataclasses import replace

        replacement = replace(entry, handler=handler)
    monkeypatch.setitem(atlas_tools._TOOL_DISPATCH, tool_name, replacement)
    with pytest.raises(HTTPException) as exc:
        await atlas_tools.execute_atlas_tool(
            atlas_tools.AtlasToolExecuteRequest(context_ref="unit-context", tool_name=tool_name),
            _auth=None,
            db=MagicMock(),
        )
    assert exc.value.status_code == 403
    handler.assert_not_awaited()
    lookup.assert_awaited_once_with(context.user_id)
