# Aethos PS — Architecture

> **Owner**: Vastu (Chief Architect)
> **Status**: Skeleton (never filled). Fill tracked in #527. Until then use the pointers below.
> **Source of truth for now**: [`docs/adr/`](../adr/) (ADR 0001–0005), [`docs/PLAN.md`](../PLAN.md) §0.2 drift note + §3–§12, [`docs/architecture/`](../architecture/) (Nous/Hermes), [`docs/infra/HOSTINGER_DEPLOYMENT.md`](../infra/HOSTINGER_DEPLOYMENT.md).

This document is the durable architecture reference. The plan covers it in narrative form; this document is the structured, ADR-indexed view.

## Sections (to be filled by Vastu)

1. **System diagram** — services, datastores, queues, external providers.
2. **Layering** — Router → Service → Repository → DB or external API.
3. **Service boundaries** — what owns what; ownership map per `app/` subpackage.
4. **Data model** — links to `supabase/migrations/` per table; ER diagram.
5. **Agent architecture** — Pydantic Graph orchestration, deps injection, tool catalog.
6. **HITL pipeline** — `agent_suggestions` + `hitl_tasks`; promotion/demotion workers.
7. **Multi-tenancy & RLS** — how tenant scoping is enforced at app + DB.
8. **Auth & RBAC** — Supabase Auth, JWT claims, role gates.
9. **Money & accounting** — Decimal types, journal patterns, FX freeze-at-post, period locks.
10. **Stripe integration** — subscriptions, Payment Links, Connect Standard, Tax.
11. **Document pipeline** — upload → extraction worker → agent → suggestion/HITL.
12. **Observability** — Langfuse (LLM), Pydantic Logfire (dev), structured logs, trace IDs.
13. **Deployment topology** — Hostinger VPS, Docker Compose, Traefik, Supabase (see `docs/infra/HOSTINGER_DEPLOYMENT.md`).

## Architecture Decision Records

ADRs live in [`docs/adr/`](../adr/). Numbered ADR-001, ADR-002, …

Process: see [`docs/team/SDLC_PROTOCOL.md`](SDLC_PROTOCOL.md) — RFC / ADR Process.

## Until this is filled

- Backend agents read [`docs/PLAN.md`](../PLAN.md) §3, §4, §5, §6, §10.
- Frontend agents read [`docs/PLAN.md`](../PLAN.md) §7.
- All agents read [`agent-harness/core/architecture-patterns.md`](../../agent-harness/core/architecture-patterns.md).

## Current pointers (2026-09-03)

- Deployment topology is **Hostinger + Docker Compose + Traefik**, not Vercel/Cloud Run/Upstash (section 13 above is stale).
- Agents are OpenAI-compatible tool loops, not PydanticAI/Pydantic Graph (section 5 above is stale).
- ~81 tables across 115 migrations; see `docs/PLAN.md` §0.2 for the deltas from the 37-table plan.

## Changelog

### [2026-05-19] — Skeleton created
