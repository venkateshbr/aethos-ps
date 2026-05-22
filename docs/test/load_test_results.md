# Load Test Results

## SLO baseline targets

From `observability-standard.md`:

| Metric | SLO |
|---|---|
| Chat TTFT p95 | < 3s |
| List endpoints p95 | < 500ms |
| Document upload enqueue p95 | < 1s |
| Webhook -> invoice paid p95 | < 1s |

## Results log

| Date | Users | Duration | Chat p95 | Engagements p95 | Invoices p95 | AR Aging p95 | Upload p95 | SLOs |
|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | 100 | 5m | -- | -- | -- | -- | -- | Pending |

## Pre-beta run

**Status**: Pending -- requires production Cloud Run deployment and load-test tenant JWT.

Run command:

```bash
export LOAD_TEST_JWT="eyJ..."
export LOAD_TEST_TENANT_ID="uuid..."

locust -f tests/load/locustfile.py \
  --host https://api.aethos.app \
  --users 100 --spawn-rate 5 \
  --run-time 5m --headless \
  --html tests/load/results/pre-beta.html
```

After the run:
1. Copy the HTML report: `cp tests/load/report.html tests/load/results/pre-beta.html`
2. Record the p95 values in the Results log table above.
3. If any SLO fails, file a `type:bug` issue tagged `priority:high, area:infra`.

## Runbook

See `tests/load/README.md` for full usage instructions.
