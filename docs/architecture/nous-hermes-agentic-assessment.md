# Nous + Hermes Agentic Framework — Assessment & Improvement Plan

Status: assessment / recommendations
Last updated: 2026-07-16
Scope: how the Hermes-backed Nous agent works today, what is solid, what is
fragile, and a phased plan to improve reliability, observability, and answer
quality while keeping Hermes as the backbone.

> Companion reference: `docs/architecture/atlas-hermes-ai-agent-architecture.md`
> (the implementation reference this assessment builds on).

## Implementation status (2026-07-16)

| Item | Status |
| --- | --- |
| P0 #1 Hermes streaming (SSE deltas, prefix-gated safety, tail-leak suppression) | ✅ done + unit-tested |
| P1 #5 HTTP resilience (split timeouts, jittered retries, circuit breaker) | ✅ done + unit-tested |
| P0 #3 provenance (real `nous:{runtime}` model) | ✅ done |
| P0 #3 Langfuse tracing of Hermes turns | ⏳ pending — needs live Hermes to verify |
| P2 #9 number-fidelity guard (wired into Basic runtime) | ✅ done + unit-tested |
| P2 #8 agent-eval harness (golden prompts + rubric + live runner) | ✅ done; 8/8 live pass on seeded tenant |
| P0 #2 server-injected `context_ref` | ⏳ pending — needs Hermes-side session mechanism |
| P1 #7 scope + replay hardening | ⏳ pending — sequence after #2 |
| P2 #10 planner / step budgets | ⏳ pending |

New modules: `app/services/circuit_breaker.py`, `app/services/number_fidelity.py`,
`app/evals/` (golden_prompts, rubric, runner). Live eval: opt-in via
`tests/eval/test_agent_eval_live.py` (`AETHOS_EVAL_LIVE=1` + token + tenant id).

## Context

Nous (formerly Atlas) is the user-facing AI agent for Aethos PS. Its advanced
runtime is **Hermes** — an external agent server that orchestrates conversation
and memory and calls back into Aethos through a private MCP tool broker. Aethos
remains the system of record; sensitive writes route to the Inbox. This document
is an assessment and a prioritized, phased plan — not a committed build. Each
phase should become its own tracked issue.

## How it works today (verified by reading the code)

Request path (`backend/app/api/v1/endpoints/chat.py`):
1. Chat endpoint loads tenant AI settings and runs `atlas_response_order`
   (default `["semantic_intent", "atlas_runtime"]`).
2. **Semantic router first** (`app/services/atlas_semantic_intent_router.py`):
   if enabled and confidence ≥ threshold, a deterministic finance answer is
   streamed and the turn ends (Hermes is bypassed for common intents).
3. Otherwise the **runtime** (`app/services/atlas_runtime.build_atlas_runtime`)
   selects `aethos_basic` (Pydantic-Graph agent in `app/agents/copilot/graph.py`)
   or `hermes_agent` (`HermesAgentRuntimeAdapter`).
4. Hermes path: `_build_hermes_instructions` mints a signed `context_ref`
   (`app/services/atlas_context.py`), embeds it in the instruction text, and calls
   `HermesClient.create_response` (`app/services/hermes_client.py`). Hermes calls
   MCP tools (`integrations/hermes/aethos_mcp_server.py`), each of which POSTs to
   the broker `POST /api/v1/atlas-tools/execute`
   (`app/api/v1/endpoints/atlas_tools.py`). The broker verifies the bearer token +
   `context_ref`, ignores any model-supplied tenant, and runs allowlisted
   read-packs / Inbox-gated write proposals.

## What's working well (keep)

- **Clean runtime seam** — `AtlasRuntime` Protocol with swappable Basic/Hermes
  adapters; runtime chosen server-side, never by the browser.
- **Strong security boundary** — broker ignores model-passed tenant/user, uses
  verified `context_ref`; writes never touch the DB directly, only Inbox paths;
  service-role calls are explicitly tenant-scoped.
- **Business-language tool design** — read-packs, not raw CRUD; a well-organised
  Hermes profile (`SOUL.md` + 7 skills) with good guardrails.
