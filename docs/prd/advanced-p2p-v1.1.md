# PRD: Advanced P2P — Recurring Vendor Bills, Multi-Step Approvals & Native Bank Formats

> **Owner**: Netra (Product Manager)
> **Status**: DRAFT — Awaiting Vishwa / Founder approval
> **Version**: v1.1
> **Created**: 2026-06-20
> **GitHub Issue**: #217
> **Parent plan section**: PLAN.md §11.5
> **Depends on**: v1 P2P complete (vendor_invoice_agent, HITL inbox, bill approval, bill_pay_agent, NACHA/CSV, AP aging)

---

## 0. Executive Summary

The v1 P2P loop (extract → HITL review → approve → pay → export) is live. This PRD defines the intelligence layer on top: the system should detect that AWS bills every month, propose automation, and then handle it forever. It should know that a bill over $50,000 needs the CFO, not just the bookkeeper. It should warn the AP clerk that paying Apex Staffing today saves $72. It should export a BACS file that the firm's HSBC UK relationship manager can upload without asking IT for help.

These capabilities are the difference between a tool that saves time and a platform that earns trust as the firm's financial backbone.

---

## 1. Product Context

### 1.1 Who is this for?

**Primary personas:**

**Sarah — Firm Owner / Managing Partner (15-person consulting firm)**
Sarah reviews finances weekly. She does not do the bookkeeping. She needs to know that large bills are on her desk, that sub-contractors are tracked for tax season, and that the firm is not leaving early-pay discounts on the table. She authorises payments over $10,000. She has 10 minutes between client calls.

