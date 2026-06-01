"""Unit tests for employee + assignment Pydantic models (issue #134)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.assignments import AssignmentResponse
from app.models.employees import EmployeeCreate, EmployeeResponse, EmploymentType

pytestmark = pytest.mark.unit


def test_employee_create_requires_valid_email() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate(first_name="A", last_name="B", email="not-an-email")


def test_employee_create_rejects_negative_rate() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate(
            first_name="A", last_name="B", email="a@b.com",
            default_bill_rate=Decimal("-1"),
        )


def test_employee_create_defaults_full_time() -> None:
    e = EmployeeCreate(first_name="A", last_name="B", email="a@b.com")
    assert e.employment_type == EmploymentType.full_time
    assert e.skills == []


def test_employee_response_serialises_rates_as_strings_and_has_login() -> None:
    r = EmployeeResponse(
        id="e1", tenant_id="t1", first_name="A", last_name="B", email="a@b.com",
        employment_type="contractor", default_bill_rate=Decimal("150.00"),
        cost_rate=None, user_id="u1", status="active", created_at="2026-01-01",
    )
    assert r.default_bill_rate == "150.00"
    assert r.cost_rate is None
    assert r.has_login is True


def test_employee_response_has_login_false_without_user() -> None:
    r = EmployeeResponse(
        id="e1", tenant_id="t1", first_name="A", last_name="B", email="a@b.com",
        employment_type="full_time", status="active", created_at="2026-01-01",
    )
    assert r.has_login is False


def test_assignment_response_serialises_override_rate() -> None:
    a = AssignmentResponse(
        id="a1", tenant_id="t1", project_id="p1", employee_id="e1",
        role="Lead", override_rate=Decimal("200.00"), created_at="2026-01-01",
    )
    assert a.override_rate == "200.00"
