# Observability Standard

Production systems with AI agents must be observable end-to-end: every request, every tool call, every LLM invocation, every webhook, every background job is traceable from the user action that triggered it to the final state effect.

## Trace IDs

Every inbound request (HTTP, SSE, WebSocket, webhook, cron, message-bus consumer) gets a trace ID:

- Generated at the edge if not present.
- Propagated to every downstream service via HTTP header (`traceparent` per W3C Trace Context).
- Attached to every log line, every database span, every external call, every LLM call.
- Echoed back to the client (response header) so support staff can pivot from a customer report to the trace.

Background jobs inherit the trace ID of the request that enqueued them.

## Structured logs

Logs are JSON, one record per event, with at minimum:

- `timestamp` (ISO 8601, UTC, microseconds).
- `level` (debug, info, warn, error).
- `service`, `version`, `env`.
- `trace_id`, `span_id`, `parent_span_id`.
- `tenant_id`, `user_id` (where applicable).
- `event` (a short kebab-case identifier, e.g., `invoice.sent`, `stripe.webhook.received`).
- `payload` — bounded, scrubbed (no secrets, no raw PII, no tokens, no card numbers, no API keys).

Logs are never the place for secrets or raw PII. Mask at the source.

## LLM / agent traces

Every LLM call gets a trace span with:

- Agent name and version.
- Prompt version (hash + label).
- Model name and version.
- Tool list passed (names, not full schemas).
- Token usage (input, output, cached if applicable).
- Latency (TTFT, total).
- Cost (in base currency, computed from token count × model rate).
- Output: structured fields if structured, full text otherwise — **masked** for PII before being sent to the observability backend.
- Score (when an eval or scorer attaches one).

Each tool call inside an agent run is its own child span:

- Tool name, input, output, duration, error if any.
- Server tools (executed by the model provider) are distinguished from client tools (executed in your code).

## HITL trace coupling

When an agent output triggers a HITL task, the trace ID of the LLM call is stored on the `hitl_task` row. When the human approves/edits/rejects, the decision event references the original trace. This is what makes the correction loop traceable later.

## Webhooks

Every inbound webhook:

- Logs receipt with provider event ID, signature verification result, and trace ID.
- Persists the raw payload (signed envelope) in a `webhook_events` audit table for ≥ 30 days.
- Replays are detected via idempotency key (provider event ID); replays are logged but do not re-effect.

Every outbound webhook:

- Includes a trace ID in the payload or signed envelope.
- Records delivery attempts and statuses.

## Metrics

Per-service:

- **Latency** — p50, p95, p99 per endpoint.
- **Error rate** — non-2xx per endpoint.
- **Throughput** — requests per minute.

Per-agent:

- **Run rate** — agent runs per minute.
- **Token consumption** — tokens per minute, broken down by model.
- **Cost** — currency per minute.
- **Confidence histogram** — distribution of `output.confidence` over time.
- **Approval rate** — approved / total decided suggestions (rolling 30 days).
- **Edit rate** — approved-with-edits / approved.

Per-business event:

- Counts of `invoice.sent`, `payment.received`, `bill.posted`, etc.
- Reconciliation deltas (e.g., Stripe payments seen vs. payments recorded).

## SLOs

For each user-facing surface define:

- **Availability SLO** — e.g., 99.5% of `/copilot/chat/stream` requests return a first token within 3s.
- **Correctness SLO** — e.g., 99.9% of accepted invoices balance.
- **Eval SLO** — average eval score on the locked dataset stays ≥ threshold; deviation is an alert.

Burn-rate alerts page the on-call when the error budget is being consumed faster than allowed.

## Health endpoints

Every service exposes:

- `GET /health` — basic liveness; no auth required.
- `GET /health/ready` — readiness (DB reachable, queue reachable, secret store decryptable); no auth required.
- `GET /admin/health` — detailed health with provider statuses; admin auth required, no secrets in output.

Health endpoints must not expose configuration values, secrets, or sensitive customer counts.

## Alert routing

Alerts have three tiers:

- **Page** — wakes the on-call. Reserved for: prod down, payments broken, security incident, SLO burn-rate breach.
- **Ticket** — opens an issue. For: SLO degradation, eval-score drift, drift in correction rate, sustained queue lag.
- **Log** — recorded but not actively routed. For: low-priority anomalies, expected one-off failures.

Every alert links to a runbook entry.

## Sampling and retention

- Traces: 100% capture of error traces; 10% sampling of successful traces (project-configurable).
- LLM traces: 100% capture in the AI observability backend (these are the eval substrate; never sample them out).
- Logs: 30-day hot, 1-year cold, project-configurable.
- Audit events (financial, auth, admin): retained per legal requirement.

## What never goes into observability

- Passwords, OTPs, recovery codes.
- API keys, OAuth tokens, webhook signing secrets.
- Full card numbers, CVCs, bank account numbers.
- Raw PII unless redaction is explicitly disabled with a documented business reason.
- Customer-uploaded document contents in full — store the trace metadata, the storage URL, and the redacted excerpts only.

If a secret leaks into a log line, the secret is rotated immediately and the leak fixed at the source.

## References

- W3C Trace Context — `traceparent` header propagation.
- Langfuse — LLM traces, scores, prompt versions, datasets.
- Anthropic tool use — `tool_use` and `tool_result` blocks emit naturally as child spans.
- See also: [security-review.md](security-review.md) (secret-handling), [agent-eval-standard.md](agent-eval-standard.md).
