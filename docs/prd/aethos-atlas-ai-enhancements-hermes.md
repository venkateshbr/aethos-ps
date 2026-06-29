# Aethos Atlas AI Enhancements - Hermes Integration Assessment

Date: 2026-06-26
Status: Planning
Scope: Independent assessment of Hermes Agent as a runtime/channel/memory layer for Aethos Atlas.

Assessment note: this document intentionally ignores prior architecture-document assumptions about PydanticAI/Pydantic Graph and evaluates Hermes against Aethos product requirements and the current Atlas implementation reality.

Follow-up decision: the preferred direction is captured in
[`aethos-atlas-powered-by-hermes-migration-plan.md`](aethos-atlas-powered-by-hermes-migration-plan.md):
Aethos remains the system of record, Atlas remains the user-facing AI brand, and
Hermes powers the agent runtime/channel/session layer behind Atlas.

## Executive View

Hermes should be evaluated seriously because it already has several capabilities Aethos would otherwise have to build:

- Multi-channel gateway for Telegram, Discord, Slack, WhatsApp, Signal, Email, Teams, and more.
- Persistent sessions with resume, titles, full history, and full-text session search.
- Profiles for isolated agents with separate config, memory, skills, gateway state, and provider keys.
- Multi-profile gateway multiplexing.
- Skills as reusable procedural instructions.
- MCP integration for exposing Aethos tools without modifying Hermes core.
- Plugin surfaces for tools, gateway adapters, memory providers, hooks, slash commands, and context engines.
- Built-in memory and session search.

The key product decision is not "Hermes or Aethos". The viable enterprise design is:

> Aethos remains the system of record for tenants, users, finance data, approvals, audit, and policy. Hermes provides agent runtime capabilities, external channel gateway, skills/profiles, and a pluggable interface into Aethos through MCP/native plugins.

Hermes should not directly own tenant business truth or final finance authority.

## Relevant Hermes Capabilities

Sources reviewed:

- Hermes docs: https://hermes-agent.nousresearch.com/docs/
- Sessions: https://hermes-agent.nousresearch.com/docs/user-guide/sessions
- Messaging gateway: https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
- Profiles: https://hermes-agent.nousresearch.com/docs/user-guide/profiles
- Multi-profile gateways: https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways
- MCP guide: https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes
- Python library: https://hermes-agent.nousresearch.com/docs/guides/python-library
- Skills: https://hermes-agent.nousresearch.com/docs/guides/work-with-skills
- Plugins: https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin
- Security: https://hermes-agent.nousresearch.com/docs/user-guide/security

Important facts from official docs:

- Messaging gateway supports many platforms and stores per-chat sessions.
- Sessions persist full message history, model config, system prompt snapshot, tool calls, tool results, token counts, timestamps, source platform, and user id in SQLite.
- Session search uses SQLite FTS5 and can retrieve actual past messages.
- Profiles are independent Hermes homes with their own config, `.env`, `SOUL.md`, memories, sessions, skills, cron jobs, and gateway state.
- Multi-profile gateway can route inbound messages to separate profiles while keeping profile credentials isolated.
- MCP is intended as an adapter layer where Hermes remains the agent and MCP servers contribute filtered tools.
- Hermes can also be embedded as a Python library, but the docs warn to create a fresh `AIAgent` per thread/task because agent instances keep internal state and are not thread-safe to share.
- Plugins can add tools, hooks, platform adapters, memory providers, and context engines.
- Hermes has defense-in-depth security features, but Aethos would still need tenant identity, RBAC, RLS, HITL, and finance audit enforcement outside Hermes.

## Integration Options

### Option A - Hermes As External Channel Companion

Shape:

- Keep in-app Atlas on Aethos-native backend.
- Run Hermes gateway for Slack/Teams/Telegram/Email.
- Hermes talks to Aethos through an Aethos MCP server or native Aethos Hermes plugin.
- Aethos stores finance actions, audit, Inbox tasks, and final records.
- Hermes stores external-channel sessions and mirrors essential conversation events into Aethos.

