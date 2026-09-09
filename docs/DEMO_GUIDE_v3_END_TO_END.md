# Aethos — End-to-End Client Demo Guide v3

> **Firm**: Meridian Advisory Group LLP (fictional) · **Base currency**: GBP · **Market**: UK
> **Guide version**: 3.0 · 2026-09-09 · Written from the
> [2026-09-09 launch-readiness review](qa/launch-readiness-review-2026-09-09.md);
> every step is backed by code that exists on `main` @ `481013b` / production `f170119`.
> Supersedes [`DEMO_GUIDE_v2.md`](DEMO_GUIDE_v2.md) as the presenter script.
> v2 remains the reference for talk-track narrative and objection handlers.

## How to use this guide

Four principles:

1. **Agentic path first, UI fallback second.** Each business step starts in Aethos Nous or with a document drop. The module screen is the fallback and the place where evidence is shown.
2. **Three-part evidence on every AI step.** (1) the Nous intent — prompt and proposed action; (2) the Inbox boundary — the human approval; (3) the evidence — record, report, journal, Agent Run Ledger.
3. **Honest boundaries inline.** Every part has a "Do not say" line. A presenter who follows it never over-claims.
4. **Deterministic where it matters.** Client names Nexus, Brightwater, Forster & Reid, Alderton, Thornton are known to the Nous semantic router, so those prompts answer the same way every time. Other names go to the model runtime and vary.

Runtime: about 90 minutes for the full guide; 25 minutes for the short path in §9.

Routes referenced: authenticated modules are under `/app/*`; public routes are `/`, `/signup`, `/login`, `/p/:token`; the employee timesheet portal is `https://timesheet.aethos.ishirock.tech`.

---

## 0. Pre-flight (presenter, the day before)

| Check | How | Pass condition |
| --- | --- | --- |
| Build is live | GitHub Actions → *Deploy Hostinger Production* → last run green; `/health/ready` returns `status: ready` | `build_sha` equals `main` |
| Stripe is in test mode | Settings → Plan & Billing badge; card step shows "Test mode" | Say "sandbox" out loud when you reach the card step |
| Hermes is up | Settings → Operational Health shows runtime `hermes_agent`; send one read prompt to Nous and check Settings → Agent Runs for a `nous_hermes_runtime` entry | If it degraded to Basic the demo still works; nothing user-visible changes |
| Email provider | `RESEND_API_KEY` configured | Only needed for the collections send in §5 D8; otherwise reject the email card with a reason |
| Demo assets | `docs/demo-assets/nexus_engagement_letter.pdf`, `brightwater_subcontractor_invoice.pdf`, `alderton_sgd_dividend_notice.pdf`, `thornton_cosec_instruction.pdf` on the presenter laptop | Keep the filenames unchanged; the filenames drive document classification |
| Disposable tenant | Either sign up live (§1) or reset an existing `Meridian Demo …` tenant: `cd backend && uv run python -m scripts.seed_demo_v2 --tenant-id <uuid> --reset --require-tenant-name 'Meridian Demo'` | Never Sterling Bridge Advisory Group |
| Credentials | Local `demo_credentials.json`, file mode 0600 | Never in slides, screenshots, or tickets |
| Browser | One recorded browser context per tenant; switch roles by explicit sign-out and sign-in | Preserves a single auditable recording |

---

## 1. Part A — New tenant signup (5 min, UI)

1. Open `https://aethos.ishirock.tech/` and click **Get started** (`/signup`).
2. **Step 1 · Account**: firm name `Meridian Demo <date>`, owner email (a real mailbox you control; no verification email is sent, but you will sign in with it), password twice, country **United Kingdom**. The country sets base currency GBP and the GB market profile.
   *Behind the scenes*: the backend creates the auth user (pre-confirmed), the tenant in `provisioning`, the owner membership with the `tenant_owner` security role, a Stripe customer and a SetupIntent; the browser then signs in.
3. **Step 2 · Plan**: choose **Growth**, monthly. *Say*: "Pricing is Stripe-driven — three tiers, five currencies."
   *Boundary*: the tiles show currency and price reference, not amounts; the selected tier is not yet written back to the tenant.
4. **Step 3 · Card**: Stripe Elements. Use `4242 4242 4242 4242`, any future expiry and CVC → **Start trial**. The backend attaches the payment method and creates a 14-day trial subscription; the tenant becomes `active`; you land on `/app/copilot` with the trial badge top right.
5. **What was provisioned automatically** (show briefly in Settings): 25 GL accounts (Bank 1100, AR 1200, AP 2000, Deferred Revenue 2200, Sales Tax 2300, Retained Earnings 3000, Revenue 4000–4003, Expenses 5000–5300, FX 7900 / 7910), 17 service-catalogue rows (ACC, TAX, COS, PAY), 13 global tax codes (GB VAT 20 / 5 / 0 and the other four markets), 22 security roles.

