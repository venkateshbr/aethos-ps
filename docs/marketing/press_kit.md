# Aethos — Press Kit

> Owner: Netra (Issue #76)
> Last updated: 2026-05-23

---

## Company Description

Aethos is an agent-first ERP for professional services firms — consulting practices, dev shops, advisory firms, and accounting practices. The product replaces the chain of manual steps between finishing a piece of client work and receiving payment: engagement letters extracted by AI, invoices drafted from approved time logs, Stripe Payment Links on every invoice, vendor bills extracted and posted with one-click approval, and a GAAP-compliant double-entry general ledger keeping score throughout. Every AI-proposed action lands in a Human-in-the-Loop review queue before it touches the books; agents earn higher autonomy over time as they demonstrate accuracy. Aethos launched in public beta in 2026 across five markets — United States, United Kingdom, Singapore, India, and Australia — with pricing in five local currencies and local tax rates pre-seeded at signup.

---

## Product Facts

| Fact | Detail |
|---|---|
| Product name | Aethos for Professional Services |
| Category | Agent-first ERP / Professional Services |
| Launch markets | US, UK, Singapore, India, Australia |
| Billing models supported | 5: time and materials, fixed fee, milestone, retainer, capped T&M |
| AI agents | 13 specialist agents (engagement extraction, invoice drafting, billing runs, expense extraction, collections, bill pay, accounting guardian, and others) |
| Accounting standard | GAAP double-entry general ledger; posted entries immutable; corrections via reversing entries |
| Tax support | Pre-seeded local rates at signup: UK VAT (20/5/0%), SG GST (9%), AU GST (10/0%), IN GST (0/5/12/18/28%); US admin-enabled per-state codes |
| Currencies | USD, GBP, SGD, INR, AUD (per-tenant base currency + per-invoice override) |
| Pricing | Starter: $29/£25/S$39/₹2,499/A$45 per month. Growth: $79/£69/S$109/₹6,999/A$119 per month. Pro: $199/£179/S$279/₹17,999/A$299 per month. |
| Trial | 14-day free trial with card capture. No permanent free tier. |
| Payment processing | Stripe Payment Links on invoices; Stripe Connect Standard for firm payouts; Stripe Tax on SaaS subscriptions |
| AP bill payments | NACHA (US) and universal CSV at launch; native BACS/ABA/GIRO/NEFT in v1.1 |
| Tech stack | Angular 19, FastAPI, PydanticAI, Supabase (PostgreSQL with row-level security), Anthropic Claude |
| Status | Public beta |

---

## Founder Bio

**[Founder Name]**, Founder and CEO

[Placeholder — replace with approved bio. Suggested elements: professional background in professional services or fintech, years running or advising PS firms, the specific pain point that motivated Aethos, location. Keep to 75 words or fewer for standard press use; 150 words for longer profiles.]

Press contact for founder interview requests: [founder@aethos.app]

---

## Key Differentiators

### vs. FreshBooks

FreshBooks is invoicing software with a time tracker bolted on. It handles straightforward T&M billing well but has no concept of an engagement letter, no milestone or retainer billing model, no HITL approval flow for AI-proposed entries, and no double-entry general ledger. FreshBooks is for freelancers who need to send invoices; Aethos is for firms that need to run their entire financial operation — from document extraction to GL close — without an accountant doing the data entry.

### vs. Xero

Xero is a capable accounting platform that requires a human to enter every transaction. It integrates with time-tracking tools like Harvest, but the integration still requires manual review and data movement. Xero has no AI extraction layer, no engagement or project management layer, and no HITL approval concept. Aethos is not a better Xero — it is a different product for a different workflow: one where the AI does the data entry and the human approves, rather than the human doing the data entry with no assistance.

### vs. QuickBooks

QuickBooks dominates the US SME accounting market and handles bookkeeping well. It is not designed for professional services billing — engagement management, project-based time tracking, milestone invoicing, and retainer billing all require workarounds or third-party integrations. QuickBooks has no AI extraction for incoming documents and no agent-first workflow. For a PS firm using QuickBooks, the typical setup is QuickBooks + Harvest + a time-to-invoice manual workflow. Aethos replaces that stack with a single product.

### What is genuinely different

Three things distinguish Aethos from every accounting or billing tool on the market:

1. **Agent-first workflow**: The primary interaction is chat and document drop, not form entry. AI agents handle data extraction and proposal; humans handle decisions. This is not AI as a feature — it is the core interaction model.

2. **HITL inbox as a trust mechanism**: Every agent-proposed change lands in a review queue with a confidence score before it touches the books. Users can promote agents to higher autonomy levels as they earn trust. This makes AI involvement auditable and reversible — a requirement for anything touching a firm's financial records.

3. **Full PS accounting in one product**: Engagements, projects, time, expenses, invoicing, AR, AP, and a real GL — not connected via integration but built as a coherent system. A transaction entered in chat results in a correctly posted journal entry without human intervention in the GL.

---

## Screenshots to Capture (5 recommended)

1. **Copilot — document drop and extraction card**
   Chat interface with a PDF engagement letter dropped in. The AI extraction card appears mid-stream showing: client name, billing model (Retainer, $8,500/mo), contract term, rate card, and confidence score (92%). Three action buttons visible: Approve, Edit, Reject.
   Caption: Drop a document. Agent extracts. You approve.

2. **HITL Inbox — review queue**
   The inbox showing three pending tasks with confidence chips (green for high confidence, amber for medium), priority labels, and keyboard navigation hints (J/K). One card expanded showing a proposed invoice draft with line items.
   Caption: Every agent proposal in one queue, with confidence scores.

3. **Invoice list with Stripe Payment Links**
   Invoice list with status badges (Draft, Sent, Overdue, Paid) and a Stripe Payment Link column. One row expanded showing the payment link URL, amount due, due date, and "Send reminder" action.
   Caption: Payment Links on every invoice. Journals post on receipt.

4. **Billing run — monthly pre-bill proposal**
   The billing run wizard showing a proposed batch of invoices across multiple engagements, with billable hours, expenses, and total per client. A summary line at the bottom shows the total batch value. Approve All and Review Individual buttons visible.
   Caption: One command to bill every active engagement.

5. **Chart of Accounts + Journal Entry**
   The accounts screen showing a standard PS chart of accounts (Revenue, AR, AP, Expenses), with one journal entry expanded showing the debit and credit lines, source (invoice send), and posted status.
   Caption: Real double-entry. Every transaction, balanced.

---

## Press Contact

**Media and analyst inquiries:**
[press@aethos.app]
Response SLA: 48 hours

**Founder interview requests:**
[founder@aethos.app]
Available for written Q&A, podcast, and video interviews. 30-minute slots available on request.

**Design partner case study requests:**
Three design-partner firms are in active use. Case study availability depends on each firm's consent. Contact us at [press@aethos.app] to request an introduction.

---

## Brand Assets

Logo files, colour tokens, and social card templates are stored in `frontend/src/assets/brand/`. For press use, request the brand pack at [press@aethos.app]. Do not use screenshots of the app as a substitute for the provided brand assets.

Primary accent: Emerald-500 (`#10b981`) on Slate-900 (`#0f172a`).
Wordmark: "Aethos" in Inter Bold. Sub-mark: rotated square micro-mark in emerald.
Dark backgrounds only — the lockup is not approved for white or light backgrounds.
