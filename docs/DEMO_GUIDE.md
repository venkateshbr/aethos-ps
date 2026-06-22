# Aethos — Demo Guide

> **Version**: 1.0 · **Date**: 2026-06-20
> **Purpose**: Walk a prospect through the Aethos PS platform in ~35 minutes
> **Audience**: Firm owners, senior accountants, PS operations leads

---

## Before You Start

### Setup Checklist
- [ ] Backend running: `cd backend && uv run uvicorn app.main:app --reload --port 8011`
- [ ] Frontend running: `cd frontend && ng serve --port 4201`
- [ ] Demo data seeded: `cd backend && uv run python -m scripts.seed_demo --tenant-id <your-demo-tenant-id> --reset`
- [ ] Browser open at `http://localhost:4201`
- [ ] Dark theme visible (Aethos dark slate — should be default)
- [ ] Sample PDFs ready: `docs/demo-assets/sample-engagement-letter.pdf` and `docs/demo-assets/sample-vendor-invoice.pdf`

### Demo Tenant State (after seed script)
- **Contacts**: Acme Corp (customer), Blackwood Consulting (customer, GBP), CloudPeak Systems (both), Apex Staffing (vendor)
- **Engagements**: Acme — Digital Transformation (T&M, USD), Blackwood — Annual Retainer (GBP £5k/mo)
- **Invoices**: INV-TEST-001 ($8,500 paid), INV-TEST-002 (£5,000 sent)
- **Bills**: CloudPeak draft (in Inbox), Apex approved (in AP)
- **Reports**: All 6 tabs have data

---

## Scenario A — Engagement to Cash (10 min)

> **Story**: "A new client sends you their engagement letter. Show me how Aethos handles everything from that document to a paid invoice — with minimal manual entry."

### A1 — Drop the Engagement Letter (2 min)

1. Open **Copilot** (home screen — `/copilot`)
2. Click the **paperclip/upload icon** in the chat bar
3. Drop `sample-engagement-letter.pdf`
4. Watch the streaming response: *"Extracting engagement details..."* → **confidence chip** appears
5. An **EngagementDraftCard** appears in chat:
   - Client name, billing arrangement, currency, total value, start/end dates
   - Confidence score (e.g. 94%) in a colored chip
   - **Approve / Edit / Reject** buttons

**Talking point**: *"The AI read the PDF, pulled out the key commercial terms, and is asking for your approval before creating anything. You can edit any field before approving."*

### A2 — Approve from Inbox (1 min)

1. Navigate to **Inbox** (`/inbox`)
2. Show the HITL card for the extracted engagement
3. Press **J/K** to navigate, **A** to approve (keyboard-first design)
4. Card shows: source document link, confidence chip, all extracted fields
5. Approve → toast: *"Engagement created"*

**Talking point**: *"Every AI action lands here first. Nothing gets created without your say-so — unless you've specifically promoted an agent to auto-execute."*

### A3 — Log Time via Chat (2 min)

1. Go back to **Copilot**
2. Type: *"Log 4 hours on the Acme Digital Transformation project for today, billable"*
3. Watch the tool call execute → *"Time entry logged — 4 hrs, Acme Phase 1, $800 billable"*
4. Navigate to **Time Entries** (`/time`) to confirm it's there

**Talking point**: *"Chat is the primary UI. Your consultants don't need to learn another form — they log time the way they'd type a Slack message."*

### A4 — Run Billing (3 min)

1. Go to **Billing Runs** (`/billing-runs`)
2. The seed data has pre-seeded the Acme engagement with time entries
3. Select the engagement → review proposed invoice (T&M lines, hours × rate)
4. Click **Confirm** → Invoice INV-TEST-001 is drafted
5. Navigate to **Invoices** (`/invoices`) → open INV-TEST-001
6. Click **Approve** → then **Send** → Stripe Payment Link is generated
7. Show the **public invoice URL** (`/p/<token>`) — client-facing, branded, Stripe Pay button

**Talking point**: *"The invoice drafter pulled every billable time entry, calculated the amount, applied tax, and generated a Stripe payment link. Your client clicks Pay — done."*

### A5 — Show AR Aging (1 min)

1. Go to **Reports** → **AR Aging** tab
2. Point out the INV-TEST-002 (Blackwood, GBP) in the 0-30 bucket
3. After payment is recorded on INV-TEST-001, AR clears

---

## Scenario B — Procure to Pay (8 min)

> **Story**: "You receive a vendor invoice from a cloud provider. Show me how the AP process works — with AI handling extraction and the platform managing payment."

### B1 — Drop Vendor Invoice (2 min)

1. **Copilot** → upload icon → drop `sample-vendor-invoice.pdf`
2. Streaming: *"Extracting vendor invoice..."*
3. **BillExtractedCard** appears: vendor name, invoice#, line items, amount, due date, **confidence chip**
4. Also flags duplicate detection: *"No duplicate found for this invoice number"*

