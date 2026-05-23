"""API-suite fixtures.

Boots an httpx client against the running API (``http://localhost:8011`` by
default — override with ``AETHOS_PS_API_URL``). Seeds two tenants once per
session and exposes a ``world`` fixture for every test.

Skip rules
----------
- If the API is unreachable we **skip**, not fail — the user may want to run
  just the unit suite. The CI job that *requires* this suite asserts the API
  is up first.
- If env vars are missing we skip too, with a clear message naming the
  missing var.
"""

from __future__ import annotations

import os

import httpx
import pytest

# Bug #96 workaround: if list-typed env vars were shell-sourced from .env
# into the pytest process env, pydantic-settings cannot parse them. Drop the
# known offenders so in-process imports of app.core.config use .env directly.
for _k in ("AGENT_MODELS", "CORS_ORIGINS"):
    os.environ.pop(_k, None)

from tests.fixtures.scenarios import (
    SeedWorld,
    auth_headers,
    seed_two_tenants,
    sweep_clean,
)

API_URL = os.environ.get("AETHOS_PS_API_URL", "http://localhost:8011")


def _api_reachable(url: str) -> bool:
    try:
        r = httpx.get(f"{url}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def _env_present() -> tuple[bool, str | None]:
    for var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"):
        if not os.environ.get(var):
            return False, var
    return True, None


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return API_URL


@pytest.fixture(scope="session", autouse=True)
def _api_alive(api_base_url: str) -> None:
    """Session guard: skip the entire api suite if the API isn't up or env is missing."""
    ok, missing = _env_present()
    if not ok:
        pytest.skip(f"API suite skipped — {missing} not set. See docs/qa/MASTER_TEST_PLAN.md §1.")
    if not _api_reachable(api_base_url):
        pytest.skip(
            f"API suite skipped — {api_base_url}/health unreachable. "
            "Start the backend with `cd backend && uv run uvicorn app.main:app --port 8011`."
        )


@pytest.fixture(scope="session")
def world() -> SeedWorld:
    """Two-tenant deterministic seed, idempotent across sessions."""
    w = seed_two_tenants()
    yield w
    if os.environ.get("AKSHA_KEEP_SEED") != "1":
        sweep_clean(w)


@pytest.fixture
def client(api_base_url: str) -> httpx.Client:
    """Plain httpx client (no auth)."""
    with httpx.Client(base_url=api_base_url, timeout=15.0) as c:
        yield c


@pytest.fixture
def client_a(api_base_url: str, world: SeedWorld) -> httpx.Client:
    """Authenticated client as Tenant A owner."""
    headers = auth_headers(world.tenant_a, role="owner")
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def client_a_manager(api_base_url: str, world: SeedWorld) -> httpx.Client:
    headers = auth_headers(world.tenant_a, role="manager")
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def client_a_viewer(api_base_url: str, world: SeedWorld) -> httpx.Client:
    headers = auth_headers(world.tenant_a, role="viewer")
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c


@pytest.fixture
def client_b(api_base_url: str, world: SeedWorld) -> httpx.Client:
    """Authenticated client as Tenant B owner — used for cross-tenant isolation tests."""
    headers = auth_headers(world.tenant_b, role="owner")
    with httpx.Client(base_url=api_base_url, headers=headers, timeout=15.0) as c:
        yield c
