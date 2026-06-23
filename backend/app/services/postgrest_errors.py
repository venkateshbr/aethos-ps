"""Helpers for handling PostgREST error payloads."""

from __future__ import annotations

from collections.abc import Iterable


def is_missing_table_error(exc: Exception, table_name: str) -> bool:
    code, message = _postgrest_error_parts(exc)
    return (code == "PGRST205" or "PGRST205" in message) and table_name in message


def is_missing_column_error(exc: Exception, column_names: str | Iterable[str]) -> bool:
    code, message = _postgrest_error_parts(exc)
    columns = {column_names} if isinstance(column_names, str) else set(column_names)
    return (code == "PGRST204" or "PGRST204" in message) and any(
        column_name in message for column_name in columns
    )


def _postgrest_error_parts(exc: Exception) -> tuple[str, str]:
    payload = getattr(exc, "args", [None])[0]
    if isinstance(payload, dict):
        code = str(payload.get("code") or "")
        message = str(payload.get("message") or "")
    else:
        code = ""
        message = str(exc)
    return code, message
