# Aethos Atlas Powered By Hermes - Migration And Deployment Plan

Date: 2026-06-26
Status: Implementation in progress
Decision posture: Aethos remains the system of record. Hermes powers the Atlas agent interaction layer.

## Product Decision

Aethos should keep all finance, tenant, user, approval, audit, and business-calculation authority. Hermes should replace the current hand-rolled Atlas agent loop as the agentic interaction layer.

The user-facing product remains **Aethos Atlas**. Hermes is an implementation detail:

- Users see Atlas, not Hermes.
- Users ask business questions and give business instructions.
- Users do not see internal tool names, tool-call traces, model traces, logs, stack traces, or raw tool outputs.
- Admins and operators can inspect evidence through Aethos Settings, Agent Run Ledger, Langfuse, and support tooling.

## Configurable AI Runtime Model

Atlas should support two AI runtimes behind the same Aethos chat interface:

| Runtime | Product label | Implementation | Default |
| --- | --- | --- | --- |
| `aethos_basic` | Aethos Basic AI | Current Aethos Atlas implementation and existing `CopilotAgent` path | Yes |
| `hermes_agent` | Hermes Agent Powered AI | Hermes-powered Atlas runtime using Aethos tools through MCP/native integration | No |

This keeps the current implementation stable while the Hermes path is built and tested.

Configuration:

```text
ATLAS_AI_RUNTIME=aethos_basic
ATLAS_HERMES_API_BASE_URL=http://hermes:8642
ATLAS_HERMES_API_SERVER_KEY=...
ATLAS_HIDE_TOOL_EVENTS=true
ATLAS_HERMES_FALLBACK_TO_BASIC=false
AETHOS_HERMES_TOOL_TOKEN=...
ATLAS_CONTEXT_SIGNING_SECRET=...
```

Runtime selection should be controlled by the Aethos API, not the browser:

1. Aethos authenticates the user and tenant.
2. Aethos chooses the runtime adapter.
3. Aethos owns chat persistence and session mapping.
4. Aethos streams a normalized Atlas response to the frontend.

Initial selection precedence:

1. Global environment variable `ATLAS_AI_RUNTIME`.
2. Default fallback: `aethos_basic`.

Future enterprise selection precedence:

1. Tenant-level AI setting, if enabled.
2. User/admin override for controlled pilots.
3. Global environment variable.
4. Default fallback: `aethos_basic`.

Important behavior:

- `aethos_basic` must remain the production default until Hermes passes parity.
- A tenant or deployment can opt into `hermes_agent` without changing frontend routes.
- Chat threads should record which runtime handled each turn for support and audit.
- The UI may later show an admin-visible "AI runtime" setting, but normal users should continue seeing only Aethos Atlas.
- Fallback from Hermes to Basic should be explicit via `ATLAS_HERMES_FALLBACK_TO_BASIC`; silent fallback can hide runtime-specific bugs and confuse audit evidence.
- Hermes tool calls must use Aethos-issued opaque `context_ref` values. Hermes must not choose tenant/user scope directly.
- Atlas chat history is persisted in Aethos and the UI can reload prior thread messages. Hermes memory/session history is an advanced runtime layer, not the only source of in-product chat continuity.

## Target Architecture

```text
Browser / future Slack / future Teams
        |
        v
Aethos Atlas UI and API facade
        |
        | selects runtime adapter
        v
Atlas Runtime Interface
        |                         |
        | aethos_basic            | hermes_agent
        v                         v
Current Aethos agent loop     Hermes API server / gateway
                                  |
                                  | Aethos-specific skills + MCP/native tools
                                  v
                              Aethos Tool Broker
        |
        v
Aethos domain APIs, services, repositories, Supabase, Inbox, audit ledger
```

### Responsibilities

| Area | Owner |
| --- | --- |
| Tenant/user identity | Aethos |
| RBAC and RLS | Aethos |
| Finance records | Aethos |
| CRUD APIs | Aethos |
| Business calculations | Aethos |
| Approval policy and Inbox | Aethos |
| Immutable audit events | Aethos |
| Agent run and tool ledger | Aethos |
| Chat UX brand | Aethos Atlas |
| AI runtime selection | Aethos |
| Basic AI runtime | Aethos current agent loop |
| Agent session continuity | Hermes, mirrored into Aethos |
| Tool orchestration | Hermes |
| Skills/persona packaging | Hermes profile distribution |
| External messaging channels | Hermes gateway, mediated by Aethos identity |
| Raw tool-call transcript | Hermes session DB plus Aethos ledger snapshots |
| Curated business memory | Aethos-governed memory, optionally exposed to Hermes |

