"""Operational telemetry counters and safe tenant health summaries."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from app.core.config import settings
from supabase import Client


@dataclass(frozen=True)
class RequestFailureEvent:
    method: str
    path: str
    status_code: int

    def key(self) -> tuple[str, str, int]:
        return (self.method, self.path, self.status_code)


class OperationalTelemetry:
    """In-process counters for request/background failure telemetry."""

    def __init__(self) -> None:
        self._request_failures: Counter[tuple[str, str, int]] = Counter()
        self._background_failures: Counter[str] = Counter()
        self._lock = Lock()

    def record_request_failure(self, *, method: str, path: str, status_code: int) -> None:
        if status_code < 400:
            return
        event = RequestFailureEvent(
            method=method.upper(),
            path=sanitise_path(path),
            status_code=status_code,
        )
        with self._lock:
            self._request_failures[event.key()] += 1

    def record_background_failure(self, worker_name: str) -> None:
        with self._lock:
            self._background_failures[sanitise_name(worker_name)] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            request_failures = [
                {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "count": count,
                }
                for (method, path, status_code), count in self._request_failures.items()
            ]
            background_failures = [
                {"worker_name": worker_name, "count": count}
                for worker_name, count in self._background_failures.items()
            ]
        request_failures.sort(key=lambda row: (-int(row["count"]), row["path"]))
        background_failures.sort(key=lambda row: (-int(row["count"]), row["worker_name"]))
        return {
            "request_failures": request_failures[:25],
            "background_failures": background_failures[:25],
        }

    def reset(self) -> None:
        with self._lock:
            self._request_failures.clear()
            self._background_failures.clear()


telemetry = OperationalTelemetry()


class TenantHealthService:
    """Build a safe operator-facing tenant health summary."""

    _TABLE_CHECKS = (
        "tenants",
        "tenant_users",
        "agent_runs",
        "agent_tool_invocations",
        "agent_workflow_runs",
        "accounting_close_tasks",
        "accounting_close_overrides",
        "financial_events",
    )

    def __init__(self, db: Client, tenant_id: str) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def summary(self) -> dict[str, Any]:
        table_checks = self._table_checks()
        agent_counts = self._agent_failure_counts()
        runtime = {
            "environment": settings.environment,
            "debug": settings.debug,
            "queue_configured": bool(settings.database_url),
            "queue_required": bool(settings.queue_required),
            "extraction_mode": settings.extraction_mode,
        }
        degraded = (
            any(check["status"] != "ok" for check in table_checks)
            or agent_counts["failed_agent_runs_24h"] > 0
            or agent_counts["failed_tool_invocations_24h"] > 0
            or agent_counts["failed_workflow_runs_24h"] > 0
        )
        return {
            "status": "degraded" if degraded else "ok",
            "tenant_id": self.tenant_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "runtime": runtime,
            "checks": {"tables": table_checks},
            "telemetry": {
                **telemetry.snapshot(),
                **agent_counts,
            },
        }

    def _table_checks(self) -> list[dict[str, str]]:
        checks: list[dict[str, str]] = []
        for table in self._TABLE_CHECKS:
            try:
                query = self.db.table(table).select("id")
                if table == "tenants":
                    query = query.eq("id", self.tenant_id)
                else:
                    query = query.eq("tenant_id", self.tenant_id)
                query.limit(1).execute()
                checks.append({"name": table, "status": "ok"})
            except Exception as exc:
                checks.append(
                    {
                        "name": table,
                        "status": "error",
                        "message": type(exc).__name__,
                    }
                )
        return checks

    def _agent_failure_counts(self) -> dict[str, Any]:
        since = (datetime.now(UTC) - timedelta(hours=24)).replace(microsecond=0).isoformat()
        return {
            "failed_agent_runs_24h": len(
                self._rows(
                    "agent_runs",
                    "id, agent_name, status, created_at",
                    status_value="failed",
                )
            ),
            "failed_tool_invocations_24h": len(
                self._rows(
                    "agent_tool_invocations",
                    "id, tool_name, status, created_at",
                    status_value="failed",
                )
            ),
            "failed_workflow_runs_24h": len(
                self._rows(
                    "agent_workflow_runs",
                    "id, workflow_name, status, created_at",
                    status_value="failed",
                )
            ),
            "failed_tools_by_name_24h": self._failed_tools_by_name(),
            "window_start": since,
        }

    def _failed_tools_by_name(self) -> list[dict[str, Any]]:
        counts: defaultdict[str, int] = defaultdict(int)
        for row in self._rows(
            "agent_tool_invocations",
            "id, tool_name, status, created_at",
            status_value="failed",
        ):
            counts[sanitise_name(str(row.get("tool_name") or "unknown"))] += 1
        return [
            {"tool_name": tool_name, "count": count}
            for tool_name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ][:25]

    def _rows(self, table: str, columns: str, *, status_value: str) -> list[dict[str, Any]]:
        try:
            result = (
                self.db.table(table)
                .select(columns)
                .eq("tenant_id", self.tenant_id)
                .eq("status", status_value)
                .gte("created_at", (datetime.now(UTC) - timedelta(hours=24)).isoformat())
                .execute()
            )
        except Exception:
            return []
        return result.data or []


def sanitise_path(path: str) -> str:
    """Remove high-cardinality or sensitive path fragments from telemetry."""
    parts = [part for part in path.split("/") if part]
    normalised: list[str] = []
    for part in parts:
        if len(part) >= 24 or _looks_like_uuid(part):
            normalised.append("{id}")
        elif len(part) >= 16 and any(ch.isdigit() for ch in part):
            normalised.append("{token}")
        else:
            normalised.append(part)
    return "/" + "/".join(normalised)


def sanitise_name(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-", "."})[:80] or "unknown"


def _looks_like_uuid(value: str) -> bool:
    return len(value) == 36 and value.count("-") == 4
