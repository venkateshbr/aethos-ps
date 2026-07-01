"""Hermes MCP bridge for Aethos Atlas tools.

Hermes sees MCP tools. Each tool delegates to the private Aethos Atlas broker,
which verifies a short-lived tenant/user context reference and then runs the
allowlisted Aethos API/service path.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("aethos")

_DEFAULT_BASE_URL = "http://api:8080"
_EXECUTE_PATH = "/api/v1/atlas-tools/execute"


@mcp.tool()
async def aethos_documents_intake_read_pack(
    context_ref: str,
    document_id: str | None = None,
    filename: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Read uploaded document metadata, extraction output, and linked Inbox tasks."""
    arguments = _optional_args(
        {
            "document_id": document_id,
            "filename": filename,
            "limit": limit,
        }
    )
    return await _execute("aethos.documents.intake_read_pack", context_ref, arguments)


@mcp.tool()
async def aethos_documents_audit_read_pack(
    context_ref: str,
    limit: int = 25,
) -> dict[str, Any]:
    """Read source-document lineage for engagements, bills, journals, and Inbox."""
    return await _execute(
        "aethos.documents.audit_read_pack",
        context_ref,
        {"limit": limit},
    )


@mcp.tool()
async def aethos_cosec_reminders_read_pack(
    context_ref: str,
    client_name: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Read COSEC filing reminders, evidence gaps, billing impact, and approval state."""
    arguments = _optional_args(
        {
            "client_name": client_name,
            "limit": limit,
        }
    )
    return await _execute("aethos.cosec.reminders_read_pack", context_ref, arguments)


@mcp.tool()
async def aethos_engagements_list(
    context_ref: str,
    status: str = "all",
    client_id: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """List tenant-scoped Aethos engagements for Atlas finance analysis."""
    arguments: dict[str, Any] = {
        "status": status,
        "limit": limit,
        "offset": offset,
    }
    if client_id:
        arguments["client_id"] = client_id
    return await _execute("aethos.engagements.list", context_ref, arguments)


@mcp.tool()
async def aethos_engagements_structure_read_pack(
    context_ref: str,
    client_name: str | None = None,
    engagement_name: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Read engagement, project/workstream, billing-term, rate-card, and setup state."""
    arguments = _optional_args(
        {
            "client_name": client_name,
            "engagement_name": engagement_name,
            "limit": limit,
        }
    )
    return await _execute("aethos.engagements.structure_read_pack", context_ref, arguments)


@mcp.tool()
async def aethos_engagements_create_review(
    context_ref: str,
    client_name: str,
    engagement_name: str,
    billing_arrangement: str | None = None,
    currency: str = "USD",
    total_value: str | None = None,
    fixed_fee_amount: str | None = None,
    cap_amount: str | None = None,
    retainer_monthly_amount: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    service_line: str | None = None,
    description: str | None = None,
    first_project_name: str | None = None,
    first_project_description: str | None = None,
) -> dict[str, Any]:
    """Prepare an engagement draft and route it to Aethos Inbox approval."""
    arguments = _optional_args(
        {
            "client_name": client_name,
            "engagement_name": engagement_name,
            "billing_arrangement": billing_arrangement,
            "currency": currency,
            "total_value": total_value,
            "fixed_fee_amount": fixed_fee_amount,
            "cap_amount": cap_amount,
            "retainer_monthly_amount": retainer_monthly_amount,
            "start_date": start_date,
            "end_date": end_date,
            "service_line": service_line,
            "description": description,
            "first_project_name": first_project_name,
            "first_project_description": first_project_description,
        }
    )
    return await _execute("aethos.engagements.create_review", context_ref, arguments)


@mcp.tool()
async def aethos_finance_ar_aging(context_ref: str) -> dict[str, Any]:
    """Return tenant-scoped Aethos AR aging buckets."""
    return await _execute("aethos.finance.ar_aging", context_ref, {})


@mcp.tool()
async def aethos_finance_ap_aging(context_ref: str) -> dict[str, Any]:
    """Return tenant-scoped Aethos AP aging buckets."""
    return await _execute("aethos.finance.ap_aging", context_ref, {})


@mcp.tool()
async def aethos_finance_wip(
    context_ref: str,
    engagement_id: str | None = None,
) -> dict[str, Any]:
    """Return tenant-scoped Aethos work-in-progress details."""
    arguments: dict[str, Any] = {}
    if engagement_id:
        arguments["engagement_id"] = engagement_id
    return await _execute("aethos.finance.wip", context_ref, arguments)


@mcp.tool()
async def aethos_delivery_resource_read_pack(
    context_ref: str,
    employee_name: str | None = None,
    project_name: str | None = None,
    client_name: str | None = None,
    period: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Read employee delivery, time approval, expense, utilization, and WIP state."""
    arguments = _optional_args(
        {
            "employee_name": employee_name,
            "project_name": project_name,
            "client_name": client_name,
            "period": period,
            "limit": limit,
        }
    )
    return await _execute("aethos.delivery.resource_read_pack", context_ref, arguments)


@mcp.tool()
async def aethos_time_log_entry(
    context_ref: str,
    project_name: str,
    hours: str,
    date: str | None = None,
    description: str | None = None,
    billable: bool = True,
) -> dict[str, Any]:
    """Log a time entry through Aethos tool policy and approval controls."""
    arguments = _optional_args(
        {
            "project_name": project_name,
            "hours": hours,
            "date": date,
            "description": description,
            "billable": billable,
        }
    )
    return await _execute("aethos.time.log_entry", context_ref, arguments)


@mcp.tool()
async def aethos_finance_ops_snapshot(
    context_ref: str,
    engagement_limit: int = 10,
) -> dict[str, Any]:
    """Return a read-only finance operations snapshot from Aethos."""
    return await _execute(
        "aethos.finance_ops.snapshot",
        context_ref,
        {"engagement_limit": engagement_limit},
    )


@mcp.tool()
async def aethos_finance_ops_control_room(
    context_ref: str,
    workflow_limit: int = 10,
    task_limit: int = 10,
) -> dict[str, Any]:
    """Return scheduled Finance Ops Manager status, pending work, and health."""
    return await _execute(
        "aethos.finance_ops.control_room",
        context_ref,
        {"workflow_limit": workflow_limit, "task_limit": task_limit},
    )


@mcp.tool()
async def aethos_operational_health_read_pack(context_ref: str) -> dict[str, Any]:
    """Read safe tenant/platform health without exposing logs, traces, or secrets."""
    return await _execute("aethos.operational_health.read_pack", context_ref, {})


@mcp.tool()
async def aethos_configuration_telemetry_read_pack(
    context_ref: str,
    inbox_limit: int = 10,
) -> dict[str, Any]:
    """Read approval controls, Finance Ops schedule, Atlas runtime, Langfuse, and alerts."""
    return await _execute(
        "aethos.configuration_telemetry.read_pack",
        context_ref,
        {"inbox_limit": inbox_limit},
    )


@mcp.tool()
async def aethos_approval_controls_read_pack(
    context_ref: str,
    inbox_limit: int = 10,
) -> dict[str, Any]:
    """Return role-aware approval policy, persona, and Inbox risk summaries."""
    return await _execute(
        "aethos.approval_controls.read_pack",
        context_ref,
        {"inbox_limit": inbox_limit},
    )


@mcp.tool()
async def aethos_finance_ops_create_action_plan(
    context_ref: str,
    period: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Create a reviewed Aethos finance ops action plan in Inbox."""
    arguments: dict[str, Any] = {"limit": limit}
    if period:
        arguments["period"] = period
    return await _execute(
        "aethos.finance_ops.create_action_plan",
        context_ref,
        arguments,
    )


@mcp.tool()
async def aethos_o2c_draft_invoice(
    context_ref: str,
    engagement_name: str | None = None,
    engagement_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Draft a customer invoice through Aethos Inbox review."""
    arguments = _optional_args(
        {
            "engagement_name": engagement_name,
            "engagement_id": engagement_id,
            "period_start": period_start,
            "period_end": period_end,
        }
    )
    return await _execute("aethos.o2c.draft_invoice", context_ref, arguments)


@mcp.tool()
async def aethos_o2c_collections_read_pack(
    context_ref: str,
    invoice_id: str | None = None,
    invoice_number: str | None = None,
    client_id: str | None = None,
    client_name: str | None = None,
    status: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Return read-only customer collections and invoice drilldown state."""
    arguments = _optional_args(
        {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "client_id": client_id,
            "client_name": client_name,
            "status": status,
            "limit": limit,
        }
    )
    return await _execute("aethos.o2c.collections_read_pack", context_ref, arguments)


@mcp.tool()
async def aethos_collections_draft_reminders(
    context_ref: str,
    minimum_days_overdue: int = 1,
    tone: str = "auto",
    client_name: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Draft overdue-invoice reminders through Aethos Inbox review."""
    arguments = _optional_args(
        {
            "minimum_days_overdue": minimum_days_overdue,
            "tone": tone,
            "client_name": client_name,
            "limit": limit,
        }
    )
    return await _execute("aethos.collections.draft_reminders", context_ref, arguments)


@mcp.tool()
async def aethos_p2p_propose_bill_payment_batch(
    context_ref: str,
    due_within_days: int = 7,
    bank_account_label: str | None = None,
) -> dict[str, Any]:
    """Prepare a controlled vendor bill-payment proposal for Inbox review."""
    arguments = _optional_args(
        {
            "due_within_days": due_within_days,
            "bank_account_label": bank_account_label,
        }
    )
    return await _execute(
        "aethos.p2p.propose_bill_payment_batch",
        context_ref,
        arguments,
    )


@mcp.tool()
async def aethos_p2p_payment_risk_read_pack(
    context_ref: str,
    bill_id: str | None = None,
    bill_number: str | None = None,
    vendor_id: str | None = None,
    vendor_name: str | None = None,
    status: str | None = None,
    due_within_days: int = 10,
    limit: int = 25,
) -> dict[str, Any]:
    """Return read-only vendor bill evidence and payment-risk state."""
    arguments = _optional_args(
        {
            "bill_id": bill_id,
            "bill_number": bill_number,
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "status": status,
            "due_within_days": due_within_days,
            "limit": limit,
        }
    )
    return await _execute("aethos.p2p.payment_risk_read_pack", context_ref, arguments)


@mcp.tool()
async def aethos_r2r_prepare_month_end_close(
    context_ref: str,
    period: str,
) -> dict[str, Any]:
    """Prepare month-end close through Aethos Inbox review."""
    return await _execute(
        "aethos.r2r.prepare_month_end_close",
        context_ref,
        {"period": period},
    )


@mcp.tool()
async def aethos_r2r_prepare_year_end_close(
    context_ref: str,
    year: int,
) -> dict[str, Any]:
    """Prepare year-end close through Aethos Inbox review."""
    return await _execute(
        "aethos.r2r.prepare_year_end_close",
        context_ref,
        {"year": year},
    )


@mcp.tool()
async def aethos_r2r_generate_financial_statement_package(
    context_ref: str,
    period_start: str,
    period_end: str | None = None,
    comparison_period_start: str | None = None,
    comparison_period_end: str | None = None,
) -> dict[str, Any]:
    """Generate a read-only Aethos financial statement package."""
    arguments = _optional_args(
        {
            "period_start": period_start,
            "period_end": period_end,
            "comparison_period_start": comparison_period_start,
            "comparison_period_end": comparison_period_end,
        }
    )
    return await _execute(
        "aethos.r2r.generate_financial_statement_package",
        context_ref,
        arguments,
    )


@mcp.tool()
async def aethos_r2r_management_pack_read_pack(
    context_ref: str,
    period: str,
    comparison_period: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Read the Aethos R2R management pack, variances, and close blockers."""
    arguments = _optional_args(
        {
            "period": period,
            "comparison_period": comparison_period,
            "limit": limit,
        }
    )
    return await _execute(
        "aethos.r2r.management_pack_read_pack",
        context_ref,
        arguments,
    )


@mcp.tool()
async def aethos_r2r_prepare_manual_journal_review(
    context_ref: str,
    amount: str,
    currency: str,
    period: str,
    base_currency: str | None = None,
    description: str | None = None,
    client_name: str | None = None,
    business_reason: str | None = None,
    supporting_evidence: str | None = None,
    entry_date: str | None = None,
    debit_account_code: str = "1100",
    credit_account_code: str = "4000",
) -> dict[str, Any]:
    """Prepare an AI-drafted manual journal review packet and route it to Inbox."""
    arguments = _optional_args(
        {
            "amount": amount,
            "currency": currency,
            "period": period,
            "base_currency": base_currency,
            "description": description,
            "client_name": client_name,
            "business_reason": business_reason,
            "supporting_evidence": supporting_evidence,
            "entry_date": entry_date,
            "debit_account_code": debit_account_code,
            "credit_account_code": credit_account_code,
        }
    )
    return await _execute(
        "aethos.r2r.prepare_manual_journal_review",
        context_ref,
        arguments,
    )


@mcp.tool()
async def aethos_r2r_accounting_decision_trail_read_pack(
    context_ref: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Read Inbox decision trails, journal context, and segregation controls."""
    return await _execute(
        "aethos.r2r.accounting_decision_trail_read_pack",
        context_ref,
        {"limit": limit},
    )


async def _execute(
    tool_name: str,
    context_ref: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    token = os.getenv("AETHOS_HERMES_TOOL_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Aethos tool broker token is not configured")

    base_url = os.getenv("AETHOS_INTERNAL_API_URL", _DEFAULT_BASE_URL).rstrip("/")
    timeout = float(os.getenv("AETHOS_TOOL_TIMEOUT_SECONDS", "30"))
    payload = {
        "context_ref": context_ref,
        "tool_name": tool_name,
        "arguments": arguments,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.post(_EXECUTE_PATH, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Aethos tool broker rejected {tool_name} with HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Aethos tool broker request failed for {tool_name}") from exc

    result = data.get("result")
    return result if isinstance(result, dict) else {"result": result}


def _optional_args(arguments: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in arguments.items() if value is not None}


if __name__ == "__main__":
    mcp.run()