## Why Hermes Fits This Shape

Hermes gives Aethos several modules that would otherwise be custom-built:

- OpenAI-compatible API server for in-app Atlas integration.
- Server-side conversation state through Responses/Sessions APIs.
- Session history with tool calls and tool results.
- Full-text session search.
- Profile distributions for packaging a whole Atlas persona, skills, config, and MCP wiring.
- Messaging gateway for Slack, Teams, Telegram, Email, WhatsApp, Signal, Discord, and other channels.
- Multi-profile gateway support for profile-per-tenant or profile-per-persona deployments.
- MCP support with tool allowlists.
- Plugin surfaces for tighter Aethos-native identity, memory, and audit behavior.

The main thing Hermes should not own is finance truth. Tool calls should always cross into Aethos APIs for data and actions.

## Important Product Constraint: Hide Tool Internals

Hermes can emit tool-progress events while streaming. Aethos should not forward those events to the user-facing Atlas UI.

The Atlas facade must:

1. Consume Hermes stream events server-side.
2. Forward only assistant text deltas and safe user-facing artifact events.
3. Suppress `tool.started`, `tool.completed`, traces, stack traces, and raw tool outputs.
4. Persist tool evidence internally in Aethos ledgers.
5. Convert internal failures into safe user messages.

Allowed user-facing events:

- Assistant text.
- Generic progress state such as "Working on this" if needed.
- Review artifact summaries such as "I created an Inbox review task".
- Links to Aethos Inbox, Documents, Reports, or record detail pages.
- User-facing draft cards only when they represent a business artifact, not an internal tool call.

Disallowed user-facing events:

- Internal tool names.
- Tool arguments.
- Tool outputs.
- Trace ids.
- Langfuse ids.
- Logs.
- Stack traces.
- SQL or raw API errors.

## Core Modules To Build

### 0. Atlas Runtime Interface

Purpose:

- Keep Aethos chat routes and frontend stable while supporting multiple agent runtimes.

Interface:

- `stream_message(tenant_id, user_id, thread_id, message, attachments, request_context)`
- returns normalized Atlas stream events:
  - `assistant_delta`
  - `assistant_done`
  - `artifact_created`
  - `safe_error`

Adapters:

- `AethosBasicRuntimeAdapter`
  - wraps the current `CopilotAgent` behavior.
  - preserves existing SSE behavior where needed.
  - remains the default.

- `HermesAgentRuntimeAdapter`
  - calls the private Hermes API server/session endpoint.
  - maps Aethos thread ids to Hermes sessions.
  - filters Hermes tool events.
  - returns only normalized Atlas events.

Leverage:

- The chat router, frontend, tests, and future external-channel bridge cross one stable interface.
- Runtime migration becomes incremental instead of a rewrite.

Locality:

- Hermes-specific HTTP calls, event filtering, session ids, and fallback logic live in one adapter, not across the router and UI.

### 1. Atlas Facade

Purpose:

- Keep the existing Atlas UI stable while changing the agent runtime behind it.

Interface:

- `GET /api/v1/chat/threads`
- `POST /api/v1/chat/threads`
- `GET /api/v1/chat/threads/{thread_id}/messages`
- `POST /api/v1/chat/threads/{thread_id}/messages`

Implementation:

- Maintain Aethos chat threads/messages as product-visible history.
- Map each Aethos thread to a Hermes session.
- Call Hermes over the internal Docker network.
- Stream only safe Atlas response deltas back to the browser.
- Mirror final assistant messages into Aethos.
- Mirror user messages and document links into Aethos.
- Keep a feature flag so current Atlas and Hermes-powered Atlas can run side by side during migration.

Feature flags:

- `ATLAS_AI_RUNTIME=aethos_basic|hermes_agent`
- `ATLAS_HIDE_TOOL_EVENTS=true`
- `ATLAS_MIRROR_HERMES_SESSIONS=true`
- `ATLAS_HERMES_FALLBACK_TO_BASIC=false`

### 2. Hermes Session Bridge

Purpose:

- Make Hermes sessions and Aethos threads correspond cleanly.

Tables:

- `atlas_hermes_sessions`
  - `tenant_id`
  - `aethos_thread_id`
  - `hermes_profile`
  - `hermes_session_id`
  - `hermes_session_key`
  - `source`
  - `external_channel`
  - `external_conversation_id`
  - `last_response_id`
  - `last_synced_at`
  - `created_at`

Behavior:

- On new Aethos thread, create or lazily initialize a Hermes session.
- Use stable session key: `aethos:{tenant_id}:{user_id}:{thread_id}`.
- For browser Atlas, call Hermes Sessions API or Responses API with this session key.
- For external channels, map Slack/Teams/Telegram session keys to Aethos threads.
- Sync final assistant text into Aethos `chat_messages`.
- Keep raw Hermes tool-call details in Hermes state and Aethos agent ledgers, not in user chat bubbles.

### 3. Aethos Tool Broker

Purpose:

- Give Hermes a narrow, governed surface for Aethos business capabilities.

Interface:

- Expose business tools through MCP and/or a native Hermes plugin.
- Tools should be business verbs, not database verbs.

Initial tools:

- `aethos.finance_ops.check`
- `aethos.inbox.list_open_tasks`
- `aethos.documents.get_status`
- `aethos.documents.extract`
- `aethos.documents.rerun_extraction`
- `aethos.engagements.list`
- `aethos.engagements.create_draft_from_document`
- `aethos.invoices.draft`
- `aethos.bills.extract_or_create_draft`
- `aethos.bill_pay.propose_batch`
- `aethos.close.prepare_month_end`
- `aethos.close.prepare_year_end`
- `aethos.reports.generate_statement_package`
- `aethos.collections.draft_reminders`
- `aethos.audit.get_decision_trail`

Rules:

- No generic SQL tool.
- No generic Supabase tool.
- No generic filesystem/terminal/browser tool in production tenant channels.
- Every tool validates tenant/user context server-side.
- Every tool applies Aethos RBAC, approval policy, period-lock policy, and tenant scoping.
- Every write-capable tool creates drafts or Inbox review tasks unless explicit tenant policy permits automation.
- Every tool response is structured and safe: ids, labels, summaries, links, and next actions.

### 4. Aethos Context Broker

Purpose:

- Prevent the model from choosing tenant/user context.

Best implementation:

- Native Hermes plugin receives platform/session/user context and requests an Aethos context from the Atlas facade.

Pragmatic first implementation:

- Aethos Atlas facade mints a short-lived signed `context_ref` for each Hermes turn.
- `context_ref` encodes:
  - tenant id
  - user id
  - Aethos thread id
  - allowed document ids
  - allowed tool scope
  - expiry
  - nonce/replay id
- Hermes tools pass the opaque `context_ref` to Aethos Tool Broker.
- Aethos validates the token and derives tenant/user context server-side.
- Tool arguments never include trusted tenant ids or user ids.

Risk:

- The model can see the opaque `context_ref`.

Mitigation:

- Short TTL.
- Scope-limited.
- One thread/run only.
- No privilege encoded beyond the authenticated user.
- Tool Broker validates every action again.

Long-term implementation:

- Native Hermes plugin injects context without exposing it in model text where possible.

### 5. Atlas Profile Distribution

Purpose:

- Package Hermes so it behaves as Aethos Atlas, not a generic assistant.

Repo layout:

```text
integrations/hermes/
  Dockerfile
  bootstrap-profile.sh
  aethos-atlas-profile/
    distribution.yaml
    SOUL.md
    config.yaml
    mcp.json
    skills/
      aethos-finance-ops-manager/SKILL.md
      aethos-engagement-letter-intake/SKILL.md
      aethos-o2c-invoice-to-cash/SKILL.md
      aethos-p2p-procure-to-pay/SKILL.md
      aethos-r2r-close-controller/SKILL.md
      aethos-collections/SKILL.md
      aethos-audit-evidence/SKILL.md
    .env.EXAMPLE
```

`SOUL.md` responsibilities:

- Name the agent as Aethos Atlas.
- Explain that Aethos is the source of truth.
- Instruct Atlas to use Aethos tools for every number and every action.
- Instruct Atlas not to reveal internal tool names, traces, logs, or raw outputs.
- Instruct Atlas to summarize outcomes and route sensitive actions to Inbox.
- Instruct Atlas to ask clarifying questions only when the tool interface requires missing business input.

Skill responsibilities:

- Teach business workflows.
- Map business intent to tool categories.
- Define approval boundaries.
- Define fallback behavior when Aethos APIs are unavailable.
- Keep prompts written in user language.

`mcp.json` responsibilities:

- Point Hermes at the Aethos MCP server or Tool Broker.
- Use explicit allowlists.
- Disable resources/prompts wrappers unless intentionally needed.

## Packaging Recommendation

### Development

Use the official Hermes image directly:

```yaml
hermes:
  image: nousresearch/hermes-agent:<pinned-version-or-digest>
  command: gateway run
  volumes:
    - hermes-data:/opt/data
    - ./integrations/hermes/aethos-atlas-profile:/opt/aethos/atlas-profile:ro
  environment:
    API_SERVER_ENABLED: "true"
    API_SERVER_HOST: "0.0.0.0"
    API_SERVER_PORT: "8642"
    API_SERVER_KEY: "${HERMES_API_SERVER_KEY}"
    API_SERVER_MODEL_NAME: "Aethos Atlas"
    AETHOS_INTERNAL_API_URL: "http://api:8080"
    AETHOS_HERMES_TOOL_TOKEN: "${AETHOS_HERMES_TOOL_TOKEN}"
  expose:
    - "8642"
```

Use a bootstrap script to install/copy the Atlas profile into Hermes state on container start.

### Production

Build a derived image:

```text
aethos-ps-hermes:<image-tag>
```

Derived image contents:

- Pinned Hermes base image.
- Aethos Atlas profile distribution.
- Aethos bootstrap script.
- Optional native Hermes plugin.
- Optional Aethos MCP client/server package if not hosted by the API container.

Why a derived image:

- Reproducible deployments.
- Profile files versioned with Aethos source.
- No runtime git install needed in production.
- Easier rollback using image tags.
- Safer than mounting mutable local profile code into production.

Runtime user data remains in a Docker volume:

```text
hermes-data:/opt/data
```

Never bake into the image:

- API keys.
- Platform tokens.
- Hermes state DB.
- Sessions.
- Memories.
- Logs.
- Tenant data.

## Hostinger Deployment Shape

Current Hostinger deployment routes public traffic only to web containers. Keep that pattern.

```text
Traefik
  -> frontend:80  -> /api/* -> api:8080
  -> timesheet:80 -> /api/* -> api:8080

api -> hermes:8642 over private Docker network
hermes -> api:8080 over private Docker network
worker -> Supabase Postgres queue
```

Hermes should not get a public Traefik route for in-app Atlas.

Only add a public route later if external channel webhooks require it:

```text
atlas-gateway.ishirock.tech -> hermes webhook gateway
```

Even then:

- Do not expose Hermes dashboard publicly.
- Do not expose Hermes API server publicly.
- Expose only the required webhook paths if possible.
- Prefer Aethos-owned webhook endpoints that forward to Hermes after identity checks when platform support allows.

### Compose Changes

Add `hermes` service:

```yaml
  hermes:
    build:
      context: ./integrations/hermes
      dockerfile: Dockerfile
    image: "aethos-ps-hermes:${AETHOS_IMAGE_TAG:-latest}"
    restart: unless-stopped
    expose:
      - "8642"
    environment:
      API_SERVER_ENABLED: "true"
      API_SERVER_HOST: "0.0.0.0"
      API_SERVER_PORT: "8642"
      API_SERVER_KEY: "${HERMES_API_SERVER_KEY:-}"
      API_SERVER_MODEL_NAME: "Aethos Atlas"
      AETHOS_INTERNAL_API_URL: "http://api:8080"
      AETHOS_HERMES_TOOL_TOKEN: "${AETHOS_HERMES_TOOL_TOKEN:-}"
      OPENROUTER_API_KEY: "${OPENROUTER_API_KEY:-}"
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY:-}"
    volumes:
      - hermes-data:/opt/data
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8642/health"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
    networks:
      - aethos-internal
```

Add API environment:

```yaml
  ATLAS_AI_RUNTIME: "${ATLAS_AI_RUNTIME:-aethos_basic}"
  ATLAS_HERMES_API_BASE_URL: "${ATLAS_HERMES_API_BASE_URL:-http://hermes:8642}"
  ATLAS_HERMES_API_SERVER_KEY: "${ATLAS_HERMES_API_SERVER_KEY:-}"
  ATLAS_HIDE_TOOL_EVENTS: "${ATLAS_HIDE_TOOL_EVENTS:-true}"
  ATLAS_HERMES_FALLBACK_TO_BASIC: "${ATLAS_HERMES_FALLBACK_TO_BASIC:-false}"
  AETHOS_HERMES_TOOL_TOKEN: "${AETHOS_HERMES_TOOL_TOKEN:-}"
```

