# Aethos — Scenario-Based Demo Guide v2

> **Firm**: Meridian Advisory Group LLP
> **Base Currency**: GBP (£)
> **Service Lines**: Accounting & Advisory · Tax Services · Company Secretarial · Payroll
> **Markets**: UK (primary), Singapore, US (cross-border clients)
> **Guide version**: 2.0 · 2026-06-20

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

1. Seed the demo tenant:
   ```bash
   cd backend
   uv run python -m scripts.seed_demo --tenant-id <uuid> --reset
   ```
2. Log in as `marcus@meridianadvisory.co.uk` (Managing Partner — owner role)
3. The Copilot home appears — this is Meridian's operations hub

---

---

# SCENARIO 1 — Enterprise Client: Nexus Capital Partners

> **Who**: Nexus Capital Partners is a mid-market PE fund with 6 portfolio companies. They need accounting, tax structuring, and COSEC across their group structure.
>
> **Relationship**: 3-year master engagement, individual service orders per entity. Annual fee: £285,000.

---

## 1.1 Onboarding a New Engagement via Document Drop

**What to show**: The AI reads an engagement letter and populates a complex engagement correctly — no manual data entry.

### Steps

1. Go to **Copilot** → drop `nexus_engagement_letter.pdf` (the engagement letter)

   The letter says:
   > *"We are pleased to confirm our engagement with Nexus Capital Partners LP for the provision of accounting and advisory services for the period 1 January 2026 to 31 December 2026.*
   > *Our fees for services are as follows:*
   > - *Group consolidation accounts (statutory): £42,000 fixed fee*
   > - *Monthly management accounts (6 portfolio companies): £8,500/month retainer*
   > - *CFO advisory services: £350/hour, billed monthly in arrears*
   > - *Out-of-pocket expenses: at cost, billed monthly*"*

2. Watch the AI extract:
   - Client: Nexus Capital Partners
   - Billing arrangement: **Mixed** (fixed fee £42,000 + retainer £8,500/month + T&M £350/hr)
   - Start date: 2026-01-01
   - Confidence chip: 91% (amber — reason: mixed billing requires review)

3. Go to **Inbox** → see the **EngagementDraftCard**:
   - Shows extracted terms side-by-side with source document link
   - Click source document link → original PDF opens in viewer
   - The mixed billing model is pre-selected correctly
   - Edit: adjust cap amount, confirm hourly rate

4. **Approve** → Engagement created: *"Nexus Capital Partners — Group Accounting & Advisory"*

**Talking point**: *"The AI read a 12-page engagement letter, pulled out the commercial terms including a complex mixed billing model, and asked for one approval. Marcus didn't type anything."*

---

## 1.2 Project Structure Under the Engagement

**What to show**: One engagement, multiple projects for each portfolio company and workstream.

1. Go to **Engagements** → open Nexus Capital Partners
2. Show the embedded projects:
   - *Statutory Accounts — FY2025* (fixed fee £42,000)
   - *Monthly Management Accounts — Portfolio* (retainer £8,500/month)
   - *CFO Advisory* (T&M £350/hr)
3. Click **Projects** in the sidebar → see all projects across all engagements
4. Filter by "Nexus" → see the full project hierarchy

**Talking point**: *"Each workstream is a separate project within the engagement — separate billing, separate P&L tracking, but all tied to the Nexus master engagement."*

---

## 1.3 Time Entry: CFO Advisory Hours

**What to show**: Consultants log time via chat — no timesheet forms.

1. In **Copilot**, type:
   > *"Log 4.5 hours on the Nexus CFO Advisory project for today — board pack review and cash flow modelling"*

2. Watch the tool call: `log_time_entry(project="Nexus CFO Advisory", hours=4.5, description="...", billable=true)`

3. Response: *"Logged 4.5 billable hours on Nexus CFO Advisory — £1,575 at £350/hr"*

4. Type: *"Log 2 hours on Nexus CFO Advisory for yesterday — internal planning, non-billable"*