**Talking point**: *"Same pattern as the engagement letter — AI extracts, confidence score shows how sure it is, you approve or edit. If it's seen the same invoice# before, it flags it as a potential duplicate."*

### B2 — Approve the Bill (1 min)

1. Go to **Inbox** → see the CloudPeak bill card
2. Click **Approve** → bill is created in AP, journal auto-posts: `DR Expense / CR Accounts Payable`
3. Navigate to **Bills** (`/bills`) → CloudPeak bill shows as **Approved**

**Talking point**: *"The moment you approve, the accounting entry is posted automatically — debit expense, credit AP. No separate journal entry step."*

### B3 — Pay Bills (3 min)

1. Go to **Billing Runs** → **Pay Bills** tab
2. Seed data shows Apex Staffing bill ($3,600 approved, due in 7 days)
3. **bill_pay_agent** has already proposed this batch (see it pre-selected)
4. Step 1: Select bills (show select-all, total amount)
5. Step 2: Review — bank account label, pay date, format (NACHA)
6. Step 3: Confirm → **Download NACHA file** button
7. Download the file → show the structured payment instruction

**Talking point**: *"The agent looks at what's due in the next 7 days and proposes the batch. High-value bills over $50k require an extra confirmation. You download the NACHA file and upload it to your bank — done."*

### B4 — Show AP Aging (1 min)

1. **Reports** → **AP Aging** tab
2. CloudPeak and Apex visible in the aging buckets
3. After batch is marked sent, Apex clears

---

## Scenario C — Record to Report (8 min)

> **Story**: "Walk me through how the books stay accurate automatically — and how you close a period."

### C1 — Auto-Posted Journals (3 min)

1. Navigate to **Accounting** → **Journal Entries**
2. Show the journal entries auto-posted from Scenario A and B:
   - `invoice_sent` → DR Accounts Receivable / CR Revenue
   - `payment_received` → DR Bank / CR Accounts Receivable
   - `bill_approved` → DR Expense / CR Accounts Payable
   - `bill_paid` (when batch is settled) → DR Accounts Payable / CR Bank
3. Click into one entry → show the balanced lines (DR = CR)

**Talking point**: *"Every financial event posts a balanced journal entry automatically — triggered by the database, not application code. The accounting guardian validates every entry before it's posted. You can't have an unbalanced journal in this system."*

### C2 — Trial Balance (1 min)

1. **Reports** → **Trial Balance** tab
2. Show all accounts with DR/CR totals
3. Green indicator: *"✓ Balanced (DR = CR)"*

### C3 — Period Lock (2 min)

1. **Accounting** → **Period Locks**
2. Lock the previous month (e.g. May 2026)
3. Try to post a backdated entry → show 422 error: *"Period 2026-05 is locked"*
4. Show reopen button (owner only)

**Talking point**: *"Period locks prevent backdating — once you close a month, nothing can post into it unless you explicitly reopen it as the owner."*

### C4 — Reports Overview (2 min)

1. **Reports** → quickly tab through:
   - **AR Aging**: color-coded buckets, total outstanding
   - **AP Aging**: what we owe
   - **Project P&L**: revenue vs cost, gross margin per project
   - **Utilization**: billable % per person
   - **WIP**: unbilled effort in dollars

**Talking point**: *"Six management reports, all real-time from the GL. No separate reporting tool — everything is in the same system where the transactions happened."*

---

## Scenario D — Agentic Intelligence (5 min)

> **Story**: "Show me how the AI is working in the background, not just when I ask it to."

### D1 — Copilot Financial Q&A (2 min)

1. **Copilot** → type: *"Show me WIP across all active projects"*
2. Watch tool call: `get_wip()` → structured result in chat
3. Type: *"Which clients owe us money past 60 days?"*
4. Watch: `get_ar_aging()` → lists overdue invoices with client names and amounts

**Talking point**: *"You can ask financial questions in plain English. The agent calls the right report, pulls live data, and gives you a direct answer — not a link to a dashboard."*

### D2 — Inbox: Autonomy Promotion (2 min)

1. **Inbox** → show the autonomy promotion card: *"Promote Expense Extractor to L3?"*
2. Show the metrics: approval rate 97%, 47/50 samples, confidence avg 91%
3. Explain: *"The system has been tracking every approval decision. When an agent meets the thresholds — 95% approval rate over 30+ samples — it surfaces a promotion card. You, as the admin, decide whether to trust it to act automatically."*
4. Show the accounting_guardian note: *"Some agents can never be promoted past L2 — like bill payment. Others, like the accounting guardian, are always L3 by design."*

### D3 — Source Document Links (1 min)

1. Open any HITL card in Inbox
2. Click the **source document link** (paperclip icon)
3. Show the original PDF in the document viewer
4. *"You can always trace any AI-extracted data back to the original document."*