Best for:

- Fast external-channel rollout.
- Avoiding a full rewrite of in-app Atlas.
- Pilots with a small number of tenants.

Tradeoffs:

- Two conversation stores exist unless mirrored carefully.
- User may see different history in Slack vs in-app Atlas unless session bridge is implemented.
- Identity mapping must be solved before write-capable tools are exposed.

Recommendation:

- Best first Hermes spike.

### Option B - Hermes As Primary Atlas Runtime

Shape:

- In-app Atlas and all external channels route to Hermes.
- Aethos backend becomes tool provider, policy engine, tenant store, and audit ledger.
- Hermes owns the active conversation loop, skills, session search, and profile/persona behavior.

Best for:

- Maximizing reuse of Hermes sessions, skills, gateway, and tool orchestration.
- Reducing custom agent runtime code in Aethos.

Tradeoffs:

- Larger migration.
- Harder to preserve current SSE/card rendering semantics.
- Requires strong session sync so Aethos UI and Hermes sessions are not split.
- Requires production-grade Aethos identity context inside Hermes tool calls.
- Requires Langfuse/observability strategy for Hermes-owned model calls.

Recommendation:

- Not first. Consider after Option A proves identity, session sync, and audit.

### Option C - Hermes Embedded As Python Library

Shape:

- FastAPI imports Hermes `AIAgent`.
- Aethos passes conversation history and tool restrictions per request.
- Aethos UI remains the only first-class channel initially.

Best for:

- Reusing Hermes tool loop and skills inside current backend process.

Tradeoffs:

- Does not use the gateway advantage much.
- Thread/task isolation matters; a new `AIAgent` per request/task is recommended.
- Packaging a git-based runtime dependency into production containers must be managed.
- Still need Aethos conversation store and context builder.

Recommendation:

- Useful for local spike, but less compelling than the sidecar/gateway model.

### Option D - Dedicated Hermes Instance Per Tenant

Shape:

- One Hermes profile or container per Aethos tenant.
- Each tenant gets isolated sessions, memory, skills, channels, and credentials.
- Aethos provisioning creates/updates tenant Hermes profile/container.

Best for:

- Strong isolation.
- Enterprise tenants with dedicated channel bots.
- Early pilots where operational count is low.

Tradeoffs:

- Operationally heavy at scale.
- Requires lifecycle automation: provision, rotate secrets, pause, archive, delete.
- Cost attribution is simpler but platform maintenance is larger.

Recommendation:

- Good for enterprise/dedicated deployments, not broad self-serve SaaS scale.

### Option E - Shared Hermes Gateway With Aethos Tenant Plugin

Shape:

- One Hermes deployment serves multiple tenants.
- A custom Aethos plugin maps every inbound channel user/thread to Aethos tenant/user.
- Aethos MCP/native tools receive tenant/user context per call.
- Hermes memory provider is backed by Aethos and scoped by tenant/user.

Best for:

- SaaS-scale multi-tenant operation.

Tradeoffs:

- More custom plugin work.
- Must prove Hermes exposes enough per-message/session/platform context to every tool/hook.
- Any context leakage bug is high severity.

Recommendation:

- Target architecture if Hermes becomes core to production channels.

## Multi-Tenant Strategy

### Pilot Strategy

Use one Hermes profile per tenant:

- `aethos-demo`
- `tenant-<slug>-atlas`
- optionally `tenant-<slug>-controller` for a high-privilege persona

Use Hermes `gateway.multiplex_profiles=true` so one default gateway process can route profile-specific channels.

Benefits:

- Clean memory/session/config isolation.
- Each tenant can have different Slack/Teams/Telegram credentials.
- Easy to reason about in early pilots.

Limitations:

- Not enough for self-serve SaaS scale.
- Per-user audit still needs Aethos identity mapping.

### Production SaaS Strategy

Use a shared Hermes deployment only after building Aethos tenant-aware plugins:

- `external_identities` table maps platform user ids to Aethos users and tenants.
- `conversation_channel_bindings` maps platform threads to Aethos chat threads and Hermes sessions.
- Aethos tool plugin/MCP server injects tenant/user context into every call.
- Aethos memory provider scopes memory reads/writes by tenant/user/client/document.
- Channel access is administered from Aethos, not only from Hermes allowlists.

## Personas And Profiles

Personas should not automatically equal tenants.

Recommended model:

- Tenant isolation: Hermes profile/container or Aethos tenant-aware plugin.
- Persona behavior: skills and `SOUL.md` instructions inside the tenant context.
- Separate profile only when a persona needs different credentials, tools, channels, or memory.

Suggested personas:

- `Aethos Atlas` - consolidated AI finance operations manager.
- `Atlas Controller` - R2R close, journals, financial statements, audit evidence.
- `Atlas AP` - vendor bills, duplicate checks, bill pay, vendor communications.
- `Atlas AR` - invoicing, collections, cash application.
- `Atlas Engagement Ops` - engagement letters, clients, projects, rate cards.

For most tenants, one Atlas profile with these skills is simpler than five separate agents. Separate profiles make sense for different channel bots or privilege boundaries.

## Aethos Tool Mapping

Hermes should not get generic database, filesystem, or terminal access in production tenant channels.

Expose Aethos business tools with narrow interfaces:

- `aethos.finance_ops.check`
- `aethos.finance_ops.create_action_plan`
- `aethos.documents.register_upload`
- `aethos.documents.extract`
- `aethos.documents.rerun_extraction`
- `aethos.engagements.create_draft_from_document`
- `aethos.invoices.draft`
- `aethos.collections.draft_reminders`
- `aethos.bills.extract_or_create_draft`
- `aethos.bill_pay.propose_batch`
- `aethos.close.prepare_month_end`
- `aethos.close.prepare_year_end`
- `aethos.reports.generate_statement_package`
- `aethos.inbox.list_open_tasks`
- `aethos.inbox.approve`
- `aethos.inbox.reject`
- `aethos.audit.get_decision_trail`
- `aethos.memory.recall`
- `aethos.memory.propose`

Tool rules:

- Every tool receives tenant/user context from Aethos identity mapping.
- Every write-capable tool enforces Aethos approval policy.
- Money-out, accounting, customer-email, and material master-data changes route to Inbox unless tenant policy explicitly permits automation.
- Tools return concise structured evidence, not raw database rows.
- Tools log `agent_runs`, `agent_tool_invocations`, and domain audit events in Aethos.

## MCP vs Native Hermes Plugin

### MCP First For Read-Only And Draft Tools

Use MCP when:

- The tool interface is stable.
- The tool can be exposed as a narrow RPC call.
- Hermes can safely discover and call it.
- Tool filtering is sufficient.

Good first MCP tools:

- finance ops check
- AR/AP/WIP status
- report package generation
- Inbox task listing
- document extraction status

### Native Hermes Plugin For Identity-Sensitive Or Write-Capable Tools

Prefer a native plugin when:

- Tool calls need access to Hermes platform/session/user metadata.
- Aethos must enforce external identity mapping before every call.
- The tool needs pre/post hooks for audit mirroring.
- We need custom slash commands like `/aethos-link`, `/aethos-tenant`, `/aethos-status`.

Likely plugin responsibilities:

- Resolve Hermes platform user to Aethos tenant/user.
- Inject current Aethos context into tool calls.
- Mirror session turns into Aethos `chat_messages`.
- Mirror Hermes tool calls into Aethos agent ledger where not already logged by Aethos tools.
- Disable generic dangerous toolsets in production tenant channels.

## Skills And Profile Distribution

Create an Aethos Hermes profile distribution:

```text
integrations/hermes/aethos-atlas-profile/
  distribution.yaml
  SOUL.md
  config.yaml
  mcp.json
  skills/
    aethos-finance-ops-manager/SKILL.md
    aethos-engagement-letter-intake/SKILL.md
    aethos-p2p-bill-pay/SKILL.md
    aethos-r2r-close-controller/SKILL.md
    aethos-collections/SKILL.md
    aethos-audit-evidence/SKILL.md
```