5. Go to **Time Entries** → see both entries. Filter by project → Nexus CFO Advisory shows 6.5 total hours, 4.5 billable.

**Talking point**: *"Partners and seniors log time in chat, the way they'd message a colleague. Billable vs non-billable is captured in the same sentence. Scope creep becomes visible instantly."*

---

## 1.4 Billing Run: Mixed Model Invoice

**What to show**: A single billing run producing a correctly structured invoice across 3 billing models.

1. Go to **Billing Runs** → click **Run Billing** for Nexus

2. The invoice drafter agent calculates:
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

3. Review the draft → click **Approve** → click **Send**

4. Stripe Payment Link generated → show the public invoice page (`/p/<token>`)
   - Nexus's finance team clicks Pay → Stripe processes → webhook fires → invoice marked paid → journal posts automatically

5. Go to **Reports** → **AR Aging** → Nexus line shows £41,661.84 in 0-30 days

**Talking point**: *"One billing run produces a perfectly structured invoice — fixed milestone, retainer, T&M, and expenses — all from data already in the system. No copy-pasting from timesheets into spreadsheets."*

---

## 1.5 Revenue Recognition: Retainer vs Fixed Fee

**What to show**: How revenue is recognised differently across billing models — WIP, deferred revenue, and the accounting guardian's role.

1. Go to **Reports** → **WIP** tab:
   - Shows Nexus CFO Advisory: 12.5 hrs × £350 = £4,375 unbilled WIP
   - Shows Statutory Accounts project: 0 WIP (fixed fee, recognised on milestone approval)

2. Go to **Accounting** → **Journal Entries** → filter by reference_type=invoice:
   ```
   DR  Accounts Receivable      £41,661.84
   CR  Revenue — Advisory Fees  £34,718.20   (recognised this period)
   CR  VAT Payable               £6,943.64
   ```

3. For the retainer portion specifically, explain:
   - Retainer fee recognised in the month it covers (June → June revenue)
   - No deferred revenue for monthly retainers
   - For annual retainer paid upfront → system would book `CR Deferred Revenue`, releasing `£8,500/month`

4. Go to **Reports** → **Project P&L** → Nexus CFO Advisory:
   ```
   Revenue (billed):     £4,375.00
   Cost (Alice: 12.5h × £150 cost rate): £1,875.00
   Gross Margin:         £2,500.00 (57%)
   ```

**Talking point**: *"Revenue recognition is baked into the accounting engine. The journal posts automatically when the invoice is approved. No manual GL entries for month-end accruals on standard billing patterns."*

---

## 1.6 Tax Advisory: T&M with Capped Fee

**What to show**: A separate Tax engagement with a T&M cap — protecting the client from overruns while ensuring Meridian is protected too.

1. In **Copilot**, type:
   > *"Create an engagement for Nexus — Corporation Tax Return FY2025, fixed fee £18,500, capped at £22,000 if advisory hours overrun"*

2. System creates: Billing arrangement = **capped_tm**, cap = £22,000, base = £18,500

3. Log tax advisory hours over time → when hours × rate approaches £22,000:
   - **Inbox alert** appears: *"Nexus Tax Advisory: 89% of £22,000 cap used (£19,580 billed). Alert: approaching cap."*
   - This is the `project_health_agent` surfacing a CAPPED_TM_APPROACHING alert

4. Show the alert card in Inbox → click **Investigate** → navigate to the project

**Talking point**: *"Meridian agreed a £22,000 cap with the client. The platform monitors every hour logged and alerts the partner before the cap is hit — not after."*

---

---

# SCENARIO 2 — Mid-Market Client: Brightwater Manufacturing Ltd

> **Who**: Brightwater makes precision parts for aerospace. £28M turnover, 180 employees. They've been with Meridian 5 years.
>
> **Services**: Monthly management accounts (retainer), annual statutory accounts + CT600 (fixed fee), monthly payroll for 180 employees.