---

## Scenario E — Multi-Currency & Settings (5 min)

> **Story**: "We work with clients in the UK and Singapore. Show me how Aethos handles multi-currency."

### E1 — GBP Engagement (2 min)

1. **Engagements** → open Blackwood Consulting (GBP £5,000/mo retainer)
2. **Invoices** → INV-TEST-002 → show GBP amount on invoice
3. **Accounting** → Journal Entries → find the INV-TEST-002 journal
4. Show the journal lines: `amount = £5,000 GBP`, `base_amount = $6,350 USD` (at current FX rate)
5. *"Journal lines store both the foreign currency amount and the base currency equivalent at the FX rate on the date of posting. The rate is never retroactively changed."*

### E2 — FX Rates (1 min)

1. Mention (or show if exposed): FX rates refresh every day at 8am UTC from Open Exchange Rates
2. If a rate is >3 days old, the system warns before posting a multi-currency entry

### E3 — Settings (2 min)

1. **Settings** → **Stripe Connect** → show onboarded state (connected, payouts enabled)
2. **Settings** → **Autonomy** → per-agent level overview
3. **Settings** → **Tax Rates** → pre-seeded rates for the firm's market (UK: VAT 20%/5%/0%)
4. **Profile** → show firm name, country, plan tier (Starter/Growth/Pro), trial end date

---

## Key Talking Points (use throughout)

| Concept | What to Say |
|---|---|
| **Agent-first** | "We don't require you to enter data. You drop a document and the agent handles it. Manual entry is always there as a fallback, but it's not the primary path." |
| **HITL by default** | "Every AI action needs your approval by default. You can promote specific agents to auto-execute once you trust their track record." |
| **Confidence chips** | "Every AI suggestion has a confidence score. High confidence = green. If it's amber or red, that's the system telling you to review carefully." |
| **Accounting guardian** | "The accounting engine validates every journal before it posts — balance check, period lock, account validity. You can't get an unbalanced book." |
| **Agentic, not just AI** | "There's a difference between an AI chatbot and an agentic platform. Agents here have memory, they track their own performance, they suggest when to promote themselves, and they degrade gracefully if the LLM is unavailable." |
| **Multi-currency** | "Day-1 support for USD, GBP, SGD, INR, and AUD. FX rates update daily. Every journal stores both the foreign amount and the base-currency equivalent — the rate is locked at posting time." |

---

## Common Questions

**Q: What if the AI makes a mistake?**
> "Every extraction goes through the Inbox for approval before anything is created. You can edit any field before approving. And all AI decisions are logged — corrections feed back into performance tracking."

**Q: Can I still use forms? We have staff who prefer that.**
> "Yes — every module has a traditional form as a fallback. Chat and document upload are the primary paths, but nothing is removed. You can enter time manually, create invoices from scratch, and post manual journal entries."

**Q: What happens if the LLM API is down?**
> "Agents degrade gracefully — the core ERP (invoices, time, bills, journals) keeps working. The AI extraction queue pauses and picks up when the API is back. Nothing blocks the essential financial workflows."

**Q: Is my financial data sent to AI models?**
> "PII is masked before any data leaves our system. Bank account numbers, tax IDs, and full card numbers are never sent to external AI APIs. The extraction agents see masked versions of sensitive fields."

**Q: What about accountants who need to close the books?**
> "Period locks are in place — once you lock a month, nothing backdates into it. We're adding a guided close assistant in the next version that checks your open items, suggests accruals, and walks you through the close checklist."

---

## Demo Reset

To reset the demo tenant to a clean state:
```bash
cd backend
uv run python -m scripts.seed_demo --tenant-id <uuid> --reset
```

This removes all `INV-TEST-*` and `BILL-TEST-*` prefixed data and re-seeds fresh demo content.

---

## Platform Overview Card (leave-behind)

```
Aethos — for Professional Services

What it replaces:
  • QBO/Xero + spreadsheets for PS billing
  • Harvest/BQE Core for time & expense
  • Manual AP processes

What's different:
  ✓ AI extracts engagement letters, vendor invoices, expense receipts
  ✓ Every AI action needs approval — nothing posts without your say-so
  ✓ Double-entry GL auto-posts on every transaction (no manual journals)
  ✓ 6 billing models: T&M, fixed, milestone, retainer, retainer-draw, capped T&M
  ✓ Multi-currency (USD/GBP/SGD/INR/AUD) from day 1
  ✓ Stripe Connect — client pays via link, funds go directly to your account
  ✓ Agents work in the background: collections emails, payment batch proposals,
    project health alerts, FX rate refreshes — all automatic

Pricing: Starter $29 · Growth $79 · Pro $199 / month
         (also available in GBP / SGD / INR / AUD)
         14-day free trial, no commitment
```
