# PLAN: Aethos for Professional Services — Comprehensive Agent-First PS ERP

> **Status**: DRAFT v4 — pending Founder approval (changelogs in §0.1)
> **Owner**: Vishwa (CPTO)
> **Created**: 2026-05-18 · **v2**: 2026-05-18 · **v3**: 2026-05-19 · **v4**: 2026-05-19
> **Goal**: Build a standalone agent-first PS ERP in a **separate `aethos-ps` repository** (sister product to `aethos`) — branded as **"Aethos"** (Linear-style minimalism; services-specific logo lockup) — in-market within **6 weeks** across **5 launch markets: US · UK · SG · IN · AU**.
> **Repo location**: `~/dev/aethos-ps` (this directory). Companion product repo at `~/dev/aethos`.

---

## 0. TL;DR

- **What**: A new sibling product `aethos-ps` (folder, backend, frontend, agents, DB) that delivers a *comprehensive* PS ERP — engagements, projects, time, expenses, billing (T&M / fixed / retainer / milestone / capped), AR, AP for project costs, GL with double-entry, reports — with a **chat-first, document-upload-first UX** wrapped around AI agents.
- **How different from erpcore PS**: Instead of dense forms, the primary interaction is **(a) chat with the AI ("create an invoice for Acme for May time")** or **(b) drop a document and let agents extract → propose → HITL approve → post**. Traditional CRUD screens still exist as a fallback / power-user surface, but the home page is the copilot.
- **Stack**: Angular 19 + Tailwind + Material (consistent with erpcore) on a **new** Supabase project; FastAPI + PydanticAI backend; Stripe for SaaS subscriptions *and* per-invoice Payment Links.
- **Timesheet**: stays as a thin `time_entries` table inside aethos-ps (so billing works), but the rich timesheet entry / approvals UX is deferred to a separate module to be built later.
- **Ship target**: **6 weeks** to a public beta in **5 launch markets — US, UK, Singapore, India, Australia** — with Stripe sandbox-driven signup, paid plans in 5 currencies, Stripe Connect for firm payouts, multi-currency AR + initial AP bill-pay, and at least 3 friendly-design-partner tenants live.

---

## 0.1 Changelog from v1 / v2 / v3

### v3 → v4 (this revision)

Two founder calls drove v4:

| Topic | v3 | v4 |
|---|---|---|
| Brand | "Aethos" (distinct name) | **"Aethos"** — keep parent brand; services-specific logo lockup; Linear-style minimalism ("Aethos, for professional services") |
| Codebase | Sibling folder `aethos-ps/` in same `aethos` repo | **Separate repo** `aethos-ps` at `~/dev/aethos-ps` — cleaner blast radius, faster AI agent context, independent release cadence |
| Brand-identity scope (Chitra) | Full identity (logo + palette + type + tone) | **Services lockup + sub-mark only** — reuse parent palette/type from `aethos` repo; ~2 days vs. ~1 week |
| Domain | Register new domain | **Founder assigns from existing Aethos domain pool** — no registration in Week 1 |
| Repo/folder structure | `aethos-ps/{backend,frontend,...}` inside aethos | Repo root IS the product — no outer wrapper. Top-level: `backend/`, `frontend/`, `shared/`, `infra/`, `docs/`, `.github/`, `.claude/` |
| Sister repo coupling | Implicit (same monorepo) | Explicit: `aethos-ps` is fully standalone; shared utilities (money/Decimal helpers, journal patterns, agent base classes, brand assets) are **copied** in Week 1, not symlinked. Future extraction to `@aethos/shared` is optional in v1.x. |
| SDLC repo of record | `venkateshbr/aethos` GitHub Issues | **New repo** `venkateshbr/aethos-ps` (or chosen name) GitHub Issues. Lifecycle / labels / role guards mirror parent. |
| Ports | 8010 / 4200 (collide w/ aethos) | **8011 / 4201** for backend / frontend dev — non-colliding when both products run locally |

Net impact:
- **Tables**: unchanged (37)
- **Agents**: unchanged (13)
- **Timeline**: **6 weeks held** — repo bootstrap is ~1 day, offset by no domain/brand-identity work
- **Risk added**: cross-repo refactor cost when erpcore patterns evolve — accepted; brand assets copied (re-sync ~twice/yr)

### v2 → v3

Founder responses to v2 Round-3 questions baked in:

| Topic | v2 | v3 |
|---|---|---|
| Brand | shortlist of 5 | **"Aethos"** chosen — rationale, domain plan, TM caveat in §17 |
| Tax rate seed | open | **Seed common rates** for US (per-state placeholders), UK (VAT 20/5/0), SG (GST 9), AU (GST 10), IN (GST 0/5/12/18/28) |
| Stripe Connect application fee | open | **0%** confirmed |
| Bill-pay file format | open | **NACHA + Universal CSV at launch** (all 5 markets) → native BACS / ABA / GIRO / NEFT in v1.1 |
| Pricing tier | confirmed $29/$79/$199 | Confirmed — plus **5-currency Stripe Prices**: $29/£25/S$39/₹2,499/A$45 (Starter) etc. (§8.1) |
| Free tier | open | **Trial-only with card capture** (14 days) — no permanent free tier in v1 |
| Outreach tone | open | **Founder-personal voice** confirmed |
| Launch geography | open | **5 markets day 1**: US · UK · SG · IN · AU (Stripe Connect supported in all 5; copy/support in English) |
| Brand identity | open | **Chitra delivers 2-3 logo + palette + type directions** in Week 1; founder picks |
| Stripe Tax | n/a | **Enabled** for SaaS subs (auto-calculates GST for IN/AU/SG, VAT for UK) |

Net impact:
- **Tables**: 37 → **37** (no new tables; tax_rates row count grows from seed data)
- **Agents**: 13 → **13** (no new agents)
- **Markets**: 1 → **5** (multi-currency was already in v2; we add tax regimes, locale plumbing, 2 bill-pay formats)
- **Timeline**: **6 weeks held** by phasing native bank-file formats (only NACHA + Universal CSV at launch; native BACS/ABA/GIRO/NEFT in v1.1)
- **Risk added**: 5-market support workload on a small team — mitigated by English-only support, async-only SLA in v1, design partners initially US-heavy

### v1 → v2

Founder responses to v1 open questions (Round 2) baked into v2:

| Topic | v1 | v2 |
|---|---|---|
| Brand | `ps.aethos.app` sub-brand | **Distinct brand name** — 5 candidates proposed in §17 (you to pick) |
| Stripe Connect | v1.1 | **In v1** — Standard accounts, per-tenant payouts (§8.4) |
| Multi-currency | USD only | **Enabled day 1** — per-tenant base currency, per-engagement / per-invoice override (§8.5) |
| Tax | Deferred | **Simple `tax_rates` table** + per-line tax (§4.10) |
| Email | TBD | **Resend** (cleaner templating + DX for branded invoice emails) |
| Pricing | TBD | **Starter $29 / Growth $79 / Pro $199 / mo** confirmed |
| Design partners | TBD | **None yet** — outreach plan added (§18) — Netra-owned |
| Agent autonomy | All L2 | **All L2 at signup, auto-promote eligibility to L3** based on confidence + correction history (§6.5) |
| AP scope | Extract + post only | **Initial bill payments** — `bills`, `bill_payments`, NACHA/CSV bank export in v1, Stripe-Connect-vendor in v1.1 (§11.5) |
| Marketing landing | TBD | **Static Angular page** in same project at brand root URL |
| Old erpcore PS code | TBD | **Delete 4 weeks after GA** |
| Branching | TBD | **Develop on `main`** — separate folder = low blast radius |

Net impact:
- **Tables**: 33 → **37** (+ `tax_rates`, `bills`, `bill_lines`, `bill_payments`; Stripe Connect fields folded into `tenants`)
- **Agents**: 12 → **13** (+ `bill_pay_agent`)
- **New mechanism**: Autonomy auto-promotion service (background worker + Inbox card flow)
- **Timeline**: 5 weeks → **6 weeks** to public beta (added: Stripe Connect, multi-currency, bill payments, tax, autonomy worker, outreach pipeline, static landing)

---

## 1. Decisions Confirmed (from Round 1 + Round 2 Q&A)