**Do not say**: "no credit card required" (the landing copy is wrong and is being corrected), "we verified your email", "you can reset your password from the login page".

---

## 2. Part B — Org users and roles (8 min, UI)

1. **Settings → Security Roles**. Show the 22-role catalogue and open one role to show duties → privileges. Roles: Tenant Owner, Tenant Admin, CFO, Finance Controller, Close Manager, AI Ops Admin, Finance Ops Manager, GL Accountant, Procurement Manager, AP Manager, AR Manager, Finance Approver, Engagement Manager, Resource Manager, AP Clerk, Billing Specialist, Collections Specialist, Finance Operator, Buyer / Requester, Auditor, Executive Viewer, Timesheet Employee. Optional: create a tenant role "Demo Billing Reviewer" from seeded duties and note it shows as tenant-created.
2. **Settings → Tenant Users → Invite**. Fields: email, display name, role, password (leave blank to auto-generate). Create four:

   | User | Role |
   | --- | --- |
   | `finops@…` | Finance Ops Manager |
   | `approver@…` | Finance Approver |
   | `controller@…` | Finance Controller |
   | `auditor@…` | Auditor |

   Each response shows a **set-password link and a temporary password once**. Copy both into the credentials file. *Say*: "Invitation email is on the roadmap; today the admin hands the link over."
3. **People → Add employee** three times, with bill and cost rates, practice area and utilisation target:

   | Employee | Title | Bill / cost (GBP per hour) |
   | --- | --- | --- |
   | Marcus Chen | Managing Partner | 350 / 180 |
   | Sarah Williams | Tax Director | 280 / 145 |
   | Alice Chen | Senior Consultant | 250 / 120 |

   Then click **Invite to timesheet portal** on Alice. The dialog shows a set-password link and temporary password. This also links the employee to a login, which is what lets chat time-logging resolve to Alice later.
4. Sign out, sign in as `finops@…`. The app forces you to `/app/profile` to change the initial password before anything else. Back in **Settings → Tenant Users**, open the audit events: `invited`, role assigned.
5. Timesheet portal: open `https://timesheet.aethos.ishirock.tech/login` as Alice → forced `/change-password` → `/timesheet`.

**Do not say**: "platform administrator", "self-service password reset", "the user got an email".

---

## 3. Part C — Setup data (10 min, UI plus the first agentic step)

Nothing in this section is seeded per tenant, so billing does not work until it is done.