---

## 2.1 Standard Monthly Retainer Billing (Zero-touch)

**What to show**: The retainer billing requires no human action when agents are at L3.

1. Go to **Settings** → **Autonomy** → show the **Invoice Drafter** at L2 with 98% approval rate and "★ Eligible" chip

2. Explain: *"After 60 consecutive approvals, Meridian promoted the invoice drafter to L3 for retainer-only invoices. It now sends the monthly invoice automatically."*

3. Go to **Invoices** → show `INV-0024` to Brightwater:
   ```
   Management Accounts — June 2026 (Retainer)    £2,800.00
   VAT @ 20%                                        £560.00
   Total                                          £3,360.00
   ```
   Status: **Sent** — created and sent without anyone clicking a button.

4. Show the journal entry auto-posted by the trigger:
   ```
   DR  Accounts Receivable    £3,360.00
   CR  Revenue                £2,800.00
   CR  VAT Payable              £560.00
   ```

5. In **Inbox** → there are NO pending tasks for Brightwater's monthly invoice. The agent handled it.

**Talking point**: *"Brightwater's monthly invoice goes out on the 1st of every month, automatically. James in Finance doesn't think about it. The L3 autonomy threshold was earned — 60 consecutive approvals with zero corrections."*

---

## 2.2 Annual Accounts + Tax — Milestone Billing

**What to show**: A fixed-fee engagement billed across milestones — draft accounts, review, sign-off.

1. Go to **Engagements** → Brightwater → *"Annual Statutory Accounts + CT600 FY2025"*

2. Show the engagement detail — Billing arrangement: **Milestone**:
   ```
   Milestone 1: Draft accounts filed for review          £4,200  (on completion)
   Milestone 2: Client-reviewed accounts signed          £4,200  (on completion)
   Milestone 3: CT600 submitted to HMRC                  £2,800  (on completion)
   Total fixed fee                                      £11,200
   ```

3. Mark Milestone 1 as complete → **Billing Run** → invoice for £4,200 + VAT generated

4. Walk through the 3 milestones over 2 months:
   - Revenue recognised at each milestone (not upfront)
   - WIP accumulates between milestones (hours logged but not yet billed)

5. After Milestone 3: Go to **Reports** → **Project P&L** → Brightwater Annual Accounts:
   ```
   Revenue:      £11,200
   Cost (hours): £3,840  (Sarah: 16h × £240/hr cost)
   Gross Margin: £7,360 (66%)
   ```

**Talking point**: *"The client agreed to three milestone payments tied to deliverables. Revenue is recognised when the milestone is delivered — not upfront, not on cash receipt. This is clean ASC/IFRS 15 percentage-of-completion."*

---

## 2.3 Payroll Service — Per-Employee Billing

**What to show**: Payroll is billed per employee per month — Aethos tracks headcount changes automatically.

1. In **Copilot**, type:
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
   - On day 32, a gentle reminder email is automatically drafted and sent (L3 for collections)

**Talking point**: *"Payroll billing scales with the client's headcount. When they hire, the next month's invoice reflects it automatically. And the collections agent has learned Brightwater always pays by day 32 — no spam reminders before that."*

---

## 2.4 Vendor Bills: Brightwater Subcontractor

**What to show**: Meridian sub-contracts some Brightwater work to a specialist firm. The invoice comes in, gets extracted, reviewed, and posted to AP.

1. In **Copilot**, drop `specialist_accountants_invoice.pdf`:
   > *"Invoice from Forster & Reid Ltd — audit support on Brightwater engagement, £3,200, dated 15 June 2026"*

2. `vendor_invoice_agent` extracts:
   - Vendor: Forster & Reid Ltd (new vendor — matched with 72% confidence against existing contacts)
   - Amount: £3,200
   - GL suggestion: **Project Costs — Subcontractors** (account 5100), confidence 94%
   - Tax ID check: UK VAT GB123456789 — ✅ format valid