| # | Decision | Choice |
|---|---|---|
| D1 | Codebase / DB isolation | **Separate repo `aethos-ps`** (sister to `aethos`) at `~/dev/aethos-ps`, **new Supabase project** (own DB, own auth, own RLS, own migrations) |
| D2 | Frontend stack | **Angular 19 + Tailwind + Angular Material** (reuse erpcore stack, dark slate theme) |
| D3 | Data model | **Full comprehensive schema, restructured + simplified** — keep all real PS concepts, collapse over-normalized tables, add agent/HITL/document tables |
| D4 | Auth & signup | **Standalone Supabase Auth** + **Stripe Setup Intent** with sandbox test card prefilled in dev → 14-day trial subscription |
| D5 | Brand | **"Aethos"** — parent brand carried through, no separate name; product positions as *"Aethos, for professional services"* (Linear-style). Services-specific logo lockup from Chitra. See §17. |
| D6 | Stripe Connect | **Standard accounts, in v1** — firms onboard their own Stripe account and receive payouts directly |
| D7 | Multi-currency | **Enabled day 1** — tenant base currency + per-engagement / per-invoice currency override; FX rates table; reports in base currency |
| D8 | Tax | **Simple `tax_rates` table** (tenant-defined), per-line tax on invoices and bills; no jurisdiction logic |
| D9 | Email | **Resend** for transactional + branded invoice emails (DMARC/SPF setup per tenant deferred to v1.1) |
| D10 | Pricing | **Starter $29 · Growth $79 · Pro $199 / mo** (Stripe Products + Prices created in setup) |
| D11 | Design partners | None yet — **Netra owns outreach** (§18); target 3 firms confirmed by end of Week 2 |
| D12 | Agent autonomy | **All agents at L2 (suggest) at signup.** Background worker tracks per-(agent, action_type) approval rate + avg confidence; when thresholds met, surfaces an Inbox card *"Promote `expense_extractor` to L3?"* — founder/admin approves explicitly (§6.5) |
| D13 | AP scope | **Initial bill payments in v1** — vendor invoices extracted → `bills` → AP journal; pay-batch UI; **NACHA/CSV bank export** for actual money movement; Stripe-Connect-vendor direct pay in v1.1 |
| D14 | Marketing landing | **Static Angular page** in same project (no separate Next.js); brand root URL serves landing → /signup → app shell |
| D15 | Old erpcore PS code | **Delete 4 weeks after aethos-ps GA**, after any internal demos / partner accounts migrate |
| D16 | Branching | **Develop on `main`** — `aethos-ps/` folder is a separate tree, blast radius is zero |
| D17 | Launch markets | **5 markets day 1: US · UK · SG · IN · AU** — common: English-speaking; Stripe Connect Standard available in all; 5 base currencies preloaded; per-market tax seed |
| D18 | Tax seed | Common rates pre-seeded per market — US (per-state placeholders, admin enables), UK (VAT 20 / 5 / 0), SG (GST 9), AU (GST 10), IN (GST 0 / 5 / 12 / 18 / 28); admin can override per-line |
| D19 | Bill-pay file format | **v1: NACHA (US) + Universal CSV (works on any bank's bulk-upload portal in all 5 markets)** · **v1.1**: native BACS (UK) / ABA (AU) / GIRO (SG) / NEFT (IN) |
| D20 | Stripe Tax | **Enabled** for SaaS subscriptions — auto-calculates GST/VAT per buyer location for our $29/$79/$199 plans |
| D21 | Free tier | **No free tier in v1** — 14-day trial with card capture (validates intent + smooths conversion) |
| D22 | Outreach voice | **Founder-personal** — DMs and posts go out from Founder account; product brand develops over time |

---

## 2. Goals & Non-Goals

### Goals (v1, 6-week target)
1. **Agent-first home**: chat is the primary surface; tool-calls render inline; uploaded files (engagement letter, receipt, vendor invoice) auto-trigger extraction agents.
2. **Comprehensive PS ERP coverage**: engagements with multiple billing arrangements, projects + phases + resource assignments, time entries (lightweight UI; deep timesheet module deferred), project expenses, multi-model invoicing, billing runs, AR, **AP + initial bill payments**, GL.
3. **HITL inbox**: every AI-proposed mutation (invoice, journal, expense, engagement, bill pay) lands in a review queue unless autonomy settings allow auto-apply at high confidence. Autonomy **auto-promotes from L2 → L3** based on confidence + correction history (with admin confirmation).
4. **Stripe end-to-end**:
   - SaaS signup with Setup Intent (sandbox card in dev) → subscription
   - Per-invoice **Payment Links** → webhook → auto-mark paid → journal
   - **Stripe Connect Standard** per tenant — customer payments flow directly to the firm's connected account (Aethos takes a configurable application fee, 0% v1)
5. **Multi-currency**: tenant base currency + per-engagement / per-invoice currency override + FX rates table; journal lines store base-currency equivalents.
6. **Simple tax**: tenant-defined `tax_rates`, per-line tax on invoices and bills.
7. **Modern visual feel**: dark slate, glass cards, micro-interactions, AI shimmer states, confidence-coloured chips, generative inline cards in chat. *Looks like a 2026 AI product, not a 2014 SaaS form.*
8. **Independently deployable**: own Vercel project, own backend service, own Supabase, own Stripe keys, own brand domain.
9. **GAAP double-entry preserved** end-to-end (DB triggers, Decimal money, balanced journals).

### Non-Goals (v1)
- Rich timesheet entry UI (calendar, week view, approvals chain) → deferred to a separate **aethos-time** sub-product. v1 ships only the `time_entries` table + chat-driven entry + a simple list view.
- Multi-currency consolidation reporting (FX rates stored; conversion at invoice creation only; no parallel-currency books).
- Procurement / PO / multi-step vendor approval workflows (vendor bills can be uploaded, extracted, posted — but no PO matching).
- Fixed-asset register, depreciation, lease accounting.
- Payroll.
- Full ASC 606 revenue-recognition automation (we store WIP and recognise on billing in v1; rev-rec agent is v1.1).
- Mobile app (responsive web only).
- Migration of any existing erpcore PS tenant data into aethos-ps (clean Supabase, no port).

---

## 3. Codebase Layout

The repo root **is** the product — no outer `aethos-ps/` wrapper. Scaffolded:

```
~/dev/aethos-ps/
  README.md
  CLAUDE.md                        # Agent instructions (mirror of aethos with PS-specific deltas)
  .gitignore
  .github/workflows/               # CI (mirror of aethos role-guard + status-lifecycle)
  .claude/agents/                  # Agent definition files (copied + adapted from aethos)
  backend/
    app/
      __init__.py
      main.py                      # FastAPI entry
      api/v1/                      # Routers (chat, engagements, projects, invoices, …)
      services/                    # Business logic
      agents/                      # PydanticAI agents + Pydantic Graph workflows
      models/                      # Pydantic request/response schemas
      domain/                      # Money, enums, rules, journal patterns (copied from aethos)
      repositories/                # Supabase data access
      events/                      # Domain events + handlers
      workers/                     # ARQ workers
      core/                        # Config, auth, RBAC, middleware
    supabase/migrations/           # Fresh migration set (numbered from 0001)
    tests/
    pyproject.toml                 # to be added Week 1
    Dockerfile                     # to be added Week 1
  frontend/
    src/app/
      core/                        # Services, guards, interceptors
      shared/                      # Reusable components (chat bubble, hitl card, money pipe)
      features/
        copilot/                   # The chat home
        inbox/                     # HITL queue
        engagements/ · projects/ · clients/ · invoices/ · billing-runs/
        expenses/ · time-entries/ · payments/ · reports/ · people/
        onboarding/ · settings/
      app.routes.ts                # to be added Week 1
      app.config.ts                # to be added Week 1
    src/assets/brand/              # Aethos services lockup (Chitra Week 1)
    package.json                   # to be added Week 1 (ng new in place)
    angular.json
    tailwind.config.js
  shared/
    schemas/                       # JSON Schemas / OpenAPI artifacts shared FE↔BE
  infra/
    vercel/                        # Frontend deploy config
    cloudrun/                      # Backend + worker deploy config
    supabase/                      # Supabase project config
  docs/
    PLAN.md                        # This document
    adr/                           # Architecture Decision Records
```

Notes:
- **Standalone repo** — `aethos-ps` is fully independent of `aethos`. No symlinks, no submodules.
- **Copy-then-adapt** the most reusable aethos modules in Week 1: `domain/money.py`, journal patterns, `BaseService`, agent base/registry, Stripe billing provider, agent definitions. Re-sync only when meaningfully helpful (not automatically).
- **Brand assets** copied from aethos's existing palette/type, with Chitra adding a services-specific logo lockup. Stored in `frontend/src/assets/brand/`.
- Old `erpcore/.../ps_*` files in aethos repo stay in place for 4 weeks post-GA, then deleted in a follow-up PR.
- **Dev ports**: backend 8011 / frontend 4201 — non-colliding with aethos's 8010 / 4200 so both can run locally side-by-side.

---

## 4. Data Model — 33 Tables

> Design principle: keep the *real* PS domain concepts, collapse over-normalised structures, add a dedicated layer for AI/HITL/document state. All money is `NUMERIC(15,2)`, all entities have `tenant_id`, `created_at`, `updated_at`, `deleted_at` (soft delete), and RLS by tenant.

### 4.1 Tenancy, Auth, Billing (5)
| Table | Purpose | Key fields |
|---|---|---|
| `tenants` | Workspaces | id, name, slug, base_currency, timezone, stripe_customer_id (SaaS billing), stripe_connect_account_id, stripe_connect_status, stripe_connect_charges_enabled, stripe_connect_payouts_enabled, plan_tier, trial_ends_at, brand_name, brand_logo_url, status |
| `tenant_users` | Membership + simple role | tenant_id, user_id (auth.users), role (`owner`/`admin`/`manager`/`staff`/`finance`), invited_at, joined_at |
| `subscriptions` | Stripe sub state | tenant_id, stripe_subscription_id, price_id, status, current_period_end, cancel_at_period_end |
| `payment_methods` | Cards on file | tenant_id, stripe_payment_method_id, brand, last4, exp_month, exp_year, is_default |
| `agent_autonomy_settings` | Per-agent autonomy | tenant_id, agent_name, action_type, level (`L0`/`L1`/`L2`/`L3`), confidence_threshold |

> **RBAC**: we use a *role enum* not a full perms matrix in v1. The 5 roles map to ~12 policy predicates in code. Reduces table count by 3 and complexity by a lot. Re-introduce a perms matrix only when a customer asks.

### 4.2 People (1)
| Table | Purpose | Key fields |
|---|---|---|
| `employees` | Billable resources | tenant_id, name, email, title, department, employment_type, cost_rate, default_bill_rate, available_hours_per_week, manager_id, skills (JSONB), tenant_user_id (nullable), status |

### 4.3 Clients & CRM (1)
| Table | Purpose | Key fields |
|---|---|---|
| `clients` | Customer firms | tenant_id, name, legal_name, address (JSONB), currency, billing_email, billing_address (JSONB), tax_id, payment_terms_days, primary_contact (JSONB), contacts (JSONB array), stripe_customer_id (nullable, for Connect) |

> Contacts collapsed into JSONB array. Splits out only if a customer wants per-contact roles/permissions.

### 4.4 Engagements (4)
| Table | Purpose | Key fields |
|---|---|---|
| `engagements` | Commercial container | tenant_id, client_id, name, type (`consulting`/`managed_services`/`project`/`retainer`), status, start_date, end_date, contract_value, currency, sow_document_id, billing_terms (JSONB — collapses billing_arrangements), retainer_balance, nte_amount, owner_employee_id |
| `engagement_documents` | SOWs, ELs, addenda | tenant_id, engagement_id, document_id, kind (`engagement_letter`/`sow`/`addendum`/`change_order`/`other`) |
| `change_orders` | Scope changes | tenant_id, engagement_id, summary, additional_value, status (`draft`/`submitted`/`approved`/`rejected`), approved_by, approved_at, document_id |
| `rate_cards` | Named rate sets | tenant_id, name, currency, effective_from, effective_to, entries (JSONB array of `{role/employee_id, rate}`), default_for_tenant |
| `rate_card_client_overrides` | Per-client rate tweaks | tenant_id, rate_card_id, client_id, overrides (JSONB), effective_from, effective_to |

> `billing_terms` JSONB on engagement collapses the previous 3-table `billing_arrangements` graph into a structured doc: `{model, rate_card_id, budget_hours, budget_amount, nte_amount, billing_frequency, milestones: [...]}`. Indexed via GIN.

### 4.5 Projects (3)
| Table | Purpose | Key fields |
|---|---|---|
| `projects` | Work units under engagement | tenant_id, engagement_id, name, project_manager_id, status, planned_start, planned_end, actual_start, actual_end, budget_hours, budget_amount, currency |
| `project_phases` | Phased delivery | tenant_id, project_id, name, sequence, planned_hours, planned_amount, status, billing_model_override (nullable) |
| `project_assignments` | Who's on it | tenant_id, project_id, employee_id, role, allocation_pct, bill_rate_override, start_date, end_date |

> `project_tasks` + `task_assignments` are **dropped**. In v1 we track at phase granularity. Task-level granularity is a v1.2 enhancement only if customers demand it. Time entries can still reference a phase.

### 4.6 Time & Expenses (2)
| Table | Purpose | Key fields |
|---|---|---|
| `time_entries` | Billable hours | tenant_id, employee_id, project_id, phase_id (nullable), entry_date, hours (NUMERIC(8,4)), billable, bill_rate, cost_rate, notes, status (`draft`/`submitted`/`approved`/`billed`/`written_off`), source (`chat`/`api`/`import`) |
| `project_expenses` | Billable expenses | tenant_id, project_id, employee_id, expense_date, amount, currency, category, billable, markup_pct, receipt_document_id, status (`draft`/`submitted`/`approved`/`reimbursed`/`billed`) |

> No `timesheets` header table in v1. Approval per `time_entry` (matches the agent-first flow: agent approves on submit unless flagged). Timesheet *grouping* can be a query in the future timesheet module.

### 4.7 Billing & AR (4)
| Table | Purpose | Key fields |
|---|---|---|
| `invoices` | AR documents | tenant_id, number (DB sequence), client_id, engagement_id, type (`tm`/`fixed_fee`/`milestone`/`retainer_invoice`/`retainer_draw`/`expense_only`), status, issue_date, due_date, currency, subtotal, tax, total, amount_paid, billing_run_id (nullable), stripe_payment_link_id (nullable), stripe_payment_link_url (nullable), stripe_invoice_id (nullable), journal_entry_id (nullable), notes, agent_drafted_by, hitl_task_id (nullable) |
| `invoice_lines` | Line items | tenant_id, invoice_id, description, qty, rate, amount, source_type (`time_entry`/`expense`/`milestone`/`adhoc`), source_id (nullable) |
| `billing_runs` | Pre-bill batch | tenant_id, name, period_start, period_end, status (`draft`/`reviewed`/`approved`/`invoiced`), created_by_agent, summary (JSONB), engagement_filter (JSONB) |
| `payments` | AR receipts | tenant_id, invoice_id, amount, payment_date, method (`stripe`/`ach`/`wire`/`check`/`manual`), stripe_payment_intent_id, journal_entry_id, notes |

> `billing_run_items` is **dropped**. Invoices reference `billing_run_id` directly. A billing run's `summary` JSONB stores the pre-bill proposal before invoices materialise.

### 4.8 Accounting (5)
| Table | Purpose | Key fields |
|---|---|---|
| `accounts` | Chart of Accounts | tenant_id, code, name, type (`asset`/`liability`/`equity`/`revenue`/`expense`), is_system, parent_id |
| `journal_entries` | GL header | tenant_id, entry_date, source (`invoice`/`payment`/`expense`/`manual`/`fx`/`adjustment`), source_id, posted, posted_at, posted_by, agent_drafted_by |
| `journal_lines` | GL detail | tenant_id, journal_entry_id, account_id, debit, credit, currency, fx_rate, base_amount, line_memo |
| `period_locks` | Close gates | tenant_id, period_start, period_end, locked_by, locked_at |
| `fx_rates` | Daily rates | tenant_id, base_currency, quote_currency, rate_date, rate, source |

> DB **triggers** auto-create journal entries on: invoice sent, payment received, expense approved, project_expense billed. Mirrors erpcore pattern but in the new Supabase project.

### 4.9 AI / Documents / HITL / Chat (6)
| Table | Purpose | Key fields |
|---|---|---|
| `documents` | Uploaded files | tenant_id, storage_path (Supabase Storage), mime, sha256, original_filename, doc_type (`engagement_letter`/`receipt`/`vendor_invoice`/`bank_statement`/`other`), entity_type, entity_id (nullable), uploaded_by_user_id, page_count, status (`uploaded`/`extracting`/`extracted`/`failed`) |
| `extraction_results` | Agent output per doc | tenant_id, document_id, agent_name, structured_output (JSONB), confidence, model_used, tokens_used, latency_ms, status |
| `agent_suggestions` | Proposed mutations | tenant_id, agent_name, suggestion_type (`create_invoice`/`create_expense`/`create_engagement`/`draft_journal`/`adjust_rate`/`send_reminder`/...), payload (JSONB), confidence, status (`pending`/`approved`/`rejected`/`auto_applied`/`expired`), created_for_user_id, decided_by_user_id, decided_at, related_entity_type, related_entity_id |
| `hitl_tasks` | Review queue items | tenant_id, kind, title, summary, suggestion_id (nullable), entity_type, entity_id (nullable), assigned_to_user_id, due_at, priority (`low`/`med`/`high`/`urgent`), status (`open`/`approved`/`rejected`/`escalated`/`auto`), decided_at |
| `chat_threads` | Conversations | tenant_id, user_id, title, summary, last_message_at, archived |
| `chat_messages` | Chat history | tenant_id, thread_id, role (`user`/`assistant`/`tool`/`system`), content, tool_calls (JSONB), tool_results (JSONB), document_ids (UUID[]), suggestion_ids (UUID[]), tokens_in, tokens_out, model_used, created_at |

> **Why both `agent_suggestions` and `hitl_tasks`?** `agent_suggestions` is the *agent's output* (immutable record of what the AI proposed + confidence). `hitl_tasks` is the *human-facing work item* with assignment, priority, due date. One suggestion may spawn multiple tasks (e.g. a billing run suggestion → 12 invoice review tasks).

> **Langfuse-tracked observability** (token spend, latency, prompt versions) lives in Langfuse — we do **not** duplicate `agent_runs` in our DB.

### 4.10 Tax (1)
| Table | Purpose | Key fields |
|---|---|---|
| `tax_rates` | Tenant-defined tax codes | tenant_id, code (e.g. `VAT-20`, `GST-18`, `CA-SALES-8.25`), name, rate (NUMERIC(7,4) — fraction, e.g. 0.2000), is_active, country (nullable), accounting_account_id (the GL account this tax posts to), is_seeded (true for system-seeded rates) |

> Each `invoice_lines` and `bill_lines` row carries `tax_rate_id` (nullable) and `tax_amount`. No jurisdiction logic in v1 — admin picks the right code; agents may suggest one based on client/vendor country.

> **Seeded at tenant creation** based on `tenants.country`:
> - **US**: empty by default (sales tax varies wildly by state/city); admin enables per-state codes from a built-in catalog
> - **UK**: `VAT-20` (standard), `VAT-5` (reduced), `VAT-0` (zero-rated)
> - **SG**: `GST-9`
> - **AU**: `GST-10`, `GST-0` (exports)
> - **IN**: `GST-0`, `GST-5`, `GST-12`, `GST-18`, `GST-28` (admin can split into CGST/SGST/IGST later in v1.1)

### 4.11 Accounts Payable & Bill Payments (3)
| Table | Purpose | Key fields |
|---|---|---|
| `bills` | Vendor invoices (AP) | tenant_id, number (vendor's invoice #), vendor_id (FK clients — vendors live in clients table with `kind='vendor'`), bill_date, due_date, currency, subtotal, tax, total, amount_paid, status (`draft`/`approved`/`scheduled`/`paid`/`void`), source (`upload`/`chat`/`manual`/`recurring`), source_document_id (nullable), project_id (nullable — for billable project costs), journal_entry_id, agent_drafted_by, hitl_task_id |
| `bill_lines` | Bill line items | tenant_id, bill_id, description, qty, rate, amount, account_id (GL expense account), tax_rate_id, tax_amount, project_id (nullable), expense_category |
| `bill_payments` | Pay batches | tenant_id, name, payment_date, status (`draft`/`approved`/`exported`/`settled`/`failed`), source_bank_account_id, total_amount, currency, method (`ach_nacha`/`ach_csv`/`wire_csv`/`stripe_connect_vendor`/`manual`), items (JSONB array of `{bill_id, amount}`), export_file_url, journal_entry_id, agent_drafted_by, approved_by_user_id, approved_at |

> Vendors and customers share the `clients` table with a `kind` discriminator (`customer`/`vendor`/`both`). Reduces duplication; allows a single client to be both (common for PS firms — your auditor may also be your client).

### 4.12 Counts
- **Total tables**: **37**
- vs. current erpcore PS (22 PS-specific + ~12 shared ≈ 34 touched):
  - **Dropped 8** over-normalised tables (tasks, task_assignments, billing_arrangements, rate_card_entries, billing_run_items, timesheets, timesheet_approval_steps, engagement_letters/deliverables)
  - **Added 12** net-new tables for AI/HITL/AP/tax/multi-currency: documents, extraction_results, agent_suggestions, hitl_tasks, chat_threads, chat_messages, agent_autonomy_settings, change_orders-redux, tax_rates, bills, bill_lines, bill_payments
  - **Folded** Stripe Connect state into `tenants` (no new table)

---

## 5. Backend Architecture

### 5.1 Layering (ported from erpcore)
```
Router (FastAPI)
  └─ Service (BaseService — tenant-scoped, soft delete helpers)
       ├─ Repository (Supabase client wrapper)
       ├─ DomainRules (pure validation — VR-01..)
       └─ Agent (PydanticAI) — invoked from service, never from router
JournalService is the only writer to journal_entries / journal_lines.
DB triggers auto-create journals for the standard 4 events (invoice sent, payment received, expense approved, expense billed).
```

### 5.2 New routers (v1)
`/api/v1/`
- `auth/*` — signup, login, password reset, invite team
- `tenants/*` — tenant CRUD, switch tenant
- `billing/*` — plans, subscribe, customer portal, current sub state
- `chat/threads` + `chat/threads/{id}/messages` — chat orchestration (SSE streaming)
- `documents/*` — upload, extract (re-run), get status, link to entity
- `inbox/tasks/*` — HITL queue (list, approve, reject, escalate, bulk-approve)
- `suggestions/*` — agent suggestions (list, accept, dismiss)
- `clients/*`, `engagements/*`, `projects/*`, `employees/*`, `rate_cards/*`
- `time_entries/*`, `expenses/*`
- `invoices/*` (with `POST {id}/send`, `POST {id}/payment-link`, `POST {id}/void`)
- `billing_runs/*` (propose, review, approve → materialise invoices)
- `payments/*`, `accounts/*`, `journals/*`, `reports/*`
- `webhooks/stripe`
- `settings/agent_autonomy`

### 5.3 Workers (ARQ)
- `extract_document_worker` — invoked on `documents` insert; runs OCR (if needed) + extraction agent
- `billing_run_worker` — scheduled monthly; produces billing run drafts
- `collections_worker` — daily; finds overdue invoices, drafts reminders
- `stripe_webhook_worker` — processes webhook events (paid, refunded, sub state change)
- `payment_link_worker` — creates Stripe Payment Links on invoice send
- `wip_snapshot_worker` — daily WIP snapshot for reporting

---

## 6. Agent Layer (PydanticAI + Pydantic Graph)

### 6.1 Orchestrator
**`copilot_agent`** — root chat agent (Pydantic Graph). On each user message:
1. **Router node** classifies intent (CRUD / Q&A / document-related / billing / collections / settings).
2. Dispatches to a **specialist agent** via a graph edge.
3. Specialist runs typed tools (each scoped to the tenant) and returns a structured response.
4. If the specialist's response includes a *mutation* (invoice draft, expense create, etc.):
   - If confidence ≥ autonomy threshold AND autonomy level ≥ L3 → execute, write `agent_suggestions` row with status `auto_applied`, post inline confirmation card.
   - Else → write `agent_suggestion` (status `pending`) + `hitl_task`, post inline review card with Approve/Edit/Reject.
5. Streams tokens to the chat UI; tool calls render as collapsible cards mid-stream.

### 6.2 Specialist agents

| Agent | Purpose | Default autonomy |
|---|---|---|
| `engagement_letter_agent` | Parse uploaded EL → draft engagement + billing_terms + rate_card hints | L2 (suggest) |
| `vendor_invoice_agent` | Parse uploaded vendor bill → AP entry + journal | L2 |
| `expense_extractor_agent` | Parse receipt → project_expense draft | L3 if confidence > 0.9 else L2 |
| `invoice_drafter_agent` | Build invoice from time + expenses + billing model | L2 |
| `billing_run_agent` | Monthly pre-bill: propose invoices for all active engagements | L1 (suggest only — humans approve the batch) |
| `project_health_agent` | Background; alerts on budget burn, scope risk, retainer balance | L2 (suggests alerts) |
| `collections_agent` | Drafts dunning emails for overdue invoices | L2 |
| `accounting_guardian` | Validates every journal before post — debits=credits, period not locked, account valid | **L3 always, cannot disable** |
| `reporting_agent` | Q&A over data (P&L by engagement, AR aging, utilization) | L3 (read-only) |
| `intelligence_agent` | Anomaly detection, suggestions on rates / under-billing / scope creep | L2 |
| `time_entry_agent` | Chat-driven time entry parsing ("I spent 3h on Acme yesterday on the discovery phase") | L3 if unambiguous else L2 |
| `revenue_recognition_agent` | (v1.1) ASC 606 — WIP, deferred revenue, recognition schedule | L1 → L2 over time |
| `bill_pay_agent` | Proposes payment batches: which approved bills to include, optimal payment date (discount capture / due date), source bank account | L2 (always — money out is sensitive) |

All agents:
- Use `deps_type=AgentDeps` (tenant-scoped DB client + user identity)
- Use Pydantic `BaseModel` typed outputs
- Mask PII before sending to LLM (`mask_pii()` ported from erpcore)
- Trace to Langfuse with prompt versioning + score capture
- Have a confidence score in their output (0..1) used by HITL gating

### 6.3 Tools (representative; not exhaustive)
- `query_clients`, `create_client`, `get_engagement`, `list_active_engagements`
- `parse_engagement_letter(document_id)`, `parse_receipt(document_id)`, `parse_vendor_invoice(document_id)`
- `propose_invoice(engagement_id, period_start, period_end)`, `send_invoice(invoice_id)`, `create_stripe_payment_link(invoice_id)`
- `log_time(employee_id, project_id, phase_id, date, hours, notes)`
- `find_overdue_invoices`, `draft_reminder(invoice_id, tone)`
- `propose_journal(...)`, `post_journal(journal_id)` (gated by accounting_guardian)
- `get_project_pnl(project_id)`, `get_utilization(employee_id, period)`

### 6.5 Autonomy auto-promotion (new in v2)

All agents start at **L2 (suggest)** when a tenant signs up. We learn each agent's track record and surface a promotion offer to the admin when justified — humans always opt in; promotion is never silent.

**Mechanism**: a `autonomy_promoter_worker` runs nightly per tenant. For each `(agent_name, action_type)` pair it computes from the last 30 days of `agent_suggestions`:
- `n` — total decided suggestions (must be ≥ 30)
- `approval_rate` = approved / decided (must be ≥ 0.95)
- `avg_confidence_of_approved` (must be ≥ 0.85)
- `edit_rate` = approved-with-edits / approved (must be ≤ 0.15)
- `time_to_decision_p50` (informational, surfaced to admin)

If thresholds hit, the worker inserts a `hitl_task` of kind `promote_autonomy`:
> *"Promote `expense_extractor.create_expense` from L2 to L3 (auto-apply on confidence > 0.9)? Last 30 days: 87 suggestions, 96% approved, 8% edited, avg confidence 0.91."*

Admin (only role `owner` / `admin`) can:
- **Approve** → `agent_autonomy_settings.level` updated to L3 with `confidence_threshold = 0.9`; takes effect immediately
- **Defer** → suggestion expires; re-evaluated in 7 days
- **Reject** → `agent_autonomy_settings.locked_at_l2 = true`; promoter won't ask again for this pair for 90 days

Demotion path: if approval rate drops below 0.85 over a rolling 14 days at L3, system auto-demotes back to L2 and notifies admin. No silent escalation, but emergency de-escalation is allowed.

Thresholds are tenant-configurable in Settings → Agent Autonomy. Defaults above are the safe shipping values.

### 6.4 HITL flow (concrete walkthrough)
1. User drops `engagement_letter_Acme.pdf` in chat.
2. Document row written → `extract_document_worker` picks it up.
3. `engagement_letter_agent` parses → emits `EngagementDraft` with confidence 0.78.
4. Agent autonomy for `engagement_letter_agent.create_engagement` = L2, threshold 0.9. Confidence is below threshold → `hitl_task` created with payload, assigned to the user, priority `med`.
5. Inline card in chat: *"I parsed Acme's engagement letter. Confidence 78%. Draft engagement: …  [Approve] [Edit] [Reject]"*.
6. User clicks Approve → API endpoint `POST /inbox/tasks/{id}/approve` → service materialises the engagement → returns success → chat shows confirmation card with link.
7. If user clicks Edit → opens an `engagement-edit` modal pre-filled; on save, the suggestion is marked `approved (with edits)` and the corrected version is stored as a training signal (later piped to fine-tune / few-shot pool).

---

## 7. Frontend Architecture

### 7.1 Stack
- Angular 19 standalone components, signals, control flow
- Tailwind v3 + Angular Material 19 (theme overridden to dark slate; not vanilla MDC)
- NgRx Signals for state stores
- HTTP via `HttpClient` with interceptors (auth, tenant, error)
- SSE for chat streaming (`EventSource`)
- Supabase JS client for: auth (PKCE), storage uploads (resumable), realtime channels (chat thread updates, inbox updates)

### 7.2 Top-level navigation (sidebar)
1. **Copilot** (home) — chat + dashboard hybrid
2. **Inbox** — HITL queue with filters (mine / all / overdue / by agent)
3. **Engagements**
4. **Projects**
5. **Clients**
6. **Invoices**
7. **Billing Runs**
8. **Expenses**
9. **Time** (light)
10. **Payments**
11. **Reports**
12. **People** (Employees + Rate Cards)
13. **Settings** (Subscription · Agent Autonomy · Branding · Stripe · Integrations · Team)

### 7.3 Copilot home (the showpiece)
Left column: collapsible thread list. Center: chat surface. Right column: contextual "what's hot" panel.

Chat surface specifics:
- Composer with: textarea, multi-file drop zone, slash menu (`/invoice`, `/engagement`, `/expense`, `/report`), voice (later).
- Streaming tokens with cursor; tool-calls render as **expanded cards** during execution (icon + tool name + spinner → result), collapse on completion.
- **Generative UI**: agent responses can include typed "card" payloads (`InvoiceDraftCard`, `EngagementDraftCard`, `ExpenseExtractedCard`, `ReportCard`, `HitlReviewCard`) that render as rich Angular components inline.
- Suggested-action chips at bottom ("Send to client", "Edit lines", "Schedule reminder").
- Right rail shows: today's HITL load, projects at risk, overdue invoices, retainers near floor.

Empty state on day 1 (no data): the copilot speaks first — *"Drop your most recent engagement letter or invoice and I'll set up your first client."*

### 7.4 Module-page conventions
Every CRUD module follows the same layout:
- Top: title, primary action button, AI suggestions bar (collapsible).
- Middle: filterable list with confidence-coloured badges where AI was involved.
- Right drawer: detail / edit; AI-suggested fields shown with a subtle wand icon and tooltip explaining the source.

### 7.5 HITL inbox UX
- Card-based queue, grouped by suggestion type.
- Each card: title, agent, confidence chip, summary diff (current vs. proposed), Approve / Approve & Edit / Reject / Escalate.
- Keyboard nav: `J/K` next/prev, `A` approve, `R` reject, `E` edit.
- Bulk-approve when filter narrows to a single type (e.g. all extracted receipts).

### 7.6 Design system
We extend erpcore's dark slate palette (slate-900/800/700) with:
- **Confidence chips**: red (<0.5), amber (0.5–0.8), emerald (>0.8)
- **Agent-touched indicator**: small sparkle (✦) badge
- **AI shimmer skeleton**: gradient-pulse for in-flight extractions
- **Generative card frame**: subtle gradient border that pulses while streaming

(Detailed spec → Chitra to own as design tickets in Week 1.)

---

## 8. Stripe Integration

### 8.1 SaaS subscriptions (signup → trial → paid)
- Reuse `services/payments/stripe_provider.py` + `services/billing/stripe_billing.py` — copy into aethos-ps, **new** test + live keys.
- Onboarding flow:
  1. Email + password (Supabase Auth)
  2. Tenant name + base currency
  3. Plan selection (Starter / Growth / Pro — defined as Stripe Products)
  4. Stripe Setup Intent — card capture; in `NODE_ENV=development` the form is prefilled with `4242 4242 4242 4242 / any future date / any CVC`
  5. Stripe Subscription created with `trial_period_days=14`
  6. Land in Copilot home; trial countdown visible top-right
- Customer portal: `stripe.billing_portal.Session.create` link in Settings.

### 8.2 Per-invoice Payment Links (the new piece)
- On `POST /invoices/{id}/send`:
  1. Create a Stripe `Product` + `Price` (one-off) reflecting the invoice total in the invoice currency.
  2. Create a `PaymentLink` with `metadata = {invoice_id, tenant_id}` and `after_completion = {type: "redirect", redirect: {url: "https://ps.aethos.app/p/{invoice.token}/thanks"}}`.
  3. Persist `stripe_payment_link_id` + `stripe_payment_link_url` on the invoice row.
  4. Email goes out with the payment link button + the PDF attachment.
- Webhook handler: on `checkout.session.completed` with matching metadata → create `payments` row → DB trigger fires `trg_payment_received` → DR Bank / CR AR.
- **Optional v1.1**: Stripe Connect Standard so payouts go directly to the firm's bank. v1 collects to Aethos account, manual payout to firm (or document Connect as opt-in).

### 8.3 Public invoice view
- Hosted page `/p/:token` (no auth) — branded invoice, line items, "Pay now" button → Payment Link.
- Token = signed UUID stored on invoice; rotated on void/resend.

### 8.4 Stripe Connect — firm payouts (new in v2)

Each tenant connects their own Stripe account (**Standard** accounts — the firm owns it, manages dashboard, handles their own KYC, owns their balance):
- Settings → "Connect Stripe" → redirect to Stripe Connect OAuth → success returns to `/settings/stripe/return` → store `stripe_connect_account_id`, `stripe_connect_status`.
- Listen to `account.updated` webhook to sync `charges_enabled` / `payouts_enabled`.
- All per-invoice `PaymentLink` calls include `on_behalf_of = <connect_account>` and `transfer_data = {destination: <connect_account>, amount: <total - application_fee>}`.
- `application_fee` = configurable; **default 0%** in v1 to remove an objection. (We can monetise via SaaS subscription only at first; introduce a 1-2% transaction fee later as a discount-vs-Stripe alternative or a free-plan revenue stream.)
- Tenants that haven't connected Stripe can still create invoices (PDF + email path), they just can't generate payment links — UI nudges to connect.

### 8.5 Multi-currency (5 launch currencies)

- `tenants.base_currency` set at signup. Picker defaults based on `tenants.country` (US→USD, UK→GBP, SG→SGD, IN→INR, AU→AUD); admin can override.
- **5 currencies preloaded** in `fx_rates`: USD, GBP, SGD, INR, AUD. Cross-rates derived from USD pivot.
- `engagements.currency` defaults to tenant base; user can override.
- `invoices.currency` inherits engagement; can override.
- `fx_rates` populated daily by `fx_refresh_worker` (source: `openexchangerates.org` free tier in v1; swap to paid when usage warrants).
- At invoice posting time: `journal_lines.base_amount = amount * fx_rate(currency → base, invoice_date)`. Both the foreign amount and base amount stored.
- Reports default to **base currency**; an invoice-currency toggle shows original.
- Payments arrive in invoice currency (Stripe handles conversion if needed). Reconciliation matches by `stripe_payment_intent_id`; FX diff (if any) booked to a `Realized FX Gain/Loss` account by the accounting_guardian.

### 8.6 Per-currency SaaS pricing (5 markets)

We create one Stripe Product per plan tier with **5 currency-specific Prices** each. Suggested launch numbers (round-numbered, PPP-adjusted):

| Plan | USD | GBP | SGD | INR | AUD |
|---|---|---|---|---|---|
| Starter | $29 | £25 | S$39 | ₹2,499 | A$45 |
| Growth | $79 | £69 | S$109 | ₹6,999 | A$119 |
| Pro | $199 | £179 | S$279 | ₹17,999 | A$299 |

Stripe Tax is enabled product-wide (`stripe_tax = true` on prices); buyer location determines GST/VAT and the invoice is grossed up automatically. Tenant sees the tax-inclusive total before card capture.

### 8.7 Stripe Connect — country coverage

Stripe Connect Standard is supported in all 5 launch markets. Onboarding redirects to Stripe with a `country` param matching `tenants.country`. Tenants in unsupported countries (out-of-scope in v1) see a "request access" form and can still use Aethos without Connect (manual mark-as-paid for AR).

---

## 9. Document Extraction Pipeline

```
Upload (multipart or chat drop)
  → Supabase Storage (private bucket per tenant)
  → INSERT documents (status=uploaded)
  → ARQ enqueues extract_document_worker
  → worker: if mime=pdf and >1pg, render pages to images; else use file directly
  → call Claude Sonnet 4.6 (vision multimodal, structured output)
  → typed agent (engagement_letter_agent / receipt / vendor_invoice / bank_statement)
  → INSERT extraction_results with confidence
  → IF auto-eligible (autonomy + confidence): materialise entity, INSERT agent_suggestion(status=auto_applied)
  → ELSE: INSERT agent_suggestion(status=pending) + hitl_task
  → realtime push to user's UI (Supabase realtime) → chat card or inbox toast
```

Notes:
- We **do not** call any non-Anthropic OCR for receipts/letters — Claude vision is good enough and avoids two-vendor surface.
- For very large PDFs (bank statements 20+ pages) we paginate and stitch.
- Failed extractions remain in `documents.status=failed` with the error in `extraction_results.error_msg`; the inbox shows a "manual entry needed" card.

---

## 10. Accounting Posture

- Pure double-entry, `NUMERIC(15,2)`, all writes through `JournalService` *or* the DB triggers.
- Trigger catalog (same as erpcore PS):
  - `trg_invoice_sent` → DR AR / CR Revenue (+ deferred-revenue split for retainers)
  - `trg_payment_received` → DR Bank / CR AR
  - `trg_expense_approved` → DR Expense / CR AP (vendor invoice) or DR Expense / CR Employee Reimbursable
  - `trg_expense_billed_to_client` → DR Reimbursable AR / CR Pass-through Revenue
- Period close per tenant; `period_locks` table; API layer rejects any write where `entry_date <= max(locked period)`.
- WIP measured as: `sum(time_entries.hours * bill_rate where status in (approved, submitted) and not yet billed)` per project. Surfaced as a *report*, not a posted journal, in v1.
- Rev-rec automation deferred to v1.1.

---

## 11. Timesheet Separation Strategy

Per your direction, the rich timesheet UI is **not** part of aethos-ps v1.

In aethos-ps v1 we have:
- `time_entries` table (required for billing)
- A simple list view + chat-driven entry ("/time 3h Acme discovery yesterday")
- A "My Time" page that's a flat table of the current week
- No approval chain UI; auto-approve unless flagged by `time_entry_agent`

In a separate future module (working title **aethos-time**) we will build:
- Calendar / week-view entry
- Multi-step approval chains
- Mobile entry
- Slack/Teams entry
- Forecasting / capacity planning

aethos-time will be a sibling app reading/writing `time_entries` via a public API exposed by aethos-ps. Decision deferred on whether aethos-time has its own DB or shares the PS one — likely shares, with a clear API boundary.

---

## 11.5 Bill Payments & AP (new in v2)

PS firms pay sub-contractors, software vendors, travel reimbursements, and project pass-throughs constantly. v1 of aethos-ps ships an **agent-driven AP loop** end-to-end, but the actual money movement in v1 is via **bank file export** (NACHA / CSV) — not a direct rail integration. v1.1 adds Stripe-Connect-vendor and Plaid+Dwolla rails.

### 11.5.1 Flow

```
Vendor invoice received (email forward, drag-drop, chat upload)
  → documents row
  → vendor_invoice_agent extracts
  → bills + bill_lines (draft, gl-coded by agent, project linked if billable)
  → hitl_task: "Review bill from <vendor> for <amount>"
  → admin approves → bill status=approved → DB trigger: DR <Expense GL> / CR <AP>
  → bill enters "Bills to Pay" list
  
Periodic (manual or daily-suggest):
  → bill_pay_agent proposes a batch (which bills, payment date, source bank account, discount-capture logic)
  → batch in draft state, admin reviews in Inbox
  → admin approves
  → system generates NACHA file (or CSV per bank template) and presents download
  → admin uploads to bank portal (out-of-band)
  → admin clicks "Mark as settled" with confirmation #
  → batch status=settled → DB trigger: DR <AP> / CR <Bank> (per bill)
  → bill.amount_paid updated, status=paid if fully paid
```

### 11.5.2 Why bank-file export over rail integration in v1
- Most small PS firms already have their bank's bill-pay flow; we're not displacing the rail, we're orchestrating the *decision*.
- Avoids us becoming a money-transmitter (the bank file = customer's bank moves the money on customer's behalf with their own ACH/BACS/etc. origination agreement).
- 1-2 day dev cost per format vs. 2-3 weeks for proper rail integration.
- v1.1 adds: (a) native **BACS** (UK), **ABA** (AU), **GIRO** (SG), **NEFT/RTGS CSV** (IN); (b) Stripe Connect to vendors with Stripe accounts → direct transfer; (c) Plaid + Dwolla for ACH; (d) Modern Treasury for higher-volume tenants.

### 11.5.2b File formats at launch (v1)

| Format | Markets | Notes |
|---|---|---|
| **NACHA** | US | Standard ACH origination file; firms upload to their bank's portal |
| **Universal CSV** | US · UK · SG · IN · AU | Generic columns: `date, beneficiary_name, account_no, bank_code (routing/sort/IFSC/BSB), amount, currency, reference`. Most banks accept a custom CSV in their bulk-payment portal. We document the column map per bank in our help center. |
| **Mark-as-paid manual** | All markets | For one-off wires, cheques, or already-paid items |

Tenants outside the US who haven't gotten native-format support yet can use Universal CSV — verified working with HSBC UK, DBS SG, ANZ AU, ICICI IN, HDFC IN as of v1.

### 11.5.3 Required tables (already in §4.11)
- `bills`, `bill_lines`, `bill_payments` — defined.

### 11.5.4 Required agents
- `vendor_invoice_agent` — already in catalog (§6.2)
- `bill_pay_agent` — new in v2, listed in §6.2; proposes batches, never executes settlement (humans approve every batch)

### 11.5.5 UI
- **Bills** page: list with status, vendor, due-in, amount, GL code; filter "to pay"; AI Suggestions bar on top ("3 bills due in 7 days totalling $12,400 — propose batch?")
- **Pay Bills** wizard: select bills → choose source bank account → choose method (NACHA / CSV / mark-as-paid manual) → review → approve → download file → confirm sent
- **Bill detail**: full extraction with confidence chips per field; "Re-extract" option; raw document viewer side-by-side

---

## 12. Deployment & Infrastructure

| Component | Where | Notes |
|---|---|---|
| Frontend | Vercel (new project `aethos-ps-web`) | `aethos-ps.com` (or chosen domain). Preview deploys on PR. Static landing at `/`, app at `/app`. |
| Backend | Cloud Run (new service `aethos-ps-api`) | `api.aethos-ps.com`. Min 1 instance to keep chat warm. |
| DB / Auth / Storage / Realtime | **New Supabase project** `aethos-ps-prod` (+ `-staging`) | Fresh `auth.users`, fresh storage buckets per tenant. |
| ARQ workers | Cloud Run worker service | Redis (Upstash) for queue. Workers: `extract_document`, `billing_run`, `collections`, `stripe_webhook`, `payment_link`, `fx_refresh`, `wip_snapshot`, `autonomy_promoter`. |
| Cache | Upstash Redis | |
| LLM | Anthropic (Claude Sonnet 4.6) + Langfuse for traces | New Anthropic key for clean per-product billing visibility. |
| Email | **Resend** | Branded transactional + invoice emails. Per-tenant DKIM/SPF in v1.1. |
| Payments | Stripe — **separate Stripe account** + **Stripe Connect (Standard)** enabled | Aethos collects SaaS subs; tenants connect their own Stripe to receive customer payments. |
| FX | openexchangerates.org (free tier in v1) | Daily refresh; swap to a paid provider when usage warrants. |
| Observability | Sentry (new project) + Langfuse | |
| CI/CD | GitHub Actions — new workflows `aethos-ps-api.yml`, `aethos-ps-web.yml` | Reuse erpcore's CI templates. |

---

## 13. Phasing — 6 Weeks to Public Beta

### Week 1 — Repo bootstrap + Foundations + Brand lockup
- ✅ **Repo `aethos-ps` initialized** at `~/dev/aethos-ps` with skeleton scaffold, README, CLAUDE.md, .gitignore, plan moved in. *(Done as a pre-execution setup.)*
- Push to GitHub (`venkateshbr/aethos-ps` — name to confirm with Founder); create GH Project board mirroring aethos lifecycle + labels; configure role-guard workflow.
- Copy + adapt agent definitions from aethos `.claude/agents/` → `aethos-ps/.claude/agents/`.
- **Founder assigns domain** from existing Aethos pool → Sthira configures Vercel project, Supabase project, Stripe account (Connect + Tax enabled), Sentry, Anthropic key, Resend, Upstash Redis.
- **Chitra** delivers 2-3 services-lockup directions (logo + accent color + sample applications); Founder picks Friday.
- New Supabase project, baseline schema (tenants with country field, tenant_users, employees, clients, accounts, journal_entries, journal_lines, documents, **tax_rates with 5-market seed**, **fx_rates with 5 currencies**)
- FastAPI scaffold + auth + tenant middleware (with `tenants.country`, `tenants.timezone`, `tenants.locale`); ports 8011 dev
- Stripe subscription signup (port erpcore billing) + sandbox card prefill + 3 Products × **5 currency Prices each** + **Stripe Tax enabled**
- Angular shell (ng new) on port 4201 with dark theme, sidebar, Copilot empty state, Angular i18n primitives, currency / date locale pipes
- Static landing page (single Angular route at `/`) — copy targets all 5 markets
- CI/CD pipelines (preview deploys working)
- **Netra**: kick off design-partner outreach pipeline (§18); founder-personal voice, English markets first

### Week 2 — Core PS data + Chat MVP + Multi-currency
- Engagements (with multi-currency support), projects (no phases yet), rate_cards, rate_card_client_overrides, project_assignments
- Multi-currency plumbing: `tenants.base_currency`, FX worker + table, base_amount on journal_lines
- CRUD APIs + Angular pages (list + detail) with currency-aware money pipe
- Copilot chat MVP: thread/messages, SSE streaming, single tool (`query_engagements`)
- `chat_orchestrator` (Pydantic Graph router) with 2 specialist agents stubbed
- File upload + `documents` table + Supabase Storage policies
- **Netra**: 30 outreach DMs sent, 5 calls booked

### Week 3 — AI doc extraction + HITL inbox + AP foundations
- `engagement_letter_agent`, `expense_extractor_agent`, `vendor_invoice_agent`
- `agent_suggestions` + `hitl_tasks` tables + APIs
- Inbox UI with cards, keyboard nav, bulk approve
- Generative card components in chat (`EngagementDraftCard`, `ExpenseExtractedCard`, `BillExtractedCard`)
- Agent autonomy settings page (defaults all L2)
- Project phases + project assignments
- **AP foundations**: `bills`, `bill_lines` tables + bill review UI; vendors as `clients.kind='vendor'`
- **Netra**: 3 design partner LOIs in hand (or rolling)

### Week 4 — Billing engine + Stripe (Payment Links + Connect) + Tax
- `time_entries` + `time_entry_agent` (chat entry) + simple list page
- `project_expenses` (UI + chat-driven)
- `invoice_drafter_agent` with all 5 invoice models (TM, fixed, milestone, retainer, retainer-draw)
- Billing runs: propose → review → approve → materialise
- **Per-line tax** on invoices and bills (using `tax_rates`)
- Stripe Payment Link creation on invoice send
- **Stripe Connect Standard** onboarding flow (Settings → Connect)
- Public invoice view (`/<token>`) — branded with tenant logo
- Stripe webhook → payment → DB trigger → journal (multi-currency aware)
- Accounting guardian + period locks

### Week 5 — Bill payments + Reports + Collections + Autonomy promoter
- `bill_payments` + `bill_pay_agent` + Pay Bills wizard (**NACHA** for US + **Universal CSV** for all 5 markets)
- Reports: project P&L, engagement summary, AR aging, **AP aging**, utilization, WIP, **multi-currency toggle**
- `reporting_agent` for natural-language Q&A
- `collections_agent` (daily) + email reminders via Resend
- `project_health_agent` (background; surfaces to Inbox)
- **`autonomy_promoter_worker`** + Inbox promotion cards (§6.5)
- Design partners onboarded to staging with sample data
- First demo to 3 design partners; rapid feedback cycle

### Week 6 — Polish, hardening, launch
- Prahari security review (auth, Stripe webhooks, Connect onboarding, tenant isolation, RLS)
- Aksha eval suite for all 13 agents (target: extraction agents > 0.85 F1 on synthetic test set)
- Sthira: load test (100 concurrent chats, 1000 doc extractions/hour)
- Performance pass on chat streaming, doc upload, list pages
- Polish: empty states, error states, loading skeletons, onboarding tour
- Marketing landing copy finalized; press kit; ProductHunt scheduled
- 3 design-partner tenants in production with real data
- **Public beta launch** (Friday of Week 6)

Each week ends with a Friday cut + demo to design partners; their feedback feeds next week's scope.

---

## 14. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | 5-week timeline is tight for "comprehensive" | Strict scope discipline; defer rev-rec, mobile, multi-currency consolidation, rich timesheet — these are explicitly out-of-scope. |
| R2 | Two frontends (Angular erpcore + Angular ps) → divergence | Extract shared design tokens + 3-4 base components into a private npm package `@aethos/ui` in Week 2. |
| R3 | Stripe Connect needed for firms to receive payouts | Document as v1.1; v1 Aethos collects and manually settles (acceptable for design-partner tenants). |
| R4 | LLM cost unpredictability at scale | Per-tenant token budget + Langfuse alerting; default Claude Sonnet (not Opus) for extraction; cache extraction by document sha256. |
| R5 | Document extraction misclassification | Always show confidence; HITL by default; corrections logged; weekly Dhruva review. |
| R6 | Period lock + agent posting collisions | Accounting guardian validates lock at draft time AND post time; rejects late-posting. |
| R7 | Webhook misses (Stripe) → invoice not marked paid | Reconciliation worker nightly: list yesterday's Stripe payments, match by metadata. |
| R8 | Customer data import from existing systems (Xero, FreshBooks) | Not in v1. Documented manual onboarding path; v1.1 adds CSV import + a connector for the top-1 system per design partner. |
| R9 | Stripe Connect onboarding friction blocks signup | Make Connect *optional* at signup — tenants can use the app without it; UI nudges to connect when they try to send their first invoice. |
| R10 | NACHA file format errors → bank rejects bill payment file | Validate file against spec before download; document per-bank format; test with 3 design partners on real banks before GA. |
| R11 | Autonomy promoter promotes too aggressively, money mistakes happen | Owner-only approval; demote on first failure; specific carve-out: agents that touch money (invoice, journal, bill_pay) require **double** the sample size (60) and **higher** thresholds (approval ≥ 0.98) before promotion eligibility. |
| R12 | Multi-currency FX rate stale or wrong on weekends | Fall back to last known rate; warn user when invoice issued on stale rate (> 3 days old); always store snapshot, never recompute. |
| R13 | Brand name conflict / trademark issue post-launch | Cheap trademark search (USPTO TESS) before domain purchase; backup names from §17; v1 includes a brand-rename guard (brand_name/brand_logo_url stored on tenants → swap is config not code). |

---

## 15. Open Questions — Status

**All 12 Round-2 and all 8 Round-3 questions resolved.** See §0.1 changelog and §1 decisions D5–D22.

### Round 4 — small items, non-blocking (I'll proceed with my defaults unless you redirect)

1. **Domain assignment**: Founder picks from existing Aethos domain pool — `services.aethos.app` / `ps.aethos.app` / `aethos.app/services` / other. Sthira configures Vercel + Resend + Stripe + Supabase to the chosen domain in Week 1 once told.
2. **Stripe Tax registration thresholds**: SG/AU/IN require business registration with local tax authorities once revenue crosses a threshold. v1 we let Stripe Tax compute liability but **register only in US (default), UK (£90k threshold), and Australia (A$75k threshold)** at launch. Singapore (S$1M) and India (₹20L for digital services) we defer registration until we approach. Acceptable?
3. **Universal CSV column map**: do you want me to expose this as a tenant-editable template (in case their bank requires a different order/header) or ship it fixed? Default: fixed columns in v1, configurable in v1.1 if a tenant requests it.
4. **Trial card capture for India**: RBI rules sometimes require additional auth on the first charge; Stripe handles this. We'll show a one-time post-trial 3DS step. Just flagging — no action needed from you.
5. **Default tenant timezone & locale**: derive from browser `Intl.DateTimeFormat().resolvedOptions()` at signup, store on tenant, allow override in settings. OK?

If you don't push back on any of these, I'll lock them as v3 defaults and proceed.

---

## 16. After Approval — Execution Plan

Once you approve this plan (with or without round-3 edits):
1. I (Vishwa) create a parent GitHub Issue `[Epic] aethos-ps v1` and decompose into ~30 sub-issues, one per slice in Section 13.
2. Sub-issues are labelled by week and assigned to **Karya** (backend), **Rupa** (frontend), **Chitra** (design specs + brand identity), **Aksha** (eval/test plans), **Sthira** (infra), **Dhruva** (agent observability + autonomy-promoter tuning), **Prahari** (security review on auth + Stripe + Connect + webhooks + bill-pay file integrity), **Netra** (design-partner outreach + onboarding).
3. Per your instruction, execution agents run on a lower-cost model (Sonnet) and I (Opus) only step in for review checkpoints at end of each week's cut.
4. Status visible on the Aethos Roadmap board, filter `epic:aethos-ps-v1`.

---

## 17. Brand — "Aethos" (parent brand carried through)

### 17.1 Positioning

The product is **Aethos**. Marketing positions it as *"Aethos, for professional services"* — Linear-style minimalism where the brand stays singular and the audience is named in the tagline. Internal abbreviation: `aethos-ps`. Repo name: `aethos-ps`. The marketing surface and app shell display only **"Aethos"** with a small **`for services`** lockup (or a sub-mark) — never "Aethos PS" or "Aethos Services" as a forced bolt-on.

### 17.2 Why keep the parent brand
- **Zero TM/domain risk** — Aethos brand and any subdomain (e.g. `services.aethos.app`, `ps.aethos.app`, `aethos.app/services`) are already in the founder's pool.
- **Trust transfer** — if any erpcore design partner sees Aethos in PS too, brand consistency reinforces "this team makes the ERP".
- **No re-brand if we ever merge products** — the two are different repos and DBs, but the brand never had to fracture.
- **Smaller week-1 scope for Chitra** — lockup + sub-mark instead of full identity. ~2 days instead of ~1 week.

### 17.3 Visual identity (Chitra, Week 1)

**Scope reduced from full identity → services lockup.** Chitra delivers **2-3 directions** for selection by mid-Week-1:
- **Logo lockup**: Aethos wordmark (existing) + services lockup. Options include a small `for services` subtitle, a distinct sub-mark, a chip/badge, or a divider treatment.
- **Palette**: inherit existing Aethos dark slate; *propose* a single services accent color (e.g. teal / warm-amber / electric-blue) that the chat surface and HITL cards can lean into.
- **Type**: inherit existing Aethos type pairing.
- **Sample applications**: app sidebar, landing section, invoice header, social card, favicon.
- **Tone-of-voice one-pager**: warm, concise, confident — *"AI does the data entry. You approve."*

### 17.4 Brand kit storage
`frontend/src/assets/brand/` — logo lockup SVGs (light/dark/mono), palette JSON, social card template, email header template. `tenants.brand_logo_url` allows per-tenant white-label in v1.1 (firms can override with their own logo on invoices/portal).

### 17.5 Domain
**Founder assigns** from existing Aethos domain pool. Sthira waits for the call before configuring Vercel / Resend / Stripe / Supabase domains. Likely candidates: `services.aethos.app`, `ps.aethos.app`, `aethos.app/services`.

---

## 18. Design Partner Outreach Plan (Netra-owned)

**Goal**: 3 paying design-partner firms in production by end of Week 6, each a 5–30-person PS firm using QBO/Xero + spreadsheets or actively churning from a legacy PSA (Harvest, BQE Core, Mavenlink, Replicon).

### 18.1 Target ICP
- **Size**: 5-30 people
- **Verticals (in priority order)**: (1) management consulting boutiques, (2) IT consulting / dev shops / fractional CTO firms, (3) corporate finance / M&A advisory, (4) marketing / brand agencies, (5) accounting / bookkeeping firms (rich self-referential angle — they'd appreciate the AI), (6) law firms (regulated, harder; lower priority)
- **Geography for first 3 design partners**: US-heavy (most active SaaS-buying PS firms on LinkedIn / Twitter), 1 may come from UK/SG/AU for early multi-market signal. India market we tap warm intros only in first 6 weeks.
- **Current stack signal**: QBO/Xero + Toggl/Harvest, or any complaint thread about BQE/Mavenlink/Replicon
- **Decision-maker**: founder, COO, or finance lead (not bookkeeper)

### 18.2 Channels & cadence (over 4 weeks)
| Week | Channel | Volume | Owner |
|---|---|---|---|
| 1 | LinkedIn — founder personal post + 30 targeted DMs | 30 DMs | Founder + Netra drafts copy |
| 1 | Twitter/X — thread: "Building AI-native PSA, 3 design-partner slots, $0 for 6 months" | 1 thread + 10 DMs to PS-tweet-influencers | Founder |
| 2 | Indie Hackers + r/consulting + r/agency posts | 3 posts | Netra |
| 2 | Apollo/Clay list: 200 firms → 100 cold emails | 100 emails | Netra (3 follow-ups each over 10 days) |
| 2 | Slack communities: Demand Curve, Trends, On Deck, RevGenius, Pavilion, Indie Hackers | 6 posts | Netra |
| 3 | Warm intros from existing network — ask 10 advisors for 1 PS-firm intro each | 10 asks | Founder |
| 3 | Show-HN / ProductHunt "Coming soon" page | 2 posts | Netra |
| 4 | Refine on what's converting; double down | varies | Netra |

Target funnel: **200 outbound → 30 replies → 10 demo calls → 3 LOIs**. If we're below 10 demo calls by end of Week 3, escalate (paid sponsorship in a PS-firm newsletter; refer-a-firm bounty; consider a niche pivot to one vertical).

### 18.3 Offer to design partners
- **6 months free** (no trial-card needed for partners; we manually flip them to a comp'd plan)
- **White-glove migration**: we copy their last 12 months of clients / engagements / invoices / time entries into aethos-ps for them
- **Weekly 30-min feedback call** with founder + Vishwa for 6 weeks
- **Their feedback materially shapes v1.x roadmap** — they see the doc, they get veto on direction-of-travel
- **Logo on landing page** (opt-in)
- **Lifetime 50% off** the equivalent plan after their 6 months (locks in goodwill + word-of-mouth)

### 18.4 Outreach copy templates

**LinkedIn DM (founder voice):**
> Hey [Name] — I'm building **Aethos**, an AI-native ERP specifically for professional services firms. Drop your engagement letter, vendor invoice, or receipt into a chat and the AI does the data entry — invoices, expenses, bill-pay, GL postings. You approve.
>
> Stripe payouts, multi-currency (we launch in US/UK/SG/IN/AU), full double-entry under the hood.
>
> Looking for 3 design-partner firms — 6 months free, white-glove migration, weekly call with me. Your feedback shapes the product.
>
> [Firm] looks like exactly the kind of practice we're building for. Open to a 20-min call this week?

**Cold email (subject: "Aethos — AI PSA for [Firm] — 6 months free for feedback"):**
> [Name] — I noticed [specific signal — recent hire, recent post about ops, etc.]. I'm building **Aethos**, an ERP for PS firms where you drop documents into a chat and AI handles the data entry — invoices, expenses, bill pay, GL postings. Engagement letter to paid invoice without a single form.
>
> 3 design-partner slots. 6 months free + we migrate your data + I personally support you for 6 weeks. You give us blunt feedback.
>
> 15-min call to show you what we have?
>
> [Demo link / Calendly]

**Twitter thread (founder voice, 6 tweets):**
> 1/ I'm building **Aethos** — an AI-native ERP for professional services firms. Most PSA tools (Harvest, BQE, Mavenlink) feel like 2014 SaaS — forms, forms, forms.
>
> 2/ The pitch: drop your engagement letter in chat. AI extracts terms, drafts the engagement, sets up billing. You approve. Done.
>
> 3/ Drop a vendor receipt. AI extracts, codes it to the right GL account, links to the right project, posts the journal. You approve. Done.
>
> 4/ Multi-currency (USD/GBP/SGD/INR/AUD), Stripe Connect payouts, Stripe Payment Links on every invoice, full double-entry GL under the hood. We keep your books, not just track work.
>
> 5/ Looking for 3 design-partner firms (5-30 ppl, services). 6 months free, weekly call with me, your feedback shapes v1.
>
> 6/ DMs open. Reply or DM if you'd like 15 min to see it.

### 18.5 Tracking
- Pipeline tracked in Notion (or a simple sheet) by Netra — name, source, stage (cold/replied/demo-booked/demo-done/LOI/signed), notes, next step, owner
- Weekly review with Founder + Vishwa every Monday for the 6 weeks
- Conversion data feeds back into outreach copy refinement

---

*End of v4.*
