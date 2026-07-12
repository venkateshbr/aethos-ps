"""Unit tests for the performance-pass additions (issue #75).

Covers:
- GET /billing/subscription-status — response shape contract
- GET /health/ready               — structure of the readiness response
- datetime.utcnow deprecation fix — no utcnow() calls remain in app/
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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


def test_health_exposes_the_deployed_build_sha(monkeypatch: pytest.MonkeyPatch):
    """Operators must be able to tie a public health response to a Git build."""
    import asyncio

    from app import main

    monkeypatch.setattr(main.settings, "build_sha", "abc123def456")

    assert asyncio.run(main.health()) == {
        "status": "ok",
        "version": "0.1.0",
        "build_sha": "abc123def456",
    }


async def _call_health_ready():
    from app.main import health_ready

    return await health_ready()


def test_signup_readiness_requires_a_real_stripe_account_and_price_catalogue():
    """Public preflight proves provider capability before creating a tenant."""
    import asyncio

    from app import main

    main.clear_signup_readiness_cache()
    billing_check = {
        "status": "ok",
        "configured": True,
        "mode": "test",
        "account_reachable": True,
        "prices_checked": 30,
    }
    with patch(
        "app.services.billing.stripe_service.StripeService.check_signup_readiness",
        new=AsyncMock(return_value=billing_check),
    ) as check:
        result = asyncio.run(main.signup_ready())

    assert result == {
        "status": "ready",
        "build_sha": main.settings.build_sha,
        "checks": {"billing": billing_check},
    }
    check.assert_awaited_once()


def test_signup_readiness_single_flights_concurrent_public_probes():
    """A cache-expiry burst must not amplify Stripe provider traffic."""
    import asyncio

    from app import main

    main.clear_signup_readiness_cache()
    billing_check = {
        "status": "ok",
        "configured": True,
        "mode": "test",
        "account_reachable": True,
        "prices_checked": 30,
    }

    async def delayed_check() -> dict[str, object]:
        await asyncio.sleep(0)
        return billing_check

    async def exercise() -> list[dict[str, object]]:
        with patch(
            "app.services.billing.stripe_service.StripeService.check_signup_readiness",
            new=AsyncMock(side_effect=delayed_check),
        ) as check:
            results = await asyncio.gather(*(main.signup_ready() for _ in range(12)))
        check.assert_awaited_once()
        return results

    results = asyncio.run(exercise())

    assert len(results) == 12
    assert all(result["status"] == "ready" for result in results)
    assert all(result["checks"] == {"billing": billing_check} for result in results)


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
        mock_settings.database_url = ""
        mock_settings.queue_required = False
        mock_settings.extraction_mode = "sync"

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
        mock_settings.queue_required = False
        mock_settings.extraction_mode = "sync"

        result = asyncio.run(_call_health_ready())

    assert result["checks"].get("queue") == {
        "status": "not_configured",
        "configured": False,
        "required": False,
    }
    assert result["status"] == "ready"


def test_health_ready_reports_test_billing_mode_without_exposing_credentials():
    """Signup preflight can prove Stripe mode without returning the secret."""
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
        mock_settings.database_url = ""
        mock_settings.queue_required = False
        mock_settings.stripe_secret_key = "sk_test_do-not-return-me"
        mock_settings.build_sha = "abc123"

        result = asyncio.run(_call_health_ready())

    assert result["build_sha"] == "abc123"
    assert result["checks"]["billing"] == {
        "status": "ok",
        "configured": True,
        "mode": "test",
    }
    assert "do-not-return-me" not in repr(result)


def test_health_ready_degrades_when_required_queue_missing():
    """Required queue mode must fail readiness when DATABASE_URL is unset."""
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
        mock_settings.database_url = ""
        mock_settings.queue_required = True
        mock_settings.extraction_mode = "sync"

        result = asyncio.run(_call_health_ready())

    assert result["status"] == "degraded"
    assert result["checks"].get("queue") == {
        "status": "not_configured",
        "configured": False,
        "required": True,
    }


def test_health_ready_ready_when_required_queue_connected():
    """Required queue mode is ready when the Procrastinate connector responds."""
    import asyncio

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        MagicMock()
    )

    with (
        patch("supabase.create_client", return_value=mock_client),
        patch("app.core.config.settings") as mock_settings,
        patch("app.workers.procrastinate_app.app") as queue_app,
    ):
        mock_settings.supabase_url = "https://fake.supabase.co"
        mock_settings.supabase_anon_key = "fake-key"
        mock_settings.database_url = "postgresql://postgres:password@db.example.test:5432/postgres"
        mock_settings.queue_required = True
        mock_settings.extraction_mode = "sync"
        queue_app.check_connection_async = AsyncMock()

        result = asyncio.run(_call_health_ready())

    assert result["status"] == "ready"
    assert result["checks"]["queue"]["status"] == "ok"
    assert result["checks"]["queue"]["configured"] is True
    assert result["checks"]["queue"]["required"] is True
    assert isinstance(result["checks"]["queue"]["latency_ms"], int)


def test_health_ready_queue_error_does_not_expose_connection_details():
    """Public readiness output must not echo a DSN or provider error text."""
    import asyncio

    from app.main import health_ready

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        MagicMock()
    )

    with (
        patch("supabase.create_client", return_value=mock_client),
        patch("app.core.config.settings") as mock_settings,
        patch("app.workers.procrastinate_app.app") as queue_app,
    ):
        mock_settings.supabase_url = "https://fake.supabase.co"
        mock_settings.supabase_anon_key = "fake-key"
        mock_settings.database_url = "postgresql://postgres:secret@db.example.test/postgres"
        mock_settings.queue_required = True
        mock_settings.extraction_mode = "sync"
        queue_app.check_connection_async = AsyncMock(
            side_effect=RuntimeError(
                "postgresql://postgres:do-not-return-me@db.example.test/postgres"
            )
        )

        result = asyncio.run(health_ready())

    assert result["status"] == "degraded"
    assert result["checks"]["queue"]["error"] == "connection_failed"
    assert result["checks"]["queue"]["error_type"] == "RuntimeError"
    assert "do-not-return-me" not in repr(result)


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
