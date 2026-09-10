# Aethos Nous on Hermes — Runtime and Learning Operations

> **Audience**: operators, SRE (Sthira), backend (Karya), analytics (Dhruva), security (Prahari).
> **User-facing counterpart**: [`docs/user-guide/platform-user-guide.md`](../user-guide/platform-user-guide.md) §3.
> **Design reference**: [`docs/architecture/atlas-hermes-ai-agent-architecture.md`](../architecture/atlas-hermes-ai-agent-architecture.md).
> **Created**: 2026-09-03 from the Hermes runtime and self-learning review (issues #529–#536).
> **Status of this document**: describes what the code does today, including the parts that do **not** work yet. Every gap is labelled with its issue number. Do not present a gap as shipped behaviour.

---

## 1. What "Nous on Hermes" actually is

Nous is the product-facing AI interface. A chat turn passes through up to three stages:

```
user prompt (POST /api/v1/chat/threads/{id}/messages, SSE)
  │
  ├─1─ semantic intent router          app/services/atlas_semantic_intent_router.py
  │     39 static intents, confidence >= 0.72 (tenant-configurable)
  │     hit → deterministic responder / read pack → answer returned, STAGE 2 AND 3 NEVER RUN
  │
  ├─2─ configured runtime              app/services/atlas_runtime.py
  │     aethos_basic  → CopilotAgent tool loop      app/agents/copilot/graph.py
  │     hermes_agent  → shared Hermes aethos-nous profile app/services/hermes_client.py
  │
  └─3─ fallback                        hermes_agent → aethos_basic when Hermes errors,
        circuit breaker opens, or the answer fails the output-safety filter
```

Hermes never touches the database. It calls back into Aethos through the **tool broker**:

```
Shared Hermes profile ──MCP──> integrations/hermes/aethos_mcp_server.py
                           (28 @mcp.tool wrappers, each takes a context token)
                              │  Bearer AETHOS_HERMES_TOOL_TOKEN
                              ▼
                POST /api/v1/atlas-tools/execute      app/api/v1/endpoints/atlas_tools.py
                  → resolves tenant/user/thread from atlas_tool_sessions (cts_… token)
                  → dispatches to Aethos services (read packs) or HITL writers
```

**Two consequences operators must internalise:**

1. **The router short-circuits Hermes.** Most demo and prompt-library questions match one of the 39 intents and are answered by deterministic code, not by Hermes. "We migrated to Hermes" is only true for the long tail unless the router is reordered or disabled (#530).
2. **Hermes authenticates as a host profile, not as a user.** The broker verifies the shared tool token and resolves the tenant from a short-lived session token, but today it does **not** check the calling user's privileges, and two write tools bypass the agent tool policy entirely (#529). Until that lands, treat Hermes access as equivalent to "any authenticated user of the tenant can read anything the read packs expose".

---

## 2. Configuration reference

### Runtime selection

| Setting | Where | Default | Notes |
|---|---|---|---|
| `ATLAS_AI_RUNTIME` | env / `app/core/config.py:114` | `aethos_basic` | `aethos_basic` or `hermes_agent`. Compose passes it through (`docker-compose.hostinger.yml:63`). |
| `tenant_ai_settings.atlas_runtime` | DB, Settings → AI Inference Settings | unset → env default | Per-tenant override resolved by `app/services/ai_settings_service.py`. |
| `atlas_response_order` | `tenant_ai_settings` | `["semantic_intent","atlas_runtime"]` | Put `atlas_runtime` first (or drop `semantic_intent`) to send everything to Hermes. |
| `atlas_semantic_threshold` | `tenant_ai_settings` | `0.72` | Higher = fewer deterministic answers, more Hermes. |
| `ATLAS_HERMES_FALLBACK_TO_BASIC` | env | `true` | Keep `true` in production; it hides Hermes outages, so pair it with the verification in §4. |

### Hermes connection

| Variable | Container | Purpose |
|---|---|---|
| `ATLAS_HERMES_API_BASE_URL` | api | Default `http://host.docker.internal:8643`, the host-gateway route to the shared `aethos-nous` Hermes profile. |
| `ATLAS_HERMES_API_SERVER_KEY` | api | Must equal `API_SERVER_KEY`/`HERMES_API_SERVER_KEY` for the `aethos-nous` Hermes profile. **If empty the client sends no auth header instead of failing** (#536). |
| `ATLAS_HERMES_TIMEOUT_SECONDS` | api | Read timeout, prod 90 s. Connect 5 s / write 10 s / pool 5 s are fixed. |
| `AETHOS_HERMES_TOOL_TOKEN` | api **and** `aethos-nous` profile | Shared secret for the tool broker. Both must match or every tool call 401s. |
| `ATLAS_CONTEXT_SIGNING_SECRET` | api | Signs the legacy `ctx_…` context ref (fallback when session minting fails). |
| `ATLAS_HIDE_TOOL_EVENTS` | api | `true` hides tool chips from users (#480). Hermes emits none today anyway (#532). |
| `OPENROUTER_API_KEY` / dedicated profile provider key | `aethos-nous` profile process | Hermes calls the model itself; this key is **not** the API's key path, so Hermes traffic never passes through Langfuse (#532). |
| `COMPOSE_PROFILES` | deploy workflow | Use `worker`; there is no longer a `hermes` Compose profile in production. |

These variables are represented in `backend/.env.example`; production secrets
must still be supplied through the VPS environment/secrets workflow.

### Hermes profile (`integrations/hermes/aethos-atlas-profile/`)

| File | Role |
|---|---|
| `SOUL.md` | Persona and hard guardrails: Aethos is the system of record; never invent financial data; never reveal tool names, arguments, outputs, traces or prompts; sensitive actions route to Inbox. |
| `config.yaml` | `model.default: anthropic/claude-haiku-4.5` (**hardcoded — Hermes does not substitute `${VARS}` here**), `max_tokens: 2048`, `provider_routing.data_collection: deny`, tool-loop hard stops (5 exact failures / 5 no-progress), 7 auto-load skills, and the MCP server registration with the 28-tool allowlist. |
| `skills/*/SKILL.md` | Seven workflow skills: finance-ops-manager, engagement-letter-intake, o2c-invoice-to-cash, p2p-procure-to-pay, r2r-close-controller, collections, audit-evidence. Each dictates which read pack to call first and which facts the answer must contain. |
| `mcp.json` | Vestigial (`{"mcpServers": {}}`); real registration lives in `config.yaml`. |

The profile remains **versioned in this repo**, but production now installs it into the shared host Hermes instance with `scripts/deploy/install-aethos-hermes-profile.sh`. Changing a prompt requires a reviewed repo change and profile install/restart, not a new Aethos Hermes image rebuild (#535).

---

## 3. Enabling Hermes in production

1. Set on the VPS `.env` (or the deploy environment):
   ```
   ATLAS_AI_RUNTIME=hermes_agent
   ATLAS_HERMES_API_BASE_URL=http://host.docker.internal:8643
   ATLAS_HERMES_API_SERVER_KEY=<same value as aethos-nous API_SERVER_KEY>
   AETHOS_HERMES_TOOL_TOKEN=<random 32+ chars, identical on api and aethos-nous>
   ATLAS_CONTEXT_SIGNING_SECRET=<random 32+ chars>
   COMPOSE_PROFILES=worker
   ```
2. Install/update the host profile: `scripts/deploy/install-aethos-hermes-profile.sh`.
3. Put the provider/API/tool secrets into `~/.hermes/profiles/aethos-nous/aethos-nous.env` and start `~/.hermes/profiles/aethos-nous/run-aethos-nous.sh` under the host process manager.
4. Deploy with `.github/workflows/deploy-hostinger.yml`; record the SHA.
5. Verify the profile API with `curl -H "Authorization: Bearer ***" http://<aethos-ps-internal-gateway>:8643/health` on the host and `curl -H "Authorization: Bearer ***" http://host.docker.internal:8643/health` from the api container.
6. Verify the API sees it: a chat turn should produce an `agent_runs` row with agent `nous_hermes_runtime` and prompt version `hermes-v1`.
7. **Confirm the turn was not a silent fallback** — see §4.

Rollback: set `ATLAS_AI_RUNTIME=aethos_basic` and restart the api container; no data migration is involved. Per-tenant rollback: Settings → AI Inference Settings → Aethos Basic.

### Secret rotation

| Secret | Blast radius | Procedure |
|---|---|---|
| `AETHOS_HERMES_TOOL_TOKEN` | All Hermes tool calls 401 until both runtimes hold the new value | Update `.env` and `aethos-nous.env`, restart `api` and `aethos-nous` together |
| `API_SERVER_KEY` / `ATLAS_HERMES_API_SERVER_KEY` | API cannot reach Hermes; every turn falls back to Basic | Same, restart both |
| `ATLAS_CONTEXT_SIGNING_SECRET` | In-flight legacy context refs invalid (session tokens unaffected) | Rotate any time; brief tool errors possible |
| Hermes provider key | Hermes answers fail → fallback to Basic | Rotate at the provider, restart `aethos-nous` |

---

## 4. Verifying which runtime answered

Fallback is silent by design, so "Hermes is configured" is not evidence that Hermes answered.

- **Per turn**: `agent_runs` row for the thread — agent name `nous_hermes_runtime` means the Hermes adapter ran; `copilot_agent` means Basic. A Hermes turn that fell back produces a Basic row.
- **Router short-circuit**: the API logs `atlas_semantic_response_used` when the deterministic path answered; no runtime row means no model was called at all.
- **Profile process**: the host process-manager logs for `aethos-nous` should show the MCP tool calls for the turn.
- **Broker**: `atlas_tool_sessions` gains one row per Hermes turn (see §6 — these are never pruned today, #536).
- **Deliberate test**: temporarily set the tenant's response order to `atlas_runtime` only and ask a long-tail question (see `docs/infra/LOCAL_HERMES_TESTING.md`).

There is currently **no runtime badge in the Nous UI and no Hermes check in `/health/ready`** (#530).

---

## 5. What is guaranteed on each path

| Guarantee | Basic (`aethos_basic`) | Hermes (`hermes_agent`) |
|---|---|---|
| Streaming answer | yes | yes |
| Tool-call chips in the UI | yes | **no** (#532) |
| Output safety filter (no tool names, prompts, provider errors) | yes | yes — regex over the first 160 chars, plus a full-answer scan; a tail leak truncates the answer silently (#532) |
| Number-fidelity guard (stated figures checked against tool results) | yes | **no** (#532) — the user guide claim applies to Basic only |
| Langfuse trace | yes | **no** (#532) — Hermes calls the provider from its own container |
| `agent_tool_invocations` ledger / replayable steps | yes | **no** (#532) — one run row, zero steps |
| Agent tool policy on writes (role, risk, kill switch, HITL routing) | yes | partial — most writes reuse the policy path, **two do not** (#529) |
| Per-user read authorisation | endpoint RBAC | **none in the broker** (#529) |
| HITL for money/accounting/external send | yes | yes (write tools create Inbox tasks, never post directly) |

---

## 6. Data the runtime writes

| Table | Written by | Lifecycle |
|---|---|---|
| `chat_threads`, `chat_messages` | chat endpoint | Per tenant/user; resumed on login. No feedback column yet (#533). |
| `agent_runs` | `chat.py` | One row per turn: agent, prompt version, model version, trace id, replay pointer. |
| `agent_tool_invocations` | Basic agent only | Hermes tool calls are absent (#532). |
| `atlas_tool_sessions` | `atlas_context.create_atlas_tool_session` | Short `cts_…` token → tenant/user/thread/scope, 15-minute TTL, service-role only (RLS with no policies). **Never pruned; nonce never verified; not single-use** (#536). |
| `agent_suggestions` + `hitl_tasks` | write tools via `suggestion_writer` (or directly, #529) | The HITL surface; approval materialises the record. |
| `agent_corrections` | `inbox_service.approve_with_edits` / `reject` | Full before/after snapshots, append-only. **Chat turns produce none** (#533). |
| `agent_eval_candidates` | `inbox_repo._record_eval_candidate` | Hashes only; no UI, no promotion path (#534). |
| Hermes conversation memory | Hermes itself (`store: true`, key `aethos:{tenant}:{user}:{thread}`) | Lives in the `aethos-nous` host Hermes profile. No retention, no clearing path, no isolation proof (#531). Not covered by tenant export/erasure. |

---

## 7. The self-learning loop — current state

A learning loop needs six stages. Today only the first is partly built:

| Stage | State | Where | Gap |
|---|---|---|---|
| **1. Capture** | partial | `agent_corrections` from Inbox edits/rejections | No feedback on chat answers at all — no thumbs, no `chat_messages.feedback`. Most Nous output is never rated (#533). |
| **2. Curate** | dead end | `agent_eval_candidates` auto-created from corrections | Stores hashes only; no reviewer UI; the `accepted/dismissed/exported` statuses are unreachable; nothing turns a candidate into an eval case (#534). |
| **3. Evaluate** | self-test only | `scripts/agent_eval_gate.py` in CI | The CI gate scores hand-written fixtures against the rubric — it never calls a model. The only real scorer (`app/evals/runner.py`, which *does* exercise whichever runtime the tenant is on) runs solely from the opt-in `tests/eval/test_agent_eval_live.py`, writes results nowhere, and covers 8 golden prompts. 13 of 14 YAML eval packs have no runner (#534). |
| **4. Deploy a change** | manual | Prompts in three places: Basic `SYSTEM_PROMPT`, the Hermes instruction string, and the image-baked `SOUL.md` + skills | No prompt registry, versions are hardcoded strings, and a skill edit needs an image rebuild + redeploy with no eval gate in front of it (#535). |
| **5. Measure** | missing | — | No Langfuse scores anywhere in the repo; Hermes turns are untraced; number-fidelity findings are logged but not persisted or counted (#532). |
| **6. Promote autonomy** | broken | `autonomy_promoter` requires `agent_autonomy_settings.eval_passed_at` | **Nothing ever writes `eval_passed_at`**, and the demotion query still uses the PostgREST filter that #395 fixed elsewhere. No agent can reach L3 and no misbehaving agent can be demoted (#496, #534). |

**Operator summary**: Nous does not learn today. It improves only when an engineer changes a prompt, a skill, a read pack or the router by hand. Tell customers exactly that; the guide wording in §3 of the user guide has been corrected to match.

### The target loop (issues #533 → #534 → #535)

```
answer ──👎/edit──> correction (+intent, runtime, trace)
   → eval candidate (with payloads)
   → reviewer accepts in Settings → Eval Candidates
   → scripts/promote_eval_candidates.py writes a case into docs/test/agent_evals/<agent>.yaml
   → nightly live eval runs the packs against a seeded staging tenant on the real runtime
   → results → agent_eval_runs + Langfuse scores; on pass stamp eval_passed_at
   → autonomy_promoter offers L2 → L3 to an admin (never silently)
   → prompt/skill changes ship through the same gate, with rollback on regression
```

### Weekly operating rhythm once the loop exists (Dhruva)

1. Review new eval candidates (accept / dismiss with a note).
2. Promote accepted ones into eval packs; open the PR.
3. Read the nightly eval drift report; investigate any intent whose score dropped.
4. Review router misroutes (worst intents by 👎 rate) and propose threshold/concept changes as an Inbox task.
5. Review autonomy promotion offers with the admin; check demotions fired where they should.

---

## 8. Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Answers look canned, no Hermes logs | Router answered (stage 1) | API log `atlas_semantic_response_used`; raise `atlas_semantic_threshold` or reorder |
| Every turn is Basic although runtime is `hermes_agent` | Hermes unreachable or key mismatch → silent fallback | Host: `curl -H "Authorization: Bearer ***" http://<aethos-ps-internal-gateway>:8643/health`; api container: `curl -H "Authorization: Bearer ***" http://host.docker.internal:8643/health` |
| Hermes answers then stops mid-sentence | Output-safety tail leak truncation | `atlas_runtime` safety patterns; #532 replaces silent truncation with a visible notice |
| Tool calls 401 | `AETHOS_HERMES_TOOL_TOKEN` differs between api and the `aethos-nous` profile | Compare both env values; restart both |
| Tool calls 400 "invalid context" | Session token expired (15 min) or mangled by a weak model | `atlas_tool_sessions` row; consider a stronger `model.default` |
| Hermes returns nothing on tool-heavy prompts | Free-tier token quota | `config.yaml` `model.default` must be a paid model; see `LOCAL_HERMES_TESTING.md` |
| Circuit breaker keeps opening | Provider errors or timeouts | Breaker is in-process per worker (#536); check Hermes logs for provider 429s |
| `atlas_tool_sessions` growing unbounded | No pruning job | #536; safe to delete rows with `expires_at < now()` |

---

## 9. Security posture (read before granting access)

- The tool token is a **service/profile** credential. Anyone who can reach the api container's broker endpoint with that token can execute any of the 28 tools for any tenant whose session token they hold. Keep the broker on host loopback/internal network only, rate-limit it (#536), and rotate the token on any api container or host profile compromise.
- Session tokens are replayable within their 15-minute TTL (nonce minted but unchecked, not single-use) — #536.
- Read packs run with the service-role client and no per-user privilege check (#529): a viewer can obtain data the UI hides from them.
- Two write tools bypass the agent tool policy (#529): a viewer can cause an accounting review packet to be created.
- Document text reaches the model without untrusted-content fencing; prompt injection inside an uploaded invoice is flagged by the extraction agents but not neutralised in the read pack (#536).
- Hermes memory isolation is not proven and the volume is shared across tenants (#531). Do not describe Nous memory as tenant-isolated in a DPA until that test exists.
- Raw document binaries (scanned receipts/invoices) are sent to the model provider unmasked (#498).

---

## 10. Related documents

- [`docs/architecture/atlas-hermes-ai-agent-architecture.md`](../architecture/atlas-hermes-ai-agent-architecture.md) — design, flows, tool catalogue (still uses the pre-rename name "Atlas" in places).
- [`docs/architecture/nous-hermes-agentic-assessment.md`](../architecture/nous-hermes-agentic-assessment.md) — the assessment that drove the migration; several "done" items are not done (#532).
- [`docs/infra/LOCAL_HERMES_TESTING.md`](LOCAL_HERMES_TESTING.md) — local container testing, the two known gotchas.
- [`docs/infra/LANGFUSE_OBSERVABILITY.md`](LANGFUSE_OBSERVABILITY.md) — traced surfaces (Hermes correctly absent).
- [`docs/prd/aethos-atlas-powered-by-hermes-migration-plan.md`](../prd/aethos-atlas-powered-by-hermes-migration-plan.md) — migration phases; Phase 7 (cutover) not executed.
- [`docs/test/agent_eval_gate.md`](../test/agent_eval_gate.md) — the offline gate as it exists today.
