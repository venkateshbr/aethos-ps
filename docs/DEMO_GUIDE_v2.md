# Aethos — Scenario-Based Demo Guide v2

> **Firm**: Meridian Advisory Group LLP
> **Base Currency**: GBP (£)
> **Service Lines**: Accounting & Advisory · Tax Services · Company Secretarial · Payroll
> **Markets**: UK (primary), Singapore, US (cross-border clients)
> **Guide version**: 2.5 · 2026-07-15 · adds Getting Started (login + navigation
> map) and a full Platform Concepts glossary so a first-time presenter can follow
> every scenario step by step and explain each concept to clients.

## Current Product Boundaries

This is a scenario script, not evidence that each scenario passed on the
current production build. Run it at `${PRODUCTION_URL}` only after the canonical
hostname is confirmed, and record actual IDs, journals, reports, and screenshots
in the current launch-readiness runbook.

For production validation, use one continuous video-recorded browser context
per tenant from signup through final evidence capture. When validating another
role, explicitly sign out and sign in as that user inside the same context.
Parallel profiles, incognito windows, or tabs are not part of the recorded
single-session proof; start a separate recording only for a different tenant.

Authenticated browser routes use the `/app/*` namespace. The current routes
used in this guide are `/app/copilot`, `/app/inbox`, `/app/clients`,
`/app/people`, `/app/engagements`, `/app/projects`, `/app/time`,
`/app/approvals`, `/app/expenses`, `/app/invoices`, `/app/payments`,
`/app/bills`, `/app/billing-runs`, `/app/accounting/journals`,
`/app/reports`, `/app/documents`, `/app/settings`, and `/app/profile`.
The public routes are `/`, `/signup`, `/login`, and `/p/:token`. There is no
standalone `/copilot`, `/reports/*`, `/payments` batch, or `/settings/stripe`
browser route.

Current limitations that must not be demonstrated as shipped behavior:

- The public signup wizard creates the authenticated owner, tenant, Stripe
  customer, and SetupIntent after the Account step; it then selects a plan,
  confirms a card with Stripe, starts the trial, and lands at
  `/app/copilot`. A declined card therefore leaves a provisioned tenant/customer
  without an active trial; signup is not one atomic card-gated transaction.
- Signup confirms the owner email server-side. The login page has no public
  self-service "forgot password" flow. Admin-created users can receive a
  one-time set-password link or temporary password, and signed-in users can
  change their password from Profile.
- The backend exposes a Stripe Customer Portal session endpoint, but the app
  has no self-service billing-management/plan-change UI. Stripe Connect status
  is embedded in `/app/settings`; its configured callback browser path is not
  in the Angular route table and must be production-tested before a demo.
- The public invoice page is not a general client portal. There is no client
  document/engagement portal for exchanging engagement letters or other files.
- There is no Settings Rate Cards management screen. Existing rate cards can
  be selected on engagement creation and inspected on engagement detail; an
  approved engagement extraction may materialize a linked card when reviewed
  rate hints exist.
- Reports do not offer an interactive "show in transaction currency" toggle.
  Financial statements are rendered in tenant base currency; transaction-
  currency detail is shown only where a particular report supplies it.
- Reports now have From month and To month statement controls. Equal values are
  a monthly statement; a range feeds Income Statement, Cash Flow, and Statutory
  Pack, while Balance Sheet and retained earnings use the ending month as the
  as-of period. Reversed or incomplete ranges are rejected before requests.
  This behavior has focused automated proof under #370, but no live Q2
  production statement is claimed by this guide.
- There is no separate platform-administrator role in the 22-role tenant
  security catalogue. Do not present Tenant Owner as a platform administrator.
- Do not claim that uploaded text, scanned images, names, tax IDs, or bank
  numbers are automatically masked before model processing. Operational-health
  and telemetry redaction is narrower than document/LLM input handling. Use
  fictional or approved data and the configured provider's data-processing
  controls.

---

## The Firm: Meridian Advisory Group LLP

Meridian is a 45-person professional services firm based in London, with a Singapore desk. They serve three market segments:

| Segment | Typical Client | Relationship | Complexity |
|---|---|---|---|
| **Enterprise** | PE-backed groups, listed companies | Multi-year, multi-entity | High — multiple service lines, complex billing |
| **Mid-Market** | Owner-managed businesses, £5–50M turnover | Annual retainer + project work | Medium — predictable, volume-driven |
| **Private Wealth** | UHNW individuals, family offices | Personal, trust & estate | High — privacy-sensitive, bespoke |

### The Partners & Service Line Heads

- **Marcus Chen** — Managing Partner, Accounting & Advisory
- **Sarah Williams** — Tax Director
- **Priya Sharma** — Head of Company Secretarial (COSEC)
- **James O'Brien** — Payroll Manager

---

## Client Portfolio

| Client | Segment | Services | Currency | Billing Model |
|---|---|---|---|---|
| **Nexus Capital Partners** | Enterprise | Accounting + Tax + COSEC | GBP | Retainer + T&M advisory |
| **Brightwater Manufacturing Ltd** | Mid-Market | Accounting + Tax + Payroll | GBP | Fixed-fee annual + monthly retainer |
| **Alderton Family Office** | Private Wealth | All 4 lines | GBP + SGD | Bespoke retainer per entity |
| **Thornton Tech Solutions** | Mid-Market | Accounting + Tax + COSEC | USD | Fixed-fee + milestone |

---

## Pre-Demo Setup

If a disposable QA environment has just been reset with
`uv run python -m scripts.reset_operational_data --execute --confirm DELETE_ALL_TENANTS`,
there are no tenants or login users. First create a tenant/user through the
normal signup flow, then seed that tenant with the command below.

Do not run that destructive reset against a retained production tenant. For a
production validation, register a new fictional tenant through `/signup` and
follow the production E2E runbook instead of seeding business data.

1. Seed the demo tenant:
   ```bash
   cd backend
   uv run python -m scripts.seed_demo_v2 --tenant-id <uuid> --reset
   ```
2. Log in as `marcus@meridianadvisory.co.uk` (Managing Partner — owner role)
3. The Aethos Nous home appears — this is Meridian's operations hub

Store generated validation credentials only in the ignored local credential
manifest specified by the runbook and set mode 0600. The retained Ishantech
runner uses `ishantech_e2e_credentials.json`; generic disposable demo runs may
use `demo_credentials.json`. Treat either file as secret: never paste
passwords, links, tokens, or sessions into decks, guides, tickets, or
screenshots.

---

## Demo Operating Pattern

Use business-language prompts. Users should not need to know internal tool names.
The reusable prompt library lives at
[`docs/copilot/prompt-library.md`](copilot/prompt-library.md).
The exact prompts used by the live browser validation are listed in the prompt
library under **Demo Guide v2 Live Validation Prompt Set**.

Nous conversations are persistent. When you log in, Nous opens the most recent
conversation and keeps its prior messages available for follow-up questions. Use
the existing conversation when you want Nous to retain context, such as asking
"what did you just find?" after an engagement-structure readback. Click **New
chat** only when you want a separate named conversation and audit trail.

For document-driven scenarios, attach the PDF or text file first, then send the
business prompt. Aethos Nous should show the file as attached and only start
extraction when the prompt is submitted.
For every AI-assisted step, show three things:

1. **Aethos Nous intent**: the prompt and the AI's proposed action.
2. **Inbox or approval boundary**: invoices, payments, journals, statements,
   emails, and vendor exceptions route to review before final execution.
3. **Evidence check**: the resulting record, report, audit trail, and Agent Run
   Ledger or Workflow Runs entry.

High-risk actions are deliberately controlled. Aethos does most of the finance
operations work, but sensitive accounting and money-movement steps still leave
clear human approval evidence.

---

## Getting Started — Access, Login, and Navigation

New to running the demo? Read this section once and you will know where every
screen lives and how to move between them. It assumes nothing.

### 1. Reach the app and sign in

1. Open the web app URL (`${PRODUCTION_URL}` for a live demo, or
   `http://localhost:4201` for a local run). You land on the public landing page.
2. Click **Sign in** (or go to `/login`). Enter the tenant owner's email and
   password — for the Meridian fixture that is
   `marcus@meridianadvisory.co.uk`.
3. On first login for an admin-invited user, Aethos forces a password change
   before anything else; the tenant owner created at signup does not hit this.
4. After sign-in you land at **Aethos Nous** (`/app/copilot`) — the chat home.
   Everything else hangs off the left navigation rail.

> A note on signup: the public `/signup` wizard creates the owner, tenant,
> Stripe customer, and a card-setup intent, then starts a trial. For a demo you
> normally log in to an already-provisioned tenant rather than signing up live.

### 2. The screen layout

Every authenticated screen shares the same frame:

- **Left navigation rail** — jumps between modules (mapped below).
- **Top bar** — tenant name, the signed-in user, and sign-out.
- **Main panel** — the module you selected.
- **Aethos Nous** is itself a full-screen module, not a floating widget.

### 3. Navigation map — what each left-nav item is for

| Nav item | Route | What you do here |
|---|---|---|
| **Aethos Nous** | `/app/copilot` | Chat with the AI. Ask questions, drop documents, request actions. The primary surface. |
| **Inbox** | `/app/inbox` | The human approval queue. AI proposals (invoices, payments, journals, emails) wait here for a person to approve, edit, or reject. |
| **Clients** | `/app/clients` | Customers and vendors (contacts). A contact can be a customer, a vendor, or both. |
| **People** | `/app/people` | Employees — role, cost rate, bill rate, utilization target. Feeds margin and WIP. |
| **Engagements** | `/app/engagements` | The commercial contracts with clients (the "deal"). Holds billing terms. |
| **Projects** | `/app/projects` | The delivery workstreams that sit under an engagement. Where time and cost land. |
| **Time** | `/app/time` | Time entries — billable and non-billable hours logged against projects. |
| **Approvals** | `/app/approvals` | Manager review of submitted timesheets before those hours become billable. |
| **Expenses** | `/app/expenses` | Project expenses (e.g., billable client travel) with receipts. |
| **Invoices** | `/app/invoices` | Customer invoices (accounts receivable). Draft → approve → send → paid. |
| **Payments** | `/app/payments` | Money received against invoices, including FX detail. |
| **Bills** | `/app/bills` | Vendor bills (accounts payable). Draft → approve → paid. |
| **Billing Runs / Pay Bills** | `/app/billing-runs` | Batch billing and the vendor payment-batch lifecycle. |
| **Accounting** | `/app/accounting/journals` | The general ledger — journal entries, manual journals, period locks. |
| **Reports** | `/app/reports` | All management and financial statements (12 tabs). |
| **Documents** | `/app/documents` | Uploaded source files (engagement letters, invoices, receipts) and their lineage. |
| **Settings** | `/app/settings` | Tax, services, collections policy, roles, users, approval controls, agent autonomy, AI runtime, operational health, integrations. |
| **Profile** | `/app/profile` | The signed-in user's own account and password. |

The public-facing routes are the landing page (`/`), `/signup`, `/login`, and
the public invoice page `/p/:token` a customer opens to view and pay an invoice.

### 4. Suggested demo run order

Follow the scenarios in order (1 → 7). If you want the shortest impressive path:
start in **Aethos Nous** with a couple of read-only questions (Scenario 6.1),
then show a **document drop → Inbox approval** (1.1), then **Reports** (5.3–5.5).
Scenarios 1–4 are client stories (O2C, tax, multi-entity, multi-currency),
Scenario 5 is the monthly close (R2R), Scenario 6 is the AI Finance Ops Manager,
and Scenario 7 is enterprise controls and audit.

---

## Platform Concepts Explained (Read This Before Demoing)

This is the plain-English dictionary of everything the scenarios reference. Each
entry says **what it is**, **why it matters to a client**, and **where you see
it**. Read it once and you can confidently narrate any screen and answer
follow-up questions. Terms are grouped by area.

### A. The agent-first operating model

- **Aethos Nous (the Copilot)** — the chat surface and the product's front door.
  Users type business-language requests ("prepare the June Nexus billing run")
  and Nous figures out which internal tool to run. *Why it matters:* users never
  learn hidden commands. *Where:* `/app/copilot`.
- **Tools** — the concrete internal actions Nous can take (query engagements,
  draft an invoice, propose a bill-pay batch, run close, generate statements).
  Nous always calls a tool to get real data — it does not invent numbers.
- **HITL (Human-in-the-loop)** — the rule that the AI proposes but a human
  disposes. Sensitive actions (sending invoices, paying bills, posting journals,
  emailing clients) never fire automatically. *Why it matters:* this is the core
  trust story — AI does the work, humans keep control of money and the ledger.