3. **Inbox** → BillExtractedCard shows:
   - Amber confidence chip (72% vendor match — needs review)
   - GL account pre-selected as 5100 (high confidence)
   - Source document link

4. Review → Edit vendor to confirm it's Forster & Reid → **Approve**

5. Bill approved → journal posts:
   ```
   DR  Project Costs — Subcontractors (5100)    £3,200.00
   CR  Accounts Payable                          £3,200.00
   ```

6. Go to **Bills** → BILL-0041 shows approved, due 15 July 2026 (Net 30)

7. Go to **Pay Bills** → Forster & Reid appears with 12 days until due date

**Talking point**: *"Meridian received the subcontractor invoice, the AI matched it to a known vendor, suggested the right cost code, and the partner approved it in the Inbox. The NACHA payment file is ready to upload to Meridian's bank."*

---

---

# SCENARIO 3 — Private Wealth: Alderton Family Office

> **Who**: The Alderton family manages £420M in assets across 12 entities: a family investment company, 4 trading subsidiaries, 3 trusts, 2 SIPP wrappers, and 2 personal tax accounts. They demand discretion, bespoke reporting, and fast response.
>
> **Annual fees**: £148,000 across all entities and service lines.

---

## 3.1 Multi-Entity Engagement Structure

**What to show**: One client, multiple entities, separate engagements, unified view.

1. Go to **Contacts** → search "Alderton" → show the Alderton Family Office as `kind=both` (they're a customer for services but also a vendor when they reimburse Meridian's disbursements through their entity)

2. Go to **Engagements** → filter by client = Alderton:
   ```
   Alderton Family Investment Co — Annual Accounts           Fixed £28,000
   Alderton Trading Group — Group Management Accounts        Retainer £4,500/mo
   Alderton Trust (1985) — Trust Accounts & Tax             Fixed £12,500
   Alderton Trust (2008) — Trust Accounts & Tax             Fixed £9,200
   Sir Richard Alderton — Personal Tax Return               Fixed £8,400
   Lady Catherine Alderton — Personal Tax Return            Fixed £6,800
   Alderton COSEC Retainer — All entities                   Retainer £3,200/mo
   ```

3. Click into *Alderton Trading Group — Management Accounts*:
   - Billing: Retainer £4,500/month, billed on 1st
   - Currency: GBP
   - Show the 6-month invoice history — always paid on day 7 (fastest paying client)

**Talking point**: *"Seven separate engagements for one family. In the old world, Meridian managed this across 7 spreadsheets and 3 billing systems. Here it's one view, one Copilot, one inbox."*

---

## 3.2 Bespoke Tax Return — Fixed Fee with Scope Creep Risk

**What to show**: A personal tax return engagement with unexpected complexity mid-year — and how the platform handles the conversation.

1. Open engagement: *"Sir Richard Alderton — Personal Tax Return FY2025"*
   - Fixed fee: £8,400
   - Project: Tax Return + 2 Trusts

2. Partway through: Sir Richard's advisor calls — he sold his property portfolio in March 2025, generating a complex CGT calculation across 12 properties with partial PPR relief.

3. In **Copilot**, Sarah (tax director) types:
   > *"The Alderton personal tax return now includes complex CGT on 12 property disposals with PPR calculations. How much additional fee should we quote for this scope change?"*

4. The `reporting_agent` responds with context:
   > *"Based on similar CGT-heavy returns in your history: average additional hours = 14–22h at £280/hr = £3,920–£6,160. Alderton's base rate is £240/hr (agreed blended). Comparable: Thornton property CGT last year — 18h, £4,320 additional fee. Recommend: quote £4,800–£5,500 for CGT work."*

5. Sarah raises a **supplemental engagement** for the CGT work:
   - Billing: Fixed £5,000 (agreed with client)
   - Creates new invoice milestone: "CGT Computation & Submission — £5,000"

6. New engagement letter is generated, dropped to the Alderton portal

