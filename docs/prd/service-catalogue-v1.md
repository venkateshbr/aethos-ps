# PRD: Products & Services Catalogue — v1

> **Owner**: Netra (Product Manager)
> **Status**: Decision-ready — immediate implementation
> **Date**: 2026-06-21
> **Priority**: Must-have (foundational)
> **Implements**: PLAN §4.x (data model extension), extends migration set 0031 (service_line on engagements)
> **Handoffs**: Karya (migration + API + seed), Rupa (Settings UI + engagement picker), Aksha (scenarios + tests), Vastu (pre-implementation review)

---

## 1. Problem Statement

Aethos PS has no concept of what the firm actually sells. An engagement knows it has a billing arrangement and a client, but not which service it delivers. This gap creates four cascading failures:

**Reporting failure.** Revenue is a single line. There is no breakdown by service line (Accounting / Tax / COSEC / Payroll), no cost-by-service attribution, no gross margin by practice area. The managing partner cannot see which service lines make money.

**Pricing inconsistency.** Every engagement starts from a blank rate. There are no defaults for what "Corporation Tax Return" typically costs at this firm. Rates drift person-to-person and engagement-to-engagement.

**AI blindness.** When a partner drops an engagement letter in Copilot, the extraction agent sees text like "corporation tax return" but has no catalogue to match it against. It cannot suggest "this looks like TAX-001 — Corporation Tax Return at £18,500 fixed fee." The AI must make a cold guess every time.

**GL fragmentation.** Revenue from all services posts to account 4000 (Revenue). There is no sub-ledger by service line to support the trial balance the demo guide shows (4000 Advisory, 4001 Tax, 4002 COSEC, 4003 Payroll). The standard COA seeded at tenant creation already has these revenue accounts; nothing links engagements to them.

### The gap in the Meridian Advisory context

In the demo, Marcus Chen reviews a trial balance showing £124,800 credited to "Revenue — Advisory", £38,200 to "Revenue — Tax", £18,400 to "Revenue — COSEC", and £8,640 to "Revenue — Payroll". Without a service catalogue, those four buckets do not exist — everything posts to 4000 and the balance sheet is useless for practice management.

---

## 2. Solution Overview

A `service_catalogue` table that each tenant configures once. It becomes the single source of truth for:

1. What services the firm offers, grouped by service line
2. Default billing unit and rate per service
3. Which GL revenue account to credit when invoiced
4. Which GL cost account to debit for time and expenses billed to that service

Pre-populated at tenant creation with ~14 standard PS services across 4 service lines. Firm admins can add custom services, deactivate ones they do not offer, and override defaults. The catalogue links outward to engagements, invoice lines, and rate cards.

### What this is not

This is not a product inventory system. There are no stock levels, no purchase orders, no warehousing. It is a menu of professional services with accounting defaults — a lightweight reference table, not a catalogue management system.

---

## 3. Data Model

### 3.1 New table: `service_catalogue`

```sql
CREATE TABLE service_catalogue (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Identity
    code                TEXT NOT NULL,           -- e.g. TAX-001, ACC-001
    name                TEXT NOT NULL,           -- e.g. "Corporation Tax Return"
    description         TEXT,                    -- optional detail shown in UI

    -- Classification
    service_line        TEXT NOT NULL
        CONSTRAINT ck_service_catalogue_service_line CHECK (
            service_line IN ('accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other')
        ),

    -- Billing defaults (auto-fill on engagement create)
    billing_unit        TEXT NOT NULL
        CONSTRAINT ck_service_catalogue_billing_unit CHECK (
            billing_unit IN ('hour', 'fixed', 'retainer', 'per_employee', 'per_entity', 'per_event')
        ),
    default_rate        NUMERIC(15,2),           -- NULL = no default (T&M with negotiated rate)
    default_currency    CHAR(3) NOT NULL DEFAULT 'GBP',

    -- GL mapping
    revenue_account_id  UUID REFERENCES accounts(id) ON DELETE SET NULL,
    cost_account_id     UUID REFERENCES accounts(id) ON DELETE SET NULL,

    -- Lifecycle
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_system           BOOLEAN NOT NULL DEFAULT FALSE,  -- seeded items; cannot be deleted

    -- Standard audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,

    UNIQUE (tenant_id, code)
);
```

