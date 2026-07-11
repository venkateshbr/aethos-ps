"""Real-stack regression for Finance Ops AR child-task approval."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from tests.fixtures.scenarios import SeedWorld, make_service_client

pytestmark = [
    pytest.mark.api,
    pytest.mark.flow_hitl,
    pytest.mark.flow_copilot,
    pytest.mark.requires_supabase,
]


def test_owner_approves_ar_action_item_and_stages_collections_review(
    client_a: httpx.Client,
    world: SeedWorld,
) -> None:
    """Human approval resolves the plan item and stages, but does not send, email."""
    db = make_service_client()
    tenant = world.tenant_a
    marker = uuid.uuid4().hex[:10]
    today = date.today()
    invoice = (
        db.table("invoices")
        .insert(
            {
                "tenant_id": tenant.tenant_id,
                "engagement_id": tenant.engagement_ids[0],
                "client_id": tenant.client_ids[0],
                "invoice_number": f"INV-AR-APPROVAL-{marker}",
                "currency": tenant.base_currency,
                "subtotal": "1250.00",
                "tax_total": "0.00",
                "total": "1250.00",
                "status": "sent",
                "issue_date": (today - timedelta(days=75)).isoformat(),
                "due_date": (today - timedelta(days=45)).isoformat(),
                "sent_at": datetime.now(UTC).isoformat(),
                "notes": f"finance-ops-ar-approval-{marker}",
            }
        )
        .execute()
        .data[0]
    )
    action_item_id = f"finance-ops-ar-{marker}"
    payload = {
        "finance_ops_action_item": True,
        "parent_plan_id": f"finance-ops-plan-{marker}",
        "period": today.strftime("%Y-%m"),
        "action_item_id": action_item_id,
        "domain": "ar",
        "recommendation": "Draft a reminder for the overdue test invoice.",
        "suggested_agent": "collections_agent",
        "suggested_tool": "send_email",
        "risk_class": "write_money_in",
        "requires_inbox_approval": True,
        "rationale": "The disposable test invoice is overdue.",
        "review_path": "/app/inbox",
        "dispatch_tool": "draft_collection_reminders",
        "dispatch_input": {
            "minimum_days_overdue": 1,
            "limit": 10,
            "tone": "auto",
        },
        "requested_by_user_id": tenant.owner.user_id,
    }
    parent_suggestion = (
        db.table("agent_suggestions")
        .insert(
            {
                "tenant_id": tenant.tenant_id,
                "agent_name": "collections_agent",
                "action_type": "finance_ops_action_item",
                "input_snapshot": {
                    "parent_plan_id": payload["parent_plan_id"],
                    "period": payload["period"],
                    "source_tool": "create_finance_ops_action_plan",
                },
                "output_snapshot": payload,
                "confidence": "0.00",
                "status": "pending",
                "hitl_required": True,
            }
        )
        .execute()
        .data[0]
    )
    parent_task = (
        db.table("hitl_tasks")
        .insert(
            {
                "tenant_id": tenant.tenant_id,
                "agent_suggestion_id": parent_suggestion["id"],
                "kind": "finance_ops_action_item",
                "priority": "high",
                "title": f"Review AR action item {marker}",
                "description": "Approve to stage a separately gated collections email.",
                "payload": payload,
                "status": "open",
            }
        )
        .execute()
        .data[0]
    )

    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    response = client_a.post(
        f"/api/v1/inbox/tasks/{parent_task['id']}/approve",
        timeout=25.0,
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200, response.text
    assert elapsed < 30
    approval = response.json()
    assert approval["materialised"] is True
    assert approval["entity_type"] == "finance_ops_action_item"
    assert approval["entity_id"] == action_item_id
    assert approval["materialisation"]["child_review_tasks_created"] >= 1
    assert approval["materialisation"]["dispatched_tool"] == (
        "draft_collection_reminders"
    )

    resolved_task = (
        db.table("hitl_tasks")
        .select("status")
        .eq("id", parent_task["id"])
        .eq("tenant_id", tenant.tenant_id)
        .single()
        .execute()
        .data
    )
    resolved_suggestion = (
        db.table("agent_suggestions")
        .select("status")
        .eq("id", parent_suggestion["id"])
        .eq("tenant_id", tenant.tenant_id)
        .single()
        .execute()
        .data
    )
    assert resolved_task["status"] == "done"
    assert resolved_suggestion["status"] == "approved"

    send_suggestions = (
        db.table("agent_suggestions")
        .select("id,status,agent_name,action_type,related_entity_id")
        .eq("tenant_id", tenant.tenant_id)
        .eq("agent_name", "collections_agent")
        .eq("action_type", "send_email")
        .eq("related_entity_id", invoice["id"])
        .gte("created_at", started_at)
        .execute()
        .data
        or []
    )
    assert len(send_suggestions) == 1
    assert send_suggestions[0]["status"] == "pending"
    send_tasks = (
        db.table("hitl_tasks")
        .select("id,status,kind,agent_suggestion_id")
        .eq("tenant_id", tenant.tenant_id)
        .eq("agent_suggestion_id", send_suggestions[0]["id"])
        .execute()
        .data
        or []
    )
    assert len(send_tasks) == 1
    assert send_tasks[0]["kind"] == "send_email"
    assert send_tasks[0]["status"] == "open"

    collection_runs = (
        db.table("agent_runs")
        .select("id,status,agent_name")
        .eq("tenant_id", tenant.tenant_id)
        .eq("agent_name", "collections_agent")
        .gte("created_at", started_at)
        .execute()
        .data
        or []
    )
    assert len(collection_runs) == 1
    assert collection_runs[0]["status"] == "succeeded"
    tool_rows = (
        db.table("agent_tool_invocations")
        .select("tool_name,status")
        .eq("tenant_id", tenant.tenant_id)
        .eq("agent_run_id", collection_runs[0]["id"])
        .order("created_at")
        .execute()
        .data
        or []
    )
    assert [(row["tool_name"], row["status"]) for row in tool_rows] == [
        ("find_overdue_invoices", "succeeded"),
        ("draft_collection_email", "succeeded"),
        ("send_email", "skipped"),
    ]

    decision_events = (
        db.table("financial_events")
        .select("event_type,action,entity_type,entity_id")
        .eq("tenant_id", tenant.tenant_id)
        .eq("entity_type", "hitl_task")
        .eq("entity_id", parent_task["id"])
        .gte("created_at", started_at)
        .execute()
        .data
        or []
    )
    assert [(row["event_type"], row["action"]) for row in decision_events] == [
        ("hitl_task.approved", "approved")
    ]
