from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.seed_demo_v2 import _guard_reset_target, _link_employee_to_user

pytestmark = pytest.mark.unit


def test_demo_reset_rejects_nonmatching_tenant_name() -> None:
    with pytest.raises(ValueError, match="Refusing reset"):
        _guard_reset_target(
            actual_name="Sterling Bridge Advisory Group",
            required_name="Meridian Demo",
        )


def test_demo_reset_accepts_exact_tenant_name() -> None:
    _guard_reset_target(
        actual_name="Meridian Demo",
        required_name="Meridian Demo",
    )


def test_demo_owner_is_linked_to_seeded_employee() -> None:
    updates: list[dict[str, str]] = []

    class Query:
        def update(self, payload: dict[str, str]) -> Query:
            updates.append(payload)
            return self

        def eq(self, *_args: object) -> Query:
            return self

        def execute(self) -> SimpleNamespace:
            return SimpleNamespace(data=[])

    class Db:
        def table(self, name: str) -> Query:
            assert name == "employees"
            return Query()

    _link_employee_to_user(  # type: ignore[arg-type]
        Db(),
        employee_id="employee-1",
        user_id="owner-1",
    )

    assert updates == [{"user_id": "owner-1"}]