**Index strategy:**
- `(tenant_id) WHERE deleted_at IS NULL` — list query
- `(tenant_id, service_line) WHERE is_active = TRUE AND deleted_at IS NULL` — service line filter
- `(tenant_id, code) WHERE deleted_at IS NULL` — code lookup (also covered by UNIQUE)

**RLS:** Standard tenant isolation policy `tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID`.

**Soft delete:** `deleted_at` follows the existing pattern. System items (`is_system = TRUE`) are excluded from delete operations at the service layer; only `is_active` can be toggled.

### 3.2 Foreign key additions to existing tables

Three existing tables gain a nullable FK to `service_catalogue`. Nullable preserves backward compatibility: existing rows have no catalogue reference and continue to work.

```sql
-- engagements: which service does this engagement deliver?
ALTER TABLE engagements
    ADD COLUMN service_catalogue_id UUID REFERENCES service_catalogue(id) ON DELETE SET NULL;

-- invoice_lines: which service does this line item represent?
ALTER TABLE invoice_lines
    ADD COLUMN service_catalogue_id UUID REFERENCES service_catalogue(id) ON DELETE SET NULL;

-- rate_card_lines: service-specific rate within a rate card
ALTER TABLE rate_card_lines
    ADD COLUMN service_catalogue_id UUID REFERENCES service_catalogue(id) ON DELETE SET NULL;
```

Note: `engagements.service_line` (added in migration 0031) continues to exist as a free-text enum for quick classification. `service_catalogue_id` adds the structured reference. When set, the UI derives `service_line` from the catalogue item rather than asking the user separately.

### 3.3 Revenue account seeding expansion

The current `seed_standard_coa` function seeds a single `4000 Revenue` account. This migration extends it to seed the four service-line sub-accounts. The system needs to seed these accounts first so the service catalogue seed function can reference their IDs.

```sql
-- Additional revenue accounts to add to seed_standard_coa
(p_tenant_id, '4000', 'Revenue — Accounting',  'revenue', TRUE),
(p_tenant_id, '4001', 'Revenue — Tax',         'revenue', TRUE),
(p_tenant_id, '4002', 'Revenue — COSEC',       'revenue', TRUE),
(p_tenant_id, '4003', 'Revenue — Payroll',     'revenue', TRUE),
(p_tenant_id, '4004', 'Revenue — Advisory',    'revenue', TRUE),
(p_tenant_id, '4005', 'Revenue — Other',       'revenue', TRUE),
-- Cost accounts
(p_tenant_id, '5010', 'Direct Costs — Accounting', 'expense', TRUE),
(p_tenant_id, '5011', 'Direct Costs — Tax',         'expense', TRUE),
(p_tenant_id, '5012', 'Direct Costs — COSEC',       'expense', TRUE),
(p_tenant_id, '5013', 'Direct Costs — Payroll',     'expense', TRUE),
(p_tenant_id, '5014', 'Direct Costs — Advisory',    'expense', TRUE),
```

The existing `4000 Revenue` and `5000 Expenses` accounts remain for backward compatibility. Service-line-specific accounts are additive.

> **Note for Karya**: The migration must add the new accounts to the `seed_standard_coa` function AND back-fill them for existing tenants via a one-time DML block in the same migration. Do not drop the generic `4000` / `5000` accounts — they are referenced by existing journal entries.

---

## 4. Seed Data

Pre-populated on tenant creation via `seed_service_catalogue(p_tenant_id UUID)` function, called from the `seed_coa_after_tenant_insert` trigger (or a dedicated trigger on the same event).

The seed assigns `revenue_account_id` and `cost_account_id` by looking up the newly seeded COA accounts by code within the same tenant.

### 4.1 Accounting Service Line (code prefix: ACC)

| Code    | Name                              | Billing Unit | Default Rate | Notes |
|---------|-----------------------------------|--------------|--------------|-------|
| ACC-001 | Monthly Management Accounts       | retainer     | (negotiated) | Most common retainer; no default rate |
| ACC-002 | Annual Statutory Accounts         | fixed        | (negotiated) | Fixed fee; rate agreed per engagement |
| ACC-003 | Group Consolidation               | fixed        | (negotiated) | Multi-entity work; bespoke pricing |
| ACC-004 | CFO Advisory                      | hour         | (negotiated) | T&M; rate set on rate card |

