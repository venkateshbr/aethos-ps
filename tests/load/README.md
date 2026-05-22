# Load Tests -- Aethos PS

Locust-based load test suite targeting the Aethos PS API.

## SLO Targets

| Endpoint | Locust name | SLO |
|---|---|---|
| Chat TTFT | `chat: send message (SSE)` | p95 < 3s |
| List engagements | `list: engagements` | p95 < 500ms |
| List invoices | `list: invoices` | p95 < 500ms |
| AR Aging report | `report: AR aging` | p95 < 500ms |
| Document upload enqueue | `upload: document` | p95 < 1s |

## User mix (100 virtual users)

| Class | Weight | Behaviour |
|---|---|---|
| `ChatUser` | 7 (70 VU) | Creates thread, sends messages, reads SSE stream |
| `BrowserUser` | 2 (20 VU) | Browses engagements, invoices, AR aging |
| `UploadUser` | 1 (10 VU) | Uploads small PDFs (engagement letters, receipts) |

## Prerequisites

```bash
pip install -r tests/load/requirements.txt
```

## Run against production

```bash
export LOAD_TEST_JWT="eyJ..."          # Valid Supabase JWT for the load-test tenant
export LOAD_TEST_TENANT_ID="uuid..."   # The matching tenant UUID

locust -f tests/load/locustfile.py \
  --host https://api.aethos.app \
  --users 100 --spawn-rate 5 \
  --run-time 5m --headless \
  --html tests/load/results/$(date +%Y-%m-%d).html
```

The `--headless` flag causes Locust to print the SLO validation report on exit
and return exit code 1 if any SLO is breached.

## Run against local dev

```bash
# Start backend first:
#   cd backend && uv run uvicorn app.main:app --port 8011

locust -f tests/load/locustfile.py \
  --host http://localhost:8011 \
  --users 10 --spawn-rate 2 \
  --run-time 1m --headless
```

Local runs without `LOAD_TEST_JWT` will receive 401 responses on
authenticated endpoints.  The test marks 401s as success to avoid polluting
error rates during pipeline smoke runs.

## Interactive UI

Omit `--headless` to open the Locust web UI at http://localhost:8089.

## CI integration

The load test is NOT run on every PR -- it runs on-demand before major releases.

To enable scheduled runs, add these GitHub secrets:
- `LOAD_TEST_JWT` -- JWT for the dedicated load-test tenant
- `LOAD_TEST_TENANT_ID` -- UUID of the load-test tenant

Then trigger manually via `gh workflow run load-test.yml` or add a cron schedule.

## Saving results

After each run, save the HTML report:

```bash
cp tests/load/report.html "tests/load/results/$(date +%Y-%m-%d).html"
```

Record the summary metrics in `docs/test/load_test_results.md`.