**Talking point**: *"When scope creeps, Sarah knows exactly what to charge because the system has history. The AI cited a comparable past matter — actual numbers, not a gut feel."*

---

## 3.3 Trust Accounts: Multi-Currency with Singapore Dividend Income

**What to show**: The Alderton 1985 Trust holds Singapore-listed shares. Annual income declared in SGD.

1. Open engagement: *"Alderton Trust (1985) — Trust Accounts & Tax"*
   - Base billing: GBP
   - Trust holds: SGD-denominated assets

2. In **Copilot**, type:
   > *"The 1985 Trust received S$42,000 dividend income from SingTel in March 2026. What is the GBP equivalent for the accounts?"*

3. Agent responds using the FX rates table:
   > *"At 28 March 2026 rate (1 GBP = 1.7234 SGD): S$42,000 = £24,370.31. Rate is current (refreshed today). Do you want me to log this as income in the trust accounts project?"*

4. Sarah confirms → Journal entry posted (via Manual Journal Entry):
   ```
   DR  Cash — Singapore Account             £24,370.31
   CR  Dividend Income — Foreign            £24,370.31
   ```
   - entry_date = 28 March 2026
   - FX rate snapshot stored; rate will not be retroactively changed

5. Go to **Reports** → **Trial Balance** → show the Foreign Dividend Income account (credit balance £24,370.31) and Cash account (debit balance includes £24,370.31)

**Talking point**: *"Every foreign income item is converted at the rate on the date it occurred — immutably locked. The auditor can trace every GBP amount back to the exact FX rate used."*

---

## 3.4 COSEC: Automated Filing Reminders

**What to show**: The COSEC retainer covers all 12 Alderton entities' statutory filings — confirmation statements, accounts filing deadlines, trust deed changes.

1. Go to **Inbox** → show a `project_health_alert` card:
   > **"Milestone Overdue — Alderton Family Investment Co"**
   > Filing deadline: 31 July 2026 (Confirmation Statement due at Companies House)
   > Status: Not yet prepared (milestone 3 days overdue)
   > Recommended action: Prepare and file confirmation statement immediately

2. Click **Investigate** → navigates to the COSEC engagement project timeline

3. Priya (COSEC manager) is notified via the Inbox:
   > "3 Alderton entities have confirmation statements due in the next 30 days"

4. Show **Projects** → filter by "COSEC" → see utilisation across all Alderton COSEC work:
   - 12 entities, each with a project
   - Priya's hours tracked across all
   - Retainer hours: 18 of 22 monthly hours used (scope creep approaching)

5. The `project_health_agent` has already created a RETAINER_FLOOR_WARNING:
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

3. Go to **Billing Runs** → invoice for April 2026 advisory:
   ```
   Advisory Retainer — April 2026    $4,500.00 USD
   ```
   Invoice sent in USD.

4. Thornton pays via Stripe Payment Link → $4,500 received

5. Go to **Accounting** → **Journal Entries** → show the payment journal:
   ```
   DR  Bank — USD Account (1102)     $4,500.00  [£3,560.28 @ 1.2641 GBP/USD]
   CR  Accounts Receivable            $4,500.00  [£3,560.28 @ 1.2641 GBP/USD]
   ```
   - `base_amount` = £3,560.28 locked at April 2026 rate
   - FX rate frozen at invoice date — never retroactively changed

6. Next month USD weakens. Invoice at new rate:
   - May invoice: $4,500 → £3,492.18 at 1.2882 GBP/USD (rate deteriorated)
   - `fx_gain_loss_service` posts:
   ```
   DR  Realized FX Loss (7900)    £68.10
   CR  Bank                       £68.10
   ```

7. Go to **Reports** → **Revenue by Engagement** → Thornton:
   - Shows USD revenue and GBP equivalent side by side
   - Toggle: "Show in USD" vs "Show in GBP base"