- **Graceful fallback** — Hermes failure falls back to the Basic runtime.
- **Hybrid determinism** — semantic router gives fast, deterministic answers for
  common intents and keeps controlled actions behind the Inbox.

## Findings — what can be improved (prioritized)

### P0 — reliability & UX correctness
1. **Hermes path is not streamed.** `HermesClient.create_response` is a blocking
   POST to `/v1/responses`; `HermesAgentRuntimeAdapter.stream_message` yields the
   whole answer as a single delta. Users wait for the full turn with no token
   streaming and no tool-status chips (the Basic path emits `tool_start`/
   `tool_result`; Hermes does not). Perceived latency is poor.
2. **`context_ref` is model-copied per tool call.** Every MCP tool takes
   `context_ref` as its first arg, and the instructions ask the model to "pass
   this opaque context_ref exactly as provided." Weaker models drop/mangle it →
   broker rejects → tool failures. This is the single biggest agentic-reliability
   risk and correlates with the free-model tool-calling flakiness observed in
   earlier E2E runs.
3. **No observability on Hermes turns.** No Langfuse span linking prompt → Hermes
   → tool calls → answer; no latency/token/cost; the Basic path records
   `agent_runs`/`agent_tool_invocations` but Hermes turns do not. Assistant
   messages are also persisted with a hardcoded `model="claude-sonnet-4-6"`
   (`chat.py`), so provenance is wrong.
4. **Output safety relies on brittle regex.** `_PROVIDER_ERROR_PATTERNS` /
   `_INTERNAL_OUTPUT_PATTERNS` in `atlas_runtime.py` scrub free text post-hoc —
   false negatives (new leak phrasings slip through) and false positives (a valid
   answer mentioning "timeout" or an account path gets suppressed).

### P1 — resilience, memory, provenance
5. **No HTTP resilience layer.** Both `HermesClient` and the MCP `_execute`
   create a new `httpx.AsyncClient` per call (no pooling), with no retries,
   backoff, circuit breaker, or split connect/read timeouts.
6. **Dual memory / divergence.** Hermes keeps its own conversation memory
   (`store=True`, keyed by `conversation`) while Aethos persists `chat_messages`.
   On fallback to Basic, Hermes memory is invisible → context loss
   mid-conversation.
7. **Coarse context scope + replay.** `context_ref` scope is always
   `atlas_tools:read` even for write-proposal tools, and the `nonce` is never
   checked, so a captured ref is replayable within its 15-min TTL (low risk over
   the private network, but under-enforced).

### P2 — quality & agentic capability
8. **No agent-eval harness.** Only contract/unit tests exist; nothing measures
   answer quality, tool-selection accuracy, number-fidelity, or refusal-leak
   rate. Regressions are only caught by slow E2E.
9. **No number-fidelity verification.** The rule "never invent numbers" is
   prompt-only; there is no check that monetary figures in the answer trace to a
   tool result.
10. **No multi-step planning / budgets.** No explicit planner/executor, tool-call
    budget, or step caps for complex multi-tool requests.

## Recommended implementation plan (phased)

### Phase 1 — Reliability & observability (P0)
- **Stream Hermes responses.** Add `HermesClient.stream_response` using the Hermes
  streaming/SSE endpoint; in `HermesAgentRuntimeAdapter.stream_message`, forward
  incremental `delta` frames and emit `tool_start`/`tool_result` chips as Hermes
  reports tool activity. Keep the safety classifier as a streaming-aware filter
  (buffer only until the first safe token). Reuse the SSE frame contract already
  parsed in `chat.py:stream_runtime`.
- **Make `context_ref` server-injected, not model-copied.** Bind the context to a
  per-conversation server-issued session so the broker resolves tenant/user
  without a model-passed arg (MCP server injects it via session/header). Interim:
  keep the arg but have the broker also accept context from a signed header and
  treat the model arg as optional. Removes the top failure mode. Touch:
  `atlas_context.py`, `atlas_tools.py`, `aethos_mcp_server.py`,
  `_build_hermes_instructions`.
