"""Probe the staged Hostinger Hermes route without an ERP app or a fallback."""

from __future__ import annotations

import json
import re
import secrets
import socket
import sys
from http.client import HTTPConnection, HTTPException

GATEWAY_HOST = "host.docker.internal"
GATEWAY_ADDRESS = "172.31.254.1"
GATEWAY_PORT = 8643
_MAX_RESPONSE_BYTES = 64 * 1024


class PreflightFailure(Exception):
    """A known failure described by a static, redacted message."""


def _post(payload: bytes, key: str | None) -> tuple[int, bytes]:
    headers = {
        "Host": f"{GATEWAY_HOST}:{GATEWAY_PORT}",
        "Content-Type": "application/json",
    }
    if key is not None:
        headers["Authorization"] = f"Bearer {key}"
    # Direct socket: no environment proxies, retries, redirect or alternate route.
    conn = HTTPConnection(GATEWAY_ADDRESS, GATEWAY_PORT, timeout=90)
    try:
        conn.request("POST", "/v1/responses", body=payload, headers=headers)
        response = conn.getresponse()
        if key is None or response.status != 200:
            return response.status, b""
        return response.status, response.read(_MAX_RESPONSE_BYTES + 1)
    finally:
        conn.close()


def _check_response(payload: bytes, nonce: str) -> None:
    if len(payload) > _MAX_RESPONSE_BYTES:
        raise PreflightFailure("response exceeded the preflight size limit")
    data = json.loads(payload)
    if not isinstance(data, dict) or data.get("status") != "completed":
        raise PreflightFailure("no completed inference response")
    output = data.get("output")
    if not isinstance(output, list) or not output:
        raise PreflightFailure("no assistant output")
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") not in {"message", "reasoning"}:
            raise PreflightFailure("unexpected response item (tools are not part of this probe)")
        if item["type"] == "reasoning":
            continue
        content = item.get("content")
        if item.get("role") != "assistant" or not isinstance(content, list):
            raise PreflightFailure("expected an assistant message")
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text":
                raise PreflightFailure("expected assistant output text")
            text = part.get("text")
            if not isinstance(text, str):
                raise PreflightFailure("expected assistant output text")
            texts.append(text)
    if "".join(texts).strip() != nonce:
        raise PreflightFailure("assistant output did not match the one-time challenge")


def main() -> int:
    try:
        key = sys.stdin.read(4098).removesuffix("\n")
        if not re.fullmatch(r"[A-Za-z0-9_./+~=-]{1,4096}", key):
            raise PreflightFailure("expected one bearer key on stdin")
        if socket.gethostbyname(GATEWAY_HOST) != GATEWAY_ADDRESS:
            raise PreflightFailure("gateway alias does not match the dedicated bridge address")

        nonce = "AETHOS_PREFLIGHT_" + secrets.token_hex(8)
        payload = json.dumps(
            {
                "model": "Aethos Nous",
                "input": f"Return only this exact string with no punctuation: {nonce}",
                "instructions": "Network preflight. Do not use tools or access tenant data.",
                "store": False,
                "stream": False,
            }
        ).encode()
        status, _ = _post(payload, None)
        if status not in (401, 403):
            raise PreflightFailure("the inference endpoint did not reject a missing bearer key")
        status, body = _post(payload, key)
        if status != 200:
            raise PreflightFailure(f"authenticated inference returned HTTP {status}")
        _check_response(body, nonce)
    except PreflightFailure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    except (OSError, HTTPException, ValueError, TypeError):
        # Never print response bodies, request headers, or exceptions carrying them.
        print("FAIL: invalid response or private gateway connection failure", file=sys.stderr)
        return 1
    print("PASS: private Hermes rejected anonymous inference and completed authenticated inference")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