1. **Settings → Tax Rates**: confirm `VAT-20` is active (global system rate) or add a tenant rate. **Settings → Services**: set default rates on ACC-001 Monthly management accounts (8,500 per month), ACC-003 Advisory hour (350), TAX-001.
2. **Settings → Rate Cards → New**: "Meridian 2026 GBP" with Partner 350, Director 280, Senior 250. *(Optional — the engagement-letter approval in Part D materialises a rate card from the letter's rate hints.)*
3. **Settings → Collections Policy**: gentle day 1, firm day 8, final day 31, cooldown 7 days, maximum 3 reminders. **Settings → Approval Controls**: manual-journal threshold 10,000; money-out owner threshold 50,000; bill-pay approver Admin. Show the **Finance role personas** panel.
4. **Settings → Agent Autonomy → AI Inference Settings**: runtime *Advanced (Hermes)*, semantic router on, minimum confidence 0.72, model chain Gemma-4 free → OpenRouter free → Claude Haiku 4.5. **Finance Ops Manager Schedule**: every business morning 07:00 UTC, escalate stale approvals after 24 hours.
5. **Contacts → New contact**: Brightwater Manufacturing Ltd (customer, GBP); Thornton Tech Solutions Ltd (customer, **USD**); Forster & Reid Ltd (vendor). Nexus and Alderton arrive through documents.
6. **First agentic step**: run Part D step D1 now so the Nexus client, engagement, rate card and project exist for the rest of the demo.

**Fast alternative**: seed the tenant with `seed_demo_v2` (6 contacts, 5 employees, 2 rate cards, 10 engagements, 9 projects, June time and expense, 3 invoices, 2 bills, close tasks, a May period lock and 4 Inbox tasks). Use it when the client wants a populated system in 25 minutes.

---

## 4. Part D — Order-to-Cash, agentic (20 min)

### D1 · Engagement letter → client, engagement, billing terms, rate card, project

Nous: attach `nexus_engagement_letter.pdf`, then send:

> Review this engagement letter, create the client, engagement, billing terms, rate card, and first project. Send anything risky to Inbox.

- **Intent**: Documents shows the file move `uploaded → extracting → extracted`.
- **Boundary**: Inbox card `create_engagement_draft` with a confidence chip, the mixed billing model (fixed 42,000 in two milestones + retainer 8,500 per month + advisory 350 per hour), rate hints, and a link to the source PDF. Click **Approve**.
- **Evidence**: Engagements shows *Nexus Capital Partners LP* with a linked rate card; Projects shows the first project; Contacts shows Nexus as a customer; Settings → Agent Runs shows the run; the engagement's decision timeline shows who approved and when.

*Honesty*: a filename containing `nexus` and `engagement` returns a deterministic fixture at confidence 1.0 without calling the model. Rename the file (for example `nx_letter_2026.pdf`) to show the live model path with a real confidence score.

### D2 · Structure readback

Nous:

> Show me the Nexus Capital Partners engagement structure. List the active projects, billing model for each workstream, and anything missing before billing.

Say this readback is guidance-level today; then open the engagement detail screen to show projects, billing terms and the linked rate card.

### D3 · Time by chat, then approval

Sign in as Alice (or any user linked to an employee). Nous:

> Log 4.5 hours on the Nexus CFO Advisory project for today - board pack review and cash flow modelling

- **Intent**: deterministic route; Nous shows "Secure action prepared".
- **Boundary**: Inbox `copilot_log_time_entry` → Approve.
- **Evidence**: Time list shows 4.5 billable hours for Alice.

Repeat with *"Log 2 hours on Nexus CFO Advisory for yesterday - internal planning, non-billable"*. In the portal, submit the week; as Finance Ops Manager open **Approvals** and approve. Entries are now billable.

### D4 · Expense (UI path)

Expenses → **New expense**: project Nexus CFO Advisory, 185.50, travel, billable, attach the receipt image.

*Boundary note*: do not approve a receipt-extracted expense from Inbox. Without a project on the extracted draft the approval currently reports success but creates nothing. This is tracked in the implementation plan (B3).

### D5 · Invoice draft by chat

Nous:

> Draft an invoice for the Nexus Capital Partners engagement for June 2026. Use approved billable time, billable expenses, and billing terms. Send the draft to Inbox before creating an invoice.

- **Intent**: the model runtime calls the `draft_invoice` tool (the deterministic invoice drafter computes lines for the engagement's billing model).
- **Boundary**: Inbox `copilot_draft_invoice` with lines — retainer, advisory hours × rate, expenses, VAT 20 % → Approve.
- **Evidence**: Invoices shows the new draft.

UI fallback: Engagements → Nexus → **Draft invoice**.

### D6 · Approve, send, public page, payment

1. Invoice detail → **Approve**. The guardian posts DR 1200 AR / CR 4000 Revenue / CR 2300 VAT. Show **Journal Entries**.
2. **Send**. A Stripe Payment Link is created and the status becomes `sent`. Open `/p/<token>` in a private window: customer-safe page with lines, total, due date and a **Pay** button. *Say*: "Email and PDF delivery is the next release; today you share the link."
3. Optional: pay with `4242` in Stripe Checkout. The webhook records the payment and posts DR 1100 Bank / CR 1200 AR; Payments shows the receipt; AR Aging drops. Fallback: Invoice → **Record payment**.

### D7 · Multi-currency

Engagements → Thornton (USD retainer 4,500 per month) → draft invoice → approve → record payment of USD 4,500. Payments shows the USD amount, the GBP `base_amount` and the `fx_rate_id`. Settings → **Historical FX provenance** shows the exact rate row used. If the rate moved between invoice and payment, Journal Entries shows the realised difference in 7900.

### D8 · Collections

Read first:

> Which customers need collections follow-up and what should we send next? Show customer balances, invoice numbers, due dates, aging buckets, payment status, reminder history, collections policy stage, blockers, and next action. Do not draft or send anything yet.

This is a live read pack. Then the controlled write:

> Draft collections reminders for invoices more than 30 days overdue. Create customer-specific reminder copy and route every email to Inbox before sending.

- **Boundary**: one `send_email` card per invoice with tone set by the policy stage. Approve one (sends through Resend); reject another with a reason (nothing is sent).

### D9 · Reports

AR Aging (ties to account 1200), WIP, Utilization, Project P&L, Revenue by engagement.

**Do not say**: "the AI emails the invoice", "switch the report to USD", "void the invoice" (not implemented), "create the engagement by typing a prompt" (no router intent yet; a document drop is the path).

---

## 5. Part E — Procure-to-Pay, agentic (12 min)

### E1 · Vendor invoice intake

Nous: attach `brightwater_subcontractor_invoice.pdf`, then send:

> Process this vendor invoice for Brightwater. Match it to the right vendor and project, flag duplicate risk, code it to the right account, compare any PO or service-order evidence, and send exceptions to Inbox.

- **Boundary**: Inbox `create_bill_draft` shows vendor match (Forster & Reid Ltd), GL suggestion 5100 with confidence, the **"No approved PO"** exception, and a clear duplicate guard. Use **Approve with edits**: confirm the vendor and enter a review reason.
- **Evidence**: Bills shows the new bill in draft with `vendor_invoice_review` evidence and the source document link.

Upload the same file a second time to show the duplicate guard blocking one-click approval.

### E2 · Bill approval

Bills → open the bill → **Approve** as AP Manager. The guardian posts DR 5100 Subcontractors / CR 2000 AP. The bill detail shows the decision timeline.

### E3 · Payment-risk reads

> Which vendor bills are due soon, which are blocked, and what evidence supports payment? … Do not create a payment batch yet.

Say this list is guidance-level today (the live version is being wired). Then the single-bill drilldown, which is live:

> Review bill BILL-<number>. Show due date, amount, vendor invoice number, coding status, source document, duplicate signals, PO/service-order match, approval state, payment readiness, existing batch status, and recommended next action.

### E4 · Bill-pay run

> Prepare this week's bill-pay run. Prioritize due and overdue approved bills, exclude anything disputed, explain the rationale, and send the payment batch to Inbox.

- **Intent**: the model runtime calls `propose_bill_payment_batch` (deterministic, due-date and discount aware).
- **Boundary**: Inbox `create_bill_payment_batch` requires Admin (money out) → Approve.
- **Evidence**: **Billing Runs / Pay Bills** wizard: *Select Bills* → *Batch Details* → **Export** (Universal CSV or NACHA template; the batch is flagged as a template until you **Confirm bank details** were completed out of band) → **Mark sent** → **Settle**. Settlement posts DR 2000 AP / CR 1100 Bank; AP Aging drops; the batch has its own approval timeline.

**Do not say**: "partial payments", "we take the early-pay discount automatically", "we send the file to the bank", "mixed-currency batches".

---

## 6. Part F — Record-to-Report and close, agentic (15 min)

### F1 · Manual journal by prompt

Optionally attach `alderton_sgd_dividend_notice.pdf`, then send:

> Prepare an SGD 18,000 dividend income journal for Alderton Trust for June 2026. Show the GBP base-currency impact, FX rate provenance, required approval role, and route it to Inbox before posting.

- **Intent**: deterministic; Nous shows the SGD lines, GBP base amounts, the FX row used, the period-lock status and the required approver.
- **Boundary**: Inbox `draft_journal`. Sign in as the **Controller** (not the submitter) and approve; same-user approval is denied and audit-visible.
- **Evidence**: Journal Entries shows the posted entry with SGD and GBP amounts; Trial Balance remains balanced.

### F2 · Close preparation and proposals

> Prepare month-end close for June 2026. Summarize readiness blockers, missing approvals, unposted journals, open AR/AP, and proposed close tasks. Route the close preparation to Inbox before creating close tasks.

- **Boundary**: Inbox `copilot_prepare_month_end_close` → Approve → close tasks are bootstrapped.
- **Evidence**: Journal Entries → close package for June: AR and AP tie-out to control accounts, WIP labelled as a current-rate estimate, GL readiness, override reasons.

For the accrual proposals use the Accounting screen actions (propose WIP accrual, expense accrual, deferred revenue release, milestone recognition, prepaid amortisation, recurring journals). Each creates a `draft_journal` card; approving posts the journal through the guardian.

### F3 · Period lock

Journal Entries → **Lock June 2026**. Try a manual journal dated 15 June → rejected with the period-lock message. Reopen as Owner, or post a July correction. Nous:

> Can I post a correcting journal dated 15 June 2026 now that June is locked? Explain the safe options and do not post anything.

(guidance answer).

### F4 · Statements and management pack

Reports: Trial Balance, Balance Sheet, Income Statement, Cash Flow, Retained Earnings, Statutory Pack. Set From April to June to show the range control. Nous:

> Give me the June 2026 month-end management pack. Explain the major variances versus May 2026, show revenue, expenses, project margin, utilization, AR/AP movement, journals, close task blockers, draft journals, and remaining close blockers. Do not post journals or lock the period.

This is a live read pack; follow with the drilldown prompt for blockers, owners and next actions.

### F5 · Year-end close

> Prepare year-end close for fiscal year 2026. Check retained earnings setup, posted P&L activity, locked periods, duplicate close risk, and current-vs-prior year statement movement. Route the retained-earnings posting to Inbox for approval before any journal is posted.

Approve as Owner → a `YE-2026` journal posts; a second attempt is blocked.

### F6 · Reversal

Journal Entries → reverse the posted manual journal → a new `manual_reversal` entry with flipped lines; the original is unchanged.

**Do not say**: "the AI closes the books", "reports in transaction currency", "WIP is exact" (it is a current-rate estimate).

---

## 7. Part G — AI Finance Ops Manager (10 min) — the showpiece

### G1 · Daily check

> Run today's finance ops check for June 2026. Tell me what needs billing, payment, collections, close, and review. Separate read-only findings from actions that need Inbox approval.

### G2 · Reviewed work plan and dispatch

> Create the next recommended finance ops work items for June 2026. Create at most five manager-reviewed work items. Route the action plan to Inbox for review. Do not approve invoices, payments, journals, or emails directly.

- **Boundary**: Inbox parent action plan → Approve → child **Plan Items** appear.
- **Dispatch**: approve one item (for example collections). It dispatches the specialist tool through the policy, which creates its own downstream Inbox card. Money, journals and emails still need their own approvals.
- **Evidence**: Settings → Agent Runs and Workflow Runs show the chain.

### G3 · Scheduled manager

Settings → Agent Autonomy → Finance Ops Manager Schedule: cadence, next run, escalation window. Workflow Runs shows the last scheduled run; Inbox shows the scheduled plan and any escalation notices. The Nous "control room" prompt is guidance-level today; use the Settings panels for figures.

### G4 · Governance controls

Settings → Agent Autonomy → disable `collections_agent` → send the reminder prompt again → blocked with a reason → re-enable. Explain the circuit breaker: three tool failures open the circuit for 15 minutes.

**Do not say**: "the agents auto-apply", "the AI has been promoted to L3", "it learns from your corrections" (capture exists; the learning loop is roadmap).

---

## 8. Part H — Controls, audit, operations (8 min)

- Sign in as **Finance Approver**: approve a manager-threshold Inbox item; attempt to create a bill → denied.
- Sign in as **Auditor**: reports and decision trails are readable; mutation controls are disabled or denied.
- Sign in as **Controller**: attempt to approve your own high-value manual journal → denied and recorded.
- Settings → Approval Controls and Finance role personas. Nous *"What am I allowed to approve…"* is guidance-level today.
- Settings → Agent Runs (open a run, use Validate Replay on a read step), Workflow Runs, Operational Health (runtime, limiter backend, failure counters, alert routing), Financial events ledger and export.
- Documents: lineage from upload → extraction → Inbox decision → business record.

**Do not say**: "platform administrator", "names and addresses are always redacted" (only with the optional NER model), "scanned images are redacted".

---

## 9. Short path (25 minutes)

| Minute | Step |
| --- | --- |
| 0–3 | §1 signup |
| 3–8 | §4 D1 engagement letter drop and approve |
| 8–10 | §4 D3 time by chat |
| 10–15 | §4 D5–D6 invoice draft, approve, send, public page |
| 15–19 | §5 E1 vendor invoice drop and approve with edits |
| 19–23 | §7 G2 action plan and dispatch |
| 23–25 | §6 F4 statements and management pack |

---

## 10. Presenter honesty card (one slide)

**Shipped**: agent-first intake for engagement letters and vendor invoices; chat actions with a mandatory Inbox approval on every write; seven billing models; GL with an accounting guardian and atomic posting; multi-currency with FX provenance; a 22-role security catalogue; close package and period locks; 19 report tabs; Hermes runtime with automatic fallback; agent run ledger and workflow runs.

**Roadmap (say it before they ask)**: invoice email and PDF (#516); invoice void and credit notes (#517); expense approval and GL posting (#518); onboarding checklist (#519); Billing Runs screen (#515); password reset and invite email; Stripe Connect live (#95); L3 autonomy promotion (#496 / #497); mobile layout (#510); CSV import (#521); data export and erasure (#522); notifications (#524).

---

## 11. Reset after the demo

```bash
cd backend
uv run python -m scripts.seed_demo_v2 \
  --tenant-id '<disposable-tenant-uuid>' \
  --reset \
  --require-tenant-name 'Meridian Demo'
```

The command refuses to run without an exact tenant-name match. Never run it against Sterling Bridge or a customer tenant. Rotate the demo user passwords afterwards and update the local credentials file.