- **Inbox** — the shared human work queue where every AI proposal waits for a
  decision: **Approve**, **Approve with edits**, or **Reject**. *Where:*
  `/app/inbox`.
- **`agent_suggestions` vs `hitl_tasks`** — under the hood, the AI's immutable
  proposed output is an *agent suggestion*; the human work item created from it is
  a *HITL task* (what you see as an Inbox card). The split preserves an audit
  trail: the original AI output is never edited, only acted upon.
- **Agent autonomy levels (L1/L2/L3)** — how much an agent may do on its own.
  **L1** = observe only; **L2 = suggest** (creates an Inbox item, needs human
  approval) — this is the **default** for every agent; **L3 = auto-apply** (acts
  without a human), granted only after confidence and correction-rate thresholds
  are met **and** an admin approves. *Why it matters:* autonomy is earned, not
  assumed. *Where:* Settings → Agent Autonomy.
- **Accounting Guardian** — a special control agent that always runs at L3 and
  **cannot be disabled**. It enforces balance, period locks, and posting rules on
  every journal. *Why it matters:* the books cannot be corrupted even by other
  agents.
- **Confidence chip** — the percentage badge on an AI extraction (e.g., "91%,
  amber — mixed billing needs review"). Green = high confidence, amber = review
  recommended. *Why it matters:* the AI tells you how sure it is.
- **Agent Run Ledger** — the record of each AI run: input, output, tools used,
  evidence snapshots, and the human decision. Supports **replay** (re-validating
  a read-only step without re-firing side effects). *Where:* Settings → Agent Runs.
- **Workflow Runs** — the record of multi-step orchestrated workflows (e.g., a
  scheduled close) and where each one is waiting on a human. *Where:* Settings →
  Workflow Runs.
- **AI runtime & semantic router** — Nous can run on the **Advanced (Hermes)**
  runtime or the built-in **Aethos Basic** runtime, and an optional
  confidence-gated **semantic router** classifies a prompt into a finance intent
  before calling a model. *Where:* Settings → Agent Autonomy → AI Inference
  Settings. *For a demo, either runtime is fine.*

### B. Clients, people, and delivery structure

- **Contact / Client** — a person or organisation you deal with. Its **kind** is
  *customer*, *vendor*, or *both* (e.g., a family office you bill but also
  reimburse). *Where:* `/app/clients`.
- **Engagement** — the commercial agreement with a client: the "deal" and its
  billing terms. One client can have many engagements. *Where:* `/app/engagements`.
- **Project (workstream)** — a unit of delivery **under an engagement**. Time and
  cost are tracked per project, so each workstream has its own P&L while rolling
  up to the engagement. *Where:* `/app/projects`.
- **Billing arrangements** — how an engagement charges. Aethos supports:
  - **time_and_materials (T&M)** — bill hours × rate as incurred.
  - **fixed_fee** — one agreed price for a defined scope.
  - **retainer** — a recurring fee for a period (e.g., £8,500/month).
  - **retainer_draw** — a retainer that is drawn down against work performed.
  - **milestone** — fixed amounts recognised as deliverables complete.
  - **capped_tm** — T&M that stops at an agreed cap (client protection).
  - **mixed** — a combination on one engagement (fixed + retainer + T&M + expenses).
  *Why it matters:* real PS firms use all of these, often together — Aethos bills
  each correctly from one dataset.
- **Rate card** — the table of who bills at what rate (e.g., Partner £350/hr,
  Manager £240/hr) attached to an engagement. There is no standalone Settings
  rate-card editor; rate cards are selected on the engagement and can be
  materialised from an approved engagement-letter extraction.
- **Service catalogue** — the firm's standard list of services (management
  accounts, VAT returns, COSEC filings, payroll) that engagements and invoice
  lines draw from. *Where:* Settings → Services.
- **Cost rate vs bill rate** — an employee's **cost rate** is what they cost the
  firm per hour; the **bill rate** is what the client is charged. The gap is
  margin. *Where:* `/app/people`.
- **Utilization** — the share of an employee's time that is billable. Feeds
  capacity and burnout signals. *Where:* Reports → Utilization.
- **Time entry** — logged hours against a project, flagged **billable** or
  **non-billable**, optionally requiring approval before it can be invoiced.
- **Project expense** — a cost booked to a project (e.g., billable client travel)
  with a receipt; billable expenses flow into invoicing, non-billable ones do not.
- **WIP (Work in Progress)** — delivered-but-not-yet-billed value (hours × rate +
  billable expenses). *Why it matters:* it shows revenue you have earned but not
  invoiced. *Where:* Reports → WIP.

### C. Order-to-Cash (O2C) — getting paid

- **Invoice** — a bill **to a customer** (accounts receivable). Lifecycle:
  **draft → approved → sent → paid**; it can be **partially paid**, **overdue**,
  **disputed/on-hold**, or **void**. Posted invoices are immutable. *Where:*
  `/app/invoices`.
- **Billing run** — the batch step that turns billing terms, approved time,
  expenses, retainers, and milestones into draft invoices in one pass. *Where:*
  `/app/billing-runs`.
- **Public invoice page** — the customer-safe page at `/p/:token` where a client
  views and pays an invoice. It shows only invoice fields — never internal
  comments, run-ledger entries, or approval history.
- **Payment** — money received against an invoice. Captures amount, currency,
  and (for foreign currency) the base amount and FX rate used. *Where:*
  `/app/payments`.
- **Stripe Payment Link vs Stripe Connect** — a **Payment Link** lets a customer
  pay a specific invoice online; **Connect** additionally routes the payout to the
  firm's connected account. Connect is optional — without it, invoices still work
  via PDF and manual "record payment".
- **Collections** — chasing overdue invoices. The **collections policy** sets
  reminder cadence and tone (gentle → firm → final); drafted reminders route to
  Inbox before any email is sent. *Where:* Settings → Collections Policy.
- **AR Aging** — outstanding receivables bucketed by age (0–30, 31–60, 61–90,
  90+). Ties to the `1200 Accounts Receivable` control account. *Where:* Reports →
  AR Aging.
- **Tax rate / VAT** — the market tax applied to invoice lines (e.g., UK VAT 20%).
  Missing tax setup blocks invoice posting. *Where:* Settings → Tax Rates.

### D. Procure-to-Pay (P2P) — paying vendors

- **Bill** — an invoice **from a vendor** (accounts payable). Lifecycle:
  **draft → approved → paid**. *Where:* `/app/bills`.
- **Extraction** — the AI reading an uploaded vendor invoice into a structured
  bill draft (vendor, amount, tax, suggested GL account).
- **Duplicate guard** — a check that the same vendor invoice number/amount is not
  being paid twice; a suspected duplicate cannot be one-click approved.
- **PO / service-order match** — comparing the bill to an approved purchase or
  service order; a mismatch keeps the bill in draft until justified.
- **GL coding** — assigning the bill to the right expense account (e.g., `5100
  Project Costs — Subcontractors`), suggested by the AI with a confidence score.
- **Bill payment batch** — a controlled run to pay multiple approved bills. Its
  lifecycle is **prepare → approve → export → send → settle**, each a separate,
  recorded step. Batches are **single-currency**. *Where:* `/app/billing-runs`
  (Pay Bills).
- **AP Aging** — outstanding payables bucketed by age; ties to the `2000 Accounts
  Payable` control account. **Unallocated GL** preserves any control-account
  amount that cannot be matched to a specific bill. *Where:* Reports → AP Aging.

### E. Record-to-Report (R2R) — the ledger and the statements

- **Double-entry / journal entry** — every financial event posts a balanced set
  of debits and credits (debits = credits). *Why it matters:* this is what makes
  it GAAP-compliant accounting, not a spreadsheet.
- **General Ledger (GL) & Chart of Accounts (COA)** — the master list of accounts
  (Bank, AR, AP, Revenue, Expenses…) and the running balances posted to them.
- **Control account** — a GL account that must reconcile to a sub-ledger (e.g.,
  `1200 AR` ties to the invoice list; `2000 AP` ties to the bill list).
- **Sub-ledger auto-posting** — invoices, bills, payments, and expenses generate
  their GL journals automatically (via database triggers), so the ledger is never
  hand-keyed for routine activity.
- **Manual journal** — a controller's hand-made adjustment. It requires a
  **business reason**, must **balance**, respects the **period lock**, and
  high-value ones route to a **different approver** (segregation of duties).
- **Reversal** — the only way to correct a posted journal: a new journal with
  flipped debits/credits. Posted entries are immutable — history is never edited.
- **Period lock** — closing an accounting month so no new or backdated entries can
  post to it. Enforced by the Accounting Guardian. *Where:* Accounting → Period
  Locks.
- **Month-end close** — the checklist that confirms the period is ready (time and
  expenses approved, AR/AP reconciled, no unposted journals) before locking.
- **Year-end close / retained earnings** — rolling the year's net income into
  `3000 Retained Earnings` and closing the P&L accounts, done through the same
  reviewed, approval-gated journal path.
- **The financial statements** (all under Reports):
  - **Trial Balance** — every account's debit/credit totals; must balance (DR=CR).
  - **Balance Sheet** — assets = liabilities + equity, as of a period end.
  - **Income Statement (P&L)** — revenue − expenses = net income, over a period.
  - **Cash Flow** — cash movement across operating, investing, financing.
  - **Retained Earnings roll-forward** — opening equity + net income → closing.
  - **Statutory Pack** — the market-specific bundle of all the above with the
    local tax summary (GB/GBP, US/USD, etc.).
- **From month / To month controls** — the Reports date range. Equal values give a
  monthly statement; a range feeds the Income Statement, Cash Flow, and Statutory
  Pack, while the Balance Sheet and retained earnings use the ending month.
  Reversed or incomplete ranges are rejected.

### F. Multi-currency

- **Base currency** — the tenant's home reporting currency (Meridian = GBP). All
  statements render in base currency.
- **Transaction amount vs base amount** — a foreign-currency line stores both the
  original amount (e.g., $4,500) **and** the base-currency equivalent (£3,560.28).
- **FX rate provenance** — each converted line records the exact immutable
  `fx_rate` row used (`fx_rate_id`), so an auditor can trace source → journal →
  statement. Rates may be stale on weekends; the system warns when a rate is >3
  days old.
- **Realized FX gain/loss** — when the base value at invoice date differs from the
  base value at payment date, the difference posts automatically to `7900 Realized
  FX Gain/Loss`.

### G. Controls, governance, and audit

- **Security roles → duties → privileges** — access is built from fine-grained
  **privileges** (e.g., `bills.approve`, `bill_payments.settle`) grouped into
  **duties**, assembled into **roles**. There are **22 seeded roles** (Owner,
  Admin, CFO, Controller, AP Manager, AP Clerk, Finance Approver, Auditor, Viewer,
  Timesheet Employee, …). *Where:* Settings → Security Roles. **Note:** there is no
  platform-administrator role — Tenant Owner is not a platform admin.
- **Legacy role projection** — each catalogue role also maps to one legacy role
  (owner/admin/manager/approver/member/auditor/viewer/employee) that many
  endpoints still enforce; so always demo the actual allowed/denied result, not
  just the role label.
- **Finance personas** — business-language groupings (e.g., "money-in approver",
  "money-out approver") used to explain what a user can do. *Where:* Settings →
  Finance Personas / Approval Controls.
- **Approval policy / thresholds** — the rules for what needs which approver
  (manual-journal threshold, bill-pay approver role, accounting approver role).
  *Where:* Settings → Approval Controls.
- **Segregation of duties & same-user approval denial** — the person who submits a
  high-value journal or payment cannot also approve it; the denial is
  audit-visible.
- **Decision trail / audit / event hash** — every record (bill, invoice, payment,
  journal, close) carries an immutable timeline: the Inbox task, actor role,
  decision type, timestamp, safe before/after summary, and an event hash.
- **Source-document lineage** — an uploaded file is evidence, not a throwaway
  prompt: it links from upload → extraction → Inbox decision → the materialised
  record. *Where:* `/app/documents`.
- **Operational Health** — the operator dashboard: runtime status, table checks,
  rate-limit backend, request/background/agent/tool/workflow failure counts, and
  where alerts route — all shown without leaking secrets. *Where:* Settings →
  Operational Health.
- **Integrations** — the Settings surface for external service connections (e.g.,
  Stripe Connect status, email/Resend, observability). Payroll bureau processing
  (Sage, Brightpay, Xero Payroll) is on the roadmap, not in v1. *Where:* Settings
  → Integrations.
- **Rate limits & abuse paths** — public endpoints (signup, public invoice) are
  rate-limited; abuse is recorded as sanitized paths, never raw tokens.