Skill principles:

- Prompts use business outcomes, not internal tool names.
- Skills explain approval boundaries clearly.
- Skills tell Hermes when to call Aethos tools and when to ask a clarifying question.
- Skills discourage use of generic terminal/filesystem tools for tenant finance work.
- Skills instruct Hermes to create Inbox review tasks instead of executing sensitive actions directly.

## Memory Strategy

Hermes memory is useful, but Aethos needs stricter finance memory.

Use three memory classes:

### 1. Hermes Session History

Good for:

- Channel conversation continuity.
- Full-text search across prior conversations.
- User asking "what did we discuss last week?"

Not enough for:

- Aethos in-app audit.
- Tenant-approved business facts.
- Finance records.

### 2. Hermes Built-In Memory

Good for:

- Non-sensitive style and operating preferences.
- Persona-level hints.
- Workflow habits.

Do not use for:

- Client facts.
- Billing terms.
- Bank/tax data.
- Approved finance policy.
- Anything that must be tenant-audited.

### 3. Aethos Memory Provider

Build a Hermes memory provider backed by Aethos:

- `sync_turn` can propose memory candidates to Aethos.
- `prefetch` retrieves tenant/user scoped memory for the current turn.
- Writes require Aethos confidence/approval rules.
- Every memory has provenance and expiry.

Backed by:

- existing `agent_memory_items`, or
- a new `agent_memory_candidates` table if review workflow requires it.

## Session And Chat Sync

If Hermes is used for external channels, Aethos needs a session bridge.

New tables:

- `external_identities`
  - tenant_id
  - user_id
  - platform
  - external_user_id
  - display_name
  - status
  - role
  - linked_at
  - revoked_at

- `conversation_channel_bindings`
  - tenant_id
  - aethos_thread_id
  - hermes_profile
  - hermes_session_id
  - platform
  - platform_conversation_id
  - platform_thread_id
  - created_by_user_id
  - last_synced_at

- `conversation_events`
  - tenant_id
  - thread_id
  - source
  - source_event_id
  - role
  - content_snapshot
  - metadata
  - created_at

Sync requirements:

- A Slack/Teams/Telegram conversation can appear in Aethos Atlas history.
- An in-app Atlas conversation can be handed off to an external channel later.
- Tool evidence and Inbox links are visible regardless of channel.
- Sync failure is non-destructive and retryable.

## Security And Governance

Required controls before write-capable external-channel launch:

- External identity linking controlled by Aethos admin.
- Per-tenant allowlist/pairing policy.
- Per-user RBAC mapped from Aethos roles.
- Generic Hermes terminal/filesystem/browser tools disabled for tenant finance channels unless explicitly allowed for internal admins.
- MCP tools filtered to the minimum useful surface.
- Every write tool routes through Aethos policy and Inbox.
- Aethos owns audit event hashing and immutable finance records.
- Secrets are per profile or per tenant and never shared across profiles.
- Memory writes are scoped and reviewable.
- Channel messages containing attachments are treated as untrusted input.
- Prompt-injection detection remains required for documents and channel messages.

## Observability

Hermes introduces a second runtime that Aethos must observe.

Required:

- Aethos request id/trace id propagated into every MCP/native plugin call.
- Hermes session id and platform source stored on Aethos agent runs.
- Aethos agent ledger records business tool calls.
- Hermes gateway health exposed to Aethos operational health.
- Langfuse trace coverage for Hermes-owned model calls or at minimum Aethos wrapper traces around business tool decisions.
- Per-tenant token/cost attribution.
- Alerts for gateway failure, profile failure, tool failures, pairing abuse, and sync lag.

## Deployment Model

For Hostinger/Docker:

- Add `hermes-gateway` container or sidecar.
- Persist `/data/.hermes` or equivalent volume.
- Mount Aethos profile distribution read-only.
- Store platform tokens and Aethos integration tokens in environment/secret files.
- Add Traefik route only for webhook-based platforms:
  - `atlas-gateway.ishirock.tech`
  - or `hermes.aethos.ishirock.tech`
