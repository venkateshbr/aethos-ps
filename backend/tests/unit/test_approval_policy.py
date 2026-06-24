from __future__ import annotations

import pytest

from app.core.rbac import UserRole
from app.services.approval_policy import ApprovalPolicyMatrix, ApprovalPolicySettings


def test_large_money_out_task_requires_owner() -> None:
    decision = ApprovalPolicyMatrix.decision_for_task(
        "create_bill_payment_batch",
        {"risk_class": "write_money_out", "total_amount": "75000.00"},
    )

    assert decision.required_role == UserRole.owner
    assert decision.reason == "money_out_above_owner_review_threshold"
    assert decision.to_metadata()["threshold"] == "50000"


def test_normal_money_out_task_requires_admin() -> None:
    decision = ApprovalPolicyMatrix.decision_for_task(
        "create_bill_payment_batch",
        {"risk_class": "write_money_out", "total_amount": "1250.00"},
    )

    assert decision.required_role == UserRole.admin
    assert decision.reason == "money_out_requires_admin_review"


def test_accounting_task_requires_admin() -> None:
    decision = ApprovalPolicyMatrix.decision_for_task(
        "copilot_prepare_month_end_close",
        {"period": "2026-06"},
    )

    assert decision.required_role == UserRole.admin
    assert decision.risk_class == "accounting"


def test_invoice_draft_requires_manager() -> None:
    decision = ApprovalPolicyMatrix.decision_for_task(
        "copilot_draft_invoice",
        {"preview": {"total": "5000.00"}},
    )

    assert decision.required_role == UserRole.manager
    assert decision.risk_class == "write_money_in"


def test_tenant_policy_can_raise_money_out_default_to_owner() -> None:
    decision = ApprovalPolicyMatrix.decision_for_task(
        "create_bill_payment_batch",
        {"risk_class": "write_money_out", "total_amount": "1250.00"},
        settings=ApprovalPolicySettings(money_out_default_role=UserRole.owner),
    )

    assert decision.required_role == UserRole.owner
    assert decision.reason == "money_out_requires_owner_review"


def test_tenant_policy_can_raise_external_send_to_admin() -> None:
    decision = ApprovalPolicyMatrix.decision_for_task(
        "send_email",
        {"subject": "Reminder"},
        settings=ApprovalPolicySettings(external_send_role=UserRole.admin),
    )

    assert decision.required_role == UserRole.admin
    assert decision.risk_class == "external_send"


def test_tenant_policy_cannot_lower_money_out_below_admin() -> None:
    with pytest.raises(ValueError, match="money_out_default_role"):
        ApprovalPolicySettings(money_out_default_role=UserRole.manager)
