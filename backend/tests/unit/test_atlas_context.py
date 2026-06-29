"""Tests for Atlas internal tool-call context references."""

from __future__ import annotations

import pytest

from app.services import atlas_context

pytestmark = pytest.mark.unit


def test_atlas_context_ref_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "secret")

    context_ref = atlas_context.create_atlas_context_ref(
        tenant_id="tenant-1",
        user_id="user-1",
        thread_id="thread-1",
        now=100,
    )

    context = atlas_context.verify_atlas_context_ref(context_ref, now=101)

    assert context.tenant_id == "tenant-1"
    assert context.user_id == "user-1"
    assert context.thread_id == "thread-1"
    assert context.scope == "atlas_tools:read"


def test_atlas_context_ref_rejects_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "secret")

    context_ref = atlas_context.create_atlas_context_ref(
        tenant_id="tenant-1",
        user_id="user-1",
        thread_id="thread-1",
        now=100,
    )
    replacement = "x" if context_ref[-1] != "x" else "y"
    tampered = f"{context_ref[:-1]}{replacement}"

    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.verify_atlas_context_ref(tampered, now=101)


def test_atlas_context_ref_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "secret")

    context_ref = atlas_context.create_atlas_context_ref(
        tenant_id="tenant-1",
        user_id="user-1",
        thread_id="thread-1",
        ttl_seconds=10,
        now=100,
    )

    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.verify_atlas_context_ref(context_ref, now=111)


def test_atlas_context_requires_signing_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atlas_context.settings, "atlas_context_signing_secret", "")
    monkeypatch.setattr(atlas_context.settings, "supabase_jwt_secret", "")
    monkeypatch.setattr(atlas_context.settings, "aethos_hermes_tool_token", "")

    with pytest.raises(atlas_context.AtlasContextError):
        atlas_context.create_atlas_context_ref(
            tenant_id="tenant-1",
            user_id="user-1",
            thread_id="thread-1",
        )