### H. How Nous stays fast, reliable, and trustworthy

These are recent enhancements to the AI agent itself. They are mostly invisible
in normal use but are worth naming when a client asks "how do I know I can trust
the AI?":

- **Streaming answers** — Nous streams its response token-by-token as it is
  produced, so long answers start appearing immediately instead of after a pause.
  *Talking point:* "the assistant feels responsive, like a person typing."
- **Automatic fallback** — Nous runs on an advanced runtime (Hermes) with the
  built-in Aethos runtime behind it. If the advanced runtime is briefly
  unavailable, Nous **falls back automatically** and still answers; a circuit
  breaker means users are not made to wait request after request during an
  outage. *Where:* the answer still arrives; Settings → Operational Health shows
  the provider signal.
- **No internal leakage** — Nous only ever shows business language. Tool names,
  system prompts, provider errors, and internal identifiers are filtered out of
  the response, even mid-stream. *Talking point:* "you see the answer, never the
  plumbing."
- **Number-fidelity guard** — when Nous states a monetary figure, it is checked
  against the source records that produced it. If a figure cannot be verified,
  Nous appends a visible caveat asking you to confirm it against Reports rather
  than presenting an unverified number as fact. *Talking point:* "the AI does not
  invent totals — and it tells you when it is unsure."
- **Answer-quality evals** — a golden-prompt evaluation suite scores Nous on
  staying on-topic, never leaking internals, routing controlled actions to the
  Inbox, and number-fidelity, so quality is measured, not assumed.
- **Provenance** — every answer records which runtime produced it, alongside the
  Agent Run Ledger and Workflow Runs evidence.

> **The three-part evidence pattern (use it on every AI step):** (1) show the
> **Nous intent** — the prompt and proposed action; (2) show the **Inbox/approval
> boundary** — the item waiting for a human; (3) show the **evidence** — the
> resulting record, report, journal, and Agent Run Ledger / Workflow Runs entry.

---

## Scenario Coverage Map

| Area | Primary scenarios | Edge/control checks included |
|---|---|---|
| O2C | 1.1-1.7, 2.1-2.3, 4.1-4.3 | Engagement/SOW intake, linked rate cards, service catalogue, tax setup, time, expenses, WIP, invoices, public invoice links, Stripe/manual payment, collections, AR payment FX, viewer denial |
| P2P | 2.4-2.5 | Vendor invoice extraction, duplicate guard, PO/service-order match, GL coding, bill approval, payment approval, export, mark-sent, settlement, high-value money-out role checks |
| R2R | 3.3, 4.1, 5.1-5.6 | Close readiness, reasoned overrides, period lock, Trial Balance, statements, year-end close, manual journal reason/approval/rejection/reversal, multi-currency base amounts, FX provenance |
| AI Ops | 6.1-6.2 | Daily Finance Ops Manager, reviewed action plans, specialist dispatch, scheduled runs, stale/high-risk escalations |
| Controls and audit | 7.0-7.5 | Tenant-user invite, ERP role assignment, independent login, finance approver, approval policy, finance personas, read-only auditor, decision trails, Agent Run Ledger, Workflow Runs, document lineage, Operational Health, rate limits, alert routing |
| Reporting and management | 5.3-5.5, 6.1, 7.2 | AR/AP Aging, WIP, utilization, Project P&L, Trial Balance, Balance Sheet, Income Statement, Cash Flow, Statutory Pack, action queues |

---

# SCENARIO 1 — Enterprise Client: Nexus Capital Partners

> **Who**: Nexus Capital Partners is a mid-market PE fund with 6 portfolio companies. They need accounting, tax structuring, and COSEC across their group structure.
>
> **Relationship**: 3-year master engagement, individual service orders per entity. Annual fee: £285,000.

---

## 1.1 Onboarding a New Engagement via Document Drop

**What to show**: The AI reads an engagement letter and populates a complex engagement correctly — no manual data entry.

### Steps

1. Go to **Aethos Nous** → drop `nexus_engagement_letter.pdf` and type:
   > *"Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox."*

   The letter says:
   > *"We are pleased to confirm our engagement with Nexus Capital Partners LP for the provision of accounting and advisory services for the period 1 January 2026 to 31 December 2026.*
   > *Our fees for services are as follows:*
   > - *Group consolidation accounts (statutory): £42,000 fixed fee*
   > - *Monthly management accounts (6 portfolio companies): £8,500/month retainer*
   > - *CFO advisory services: £350/hour, billed monthly in arrears*
   > - *Out-of-pocket expenses: at cost, billed monthly*

2. Watch the AI extract:
   - Client: Nexus Capital Partners
   - Billing arrangement: **Mixed** (fixed fee £42,000 + retainer £8,500/month + T&M £350/hr)
   - Start date: 2026-01-01
   - Confidence chip: 91% (amber — reason: mixed billing requires review)
   - Nous reads the extraction payload and linked Inbox task directly; it
     should not ask you to retype the client name, billing model, rate hints,
     project name, or extracted commercial terms.

3. Go to **Inbox** → see the **EngagementDraftCard**:
   - Shows extracted terms side-by-side with source document link
   - Click source document link → original PDF opens in viewer
   - The mixed billing model is pre-selected correctly
   - Shows reviewed rate hints:
     - CFO Advisory Partner — £350/hour
     - Manager — £240/hour
     - Associate — £145/hour
   - Edit: adjust cap amount, confirm hourly rate

4. **Approve** → Engagement created: *"Nexus Capital Partners — Group Accounting & Advisory"*

5. Check:
   - **Engagements** → Nexus engagement references a linked rate card
   - **Projects** → first project was created under the engagement
   - Engagement detail → the linked rate-card name or ID is present
   - Limitation: there is no Settings Rate Cards management screen to open
   - **Inbox decision history** → approval payload includes `rate_card_id` and line count

**Talking point**: *"The AI read a 12-page engagement letter, pulled out the commercial terms, created the engagement and first project, and materialised a rate card from the reviewed commercial hints. Marcus approved the packet instead of re-keying the contract."*

---

## 1.2 Project Structure Under the Engagement

**What to show**: One engagement, multiple projects for each portfolio company and workstream.

1. In **Aethos Nous**, type:
   > *"Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing."*

2. Nous should return the engagement, child projects/workstreams, billing
   arrangement and terms by workstream, linked source document/rate card state,
   and any setup gaps before billing.

3. Go to **Engagements** → open Nexus Capital Partners
4. Show the embedded projects:
   - *Statutory Accounts — FY2025* (fixed fee £42,000)
   - *Monthly Management Accounts — Portfolio* (retainer £8,500/month)
   - *CFO Advisory* (T&M £350/hr)
5. Click **Projects** in the sidebar → see all projects across all engagements
6. Filter by "Nexus" → see the full project hierarchy

**Talking point**: *"Each workstream is a separate project within the engagement — separate billing, separate P&L tracking, but all tied to the Nexus master engagement."*

---

## 1.3 Time Entry: CFO Advisory Hours

**What to show**: Consultants log time via chat — no timesheet forms.

1. In **Aethos Nous**, type:
   > *"Log 4.5 hours on the Nexus CFO Advisory project for today — board pack review and cash flow modelling"*

2. Aethos Nous returns a reviewable action card for the time entry:
   - Project: Nexus CFO Advisory
   - Hours: 4.5
   - Billable: Yes
   - Narrative: Board pack review and cash flow modelling
   - If the authenticated user maps to an employee, the entry is created for
     that employee; otherwise Nous should explain the employee-resolution
     blocker instead of claiming time tools are unavailable.

3. Response: *"Logged 4.5 billable hours on Nexus CFO Advisory — £1,575 at £350/hr"*

4. Type: *"Log 2 hours on Nexus CFO Advisory for yesterday — internal planning, non-billable"*

5. Go to **Time Entries** → see both entries. Filter by project → Nexus CFO Advisory shows 6.5 total hours, 4.5 billable.

**Talking point**: *"Partners and seniors log time in chat, the way they'd message a colleague. Billable vs non-billable is captured in the same sentence. Scope creep becomes visible instantly."*

---

## 1.3A People, Timesheet Approval, and Billable Expenses

**What to show**: Delivery records flow into WIP and invoicing with staff,
rate, approval, and receipt evidence.

1. Go to **People** → open Alice Chen:
   - Role, cost rate, target utilization, manager, and default bill rate are visible
   - These values feed utilization, project margin, and WIP reporting

2. In **Aethos Nous**, type:
   > *"Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus."*

3. Nous should return Alice-specific June approved time, pending/submitted
   time, billable expenses, utilization, WIP value, and invoice-ready entries.
   It should source the answer from time entries, project expenses, employees,
   projects, engagements, and invoice linkage.

4. Go to **Time Entries**:
   - Filter to Nexus CFO Advisory
   - Confirm billable and non-billable entries are separated
   - If using the timesheet approval flow, show approved vs pending entries before billing

5. Go to **Expenses** or upload a receipt through **Aethos Nous**:
   > *"Process this client travel receipt for Nexus CFO Advisory. Classify it as a billable project expense, attach the receipt evidence, and send anything uncertain to Inbox."*

6. Check:
   - Billable expense appears on the project and WIP/revenue workflow
   - Receipt/source-document link is preserved
   - Non-billable or unapproved items are excluded from invoice drafting
   - Project P&L shows delivery cost separately from billed revenue

**Talking point**: *"Aethos does not invoice from a free-text story. It invoices from approved people, time, expense, and rate-card records, with receipts and approvals available for audit."*

---

## 1.4 Billing Run: Mixed Model Invoice

**What to show**: A single billing run producing a correctly structured invoice across 3 billing models.

1. In **Aethos Nous**, type:
   > *"Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending."*

2. Go to **Billing Runs** → click **Run Billing** for Nexus if you want to show the UI fallback path.

3. The invoice drafter calculates:
   ```
   Line 1: Group Statutory Accounts (Fixed Fee — Milestone 1/2)    £21,000.00
   Line 2: Monthly Management Accounts — June 2026 (Retainer)       £8,500.00
   Line 3: CFO Advisory — June 2026 (12.5 hrs × £350)               £4,375.00
   Line 4: Expenses — Travel & Subsistence                             £843.20
                                                              ─────────────────
   Subtotal                                                          £34,718.20
   VAT @ 20%                                                          £6,943.64
   Total                                                             £41,661.84
   ```

4. Review the draft → click **Approve** → click **Send**

5. When server-side Stripe is configured, show the generated public invoice
   page (`/p/<token>`)
   - Nexus's finance team clicks Pay → Stripe processes → webhook fires
   - Verify both the paid/payment state and the separate DR Bank / CR AR journal.
     Current webhook handling can report `journal_posted=false` after payment
     state changes; that is a P0, not a successful automatic posting.
   - Also test the configured `/p/<token>/thanks` redirect; it is not a current
     Angular route and must not be presented as working without browser proof.

6. In **Aethos Nous**, type:
   > *"Check the Nexus June invoice after sending. Confirm invoice status, payment link readiness, AR Aging bucket, and posted journal evidence."*

7. Go to **Reports** → **AR Aging** → Nexus line shows £41,661.84 in 0-30 days

**Talking point**: *"One billing run produces a perfectly structured invoice — fixed milestone, retainer, T&M, and expenses — all from data already in the system. No copy-pasting from timesheets into spreadsheets."*

---

## 1.5 Revenue Recognition: Retainer vs Fixed Fee

**What to show**: How revenue is recognised differently across billing models — WIP, deferred revenue, and the accounting guardian's role.

1. In **Aethos Nous**, type:
   > *"Explain how Nexus June revenue is recognized across fixed-fee milestone, retainer, T&M advisory WIP, and expenses. Tie the explanation to invoice-backed journals and Project P&L."*

2. Go to **Reports** → **WIP** tab:
   - Shows Nexus CFO Advisory: 12.5 hrs × £350 = £4,375 unbilled WIP
   - Shows Statutory Accounts project: 0 WIP (fixed fee, recognised on milestone approval)

3. Go to **Accounting** → **Journal Entries** → filter to invoice-backed journals:
   ```
   DR  Accounts Receivable      £41,661.84
   CR  Revenue — Advisory Fees  £34,718.20   (recognised this period)
   CR  VAT Payable               £6,943.64
   ```

4. For the retainer portion specifically, explain:
   - Retainer fee recognised in the month it covers (June → June revenue)
   - No deferred revenue for monthly retainers
   - For annual retainer paid upfront → system would book `CR Deferred Revenue`, releasing `£8,500/month`

