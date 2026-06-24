"""Supabase client dependency tests."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import db as db_module

pytestmark = pytest.mark.unit


class _Postgrest:
    def __init__(self) -> None:
        self.token: str | None = None

    def auth(self, token: str) -> None:
        self.token = token


class _Client:
    def __init__(self) -> None:
        self.postgrest = _Postgrest()


def test_get_user_rls_client_sets_caller_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    created = _Client()

    def _create_client(url: str, key: str) -> _Client:
        assert url == db_module.settings.supabase_url
        assert key == db_module.settings.supabase_anon_key
        return created

    monkeypatch.setattr(db_module, "create_client", _create_client)

    result = db_module.get_user_rls_client(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-token")
    )

    assert result is created
    assert created.postgrest.token == "jwt-token"


def test_get_user_rls_client_requires_bearer_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        db_module.get_user_rls_client(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
