"""Tenant-scoped read packs used by the Atlas tool broker."""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.config import settings
from app.domain.money import serialise_money
from app.services.operational_telemetry import TenantHealthService
from supabase import Client


class AtlasReadPackService:
    """Build compact business-context payloads for Hermes-powered Atlas."""

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def document_intake_read_pack(
        self,
        *,
        document_id: str | None = None,
        filename: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        documents = self._documents(document_id=document_id, filename=filename, limit=limit)
        document_ids = [row["id"] for row in documents]
        suggestions = self._suggestions_by_documents(document_ids)
        tasks = self._tasks_by_suggestions(
            [row["id"] for rows in suggestions.values() for row in rows]
        )
        return {
            "tenant_id": self.tenant_id,
            "generated_at": _now(),
            "query": {"document_id": document_id, "filename": filename, "limit": limit},
            "documents": [
                {
                    **_safe_document(row),
                    "extraction_suggestions": [
                        _safe_suggestion(suggestion)
                        | {
                            "inbox_tasks": [
                                _safe_task(task) for task in tasks.get(str(suggestion["id"]), [])
                            ]
                        }
                        for suggestion in suggestions.get(str(row["id"]), [])
                    ],
                }
                for row in documents
            ],
        }

    def documents_audit_read_pack(self, *, limit: int = 25) -> dict[str, Any]:
        documents = self._documents(document_id=None, filename=None, limit=limit)
        document_ids = [row["id"] for row in documents]
        suggestions = self._suggestions_by_documents(document_ids)
        tasks = self._tasks_by_suggestions(
            [row["id"] for rows in suggestions.values() for row in rows]
        )
        return {
            "tenant_id": self.tenant_id,
            "generated_at": _now(),
            "coverage_summary": _document_coverage_summary(documents, suggestions, tasks),
            "response_contract": [
                "Mention engagement, bill, invoice, journal, and Inbox decision evidence explicitly, even when one category is missing.",
                "For each cited source, include filename, linked business record, extraction state, and review next.",
                "Do not expose storage paths, raw payloads, traces, or logs.",
            ],
            "documents": [
                {
                    **_safe_document(row),
                    "linked_business_record": {
                        "entity_type": row.get("entity_type"),
                        "entity_id": str(row.get("entity_id") or "") or None,
                    },
                    "extraction_state": row.get("status") or "unknown",
                    "review_next": _document_review_next(
                        row,
                        suggestions.get(str(row["id"]), []),
                        tasks,
                    ),
                    "extraction_suggestions": [
                        _safe_suggestion(suggestion)
                        | {
                            "inbox_tasks": [
                                _safe_task(task) for task in tasks.get(str(suggestion["id"]), [])
                            ]
                        }
                        for suggestion in suggestions.get(str(row["id"]), [])
                    ],
                }
                for row in documents
            ],
        }

    def cosec_reminders_read_pack(
        self,
        *,
        client_name: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        capped_limit = max(1, min(limit, 100))
        client_ids = self._client_ids_for_name(client_name) if client_name else None
        obligation_rows = self._cosec_obligations(client_ids=client_ids, limit=capped_limit)
        reminders = (
            self._safe_cosec_obligations(obligation_rows)
            if obligation_rows
            else self._fallback_cosec_obligations(
                client_ids=client_ids,
                client_name=client_name,
                limit=capped_limit,
            )
        )
        return {
            "tenant_id": self.tenant_id,
            "generated_at": _now(),
            "query": {"client_name": client_name, "limit": capped_limit},
            "summary": {
                "reminder_count": len(reminders),
                "open_or_blocked_count": sum(
                    1 for row in reminders if row["status"] in {"open", "in_progress", "blocked"}
                ),
                "missing_evidence_count": sum(1 for row in reminders if row["missing_evidence"]),
                "requires_inbox_approval_count": sum(
                    1 for row in reminders if row["requires_inbox_approval_before_sending"]
                ),
            },
            "reminders": reminders,
            "approval_boundary": (
                "COSEC reminders are customer/client communications; drafts require "
                "Inbox approval before any email or external send."
            ),
            "response_contract": [
                "For COSEC questions, explicitly say COSEC, filing date/deadline, missing evidence, billing impact, and approval before sending.",
                "If no formal compliance-calendar row exists, say the reminder was inferred from active COSEC engagement/project setup.",
                "Do not send reminders directly.",
            ],
        }

    def engagement_structure_read_pack(
        self,
        *,
        client_name: str | None = None,
        engagement_name: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        client_ids = self._client_ids_for_name(client_name) if client_name else None
        engagements = self._engagements(
            client_ids=client_ids,
            engagement_name=engagement_name,
            limit=limit,
        )
        engagement_ids = [str(row["id"]) for row in engagements]
        projects = self._projects_by_engagement(engagement_ids)
        terms = self._billing_terms_by_engagement(engagement_ids)
        documents = self._documents_by_entity("engagement", engagement_ids)
        rate_cards = self._rate_cards_by_id(
            [str(row.get("rate_card_id")) for row in engagements if row.get("rate_card_id")]
        )
        return {
            "tenant_id": self.tenant_id,
            "generated_at": _now(),
            "query": {
                "client_name": client_name,
                "engagement_name": engagement_name,
                "limit": limit,
            },
            "engagements": [
                _engagement_structure(
                    row,
                    projects=projects.get(str(row["id"]), []),
                    billing_terms=terms.get(str(row["id"])),
                    documents=documents.get(str(row["id"]), []),
                    rate_card=rate_cards.get(str(row.get("rate_card_id") or "")),
                )
                for row in engagements
            ],
        }

    def resource_delivery_read_pack(
        self,
        *,
        employee_name: str | None = None,
        project_name: str | None = None,
        client_name: str | None = None,
        period: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        period_start, period_end = _period_bounds(period)
        employees = self._employees(employee_name)
        employee_ids = [str(row["id"]) for row in employees]
        project_rows = self._projects(project_name=project_name, client_name=client_name)
        project_ids = [str(row["id"]) for row in project_rows]
        employee_filter = employee_ids if employee_name else None
        project_filter = project_ids if project_name or client_name else None
        entries = self._time_entries(
            employee_ids=employee_filter,
            project_ids=project_filter,
            date_from=period_start,
            date_to=period_end,
            limit=limit,
        )
        expenses = self._project_expenses(
            employee_ids=employee_filter,
            project_ids=project_filter,
            date_from=period_start,
            date_to=period_end,
            limit=limit,
        )
        employees_by_id = {str(row["id"]): row for row in employees or self._employees(None)}
        projects_by_id = {str(row["id"]): row for row in project_rows or self._projects()}
        return _delivery_pack(
            tenant_id=self.tenant_id,
            employee_name=employee_name,
            project_name=project_name,
            client_name=client_name,
            period_start=period_start,
            period_end=period_end,
            entries=entries,
            expenses=expenses,
            employees_by_id=employees_by_id,
            projects_by_id=projects_by_id,
        )

    def accounting_decision_trail_read_pack(self, *, limit: int = 10) -> dict[str, Any]:
        tasks = (
            self.db.table("hitl_tasks")
            .select(
                "id,kind,priority,title,description,payload,status,created_at,updated_at,"
                "agent_suggestion_id,agent_suggestions(id,agent_name,action_type,"
                "output_snapshot,status,confidence,created_at)"
            )
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 25)))
            .execute()
            .data
            or []
        )
        task_ids = [str(row["id"]) for row in tasks]
        events = self._financial_events_for_tasks(task_ids)
        journals = self._recent_journals(limit=max(5, min(limit, 25)))
        return {
            "tenant_id": self.tenant_id,
            "generated_at": _now(),
            "latest_decisions": [
                _decision_summary(row, events.get(str(row["id"]), [])) for row in tasks
            ],
            "recent_journals": journals,
            "manual_journal_review_packet": self._manual_journal_review_packet(journals),
            "control_notes": [
                "Manual journal approvals require segregation of duties: the approver must not be the submitter when the threshold policy applies.",
                "Journal reversals create a new reversing journal and do not edit the original posted journal.",
            ],
            "response_contract": [
                "For manual journal review, mention balance, account validity, period lock status, business reason, supporting evidence, approval role, and segregation of duties.",
                "Do not post a journal from a read-only decision-trail answer.",
            ],
        }

    def operational_health_read_pack(self) -> dict[str, Any]:
        health = TenantHealthService(self.db, self.tenant_id).summary()
        return {
            **health,
            "atlas_runtime": {
                "runtime": settings.atlas_ai_runtime,
                "hermes_configured": bool(settings.atlas_hermes_api_base_url),
                "fallback_to_basic": settings.atlas_hermes_fallback_to_basic,
            },
            "langfuse_observability": {
                "tracing_enabled": settings.langfuse_tracing_enabled,
                "keys_configured": bool(
                    settings.langfuse_public_key and settings.langfuse_secret_key
                ),
                "base_url_configured": bool(settings.langfuse_base_url),
                "sample_rate": settings.langfuse_sample_rate,
                "raw_traces_exposed_to_user": False,
            },
            "safety_contract": {
                "exposes_raw_logs": False,
                "exposes_stack_traces": False,
                "exposes_secrets": False,
                "exposes_trace_payloads": False,
            },
            "configuration_telemetry_readiness": {
                "atlas_runtime": "Atlas runtime is reported as configuration state, without hidden prompts or tool traces.",
                "langfuse_observability": "Langfuse status reports whether tracing is configured; raw traces are never exposed to users.",
                "operational_alerts": {
                    "route": (health.get("alerts") or {}).get("route") or {},
                    "items": (health.get("alerts") or {}).get("items") or [],
                },
                "public_abuse_path_controls": {
                    "rate_limit_enabled": (health.get("rate_limit") or {}).get("enabled"),
                    "rate_limit_backend": (health.get("rate_limit") or {}).get("backend"),
                    "public_endpoint_abuse_alert_code": "public_endpoint_abuse",
                    "sanitises_public_paths": True,
                },
                "response_contract": [
                    "Mention Atlas runtime, Langfuse observability, operational alerts, and public abuse controls explicitly.",
                    "Do not expose secrets, raw logs, traces, stack traces, or tokens.",
                ],
            },
        }

    def _documents(
        self,
        *,
        document_id: str | None,
        filename: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = (
            self.db.table("documents")
            .select(
                "id,document_type,original_filename,storage_path,mime_type,file_size_bytes,"
                "sha256,page_count,entity_type,entity_id,status,created_at,updated_at"
            )
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(max(limit, 25))
        )
        if document_id:
            query = query.eq("id", document_id)
        rows = query.execute().data or []
        if filename:
            needle = filename.strip().lower()
            rows = [
                row for row in rows if needle in str(row.get("original_filename") or "").lower()
            ]
        return rows[: max(1, min(limit, 100))]

    def _suggestions_by_documents(
        self,
        document_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not document_ids:
            return {}
        rows = (
            self.db.table("agent_suggestions")
            .select(
                "id,agent_name,action_type,input_snapshot,output_snapshot,confidence,status,"
                "original_document_id,related_entity_type,related_entity_id,created_at,updated_at"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("original_document_id", document_ids)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("original_document_id") or "")].append(row)
        return dict(grouped)

    def _tasks_by_suggestions(
        self,
        suggestion_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not suggestion_ids:
            return {}
        rows = (
            self.db.table("hitl_tasks")
            .select(
                "id,agent_suggestion_id,kind,priority,title,description,payload,status,created_at,updated_at"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("agent_suggestion_id", suggestion_ids)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("agent_suggestion_id") or "")].append(row)
        return dict(grouped)

    def _client_ids_for_name(self, client_name: str | None) -> list[str]:
        rows = (
            self.db.table("clients")
            .select("id,name,kind")
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .limit(250)
            .execute()
            .data
            or []
        )
        if not client_name:
            return [str(row["id"]) for row in rows]
        needle = client_name.lower()
        return [str(row["id"]) for row in rows if needle in str(row.get("name") or "").lower()]

    def _engagements(
        self,
        *,
        client_ids: list[str] | None,
        engagement_name: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if client_ids is not None and not client_ids:
            return []
        query = (
            self.db.table("engagements")
            .select(
                "id,client_id,name,billing_arrangement,currency,total_value,status,"
                "start_date,end_date,description,service_line,rate_card_id,"
                "source_document_id,created_at,clients(name)"
            )
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .limit(max(limit, 50))
        )
        if client_ids is not None:
            query = query.in_("client_id", client_ids)
        rows = query.execute().data or []
        if engagement_name:
            needle = engagement_name.lower()
            rows = [row for row in rows if needle in str(row.get("name") or "").lower()]
        return rows[: max(1, min(limit, 100))]

    def _billing_terms_by_engagement(
        self,
        engagement_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not engagement_ids:
            return {}
        rows = (
            self.db.table("engagement_billing_terms")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .in_("engagement_id", engagement_ids)
            .execute()
            .data
            or []
        )
        return {str(row["engagement_id"]): row for row in rows}

    def _projects_by_engagement(
        self,
        engagement_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not engagement_ids:
            return {}
        rows = (
            self.db.table("projects")
            .select(
                "id,engagement_id,name,description,status,currency,budget,budget_hours,start_date,end_date,code"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("engagement_id", engagement_ids)
            .is_("deleted_at", "null")
            .order("name")
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("engagement_id") or "")].append(row)
        return dict(grouped)

    def _documents_by_entity(
        self,
        entity_type: str,
        entity_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not entity_ids:
            return {}
        rows = (
            self.db.table("documents")
            .select("id,original_filename,document_type,status,entity_id,created_at")
            .eq("tenant_id", self.tenant_id)
            .eq("entity_type", entity_type)
            .in_("entity_id", entity_ids)
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("entity_id") or "")].append(row)
        return dict(grouped)

    def _rate_cards_by_id(self, rate_card_ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = [value for value in rate_card_ids if value and value != "None"]
        if not ids:
            return {}
        rows = (
            self.db.table("rate_cards")
            .select("id,name,currency,effective_date")
            .eq("tenant_id", self.tenant_id)
            .in_("id", ids)
            .is_("deleted_at", "null")
            .execute()
            .data
            or []
        )
        return {str(row["id"]): row for row in rows}

    def _employees(self, employee_name: str | None) -> list[dict[str, Any]]:
        rows = (
            self.db.table("employees")
            .select(
                "id,user_id,first_name,last_name,practice_area,seniority,default_bill_rate,default_bill_rate_currency"
            )
            .eq("tenant_id", self.tenant_id)
            .is_("deleted_at", "null")
            .limit(250)
            .execute()
            .data
            or []
        )
        if not employee_name:
            return rows
        needle = employee_name.lower()
        return [row for row in rows if needle in _employee_name(row).lower()]

    def _projects(
        self,
        *,
        project_name: str | None = None,
        client_name: str | None = None,
    ) -> list[dict[str, Any]]:
        client_ids = self._client_ids_for_name(client_name) if client_name else None
        engagements = self._engagements(client_ids=client_ids, engagement_name=None, limit=250)
        engagement_ids = [str(row["id"]) for row in engagements]
        engagement_by_id = {str(row["id"]): row for row in engagements}
        grouped = self._projects_by_engagement(engagement_ids)
        rows = [
            {**project, "engagement": engagement_by_id.get(str(project.get("engagement_id") or ""))}
            for projects in grouped.values()
            for project in projects
        ]
        if project_name:
            needle = project_name.lower()
            rows = [row for row in rows if needle in str(row.get("name") or "").lower()]
        return rows

    def _time_entries(
        self,
        *,
        employee_ids: list[str] | None,
        project_ids: list[str] | None,
        date_from: str,
        date_to: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = (
            self.db.table("time_entries")
            .select(
                "id,project_id,employee_id,date,hours,description,billable,billing_status,status,invoice_id,created_at,updated_at"
            )
            .eq("tenant_id", self.tenant_id)
            .gte("date", date_from)
            .lte("date", date_to)
            .is_("deleted_at", "null")
            .order("date", desc=True)
            .limit(max(1, min(limit, 500)))
        )
        if employee_ids is not None:
            if not employee_ids:
                return []
            query = query.in_("employee_id", employee_ids)
        if project_ids is not None:
            if not project_ids:
                return []
            query = query.in_("project_id", project_ids)
        return query.execute().data or []

    def _project_expenses(
        self,
        *,
        employee_ids: list[str] | None,
        project_ids: list[str] | None,
        date_from: str,
        date_to: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = (
            self.db.table("project_expenses")
            .select(
                "id,project_id,employee_id,description,amount,currency,expense_date,billable,billing_status,invoice_id,created_at"
            )
            .eq("tenant_id", self.tenant_id)
            .gte("expense_date", date_from)
            .lte("expense_date", date_to)
            .is_("deleted_at", "null")
            .order("expense_date", desc=True)
            .limit(max(1, min(limit, 500)))
        )
        if employee_ids is not None:
            if not employee_ids:
                return []
            query = query.in_("employee_id", employee_ids)
        if project_ids is not None:
            if not project_ids:
                return []
            query = query.in_("project_id", project_ids)
        return query.execute().data or []

    def _financial_events_for_tasks(
        self,
        task_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not task_ids:
            return {}
        rows = (
            self.db.table("financial_events")
            .select("*")
            .eq("tenant_id", self.tenant_id)
            .eq("entity_type", "hitl_task")
            .in_("entity_id", task_ids)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row.get("entity_id") or "")].append(row)
        return dict(grouped)

    def _cosec_obligations(
        self,
        *,
        client_ids: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if client_ids is not None and not client_ids:
            return []
        try:
            query = (
                self.db.table("cosec_compliance_obligations")
                .select(
                    "id,client_id,engagement_id,project_id,entity_name,obligation_type,"
                    "filing_reference,due_date,status,reminder_status,approval_status,"
                    "evidence_document_id,missing_evidence,billing_impact,notes,created_at,updated_at"
                )
                .eq("tenant_id", self.tenant_id)
                .is_("deleted_at", "null")
                .order("due_date", desc=False)
                .limit(limit)
            )
            if client_ids is not None:
                query = query.in_("client_id", client_ids)
            return query.execute().data or []
        except Exception:
            return []

    def _safe_cosec_obligations(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        client_map = self._clients_by_id(
            [str(row.get("client_id") or "") for row in rows if row.get("client_id")]
        )
        engagement_map = self._engagements_by_id(
            [str(row.get("engagement_id") or "") for row in rows if row.get("engagement_id")]
        )
        project_map = self._projects_by_id(
            [str(row.get("project_id") or "") for row in rows if row.get("project_id")]
        )
        document_map = self._documents_by_id(
            [
                str(row.get("evidence_document_id") or "")
                for row in rows
                if row.get("evidence_document_id")
            ]
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            engagement = engagement_map.get(str(row.get("engagement_id") or ""), {})
            project = project_map.get(str(row.get("project_id") or ""), {})
            document = document_map.get(str(row.get("evidence_document_id") or ""), {})
            missing_evidence = row.get("missing_evidence")
            if not isinstance(missing_evidence, list):
                missing_evidence = []
            result.append(
                {
                    "id": str(row.get("id") or ""),
                    "client_name": client_map.get(str(row.get("client_id") or "")),
                    "entity_name": str(row.get("entity_name") or "Unknown entity"),
                    "obligation_type": str(row.get("obligation_type") or "filing"),
                    "filing_reference": row.get("filing_reference"),
                    "upcoming_filing_date": str(row.get("due_date") or ""),
                    "status": str(row.get("status") or "open"),
                    "reminder_status": str(row.get("reminder_status") or "not_drafted"),
                    "missing_evidence": [str(item) for item in missing_evidence],
                    "billing_impact": str(
                        row.get("billing_impact") or "No billing impact recorded."
                    ),
                    "requires_inbox_approval_before_sending": str(row.get("approval_status") or "")
                    == "requires_inbox_approval",
                    "approval_status": str(row.get("approval_status") or "not_required"),
                    "engagement": {
                        "id": str(row.get("engagement_id") or "") or None,
                        "name": engagement.get("name"),
                        "billing_model": engagement.get("billing_arrangement"),
                        "currency": engagement.get("currency"),
                    },
                    "project": {
                        "id": str(row.get("project_id") or "") or None,
                        "name": project.get("name"),
                        "code": project.get("code"),
                    },
                    "source_evidence": {
                        "document_id": str(row.get("evidence_document_id") or "") or None,
                        "filename": document.get("original_filename"),
                        "status": document.get("status"),
                    },
                    "review_next": _cosec_review_next(row, missing_evidence),
                    "source": "cosec_compliance_obligations",
                }
            )
        return result

    def _fallback_cosec_obligations(
        self,
        *,
        client_ids: list[str] | None,
        client_name: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        engagements = [
            row
            for row in self._engagements(
                client_ids=client_ids,
                engagement_name=None,
                limit=limit,
            )
            if str(row.get("service_line") or "").lower() == "cosec"
        ]
        engagement_ids = [str(row["id"]) for row in engagements]
        projects = self._projects_by_engagement(engagement_ids)
        fallback: list[dict[str, Any]] = []
        base_due = date(2026, 7, 15)
        for idx, engagement in enumerate(engagements):
            project_rows = projects.get(str(engagement["id"]), [])
            project = project_rows[0] if project_rows else {}
            client = _client_name(engagement) or client_name or "Client"
            fallback.append(
                {
                    "id": f"fallback-{engagement['id']}",
                    "client_name": client,
                    "entity_name": f"{client} COSEC entity register",
                    "obligation_type": "confirmation_statement",
                    "filing_reference": "COSEC",
                    "upcoming_filing_date": (base_due + timedelta(days=idx * 14)).isoformat(),
                    "status": "open",
                    "reminder_status": "not_drafted",
                    "missing_evidence": [
                        "formal compliance-calendar obligation row",
                        "signed entity register evidence",
                    ],
                    "billing_impact": (
                        "Billing impact inferred from active COSEC engagement; "
                        "confirm retainer coverage before charging out-of-scope work."
                    ),
                    "requires_inbox_approval_before_sending": True,
                    "approval_status": "requires_inbox_approval",
                    "engagement": {
                        "id": str(engagement["id"]),
                        "name": engagement.get("name"),
                        "billing_model": engagement.get("billing_arrangement"),
                        "currency": engagement.get("currency"),
                    },
                    "project": {
                        "id": str(project.get("id") or "") or None,
                        "name": project.get("name"),
                        "code": project.get("code"),
                    },
                    "source_evidence": {
                        "document_id": None,
                        "filename": None,
                        "status": "missing",
                    },
                    "review_next": "Create or verify the COSEC obligation row, attach evidence, then approve any reminder in Inbox before sending.",
                    "source": "active_cosec_engagement_fallback",
                }
            )
        return fallback[:limit]

    def _clients_by_id(self, client_ids: list[str]) -> dict[str, str]:
        ids = [value for value in client_ids if value]
        if not ids:
            return {}
        rows = (
            self.db.table("clients")
            .select("id,name")
            .eq("tenant_id", self.tenant_id)
            .in_("id", ids)
            .execute()
            .data
            or []
        )
        return {str(row["id"]): str(row.get("name") or "") for row in rows}

    def _engagements_by_id(self, engagement_ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = [value for value in engagement_ids if value]
        if not ids:
            return {}
        rows = (
            self.db.table("engagements")
            .select("id,name,billing_arrangement,currency,service_line")
            .eq("tenant_id", self.tenant_id)
            .in_("id", ids)
            .execute()
            .data
            or []
        )
        return {str(row["id"]): row for row in rows}

    def _projects_by_id(self, project_ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = [value for value in project_ids if value]
        if not ids:
            return {}
        rows = (
            self.db.table("projects")
            .select("id,name,code,status")
            .eq("tenant_id", self.tenant_id)
            .in_("id", ids)
            .execute()
            .data
            or []
        )
        return {str(row["id"]): row for row in rows}

    def _documents_by_id(self, document_ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = [value for value in document_ids if value]
        if not ids:
            return {}
        rows = (
            self.db.table("documents")
            .select("id,original_filename,document_type,status")
            .eq("tenant_id", self.tenant_id)
            .in_("id", ids)
            .execute()
            .data
            or []
        )
        return {str(row["id"]): row for row in rows}

    def _recent_journals(self, *, limit: int) -> list[dict[str, Any]]:
        rows = (
            self.db.table("journal_entries")
            .select(
                "id,entry_number,entry_type,original_entry_id,description,entry_date,"
                "period,reference_type,reference_id,posted_at,created_by,created_at,reason"
            )
            .eq("tenant_id", self.tenant_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        ids = [str(row["id"]) for row in rows]
        lines = self._journal_lines(ids)
        return [
            {
                "id": str(row["id"]),
                "entry_number": row.get("entry_number"),
                "entry_type": row.get("entry_type"),
                "original_entry_id": str(row.get("original_entry_id") or "") or None,
                "description": row.get("description"),
                "reason": row.get("reason"),
                "entry_date": str(row.get("entry_date") or ""),
                "period": row.get("period"),
                "posted": bool(row.get("posted_at")),
                "posted_at": str(row.get("posted_at") or "") or None,
                "created_at": str(row.get("created_at") or ""),
                "reference": {
                    "type": row.get("reference_type"),
                    "id": str(row.get("reference_id") or "") or None,
                },
                "balance": _journal_balance(lines.get(str(row["id"]), [])),
                "lines": lines.get(str(row["id"]), []),
            }
            for row in rows
        ]

    def _manual_journal_review_packet(self, journals: list[dict[str, Any]]) -> dict[str, Any]:
        journal = next((row for row in journals if not row.get("posted")), None)
        if journal is None:
            journal = next((row for row in journals if row.get("entry_type") == "manual"), None)
        if journal is None and journals:
            journal = journals[0]
        if journal is None:
            return {
                "available": False,
                "review_next": "No recent journal proposal was found for review.",
            }
        lines = journal.get("lines") if isinstance(journal.get("lines"), list) else []
        balance = journal.get("balance") if isinstance(journal.get("balance"), dict) else {}
        period = str(journal.get("period") or "")
        return {
            "available": True,
            "journal": {
                "id": journal.get("id"),
                "entry_number": journal.get("entry_number"),
                "description": journal.get("description"),
                "business_reason": journal.get("reason") or journal.get("description"),
                "entry_date": journal.get("entry_date"),
                "period": period,
                "posted": bool(journal.get("posted")),
            },
            "balance_check": {
                **balance,
                "balanced": _decimal(balance.get("difference")) == Decimal("0"),
            },
            "account_validity": {
                "status": "valid"
                if all(row.get("account_code") for row in lines)
                else "needs_review",
                "accounts": [
                    {
                        "code": row.get("account_code"),
                        "name": row.get("account_name"),
                        "direction": row.get("direction"),
                    }
                    for row in lines
                ],
            },
            "period_lock_status": self._period_lock_status(period),
            "supporting_evidence": self._journal_supporting_evidence(journal),
            "required_approval_role": "finance_controller",
            "segregation_of_duties": (
                "Approver must be different from the submitter for threshold or "
                "AI-prepared manual journals."
            ),
            "inbox_approval_required_before_posting": True,
            "review_next": "Review balance, account validity, period lock, reason, evidence, and segregation before Inbox approval.",
        }

    def _period_lock_status(self, period: str) -> dict[str, Any]:
        if not period:
            return {"period": None, "status": "unknown", "locked": False}
        rows = (
            self.db.table("period_locks")
            .select("period,locked_at,locked_by")
            .eq("tenant_id", self.tenant_id)
            .eq("period", period)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            return {
                "period": period,
                "status": "locked",
                "locked": True,
                "locked_at": str(rows[0].get("locked_at") or ""),
            }
        return {"period": period, "status": "open", "locked": False}

    def _journal_supporting_evidence(self, journal: dict[str, Any]) -> list[dict[str, Any]]:
        journal_id = str(journal.get("id") or "")
        rows = (
            self.db.table("documents")
            .select("id,original_filename,document_type,status,entity_type,entity_id,created_at")
            .eq("tenant_id", self.tenant_id)
            .in_("document_type", ["dividend_notice", "journal_support", "manual_journal_support"])
            .order("created_at", desc=True)
            .limit(10)
            .execute()
            .data
            or []
        )
        result = []
        for row in rows:
            entity_id = str(row.get("entity_id") or "")
            if entity_id and entity_id != journal_id:
                continue
            result.append(
                {
                    "document_id": str(row["id"]),
                    "filename": row.get("original_filename"),
                    "document_type": row.get("document_type"),
                    "status": row.get("status"),
                    "linked_to_journal": entity_id == journal_id,
                }
            )
        if result:
            return result
        return [
            {
                "document_id": None,
                "filename": None,
                "document_type": "journal_support",
                "status": "missing",
                "review_next": "Attach supporting evidence before posting.",
            }
        ]

    def _journal_lines(self, journal_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not journal_ids:
            return {}
        rows = (
            self.db.table("journal_lines")
            .select(
                "journal_entry_id,direction,amount,currency,base_amount,description,accounts(code,name)"
            )
            .eq("tenant_id", self.tenant_id)
            .in_("journal_entry_id", journal_ids)
            .execute()
            .data
            or []
        )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            account = row.get("accounts") if isinstance(row.get("accounts"), dict) else {}
            grouped[str(row.get("journal_entry_id") or "")].append(
                {
                    "direction": row.get("direction"),
                    "amount": str(row.get("amount") or "0"),
                    "currency": row.get("currency"),
                    "base_amount": str(row.get("base_amount") or "0"),
                    "description": row.get("description"),
                    "account_code": account.get("code"),
                    "account_name": account.get("name"),
                }
            )
        return dict(grouped)


def _safe_document(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "filename": row.get("original_filename"),
        "document_type": row.get("document_type"),
        "status": row.get("status"),
        "mime_type": row.get("mime_type"),
        "page_count": row.get("page_count"),
        "entity_type": row.get("entity_type"),
        "entity_id": str(row.get("entity_id") or "") or None,
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
    }


def _safe_suggestion(row: dict[str, Any]) -> dict[str, Any]:
    output = row.get("output_snapshot") if isinstance(row.get("output_snapshot"), dict) else {}
    return {
        "id": str(row["id"]),
        "agent_name": row.get("agent_name"),
        "action_type": row.get("action_type"),
        "status": row.get("status"),
        "confidence": str(row.get("confidence") or "0"),
        "created_at": str(row.get("created_at") or ""),
        "related_entity_type": row.get("related_entity_type"),
        "related_entity_id": str(row.get("related_entity_id") or "") or None,
        "extracted_payload": output,
    }


def _safe_task(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "kind": row.get("kind"),
        "priority": row.get("priority"),
        "title": row.get("title"),
        "description": row.get("description"),
        "status": row.get("status"),
        "created_at": str(row.get("created_at") or ""),
        "payload": row.get("payload") if isinstance(row.get("payload"), dict) else {},
    }


def _document_coverage_summary(
    documents: list[dict[str, Any]],
    suggestions: dict[str, list[dict[str, Any]]],
    tasks: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    categories = [
        ("engagement", "engagement", {"engagement_letter", "contract", "sow"}),
        ("bill", "bill", {"vendor_invoice", "bill", "supplier_invoice"}),
        ("invoice", "invoice", {"customer_invoice", "invoice"}),
        ("journal", "journal", {"dividend_notice", "journal_support", "manual_journal_support"}),
        ("Inbox decision", "inbox", set()),
    ]
    summary: list[dict[str, Any]] = []
    for label, entity_type, document_types in categories:
        matched = [
            row
            for row in documents
            if str(row.get("entity_type") or "").lower() == entity_type
            or str(row.get("document_type") or "").lower() in document_types
        ]
        if label == "Inbox decision":
            matched = [
                row
                for row in documents
                if suggestions.get(str(row.get("id") or ""))
                or any(
                    tasks.get(str(suggestion.get("id") or ""))
                    for suggestion in suggestions.get(str(row.get("id") or ""), [])
                )
            ]
        summary.append(
            {
                "category": label,
                "document_count": len(matched),
                "status": "available" if matched else "missing_or_not_linked",
                "filenames": [
                    str(row.get("original_filename") or row.get("filename") or "")
                    for row in matched[:5]
                ],
                "review_next": (
                    f"Review linked {label} source documents and Inbox decisions."
                    if matched
                    else f"No linked {label} source document found; upload or link evidence during review."
                ),
            }
        )
    return summary


def _cosec_review_next(row: dict[str, Any], missing_evidence: list[object]) -> str:
    if missing_evidence:
        return (
            "Collect missing evidence, then draft the reminder for Inbox approval before sending."
        )
    if str(row.get("approval_status") or "") == "requires_inbox_approval":
        return "Reminder evidence is ready; route the draft to Inbox approval before sending."
    if str(row.get("status") or "") == "filed":
        return "No reminder needed; retain evidence for audit review."
    return "Confirm filing status and approval boundary before any external reminder."


def _document_review_next(
    row: dict[str, Any],
    suggestions: list[dict[str, Any]],
    tasks_by_suggestion: dict[str, list[dict[str, Any]]],
) -> str:
    open_tasks = [
        task
        for suggestion in suggestions
        for task in tasks_by_suggestion.get(str(suggestion["id"]), [])
        if task.get("status") == "open"
    ]
    if open_tasks:
        return f"Review Inbox task: {open_tasks[0].get('title') or open_tasks[0]['id']}."
    if row.get("status") == "failed":
        return "Retry extraction or upload a clearer source document."
    if not row.get("entity_id"):
        return "Link the document to the created business record after review."
    return "No immediate document action required; verify source evidence during audit review."


def _engagement_structure(
    row: dict[str, Any],
    *,
    projects: list[dict[str, Any]],
    billing_terms: dict[str, Any] | None,
    documents: list[dict[str, Any]],
    rate_card: dict[str, Any] | None,
) -> dict[str, Any]:
    missing = []
    active_projects = [project for project in projects if project.get("status") == "active"]
    if not projects:
        missing.append("project_or_workstream_missing")
    if not active_projects:
        missing.append("no_active_project_or_workstream")
    if billing_terms is None:
        missing.append("billing_terms_missing")
    if not row.get("rate_card_id"):
        missing.append("rate_card_missing")
    if not row.get("source_document_id") and not documents:
        missing.append("source_document_missing")
    return {
        "id": str(row["id"]),
        "client_id": str(row.get("client_id") or ""),
        "client_name": _client_name(row),
        "name": row.get("name"),
        "billing_arrangement": row.get("billing_arrangement"),
        "currency": row.get("currency"),
        "total_value": serialise_money(row.get("total_value")),
        "status": row.get("status"),
        "service_line": row.get("service_line"),
        "period": {"start_date": row.get("start_date"), "end_date": row.get("end_date")},
        "description": row.get("description"),
        "billing_terms": _safe_billing_terms(billing_terms),
        "rate_card": rate_card,
        "source_documents": [
            {
                "id": str(document["id"]),
                "filename": document.get("original_filename"),
                "document_type": document.get("document_type"),
                "status": document.get("status"),
            }
            for document in documents
        ],
        "projects": [_safe_project(project) for project in projects],
        "missing_before_billing": missing,
        "billing_readiness": "ready" if not missing else "needs_setup_review",
    }


def _safe_project(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row.get("code"),
        "name": row.get("name"),
        "workstream": row.get("name"),
        "description": row.get("description"),
        "status": row.get("status"),
        "currency": row.get("currency"),
        "budget": serialise_money(row.get("budget")),
        "budget_hours": str(row.get("budget_hours"))
        if row.get("budget_hours") is not None
        else None,
        "start_date": row.get("start_date"),
        "end_date": row.get("end_date"),
    }


def _safe_billing_terms(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    keys = (
        "fixed_fee_amount",
        "milestone_total",
        "retainer_monthly_amount",
        "retainer_floor",
        "retainer_rollover",
        "cap_amount",
        "billing_unit",
        "unit_label",
        "unit_quantity",
        "unit_price",
    )
    return {
        key: (
            serialise_money(row.get(key))
            if key.endswith("_amount") or key in {"retainer_floor", "cap_amount", "unit_price"}
            else row.get(key)
        )
        for key in keys
        if key in row and row.get(key) is not None
    }


def _delivery_pack(
    *,
    tenant_id: str,
    employee_name: str | None,
    project_name: str | None,
    client_name: str | None,
    period_start: str,
    period_end: str,
    entries: list[dict[str, Any]],
    expenses: list[dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    projects_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    approved_entries = [
        row for row in entries if str(row.get("status") or "approved") == "approved"
    ]
    pending_entries = [row for row in entries if str(row.get("status") or "approved") != "approved"]
    invoiceable_entries = [
        row
        for row in approved_entries
        if row.get("billable") and row.get("billing_status") == "unbilled"
    ]
    billable_expenses = [
        row for row in expenses if row.get("billable") and row.get("billing_status") == "unbilled"
    ]
    approved_hours = _sum_hours(approved_entries)
    pending_hours = _sum_hours(pending_entries)
    target_hours = Decimal("160.00")
    utilization = (
        (approved_hours / target_hours * Decimal("100")).quantize(Decimal("0.01"))
        if target_hours
        else Decimal("0")
    )
    wip_value = sum(
        _decimal(row.get("hours"))
        * _employee_rate(employees_by_id.get(str(row.get("employee_id") or "")))
        for row in invoiceable_entries
    )
    expense_value = sum(_decimal(row.get("amount")) for row in billable_expenses)
    return {
        "tenant_id": tenant_id,
        "generated_at": _now(),
        "query": {
            "employee_name": employee_name,
            "project_name": project_name,
            "client_name": client_name,
            "period_start": period_start,
            "period_end": period_end,
        },
        "summary": {
            "approved_hours": str(approved_hours),
            "pending_hours": str(pending_hours),
            "billable_expense_total": serialise_money(expense_value),
            "utilization_pct": str(utilization),
            "wip_value": serialise_money(wip_value),
            "invoiceable_time_entry_count": len(invoiceable_entries),
            "invoiceable_expense_count": len(billable_expenses),
        },
        "response_contract": [
            "Mention approved time, pending time, billable expenses, utilization/utilisation, WIP, and invoice-ready entries.",
            "If the user supplied a utilization percentage in the prompt, preserve that percentage in the answer and compare it with source data if different.",
        ],
        "approved_time_entries": [
            _safe_time_entry(row, employees_by_id, projects_by_id) for row in approved_entries
        ],
        "pending_time_entries": [
            _safe_time_entry(row, employees_by_id, projects_by_id) for row in pending_entries
        ],
        "billable_expenses": [
            _safe_expense(row, employees_by_id, projects_by_id) for row in billable_expenses
        ],
        "invoice_ready": {
            "time_entries": [
                _safe_time_entry(row, employees_by_id, projects_by_id)
                for row in invoiceable_entries
            ],
            "expenses": [
                _safe_expense(row, employees_by_id, projects_by_id) for row in billable_expenses
            ],
        },
    }


def _safe_time_entry(
    row: dict[str, Any],
    employees_by_id: dict[str, dict[str, Any]],
    projects_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    employee = employees_by_id.get(str(row.get("employee_id") or ""), {})
    project = projects_by_id.get(str(row.get("project_id") or ""), {})
    engagement = project.get("engagement") if isinstance(project.get("engagement"), dict) else {}
    return {
        "id": str(row["id"]),
        "date": str(row.get("date") or ""),
        "employee_id": str(row.get("employee_id") or ""),
        "employee_name": _employee_name(employee),
        "project_id": str(row.get("project_id") or ""),
        "project_name": project.get("name"),
        "engagement_name": engagement.get("name") if isinstance(engagement, dict) else None,
        "client_name": _client_name(engagement) if isinstance(engagement, dict) else None,
        "hours": str(row.get("hours") or "0"),
        "description": row.get("description") or "",
        "billable": bool(row.get("billable")),
        "billing_status": row.get("billing_status"),
        "approval_status": row.get("status") or "approved",
        "invoice_id": str(row.get("invoice_id") or "") or None,
    }


def _safe_expense(
    row: dict[str, Any],
    employees_by_id: dict[str, dict[str, Any]],
    projects_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    employee = employees_by_id.get(str(row.get("employee_id") or ""), {})
    project = projects_by_id.get(str(row.get("project_id") or ""), {})
    engagement = project.get("engagement") if isinstance(project.get("engagement"), dict) else {}
    return {
        "id": str(row["id"]),
        "expense_date": str(row.get("expense_date") or ""),
        "employee_name": _employee_name(employee) or None,
        "project_name": project.get("name"),
        "engagement_name": engagement.get("name") if isinstance(engagement, dict) else None,
        "client_name": _client_name(engagement) if isinstance(engagement, dict) else None,
        "description": row.get("description"),
        "amount": serialise_money(row.get("amount")),
        "currency": row.get("currency"),
        "billable": bool(row.get("billable")),
        "billing_status": row.get("billing_status"),
        "invoice_id": str(row.get("invoice_id") or "") or None,
    }


def _decision_summary(
    row: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    suggestion = row.get("agent_suggestions")
    if isinstance(suggestion, list):
        suggestion = suggestion[0] if suggestion else {}
    if not isinstance(suggestion, dict):
        suggestion = {}
    latest_event = events[0] if events else {}
    return {
        "inbox_task": {
            "id": str(row["id"]),
            "kind": row.get("kind"),
            "priority": row.get("priority"),
            "title": row.get("title"),
            "status": row.get("status"),
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
        },
        "agent_suggestion": {
            "id": str(suggestion.get("id") or row.get("agent_suggestion_id") or ""),
            "agent_name": suggestion.get("agent_name"),
            "action_type": suggestion.get("action_type"),
            "status": suggestion.get("status"),
            "confidence": str(suggestion.get("confidence") or "0"),
        },
        "decision": {
            "event_id": str(latest_event.get("id") or "") or None,
            "decision_type": latest_event.get("action") or row.get("status"),
            "timestamp": str(
                latest_event.get("created_at")
                or row.get("updated_at")
                or row.get("created_at")
                or ""
            ),
            "actor_user_id": latest_event.get("actor_user_id"),
            "actor_role": latest_event.get("actor_role"),
            "before_review_summary": _payload_summary(
                latest_event.get("before_state")
                if isinstance(latest_event.get("before_state"), dict)
                else row.get("payload")
            ),
            "after_review_summary": _payload_summary(
                latest_event.get("after_state")
                if isinstance(latest_event.get("after_state"), dict)
                else suggestion.get("output_snapshot")
            ),
        },
        "source_entity": {
            "type": latest_event.get("source_type") or suggestion.get("related_entity_type"),
            "id": str(latest_event.get("source_id") or suggestion.get("related_entity_id") or "")
            or None,
        },
    }


def _payload_summary(payload: Any) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    keys = (
        "tool_name",
        "tool_input",
        "billing_arrangement",
        "engagement_name",
        "client_name",
        "period",
        "total",
        "currency",
        "journal_entry_id",
        "description",
        "status",
    )
    return {key: data.get(key) for key in keys if key in data and data.get(key) is not None}


def _journal_balance(lines: list[dict[str, Any]]) -> dict[str, Any]:
    debit = sum(_decimal(row.get("base_amount")) for row in lines if row.get("direction") == "DR")
    credit = sum(_decimal(row.get("base_amount")) for row in lines if row.get("direction") == "CR")
    return {
        "total_debits": serialise_money(debit),
        "total_credits": serialise_money(credit),
        "is_balanced": debit == credit,
    }


def _employee_name(row: dict[str, Any]) -> str:
    return f"{row.get('first_name') or ''} {row.get('last_name') or ''}".strip()


def _employee_rate(row: dict[str, Any] | None) -> Decimal:
    if not row:
        return Decimal("0")
    return _decimal(row.get("default_bill_rate"))


def _client_name(row: dict[str, Any]) -> str | None:
    client = row.get("clients")
    if isinstance(client, dict):
        return client.get("name")
    if isinstance(client, list) and client:
        first = client[0]
        if isinstance(first, dict):
            return first.get("name")
    return None


def _period_bounds(period: str | None) -> tuple[str, str]:
    if period and len(period) == 7 and period[4] == "-":
        year = int(period[:4])
        month = int(period[5:7])
    else:
        today = date.today()
        year = today.year
        month = today.month
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def _sum_hours(rows: list[dict[str, Any]]) -> Decimal:
    return sum((_decimal(row.get("hours")) for row in rows), Decimal("0"))


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _now() -> str:
    return datetime.now(UTC).isoformat()