Post-cutover:

```text
ATLAS_AI_RUNTIME=hermes_agent
```

Pre-cutover:

```text
ATLAS_AI_RUNTIME=aethos_basic
```

### Secrets

Required new runtime secrets:

- `HERMES_API_SERVER_KEY`
- `AETHOS_HERMES_TOOL_TOKEN`

Optional:

- External channel bot tokens.
- `HERMES_DASHBOARD=0` or omitted in production.
- Provider keys only if Hermes calls the model provider directly instead of reusing Aethos/OpenRouter config.

Do not route `HOSTINGER_API_KEY` or deployment-only values into the Hermes container.

## In-App Atlas Request Flow

1. User opens `/app/copilot`.
2. Frontend uses existing Atlas endpoints.
3. Aethos API authenticates user and tenant.
4. Aethos loads or creates `chat_thread`.
5. Aethos resolves or creates a Hermes session mapping.
6. Aethos creates a short-lived `context_ref`.
7. Aethos sends the user message to Hermes Sessions API:
   - session id or session key
   - current input
   - Atlas instructions
   - hidden Aethos context reference
8. Hermes uses Atlas profile, skills, memory, and Aethos tools.
9. Hermes may call Aethos tools through MCP/plugin.
10. Aethos Tool Broker executes business operations through normal Aethos domain code.
11. Aethos Tool Broker records agent run/tool evidence.
12. Hermes returns final response stream.
13. Aethos Atlas facade filters events:
   - forwards assistant text
   - suppresses tool traces
   - emits only safe artifact/link events
14. Aethos persists final chat messages.

## Existing Feature Migration Map

| Existing Atlas capability | Hermes-powered implementation |
| --- | --- |
| Active engagement lookup | `aethos.engagements.list` |
| AR aging | `aethos.finance.ar_aging` or finance ops check |
| AP aging | `aethos.finance.ap_aging` or finance ops check |
| WIP | `aethos.finance.wip` |
| Time logging | `aethos.time.log_entry`, with existing policy |
| Rate card update | `aethos.rate_cards.update`, Inbox/policy gated where needed |
| Draft invoice | `aethos.invoices.draft`, creates Inbox review |
| Collections reminders | `aethos.collections.draft_reminders`, creates Inbox review |
| Bill extraction | `aethos.bills.extract_or_create_draft`, creates Inbox review |
| Bill-pay proposal | `aethos.bill_pay.propose_batch`, creates Inbox review |
| Month-end close | `aethos.close.prepare_month_end`, creates Inbox review |
| Year-end close | `aethos.close.prepare_year_end`, creates Inbox review |
| Financial statement package | `aethos.reports.generate_statement_package` |
| Engagement-letter upload | `aethos.documents.extract` + `aethos.engagements.create_draft_from_document` |
| Engagement-letter retry | `aethos.documents.rerun_extraction` |
| Decision trail | `aethos.audit.get_decision_trail` |
| Agent run evidence | Aethos Agent Run Ledger, internal only |

## Document Upload And Retry

Browser upload remains Aethos-owned:

1. User attaches file in Atlas.
2. Frontend uploads file to `/api/v1/documents/upload?process=false`.
3. Message send includes the document id.
4. Atlas facade links document id to thread/message.
5. Hermes sees a business instruction plus document reference.
6. Hermes calls Aethos document tool.
7. Aethos extraction worker/service performs extraction.
8. Inbox receives review task.
9. User can later say, "try the same engagement letter again; billing is mixed."
10. Hermes uses session history and Aethos document links to call rerun extraction.
11. Aethos creates a new extraction attempt and review task without overwriting audit evidence.

External channel upload later:

- Hermes receives the attachment.
- Aethos channel adapter registers the file into Aethos documents.
- The rest of the flow is identical.

## Memory Strategy

The phrase "store tool calls in Hermes memory" should be implemented carefully.

Recommended split:

- Hermes **sessions** store raw conversation history, tool calls, and tool results.
- Aethos **agent ledger** stores audit-safe tool evidence and hashes.
- Aethos **memory** stores curated business facts, preferences, corrections, and policies.
- Hermes **memory** can store non-authoritative interaction preferences and session recall, but not finance truth.