- Telegram can use polling initially; Slack/Teams typically need HTTPS callbacks.
- Restrict network access to Aethos API and required platform/model providers.

Pilot deployment:

- One Hermes gateway container.
- One profile: `aethos-demo`.
- One external channel: Slack or Telegram.
- One read-only MCP tool and one Inbox-gated draft tool.

Enterprise deployment:

- Profile per dedicated tenant or shared gateway with Aethos tenant-aware plugin.
- Automated profile provisioning/deprovisioning.
- Per-tenant token budgets and profile health.
- Backups for Hermes state if Hermes sessions are product-visible.

## Implementation Plan

### Phase 0 - Technical Spike

Goal:

- Prove Hermes can safely call Aethos tools and preserve Aethos audit requirements.

Build:

- Local Hermes profile named `aethos-demo`.
- Aethos MCP server exposing:
  - `aethos.finance_ops.check`
  - `aethos.inbox.list_open_tasks`
- A native plugin or hook prototype that can see enough platform/session context to map calls to Aethos.
- A sample Aethos skill: finance ops manager.

Acceptance:

- Hermes can answer finance ops status using Aethos API, not invented data.
- Tool call is logged in Aethos with tenant/user/source metadata.
- Generic dangerous toolsets are disabled.

Decision gate:

- If Hermes cannot pass reliable tenant/user/session context to Aethos tools, do not expose write-capable tools through Hermes yet.

### Phase 1 - External Channel Pilot

Goal:

- One external channel works for one tenant.

Build:

- Telegram or Slack Hermes gateway.
- Static allowlist or Aethos-admin-approved pairing.
- Session bridge table.
- Mirror Hermes conversation turns into Aethos chat history.
- Add Inbox-gated tool:
  - `aethos.documents.rerun_extraction`, or
  - `aethos.finance_ops.create_action_plan`.

Acceptance:

- User asks in Slack/Telegram for finance ops status.
- User uploads or references a document and asks for retry.
- Aethos creates an Inbox task instead of executing sensitive action directly.
- The conversation appears in Aethos Atlas history.

Tests:

- Channel smoke test.
- Aethos API contract for identity mapping.
- E2E: external prompt -> Aethos tool -> Inbox task -> in-app review.

### Phase 2 - Aethos Profile Distribution

Goal:

- Package repeatable Aethos-specific Hermes setup.

Build:

- `SOUL.md` for Aethos Atlas.
- Skills for O2C, P2P, R2R, collections, audit evidence.
- MCP config with tool filtering.
- Deployment docs.
- Seed/demo profile.

Acceptance:

- A new tenant pilot profile can be provisioned from the distribution.
- Skills consistently route business prompts to Aethos tools.
- Tool names are not required from users.

### Phase 3 - Aethos Memory Provider

Goal:

- Use Aethos as the tenant-governed memory store.

Build:

- Hermes memory provider plugin.
- Memory candidate review path.
- Tenant/user/client/document scoped retrieval.
- Memory expiry and provenance.

Acceptance:

- Approved extraction correction is recalled in a later channel session.
- Cross-tenant retrieval fails closed.
- Memory is visible/auditable in Aethos.

### Phase 4 - Production Multi-Tenant Model

Goal:

- Decide between profile-per-tenant and shared tenant-aware Hermes deployment.

Build:

- Provisioning automation.
- Health checks.
- Secret rotation.
- Tenant budget tracking.
- Profile/session backup and deletion.
- Admin UI for channel linkage and revocation.

Acceptance:

- Admin can enable/disable a tenant channel.
- User revocation immediately blocks external-channel tool access.
- Tenant deletion removes or archives Hermes sessions according to retention policy.

## Impact On Aethos

### Backend

New modules:

- Aethos MCP server or native Hermes integration plugin.
- External identity mapping.
- Channel session bridge.
- Conversation event ingestion.
- Aethos-backed memory provider.
- Hermes health/observability ingestion.

