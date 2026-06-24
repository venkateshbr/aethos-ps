# E2E Scenario - Ops And Security

> Public endpoint protection -> telemetry -> tenant health -> routed alerts.

## Workflow

- **Name**: ops-security
- **Entry point**: `/api/v1/auth/signup`, `/api/v1/public/invoices/{token}`,
  `/api/v1/tenants/health`, `/app/settings`.
- **Exit state**: abusive traffic fails safely; operators can inspect health
  and routed alerts without secrets or raw customer data.

## Preconditions

- Test environment can lower rate-limit thresholds.
- Distributed limiter can be enabled with `RATE_LIMIT_BACKEND=supabase` and
  migration `0089_distributed_rate_limit_events.sql`.
- Tenant admin credentials are available for tenant health.
- Agent ledger tables exist.

## Happy Path

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 1 | Public visitor | Calls signup under the configured threshold | Request proceeds normally and includes rate-limit headers. |
| 2 | Customer | Opens a valid public invoice link under the configured threshold | Public invoice lookup proceeds normally and includes rate-limit headers. |
| 3 | Internal operator | Calls tenant health as admin | Response includes runtime shape, table checks, request/background failure counters, and agent/tool/workflow failure counts. |
| 4 | Internal operator | Opens Settings -> Operational Health | Dashboard renders table checks, rate-limit backend, failure counters, and routed alerts. |

## Abuse Paths

| ID | Trigger | Expected behavior |
| --- | --- | --- |
| OPS-1 | Same client exceeds signup threshold | API returns 429 with safe `rate_limit_exceeded` detail, `Retry-After`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining`. |
| OPS-2 | Same client exceeds public invoice token threshold | API returns 429 and telemetry records the sanitized path, not the raw token. |
| OPS-3 | Tenant health called by unauthorized user | API denies access through normal RBAC. |
| OPS-4 | Agent/tool/workflow failures exist | Tenant health reports counts and tool names only; no payload snapshots, API keys, JWTs, invoice tokens, or document text. |
| OPS-5 | Distributed rate-limit backend is unavailable | Middleware falls back to in-memory limiting by default and records `rate_limit_distributed_backend` as a sanitized background failure. |
| OPS-6 | Repeated abuse or background failure crosses threshold | Tenant health includes routed alert items for the configured channel or runbook queue. |

## Audit And Telemetry

- Request failure counters are keyed by sanitized method/path/status.
- Background failures are keyed by worker name.
- Agent run, tool invocation, and workflow failure counts come from existing
  ledger tables.
- Distributed rate-limit subjects are SHA-256 hashes, never raw client
  addresses or public tokens.
- Alert route output exposes route type, channel label, and runbook link only;
  webhook URLs and credentials are never returned.
- Tenant health output must be safe to paste into support tickets.

## Executable Test Mapping

```text
backend/tests/unit/test_ops_hardening.py::test_rate_limit_middleware_returns_safe_429_shape
backend/tests/unit/test_ops_hardening.py::test_supabase_rate_limiter_uses_rpc_with_hashed_subject
backend/tests/unit/test_ops_hardening.py::test_supabase_rate_limiter_falls_back_to_memory_when_rpc_fails
backend/tests/unit/test_ops_hardening.py::test_operational_telemetry_sanitises_paths_and_counts_failures
backend/tests/unit/test_ops_hardening.py::test_tenant_health_summary_exposes_safe_operational_signals
backend/tests/unit/test_ops_hardening.py::test_tenant_health_alerts_route_without_raw_sensitive_values
backend/tests/unit/test_ops_hardening.py::test_tenant_health_endpoint_returns_admin_scoped_safe_summary
frontend/src/app/features/settings/tenant-health.component.spec.ts
```