5. Go to **Reports** → **Project P&L** → Nexus CFO Advisory:
   ```
   Revenue (billed):     £4,375.00
   Cost (Alice: 12.5h × £150 cost rate): £1,875.00
   Gross Margin:         £2,500.00 (57%)
   ```

**Talking point**: *"Revenue recognition is baked into the accounting engine. The journal posts automatically when the invoice is approved. No manual GL entries for month-end accruals on standard billing patterns."*

---

## 1.6 Tax Advisory: T&M with Capped Fee

**What to show**: A separate Tax engagement with a T&M cap — protecting the client from overruns while ensuring Meridian is protected too.

1. In **Aethos Nous**, type:
   > *"Create an engagement for Nexus — Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun"*

2. Nous should resolve Nexus from contact data, classify the service line as
   Tax, prepare billing arrangement = **capped_tm**, cap = £22,000, base =
   £18,500, and route the engagement draft to Inbox. It should not ask for
   internal client IDs, service IDs, or engagement IDs already available in
   Aethos.

3. Approve the Inbox item if you want to materialize it during the demo.

4. Log tax advisory hours over time → when hours × rate approaches £22,000:
   - **Inbox alert** appears: *"Nexus Tax Advisory: 89% of £22,000 cap used (£19,580 billed). Alert: approaching cap."*
   - The project health automation classifies it as a capped-fee risk alert

5. Show the alert card in Inbox → click **Investigate** → navigate to the project

**Talking point**: *"Meridian agreed a £22,000 cap with the client. The platform monitors every hour logged and alerts the partner before the cap is hit — not after."*

---

## 1.7 O2C Controls, Pricing, Collections, and Public Invoice Edge Checks

**What to show**: Order-to-cash is not just invoice creation. Pricing setup,
tax, payment collection, public links, reminders, and read-only access all stay
controlled.

1. In **Aethos Nous**, type:
   > *"Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval."*

2. Go to **Settings** and quickly show:
   - **Services** → standard professional-services catalogue and active service lines
   - **Tax Rates** → UK VAT rate used by the invoice
   - Engagement detail → Nexus linked rate card from the engagement letter
   - Limitation: rate-card create/edit is not exposed as a Settings walkthrough
   - **Collections Policy** → reminder timing and tone policy
   - **Stripe Connect** → connected status or manual-payment fallback state

3. In **Aethos Nous**, type:
   > *"Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet."*

4. Aethos Nous should return:
   - Customer balances and overdue balances by currency
   - Invoice-level status: current, overdue, disputed/on-hold, partially paid, sent, draft, paid, or voided
   - Due date, aging bucket, balance due, paid amount, public invoice state, and payment-link state
   - Last reminder tone/status, reminder count, policy stage, cooldown or max-reminder blockers
   - Recommended next action, clearly separated from any draft/send action

5. For a single-invoice drilldown, type:
   > *"Review invoice INV-1001. Show due date, aging, balance due, paid or partially paid amount, public invoice and payment-link state, reminder history, collections policy stage, blockers, and recommended next action."*

6. Then ask for the controlled write action:
   > *"Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending."*

7. **Inbox** → open a collections email task:
   - Invoice, customer, recipient, tone, subject, body, confidence, and eligibility rationale are visible
   - Approval sends through the configured email path
   - Rejection records the reason and sends nothing

8. Public invoice safety check:
   - Open the Nexus public invoice link in a private browser window
   - Confirm only customer-facing invoice fields, line items, total, due date, and payment status are visible
   - Confirm internal comments, run-ledger entries, source documents, and approval history are not exposed

9. Edge-case checks to call out:
   - Missing tax setup blocks invoice posting and points the user to **Settings / Tax Rates**
   - Viewer users can inspect permitted invoice/report data but cannot approve, send, void, or record payment
   - A locked accounting period blocks backdated invoice posting
   - If server-side Stripe is configured, a Payment Link can still be created
     without Connect; Connect adds destination/on-behalf-of payout routing. If
     Stripe itself is not configured, the invoice uses the PDF-only path and
     can be settled through manual record payment.
   - Stripe webhook/reconciliation evidence is visible through payment and webhook-event records when payment automation is enabled
   - Disputed or collections-hold invoices are not reminded until the blocker is resolved
   - Partially paid invoices show remaining balance and collect only the remaining balance

**Talking point**: *"The same AI prompt can check the whole O2C chain: pricing, tax, invoice status, payment link, collections, and accounting evidence. The public invoice is customer-safe, and every external send is still approval-gated."*

---

---

# SCENARIO 2 — Mid-Market Client: Brightwater Manufacturing Ltd

> **Who**: Brightwater makes precision parts for aerospace. £28M turnover, 180 employees. They've been with Meridian 5 years.
>
> **Services**: Monthly management accounts (retainer), annual statutory accounts + CT600 (fixed fee), monthly payroll for 180 employees.

---

## 2.1 Standard Monthly Retainer Billing

**What to show**: The AI identifies routine billing, prepares the work, and keeps the approval boundary visible.

1. In **Aethos Nous**, type:
   > *"Show me Brightwater's June 2026 billing status. Prepare the monthly management accounts retainer invoice if it is due, but route the draft to Inbox before sending."*

2. Aethos Nous summarizes:
   - Engagement: Brightwater Monthly Management Accounts
   - Billing model: monthly retainer
   - Period: June 2026
   - Amount: £2,800 plus VAT
   - Approval boundary: invoice draft requires review before send

3. Go to **Inbox** → open the invoice draft card:
   - Billing terms and period are shown
   - Source engagement and client are linked
   - Reviewer can approve, reject, or approve with edits

4. Approve the draft → go to **Invoices** → show `INV-0024` to Brightwater:
   ```
   Management Accounts — June 2026 (Retainer)    £2,800.00
   VAT @ 20%                                        £560.00
   Total                                          £3,360.00
   ```
   Status: **Approved** or **Sent**, depending on the demo step completed.

5. Show the journal entry posted by the guarded invoice approval path:
   ```
   DR  Accounts Receivable    £3,360.00
   CR  Revenue                £2,800.00
   CR  VAT Payable              £560.00
   ```

6. Check:
   - **Agent Run Ledger** → Aethos Nous run and action evidence are visible
   - **Inbox decision history** → reviewer, action, and before/after payload are recorded
   - **Reports / Revenue** and **AR Aging** → Brightwater appears in the correct period

**Talking point**: *"The AI did the billing work: found the due retainer, prepared the invoice, and explained the basis. The firm still has a clean review gate before the client receives anything."*

---

## 2.2 Annual Accounts + Tax — Milestone Billing

**What to show**: A fixed-fee engagement billed across milestones — draft accounts, review, sign-off.

1. In **Aethos Nous**, type:
   > *"Show me Brightwater's annual statutory accounts and CT600 milestones. Tell me which milestones are complete, which can be billed, and what evidence will be used for the invoice."*

2. Go to **Engagements** → Brightwater → *"Annual Statutory Accounts + CT600 FY2025"*

3. Show the engagement detail — Billing arrangement: **Milestone**:
   ```
   Milestone 1: Draft accounts filed for review          £4,200  (on completion)
   Milestone 2: Client-reviewed accounts signed          £4,200  (on completion)
   Milestone 3: CT600 submitted to HMRC                  £2,800  (on completion)
   Total fixed fee                                      £11,200
   ```

4. Mark Milestone 1 as complete → **Billing Run** → invoice for £4,200 + VAT generated

5. Walk through the 3 milestones over 2 months:
   - Revenue recognised at each milestone (not upfront)
   - WIP accumulates between milestones (hours logged but not yet billed)

6. After Milestone 3: Go to **Reports** → **Project P&L** → Brightwater Annual Accounts:
   ```
   Revenue:      £11,200
   Cost (hours): £3,840  (Sarah: 16h × £240/hr cost)
   Gross Margin: £7,360 (66%)
   ```

**Talking point**: *"The client agreed to three milestone payments tied to deliverables. Revenue is recognised when the milestone is delivered — not upfront, not on cash receipt. This is clean ASC/IFRS 15 percentage-of-completion."*

---

## 2.3 Payroll Service — Per-Employee Billing

**What to show**: Payroll is billed per employee per month — Aethos tracks headcount changes automatically.

1. In **Aethos Nous**, type:
   > *"Create a payroll engagement for Brightwater — £8.50 per employee per month, 180 employees, starting June 2026"*

2. System creates T&M engagement with rate = £8.50/employee/employee-month

3. Brightwater hires 5 people in July → consultant updates headcount:
   > *"Update Brightwater employee count to 185 for July payroll billing"*

4. **Billing Run** for July payroll:
   ```
   Payroll services — July 2026 (185 employees × £8.50)    £1,572.50
   VAT @ 20%                                                  £314.50
   Total                                                    £1,887.00
   ```

5. Show the collections agent working in the background:
   - Brightwater is consistently a net-30 payer
   - Collections agent has learned this pattern and suppresses reminders until day 32
   - On day 32, a gentle reminder email is drafted and routed to Inbox before sending

**Talking point**: *"Payroll billing scales with the client's headcount. When they hire, the next month's invoice reflects it automatically. And the collections agent has learned Brightwater always pays by day 32 — no spam reminders before that."*

---

## 2.4 Vendor Bills: Brightwater Subcontractor

**What to show**: Meridian sub-contracts some Brightwater work to a specialist firm. The invoice comes in, gets extracted, reviewed, and posted to AP.

1. In **Aethos Nous**, upload `brightwater_subcontractor_invoice.pdf` and type:
   > *"Process this vendor invoice for Forster & Reid Ltd. Match it to Brightwater, code it to subcontractor project cost where appropriate, flag any duplicate or PO mismatch risk, and send the bill draft to Inbox for review."*

2. Aethos Nous extracts:
   - Vendor: Forster & Reid Ltd (new vendor — matched with 72% confidence against existing contacts)
   - Amount: £3,200
   - GL suggestion: **Project Costs — Subcontractors** (account 5100), confidence 94%
   - Project/customer hint: Brightwater Annual Accounts
   - Duplicate guard: no exact vendor invoice number match
   - PO/service-order match: no approved PO found, exception requires review
   - Tax ID check: UK VAT GB123456789 — ✅ format valid

3. **Inbox** → BillExtractedCard shows:
   - Amber confidence chip (72% vendor match — needs review)
   - GL account pre-selected as 5100 (high confidence)
   - Source document link
   - Match/coding evidence, duplicate guard details, and required correction fields

4. Review → edit vendor to confirm it is Forster & Reid → enter reason:
   > *"Legitimate new subcontractor invoice for Brightwater audit support; no existing PO, approved by engagement partner."*
   Then **Approve**.

5. Bill approved → journal posts:
   ```
   DR  Project Costs — Subcontractors (5100)    £3,200.00
   CR  Accounts Payable                          £3,200.00
   ```

6. Go to **Bills** → BILL-0041 shows approved, due 15 July 2026 (Net 30)

7. In **Aethos Nous**, type:
   > *"Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet."*

8. Aethos Nous should return:
   - Vendor balances and due-soon totals by currency
   - Bill-level state: draft, approved, paid, voided, duplicate risk, or missing evidence
   - Coding status, source document availability, duplicate review state, PO/service-order match state
   - Payment readiness, blockers, safe batch status, export presence, send/settlement state
   - No raw bank details, export hashes, tool calls, traces, logs, or raw payloads

9. For a single bill drilldown, type:
   > *"Review bill BILL-0041. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action."*

10. Then ask for the controlled payment action:
   > *"Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox."*

11. **Inbox** → approve the bill-pay proposal. Then go to **Pay Bills**:
   - Draft payment batch exists
   - Forster & Reid is selected with due-date rationale
   - An AP Manager/AP Clerk with `bills.approve` can approve the source bill
   - Use an AP Manager with `bill_payments.prepare`,
     `bill_payments.approve`, `bill_payments.export`, and
     `bill_payments.settle` for the batch lifecycle; no legacy-role fallback is
     required
   - The seeded AP Clerk duty currently includes those same broad payment
     privileges, so using a separate AP Manager here demonstrates process
     segregation rather than claiming the default Clerk role enforces it
   - Export CSV/NACHA file where available
   - Mark batch sent
   - Confirm settlement when bank confirmation is received

12. Check:
   - **Bills** → bill status moves from approved to paid/settled
   - **AP Aging** → Forster & Reid drops out of unpaid AP
   - **Journal Entries** → settlement journal evidence is visible
   - **Financial Events** or decision trail → bill approval, batch approval, export/send, and settlement events are recorded

**Talking point**: *"Meridian received the subcontractor invoice, the AI extracted and coded it, the partner approved the exception in Inbox, and bill pay followed a controlled approve-export-send-settle lifecycle."*

---

