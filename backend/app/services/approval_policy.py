"""Seeded enterprise approval policy matrix.

The first enterprise controls slice keeps policy in code so approval behavior is
deterministic and testable before a tenant-configurable policy UI exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.rbac import ROLE_HIERARCHY, UserRole

_OWNER_REVIEW_MONEY_OUT_THRESHOLD = Decimal("50000")
_MANUAL_JOURNAL_APPROVAL_THRESHOLD = Decimal("10000")
_ROLE_NAMES = {"manager", "admin", "owner"}
_MANUAL_JOURNAL_KINDS = {"draft_journal", "create_journal", "create_manual_journal"}


@dataclass(frozen=True)
class ApprovalPolicySettings:
    """Tenant-configurable approval requirements with safe launch defaults."""

    money_out_default_role: UserRole = UserRole.admin
    money_out_owner_threshold: Decimal = _OWNER_REVIEW_MONEY_OUT_THRESHOLD
    money_out_owner_role: UserRole = UserRole.owner
    accounting_role: UserRole = UserRole.admin
    manual_journal_approval_threshold: Decimal = _MANUAL_JOURNAL_APPROVAL_THRESHOLD
    money_in_role: UserRole = UserRole.manager
    draft_role: UserRole = UserRole.manager
    external_send_role: UserRole = UserRole.manager
    high_risk_role: UserRole = UserRole.admin
    policy_source: str = "system_default"

    def __post_init__(self) -> None:
        _assert_role_at_least(
            self.money_out_default_role,
            UserRole.admin,
            "money_out_default_role",
        )
        _assert_role_at_least(
            self.money_out_owner_role,
            UserRole.owner,
            "money_out_owner_role",
        )
        _assert_role_at_least(self.accounting_role, UserRole.admin, "accounting_role")
        _assert_role_at_least(self.money_in_role, UserRole.manager, "money_in_role")
        _assert_role_at_least(self.draft_role, UserRole.manager, "draft_role")
        _assert_role_at_least(
            self.external_send_role,
            UserRole.manager,
            "external_send_role",
        )
        _assert_role_at_least(self.high_risk_role, UserRole.admin, "high_risk_role")
        if self.money_out_owner_threshold < 0:
            raise ValueError("money_out_owner_threshold must be >= 0")
        if self.manual_journal_approval_threshold < 0:
            raise ValueError("manual_journal_approval_threshold must be >= 0")


def default_approval_policy_settings() -> ApprovalPolicySettings:
    return ApprovalPolicySettings()


def approval_policy_settings_from_mapping(
    row: dict[str, Any] | None,
    *,
    policy_source: str = "tenant_default",
) -> ApprovalPolicySettings:
    """Build validated settings from a DB/API row, falling back per field."""
    data = row or {}
    defaults = default_approval_policy_settings()
    return ApprovalPolicySettings(
        money_out_default_role=_role_or_default(
            data.get("money_out_default_role"),
            defaults.money_out_default_role,
        ),
        money_out_owner_threshold=_decimal_or_default(
            data.get("money_out_owner_threshold"),
            defaults.money_out_owner_threshold,
        ),
        money_out_owner_role=_role_or_default(
            data.get("money_out_owner_role"),
            defaults.money_out_owner_role,
        ),
        accounting_role=_role_or_default(data.get("accounting_role"), defaults.accounting_role),
        manual_journal_approval_threshold=_decimal_or_default(
            data.get("manual_journal_approval_threshold"),
            defaults.manual_journal_approval_threshold,
        ),
        money_in_role=_role_or_default(data.get("money_in_role"), defaults.money_in_role),
        draft_role=_role_or_default(data.get("draft_role"), defaults.draft_role),
        external_send_role=_role_or_default(
            data.get("external_send_role"),
            defaults.external_send_role,
        ),
        high_risk_role=_role_or_default(data.get("high_risk_role"), defaults.high_risk_role),
        policy_source=policy_source,
    )


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
    def decision_for_task(
        kind: str,
        payload: dict[str, Any],
        *,
        settings: ApprovalPolicySettings | None = None,
    ) -> ApprovalPolicyDecision:
        policy = settings or default_approval_policy_settings()
        risk_class = ApprovalPolicyMatrix._risk_class(kind, payload)
        amount = ApprovalPolicyMatrix._amount(payload)

        if risk_class == "write_money_out":
            if amount is not None and amount >= policy.money_out_owner_threshold:
                return ApprovalPolicyDecision(
                    required_role=policy.money_out_owner_role,
                    reason="money_out_above_owner_review_threshold",
                    risk_class=risk_class,
                    amount=amount,
                    threshold=policy.money_out_owner_threshold,
                )
            return ApprovalPolicyDecision(
                required_role=policy.money_out_default_role,
                reason=_role_review_reason("money_out", policy.money_out_default_role),
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class == "accounting":
            if (
                kind in _MANUAL_JOURNAL_KINDS
                and amount is not None
                and amount >= policy.manual_journal_approval_threshold
            ):
                return ApprovalPolicyDecision(
                    required_role=policy.accounting_role,
                    reason="manual_journal_above_approval_threshold",
                    risk_class=risk_class,
                    amount=amount,
                    threshold=policy.manual_journal_approval_threshold,
                )
            return ApprovalPolicyDecision(
                required_role=policy.accounting_role,
                reason=_role_review_reason("accounting", policy.accounting_role),
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class == "write_money_in":
            return ApprovalPolicyDecision(
                required_role=policy.money_in_role,
                reason=_role_review_reason("money_in", policy.money_in_role),
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class == "external_send":
            return ApprovalPolicyDecision(
                required_role=policy.external_send_role,
                reason="external_send_requires_review",
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class == "high_risk":
            return ApprovalPolicyDecision(
                required_role=policy.high_risk_role,
                reason=_role_review_reason("high_risk_ai_action", policy.high_risk_role),
                risk_class=risk_class,
                amount=amount,
            )

        if risk_class in {"draft", "write_low_risk"}:
            return ApprovalPolicyDecision(
                required_role=policy.draft_role,
                reason=_role_review_reason(risk_class, policy.draft_role),
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
        if kind in {
            "copilot_prepare_month_end_close",
            "copilot_prepare_year_end_close",
        } or tool_name in {
            "prepare_month_end_close",
            "prepare_year_end_close",
        }:
            return "accounting"
        if kind == "copilot_draft_invoice" or tool_name == "draft_invoice":
            return "write_money_in"
        if kind == "send_email":
            return "external_send"
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
                "total_debits",
            ):
                value = source.get(key)
                if value is None:
                    continue
                try:
                    return Decimal(str(value))
                except (InvalidOperation, ValueError):
                    continue
            lines = source.get("lines")
            if isinstance(lines, list):
                total_debits = Decimal("0")
                for line in lines:
                    if not isinstance(line, dict) or line.get("direction") != "DR":
                        continue
                    try:
                        total_debits += Decimal(str(line.get("amount") or "0"))
                    except (InvalidOperation, ValueError):
                        continue
                if total_debits > 0:
                    return total_debits
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


def _assert_role_at_least(actual: UserRole, minimum: UserRole, field: str) -> None:
    if ROLE_HIERARCHY[actual] < ROLE_HIERARCHY[minimum]:
        raise ValueError(f"{field} cannot be lower than {minimum.value}")


def _role_or_default(value: object, default: UserRole) -> UserRole:
    try:
        role = UserRole(str(value))
    except ValueError:
        return default
    if role.value not in _ROLE_NAMES:
        return default
    return role


def _decimal_or_default(value: object, default: Decimal) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _role_review_reason(prefix: str, role: UserRole) -> str:
    return f"{prefix}_requires_{role.value}_review"