Revenue account: `4000 Revenue — Accounting`. Cost account: `5010 Direct Costs — Accounting`.

### 4.2 Tax Service Line (code prefix: TAX)

| Code    | Name                              | Billing Unit | Default Rate | Notes |
|---------|-----------------------------------|--------------|--------------|-------|
| TAX-001 | Corporation Tax Return (CT600)    | fixed        | (negotiated) | Annual statutory work |
| TAX-002 | Personal Tax Return (SA100)       | fixed        | (negotiated) | Self-assessment |
| TAX-003 | Trust Accounts & Tax              | fixed        | (negotiated) | Trust-specific work |
| TAX-004 | Tax Advisory (T&M)                | hour         | (negotiated) | Structuring, planning |
| TAX-005 | VAT Return Filing                 | retainer     | (negotiated) | Quarterly cycle |

Revenue account: `4001 Revenue — Tax`. Cost account: `5011 Direct Costs — Tax`.

### 4.3 Company Secretarial Service Line (code prefix: CSC)

| Code    | Name                                      | Billing Unit | Default Rate | Notes |
|---------|-------------------------------------------|--------------|--------------|-------|
| CSC-001 | COSEC Retainer                            | retainer     | (negotiated) | Monthly statutory maintenance |
| CSC-002 | Director Appointment / Resignation (AP01) | per_event    | (negotiated) | Per Companies House filing |
| CSC-003 | Share Allotment (SH01)                    | per_event    | (negotiated) | Per allotment event |
| CSC-004 | Registered Office / Other Filings         | per_event    | (negotiated) | Catch-all event billing |

Revenue account: `4002 Revenue — COSEC`. Cost account: `5012 Direct Costs — COSEC`.

### 4.4 Payroll Service Line (code prefix: PAY)

| Code    | Name                              | Billing Unit  | Default Rate | Notes |
|---------|-----------------------------------|---------------|--------------|-------|
| PAY-001 | Payroll Bureau — Monthly          | per_employee  | (negotiated) | Per employee per month |

Revenue account: `4003 Revenue — Payroll`. Cost account: `5013 Direct Costs — Payroll`.

**Total seeded items: 14 services across 4 service lines.**

Default rates are intentionally left as `NULL` in the seed. Professional services rates are negotiated per client and vary significantly by firm size and market. Leaving them null forces an explicit rate decision when creating an engagement — better UX than silently using a stale default. Firms that want a default rate can set it in Settings after seeding.

---

## 5. User Stories

### US-01: Firm admin configures the service catalogue

> As a firm owner or admin, I want to see my firm's standard services pre-seeded on signup, so that I can immediately start creating engagements without configuring the catalogue from scratch.

**Acceptance criteria:**

- AC-01-1: On first login after tenant creation, navigating to Settings > Services & Products shows 14 pre-seeded services grouped by service line (Accounting 4, Tax 5, COSEC 4, Payroll 1).
- AC-01-2: Each seeded item shows: code, name, service line, billing unit, default rate (blank if unset), revenue GL account, cost GL account, active toggle.
- AC-01-3: System items (`is_system = TRUE`) display a lock icon. Delete is disabled for system items; only the active toggle and default rate/description are editable.
- AC-01-4: Firm owner can add a custom service by clicking "Add Service". Required fields: name, service line, billing unit. Optional: code (auto-generated if blank as `SVC-NNN`), description, default rate, GL accounts.
- AC-01-5: Custom services can be edited and soft-deleted. Deleting a service that is referenced by one or more engagements shows a warning: "N engagements use this service. The service will be deactivated, not deleted." Deactivation prevents selection on new engagements but preserves historical references.
- AC-01-6: Inactive services (is_active = FALSE) are hidden from engagement and invoice line pickers but visible in Settings with a visual indicator.
- AC-01-7: GL account fields in the form show a dropdown of the tenant's revenue accounts (filtered to `account_type = revenue`) and cost accounts (filtered to `account_type = expense`). Both fields are optional — services without GL mapping use the default `4000 Revenue` / `5000 Expenses` accounts for journal posting.
- AC-01-8: Only users with role `owner` or `admin` can create, edit, or deactivate services. Manager and below see the catalogue as read-only.

