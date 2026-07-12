"""Regression coverage for Aksha real-stack fixture cleanup."""

from __future__ import annotations

from typing import Any

import pytest

from tests.fixtures import scenarios

pytestmark = pytest.mark.unit


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _TenantQuery:
    def __init__(self, db: _TenantDb) -> None:
        self.db = db
        self.filters: list[tuple[str, Any]] = []
        self.payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> _TenantQuery:
        return self

    def update(self, payload: dict[str, Any]) -> _TenantQuery:
        self.payload = dict(payload)
        return self

    def delete(self) -> _TenantQuery:
        raise AssertionError("fixture cleanup must not hard-delete financial tenants")

    def eq(self, field: str, value: Any) -> _TenantQuery:
        self.filters.append((field, value))
        return self

    def limit(self, _value: int) -> _TenantQuery:
        return self

    def execute(self) -> _Result:
        matches = [
            row
            for row in self.db.rows
            if all(row.get(field) == value for field, value in self.filters)
        ]
        if self.payload is None:
            return _Result([dict(row) for row in matches])

        slug = next(
            (str(value) for field, value in self.filters if field == "slug"),
            "",
        )
        self.db.update_attempts.append(slug)
        if slug in self.db.raise_for_slugs:
            raise RuntimeError("sensitive backend detail")
        if slug not in self.db.noop_for_slugs:
            for row in matches:
                row.update(self.payload)
        return _Result([dict(row) for row in matches])


class _TenantDb:
    def __init__(
        self,
        rows: list[dict[str, Any]],
        *,
        raise_for_slugs: set[str] | None = None,
        noop_for_slugs: set[str] | None = None,
    ) -> None:
        self.rows = rows
        self.raise_for_slugs = raise_for_slugs or set()
        self.noop_for_slugs = noop_for_slugs or set()
        self.update_attempts: list[str] = []

    def table(self, name: str) -> _TenantQuery:
        assert name == "tenants"
        return _TenantQuery(self)


def _world() -> scenarios.SeedWorld:
    run_id = "aksha-test123"
    owner = scenarios.SeedUser(
        user_id="owner-1",
        email="owner@example.test",
        role="owner",
    )
    tenant_a = scenarios.SeedTenant(
        tenant_id="tenant-a",
        name="Acme",
        slug=f"acme-{run_id}",
        country="US",
        base_currency="USD",
        owner=owner,
    )
    tenant_b = scenarios.SeedTenant(
        tenant_id="tenant-b",
        name="Bravo",
        slug=f"bravo-{run_id}",
        country="GB",
        base_currency="GBP",
        owner=owner,
    )
    return scenarios.SeedWorld(run_id=run_id, tenant_a=tenant_a, tenant_b=tenant_b)


def _tenant_rows(world: scenarios.SeedWorld) -> list[dict[str, Any]]:
    return [
        {
            "id": world.tenant_a.tenant_id,
            "slug": world.tenant_a.slug,
            "status": "active",
            "stripe_subscription_status": "trialing",
        },
        {
            "id": world.tenant_b.tenant_id,
            "slug": world.tenant_b.slug,
            "status": "active",
            "stripe_subscription_status": "trialing",
        },
    ]


def test_sweep_clean_soft_deletes_and_verifies_both_tenants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _world()
    db = _TenantDb(_tenant_rows(world))
    monkeypatch.setattr(scenarios, "make_service_client", lambda: db)

    scenarios.sweep_clean(world)

    assert db.update_attempts == [world.tenant_a.slug, world.tenant_b.slug]
    assert [row["status"] for row in db.rows] == ["deleted", "deleted"]
    assert [row["stripe_subscription_status"] for row in db.rows] == [
        "canceled",
        "canceled",
    ]


@pytest.mark.parametrize("failure_mode", ["raises", "silent_noop"])
def test_sweep_clean_attempts_both_and_surfaces_safe_aggregate_failure(
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    world = _world()
    failed_slug = world.tenant_a.slug
    db = _TenantDb(
        _tenant_rows(world),
        raise_for_slugs={failed_slug} if failure_mode == "raises" else set(),
        noop_for_slugs={failed_slug} if failure_mode == "silent_noop" else set(),
    )
    monkeypatch.setattr(scenarios, "make_service_client", lambda: db)

    with pytest.raises(RuntimeError, match="Aksha fixture cleanup failed") as exc_info:
        scenarios.sweep_clean(world)

    assert db.update_attempts == [world.tenant_a.slug, world.tenant_b.slug]
    assert world.tenant_a.slug in str(exc_info.value)
    assert "sensitive backend detail" not in str(exc_info.value)
    assert db.rows[1]["status"] == "deleted"