Why:

- Raw tool calls are history/evidence, not semantic memory.
- Finance facts must be tenant-scoped, auditable, revocable, and sourced.
- Hermes memory can improve interaction quality, but live Aethos APIs remain authoritative.

Memory examples:

| Item | Storage |
| --- | --- |
| "User prefers concise close summaries" | Hermes memory or Aethos user preference |
| "Nexus billing arrangement corrected to mixed" | Aethos memory candidate after approval |
| "Last tool call returned AR aging" | Hermes session + Aethos agent ledger |
| "Invoice INV-1007 is overdue" | Aethos live data only |
| "Tenant policy requires CFO approval over $25k" | Aethos policy table and Aethos memory summary if useful |

## Observability

User-facing Atlas:

- No traces.
- No internal tool logs.
- No raw model/tool errors.

Admin/operator surfaces:

- Aethos Agent Run Ledger.
- Langfuse traces if configured.
- Settings operational health.
- Hermes health status.
- Hermes session id and Aethos thread id correlation.

New telemetry fields:

- `hermes_session_id`
- `hermes_run_id`
- `hermes_profile`
- `atlas_runtime`
- `source_channel`
- `aethos_thread_id`

Operational checks:

- `GET http://hermes:8642/health`
- `GET http://hermes:8642/health/detailed` internally
- API readiness should optionally include Hermes when `ATLAS_AI_RUNTIME=hermes_agent`.

## Migration Phases

### Phase 0 - Runtime Configuration And Adapter Seam

Goal:

- Make Atlas runtime selection configurable without changing current behavior.

Build:

- Add settings:
  - `atlas_ai_runtime`
  - `atlas_hermes_api_base_url`
  - `atlas_hermes_api_server_key`
  - `atlas_hide_tool_events`
  - `atlas_hermes_fallback_to_basic`
- Add `AtlasRuntime` interface.
- Add `AethosBasicRuntimeAdapter` that wraps the current implementation.
- Update chat route to call the runtime interface.
- Record runtime mode on chat messages or agent runs where practical.

Acceptance:

- With no new env vars, Atlas behaves exactly as it does today.
- `ATLAS_AI_RUNTIME=aethos_basic` uses the current implementation.
- `ATLAS_AI_RUNTIME=hermes_agent` can be enabled later without frontend route changes.
- Invalid runtime config fails startup or returns a clear operator-facing error.

Tests:

- Unit: default settings resolve to `aethos_basic`.
- Unit: runtime factory returns the Basic adapter by default.
- Unit/API: chat route still streams through Basic adapter.
- Unit: invalid runtime is rejected.

### Phase 1 - Aethos History And Session Bridge

Goal:

- Make Aethos chat history reliable before runtime replacement.

Build:

- Message-history route.
- Frontend history load.
- `atlas_hermes_sessions` migration.
- Feature flag plumbing.

Acceptance:

- Existing Atlas works unchanged.
- Thread history survives refresh.
- Hermes can be disabled without breaking Atlas.

### Phase 2 - Hermes Container And Profile

Goal:

- Run Hermes privately beside Aethos.

Build:

- `integrations/hermes/Dockerfile`.
- Atlas profile distribution.
- Hostinger compose `hermes` service.
- API settings for Hermes base URL/key.
- Health check.
- Runtime factory can instantiate `HermesAgentRuntimeAdapter` when configured.

Acceptance:

- `api` can call `http://hermes:8642/health`.
- Hermes model name is "Aethos Atlas".
- No public route exposes Hermes API or dashboard.
- `ATLAS_AI_RUNTIME=aethos_basic` still works when the Hermes service is stopped.

### Phase 3 - Read-Only Tool Broker

Goal:

- Prove Hermes can orchestrate through Aethos APIs safely.

Build:

- Aethos MCP/native tool surface for:
  - finance ops check
  - engagement lookup
  - AR/AP/WIP
  - Inbox list
- Context broker.
- Tool allowlist.

Acceptance:

- Atlas powered by Hermes answers read-only finance prompts from live Aethos data.
- No tool names are shown to the user.
- Aethos ledger records tool evidence internally.
- Switching back to `ATLAS_AI_RUNTIME=aethos_basic` restores the current agent path without data loss.