---

### US-02: Partner creates an engagement with service selection

> As a partner, when I create an engagement I want to select the service from our catalogue so that the billing arrangement and suggested rate auto-fill, saving me time and ensuring consistency.

**Acceptance criteria:**

- AC-02-1: The engagement create form includes a "Service" picker field, positioned before the billing arrangement field. The picker shows active services grouped by service line (same grouping as Settings).
- AC-02-2: Selecting a service auto-fills: billing arrangement (mapped from `billing_unit` — see mapping table below), default rate (if set on the catalogue item), and pre-selects the service line classification.
- AC-02-3: The auto-filled values are editable — the partner can override billing unit, rate, and service line for this specific engagement without changing the catalogue default.
- AC-02-4: The "Service" field is optional (nullable FK). Partners can create engagements without selecting a catalogue item (backward compatibility).
- AC-02-5: When a service is selected, the engagement form shows the service's revenue GL account below the service picker as an informational field: "Revenue posts to: 4001 Revenue — Tax". This is not editable from the engagement form; GL mapping is managed in Settings.
- AC-02-6: Service picker includes a search box. Searching by code (e.g. "TAX-001") or by name (e.g. "corporation tax") returns matching results.

**`billing_unit` to `billing_arrangement` mapping:**

| Catalogue `billing_unit` | Maps to `billing_arrangement` |
|--------------------------|-------------------------------|
| `hour`                   | `time_and_materials` |
| `fixed`                  | `fixed_fee` |
| `retainer`               | `retainer` |
| `per_employee`           | `time_and_materials` (rate unit = per employee) |
| `per_entity`             | `time_and_materials` (rate unit = per entity) |
| `per_event`              | `fixed_fee` (one milestone per event) |

---

### US-03: AI matches engagement letter to catalogue service

> As a partner, when I drop an engagement letter in Copilot, I want the AI to read it and suggest which catalogue service it matches, so that the engagement is pre-configured with the right service, billing unit, and rate default.

**Acceptance criteria:**

- AC-03-1: The `engagement_letter_agent` (or `chat_orchestrator` calling an extraction specialist) receives the tenant's active service catalogue as a tool response or structured context when processing a dropped document.
- AC-03-2: The agent's structured output includes `suggested_service_catalogue_id` (UUID or null) and `service_match_confidence` (0.0–1.0) alongside the existing extraction fields (client, billing terms, dates).
- AC-03-3: When `service_match_confidence >= 0.80`, the `EngagementDraftCard` in Inbox shows a "Service match" chip: "[ACC-002] Annual Statutory Accounts — 88% confidence". The chip is pre-selected but editable.
- AC-03-4: When `service_match_confidence < 0.80` or no match is found, the service field is shown blank with a placeholder "Select service (optional)". No chip is shown. The agent does not guess in ambiguous cases.
- AC-03-5: The confidence threshold for displaying a service match chip is configurable per tenant in agent autonomy settings (default: 0.80). This follows the existing `agent_autonomy_settings` pattern.
- AC-03-6: The Copilot tool `get_service_catalogue` is available to all chat agents and returns the tenant's active services as a structured list: `[{id, code, name, service_line, billing_unit, default_rate}]`. This tool is used for both document extraction and conversational service lookup ("what do we charge for personal tax returns?").
- AC-03-7: PII masking applies: the engagement letter's client name and tax ID are masked before sending to the LLM, following the existing masking pattern. Service names and billing terms are not PII and are sent unmasked.

---

### US-04: Managing partner sees P&L by service line

> As a managing partner, I want to see revenue and cost broken down by service line in the reports, so that I can identify which practice areas are most profitable and where to invest or cut.

**Acceptance criteria:**