**Talking point**: *"Thornton pays in dollars. Meridian's books are in pounds. Every transaction captures both — the foreign amount and the sterling equivalent locked at the exchange rate on the day. FX gains and losses are calculated and posted automatically."*

---

## 4.2 Startup Equity Event: Milestone Billing for Fundraise Advisory

**What to show**: Thornton is raising a Series A. Meridian advises on the tax structuring. This is high-stakes work billed on a success milestone.

1. In **Copilot**, type:
   > *"Create a new engagement for Thornton Tech — Series A tax structuring advisory. Success fee: 0.75% of funds raised, payable on closing. Estimated raise: $12M."*

2. System creates:
   - Billing arrangement: **Milestone** (single milestone: "Series A Close")
   - Milestone amount: 0.75% × $12,000,000 = $90,000 (estimated)
   - Note: actual amount confirmed at close

3. Months later: Series A closes at $14.2M.

4. In **Copilot**: *"Thornton Series A closed at $14.2M. Update the milestone amount and invoice."*

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

1. Thornton appoints a new director. In **Copilot**:
   > *"Bill Thornton Tech for director appointment — AP01 filing, COSEC standard fee £650"*

2. System creates: Billing arrangement = **Fixed**, one milestone, £650

3. Thornton issues new shares for the Series A. In **Copilot**:
   > *"Log COSEC work for Thornton — SH01 shares allotment filing and shareholder register update, £1,200"*

4. Thornton updates registered office. Another £250.

5. Go to **Engagements** → Thornton COSEC → show three separate mini-engagements or one T&M billing:
   - Director appointment: £650
   - Share allotment: £1,200
   - Registered office: £250
   - Total April COSEC work: £2,100

6. Billing run → single invoice consolidating all three COSEC events for April:
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

## 5.1 Pre-Close Checklist (Close Assist Agent)

1. Marcus (Managing Partner) goes to **Accounting** → **Journal Entries** → clicks **Close Period: June 2026**

2. The `close_assist_agent` runs 10 pre-close checks in real-time (SSE streaming):
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

3. Two bills need approving:
   - Marcus clicks **Resolve** on the bill items → navigated to Bills list → approves both
   - Or: dismiss with reason ("Intentionally carrying to July")

4. WIP warning: Marcus decides to bill Brightwater for the 6.5 hours before close:
   - Billing run → £1,872 + VAT invoice for Brightwater

5. Checklist now shows ✅ for all items → **Lock June 2026**

---

## 5.2 Period Lock in Action

1. Period locked: June 2026

2. Try to post a backdated entry:
   - In **Accounting** → **New Journal Entry** → set date to 15 June 2026
   - Click Post → error: *"Period 2026-06 is locked. Entry rejected by Accounting Guardian."*

3. Correct approach: reopen June (owner-only) OR post a July correcting entry with description "Correction re June accrual"

4. Go to **Accounting** → **Period Locks** → show the lock record: locked by Marcus, timestamp, all entries frozen.

---

## 5.3 Trial Balance Review

1. Go to **Reports** → **Trial Balance** → set period to June 2026