- **Trace Hermes turns.** Wrap each Hermes turn in a Langfuse span (reuse the
  Basic path's tracing in `app/agents/base.py`); propagate a trace id to the
  broker so `agent_runs`/`agent_tool_invocations` record Hermes tool calls.
  Persist the real runtime + model in `chat.py`.
- **Harden output safety.** Keep regex as defense-in-depth; prefer Hermes output
  that separates assistant text from control/tool text; add unit tests with known
  leak/error phrasings and known false-positive strings.

### Phase 2 — Resilience & memory (P1)
- **Shared resilient HTTP.** Module-level `httpx.AsyncClient` with connection
  limits and split connect/read timeouts in `HermesClient` and MCP `_execute`;
  bounded retries with jitter for idempotent reads; a circuit breaker that
  fast-fails to the Basic fallback when Hermes is down (feed
  `operational_telemetry`).
- **Single source of conversation truth.** Pass recent Aethos `chat_messages` into
  each Hermes turn (or make Aethos memory authoritative and Hermes stateless per
  turn) so fallback to Basic is seamless. Document the memory contract.
- **Scope + replay hardening.** Add an `atlas_tools:propose_write` scope for
  write-proposal tools with a shorter TTL; optional nonce cache for replay defense
  on write scope.

### Phase 3 — Quality & agentic capability (P2)
- **Agent-eval harness (Dhruva).** Golden dataset from the Demo Guide v2 /
  prompt-library prompts with an LLM-judge rubric (tool-selection correctness,
  number-fidelity, no-leak, correct Inbox routing). Run in CI against a seeded
  tenant; track pass-rate over time. Highest-leverage quality investment; directly
  de-risks model/prompt changes.
- **Number-fidelity guard.** After a turn, cross-check monetary figures in the
  answer against the tool results that produced them; append a caveat when a
  figure has no supporting tool result.
- **Planning & budgets.** Tool-call budget and step cap per turn; optional
  planner/executor for multi-tool requests; structured output schema (assumptions
  / actions-needing-approval / next-actions) the UI can render.

## Files that will be touched (primary)

| File | Change |
| --- | --- |
| `backend/app/services/hermes_client.py` | streaming, shared client, retries |
| `backend/app/services/atlas_runtime.py` | stream forwarding, tracing, tool-status frames, circuit breaker |
| `backend/app/services/atlas_context.py` | scope classes, optional nonce store |
| `backend/app/api/v1/endpoints/atlas_tools.py` | header-injected context, trace propagation, per-tool scope |
| `backend/app/api/v1/endpoints/chat.py` | real model/runtime provenance, tool-status passthrough |
| `integrations/hermes/aethos_mcp_server.py` | server-injected context, shared client |
| `integrations/hermes/aethos-atlas-profile/` | drop the "copy the context_ref" instruction; tighten skill routing |
| `backend/app/evals/` (new) | agent-eval harness + golden dataset |

## Verification

- **Unit**: extend `test_hermes_client.py` (streaming + retries),
  `test_atlas_context.py` (new scopes/replay),
  `test_atlas_tools_api_contract.py` (header-injected context), and new
  output-safety tests. Run `cd backend && uv run pytest tests/unit -q`.
- **Live browser**: run the Copilot live specs against a Hermes-up stack and
  confirm token streaming, tool-status chips, and correct answers:
  `frontend/e2e/copilot-*-live.spec.ts`, `demo-v2-production-validation.spec.ts`.
- **Eval**: run the new eval harness against a seeded tenant; record pass-rate.
- **Observability**: confirm each Hermes turn produces a Langfuse trace with tool
  spans, latency, and token/cost, and that `agent_runs` shows Hermes activity.

## Out of scope / risks

- Renaming internal `atlas_*` identifiers (separate migration; unrelated).
- Hermes-server internals live outside this repo (`integrations/hermes` is the
  bridge/profile only); streaming depends on the Hermes API supporting SSE —
  Phase 1 must confirm the Hermes streaming contract first.
- Applying any DB/env changes to shared environments must be coordinated.
