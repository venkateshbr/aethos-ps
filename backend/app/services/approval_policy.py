"""Seeded enterprise approval policy matrix.

The first enterprise controls slice keeps policy in code so approval behavior is
deterministic and testable before a tenant-configurable policy UI exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.rbac import UserRole

_OWNER_REVIEW_MONEY_OUT_THRESHOLD = Decimal("50000")


@dataclass(frozen=True)
class ApprovalPolicyDecision:
    required_role: UserRole
    reason: str
    risk_class: str
    amount: Decimal | None = None
    threshold: Decimal | None = None

    def to_metadata(self) -> dict[str, str]:
        result = {
            "required_role": self.required_role.value,
            "reason": self.reason,
            "risk_class": self.risk_class,
        }
        if self.amount is not None:
            result["amount"] = str(self.amount)
        if self.threshold is not None:
            result["threshold"] = str(self.threshold)
        return result


class ApprovalPolicyMatrix:
    """Resolve approval requirements for HITL tasks."""

    @staticmethod
    def decision_for_task(kind: str, payload: dict[str, Any]) -> ApprovalPolicyDecision:
        risk_class = ApprovalPolicyMatrix._risk_class(kind, payload)
        amount = ApprovalPolicyMatrix._amount(payload)

        if risk_class == "write_money_out":
            if amount is not None and amount >= _OWNER_REVIEW_MONEY_OUT_THRESHOLD:
                return ApprovalPolicyDecision(
                    required_role=UserRole.owner,
                    reason="money_out_above_owner_review_threshold",
                    risk_class=risk_class,
                    amount=amount,
                    threshold=_OWNER_REVIEW_MONEY_OUT_THRESHOLD,
                )
            return ApprovalPolicyDecision(
                required_role=UserRole.admin,
                reason="money_out_requires_admin_review",
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class == "accounting":
            return ApprovalPolicyDecision(
                required_role=UserRole.admin,
                reason="accounting_requires_admin_review",
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class == "write_money_in":
            return ApprovalPolicyDecision(
                required_role=UserRole.manager,
                reason="money_in_requires_manager_review",
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class in {"draft", "write_low_risk"}:
            return ApprovalPolicyDecision(
                required_role=UserRole.manager,
                reason=f"{risk_class}_requires_manager_review",
                risk_class=risk_class,
                amount=amount,
            )

        return ApprovalPolicyDecision(
            required_role=UserRole.manager,
            reason="hitl_task_requires_manager_review",
            risk_class=risk_class,
            amount=amount,
        )

    @staticmethod
    def _risk_class(kind: str, payload: dict[str, Any]) -> str:
        explicit = str(payload.get("risk_class") or "").strip()
        if explicit:
            return explicit

        tool_name = str(
            payload.get("tool_name")
            or payload.get("suggested_tool")
            or payload.get("dispatch_tool")
            or ""
        ).strip()

        if kind == "create_bill_payment_batch" or tool_name == "propose_bill_payment_batch":
            return "write_money_out"
        if kind in {"draft_journal", "create_journal", "create_manual_journal"}:
            return "accounting"
        if kind == "copilot_prepare_month_end_close" or tool_name == "prepare_month_end_close":
            return "accounting"
        if kind == "copilot_draft_invoice" or tool_name == "draft_invoice":
            return "write_money_in"
        if kind == "send_email":
            return "write_low_risk"
        return "draft"

    @staticmethod
    def _amount(payload: dict[str, Any]) -> Decimal | None:
        for source in ApprovalPolicyMatrix._payload_sources(payload):
            for key in (
                "total_amount",
                "total",
                "amount",
                "subtotal",
                "net_income",
            ):
                value = source.get(key)
                if value is None:
                    continue
                try:
                    return Decimal(str(value))
                except (InvalidOperation, ValueError):
                    continue
        return None

    @staticmethod
    def _payload_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
        sources = [payload]
        preview = payload.get("preview")
        if isinstance(preview, dict):
            sources.append(preview)
        source_plan_action = payload.get("source_plan_action")
        if isinstance(source_plan_action, dict):
            sources.append(source_plan_action)
        return sources