**Marcus — AP Clerk / Bookkeeper (works for Sarah's firm)**
Marcus processes 30–80 vendor bills per month: SaaS subscriptions, sub-contractor invoices, travel reimbursements, facilities. He approves small bills solo. He routes large bills to Sarah. He is tired of manually exporting CSV files and then reformatting them for the bank's bulk-pay portal. He loves that the AI already coded the GL account correctly — he just reviews it.

**Secondary personas:**

**Priya — Finance Manager / Controller (50-person advisory firm)**
Priya owns the approval matrix. She sets thresholds. She wants an audit trail of who approved what and when. She cares about period close and making sure no bill slips through as a duplicate.

**Dev / CFO (final approver on large payments)**
Dev sees one notification per week: "Three bills over $25,000 are waiting for your approval." He clicks, reviews the summary, and approves from the Inbox. He does not want to log into a separate system.

---

## 2. Problem Statements

| # | Problem | Impact | Current State |
|---|---------|--------|---------------|
| P1 | Recurring bills (AWS, GitHub, rent, retainer sub-contractors) are re-entered manually each month | 20–30 minutes per AP clerk per month, high risk of missed payment | Not automated |
| P2 | All bills route to a single approver regardless of amount | Controllers and owners waste time on $48 SaaS bills; large bills lack required sign-off rigour | Binary approve/reject |
| P3 | Early-pay discounts are missed because no one flags them systematically | 2% on $20k/month = $400/month lost; $4,800/year per mid-size firm | No discount intelligence |
| P4 | UK/AU/SG/IN tenants export Universal CSV and then reformat it for their bank's portal | 15–30 minutes per payment run; error-prone manual reformatting | NACHA (US) + Universal CSV only |
| P5 | 1099 tracking is done in a spreadsheet outside the ERP | Tax season scramble; risk of under-reporting | No contractor tracking |

---

## 3. Feature Scope — v1.1 vs v1.2

### v1.1 (this PRD — next sprint)

| # | Feature | Priority | Effort |
|---|---------|----------|--------|
| F1 | Recurring Bill Intelligence | Must | L |
| F2 | Multi-Step Bill Approval Workflow | Must | M |
| F3 | Vendor Payment Terms & Early-Pay Discounts | Must | M |
| F4 | Native Bank File Formats (BACS, ABA, GIRO, NEFT) | Must | L |
| F5 | 1099 / Contractor Tracking (US only) | Should | M |

### v1.2 (next cycle — not in this PRD)

| Feature | Rationale for deferral |
|---------|----------------------|
| Stripe Connect to vendors (direct transfer) | Rail integration; requires money-transmitter analysis |
| Plaid + Dwolla ACH origination | Rail integration; separate compliance review |
| Modern Treasury (high-volume) | Enterprise tier feature; post-GA |
| Purchase Order matching | PO module not yet in scope |
| Three-way match (PO / GR / Invoice) | Depends on PO and goods-receipt modules |
| Duplicate invoice detection (ML) | Needs 6+ months of data per tenant to be reliable |
| Vendor self-service portal | Separate product surface; not v1.x |

---

## 4. Feature: Recurring Bill Intelligence (F1)

### 4.1 Problem Statement

PS firms pay the same vendors on a predictable schedule: AWS on the 1st of every month, Slack on the 15th, a sub-contractor retainer on the last business day. Currently every bill comes in, gets uploaded, extracted, reviewed, and approved from scratch — even when the agent has seen the same vendor six months in a row for ~$2,340.

The system should notice this pattern, propose a recurring schedule to the admin (once), and then auto-generate draft bills on schedule — subject to variance checks and a final HITL approval before payment.

### 4.2 User Stories

**US-P2P-101: Agent Detects Recurring Pattern**

As Marcus (AP clerk), I want the system to automatically identify that AWS sends a bill every month for approximately the same amount, so that I do not have to manually enter it each month.

Acceptance criteria:
- Given 3 or more bills from the same vendor within the last 6 months with interarrival intervals within ±7 days and amounts within ±20% of each other, when the pattern detection worker runs (nightly), then the `recurring_bill_detection_worker` creates a `recurring_bill_schedule` row in `draft` status and queues an Inbox card for admin review.
- Given a detected pattern, when the Inbox card is rendered, then it shows: vendor name, detected frequency (monthly / biweekly / weekly / annual), detected average amount, suggested next bill date, and a confidence percentage.
- Given the LLM API is unavailable, when the detection worker runs, then pattern detection falls back to the SQL-only heuristic (no LLM call required for detection; LLM is optional for the natural-language summary on the card).
- Given fewer than 3 historical bills from a vendor, when the worker runs, then no schedule is proposed for that vendor.

**US-P2P-102: Admin Approves Recurring Schedule**

As Sarah (firm owner), I want to approve a proposed recurring schedule once, so that the system handles the bill entry automatically going forward.

Acceptance criteria:
- Given a `recurring_bill_schedule` in `draft` status, when Sarah opens the Inbox card, then she sees the proposed schedule with the option to: (a) approve as-is, (b) edit the amount, frequency, or GL code, or (c) dismiss (do not propose again for 60 days).
- Given Sarah clicks "Approve Schedule", when the system confirms, then the `recurring_bill_schedule` status is set to `active` and a success notification appears.
- Given Sarah edits the schedule before approving, when she saves, then her edits are preserved and override the agent's proposed values.
- Given Sarah dismisses the card, when the worker runs again within 60 days, then no new card is created for that vendor.

**US-P2P-103: Auto-Generation of Draft Bills**

As Marcus, I want the system to automatically create a draft bill when a scheduled recurring bill is due, so that it appears in my review queue without me needing to upload anything.

Acceptance criteria:
- Given an `active` recurring_bill_schedule with `next_bill_date` = today, when the `billing_run_worker` runs at 00:30 UTC, then a `bills` row is created with `status=draft`, `source='recurring'`, and all fields pre-populated from the schedule template.
- Given the auto-generated draft, when Marcus opens Bills, then the bill is visible with a "Recurring" badge and the schedule name.
- Given the auto-generated bill, when Marcus reviews it, then he follows the normal HITL approval flow (review → approve → pay) — no extra steps.
- Given no actual vendor invoice arrives (the bill is agent-generated), when Marcus approves, then the audit log shows `source='recurring'` and the schedule_id reference.

**US-P2P-104: Variance Detection — Flag for Human Review**

As Sarah, I want the system to flag a recurring bill for human review if the actual amount is more than 15% higher than the scheduled amount, so that unexpected cost spikes do not slip through automatically.

Acceptance criteria:
- Given an active schedule with an expected amount of $2,340, when a vendor uploads or emails an invoice for $3,100 (>15% variance), then the agent flags the bill with a `variance_flag=true` and a HITL card explains: "AWS bill is 32% higher than the $2,340 monthly average — review before approving."
- Given the variance flag, when the bill appears in the Inbox, then it cannot be auto-approved at L3; it requires explicit manual approval regardless of autonomy settings.
- Given the flagged bill is approved by an admin, when Marcus confirms, then the approved amount is factored into the rolling average for the next variance check (the schedule's `avg_amount` is updated using a 3-month rolling window).
- Given the variance is ≤15%, when the detection worker runs, then the bill proceeds to the normal draft → review flow without a variance flag.

**US-P2P-105: Schedule Management**

As Marcus, I want to view, pause, and edit all active recurring schedules, so that I have full visibility and control over automated bill generation.

Acceptance criteria:
- Given the Settings → AP Controls page, when Marcus navigates to "Recurring Schedules", then he sees a list of all active, draft, and paused schedules with: vendor, frequency, next date, amount, GL code, and status.
- Given an active schedule, when Marcus clicks "Pause", then the schedule status = `paused` and no bills are auto-generated until he resumes.
- Given a paused schedule, when Marcus clicks "Resume", then the `next_bill_date` is recalculated from today and generation resumes.
- Given Marcus edits a schedule (amount, GL, frequency), when he saves, then the change takes effect from the next generation date; previously generated bills are not retroactively changed.

### 4.3 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R-F1-01 | `recurring_bill_detection_worker` runs nightly; analyzes `bills` table for patterns across each (tenant_id, vendor_id) pair | Must |
| R-F1-02 | Pattern = 3+ bills in 6 months, interarrival ±7 days, amount variance ≤20% | Must |
| R-F1-03 | Worker creates `recurring_bill_schedules` row in `draft` status; queues Inbox card via `hitl_tasks` | Must |
| R-F1-04 | Admin can approve, edit, or dismiss a schedule from the Inbox card | Must |
| R-F1-05 | `billing_run_worker` generates draft `bills` from active schedules at 00:30 UTC | Must |
| R-F1-06 | Variance threshold: if actual > schedule_avg × 1.15, set `variance_flag=true` on the bill | Must |
| R-F1-07 | Variance-flagged bills cannot be auto-approved at any autonomy level | Must |
| R-F1-08 | Schedule management UI in Settings → AP Controls → Recurring Schedules | Must |
| R-F1-09 | Pause / resume / edit / delete schedule operations | Must |
| R-F1-10 | Rolling 3-month average amount recalculated after each approved bill from a schedule | Should |
| R-F1-11 | LLM used only for natural-language summary in the Inbox card; detection logic is pure SQL/Python | Should |
| R-F1-12 | Audit log entry for every schedule state change | Must |

### 4.4 Agent Behavior Specification

**Agent**: `recurring_bill_detection_worker` (new Procrastinate background worker; not a PydanticAI LLM agent — SQL-driven with optional LLM summary)

**Detection algorithm (SQL-level):**

```
For each (tenant_id, vendor_id) pair:
  1. Fetch all bills in the past 180 days (status NOT 'void')
  2. If count < 3: skip
  3. Calculate interarrival days between consecutive bills (by bill_date)
  4. If std_dev(interarrival_days) > 7: no pattern (too irregular)
  5. If std_dev(amount) / avg(amount) > 0.20: no pattern (too variable)
  6. Classify frequency:
     - avg_interval 28–32 days → 'monthly'
     - avg_interval 13–15 days → 'biweekly'
     - avg_interval 6–8 days → 'weekly'
     - avg_interval 88–92 days → 'quarterly'
     - avg_interval 360–370 days → 'annual'
  7. Calculate next_bill_date = last_bill_date + avg_interval_days
  8. If no existing schedule for (tenant_id, vendor_id) with status in ('draft','active','paused'):
     CREATE recurring_bill_schedules row (status='draft')
     CREATE hitl_task (type='recurring_schedule_proposal')
```

**LLM call (optional — for Inbox card summary only):**

The LLM is called to generate a one-sentence plain-English summary for the Inbox card:
- Input: vendor name, frequency, avg amount, currency, next date
- Output: "AWS sends a monthly bill for approximately $2,340 — approve this recurring schedule to automate future bill entry."
- If LLM is unavailable: use a template string; do not block the card from appearing.

**Variance check (at bill approval time, not detection time):**

```
When a bill is submitted for approval (source='recurring' or vendor has active schedule):
  schedule = get_active_schedule(tenant_id, vendor_id)
  if schedule and bill.total > schedule.avg_amount * 1.15:
    bill.variance_flag = True
    create hitl_task(type='variance_review', bill_id=bill.id)
```

**Autonomy level**: The detection worker is a background process (no autonomy level). The resulting HITL task follows L2 semantics — the agent proposes; the human approves. Variance-flagged bills are L1 (human always reviews before approval) regardless of tenant autonomy settings.

### 4.5 Data Model Changes

**New table: `recurring_bill_schedules`**

```sql
CREATE TABLE recurring_bill_schedules (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  vendor_id       UUID NOT NULL REFERENCES clients(id),  -- clients.kind='vendor'
  status          TEXT NOT NULL DEFAULT 'draft'          -- 'draft' | 'active' | 'paused' | 'cancelled'
    CHECK (status IN ('draft','active','paused','cancelled')),
  frequency       TEXT NOT NULL                          -- 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'annual'
    CHECK (frequency IN ('weekly','biweekly','monthly','quarterly','annual')),
  avg_amount      NUMERIC(15,2) NOT NULL,
  currency        TEXT NOT NULL DEFAULT 'USD',
  next_bill_date  DATE NOT NULL,
  day_of_month    INT,                                   -- nullable; used for monthly schedules
  gl_account_id   UUID REFERENCES accounts(id),
  project_id      UUID REFERENCES projects(id),
  notes           TEXT,
  variance_pct    NUMERIC(5,2) NOT NULL DEFAULT 15.00,   -- variance threshold, default 15%
  detected_from_bill_ids  UUID[] NOT NULL DEFAULT '{}',  -- source bills used for detection
  approved_by_user_id UUID REFERENCES tenant_users(id),
  approved_at     TIMESTAMPTZ,
  dismissed_until DATE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, vendor_id, status)                  -- one active schedule per vendor
    DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_recurring_schedules_tenant_next_date
  ON recurring_bill_schedules(tenant_id, next_bill_date)
  WHERE status = 'active';
```

**Changes to `bills` table:**

```sql
ALTER TABLE bills ADD COLUMN recurring_schedule_id UUID REFERENCES recurring_bill_schedules(id);
ALTER TABLE bills ADD COLUMN variance_flag BOOLEAN NOT NULL DEFAULT FALSE;
-- source column already exists with value 'recurring' available
```

**RLS:** `recurring_bill_schedules` follows tenant isolation pattern: `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`.

---

## 5. Feature: Multi-Step Bill Approval Workflow (F2)

### 5.1 Problem Statement

All bills currently route to a single approver. A $48 SaaS renewal and a $45,000 sub-contractor invoice follow the same flow. Firms want a threshold-based matrix: small bills → bookkeeper; medium bills → finance manager; large bills → owner or CFO. The current binary approve/reject model cannot support this without custom engineering for each tenant.

### 5.2 User Stories

**US-P2P-201: Admin Configures Approval Matrix**

As Sarah (firm owner), I want to define approval thresholds so that small bills are handled by my bookkeeper while large bills require my sign-off.

Acceptance criteria:
- Given the Settings → AP Controls page, when Sarah opens "Approval Workflows", then she sees a threshold matrix with configurable rows: (a) up to amount Tier 1 → approver role(s), (b) Tier 1 to Tier 2 → approver role(s), (c) above Tier 2 → approver role(s) + optional email confirmation.
- Given Sarah sets Tier 1 = $5,000 (single approver: "AP Clerk" role) and Tier 2 = $25,000 (two approvers: "Finance Manager" + "Owner"), when she saves, then those rules are persisted to `bill_approval_rules` and applied to all new bills from that point forward.
- Given a rule with two required approvers, when the first approver approves, then the bill moves to a "pending second approval" state and a notification is sent to the second approver.
- Given a rule with an email confirmation link for bills over Tier 2, when Dev (CFO) approves the last step, then the bill is fully approved and a journal entry is created.
- Given Sarah has not configured any rules, when a bill is submitted, then it uses the default single-approver flow (backward compatible with v1 behavior).

**US-P2P-202: Sequential Step Routing**

As Marcus (AP clerk), I want the system to automatically route a bill to the right approver based on its amount, so that I do not have to manually decide who to send it to.

Acceptance criteria:
- Given a bill for $3,200 and a rule that bills under $5,000 require Marcus's approval only, when the bill is ready for approval, then only Marcus receives an Inbox notification; Sarah does not see it.
- Given a bill for $18,000 and a Tier 1 threshold of $5,000, when the bill is submitted, then Marcus receives step 1 approval request; after Marcus approves, Sarah automatically receives step 2 approval request.
- Given a two-step approval where Marcus approved step 1 but Sarah has not yet approved step 2, when the bill due date passes, then an escalation notification is sent to Sarah.
- Given Marcus tries to approve a bill that exceeds his approval tier, when he clicks Approve, then the system rejects the action with a clear message: "This bill requires approval from Finance Manager or above."

**US-P2P-203: Email Confirmation for High-Value Bills**

As Dev (CFO), I want to approve large bills via a secure email link, so that I can act on them without logging into the system.

Acceptance criteria:
- Given a bill that triggers the highest approval tier (e.g., over $50,000), when the second approver (e.g., Finance Manager) completes their step, then the system sends a branded email to the CFO with a secure one-time link summarizing the bill.
- Given Dev clicks the "Approve" button in the email, when the link is valid (not expired, not already used), then the bill is approved, the journal entry is created, and Dev receives a confirmation email.
- Given the email link has expired (24 hours), when Dev clicks it, then he sees a page asking him to log in to approve via the Inbox instead.
- Given the bill is voided while awaiting email confirmation, when Dev clicks the email link, then he sees a message: "This bill has been voided. No action required."

**US-P2P-204: Approval Audit Trail**

As Priya (Finance Manager), I want a complete audit trail of who approved each bill and when, so that I can satisfy audit requirements and period close reviews.

Acceptance criteria:
- Given a multi-step approved bill, when Priya views the bill detail, then she sees a timeline: "Step 1: Marcus approved $18,000 on June 15 at 2:34 PM" and "Step 2: Sarah approved on June 16 at 9:12 AM."
- Given an email-confirmation approval, when the timeline is rendered, then it shows "Approved via email confirmation link" with the timestamp.
- Given the audit log, when Priya exports it, then it includes: bill_id, vendor, amount, each approver user_id + name + timestamp + step number + method (in-app / email link).

### 5.3 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R-F2-01 | `bill_approval_rules` table: (tenant_id, tier_order, min_amount, max_amount, required_approver_roles, email_confirmation_required) | Must |
| R-F2-02 | `bill_approval_steps` table tracks each step (bill_id, step_num, required_role, status, approved_by, approved_at, method) | Must |
| R-F2-03 | Bill approval engine: on submit, evaluate amount against rules → create step rows → notify step-1 approver | Must |
| R-F2-04 | On step N approval: if step N+1 exists, create hitl_task for step N+1 approver | Must |
| R-F2-05 | Role-based approval guard: reject approve action if user's role does not match required_approver_roles for that step | Must |
| R-F2-06 | Email confirmation: generate signed one-time token (JWT, 24h TTL); send via Resend; validate on click | Must |
| R-F2-07 | Escalation: if step pending > bill.due_date - 2 days, send reminder notification | Should |
| R-F2-08 | Default behavior (no rules configured): single-approver (any admin-role user) — v1 backward compatible | Must |
| R-F2-09 | Approval rules UI in Settings → AP Controls → Approval Workflows | Must |
| R-F2-10 | Audit timeline on bill detail page showing each step | Must |
| R-F2-11 | Prahari security review required before implementation (signed tokens, RBAC enforcement) | Must |

### 5.4 Data Model Changes

**New table: `bill_approval_rules`**

```sql
CREATE TABLE bill_approval_rules (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES tenants(id),
  tier_order       INT NOT NULL,                          -- 1, 2, 3
  min_amount       NUMERIC(15,2) NOT NULL DEFAULT 0,
  max_amount       NUMERIC(15,2),                         -- NULL = no upper limit
  currency         TEXT NOT NULL DEFAULT 'USD',
  required_roles   TEXT[] NOT NULL,                       -- e.g. ['admin', 'manager']
  email_confirm_required BOOLEAN NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, tier_order)
);
```

**New table: `bill_approval_steps`**

```sql
CREATE TABLE bill_approval_steps (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES tenants(id),
  bill_id          UUID NOT NULL REFERENCES bills(id),
  step_num         INT NOT NULL,
  required_roles   TEXT[] NOT NULL,
  status           TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected','skipped')),
  approved_by      UUID REFERENCES tenant_users(id),
  approved_at      TIMESTAMPTZ,
  method           TEXT CHECK (method IN ('in_app','email_link')),
  email_token      TEXT,                                  -- signed JWT, stored hashed
  email_token_expires_at TIMESTAMPTZ,
  email_sent_to    TEXT,                                  -- email address for audit
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (bill_id, step_num)
);
```

**Changes to `bills` table:**

```sql
ALTER TABLE bills ADD COLUMN approval_step_current INT DEFAULT 1;
ALTER TABLE bills ADD COLUMN approval_completed_at TIMESTAMPTZ;
-- status values extended: 'pending_approval' (step in progress) already covered by existing 'draft'/'approved' flow
-- no change to status column; step state lives in bill_approval_steps
```

---

## 6. Feature: Vendor Payment Terms & Early-Pay Discounts (F3)

### 6.1 Problem Statement

AP clerks and finance managers know the payment terms for their key vendors but the system does not — so it cannot warn them when an early-pay discount is expiring, optimize payment runs to capture discounts, or enforce that a Net 60 vendor is not paid early and starving cash flow.

### 6.2 User Stories

**US-P2P-301: Set Payment Terms on Vendor**

As Marcus (AP clerk), I want to record payment terms and early-pay discount details on a vendor's contact record, so that the system can apply them automatically to new bills.

Acceptance criteria:
- Given a vendor contact in Settings → Vendors, when Marcus opens the vendor detail, then he sees a "Payment Terms" section with: (a) standard terms dropdown (Net 15 / Net 30 / Net 45 / Net 60 / Net 90 / Due on Receipt / Custom days), (b) early-pay discount percentage (numeric, nullable), (c) early-pay discount days (numeric, nullable).
- Given Marcus sets Apex Staffing to "2/10 Net 30" (2% discount if paid within 10 days), when a new bill from Apex Staffing is created (by upload, extraction, or recurring generation), then the bill's `payment_terms_days=30`, `discount_pct=2.00`, `discount_days=10`, and `discount_deadline=bill_date + 10` are auto-populated.
- Given these fields are set, when the bill is in "approved" status and today is before the discount_deadline, then the Inbox shows a discount alert card.

**US-P2P-302: Discount Alert in Inbox**

As Sarah (firm owner), I want to receive an alert when an early-pay discount is about to expire, so that I can act before the window closes.

Acceptance criteria:
- Given a bill with a discount_deadline within the next 3 days, when the `discount_alert_worker` runs (daily at 08:00 tenant local time), then an Inbox notification appears: "Pay Apex Staffing before [date] to save [currency][amount] ([X]% early-pay discount)."
- Given the alert card, when Sarah clicks "View Bill", then she is taken directly to the bill detail with the discount amount prominently displayed.
- Given the discount deadline has passed, when Sarah views the bill, then the discount badge shows "Discount expired" in muted text (not an error, just informational).
- Given Marcus pays the bill before the discount_deadline, when the payment is recorded, then the system calculates and applies the discount: (a) bill payment amount = bill.total × (1 - discount_pct/100); (b) the discount amount posts to a "Purchase Discounts" GL account (typically 5900 or tenant-configured).

**US-P2P-303: bill_pay_agent Discount Optimisation**

As Marcus (AP clerk), I want the bill_pay_agent to factor in early-pay discount windows when proposing payment batches, so that the system helps me capture savings without manual tracking.

Acceptance criteria:
- Given 5 approved bills ready for payment and one of them has a discount_deadline 2 days from now, when the bill_pay_agent proposes a payment batch, then it groups the discount-eligible bill first, flagged with: "Include today to capture $72 early-pay discount (2% on $3,600)."
- Given the agent's batch proposal in the Inbox, when Marcus reviews it, then he can see the total savings from discount capture in the batch summary line.
- Given Marcus removes the discount-eligible bill from the batch, when the batch is saved, then the agent logs the decision and does not re-add it automatically (human override respected).

### 6.3 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R-F3-01 | `clients` table: add `payment_terms_days`, `discount_pct`, `discount_days` columns (for kind='vendor') | Must |
| R-F3-02 | `bills` table: add `payment_terms_days`, `discount_pct`, `discount_days`, `discount_deadline`, `discount_amount` columns | Must |
| R-F3-03 | Auto-populate discount fields from vendor contact when bill is created (extraction or manual) | Must |
| R-F3-04 | `discount_alert_worker` (new Procrastinate task): daily check for bills with discount_deadline within 3 days | Must |
| R-F3-05 | Inbox card for discount alert with save amount and deadline | Must |
| R-F3-06 | `bill_pay_agent` updated: prioritize discount-eligible bills in batch proposals | Must |
| R-F3-07 | Discount GL posting: create `purchase_discounts` account (GL code 5900) if not present; post discount amount as a credit on bill payment | Must |
| R-F3-08 | Payment terms selector on vendor contact page (Settings → Vendors) | Must |
| R-F3-09 | Display discount deadline and savings on bill detail page | Should |
| R-F3-10 | Discount capture rate metric available in AP Reports | Could |

### 6.4 Data Model Changes

**Changes to `clients` table (vendor fields):**

```sql
ALTER TABLE clients ADD COLUMN payment_terms_days INT;           -- default days to pay (e.g. 30)
ALTER TABLE clients ADD COLUMN early_pay_discount_pct NUMERIC(5,2); -- e.g. 2.00 for 2%
ALTER TABLE clients ADD COLUMN early_pay_discount_days INT;      -- days within which discount applies (e.g. 10)
```

**Changes to `bills` table:**

```sql
ALTER TABLE bills ADD COLUMN payment_terms_days INT;
ALTER TABLE bills ADD COLUMN discount_pct        NUMERIC(5,2);
ALTER TABLE bills ADD COLUMN discount_days       INT;
ALTER TABLE bills ADD COLUMN discount_deadline   DATE;
ALTER TABLE bills ADD COLUMN discount_amount     NUMERIC(15,2);  -- pre-calculated = total * discount_pct / 100
```

---

## 7. Feature: Native Bank File Formats (F4)

### 7.1 Problem Statement

Non-US tenants are currently exporting a Universal CSV that they then have to manually reformat for their bank's bulk-payment portal. HSBC UK wants a BACS file. DBS Singapore wants a GIRO file. ICICI India expects NEFT batch instructions. This manual reformatting takes 15–30 minutes per payment run and introduces errors.

The v1 decision to defer native formats was correct — we needed to validate the workflow first. The workflow is validated. Now we add the formats.

### 7.2 User Stories

**US-P2P-401: Tenant Selects Bank Format**

As Sarah (UK firm owner), I want to configure my preferred bank file format once in Settings, so that every payment run exports in the correct format without me choosing each time.

Acceptance criteria:
- Given Settings → Payments → Bank Format, when Sarah opens the page, then she sees a selector: NACHA (US) / BACS (UK) / ABA (AU) / GIRO (SG) / NEFT (IN) / Universal CSV (All Markets).
- Given Sarah selects BACS, when she saves, then all future payment batch exports default to BACS format.
- Given a tenant with country='GB' (UK), when they first open Settings → Payments, then BACS is pre-selected as the default (smart default based on tenant.country).
- Given a tenant running a multi-currency payment batch in USD and GBP, when they export, then they are prompted to select the format per currency or choose a combined export.

**US-P2P-402: BACS File Export (UK)**

As Marcus (UK AP clerk), I want to export an approved payment batch as a standard BACS file, so that I can upload it directly to my bank's BACS origination portal without manual reformatting.

Acceptance criteria:
- Given an approved payment batch with BACS format selected, when Marcus clicks "Download BACS File", then the system generates a valid BACS Standard 18 payment file (`.txt`).
- Given the BACS file, when Marcus opens it, then it contains: (a) header record with originator sort code and account number; (b) one credit detail record per bill payment with beneficiary sort code, account number, reference, and amount (in pence, no decimal); (c) trailer record with total credits and total amount.
- Given a bill with a missing beneficiary sort code or account number, when the export is triggered, then the system shows a validation error: "Apex Staffing is missing UK sort code and account number. Please update vendor banking details before exporting."
- Given the BACS file download completes, when Marcus views the batch, then the batch status remains "approved" (it moves to "exported" only after Marcus confirms upload to bank).

**US-P2P-403: ABA File Export (Australia)**

As Marcus (AU AP clerk), I want to export a payment batch as an ABA (DE) file, so that I can upload it to ANZ/CommBank/NAB/Westpac without reformatting.

Acceptance criteria:
- Given an approved payment batch with ABA format selected, when Marcus clicks "Download ABA File", then the system generates a valid ABA (Direct Entry) file conforming to the Australian Payments Network DE format specification.
- Given the ABA file, when Marcus opens it, then it contains: (a) descriptive record (type 0) with reel sequence number, name of user institution, APCA number, description, and date; (b) detail records (type 1) per payment with BSB, account number, indicator, transaction code (50 = credit), amount in cents, account name (max 32 chars), lodgement reference, trace BSB and account; (c) file total record (type 7) with net total, credit total, debit total, count.
- Given a vendor with a missing BSB or account number, when export is triggered, then a validation error is shown for each incomplete vendor.

**US-P2P-404: GIRO File Export (Singapore)**

As Marcus (SG AP clerk), I want to export a payment batch as a GIRO file, so that I can upload it to DBS/POSB/OCBC/UOB for local SGD bulk payments.

Acceptance criteria:
- Given an approved payment batch with GIRO format selected, when Marcus clicks "Download GIRO File", then the system generates a valid GIRO IBG (Interbank GIRO) file in the format accepted by Singapore's major banks.
- Given the file, when Marcus opens it, then it contains: originator bank code, originator account, value date, and per-payment records with: beneficiary bank code, beneficiary account, amount in cents (SGD), and payment reference (max 20 chars).
- Given a vendor with a missing Singapore bank code or account number, when export is triggered, then a validation error identifies the incomplete vendor records.

**US-P2P-405: NEFT Batch File Export (India)**

As Marcus (IN AP clerk), I want to export a payment batch as a NEFT batch instruction file, so that I can upload it to HDFC/ICICI/SBI for bulk INR transfers without reformatting.

Acceptance criteria:
- Given an approved payment batch with NEFT format selected, when Marcus clicks "Download NEFT File", then the system generates a CSV/XML file in the format accepted by HDFC/ICICI NetBanking bulk upload (the two largest PS firm banks in India by coverage).
- Given the file, when Marcus opens it, then it contains per-payment: beneficiary name, IFSC code, account number, amount (in INR, 2 decimal places), payment purpose code, and narration (max 30 chars).
- Given a vendor with a missing IFSC code or account number, when export is triggered, then a validation error identifies the incomplete vendors.
- Given a payment batch with amounts in USD (foreign invoices), when NEFT export is requested, then the system warns: "NEFT only supports INR. Amounts will be exported in INR at today's FX rate. Confirm?"

**US-P2P-406: Vendor Banking Details**

As Marcus (AP clerk), I want to record and manage banking details for each vendor per-country, so that payment file exports always have the correct account data.

Acceptance criteria:
- Given a vendor contact detail page, when Marcus opens the "Banking Details" section, then he can add one or more bank accounts, each with: country, bank name, account number, routing code (sort code / BSB / bank code / IFSC depending on country), account type, and currency.
- Given Marcus adds a UK sort code, when he saves, then the system validates the sort code format (6 digits, optionally XX-XX-XX formatted) and rejects invalid values.
- Given Marcus adds a BSB (AU), when he saves, then the system validates BSB format (6 digits or XXX-XXX).
- Given Marcus adds an IFSC code (IN), when he saves, then the system validates IFSC format (4 alpha chars + 0 + 6 alphanumeric).

### 7.3 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R-F4-01 | New table `vendor_bank_accounts` for per-vendor per-country banking details | Must |
| R-F4-02 | `tenants` table: add `preferred_bank_format` column | Must |
| R-F4-03 | Smart default: set `preferred_bank_format` based on `tenants.country` (GB→BACS, AU→ABA, SG→GIRO, IN→NEFT, US→NACHA, others→CSV) | Must |
| R-F4-04 | `BacsExporter` service: generates BACS Standard 18 `.txt` file | Must |
| R-F4-05 | `AbaExporter` service: generates ABA Direct Entry file (Australian Payments Network spec) | Must |
| R-F4-06 | `GiroExporter` service: generates Singapore IBG GIRO file | Must |
| R-F4-07 | `NeftExporter` service: generates NEFT bulk upload CSV (HDFC/ICICI format) | Must |
| R-F4-08 | Pre-export validation: check all vendors in batch have required banking fields; return structured errors | Must |
| R-F4-09 | Settings → Payments → Bank Format selector with smart default | Must |
| R-F4-10 | Vendor banking details sub-section on vendor contact page | Must |
| R-F4-11 | Country-specific field validation (sort code, BSB, IFSC format checks) | Must |
| R-F4-12 | Multi-currency batch: prompt user to select format per currency or export separately | Should |
| R-F4-13 | Prahari security review required: banking details are sensitive PII | Must |
| R-F4-14 | Never log raw account numbers in application logs; mask as `****1234` | Must |

### 7.4 Data Model Changes

**New table: `vendor_bank_accounts`**

```sql
CREATE TABLE vendor_bank_accounts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  vendor_id       UUID NOT NULL REFERENCES clients(id),
  country         TEXT NOT NULL,                          -- ISO 3166-1 alpha-2
  bank_name       TEXT NOT NULL,
  account_name    TEXT NOT NULL,                          -- beneficiary name on account
  account_number  TEXT NOT NULL,                          -- stored encrypted at rest
  routing_code    TEXT,                                   -- sort code / BSB / bank code / IFSC
  account_type    TEXT DEFAULT 'checking'
    CHECK (account_type IN ('checking','savings','current')),
  currency        TEXT NOT NULL,
  is_default      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vendor_bank_accounts_vendor ON vendor_bank_accounts(tenant_id, vendor_id);
```

**Changes to `tenants` table:**

```sql
ALTER TABLE tenants ADD COLUMN preferred_bank_format TEXT DEFAULT 'csv'
  CHECK (preferred_bank_format IN ('nacha','bacs','aba','giro','neft','csv'));
```

**Security note:** `account_number` and `routing_code` must be encrypted at rest using Supabase vault or a symmetric key stored in environment config. Raw values are never returned in API list responses — only the last 4 digits. Full value returned only in the export generation path.

---

## 8. Feature: 1099 / Contractor Tracking (F5, US Market)

### 8.1 Problem Statement

US PS firms regularly pay independent contractors. IRS Form 1099-NEC must be filed for any contractor paid $600 or more in a calendar year. Currently firms track this in spreadsheets alongside their ERP. At year-end this becomes a scramble.

### 8.2 User Stories

**US-P2P-501: Flag Vendor as 1099 Contractor**

As Sarah (US firm owner), I want to flag certain vendors as 1099 contractors and record their tax information, so that the system can automatically track payments for year-end reporting.

Acceptance criteria:
- Given a vendor contact detail page, when Sarah opens "Tax Information", then she sees: (a) "1099 Vendor" toggle; (b) Tax ID (EIN or SSN/ITIN — masked after entry); (c) contractor type (Individual / Business entity); (d) Form W-9 received date.
- Given Sarah enables the 1099 toggle and enters a Tax ID, when she saves, then the vendor is flagged as `is_1099=true` and subsequent payments are tracked in the `contractor_payments_1099` view.
- Given the Tax ID field, when Sarah enters a value and saves, then the Tax ID is stored encrypted; only the last 4 digits are shown in the UI.

**US-P2P-502: Year-End 1099 Report**

As Sarah (US firm owner), I want a year-end report of all 1099 contractor payments, so that I can file accurate 1099-NEC forms without manually aggregating data.

Acceptance criteria:
- Given the Reports → Tax → 1099 Contractor Summary page, when Sarah selects a tax year (calendar year), then she sees a table: contractor name, Tax ID (masked), total paid (USD), payment method breakdown, and whether the $600 threshold has been met.
- Given a contractor paid $450 in the calendar year, when the report is viewed, then they are shown with a "Below $600 threshold — no 1099 required" indicator.
- Given a contractor paid $1,200 in the calendar year, when the report is viewed, then they are shown with a "1099 required" indicator and a "Export" button.
- Given Sarah clicks "Export to CSV", when the download completes, then the CSV contains: Payer name, Payer EIN, Recipient name, Recipient TIN (masked), Box 1 (nonemployee compensation), Box 4 (federal tax withheld, if any), Recipient address.

**US-P2P-503: Payment Tracking for 1099 Vendors**

As Marcus (AP clerk), I want all payments to 1099-flagged vendors to be automatically included in the year-end tracking, so that I do not have to manually maintain a separate log.

Acceptance criteria:
- Given a bill payment to a vendor with `is_1099=true`, when the payment is recorded (status=settled), then the payment is automatically included in the `contractor_payments_1099` materialized view for the relevant tax year.
- Given a payment in a foreign currency (e.g., USD equivalent of GBP payment), when tracked, then the 1099 amount is the USD equivalent at the date of payment (using the FX rate stored in `fx_rates`).
- Given a bill payment to a non-1099 vendor, when recorded, then no 1099 tracking entry is created.

### 8.3 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| R-F5-01 | `clients` table: add `is_1099`, `tax_id_encrypted`, `tax_id_type` ('ein'/'ssn'/'itin'), `contractor_type`, `w9_received_date` | Must |
| R-F5-02 | Tax ID stored encrypted; masked in all UI surfaces; full value never returned in API responses | Must |
| R-F5-03 | `contractor_payments_1099` view or materialized view: aggregate paid amounts per contractor per calendar year | Must |
| R-F5-04 | Reports → Tax → 1099 Contractor Summary page (US tenants only — gated by `tenants.country='US'`) | Must |
| R-F5-05 | Export to CSV with IRS-compatible fields | Must |
| R-F5-06 | $600 threshold indicator on the report | Must |
| R-F5-07 | Prahari security review: Tax ID encryption, access controls | Must |
| R-F5-08 | W-9 document upload (store in Supabase Storage as a `documents` row with doc_type='w9') | Should |

### 8.4 Data Model Changes

**Changes to `clients` table:**

```sql
ALTER TABLE clients ADD COLUMN is_1099                BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE clients ADD COLUMN tax_id_encrypted        TEXT;           -- AES-256 encrypted
ALTER TABLE clients ADD COLUMN tax_id_type             TEXT
  CHECK (tax_id_type IN ('ein','ssn','itin'));
ALTER TABLE clients ADD COLUMN contractor_type         TEXT
  CHECK (contractor_type IN ('individual','business'));
ALTER TABLE clients ADD COLUMN w9_received_date        DATE;
ALTER TABLE clients ADD COLUMN w9_document_id          UUID REFERENCES documents(id);
```

**New view: `contractor_payments_1099`**

```sql
CREATE VIEW contractor_payments_1099 AS
SELECT
  bp.tenant_id,
  c.id             AS vendor_id,
  c.name           AS vendor_name,
  c.tax_id_encrypted,
  c.tax_id_type,
  c.contractor_type,
  EXTRACT(YEAR FROM bp.payment_date)::INT AS tax_year,
  SUM(
    CASE
      WHEN b.currency = t.base_currency THEN bpi.amount
      ELSE bpi.amount * COALESCE(fx.rate, 1)  -- convert to USD equivalent
    END
  ) AS total_paid_usd,
  COUNT(DISTINCT bp.id) AS payment_count
FROM bill_payments bp
JOIN bill_payment_items bpi ON bpi.bill_payment_id = bp.id
JOIN bills b ON b.id = bpi.bill_id
JOIN clients c ON c.id = b.vendor_id
JOIN tenants t ON t.id = bp.tenant_id
LEFT JOIN fx_rates fx ON fx.from_currency = b.currency
  AND fx.to_currency = 'USD'
  AND fx.rate_date = bp.payment_date
WHERE bp.status = 'settled'
  AND c.is_1099 = TRUE
  AND t.country = 'US'
GROUP BY bp.tenant_id, c.id, c.name, c.tax_id_encrypted, c.tax_id_type, c.contractor_type, tax_year;
```

---

## 9. HITL Design Patterns for New Features

### 9.1 New Inbox Card Types

| Card Type | Trigger | Action Options | Agent Autonomy |
|-----------|---------|----------------|----------------|
| `recurring_schedule_proposal` | Detection worker finds pattern | Approve / Edit / Dismiss | L2 — propose only |
| `variance_review` | Recurring bill > 15% over avg | Review / Override approve / Flag for finance | L1 — human required |
| `discount_expiry_alert` | Discount deadline within 3 days | View Bill / Snooze | L2 — inform only |
| `multi_step_approval_request` | Bill routed to step N | Approve / Reject / Comment | L2 — human decides |
| `email_approval_confirmation` | High-value bill awaiting CFO | Approve (via email link) | L2 — human decides |

### 9.2 Agent Autonomy Levels Applied

| Feature | Agent Autonomy | Rationale |
|---------|----------------|-----------|
| Recurring pattern detection | Background process (no autonomy level) | SQL analysis — no AI action on user data |
| Recurring bill draft generation | L2 — generates draft, human approves | Money write operation requires HITL |
| Variance detection | L1 — human always required | Cost spike; override the normal flow |
| Discount alert | L2 — informs, does not act | Informational only |
| Approval routing | No autonomy — deterministic rules engine | Rule-based, not AI-driven |
| Payment batch with discount optimization | L2 — proposes batch with reasoning | Human approves every payment run |

### 9.3 Fallback Behaviors

| Feature | Primary Path | Fallback (Agent Unavailable) |
|---------|-------------|------------------------------|
| Recurring schedule Inbox card summary | LLM generates natural-language text | Template string: "Detected recurring bill from {vendor}: ~{amount}/{frequency}" |
| bill_pay_agent discount batch ordering | LLM proposes optimized batch | Bills sorted by due date; discount-eligible bills tagged but not reordered |
| Variance detection | SQL-level check (no LLM needed) | Always available; not dependent on LLM |

---

## 10. UX Flows

### 10.1 Recurring Bill Setup Flow

```
[FIRST TIME - Inbox Card]
Inbox notification: "Recurring Bill Pattern Detected"
  → Card shows: Vendor | Frequency | Avg Amount | Next Expected Date | Confidence
  → Actions: [Approve Schedule] [Edit] [Dismiss]
  
[APPROVE path]
  → Confirmation: "Monthly bill from AWS for ~$2,340 will be auto-generated on the 1st of each month."
  → Admin clicks OK
  → Schedule status = active
  → Next auto-generation on scheduled date

[EDIT path]
  → Drawer opens with editable fields: amount, frequency, start date, GL code, project
  → Admin edits and confirms
  → Schedule saved with admin-specified values

[VARIANCE - in monthly operation]
  → billing_run_worker generates draft bill
  → Vendor sends actual invoice ($3,100 vs expected $2,340)
  → vendor_invoice_agent extracts actual invoice → merges with recurring draft
  → Variance flag set → Inbox card: "AWS bill is 32% above expected. Review required."
  → Admin reviews and approves or rejects
```

### 10.2 Multi-Step Approval Flow (Two-Step Example)

```
Bill for $18,000 submitted (threshold: Tier 1 = $5,000, Tier 2 = $25,000)
  
  Step 1 → Marcus (AP Clerk role)
    - Inbox card: "Bill from Apex Staffing for $18,000 — Step 1 of 2"
    - Marcus reviews → clicks Approve
    - bill_approval_steps row: step_1, status=approved
  
  Step 2 → Sarah (Finance Manager role)
    - Inbox notification sent
    - Card: "Bill from Apex Staffing for $18,000 — Step 2 of 2 (Marcus approved Step 1)"
    - Sarah reviews → clicks Approve
    - bill_approval_steps row: step_2, status=approved
    - Bill status = approved
    - GL journal entry created (DR Expense / CR AP)
```

### 10.3 Native Bank File Export Flow

```
Pay Bills wizard
  → Step 1: Select bills
  → Step 2: Choose source bank account
  → Step 3: Review (bank format shown: "BACS" pre-selected for UK tenant)
  
  [On Review step]
  → Validation check runs:
    - All vendors have UK sort code + account number? ✓/✗
    - Errors shown inline: "Apex Ltd is missing sort code — [Fix Now]"
  
  → Admin fixes missing details inline (drawer opens for vendor)
  → Re-validate
  → Approve
  → "Download BACS File" button
  
  [After Download]
  → Modal: "Upload this file to your bank's payment portal, then click 'Mark as Sent' to confirm."
  → Admin clicks "Mark as Sent" → batch status = exported
  → Admin clicks "Confirm Settled" (with optional bank ref) → status = settled → GL journals created
```

---

## 11. Non-Goals

The following are explicitly out of scope for v1.1:

- PO / purchase order creation or three-way matching
- Vendor self-service invoice submission portal
- Vendor payment rail integrations (Stripe Connect to vendors, Plaid/Dwolla, Modern Treasury)
- ML-based duplicate invoice detection (insufficient data in v1)
- RTGS (India) — NEFT covers the use case for SME-scale amounts
- Multi-format export from a single batch (one format per batch export run)
- Form 1096 filing or e-file integration with IRS
- State-level tax withholding on 1099 payments
- BACS direct debit (collections from customers) — out of scope; this is AP only
- Vendor portal or web form for vendors to upload their own invoices
- Automatic bank reconciliation matching of BACS/ABA/GIRO/NEFT payment confirmations

---

## 12. Open Product Questions

| # | Question | Owner | Target |
|---|---------|-------|--------|
| Q1 | For multi-step approvals: should the rejection at Step 2 route back to Step 1, or void the bill? (Current proposal: route back to Step 1 with a comment, not void) | Netra + Vishwa | Before Vastu designs the schema |
| Q2 | GIRO file format: DBS and UOB have subtly different column orders. Should we generate one format per bank or a single "DBS-compatible" file? | Netra + Vastu | Sprint planning |
| Q3 | For 1099: should the W-9 upload be mandatory before flagging is_1099=true, or optional? (Proposal: optional — firms may receive it via mail) | Netra | Sprint planning |
| Q4 | Recurring bill detection: when a vendor's actual invoice arrives via email/upload and matches an active schedule, should we merge them into one bill or keep two rows? (Proposal: merge — update the recurring draft with extracted values) | Netra + Karya | Before implementation |
| Q5 | What happens if a recurring schedule's `next_bill_date` falls on a weekend or bank holiday? (Proposal: advance to next business day, using tenant.country for holiday calendar) | Vastu | Architecture review |
| Q6 | Multi-step approval for recurring bills: do recurring bills still go through the multi-step matrix? (Proposal: yes — the approval matrix applies to all bills regardless of source) | Netra | Before Aksha writes tests |

---

## 13. Success Metrics

| Metric | v1.1 Target | How Measured |
|--------|-------------|--------------|
| Recurring schedule adoption | ≥50% of tenants with 3+ recurring vendors activate at least one schedule within 30 days of the feature launch | Langfuse event: `recurring_schedule_approved` per tenant |
| Early-pay discount capture rate | Tenants using discount alerts capture ≥60% of available discounts within the window | `discount_captured` flag on bill_payments / `discount_deadline` passed |
| Multi-step approval adoption | ≥30% of tenants with >3 users configure at least one approval rule | `bill_approval_rules` count per tenant |
| BACS/ABA/GIRO/NEFT adoption | ≥80% of non-US tenants switch from Universal CSV to their native format within 60 days | `preferred_bank_format` setting + export event log |
| 1099 report generation (US) | ≥25% of US tenants generate the 1099 report before January 31 | `report_generated` event for type='1099' |
| Payment file validation error rate | <5% of payment exports have a validation error requiring manual fix | Error events on export endpoint |
| Time saved per payment run (qualitative) | Design partners report >15 minutes saved per run from native format | Design partner interviews |

---

## 14. Dependencies & Sequencing

### 14.1 Cross-Feature Dependencies

```
F4 (Native Bank Formats) → needs F1 data (recurring bills feed into batches)
F2 (Multi-Step Approval) → F1 bills go through F2 approval matrix
F3 (Payment Terms) → F4 payment exports use discount amounts for correct payment values
F5 (1099 Tracking) → needs F4 settled payments for accurate tracking
```

### 14.2 Team Sequencing

Following SDLC agent execution order:

1. **Vastu** — Architecture review + ADR for: (a) multi-step approval state machine, (b) bank account encryption, (c) recurring schedule FSM
2. **Chitra** — UX designs for: Inbox card variants, Approval Workflow settings page, Bank Format settings, Vendor Banking Details drawer
3. **Aksha** — Scenario documents + skeleton e2e tests for all 5 features
4. **Karya** — Backend implementation (migrations, services, agents, workers)
5. **Rupa** — Frontend (Angular components, new Inbox cards, settings pages)
6. **Vastu** — Post-implementation review
7. **Prahari** — Security review (bank account encryption, approval tokens, Tax ID encryption)
8. **Aksha** — Full regression suite
9. **Sthira** — Deploy + observability (new Procrastinate workers, Langfuse events)

### 14.3 Implementation Sequencing within v1.1

| Sprint | Features | Rationale |
|--------|---------|-----------|
| Sprint 1 | F3 (Payment Terms) + F2 (Multi-Step Approval) | Lower data model surface; immediate UX value; no new workers |
| Sprint 2 | F4 (Native Bank Formats) | Self-contained; unblocks non-US design partners |
| Sprint 3 | F1 (Recurring Bill Intelligence) | Needs F2 approval flow in place; new worker; most complex |
| Sprint 3 | F5 (1099 Tracking) | Can run parallel to F1 if bandwidth allows |

---

## 15. Security Considerations

Security review by Prahari is **mandatory** before implementation of:

- Vendor banking details (`vendor_bank_accounts`) — account numbers and routing codes are financial PII; encryption at rest required
- Multi-step approval email tokens — must use signed JWTs with short TTL; single-use; invalidated on bill void
- 1099 Tax IDs — EIN/SSN/ITIN are US federal tax IDs; PCI-adjacent sensitivity; must be encrypted at rest and masked in all API responses
- Never log raw account numbers, routing codes, or tax IDs in application logs
- RBAC enforcement on approval steps: role validation at the API layer, not just UI

---

## 16. Implementation Issue Checklist (for Vishwa to create)

After PRD approval, Vishwa to create implementation sub-issues:

| # | Title | Assignee | Type |
|---|-------|----------|------|
| I-1 | [Vastu] ADR: Multi-step approval state machine + bank account encryption | Vastu | spike |
| I-2 | [Chitra] UX designs: Recurring bill Inbox cards + Approval Workflow settings | Chitra | task |
| I-3 | [Aksha] Scenario docs + e2e skeleton: Advanced P2P v1.1 | Aksha | task |
| I-4 | [Karya] Migrations: recurring_bill_schedules, bill_approval_rules, bill_approval_steps, vendor_bank_accounts | Karya | task |
| I-5 | [Karya] Recurring bill detection worker + schedule management APIs | Karya | task |
| I-6 | [Karya] Multi-step approval engine + email confirmation flow | Karya | task |
| I-7 | [Karya] Payment terms on vendors + discount alert worker + bill_pay_agent discount optimization | Karya | task |
| I-8 | [Karya] Native bank format exporters: BACS, ABA, GIRO, NEFT | Karya | task |
| I-9 | [Karya] 1099 tracking: client table fields + report API + CSV export | Karya | task |
| I-10 | [Rupa] Frontend: Recurring schedule Inbox cards + Settings → Recurring Schedules | Rupa | task |
| I-11 | [Rupa] Frontend: Approval Workflow settings + multi-step approval Inbox cards | Rupa | task |
| I-12 | [Rupa] Frontend: Vendor Banking Details + Settings → Payments → Bank Format | Rupa | task |
| I-13 | [Rupa] Frontend: Vendor payment terms fields + discount alert card + 1099 report page | Rupa | task |
| I-14 | [Prahari] Security review: bank account encryption, approval tokens, Tax ID encryption | Prahari | task |
| I-15 | [Sthira] Register new Procrastinate workers; Langfuse events for new features | Sthira | task |

---

## Changelog

### [2026-06-20] — PRD created by Netra
- Initial PRD for Advanced P2P v1.1 in response to GitHub issue #217
- Covers: Recurring Bill Intelligence, Multi-Step Approval, Payment Terms & Discounts, Native Bank Formats, 1099 Tracking
- 5 features, 15 user stories, complete data model, agent behavior spec, phasing
- Awaiting Vishwa / Founder approval before implementation issues are created
