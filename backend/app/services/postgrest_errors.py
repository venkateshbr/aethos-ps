"""Helpers for handling PostgREST error payloads."""

from __future__ import annotations


def is_missing_table_error(exc: Exception, table_name: str) -> bool:
    payload = getattr(exc, "args", [None])[0]
    if isinstance(payload, dict):
        code = str(payload.get("code") or "")
        message = str(payload.get("message") or "")
    else:
        code = ""
        message = str(exc)
    return (code == "PGRST205" or "PGRST205" in message) and table_name in message
