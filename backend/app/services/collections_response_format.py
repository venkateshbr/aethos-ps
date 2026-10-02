"""User-facing response formatting for collections workflows."""

from __future__ import annotations


def format_collections_reminder_result(result: dict[str, object]) -> str:
    """Render customer-safe collections reminder output for Nous responses."""

    drafts = result.get("drafts") if isinstance(result, dict) else []
    skipped = result.get("skipped") if isinstance(result, dict) else []
    draft_rows = drafts if isinstance(drafts, list) else []
    skipped_rows = skipped if isinstance(skipped, list) else []
    raw_created_count = result.get("created_review_tasks")
    created_count = (
        raw_created_count
        if isinstance(raw_created_count, int)
        else len(draft_rows)
    )

    lines: list[str]
    if created_count > 0:
        lines = [
            (
                f"Drafted {created_count} customer-specific collections reminder "
                "email(s) and routed every email to Inbox approval before sending."
            )
        ]
        for row in draft_rows[:5]:
            if not isinstance(row, dict):
                continue
            client_name = str(row.get("client_name") or "customer").strip()
            invoice_number = str(row.get("invoice_number") or "invoice").strip()
            days_overdue = row.get("days_overdue")
            overdue_label = (
                f"{days_overdue} days overdue"
                if isinstance(days_overdue, int) and days_overdue > 0
                else "overdue"
            )
            lines.append(
                f"- Customer: {client_name}; invoice {invoice_number}; {overdue_label}; Inbox approval required before send."
            )
    else:
        lines = [
            (
                "No customer-specific collections reminder drafts were created because "
                "eligible overdue customer invoices are blocked or in cooldown. "
                "No email was sent; any future reminder must still route to Inbox approval before sending."
            )
        ]
        for row in skipped_rows[:5]:
            if not isinstance(row, dict):
                continue
            client_name = str(row.get("client_name") or "customer").strip()
            invoice_number = str(row.get("invoice_number") or "invoice").strip()
            reason = str(row.get("reason") or "blocked").replace("_", " ")
            days_overdue = row.get("days_overdue")
            overdue_label = (
                f"{days_overdue} days overdue"
                if isinstance(days_overdue, int) and days_overdue > 0
                else "overdue"
            )
            lines.append(
                f"- Customer: {client_name}; invoice {invoice_number}; {overdue_label}; blocker: {reason}."
            )
    return "\n".join(lines)
