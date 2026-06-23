"""Deterministic payment-run priority scoring for AP batches."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.money import serialise_money

_HIGH_VALUE_REVIEW_THRESHOLD = Decimal("50000")


@dataclass(frozen=True)
class PaymentOptimization:
    ranked_bills: list[dict[str, Any]]
    summary: dict[str, Any]
    risk_review_required: bool


def build_payment_optimization(
    bills: list[dict[str, Any]],
    *,
    pay_date: date,
) -> PaymentOptimization:
    """Rank bills by due-date urgency and flag manual-review conditions."""
    scored: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    review_flags: list[dict[str, Any]] = []

    total = Decimal("0")
    currencies = sorted({str(bill.get("currency") or "USD") for bill in bills})
    for bill in bills:
        amount = Decimal(str(bill.get("total") or "0"))
        total += amount
        due_date = _parse_date(bill.get("due_date"))
        score, reasons, days_to_due = _score_due_date(due_date, pay_date)
        if amount > _HIGH_VALUE_REVIEW_THRESHOLD:
            score += 20
            reasons.append("high_value")
            review_flags.append(
                {
                    "bill_id": str(bill["id"]),
                    "bill_number": bill.get("bill_number") or "",
                    "reason": "high value payment requires manual review",
                    "amount": serialise_money(amount),
                }
            )
        if due_date is None:
            review_flags.append(
                {
                    "bill_id": str(bill["id"]),
                    "bill_number": bill.get("bill_number") or "",
                    "reason": "missing due date",
                }
            )

        driver = {
            "bill_id": str(bill["id"]),
            "bill_number": bill.get("bill_number") or "",
            "priority_score": score,
            "days_to_due": days_to_due,
            "reasons": reasons,
            "amount": serialise_money(amount),
        }
        scored.append((score, bill, driver))

    scored.sort(
        key=lambda item: (
            -item[0],
            _parse_date(item[1].get("due_date")) or date.max,
            str(item[1].get("bill_number") or item[1].get("id")),
        )
    )
    ranked_bills = [bill for _, bill, _driver in scored]
    drivers = [driver for _score, _bill, driver in scored]

    summary: dict[str, Any] = {
        "pay_date": pay_date.isoformat(),
        "bill_count": len(bills),
        "currency": currencies[0] if currencies else "USD",
        "currencies": currencies,
        "total": serialise_money(total),
        "ranked_bill_ids": [str(bill["id"]) for bill in ranked_bills],
        "drivers": drivers,
        "manual_review_flags": review_flags,
    }
    return PaymentOptimization(
        ranked_bills=ranked_bills,
        summary=summary,
        risk_review_required=bool(review_flags),
    )


def _score_due_date(due_date: date | None, pay_date: date) -> tuple[int, list[str], int | None]:
    if due_date is None:
        return 10, ["missing_due_date"], None
    days_to_due = (due_date - pay_date).days
    if days_to_due < 0:
        return 120 + min(abs(days_to_due), 30), ["overdue"], days_to_due
    if days_to_due <= 3:
        return 90, ["due_within_3_days"], days_to_due
    if days_to_due <= 7:
        return 70, ["due_within_7_days"], days_to_due
    if days_to_due <= 14:
        return 40, ["due_within_14_days"], days_to_due
    return 15, ["not_urgent"], days_to_due


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