## 2.5 P2P Exception and Payment-Control Edge Checks

**What to show**: Vendor invoice intake, bill approval, and payment approval are
separate controls. Exceptions must be explained before a bill or payment batch
can move forward.

1. In **Aethos Nous**, type:
   > *"Review this possible duplicate vendor invoice. Compare the vendor, invoice number, amount, date, source document, and coding evidence. If it is legitimate, require a duplicate-review reason before approval."*

2. **Inbox** → duplicate bill draft check:
   - One-click approval is blocked
   - **Approve with edits** requires a duplicate-review reason
   - The reason is persisted to the created bill's review evidence

3. In **Aethos Nous**, type:
   > *"Show me vendor match evidence, duplicate guard details, GL coding suggestions, project and customer hints, source document link, and required reviewer corrections for this invoice before I approve it."*

4. **Bills** → open the bill detail:
   - `vendor_invoice_review` evidence is visible in business terms
   - Line-level PO/service-order match summary is visible
   - Quantity, unit-price, unmatched-line, or service-period exceptions keep the bill in draft until corrected or justified

5. In **Aethos Nous**, type:
   > *"Which vendor bills are due soon, which are blocked, and what evidence supports payment? Show vendor, bill number, amount, due date, status, coding evidence, source document, duplicate risk, PO/service-order match, payment-batch state, blockers, and next action. Do not create a payment batch yet."*

6. Then type:
   > *"Prepare a payment approval packet for bills due in the next 10 days. Include vendor, amount, due date, coding evidence, duplicate status, cash impact, and the approver role required for the batch."*

7. Payment edge checks:
   - Direct batch actions enforce `bill_payments.prepare`,
     `bill_payments.approve`, `bill_payments.export`, and
     `bill_payments.settle`; prove AP Manager succeeds without admin fallback
   - Bill create/void and approval separately enforce `bills.manage` and
     `bills.approve`; verify a seeded AP role succeeds without admin fallback
   - Finance Approver can approve/reject manager-threshold Inbox/procurement reviews but cannot create bills, create procurement documents, or approve Admin/Owner-threshold spend
   - Viewer and Auditor users can inspect Pay Bills when granted
     `bill_payments.read`, but cannot create/approve a batch, export files,
     mark sent, or settle it
   - Limitation: vendor-bank validation is not a proven execution block and the
     current export can contain blank/placeholder bank fields. Stop before
     download/upload and record the gap.
   - Payment file export, mark-sent, and settlement confirmation are separate recorded lifecycle steps
   - Settlement posts a DR Accounts Payable / CR Bank journal and updates AP Aging and Cash Flow
   - Draft, paid, voided, duplicate-risk, PO-mismatch, and missing-evidence bills are explained before payment
   - Existing draft/approved/sent payment batches are shown without exposing raw bank details or export hashes
   - Limitation: partial AP payments, early-pay discounts, mixed-currency
     batches, bank-balance checks, and duplicate-open-batch prevention are not
     supported/proven by the current Pay Bills service

**Talking point**: *"P2P is deliberately staged: extract and code the invoice, approve the bill, approve the payment batch, export/send, then settle. The AI prepares each packet, but duplicate risk, PO mismatch, and money-out approval are never silently bypassed."*

---

---

# SCENARIO 3 — Private Wealth: Alderton Family Office

> **Who**: The Alderton family manages £420M in assets across 12 entities: a family investment company, 4 trading subsidiaries, 3 trusts, 2 SIPP wrappers, and 2 personal tax accounts. They demand discretion, bespoke reporting, and fast response.
>
> **Annual fees**: £148,000 across all entities and service lines.

---

## 3.1 Multi-Entity Engagement Structure

**What to show**: One client, multiple entities, separate engagements, unified view.

1. In **Aethos Nous**, type:
   > *"Show me the Alderton Family Office structure. List the entities, active engagements, currencies, billing models, and any upcoming deadlines or approvals."*

2. Go to **Contacts** → search "Alderton" → show the Alderton Family Office as `kind=both` (they're a customer for services but also a vendor when they reimburse Meridian's disbursements through their entity)

3. Go to **Engagements** → filter by client = Alderton:
   ```
   Alderton Family Investment Co — Annual Accounts           Fixed £28,000
   Alderton Trading Group — Group Management Accounts        Retainer £4,500/mo
   Alderton Trust (1985) — Trust Accounts & Tax             Fixed £12,500
   Alderton Trust (2008) — Trust Accounts & Tax             Fixed £9,200
   Sir Richard Alderton — Personal Tax Return               Fixed £8,400
   Lady Catherine Alderton — Personal Tax Return            Fixed £6,800
   Alderton COSEC Retainer — All entities                   Retainer £3,200/mo
   ```

4. Click into *Alderton Trading Group — Management Accounts*:
   - Billing: Retainer £4,500/month, billed on 1st
   - Currency: GBP
   - Show the 6-month invoice history — always paid on day 7 (fastest paying client)

**Talking point**: *"Seven separate engagements for one family. In the old world, Meridian managed this across 7 spreadsheets and 3 billing systems. Here it's one view, one Aethos Nous, one inbox."*

---

## 3.2 Bespoke Tax Return — Fixed Fee with Scope Creep Risk

**What to show**: A personal tax return engagement with unexpected complexity mid-year — and how the platform handles the conversation.

1. Open engagement: *"Sir Richard Alderton — Personal Tax Return FY2025"*
   - Fixed fee: £8,400
   - Project: Tax Return + 2 Trusts

2. Partway through: Sir Richard's advisor calls — he sold his property portfolio in March 2025, generating a complex CGT calculation across 12 properties with partial PPR relief.

3. In **Aethos Nous**, Sarah (tax director) types:
   > *"The Alderton personal tax return now includes complex CGT on 12 property disposals with PPR calculations. How much additional fee should we quote for this scope change?"*

4. Aethos Nous responds with reporting context:
   > *"Based on similar CGT-heavy returns in your history: average additional hours = 14–22h at £280/hr = £3,920–£6,160. Alderton's base rate is £240/hr (agreed blended). Comparable: Thornton property CGT last year — 18h, £4,320 additional fee. Recommend: quote £4,800–£5,500 for CGT work."*

5. Sarah raises a **supplemental engagement** for the CGT work:
   - Billing: Fixed £5,000 (agreed with client)
   - Creates new invoice milestone: "CGT Computation & Submission — £5,000"

6. Generate the engagement letter out of band, then attach it in
   `/app/copilot` for reviewed intake. Aethos does not currently provide a
   general Alderton/client document portal; `/p/:token` is invoice-only.

**Talking point**: *"When scope creeps, Sarah knows exactly what to charge because the system has history. The AI cited a comparable past matter — actual numbers, not a gut feel."*

---

## 3.3 Trust Accounts: Multi-Currency with Singapore Dividend Income

**What to show**: The Alderton 1985 Trust holds Singapore-listed shares. Annual income declared in SGD.

1. Open engagement: *"Alderton Trust (1985) — Trust Accounts & Tax"*
   - Base billing: GBP
   - Trust holds: SGD-denominated assets

2. In **Aethos Nous**, type:
   > *"Prepare a manual journal packet for the 1985 Trust's S$42,000 SingTel dividend received on 28 March 2026. Show the GBP base-currency impact using the posting-date FX rate, route it to Inbox before posting, and verify the Trial Balance remains balanced after approval."*

   Live validation prompt:
   > *"Prepare an SGD 18,000 dividend income journal for Alderton Trust for June 2026. Show the GBP base-currency impact, FX rate provenance, required approval role, and route it to Inbox before posting."*

3. Aethos Nous responds using the FX rates table:
   > *"At 28 March 2026 rate (1 GBP = 1.7234 SGD): S$42,000 = £24,370.31. Rate is current. This journal needs controller review before posting."*

4. **Inbox** → controller reviews the manual journal packet:
   - Business reason: "Record SingTel dividend income for 1985 Trust accounts"
   - Period lock status: open
   - Required approval role: Accounting/Admin if above threshold
   - Same-user approval denied for threshold journals and Nous AI-prepared manual journals

5. Approve as Marcus or Rachel → Journal entry posts:
   ```
   DR  Cash — Singapore Account     S$42,000.00   [base £24,370.31]
   CR  Dividend Income — Foreign    S$42,000.00   [base £24,370.31]
   ```
   - entry_date = 28 March 2026
   - `base_amount` stored in GBP
   - `fx_rate_id` points to the immutable `fx_rates` row used
   - `manual_journal.posted` audit evidence includes reason, actor role, line count, and debit total

6. Go to **Reports** → **Trial Balance** → show the Foreign Dividend Income account (credit balance £24,370.31) and Cash account (debit balance includes £24,370.31)

**Talking point**: *"Every foreign income item keeps the transaction currency, the GBP base amount, and the exact FX row used. The auditor can trace the number from source document to journal to Trial Balance."*

---

## 3.4 COSEC: Automated Filing Reminders

**What to show**: The COSEC retainer covers all 12 Alderton entities' statutory filings — confirmation statements, accounts filing deadlines, trust deed changes.

1. In **Aethos Nous**, type:
   > *"Review COSEC filing reminders for Alderton entities. Show upcoming filing dates, missing evidence, billing impact, and which reminders need approval before sending."*

2. Nous should return the COSEC compliance-calendar view:
   - Entity name and filing/reference type
   - Upcoming filing date/deadline
   - Missing evidence, such as board minutes, register confirmation, or signed accounts approval
   - Billing impact against the retainer or out-of-scope work
   - Whether the reminder must be approved in Inbox before sending

3. Go to **Inbox** → show any COSEC reminder or project health review card. The reminder must remain a draft until reviewed; Nous must not send client email directly.

4. Click **Investigate** → navigates to the COSEC engagement project timeline or obligation source record.

5. Priya (COSEC manager) is notified via the Inbox:
   > "3 Alderton entities have confirmation statements due in the next 30 days"

6. Show **Projects** → filter by "COSEC" → see utilisation across all Alderton COSEC work:
   - 12 entities, each with a project
   - Priya's hours tracked across all
   - Retainer hours: 18 of 22 monthly hours used (scope creep approaching)

7. Project health automation has already created a retainer floor warning:
   > *"Alderton COSEC Retainer: 82% of monthly hours used by day 20. If current pace continues, overage of 8–12 hours likely."*

**Talking point**: *"Priya doesn't chase deadlines in a spreadsheet. The system watches every entity's milestone calendar and alerts her proactively — not after the deadline passes."*

---

---

# SCENARIO 4 — Mid-Market International: Thornton Tech Solutions

> **Who**: Thornton Tech is a London-based SaaS company, incorporated in the UK but billing in USD (US clients, US investors). They need UK statutory accounts (GBP), US tax compliance (USD), and COSEC for their UK holding co.
>
> **Challenge**: Multi-currency accounting — expenses in GBP, revenue in USD, reporting in both.

---

## 4.1 USD-Billed Engagement, GBP Base Currency

**What to show**: Meridian invoices Thornton in USD, but Meridian's books are in GBP. FX handling is automatic.