Changed modules:

- Chat history model must support external source/platform metadata.
- Agent ledger must include external channel and Hermes session references.
- Inbox must support tasks created from external channels.
- Document extraction retry must work without relying on in-app UI state.

### Frontend

Changes:

- Atlas thread history shows source channel badges.
- Thread detail can show linked Slack/Teams/Telegram session metadata.
- Admin/settings UI for channel linkage and revocation.
- Memory review UI later.

### Database

Likely migrations:

- `external_identities`
- `conversation_channel_bindings`
- `conversation_events` or expanded `chat_messages` metadata
- `agent_memory_candidates` if memory review is separate from `agent_memory_items`
- indexes on tenant/source/session ids
- RLS policies for every new table

### Infra

Changes:

- Add Hermes gateway container/service.
- Add persistent volume.
- Add webhook route if using Slack/Teams/WhatsApp/etc.
- Add profile distribution deployment.
- Add gateway health checks and logs.
- Add secrets for platform tokens and Aethos integration credentials.

### QA

New scenario classes:

- Channel identity linking.
- Cross-tenant channel isolation.
- External prompt to Aethos read-only tool.
- External prompt to Inbox-gated write tool.
- External document attachment to extraction retry.
- External conversation visible in Aethos Atlas.
- Memory recall across external sessions.
- User revocation and tenant deletion.

## Risk Assessment

High risks:

- Tenant data leakage through shared Hermes memory/session state.
- Weak per-user audit if tools only use tenant-scoped service tokens.
- Split-brain conversation history between Hermes and Aethos.
- External-channel users bypassing Aethos RBAC.
- Generic Hermes tools being available in production finance channels.
- Langfuse/audit gaps for model calls owned by Hermes.

Medium risks:

- Operational complexity of profiles/containers at scale.
- Version drift from git-based Hermes dependency.
- Channel provider webhook and token management.
- Message/file attachment semantics differ across platforms.
- Cost attribution across Hermes profiles and Aethos tenants.

Mitigations:

- Start read-only.
- Use profile-per-tenant for pilots.
- Disable generic risky toolsets.
- Route all business writes through Aethos tools and Inbox.
- Mirror sessions into Aethos.
- Build identity mapping before write tools.
- Use Aethos memory provider for tenant facts.

## Recommendation

Use a staged hybrid path:

1. Fix Aethos-native chat history and document retry first, because this is needed regardless of Hermes.
2. Run a Hermes sidecar spike for one tenant and one channel.
3. Expose Aethos through a narrow MCP server for read-only tools first.
4. Add a native Hermes plugin if MCP cannot carry enough tenant/user/session context.
5. Keep Aethos as the system of record for tenant data, audit, memory, and approvals.
6. Adopt Hermes for external channels and skills if the spike proves identity, audit, and session sync.
7. Revisit replacing the in-app Atlas runtime only after the sidecar pattern works in production.

## Open Decision Questions

1. First external channel: Slack, Teams, or Telegram?
2. Pilot isolation: profile-per-tenant or dedicated container-per-tenant?
3. Should Hermes sessions be product-visible in Aethos immediately, or only after the channel pilot proves stable?
4. Should Aethos expose tools through MCP first, or build a native Hermes plugin first because of identity/audit needs?
5. Should tenant business memory writes require Inbox approval, admin approval, or confidence-based auto-promotion?

## Recommended First Hermes Issue

Title: Spike Hermes sidecar for Aethos Atlas external-channel finance ops

Scope:

- Add local Hermes profile/distribution prototype.
- Add read-only Aethos MCP server with finance ops check.
- Add one Aethos Atlas skill.
- Prove one external channel can call the read-only tool.
- Record Aethos agent ledger evidence with source channel/session metadata.
- Document blockers around identity, memory, audit, and deployment.

Out of scope:

- Write-capable actions beyond Inbox-gated prototype.
- Full multi-tenant provisioning.
- Replacing in-app Atlas.
- Production channel rollout.
