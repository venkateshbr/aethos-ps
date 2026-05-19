"""Unit tests for RBAC role hierarchy.

These tests are pure-Python — no I/O, no DB, no HTTP.
"""

from __future__ import annotations

import pytest

from app.core.rbac import ROLE_HIERARCHY, UserRole

pytestmark = pytest.mark.unit


def test_owner_has_highest_rank() -> None:
    assert ROLE_HIERARCHY[UserRole.owner] > ROLE_HIERARCHY[UserRole.admin]


def test_viewer_has_lowest_rank() -> None:
    assert ROLE_HIERARCHY[UserRole.viewer] < ROLE_HIERARCHY[UserRole.member]


def test_all_roles_in_hierarchy() -> None:
    for role in UserRole:
        assert role in ROLE_HIERARCHY, f"{role!r} missing from ROLE_HIERARCHY"


def test_hierarchy_is_strictly_ordered() -> None:
    """No two roles share the same rank."""
    ranks = list(ROLE_HIERARCHY.values())
    assert len(ranks) == len(set(ranks)), "Duplicate ranks found in ROLE_HIERARCHY"


def test_role_enum_values_are_strings() -> None:
    """Roles must be str enum so they round-trip through JSON cleanly."""
    for role in UserRole:
        assert isinstance(role.value, str)


def test_admin_outranks_manager() -> None:
    assert ROLE_HIERARCHY[UserRole.admin] > ROLE_HIERARCHY[UserRole.manager]


def test_manager_outranks_member() -> None:
    assert ROLE_HIERARCHY[UserRole.manager] > ROLE_HIERARCHY[UserRole.member]
