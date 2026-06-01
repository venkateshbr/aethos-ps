"""The 'employee' role must sit below 'viewer' so portal logins are rejected
by every ERP require_role gate (issue #134, P0)."""

from __future__ import annotations

import pytest

from app.core.rbac import ROLE_HIERARCHY, UserRole

pytestmark = pytest.mark.unit


def test_employee_is_lowest_privilege() -> None:
    assert ROLE_HIERARCHY[UserRole.employee] == 0
    assert ROLE_HIERARCHY[UserRole.employee] < ROLE_HIERARCHY[UserRole.viewer]


def test_employee_below_every_other_role() -> None:
    others = [r for r in UserRole if r != UserRole.employee]
    assert all(ROLE_HIERARCHY[UserRole.employee] < ROLE_HIERARCHY[o] for o in others)