1. Go to **Engagements** → *"Thornton Tech — Accounting & Advisory FY2026"*
   - Currency: USD (Thornton's invoicing currency)
   - Meridian's base currency: GBP

2. Show the engagement detail:
   ```
   Monthly advisory retainer: $4,500/month
   Annual statutory accounts: $18,000 fixed
   ```

   Before posting, use **Settings** -> **Historical FX provenance** to look up
   USD -> GBP for the invoice date. Record the requested date, matched date,
   rate, source, immutable FX row ID, and staleness. This panel is read-only.

3. Go to **Billing Runs** → invoice for April 2026 advisory:
   ```
   Advisory Retainer — April 2026    $4,500.00 USD
   ```
   Invoice sent in USD.

4. Thornton pays via Stripe Payment Link → $4,500 received. If using manual demo data, record the same receipt from **Invoices** → **Record payment**.

5. In **Aethos Nous**, type:
   > *"Review the latest Thornton USD payment. Confirm the transaction amount, GBP base amount, FX rate used, realised FX impact, and whether AR Aging and Cash Flow updated after settlement."*

6. Go to **Payments** → show the receipt:
   - `amount`: $4,500.00
   - `currency`: USD
   - `base_amount`: £3,560.28
   - `fx_rate_id`: populated for the payment-date USD→GBP rate

7. Go to **Accounting** → **Journal Entries** → show the payment journal:
   ```
   DR  Bank (1100)                   $4,500.00  [£3,560.28 @ 1.2641 GBP/USD]
   CR  Accounts Receivable            $4,500.00  [£3,560.28 @ 1.2641 GBP/USD]
   ```
   - `base_amount` = £3,560.28 locked at the payment-date rate
   - `fx_rate_id` is stored on both payment journal lines
   - If the invoice-date base total differs from the payment-date base amount, realised FX is calculated automatically

8. Next month USD weakens. Invoice at new rate:
   - May invoice: $4,500 → £3,492.18 at 1.2882 GBP/USD (rate deteriorated)
   - Realised FX service posts the base-currency adjustment:
   ```
   DR  Realized FX Loss (7900)    £68.10
   CR  Accounts Receivable        £68.10
   ```

9. Go to **Reports** → **Revenue by Engagement** → Thornton:
   - Verify the tenant-base GBP revenue and any transaction-currency detail the
     current response actually supplies
   - Limitation: there is no interactive USD/GBP report-currency toggle
   - **AR Aging** no longer includes the paid invoice
   - **Cash Flow** reflects the GBP base receipt

**Talking point**: *"Thornton pays in dollars. Meridian's books are in pounds. Every receipt captures the USD transaction amount, the GBP base amount, the FX row used, and any realised gain or loss."*

---

## 4.2 Startup Equity Event: Milestone Billing for Fundraise Advisory

**What to show**: Thornton is raising a Series A. Meridian advises on the tax structuring. This is high-stakes work billed on a success milestone.

1. In **Aethos Nous**, type:
   > *"Create a new engagement for Thornton Tech — Series A tax structuring advisory. Success fee: 0.75% of funds raised, payable on closing. Estimated raise: $12M."*

2. System creates:
   - Billing arrangement: **Milestone** (single milestone: "Series A Close")
   - Milestone amount: 0.75% × $12,000,000 = $90,000 (estimated)
   - Note: actual amount confirmed at close

3. Months later: Series A closes at $14.2M.

4. In **Aethos Nous**: *"Thornton Series A closed at $14.2M. Update the milestone amount and invoice."*

5. Agent updates milestone to 0.75% × $14,200,000 = $106,500 → billing run generates:
   ```
   Series A Tax Structuring — Success Fee    $106,500.00
                                             £84,142.35 (at closing rate)
   ```

6. Invoice sent → Thornton pays → $106,500 posted:
   ```
   DR  Bank — USD Account           $106,500.00   [£84,142.35]
   CR  Accounts Receivable          $106,500.00   [£84,142.35]
   ```

7. Go to **Reports** → **Project P&L** → Thornton Series A:
   ```
   Revenue:     $106,500.00  (£84,142.35)
   Cost:        $8,400.00    (£6,636.84)  — 42 hours at Sarah's $200/hr cost
   Gross Margin: 92%
   ```

**Talking point**: *"A £84,000 success fee. One billing run. The AI updated the milestone amount, generated the invoice, and posted the journal. The partner's only job was approving the updated amount."*

---

## 4.3 COSEC: Company Changes → Per-Event Billing

**What to show**: COSEC for Thornton is billed per statutory event, not a retainer. Each Companies House filing triggers a bill.

1. Thornton appoints a new director. In **Aethos Nous**:
   > *"Bill Thornton Tech for director appointment — AP01 filing, COSEC standard fee £650"*

2. System creates: Billing arrangement = **Fixed**, one milestone, £650

3. Thornton issues new shares for the Series A. In **Aethos Nous**:
   > *"Log COSEC work for Thornton — SH01 shares allotment filing and shareholder register update, £1,200"*

4. Upload `docs/demo-assets/thornton_cosec_instruction.pdf` in **Aethos Nous** and send:
   > *"Review this COSEC instruction for Thornton. Identify the company change, create the required filing/project work item, identify billing impact, and route any external filing or invoice action to Inbox."*

   Nous classifies the file as a COSEC instruction, prepares the company-change / filing work item review packet, identifies billing impact, and leaves external filing and invoice actions approval-gated in Inbox.

5. Thornton updates registered office. Another £250.

6. Go to **Engagements** → Thornton COSEC → show three separate mini-engagements or one T&M billing:
   - Director appointment: £650
   - Share allotment: £1,200
   - Registered office: £250
   - Total April COSEC work: £2,100

7. Billing run → single invoice consolidating all three COSEC events for April:
   ```
   Director Appointment (AP01 filing)       £650.00
   Share Allotment (SH01 + register)      £1,200.00
   Registered Office Update                 £250.00
   Subtotal                               £2,100.00
   VAT @ 20%                                £420.00
   Total                                  £2,520.00
   ```

**Talking point**: *"COSEC work is event-driven, not time-driven. Each corporate action is logged as it happens. The monthly billing run consolidates everything into one clean invoice."*

---

---

# SCENARIO 5 — Record to Report: Month-End Close

> **What to show**: At month-end, Meridian closes the books across all 4 client service lines. Show the close process, trial balance, and period lock.

---

## 5.1 AI-Assisted Pre-Close Checklist

1. Marcus (Managing Partner) opens **Aethos Nous** and types:
   > *"Prepare month-end close for June 2026. Summarize readiness blockers, missing approvals, unposted journals, open AR/AP, and proposed close tasks. Route the close preparation to Inbox before creating close tasks."*

2. Aethos Nous summarizes the pre-close checks:
   ```
   ✅ All June time entries approved (47/47)
   ✅ All June expenses approved (12/12)
   ⚠️ 2 bills received but not yet approved (Forster & Reid, £3,200; BT Broadband, £189)
   ⚠️ Brightwater WIP: 6.5 hours unbilled (£1,872 at £288/hr blended rate)
   ✅ AR sub-ledger reconciles to AR control account (£127,420.00)
   ✅ AP sub-ledger reconciles to AP control account (£42,318.00)
   ✅ Bank accounts reconciled (3/3 accounts)
   ✅ No transactions in locked prior periods
   ✅ VAT return period aligns with invoice dates
   ⚠️ Alderton SGD dividend income: FX rate >3 days old at transaction date (warning only)
   ```

3. **Inbox** → approve the close-preparation task. Approval bootstraps close tasks and records workflow evidence.

4. Two bills need approving:
   - Marcus clicks **Resolve** on the bill items → navigated to Bills list → approves both
   - Or: dismiss with reason ("Intentionally carrying to July")

5. WIP warning: Marcus decides to bill Brightwater for the 6.5 hours before close:
   - Billing run → £1,872 + VAT invoice for Brightwater

6. If a blocker is valid but intentionally waived, open **Accounting** → close package and record an override reason:
   > *"BT Broadband bill received after cutoff; approved to carry to July close package."*

7. Checklist now shows ✅ for all items or documented overrides → **Lock June 2026**

8. Check:
   - **Workflow Runs** → close workflow completed with waiting-on-human steps resolved
   - **Action Queue** → close items are no longer stale
   - **Close Package** → period-end AR/AP tie to posted base-currency control
     accounts even if a later receipt/settlement exists; unmatched control
     activity is shown as unallocated
   - **Close Package** → WIP is visibly labeled a current-rate-card estimate,
     because historical rate-card values are not versioned
   - **Close Package** → GL readiness and override reasons are visible

---

## 5.2 Period Lock in Action

1. Period locked: June 2026

2. In **Aethos Nous**, type:
   > *"Can I post a correcting journal dated 15 June 2026 now that June is locked? Explain the safe options and do not post anything."*

3. Try to post a backdated entry:
   - In **Accounting** → **New Journal Entry** → set date to 15 June 2026
   - Click Post → error: *"Period 2026-06 is locked. Entry rejected by Accounting Guardian."*

4. Correct approach: reopen June (owner-only) OR post a July correcting entry with description "Correction re June accrual"

5. Go to **Accounting** → **Period Locks** → show the lock record: locked by Marcus, timestamp, all entries frozen.

---

## 5.3 Trial Balance Review

1. In **Aethos Nous**, type:
   > *"Verify June 2026 Trial Balance. Confirm total debits equal total credits, highlight FX gain/loss, and point me to any unposted journals or close blockers."*

2. Go to **Reports** → **Trial Balance** → set period to June 2026

3. Show the 12-account COA with balances:
   ```
   Code   Account                        DR            CR
   ──────────────────────────────────────────────────────
   1100   Bank (GBP)                £87,420.31
   1101   Bank (USD — converted)    £42,318.94
   1200   Accounts Receivable       £76,840.20
   2000   Accounts Payable                        £18,420.00
   2300   VAT Payable                             £24,618.90
   3000   Retained Earnings                       £48,200.00
   4000   Revenue — Advisory       £124,800.00
   4001   Revenue — Tax             £38,200.00
   4002   Revenue — COSEC           £18,400.00
   4003   Revenue — Payroll          £8,640.00
   5000   Expenses                  £68,240.00
   5100   Employee Expenses          £9,180.00
   7900   Realized FX Gain/Loss        £240.35
   ──────────────────────────────────────────────────────
   Total                          £343,479.80   £343,479.80
   ```
   ✅ **Balanced — DR = CR**

4. FX note: £240.35 in account 7900 (net realized FX loss from USD invoices received)

---

## 5.4 Management Reporting Snapshot

Before presenting AR or AP Aging, explain that each public report is a current
snapshot in the tenant's base currency. Partial receipts and payments reduce
the posted control-account balance, the total ties to `1200 Accounts
Receivable` or `2000 Accounts Payable`, and **Unallocated GL** preserves any
control-account amount that cannot be matched to an invoice or bill. A close
package instead calculates its aging as of the selected period end.

1. **Reports** → **Project P&L** → sort by Gross Margin descending:
   - Thornton Series A: 92% (exceptional)
   - Nexus CFO Advisory: 57% (good)
   - Brightwater Annual Accounts: 66% (good)
   - Brightwater Payroll: 38% (volume margin, acceptable)

2. **Reports** → **Utilization** → June:
   - Sarah Williams: 87% billable (high — approaching burnout threshold)
   - Priya Sharma: 71% billable (healthy)
   - Alice Chen: 64% billable (below target — investigate)

3. In **Aethos Nous**, Marcus types:
   > *"Alice is at 64% utilisation in June. Which clients have unbilled WIP tied to Alice?"*

4. Aethos Nous response:
   > *"Alice has 22 unbilled hours across 3 projects: Brightwater Management Accounts (8h, £2,240), Nexus CFO Advisory (9h, £3,150), Alderton Trust 1985 (5h, £1,200). Total WIP: £6,590. Brightwater is past month-end — recommend billing today."*

5. Marcus approves the Brightwater billing run from the chat response card.

---

## 5.5 Financial Statement Package and Year-End Close

**What to show**: Aethos Nous generates a statement package from reports, not from hallucinated numbers, and year-end close remains approval-gated.

1. In **Aethos Nous**, type:
   > *"Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period."*

2. Check the management-pack response:
   - Periods are normalized to June 2026 and May 2026 even if the prompt uses business language
   - Revenue, expenses, net income, cash movement, and balance-sheet totals cite report data
   - AR/AP movement is shown separately from open AR/AP aging
   - Project margin and utilization highlights identify the source project or employee rows
   - Draft journals, locked-period state, missing close tasks, pending reviews, and close blockers are listed without mutating records

3. Ask a drilldown follow-up:
   > *"Drill into the draft journals and close task blockers for June 2026. Which ones block close, who owns them, and what should happen next?"*

4. Verify:
   - Aethos Nous keeps the answer read-only
   - No Inbox task, journal, or period lock is created by this readback
   - The blocker list agrees to **Accounting** → **Journal Entries** and the close package

5. In **Aethos Nous**, type:
   > *"Generate the financial statement package for June 2026 with Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack, close-readiness warnings, and evidence-backed management commentary. Compare it to May 2026 and show the variances."*

6. Check the response:
   - Numbers match Reports tabs
   - Variances cite report rows and close-readiness evidence
   - Missing prerequisites remain visible instead of hidden
   - No records are mutated by statement generation

7. In **Reports**, open:
   - Trial Balance
   - Balance Sheet
   - Income Statement
   - Cash Flow
   - Statutory Pack

   Use **From month = 2026-06** and **To month = 2026-06** for the monthly
   package. To exercise the implemented range control, use From 2026-04 and To
   2026-06: Income Statement, Cash Flow, and Statutory Pack receive the full
   inclusive range, while Balance Sheet and retained earnings are as of June.
   Capture the actual network parameters and tie-out before calling this Q2 a
   live PASS; the guide itself is not that evidence.

8. In **Aethos Nous**, type:
   > *"Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted."*

9. **Inbox** → review the year-end close task:
   - Retained earnings account: `3000 Retained Earnings`
   - Posting preview shows revenue and expense close-out lines
   - Duplicate close and locked-year risks are listed
   - Current-vs-prior year commentary is included

10. Approve as Owner/Admin → go to **Accounting**:
   - A `year_end_close` journal appears
   - P&L accounts are closed for the fiscal year
   - Duplicate year-end close attempt is blocked with a readable error

**Talking point**: *"Management-pack review is read-only and source-backed. Statement generation is deterministic. Year-end close is not an AI text answer; it is a reviewed accounting task that posts through the same guarded journal path."*

---

## 5.6 Manual Journal Lifecycle and R2R Edge Checks

**What to show**: Manual accounting changes are possible, but every path is
balanced, reasoned, policy-aware, and reversible through a new entry instead of
editing history.

1. In **Aethos Nous**, type:
   > *"Review this manual journal proposal for balance, account validity, period lock status, business reason, supporting evidence, approval role, and whether the approver is different from the submitter. Do not post it without Inbox approval."*

2. Nous should summarize the manual-journal review packet:
   - Balance check and debit/credit equality
   - Account validity for debit and credit lines
   - Period lock status
   - Business reason and supporting evidence
   - Required approval role and whether the approver must be different from the submitter
   - Confirmation that the journal is not posted without Inbox approval

3. In **Accounting** → **Journal Entries**, demonstrate:
   - A balanced under-threshold manual journal created from the Accounting UI with a business reason posts through the guarded path
   - A missing or short reason is rejected with a clear validation message
   - An imbalanced journal is rejected and no journal is posted
   - A posting date in a locked period is rejected with the period-lock message

4. High-value journal approval:
   - Set or show the manual-journal approval threshold in **Settings / Approval Controls**
   - Submit a high-value balanced journal with a reason
   - It creates an Inbox review task instead of posting immediately
   - Same-user approval is denied and remains audit-visible
   - A different Accounting/Admin approver can approve and post it
   - Rejection captures the rejection reason and posts no journal

4. Reversal check:
   > *"Prepare a reversal packet for this posted manual journal. Explain why reversal is appropriate, propose an open-period reversal date, show the flipped debit and credit lines, and confirm the reversal will create a new journal rather than editing the original."*

5. Verify:
   - Reversal creates a new `manual_reversal` journal with flipped lines
   - The original journal remains immutable
   - Attempting to reverse the same original twice is blocked
   - Non-manual journals cannot be reversed through the manual-journal path
   - Trial Balance and financial statements remain balanced after posting or reversal

6. Multi-currency edge check:
   - Foreign-currency manual journal lines store transaction amount, base amount, and FX rate provenance
   - If no FX rate exists for the posting date/currency pair, posting is rejected rather than silently guessing

**Talking point**: *"Manual journals are not a back door. The controller can still make accounting adjustments, but Aethos requires a reason, validates balance and period, routes high-value items to a different approver, and fixes mistakes with reversals rather than edits."*

---

---

# SCENARIO 6 — Finance Ops Manager Command Center

> **What to show**: A finance department run by AI agents, with humans reviewing exceptions and high-risk actions.

---

## 6.1 Daily Finance Ops Check and Reviewed Work Plan

1. In **Aethos Nous**, type:
   > *"Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval."*

2. Aethos Nous returns sections:
   - AR: overdue invoices, collection drafts, paid invoice exceptions
   - AP: approved bills due, duplicate or unmatched bills
   - WIP: unbilled time and expenses
   - Close: readiness blockers and open tasks
   - Reports: margin, utilization, action queue exceptions
   - Agent activity: failed/skipped runs and pending approvals

3. In **Aethos Nous**, type:
   > *"Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly."*

4. **Inbox** → approve the Finance Ops action plan.

5. After approval, type:
   > *"After I approve the action plan, create the specialist follow-up tasks for the approved Plan Items. Keep final invoices, payments, journals, statements, and emails behind their own approvals."*

6. Check:
   - Parent action-plan task is approved
   - Child Finance Ops action-item tasks appear
   - Plan Item approval dispatches specialist workflows such as collections, bill pay, and close prep
   - Downstream money/accounting/email actions still require their own approval

**Talking point**: *"The Finance Ops Manager consolidates AR, AP, WIP, close, and reporting into one daily operating plan. It creates work for the specialist agents, but it does not silently send emails, pay bills, or post journals."*

---

## 6.2 Scheduled Finance Ops Manager

1. In **Aethos Nous**, type:
   > *"Show me the Finance Ops Manager control room. Include the current schedule, next run, latest scheduled run, failed or skipped workflows, open action plans, open Plan Items, stale approval escalations, and operational health. Do not show tool names, traces, logs, context IDs, or raw system details."*

2. Aethos Nous should return:
   - Current schedule, cadence, run hour, time horizon, and next run
   - Latest scheduled Finance Ops Manager run and status
   - Failed or skipped workflows that need review
   - Open Finance Ops action plans, Plan Items, and escalation notices waiting in Inbox
   - Operational Health status, rate-limit backend, recent failure counts, and alert route
   - No raw traces, logs, tool calls, context references, or stack traces

3. Or go to **Settings** → **Agent Autonomy** → Finance Ops Manager Schedule.

4. Configure:
   - Cadence: every business morning
   - Time: 07:00 UTC
   - Creates reviewed action plan in Inbox
   - Escalates stale high-risk approvals

5. Check:
   - **Workflow Runs** → latest scheduled run, status, period, and business summary
   - **Inbox** → scheduled action plan, Plan Items, and escalation notices awaiting review
   - **Operational Health** → runtime, table, limiter, failure, workflow, tool, and alert signals
   - **Reports / Action Queue** → assigned-to-me and all-work queues show owners and SLA chips

**Talking point**: *"This is not just chat. It is a scheduled finance-ops manager that wakes up, inspects the business, prepares a work plan, and escalates stale approvals."*

---

# SCENARIO 7 — Enterprise Controls, Audit, and Operations

> **What to show**: The platform is enterprise-ready because agents are governed, traceable, and role-aware.

---

## 7.0 Tenant User Administration and Independent ERP Login

**What to show**: Tenant owners can invite finance operators into the main
Aethos app, assign an ERP role, and audit access changes without direct database
work.

1. Log in as Marcus or another owner/admin user.

2. Go to **Settings** → **Security Roles**.

3. Show all 22 seeded roles and their current legacy enforcement projection:
   - `owner`: Tenant Owner
   - `admin`: Tenant Admin, CFO, Finance Controller, GL Accountant, Close
     Manager, AI Operations Admin
   - `manager`: Finance Ops Manager, Procurement Manager, AP Manager, AP Clerk,
     AR Manager, Billing Specialist, Collections Specialist, Engagement Manager,
     Resource Manager
   - `approver`: Finance Approver
   - `member`: Finance Operator, Buyer / Requester
   - `auditor`: Auditor
   - `viewer`: Executive Viewer
   - `employee`: Timesheet Employee

   There is no Platform Administrator role in this catalogue. Platform support
   and control-plane administration require a separately designed and tested
   boundary; they must not be represented by Tenant Owner.

4. Optional tenant-admin check: create a disposable role named
   **Demo Billing Reviewer** from seeded duties such as Finance read access,
   Billing management, and Manager-threshold approval. Confirm the role appears
   as tenant-created, not system-created.

5. Go to **Settings** → **Tenant Users**.

6. Create four demo ERP users:
   - Finance Ops Manager: security role `Finance Ops Manager`
   - Finance Approver: security role `Finance Approver`
   - Finance Controller: security role `Finance Controller`
   - Read-only Auditor: security role `Auditor`

   This four-person switch is only the short demo. The production launch run
   must create and independently test all 22 configured roles.

7. For each user, set or capture the initial password. Confirm the user row
   shows initial password change required.

8. After invite, show the generated temporary password or set-password link.
   Store it only in the secure demo credential file or your password manager,
   not in shared screenshots.

9. Continue in the tenant's same recorded browser context. Explicitly sign out,
   then log in sequentially as each invited user at the main Aethos app, not the
   timesheet portal. Confirm the first screen is Account/Profile and that
   changing the initial password is required before normal app navigation.

10. Validate the Finance Ops Manager can:
   - Open **Aethos Nous**
   - Open **Reports**
   - Inspect permitted Inbox and finance records
   - Create permitted operational records such as clients, engagements, projects,
     bills, procurement documents, and draft invoices
   - Ask a role-aware access prompt:
     > *"Show me which finance personas my current role maps to. Summarize what I can do in Inbox, Bills/AP, Invoices/AR, Reports, Accounting, and Settings, and which actions still need another approver."*

11. Validate the Finance Approver:
   - Can approve or reject manager-threshold Inbox/procurement review work
   - Cannot create clients, engagements, bills, procurement documents, journals,
     or tenant settings
   - Cannot directly approve payment batches because the seeded role lacks
     `bill_payments.approve`, and cannot approve Admin/Owner-threshold
     accounting or high-risk AI work

12. Validate the Finance Controller:
   - Can inspect accounting, journals, close, statements, and audit evidence
   - Can approve admin-threshold accounting work where policy allows
   - Cannot grant Tenant Owner authority

13. Validate the Auditor:
   - Can inspect reports, source documents, record details, Inbox history, and
     decision trails
   - Cannot approve, reject, create, post, pay, send, lock, or change settings

14. Switch back to Marcus and update the invited user:
   - Change display name or role where allowed
   - Confirm the Settings audit trail records the actor, target user, event,
     prior role codes, and new role codes
   - Deactivate a disposable test user and confirm they can no longer access
     the tenant

15. Explain the current role model:
   - Main ERP users are assigned seeded security roles made of duties and
     privileges
   - Each assignment projects to one legacy `tenant_users.role`; many API
     endpoints still enforce that legacy hierarchy rather than an individual
     catalogue privilege
   - Invoice, bill, payment-batch, and procurement endpoints now enforce their
     named catalogue privileges; procurement approval also preserves amount
     thresholds and rejects requester self-approval
   - Distinct catalogue roles with the same projection can therefore have the
     same effective behavior on legacy-gated routes; demonstrate the actual
     positive and negative result, not the role label alone
   - Tenant Admins can create users, create tenant roles from seeded duties,
     assign non-owner roles, and set initial passwords
   - Only Tenant Owners can grant Tenant Owner authority
   - Timesheet-only employees are invited and tested separately through the
     People/timesheet flow
   - Users cannot demote or deactivate themselves

**Talking point**: *"Aethos can run finance work through AI agents, but access is still tenant-scoped, role-assigned, privilege-driven, and auditable. Tenant Admins manage users and roles; the finance manager operates; the finance approver reviews; the auditor inspects evidence; and owner-level approvals stay with the owner."*

---

## 7.0A AI Inference Runtime and Model Routing

**What to show**: Tenant admins can configure the AI runtime and model routing
without editing deployment files.

1. Log in as Marcus or another Tenant Admin / Owner.

2. Go to **Settings** → **Agent Autonomy** → **AI Inference Settings**.

3. Show the default OpenRouter chain:
   - Primary: `google/gemma-4-31b-it:free`
   - Free router: `openrouter/free`
   - Fallback: `anthropic/claude-haiku-4.5`

4. Explain the runtime selector:
   - **Advanced Nous powered by Hermes** keeps conversation orchestration and
     memory in Hermes
   - **Aethos Basic AI** uses the built-in Aethos runtime directly

5. Explain the response routing controls:
   - **Semantic router** lets Nous classify business-language prompts into
     finance intents with confidence before calling the model runtime
   - **Minimum confidence** controls when a semantic answer is allowed. Keep the
     demo default at `0.72`
   - **Response order** defaults to `Semantic router, then configured runtime`.
     If the prompt is low-confidence, Nous falls back to Hermes or Aethos Basic

6. Save the settings and refresh the card. The effective model-chain chips
   should match the selected routing order.

7. Note the current boundary: Aethos Basic, Nous fallback, and tenant-scoped
   document/reporting agents use the tenant model chain. Hermes uses the mounted
   Nous profile for its primary model until dynamic per-tenant Hermes model
   switching is added.

**Talking point**: *"The tenant admin can decide whether Nous first uses Aethos' semantic finance router or goes straight to the configured model runtime. The semantic router is confidence-gated and still routes controlled finance actions through Inbox."*

---

## 7.1 Approval Policy, Personas, and Denied Actions

1. In **Aethos Nous**, type:
   > *"What am I allowed to approve, what requires Owner approval, and which Inbox items are high risk? Include my finance personas, effective thresholds, pending high-risk tasks, and why each item needs review. Do not show tool names, policy reason codes, raw payloads, traces, logs, or context IDs."*

2. Aethos Nous should return:
   - Current tenant role and matching finance personas
   - Finance Approver/Manager/Admin/Owner approval thresholds in business language
   - Which policy rules the current user can approve
   - Pending high-risk Inbox tasks, required approver role, and reason for review
   - Tasks requiring a higher role than the current user
   - Denied-action explanations without raw payloads or internal reason codes

3. Go to **Settings** → **Approval Controls**:
   - Manual journal threshold
   - Bill-pay approval role
   - Accounting approval role
   - Lower-risk draft, money-in, and external-send categories can use Finance
     Approver; money-out, accounting, and high-risk AI stay Admin/Owner gated
   - Finance role personas catalog

4. In the same recorded browser context, sign out and log in as Finance Approver:
   > *"What can I approve now, what requires Admin or Owner, and which actions are intentionally blocked for the Finance Approver role?"*

5. Check:
   - Manager-threshold Inbox/procurement reviews can be approved or rejected
   - Create/edit/post/pay/send/settings actions remain blocked
   - Admin/Owner-threshold money-out, accounting, and high-risk AI work remains blocked

6. In that same context, sign out and log in as Auditor:
   > *"As a read-only auditor, show me the records I can inspect for this bill-payment batch and which actions are intentionally blocked for my role."*

7. Check:
   - Auditor can inspect permitted records
   - Mutation buttons are disabled or absent
   - Direct mutation API attempts fail cleanly
   - Same-user high-value manual-journal approval is denied and audit-visible
   - Nous does not expose tool calls, policy reason codes, raw task payloads, traces, logs, or context IDs

**Talking point**: *"Aethos lets AI agents do the routine work, but approval policy and role controls decide what can actually mutate finance records."*

---

## 7.2 Decision Trail and Agent Run Ledger

1. In **Aethos Nous**, type:
   > *"Show the decision trail for this bill, invoice, payment batch, journal, or close record. Include the related Inbox task, actor role, decision type, timestamp, and before/after review summary."*

2. Nous should return the latest relevant Inbox task or decision event with:
   - Task title, kind, status, and priority
   - Actor role and decision type when a decision exists
   - Timestamp from the decision event or task update
   - Safe before/after review summary
   - Linked source entity and recent journal context
   - Segregation-of-duties note for manual journal approvals

3. Open a bill created from the Brightwater invoice:
   - Source document link
   - Vendor match evidence
   - Reviewer edits
   - Duplicate-review reason
   - GL coding evidence
   - Payment eligibility

4. Go to **Settings** → **Agent Runs**:
   - Filter by recent Aethos Nous run
   - Open run details
   - Show actions, evidence snapshots, and source records
   - Use Validate Replay for supported read-only steps
   - For posting, payment, or email steps, show the planned operator action instead of replaying the side effect

**Talking point**: *"Every AI-assisted decision has a record: input, output, reviewer, before/after payload, and action evidence. Replay is safe by design; it validates or plans side effects instead of firing them again."*

---

## 7.3 Operational Health

1. In **Aethos Nous**, type:
   > *"Review operational health for this tenant. Summarize runtime status, table checks, rate-limit backend, request failures, background failures, agent/tool/workflow failures, and routed alerts without exposing secrets or tokens."*

2. Nous should return safe platform-owned health context:
   - Runtime and Nous runtime
   - Langfuse observability configuration status, not raw traces
   - Rate-limit backend and public abuse-path indicators
   - Background worker failure spikes
   - Agent, tool, and workflow failure spikes
   - Degraded service flags and routed-alert metadata
   - Explicit safety statement that raw logs, traces, stack traces, context IDs,
     and secrets are not exposed

3. Go to **Settings** → **Operational Health**:
   - Runtime and table checks
   - Rate-limit backend state
   - Request/background failure summaries
   - Agent/tool/workflow failures
   - Alert routing

4. In **Aethos Nous**, type:
   > *"Show which operational alerts would route to the runbook or webhook today. Include degraded health, public endpoint abuse, background failure spikes, and agent/tool/workflow failure spikes."*

5. Check:
   - No secrets, raw JWTs, public invoice tokens, document text, or request payloads appear
   - Alerts route to runbook/webhook metadata only

**Talking point**: *"Enterprise readiness is not just features. It is knowing when the system is unhealthy, protecting public endpoints, and giving operators safe signals without leaking sensitive data."*

---

## 7.4 Documents, Source Evidence, and Record-Scoped Audit

**What to show**: Uploaded files are not just chat attachments. They become
source evidence tied to Inbox decisions and materialized business records.

1. In **Aethos Nous**, type:
   > *"Find source documents connected to this bill, invoice, engagement, or close task. Summarize extraction status, Inbox decision outcome, and the materialized record it supports."*

2. Go to **Documents**:
   - Show the generated demo files in `docs/demo-assets/`
   - Engagement letter → extracted engagement draft → approved engagement, first project, linked rate card
   - Vendor invoice → extracted bill draft → reviewed bill → payment batch
   - Dividend notice → manual journal packet → approved posted journal
   - COSEC instruction → engagement/project or billing event evidence

3. Open a source document link from an Inbox task or business record:
   - The file opens from the source-document surface
   - Extraction status, confidence, and document type are visible
   - Deleted or unauthorized document access follows normal tenant/RBAC controls

4. Record-scoped audit check:
   - Open the related bill, invoice, engagement, journal, or close record
   - Confirm the decision timeline shows the Inbox task, actor role, decision type, timestamp, safe before/after summary, and event hash
   - Viewer/auditor can inspect permitted evidence without gaining mutation access

**Talking point**: *"The PDF is evidence, not a one-off prompt input. Aethos carries source-document lineage from upload to Inbox decision to the business record and audit timeline."*

---

## 7.5 Configuration, Telemetry, and Abuse-Path Checks

**What to show**: Enterprise operation includes configuration surfaces, safe
telemetry, and abuse-path behavior, not only happy-path finance workflows.

1. In **Aethos Nous**, type:
   > *"Review configuration and telemetry readiness. Show approval controls, scheduled Finance Ops Manager settings, Nous runtime, Langfuse observability status, operational alerts, and any public abuse-path controls that need attention."*

2. Nous should return:
   - Approval controls and effective thresholds
   - Scheduled Finance Ops Manager cadence, escalation windows, last run, open scheduled plans, and approval boundary
   - Nous runtime mode and whether Hermes/basic fallback is configured
   - Langfuse observability configuration status without raw traces
   - Operational alerts and public abuse-path controls such as rate limits and sanitized public paths

3. In **Settings**, show the implemented configuration surfaces:
   - **Services**: active service catalogue used by engagements and invoice lines
   - **Tax Rates**: market tax setup used by invoices and bills
   - **Collections Policy**: reminder cadence and tone
   - **Agent Autonomy**: scheduled Finance Ops Manager cadence and escalation settings
   - **Approval Controls**: policy matrix and finance persona catalog
   - **Agent Runs** and **Workflow Runs**: run evidence, replay-safe validation, and failures
   - **Operational Health**: runtime shape, table checks, failure counters, limiter state, and routed alerts

4. In **Aethos Nous**, type:
   > *"Review agent activity and workflow telemetry for this tenant. Highlight failures, skipped actions, pending Inbox approvals, stale work, and anything that needs escalation."*

5. Abuse-path checks to explain:
   - Signup and public invoice endpoints are rate-limited
   - Repeated public invoice abuse records sanitized paths, not raw public tokens
   - Unauthorized tenant-health access is denied by RBAC
   - Distributed rate-limit backend state is visible without exposing hashed subjects or credentials
   - If the distributed limiter backend is unavailable, the system reports the fallback/deny-safe state in operational health
   - Routed alerts expose channel/runbook metadata only, not webhook secrets or customer payloads

6. Operator checklist:
   - Health output is safe to paste into a support ticket
   - No raw JWTs, public invoice tokens, bank details, API keys, document text, or customer payload snapshots are shown
   - Agent/tool/workflow failure counts are visible enough to triage without leaking data

**Talking point**: *"The same platform that lets AI run finance work also shows operators when automation is degraded, abusive, or waiting on review. That is the difference between a demo bot and an enterprise operating system."*

---

# DEMO CLOSING: The Agentic Difference

## What Meridian's team doesn't do anymore

| Old way (before Aethos) | New way |
|---|---|
| Type engagement terms from PDF into billing software | Drop PDF → AI extracts client, engagement, first project, and rate card → one Inbox approval |
| Send monthly retainer invoices manually on 1st | Aethos Nous or the scheduled Finance Ops Manager prepares due invoices → Inbox approval before send |
| Spreadsheet for subcontractor invoices received | Upload invoice → vendor match, duplicate guard, GL coding, bill approval, and bill-pay batch |
| Chase clients with standard email templates | Collections drafts personalised reminders based on client history → Inbox approval before send |
| Pull timesheets from 3 systems to calculate WIP | Time and WIP are live; Aethos Nous recommends what to bill and why |
| Month-end: 3-day close spreadsheet checklist | AI close prep creates reviewed tasks, close package evidence, and reasoned overrides |
| FX conversion done manually in Excel | FX rates, base amounts, and rate provenance are stored on payment and journal lines |
| Partner calls to ask "did Brightwater pay?" | Finance Ops Manager flags AR, AP, WIP, close, and approval blockers each day |
| Teach users hidden commands | Prompt library and demo guide give business-language prompts users can reuse |

## The key numbers for this demo

- **4 clients** | **£640K+ annual fees** | **7 service lines** | **3 billing models**
- **4 currencies** (GBP, USD, SGD, EUR)
- **One AI Finance Ops Manager** coordinating specialist AR, AP, WIP, close, reporting, and controls workflows
- **Approval gates** for invoice sending, bill payment, high-value journals, year-end close, and external emails
- **One Inbox**, **Agent Run Ledger**, and **Workflow Runs** for human judgment and audit evidence
- **Prompt library** plus scenario guide using real business prompts instead of internal tool names

---

## Objection Handlers

**"We already have Xero/QBO — why do we need this?"**
> Xero tells you what happened. Aethos coordinates the work: engagement terms, billing rules, WIP, AP, close, approvals, and evidence. The AI prepares the action; Inbox controls what is sent, posted, paid, or emailed.

**"Our clients have complex requirements — can AI handle that?"**
> AI extracts and proposes. Humans approve. The AI doesn't post a £106,500 invoice without the partner confirming. Complexity is handled at the engagement setup stage; once set, billing runs correctly every time.

**"What if the AI makes a mistake?"**
> Every AI suggestion has a confidence score, source evidence, Inbox decision history, and Agent Run Ledger entry. Low-confidence extraction is flagged for review. Accounting actions pass through balance checks, period-lock checks, approval policy, and same-user approval denial.

**"Do users need to know tool names?"**
> No. Users prompt in business language: "prepare bill pay", "run close readiness", "generate financial statements", "show the decision trail". Aethos Nous infers the workflow. Tool names are for engineering and QA proof, not operator training.

**"Is this enterprise-ready enough for finance operations?"**
> The demo shows role-aware approvals, read-only auditor access, decision trails, replay-safe run evidence, operational health, rate-limit status, and safe alert routing. The current model is AI-led operations with explicit controls around money, journals, statements, and external communications.

**"What about GDPR / data privacy for our clients?"**
> Aethos tenant access, source-document permissions, and operational telemetry
> redaction are separate controls. The current build does not prove universal
> pre-model masking of names, bank numbers, tax IDs, extracted document text, or
> scanned images. Use only fictional or contractually approved data in this
> demo, configure an approved model provider and retention policy, and review
> the extracted proposal before posting it. Do not promise field-level masking
> unless production evidence for that exact input path exists.

**"We do payroll — can this handle PAYE, RTI?"**
> Payroll in v1 handles the billing and time-tracking side — what you charge clients for payroll services, not the payroll bureau processing itself. The payroll processing integrations (Sage, Brightpay, Xero Payroll) are on the roadmap.

---

## Appendix: Sample Files for Demo

Generated demo PDFs are in `docs/demo-assets/`. Regenerate them with:

```bash
python3 scripts/generate_demo_assets.py
```

- `nexus_engagement_letter.pdf` — Multi-page engagement letter with mixed billing terms
- `brightwater_subcontractor_invoice.pdf` — Forster & Reid invoice, UK VAT number
- `alderton_sgd_dividend_notice.pdf` — Singapore dividend income statement in SGD
- `thornton_cosec_instruction.pdf` — New director appointment instruction letter

> **Tip for demos**: Keep the mode-0600 credential manifest ready, but perform role changes by explicit sign-out/sign-in in one continuous recorded browser context per tenant. This preserves a single auditable recording while showing that the manager operates, the approver decides manager-threshold reviews, the controller handles accounting controls, the auditor inspects evidence only, and Marcus keeps owner-only settings and approvals.
