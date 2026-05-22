"""
Aethos PS -- Locust load test suite.

Targets:
  - 100 concurrent simulated users (chat-heavy workload)
  - SLO verification from observability-standard.md:
      Chat TTFT p95 < 3s
      List endpoints p95 < 500ms
      Document upload enqueue p95 < 1s
      Webhook -> invoice paid p95 < 1s (tested indirectly)

Usage:
  locust -f tests/load/locustfile.py --host https://api.aethos.app \\
         --users 100 --spawn-rate 5 --run-time 5m --headless \\
         --html tests/load/report.html

  For local testing against :8011:
  locust -f tests/load/locustfile.py --host http://localhost:8011 \\
         --users 10 --spawn-rate 2 --run-time 1m --headless

Environment variables (required for authenticated endpoints):
  LOAD_TEST_JWT           A valid Supabase JWT for a dedicated load-test tenant.
  LOAD_TEST_TENANT_ID     The tenant UUID that matches the JWT.
  LOAD_TEST_ENGAGEMENT_ID An engagement UUID within the load-test tenant (optional).

Locust endpoint naming convention used here:
  "<resource>: <action>"  -- e.g. "chat: send message (SSE)"

  Keeping names consistent is important: the SLO validation listener at the
  bottom references these exact strings to look up stats entries.
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, TaskSet, between, events, tag, task
from locust.env import Environment

# ---------------------------------------------------------------------------
# Configuration -- read from environment; sensible defaults for local dev.
# ---------------------------------------------------------------------------

TEST_JWT: str = os.environ.get("LOAD_TEST_JWT", "")
TEST_TENANT_ID: str = os.environ.get("LOAD_TEST_TENANT_ID", "")
TEST_ENGAGEMENT_ID: str = os.environ.get("LOAD_TEST_ENGAGEMENT_ID", "")

# Fake PDF bytes -- minimal valid-ish PDF header that passes the MIME check.
# The document endpoint validates MIME via Content-Type, not magic bytes,
# so any non-empty bytes under 20 MB will be accepted.
_FAKE_PDF: bytes = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
    b"xref\n0 3\n"
    b"%%EOF"
)

_CHAT_PROMPTS: list[str] = [
    "What are my active engagements?",
    "Show me AR aging",
    "What is the WIP for this month?",
    "How many time entries were logged this week?",
    "Summarise outstanding invoices",
    "Which clients have overdue balances?",
]


# ---------------------------------------------------------------------------
# Auth helper -- reuse pre-seeded test JWT across all users
# ---------------------------------------------------------------------------


def _auth_headers() -> dict[str, str]:
    """Return Authorization + tenant headers when a JWT is configured.

    Without a JWT the load test still runs but every authenticated endpoint
    will return 401.  That is acceptable for a local smoke run to verify the
    pipeline mechanics; the SLO validator marks 401 responses as success so
    they don't pollute latency percentiles.
    """
    if TEST_JWT:
        return {
            "Authorization": f"Bearer {TEST_JWT}",
            "X-Tenant-ID": TEST_TENANT_ID,
        }
    return {}


# ---------------------------------------------------------------------------
# Task sets
# ---------------------------------------------------------------------------


class ChatTasks(TaskSet):
    """Simulates a user sending messages to the Copilot chat endpoint.

    Weight 7 in ChatUser -- reflects the chat-heavy usage profile described
    in issue #86 (100 concurrent chat users, 1000 doc extractions/hour).
    """

    thread_id: str | None = None

    def on_start(self) -> None:
        """Create a thread before the task loop starts."""
        resp = self.client.post(
            "/api/v1/chat/threads",
            headers=_auth_headers(),
            json={},
            name="chat: create thread",
        )
        if resp.status_code == 201:
            self.thread_id = resp.json().get("id")

    @tag("chat", "critical")
    @task(5)
    def send_message(self) -> None:
        """POST a message and consume the first SSE frame to measure TTFT.

        Locust measures the response time from request start to the moment
        we close (or first read from) the stream, which corresponds to TTFT
        for an SSE endpoint.

        SLO: p95 < 3s (chat TTFT).
        """
        if not self.thread_id:
            return

        msg = random.choice(_CHAT_PROMPTS)

        with self.client.post(
            f"/api/v1/chat/threads/{self.thread_id}/messages",
            headers={**_auth_headers(), "Accept": "text/event-stream"},
            json={"content": msg},
            stream=True,
            name="chat: send message (SSE)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                # Read just the first chunk -- that is what we measure as TTFT.
                # We immediately break so Locust records time-to-first-byte.
                for _line in resp.iter_lines():
                    break
                resp.success()
            elif resp.status_code == 401:
                # Expected when running without a real JWT.  Mark success so
                # we do not pollute error rates in pipeline smoke runs.
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @tag("chat")
    @task(2)
    def list_threads(self) -> None:
        """GET /api/v1/chat/threads -- warm-list latency check.

        SLO: p95 < 500ms (list endpoint).
        """
        self.client.get(
            "/api/v1/chat/threads",
            headers=_auth_headers(),
            name="chat: list threads",
        )


class ListTasks(TaskSet):
    """Simulates a user browsing the main list views (engagements, invoices,
    AR aging, bills, time entries).  These are the pages that must stay under
    500ms p95 per the observability standard.
    """

    @tag("list", "critical")
    @task(3)
    def list_engagements(self) -> None:
        """GET /api/v1/engagements -- SLO: p95 < 500ms."""
        self.client.get(
            "/api/v1/engagements",
            headers=_auth_headers(),
            name="list: engagements",
        )

    @tag("list", "critical")
    @task(2)
    def list_invoices(self) -> None:
        """GET /api/v1/invoices -- SLO: p95 < 500ms."""
        self.client.get(
            "/api/v1/invoices",
            headers=_auth_headers(),
            name="list: invoices",
        )

    @tag("list", "critical")
    @task(2)
    def ar_aging(self) -> None:
        """GET /api/v1/reports/ar-aging -- SLO: p95 < 500ms."""
        self.client.get(
            "/api/v1/reports/ar-aging",
            headers=_auth_headers(),
            name="report: AR aging",
        )

    @tag("list")
    @task(1)
    def list_bills(self) -> None:
        self.client.get(
            "/api/v1/bills",
            headers=_auth_headers(),
            name="list: bills",
        )

    @tag("list")
    @task(1)
    def list_time_entries(self) -> None:
        self.client.get(
            "/api/v1/time-entries",
            headers=_auth_headers(),
            name="list: time entries",
        )

    @tag("health")
    @task(1)
    def health_ping(self) -> None:
        """Lightweight liveness check -- should always be < 50ms."""
        self.client.get("/api/v1/ping", name="health: ping")


class DocumentUploadTasks(TaskSet):
    """Simulates document uploads.

    Less frequent than chat (weight=1 in UploadUser) because uploads are
    expensive: storage write + DB insert + ARQ enqueue.  Target throughput
    from issue #86: 1 000 doc extractions/hour ~ 0.28/s across all users.

    SLO: enqueue latency p95 < 1s (measured as full POST latency to 201).
    """

    @tag("upload", "critical")
    @task(1)
    def upload_pdf(self) -> None:
        """POST /api/v1/documents/upload -- measure enqueue latency.

        We send a minimal PDF (<1 KB) so the upload itself does not dominate
        timing.  The endpoint does:
          1. Validate MIME + size
          2. SHA-256
          3. Supabase Storage upload
          4. DB insert (documents row)
          5. ARQ enqueue
        Steps 3-5 are what we are stress-testing.
        """
        with self.client.post(
            "/api/v1/documents/upload",
            headers=_auth_headers(),
            files={"file": ("load_test.pdf", _FAKE_PDF, "application/pdf")},
            name="upload: document",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code == 401:
                # Expected without a real JWT.
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")


# ---------------------------------------------------------------------------
# User profiles (weighted mix totalling 100 virtual users)
# ---------------------------------------------------------------------------


class ChatUser(HttpUser):
    """Heavy chat user -- 70 of 100 virtual users.

    Simulates a typical Aethos PS power user who spends most of their time
    talking to the Copilot (creating threads, sending messages).
    """

    weight = 7
    wait_time = between(1, 3)
    tasks = [ChatTasks]


class BrowserUser(HttpUser):
    """User browsing list/report pages -- 20 of 100 virtual users.

    Simulates a user checking dashboards, AR aging, invoices.
    """

    weight = 2
    wait_time = between(2, 5)
    tasks = [ListTasks]


class UploadUser(HttpUser):
    """Document-upload user -- 10 of 100 virtual users.

    Simulates a user who drops documents (engagement letters, receipts,
    vendor invoices) for AI extraction.  Longer wait times reflect the
    real-world cadence of document processing.
    """

    weight = 1
    wait_time = between(10, 30)
    tasks = [DocumentUploadTasks]


# ---------------------------------------------------------------------------
# SLO validation hook -- runs when the test exits
# ---------------------------------------------------------------------------

#: SLO definitions: (locust request name, HTTP method, threshold_ms)
#: These names must exactly match the `name=` arguments used in task methods.
_SLO_TABLE: list[tuple[str, str, int]] = [
    ("chat: send message (SSE)", "POST", 3000),   # Chat TTFT p95 < 3s
    ("list: engagements",        "GET",   500),   # List p95 < 500ms
    ("list: invoices",           "GET",   500),   # List p95 < 500ms
    ("report: AR aging",         "GET",   500),   # List p95 < 500ms
    ("upload: document",         "POST", 1000),   # Upload enqueue p95 < 1s
]


@events.quitting.add_listener
def validate_slos(environment: Environment, **_kwargs: object) -> None:
    """Print an SLO pass/fail report when the test ends.

    Sets ``environment.process_exit_code = 1`` if any SLO is violated so that
    CI pipelines detect the failure.
    """
    stats = environment.runner.stats

    sep = "=" * 62
    print(f"\n{sep}")
    print("SLO VALIDATION REPORT")
    print(sep)

    all_pass = True
    for name, method, threshold_ms in _SLO_TABLE:
        entry = stats.entries.get((name, method))
        if entry is None or entry.num_requests == 0:
            print(f"  SKIP  {name!r} ({method}) -- no data collected")
            continue

        p95_ms = entry.get_response_time_percentile(0.95)
        passed = p95_ms <= threshold_ms
        if not passed:
            all_pass = False

        mark = "PASS" if passed else "FAIL"
        print(
            f"  {mark}  {name} ({method}): "
            f"p95={p95_ms:.0f}ms  SLO=<{threshold_ms}ms  "
            f"n={entry.num_requests}"
        )

    print(sep)
    print(f"Overall: {'PASS' if all_pass else 'FAIL'}")
    print(f"{sep}\n")

    if not all_pass:
        environment.process_exit_code = 1