### Phase 4 - Inbox-Gated Write Tools

Goal:

- Restore all current Atlas workflows behind Hermes.

Build:

- Invoice draft.
- Collections draft.
- Bill extraction.
- Bill-pay proposal.
- Close preparation.
- Statement package.
- Engagement-letter extraction.

Acceptance:

- Existing demo guide scenarios pass.
- Sensitive actions still go to Inbox.
- No write action bypasses Aethos policy.

### Phase 5 - Document Retry And Memory

Goal:

- Improve beyond current Atlas.

Build:

- Versioned rerun extraction.
- Correction prompt capture.
- Aethos memory candidates.
- Hermes session search integration for "we discussed this before" behavior.

Acceptance:

- User can return after refresh and say "extract that engagement letter again".
- Atlas identifies prior document and creates a corrected Inbox task.
- Approved corrections can influence future relevant extraction.

### Phase 6 - External Channels

Goal:

- Add Slack/Teams/Telegram without changing Aethos business logic.

Build:

- External identity mapping.
- Channel session bridge.
- Optional public Hermes webhook route or Aethos-owned webhook relay.
- Admin UI for pairing/revocation.

Acceptance:

- External channel user maps to Aethos tenant/user.
- Same Aethos tools and approvals apply.
- External conversation appears in Aethos Atlas history.

### Phase 7 - Cutover And Deletion

Goal:

- Remove old hand-rolled agent loop after parity.

Actions:

- Default `ATLAS_AI_RUNTIME=hermes_agent`.
- Keep rollback flag for one release.
- Remove old CopilotAgent path only after production proof.
- Retain Aethos Tool Broker and Atlas Facade as stable modules.

## QA Plan

Regression scenarios:

- Runtime default is Basic with no Hermes container required.
- Runtime config can switch to Hermes in an isolated environment.
- Runtime config can switch back to Basic.
- Refresh chat history.
- Active engagements prompt.
- AR/AP/WIP prompts.
- Log time through Atlas.
- Draft invoice through Atlas and approve in Inbox.
- Upload engagement letter and create engagement through Inbox.
- Retry engagement-letter extraction after refresh.
- Upload vendor bill and create bill through Inbox.
- Propose bill-pay batch.
- Prepare month-end close.
- Generate financial statements.
- Ask decision trail.
- Confirm no tool names, traces, or logs are visible in chat.
- Confirm agent run evidence is visible only in Settings/admin surfaces.
- Confirm tenant B cannot access tenant A Hermes session or tool context.

Cutover acceptance:

- All current demo guide v2 Atlas scenarios pass.
- Enterprise E2E scenarios involving Atlas pass.
- Public production smoke passes on `aethos.ishirock.tech`.
- Hermes health is included in operational health.
- Rollback to current runtime is documented and tested.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Hermes exposes generic tools | Disable generic terminal/filesystem/browser tools in production Atlas profile; expose only Aethos tools |
| User sees tool traces | Atlas facade filters stream events and UI removes tool-call cards for Hermes runtime |
| Tenant leakage | Context broker, RLS, short-lived context refs, per-tenant tests |
| Split conversation history | Session bridge mirrors Hermes sessions into Aethos chat history |
| Write bypasses Inbox | Tool Broker enforces Aethos approval policy on every write |
| Hermes state loss | Persist `hermes-data` volume and document backup/restore |
| Version drift | Pin Hermes image digest/version and build derived image |
| Observability gap | Mirror Hermes ids into Aethos ledger and health surfaces |
| Channel spoofing | Aethos-owned external identity mapping and revocation |
| Runtime switch breaks current Atlas | Default to `aethos_basic`; introduce `AtlasRuntime` adapter seam before Hermes; test Basic path on every slice |

## Recommended Implementation Issue Breakdown

### Issue 1 - Configurable Atlas Runtime Seam

Status: Implemented in the first migration slice.

Title: Add configurable Atlas AI runtimes with Aethos Basic default

Scope:

- Add `ATLAS_AI_RUNTIME=aethos_basic|hermes_agent`.
- Add runtime settings and validation.
- Add `AtlasRuntime` interface.
- Add `AethosBasicRuntimeAdapter` around the current implementation.
- Route existing chat endpoint through the runtime interface.
- Preserve existing frontend and route contracts.
- Add tests proving Basic remains the default and current chat behavior still works.

Out of scope:

- Hermes container.
- Hermes HTTP calls.
- MCP tools.
- Runtime cutover.

### Issue 2 - Private Hermes Runtime Packaging

Status: Foundation implemented. Hermes is packaged as an optional private
Compose profile and the backend has a Hermes client/adapter; business tool
parity remains in later issues.

Title: Package Hermes as private Atlas runtime candidate

Scope:

- Add Hermes container behind the internal Docker network.
- Add derived `aethos-ps-hermes` image or dev-only official image wiring.
- Add Atlas profile distribution.
- Add backend Hermes client.
- Add `HermesAgentRuntimeAdapter` with health-check and safe-error behavior.
- Add session bridge table.
- Prove `ATLAS_AI_RUNTIME=aethos_basic` works without Hermes running.

Out of scope:

- Business tool parity.
- Write-capable tools.
- External channels.

### Issue 3 - Read-Only Hermes Tool Orchestration

Status: First backend/MCP foundation implemented. Live Hermes container build
and browser E2E remain pending because local Docker was unavailable during
verification.

Title: Prove Hermes-powered Atlas read-only Aethos tool orchestration

Scope:

- Add read-only Aethos Tool Broker/MCP tools for finance ops check and engagement lookup. Implemented for:
  - `aethos.engagements.list`
  - `aethos.finance.ar_aging`
  - `aethos.finance.ap_aging`
  - `aethos.finance.wip`
  - `aethos.finance_ops.snapshot`
- Add context broker for tenant/user-safe tool calls. Implemented with short-lived HMAC-signed `context_ref`.
- Filter Hermes tool events so users see only Atlas text. Implemented in the Hermes adapter by extracting visible response text and ignoring tool/function output items.
- Add E2E proof that Hermes-powered Atlas can answer live-data prompts. Pending live container verification.
- Add runtime rollback proof back to `aethos_basic`. Implemented via default runtime and optional `ATLAS_HERMES_FALLBACK_TO_BASIC=true`.

Out of scope:

- Inbox-gated writes.
- Full document retry.
- Removing old Atlas runtime.

Implemented files:

- `backend/app/services/atlas_context.py`
- `backend/app/api/v1/endpoints/atlas_tools.py`
- `integrations/hermes/aethos_mcp_server.py`
- `integrations/hermes/aethos-atlas-profile/config.yaml`

Verification completed:

- Focused backend tests: `51 passed`.
- Ruff on touched backend files: passed.
- Hostinger Compose config with `--profile hermes`: passed.
- Hermes MCP bridge script: Python compile passed.

Verification pending:

- Hermes image build and live MCP discovery. Local Docker daemon was not available:
  `failed to connect to the docker API at unix:///Users/vramakrishnaiah/.orbstack/run/docker.sock`.
- Live `ATLAS_AI_RUNTIME=hermes_agent` chat E2E against a running Hermes container.

### Issue 4 - Current Atlas Workflow Parity

Status: First parity layer implemented for the current Basic Atlas finance
workflow set. Browser E2E and document-intake parity remain pending.

Title: Migrate current Atlas workflows to Hermes Agent Powered AI behind Aethos tools

Scope:

- Finance Ops action-plan creation through Inbox. Implemented via
  `aethos.finance_ops.create_action_plan`, reusing the existing Basic Atlas
  policy/HITL execution path.
- Invoice draft. Implemented via `aethos.o2c.draft_invoice`.
- Collections reminders. Implemented via `aethos.collections.draft_reminders`.
- Bill-pay proposal. Implemented via `aethos.p2p.propose_bill_payment_batch`.
- Month-end/year-end close preparation. Implemented via
  `aethos.r2r.prepare_month_end_close` and `aethos.r2r.prepare_year_end_close`.
- Financial statement package. Implemented via
  `aethos.r2r.generate_financial_statement_package`.
- Bill extraction.
- Engagement-letter extraction.
- Existing demo guide and enterprise E2E parity.

Out of scope:

- External channels.
- Removing Basic runtime.

### Issue 5 - Document Retry, Memory, And External Channels

Title: Add Hermes-powered document retry, governed memory, and channel foundation

Scope:

- Versioned extraction retry from prior conversation context.
- Aethos-governed memory candidates and recall.
- External identity mapping.
- Channel session bridge.
- First Slack/Teams/Telegram pilot.

Out of scope:

- Broad self-serve multi-channel rollout.
- Removing Aethos Basic AI fallback.