2. Show the 12-account COA with balances:
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
   5000   Direct Costs — Salaries   £68,240.00
   5100   Subcontractor Costs        £9,180.00
   7900   Realized FX Gain/Loss        £240.35
   ──────────────────────────────────────────────────────
   Total                          £343,479.80   £343,479.80
   ```
   ✅ **Balanced — DR = CR**

3. FX note: £240.35 in account 7900 (net realized FX loss from USD invoices received)

---

## 5.4 Management Reporting Snapshot

1. **Reports** → **Project P&L** → sort by Gross Margin descending:
   - Thornton Series A: 92% (exceptional)
   - Nexus CFO Advisory: 57% (good)
   - Brightwater Annual Accounts: 66% (good)
   - Brightwater Payroll: 38% (volume margin, acceptable)

2. **Reports** → **Utilization** → June:
   - Sarah Williams: 87% billable (high — approaching burnout threshold)
   - Priya Sharma: 71% billable (healthy)
   - Alice Chen: 64% billable (below target — investigate)

3. In **Copilot**, Marcus types:
   > *"Alice is at 64% utilisation in June. Which clients have unbilled WIP tied to Alice?"*

4. Agent response:
   > *"Alice has 22 unbilled hours across 3 projects: Brightwater Management Accounts (8h, £2,240), Nexus CFO Advisory (9h, £3,150), Alderton Trust 1985 (5h, £1,200). Total WIP: £6,590. Brightwater is past month-end — recommend billing today."*

5. Marcus approves the Brightwater billing run from the chat response card.

---

---

# DEMO CLOSING: The Agentic Difference

## What Meridian's team doesn't do anymore

| Old way (before Aethos) | New way |
|---|---|
| Type engagement terms from PDF into billing software | Drop PDF → AI extracts → one approval |
| Send monthly retainer invoices manually on 1st | Invoice drafter runs at L3 — sends itself |
| Spreadsheet for subcontractor invoices received | Drop PDF → vendor matched → GL coded → AP posted |
| Chase clients with standard email templates | Collections agent drafts personalised reminders based on client history |
| Pull timesheets from 3 systems to calculate WIP | WIP report live in Aethos, updated as hours are logged |
| Month-end: 3-day close spreadsheet checklist | Close assist agent runs 10 checks in 30 seconds |
| FX conversion done manually in Excel | FX rates refreshed daily; conversion posted automatically; rates frozen at transaction date |
| Partner calls to ask "did Brightwater pay?" | Intelligence agent flags overdue invoices before the partner thinks to ask |

## The key numbers for this demo

- **4 clients** | **£640K+ annual fees** | **7 service lines** | **3 billing models**
- **4 currencies** (GBP, USD, SGD, EUR)
- **13 AI agents** working in the background
- **Zero manual GL entries** for standard billing patterns
- **One Inbox** for everything needing human judgment

---

## Objection Handlers

**"We already have Xero/QBO — why do we need this?"**
> Xero tells you what happened. Aethos does it for you. Xero has no concept of your engagement terms, your billing arrangements, your WIP, or your client relationships. Every invoice is still a manual act.

**"Our clients have complex requirements — can AI handle that?"**
> AI extracts and proposes. Humans approve. The AI doesn't post a £106,500 invoice without the partner confirming. Complexity is handled at the engagement setup stage; once set, billing runs correctly every time.

**"What if the AI makes a mistake?"**
> Every AI suggestion has a confidence score and a source document link. If the confidence is below 85%, the card is flagged amber — the reviewer knows to look carefully. And the Accounting Guardian rejects any imbalanced journal before it posts — it's impossible to create a broken entry.

**"What about GDPR / data privacy for our clients?"**
> PII is masked before any data leaves your system and reaches an AI model. Bank account numbers, tax IDs, and full names are never sent to the LLM. The AI sees masked versions: `GB12*****89`, `[CLIENT NAME]`.

**"We do payroll — can this handle PAYE, RTI?"**
> Payroll in v1 handles the billing and time-tracking side — what you charge clients for payroll services, not the payroll bureau processing itself. The payroll processing integrations (Sage, Brightpay, Xero Payroll) are on the roadmap.

---

## Appendix: Sample Files for Demo

Place these in `docs/demo-assets/`:

- `nexus_engagement_letter.pdf` — Multi-page engagement letter with mixed billing terms
- `brightwater_subcontractor_invoice.pdf` — Forster & Reid invoice, UK VAT number
- `alderton_sgd_dividend_notice.pdf` — Singapore dividend income statement in SGD
- `thornton_cosec_instruction.pdf` — New director appointment instruction letter

> **Tip for demos**: Have two browser tabs open — one logged in as Marcus (Managing Partner, owner role) and one as Sarah (Tax Director, manager role). Switch tabs to show role-based access: Sarah can approve time but can't lock periods; Marcus can do everything.
