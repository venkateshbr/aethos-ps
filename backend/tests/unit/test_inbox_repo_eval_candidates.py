"""Unit tests for correction-to-eval candidate capture."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.repositories.inbox_repo import InboxRepository
from app.services.agent_run_ledger import stable_payload_hash


class _Query:
    def __init__(self, rows: list[dict], table_name: str) -> None:
        self.rows = rows
        self.table_name = table_name
        self.filters: list[tuple[str, object]] = []
        self.limit_value: int | None = None
        self.mode = "select"
        self.payload: dict | None = None

    def select(self, *_args: object, **_kwargs: object) -> _Query:
        return self

    def eq(self, column: str, value: object) -> _Query:
        self.filters.append((column, value))
        return self

    def limit(self, value: int) -> _Query:
        self.limit_value = value
        return self

    def insert(self, payload: dict) -> _Query:
        self.mode = "insert"
        self.payload = payload
        return self

    def upsert(self, payload: dict, **_kwargs: object) -> _Query:
        self.mode = "upsert"
        self.payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        if self.mode == "insert":
            assert self.payload is not None
            row = {**self.payload, "id": f"{self.table_name}-{len(self.rows) + 1}"}
            self.rows.append(row)
            return SimpleNamespace(data=[row])

        if self.mode == "upsert":
            assert self.payload is not None
            key = (
                self.payload["tenant_id"],
                self.payload["agent_correction_id"],
            )
            for row in self.rows:
                if (row["tenant_id"], row["agent_correction_id"]) == key:
                    row.update(self.payload)
                    return SimpleNamespace(data=[row])
            row = {**self.payload, "id": f"{self.table_name}-{len(self.rows) + 1}"}
            self.rows.append(row)
            return SimpleNamespace(data=[row])

        rows = self._filtered_rows()
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)

    def _filtered_rows(self) -> list[dict]:
        rows = self.rows
        for column, value in self.filters:
            rows = [row for row in rows if row.get(column) == value]
        return rows


class _Db:
    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables

    def table(self, name: str) -> _Query:
        return _Query(self.tables.setdefault(name, []), name)


@pytest.mark.asyncio
async def test_record_correction_creates_eval_candidate() -> None:
    db = _Db(
        {
            "agent_suggestions": [
                {
                    "id": "suggestion-1",
                    "tenant_id": "tenant-1",
                    "input_snapshot": {"message": "update rate"},
                    "output_snapshot": {"rate": "100.00"},
                }
            ],
            "agent_corrections": [],
            "agent_eval_candidates": [],
        }
    )
    repo = InboxRepository(db, tenant_id="tenant-1")  # type: ignore[arg-type]

    await repo.record_correction(
        suggestion_id="suggestion-1",
        agent_name="copilot_agent",
        action_type="copilot_update_rate_card",
        original_output={"rate": "100.00"},
        corrected_output={"rate": "125.00"},
        correction_type="edit",
        corrected_by="user-1",
    )

    correction = db.tables["agent_corrections"][0]
    candidate = db.tables["agent_eval_candidates"][0]
    assert candidate["agent_correction_id"] == correction["id"]
    assert candidate["agent_suggestion_id"] == "suggestion-1"
    assert candidate["eval_case_key"].endswith(f"correction:{correction['id']}")
    assert candidate["input_hash"] == stable_payload_hash({"message": "update rate"})
    assert candidate["original_output_hash"] == stable_payload_hash({"rate": "100.00"})
    assert candidate["corrected_output_hash"] == stable_payload_hash({"rate": "125.00"})
    assert candidate["reason"] == "human_edit"