- AC-04-1: Reports > Revenue by Service Line shows a table and bar chart with columns: Service Line, Revenue (MTD), Revenue (QTD), Revenue (YTD), as currency in the tenant's base currency. Rows: Accounting, Tax, COSEC, Payroll, Advisory, Other, Unclassified (engagements without a catalogue assignment).
- AC-04-2: Revenue is sourced from posted journal entries on the relevant revenue accounts (4000–4005). Revenue from invoices where `invoice_lines.service_catalogue_id` links to a service in a given service line is allocated to that line. Legacy invoice lines with no catalogue reference fall into "Unclassified".
- AC-04-3: Reports > Revenue by Service (granular) shows the same period columns at individual service granularity (ACC-001 Management Accounts, TAX-001 Corporation Tax Return, etc.) with a total row per service line.
- AC-04-4: Reports > Cost by Service Line shows direct costs attributed to each service line from the cost accounts (5010–5014). Cost is derived from: time entries where the related engagement has a `service_catalogue_id`, plus `project_expenses` similarly linked.
- AC-04-5: Reports > Gross Margin by Service Line shows: Revenue, Cost, Gross Margin (£), Gross Margin (%). Sorted by margin % descending by default.
- AC-04-6: Reports > WIP by Service Line shows unbilled time entries and expenses grouped by service line, with the WIP value calculated as hours × bill rate for time entries.
- AC-04-7: All service line reports support period filtering: custom date range, MTD, QTD, YTD. Default: current month.
- AC-04-8: Reports are accessible to roles `owner`, `admin`, `manager`, `finance`. Role `staff` does not see revenue or margin reports.

---

### US-05: Billing manager sets service-specific rates

> As a billing manager, I want to set different hourly rates for different services within the same rate card, so that tax advisory work and COSEC work are priced correctly for the same employee without maintaining separate rate cards.

**Acceptance criteria:**

- AC-05-1: Rate card lines (within a rate card) can optionally reference a `service_catalogue_id`. A rate card line with a service reference overrides the base role rate for that service.
- AC-05-2: The rate card editor UI shows a "Service (optional)" column in the rate card lines table. When blank, the line is a default rate for the role. When set, it is a service-specific override.
- AC-05-3: Rate resolution order when billing T&M time: (1) service-specific rate for employee's role on the matching rate card line; (2) role-level default on the rate card; (3) employee's `default_bill_rate`; (4) engagement-level rate. The system picks the first non-null value.
- AC-05-4: The invoice line description auto-populates with the service name when a service catalogue item is referenced (e.g. "Tax Advisory — T&M, June 2026" rather than "Professional Services").
- AC-05-5: When creating a billing run, the billing run summary groups WIP by service line (not just by project) so the reviewing partner can see the service-level breakdown before approving.

---

## 6. Integration Points

### 6.1 Settings > Services & Products (new page, Rupa)

New settings route: `/settings/services`. Accessible from the Settings sidebar under a new "Practice" section.

Page layout:
- Header with "Services & Products" title and "Add Service" button (owner/admin only)
- Tab strip: "All" | "Accounting" | "Tax" | "COSEC" | "Payroll" | "Advisory" | "Other"
- Table: Code | Name | Billing Unit | Default Rate | Revenue Account | Active toggle
- Row actions: Edit (pencil) | Deactivate (toggle) — Delete disabled for system items
- Edit opens a slide-over panel (not a modal) with all fields

Design note: Follow the existing settings page pattern (dark slate, `mat-table`, slide-over panel with `mat-drawer`). Use the existing `MoneyPipe` for displaying default rates. Active toggle uses `mat-slide-toggle`.

### 6.2 Engagement create and edit forms (Rupa)

- Add "Service" `mat-autocomplete` field with service line grouping (using `mat-optgroup`)
- On selection: auto-fill billing arrangement dropdown, populate default rate field, show revenue account info chip
- Service field positioned between "Client" and "Billing Arrangement" in the form layout
- The field is optional — no validation error if left blank

### 6.3 Invoice line items (Rupa)

- Invoice line edit form gets an optional "Service" reference field
- When set, auto-populates description with service name
- Line items in the invoice PDF/HTML show the service name if present

### 6.4 Rate cards (Rupa)

- Rate card line editor gets an optional "Service" column
- Tooltip on the column header: "Override this rate for a specific service. Leave blank for a role-level default."

### 6.5 Copilot — `get_service_catalogue` tool (Karya)

New PydanticAI tool registered on the `chat_orchestrator` and `engagement_letter_agent`:

```python
@tool
async def get_service_catalogue(ctx: RunContext[AgentDeps]) -> list[ServiceCatalogueItem]:
    """Return the tenant's active service catalogue for service matching and pricing lookups."""
    ...
```

