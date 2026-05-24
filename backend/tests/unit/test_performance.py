"""Unit tests for the performance-pass additions (issue #75).

Covers:
- GET /billing/subscription-status — response shape contract
- GET /health/ready               — structure of the readiness response
- datetime.utcnow deprecation fix — no utcnow() calls remain in app/
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# subscription_status — response shape
# ---------------------------------------------------------------------------


def test_subscription_status_returns_expected_keys_when_tenant_found():
    """subscription_status must return status, trial_ends_at, plan_tier."""
    from app.api.v1.endpoints.billing import subscription_status

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "stripe_subscription_status": "trialing",
            "trial_ends_at": "2026-06-03T00:00:00Z",
            "plan_tier": "starter",
        }
    ]

    result = subscription_status(tenant_id="tenant-123", db=mock_db, _=MagicMock())

    assert set(result.keys()) == {"status", "trial_ends_at", "plan_tier"}
    assert result["status"] == "trialing"
    assert result["plan_tier"] == "starter"
    assert result["trial_ends_at"] == "2026-06-03T00:00:00Z"


def test_subscription_status_returns_unknown_when_tenant_not_found():
    """subscription_status must return status=unknown when the tenant row is missing."""
    from app.api.v1.endpoints.billing import subscription_status

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    result = subscription_status(tenant_id="ghost-tenant", db=mock_db, _=MagicMock())

    assert result["status"] == "unknown"
    assert result["trial_ends_at"] is None
    assert result["plan_tier"] == "trial"


def test_subscription_status_defaults_missing_fields():
    """subscription_status must default stripe_subscription_status to 'trialing'."""
    from app.api.v1.endpoints.billing import subscription_status

    mock_db = MagicMock()
    # Tenant row exists but columns are absent
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{}]

    result = subscription_status(tenant_id="tenant-456", db=mock_db, _=MagicMock())

    assert result["status"] == "trialing"
    assert result["plan_tier"] == "trial"
    assert result["trial_ends_at"] is None


# ---------------------------------------------------------------------------
# health_ready — structure
# ---------------------------------------------------------------------------


async def _call_health_ready():
    from app.main import health_ready

    return await health_ready()


def test_health_ready_structure_on_db_ok():
    """health_ready must return status=ready and checks.db.status=ok on success."""
    import asyncio

    # Patch both create_client and settings so no real Supabase call is made
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        MagicMock()
    )

    with (
        patch("supabase.create_client", return_value=mock_client),
        patch("app.core.config.settings") as mock_settings,
    ):
        mock_settings.supabase_url = "https://fake.supabase.co"
        mock_settings.supabase_anon_key = "fake-key"
        mock_settings.upstash_redis_url = None

        result = asyncio.run(_call_health_ready())

    assert "status" in result
    assert "checks" in result
    assert isinstance(result["checks"], dict)


def test_health_ready_structure_keys():
    """health_ready must always include status and checks keys."""
    import asyncio

    # Force a DB failure to test degraded path
    with patch("supabase.create_client", side_effect=Exception("connection refused")):
        result = asyncio.run(_call_health_ready())

    assert "status" in result
    assert "checks" in result
    assert result["status"] == "degraded"
    assert result["checks"]["db"]["status"] == "error"


def test_health_ready_queue_not_configured_when_database_url_missing():
    """health_ready.checks.queue must be not_configured when database_url is falsy.

    Post-Procrastinate migration: the queue lives in Postgres, not Redis. The
    health check probes the Procrastinate connector (driven by `database_url`).
    """
    import asyncio

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        MagicMock()
    )

    with (
        patch("supabase.create_client", return_value=mock_client),
        patch("app.core.config.settings") as mock_settings,
    ):
        mock_settings.supabase_url = "https://fake.supabase.co"
        mock_settings.supabase_anon_key = "fake-key"
        mock_settings.database_url = ""  # not configured

        result = asyncio.run(_call_health_ready())

    assert result["checks"].get("queue") == {"status": "not_configured"}


# ---------------------------------------------------------------------------
# utcnow deprecation — static check
# ---------------------------------------------------------------------------


def test_no_utcnow_calls_in_app_source():
    """Ensure datetime.utcnow() has been purged from app/ source files.

    This is a regression guard: utcnow() is deprecated in Python 3.12 and
    removed in 3.14. All call-sites must use datetime.now(UTC) instead.
    """
    import pathlib

    app_dir = pathlib.Path(__file__).resolve().parents[2] / "app"
    offenders = []
    for py_file in app_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        if "utcnow()" in text:
            offenders.append(str(py_file.relative_to(app_dir.parent)))

    assert not offenders, (
        f"Found utcnow() in {len(offenders)} file(s) — replace with datetime.now(UTC):\n"
        + "\n".join(offenders)
    )
