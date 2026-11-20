"""Exercise the offline preflight against a real loopback HTTP listener."""

import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any

import pytest

pytestmark = pytest.mark.unit

_TEST_KEY = "fixture-bearer-not-a-secret"


@pytest.mark.parametrize(
    ("unauthenticated", "authenticated", "result", "calls"),
    [
        (401, "ok", 0, 2),
        (403, "ok", 0, 2),
        (200, "ok", 1, 1),
        (401, 403, 1, 2),
        (401, 302, 1, 2),
        (401, 503, 1, 2),
        (401, "wrong-text", 1, 2),
        (401, "malformed", 1, 2),
        (401, "failed", 1, 2),
        (401, "tool-call", 1, 2),
    ],
)
def test_probe_over_http(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    unauthenticated: int,
    authenticated: str | int,
    result: int,
    calls: int,
) -> None:
    from scripts import hermes_preflight

    requests: list[tuple[str, str | None, dict[str, Any]]] = []

    class FixtureHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            bearer = self.headers.get("Authorization")
            requests.append((self.path, bearer, body))
            outcome = unauthenticated if bearer is None else authenticated
            if isinstance(outcome, int):
                self.send_response(outcome)
                if outcome == 302:
                    self.send_header("Location", "/not-the-probe")
                payload = _TEST_KEY.encode()  # Simulate an upstream echo of sensitive data.
            else:
                self.send_response(200)
                nonce = body["input"].split()[-1]
                message = {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": nonce}],
                }
                response = {"status": "completed", "output": [message]}
                if outcome == "wrong-text":
                    message["content"][0]["text"] = _TEST_KEY
                if outcome == "tool-call":
                    response["output"].insert(0, {"type": "function_call"})
                if outcome == "failed":
                    response["status"] = "failed"
                payload = json.dumps(response).encode() if outcome != "malformed" else b"not JSON"
            self.end_headers()
            self.wfile.write(payload)

    with HTTPServer(("127.0.0.1", 0), FixtureHandler) as server:
        worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        worker.start()
        try:
            monkeypatch.setattr(hermes_preflight, "GATEWAY_HOST", "127.0.0.1")
            monkeypatch.setattr(hermes_preflight, "GATEWAY_PORT", server.server_port)
            monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
            monkeypatch.setenv("NO_PROXY", "")
            monkeypatch.setattr("sys.stdin", io.StringIO(_TEST_KEY + "\n"))
            assert hermes_preflight.main() == result
        finally:
            server.shutdown()
            worker.join()

    assert len(requests) == calls
    assert all(path == "/v1/responses" for path, _, _ in requests)
    assert [auth for _, auth, _ in requests] == [None, f"Bearer {_TEST_KEY}"][:calls]
    assert all(body["store"] is False and body["stream"] is False for _, _, body in requests)
    assert "conversation" not in requests[0][2]
    out, err = capsys.readouterr()
    assert _TEST_KEY not in out + err
    assert "PASS" in out if result == 0 else "FAIL" in err


@pytest.mark.parametrize("key", ["", "\n", "prefix\nsuffix", "bearer key", "x" * 4097])
def test_invalid_key_fails_before_network(
    key: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts import hermes_preflight

    def unexpected_request(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid credentials should not trigger a network request")

    monkeypatch.setattr("sys.stdin", io.StringIO(key))
    monkeypatch.setattr(hermes_preflight, "_post", unexpected_request)
    assert hermes_preflight.main() == 1
    assert "FAIL" in capsys.readouterr().err