Returns: `[{id, code, name, service_line, billing_unit, default_rate, default_currency}]`

This tool is called when:
- A partner asks "what do we charge for personal tax returns?" (conversational lookup)
- An engagement letter is extracted and service matching is needed
- A billing run summary is being generated (to label WIP by service)

### 6.6 Reports (Karya — backend query layer, Rupa — frontend)

New report endpoints:
- `GET /api/v1/reports/revenue-by-service-line?period_start=&period_end=`
- `GET /api/v1/reports/revenue-by-service?period_start=&period_end=`
- `GET /api/v1/reports/cost-by-service-line?period_start=&period_end=`
- `GET /api/v1/reports/margin-by-service-line?period_start=&period_end=`
- `GET /api/v1/reports/wip-by-service-line`

Revenue queries join `invoice_lines` → `service_catalogue` → `accounts` and aggregate by service line. The query falls back to the engagement's `service_line` enum when `invoice_lines.service_catalogue_id` is null (progressive enrichment — not all historical data will have catalogue references).

---

## 7. Acceptance Criteria — Implementation Completeness Gates

These ACs govern the Definition of Done for the implementation ticket. They supplement the per-story ACs above.

### Backend (Karya)

- AC-BE-1: Migration creates `service_catalogue` table with all columns, constraints, RLS, indexes, and audit triggers.
- AC-BE-2: Migration adds `service_catalogue_id` FK column to `engagements`, `invoice_lines`, `rate_card_lines`.
- AC-BE-3: Migration adds service-line revenue accounts (4000–4005) and cost accounts (5010–5014) to `seed_standard_coa`, and back-fills them for all existing tenants.
- AC-BE-4: `seed_service_catalogue(p_tenant_id)` function inserts 14 system services (ACC-001 through PAY-001) referencing the correct revenue and cost accounts by code lookup. Idempotent (`ON CONFLICT DO NOTHING`).
- AC-BE-5: `seed_coa_after_tenant_insert` trigger (or equivalent) calls `seed_service_catalogue` on new tenant creation.
- AC-BE-6: `ServiceCatalogueRepository` implements: list (filtered by service_line, is_active), get_by_id, get_by_code, create, update, soft_delete (with guard on is_system items).
- AC-BE-7: `ServiceCatalogueService` enforces RBAC: create/update/delete require role `owner` or `admin`. Read is open to all tenant members.
- AC-BE-8: `GET /api/v1/service-catalogue` returns paginated list with filters `?service_line=&is_active=`.
- AC-BE-9: `POST /api/v1/service-catalogue` creates a custom service.
- AC-BE-10: `PATCH /api/v1/service-catalogue/{id}` updates a service. Returns 409 if attempting to delete a system item. Returns 400 if `is_active=false` and the item has active engagement references (soft warning: response includes `warning: "N active engagements reference this service"`).
- AC-BE-11: `DELETE /api/v1/service-catalogue/{id}` performs soft delete. Returns 403 if `is_system=TRUE`.
- AC-BE-12: Report endpoints return correct figures derived from posted journal entries, not from invoice totals (matching the accounting engine's source of truth).
- AC-BE-13: `get_service_catalogue` PydanticAI tool is registered and returns structured output. It is covered by an agent eval in `docs/test/agent_evals/engagement_letter_agent.yaml`.
- AC-BE-14: All money fields use `Decimal`, never `float`.
- AC-BE-15: `ruff check` passes with zero errors.

### Frontend (Rupa)

- AC-FE-1: Settings > Services & Products page renders the seeded catalogue on first login, grouped by service line.
- AC-FE-2: Tab strip filters the table by service line without a page reload.
- AC-FE-3: "Add Service" slide-over panel validates required fields (name, service line, billing unit) before submitting. Inline errors for missing fields.
- AC-FE-4: System items show a lock icon and the delete button is absent from the row actions.
- AC-FE-5: Engagement create form service picker shows autocomplete with optgroups. Selecting a service auto-fills billing arrangement and shows the revenue account chip.
- AC-FE-6: Revenue by Service Line report renders a bar chart (Angular Material or Chart.js — Rupa to confirm with Chitra design spec) and a summary table. Period selector defaults to current month.
- AC-FE-7: Gross Margin by Service Line report formats margin percentages with one decimal place. Negative margins display in red.
- AC-FE-8: All monetary values use the existing `CurrencyPipe` or `MoneyPipe` — no `parseFloat()` on API strings.
- AC-FE-9: Dark slate theme compliance. No inline light-mode styles.
- AC-FE-10: `ng lint` passes with zero errors.

### Agent / AI (Karya + Dhruva)

- AC-AI-1: `get_service_catalogue` tool returns results within 200ms p95 for a tenant with 50 catalogue items.
- AC-AI-2: Engagement letter extraction for a standard UK PS firm engagement letter correctly suggests the matching service (TAX-001, ACC-002, etc.) with confidence ≥ 0.80 in at least 4 of 5 test cases in the eval pack.
- AC-AI-3: Confidence < 0.80 correctly produces `suggested_service_catalogue_id = null` (no hallucinated match).
- AC-AI-4: Conversational query "what do we charge for corporation tax returns?" returns the catalogue entry for TAX-001 with the default rate if set, or states "no default rate configured" if null.

### QA / E2E (Aksha)

Aksha to produce scenario document at `docs/test/e2e_service_catalogue.md`. Minimum required scenarios:

- SC-01: Admin adds a custom service "R&D Tax Credits Advisory" under Tax, sets billing unit = fixed, default rate blank, verifies it appears in the catalogue and in the engagement service picker.
- SC-02: Partner creates engagement for Nexus Capital Partners, selects TAX-001 from the picker, verifies billing arrangement auto-fills as fixed_fee.
- SC-03: Drop nexus_engagement_letter.pdf in Copilot. Verify EngagementDraftCard shows service match chip "ACC-002 — Annual Statutory Accounts" with confidence ≥ 80%.
- SC-04: Navigate to Reports > Revenue by Service Line. Verify Accounting, Tax, COSEC, Payroll rows are present with correct YTD totals (post-seed data from demo scenario).
- SC-05: Attempt to delete system item ACC-001 — verify delete button is absent.
- SC-06: Deactivate CSC-004 — verify it disappears from the engagement service picker but remains visible in Settings with "Inactive" badge.

---

## 8. Reports Enabled

This feature unlocks the following reporting capabilities, all previously impossible:

| Report | Source | Key insight |
|--------|---------|-------------|
| Revenue by Service Line | `invoice_lines.service_catalogue_id` → GL accounts 4000–4005 | Which practice area earns the most |
| Revenue by Service (granular) | Same, at individual service code level | Which specific services drive revenue |
| Cost by Service Line | `time_entries` / `project_expenses` via engagement → `service_catalogue_id` | Which services are most expensive to deliver |
| Gross Margin by Service Line | Revenue − Cost per service line | Which services are most profitable |
| WIP by Service Line | Unbilled time entries grouped by service catalogue | Where unbilled work is accumulating |

These five reports directly support the month-end close scenario (DEMO §5.4) where Marcus reviews utilisation and WIP across service lines.

---

## 9. MoSCoW Prioritisation

### Must (v1, this ticket)
- `service_catalogue` table, migration, RLS, seed data (14 items)
- Service-line revenue accounts seeded in COA (4000–4005)
- FK additions to `engagements`, `invoice_lines`, `rate_card_lines`
- CRUD API endpoints
- Settings > Services & Products UI
- Engagement create form service picker with auto-fill
- `get_service_catalogue` Copilot tool
- Service matching in engagement letter extraction
- Revenue by Service Line and Gross Margin by Service Line reports

### Should (v1, can follow in same sprint)
- Revenue by Service (granular) report
- WIP by Service Line report
- Rate card service-specific rate overrides
- Billing run summary grouped by service line

### Could (v1.1)
- Cost by Service Line report (requires cost rate tracking to be tightened)
- Service-level P&L with blended cost rate calculations
- Bulk import of custom services via CSV
- Service templates shared across tenants in the same firm group

### Won't (explicitly out of scope)
- Service catalogue shared between tenants (each tenant owns their own)
- Product inventory / stock / physical goods
- Pricing rules engine (volume discounts, tiered rates per service)
- Integration with external service management tools (ConnectWise, ServiceNow)

---

## 10. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| OQ-1 | Should service codes be auto-generated (ACC-NNN) or always user-specified? Proposed: auto-generate if blank; allow override. | Netra / Rupa | Proposed — confirm with Vishwa |
| OQ-2 | The existing `engagements.service_line` enum (migration 0031) is now partially superseded by `service_catalogue_id → service_line`. Should the free-text enum be deprecated in favour of deriving it from the catalogue? Or keep both for engagements without a catalogue reference? | Vastu | Needs architecture decision before migration |
| OQ-3 | For the demo seed (Meridian Advisory), should the Meridian-specific engagements be back-assigned to catalogue items, or only forward-looking? | Karya / Aksha | Prefer forward-only; demo seed creates engagements with catalogue references from the start |
| OQ-4 | Revenue account split: the current COA seeds a single `4000 Revenue`. Splitting into 4000–4005 changes the trial balance the demo shows. Is the demo trial balance in `DEMO_GUIDE_v2.md` prescriptive (Karya must match it) or illustrative? | Vishwa / Karya | Clarify before migration |
| OQ-5 | What is the fallback GL account for invoice lines with no `service_catalogue_id`? Proposed: fall through to the engagement's service_line → account mapping; if engagement also has no service_line, post to generic `4000 Revenue`. | Karya | Proposed — needs sign-off |

---

## 11. Success Metrics

| Metric | Target | How measured |
|--------|--------|--------------|
| Service catalogue adoption | 90% of new engagements created with a service selected (within 30 days of feature release) | `engagements.service_catalogue_id IS NOT NULL` rate |
| Report usage | "Revenue by Service Line" viewed at least once per month by ≥ 1 user per active tenant | Langfuse / analytics event |
| AI service match rate | ≥ 80% of engagement letters produce a service match suggestion with confidence ≥ 0.80 | Agent eval pack in `engagement_letter_agent.yaml` |
| Settings page completion | ≥ 80% of tenants who view Settings > Services adjust at least one item (set a default rate or add a custom service) within 7 days | Analytics funnel |
| Zero unclassified in reports | < 10% of invoice line revenue falls into "Unclassified" within 60 days of feature release | Report metric |

---

## 12. Security Considerations

The service catalogue contains no PII (no client names, no individual rates). However:

- Catalogue data is tenant-scoped; RLS must prevent cross-tenant reads. Standard RLS policy applies.
- The `get_service_catalogue` tool returns service names and rates. Service rates are not PII but may be commercially sensitive. Rates are NOT sent to the LLM in the tool response — only `id`, `code`, `name`, `service_line`, `billing_unit` are included. `default_rate` is excluded from the LLM-facing tool response to avoid rate information appearing in LLM context. Rate lookups for billing remain server-side.
- Prahari to review the tool definition before merge (standard rule: any new agent tool that reads financial data requires Prahari sign-off).

---

## 13. Dependencies and Handoff Plan

### Pre-implementation (before Karya starts)
1. Vastu pre-implementation review — confirm data model, FK strategy, OQ-2 resolution (service_line enum deprecation or coexistence)
2. Chitra design spec for Settings > Services & Products page and engagement form picker
3. Aksha scenario document at `docs/test/e2e_service_catalogue.md`

### Implementation order
1. **Karya** — Migration (table + FK additions + COA extension + seed function), API endpoints, `get_service_catalogue` tool, report query layer
2. **Rupa** — Settings page, engagement form picker update, invoice line service field, report frontend
3. **Karya + Dhruva** — Agent eval pack update for `engagement_letter_agent.yaml`

### Post-implementation (before merge)
1. Vastu post-implementation review
2. Aksha runs scenario suite; signs off `status:in-review`
3. Prahari reviews `get_service_catalogue` tool definition
4. Vishwa final review and merge

---

## Changelog

### [2026-06-21] — v1 created
- Initial PRD authored by Netra
- Scope: service_catalogue table, 14-item seed, FK additions, CRUD API, Settings UI, engagement picker, AI service matching, 5 service line reports
- Open questions OQ-1 through OQ-5 identified; pending Vishwa + Vastu resolution before implementation starts
- Firm context: Meridian Advisory Group LLP (4 service lines: Accounting, Tax, COSEC, Payroll) from DEMO_GUIDE_v2.md
