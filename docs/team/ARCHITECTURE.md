# Aethos PS — Architecture

> **Owner**: Vastu (Chief Architect)
> **Status**: Skeleton — to be filled by Vastu in Week 1 (PLAN §13).
> **Source of truth for now**: [`docs/PLAN.md`](../PLAN.md) §3-§12.

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
13. **Deployment topology** — Vercel, Cloud Run, Supabase, Upstash.

## Architecture Decision Records

ADRs live in [`docs/adr/`](../adr/). Numbered ADR-001, ADR-002, …

Process: see [`docs/team/SDLC_PROTOCOL.md`](SDLC_PROTOCOL.md) — RFC / ADR Process.

## Until this is filled

- Backend agents read [`docs/PLAN.md`](../PLAN.md) §3, §4, §5, §6, §10.
- Frontend agents read [`docs/PLAN.md`](../PLAN.md) §7.
- All agents read [`agent-harness/core/architecture-patterns.md`](../../agent-harness/core/architecture-patterns.md).

## Changelog

### [2026-05-19] — Skeleton created
