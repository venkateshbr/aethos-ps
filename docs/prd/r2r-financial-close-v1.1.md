# PRD: R2R — Balance Sheet, Cash Flow Statement & Financial Close Automation
**Version**: 1.1
**Status**: In Review — Awaiting Vishwa/Founder Approval
**Author**: Netra (PM)
**GitHub Issue**: #216
**Date**: 2026-06-20

---

## Table of Contents

1. [Overview & Motivation](#1-overview--motivation)
2. [User Personas](#2-user-personas)
3. [Current State & Gap Analysis](#3-current-state--gap-analysis)
4. [Feature Set Summary](#4-feature-set-summary)
5. [Feature 1 — Balance Sheet Report](#5-feature-1--balance-sheet-report)
6. [Feature 2 — Cash Flow Statement (Indirect Method)](#6-feature-2--cash-flow-statement-indirect-method)
7. [Feature 3 — Financial Close Automation (Close-Assist Agent + Wizard)](#7-feature-3--financial-close-automation-close-assist-agent--wizard)
8. [Feature 4 — Year-End Close (Income Summary & Retained Earnings Roll)](#8-feature-4--year-end-close-income-summary--retained-earnings-roll)
9. [Feature 5 — Manual Journal Audit Trail Enhancement](#9-feature-5--manual-journal-audit-trail-enhancement)
10. [Data Model Changes](#10-data-model-changes)
11. [Agent Behavior Spec — close_assist_agent](#11-agent-behavior-spec--close_assist_agent)
12. [UX Flow Descriptions](#12-ux-flow-descriptions)
13. [Phasing — v1.1 vs v1.2](#13-phasing--v11-vs-v12)
14. [Implementation Handoff — Issue Decomposition](#14-implementation-handoff--issue-decomposition)
15. [Acceptance Criteria Summary (Aksha Handoff)](#15-acceptance-criteria-summary-aksha-handoff)
16. [Open Questions](#16-open-questions)

---

## 1. Overview & Motivation

### Problem Statement

Aethos PS v1 ships with six operational reports — AR aging, AP aging, Project P&L, Utilization, WIP, and Revenue by Engagement. These are sufficient for day-to-day operations, but professional services firms — particularly those with 5+ employees, external investors, bank covenants, or audit requirements — need:

1. A **Balance Sheet** to understand net asset position at any point in time.
2. A **Cash Flow Statement** to see if profitability is translating to actual cash.
3. A **structured financial close process** so month-end isn't a chaotic scramble.
4. A **year-end close** that properly rolls net income into retained earnings.
5. A **complete audit trail** on manual journals for compliance and accountability.

Without these, Aethos PS cannot serve as the system of record for firms that have a Controller, an outside CPA, or any reporting obligation beyond their own team. We lose deals to QuickBooks and Xero solely because they produce a Balance Sheet.

### Why v1.1, Not v1?

These features require:
- A sufficiently complete Chart of Accounts with proper account type tagging (assets, liabilities, equity).
- At least one full operating period of posted transactions for the Cash Flow delta calculations to be meaningful.
- The Financial Close wizard depends on the AR/AP aging and WIP reports that ship in v1.

Design partners should be on the system for 4-8 weeks before close automation adds clear value. v1.1 is the right milestone.

### Agentic Principle

The close process in Aethos is not a manual checklist the user drills through alone. The `close_assist_agent` is proactive:
- It runs preliminary checks the moment the user initiates close.
- It tells the user what is incomplete before they have to look.
- It proposes standard accrual journal entries automatically.
- It surfaces risk ("4 time entries not yet approved — close may understate revenue by $4,800").
- It never blocks the close if the accountant explicitly overrides with a reason.

Human-in-control, AI-doing-the-work.

---

## 2. User Personas

### Persona A — The Firm Owner / Managing Partner
- Runs a 5–25 person consulting, advisory, or dev shop.
- Checks financials monthly; reviews with their CPA quarterly.
- Does not know GAAP deeply but understands P&L and cash position intuitively.
- Pain: "I have no idea if we're actually profitable once payroll clears."
- Goal: A clean Balance Sheet and Cash Flow they can email their CPA without embarrassment.

### Persona B — The Senior Accountant / Controller
- Handles month-end close for the firm (may be part-time or outsourced).
- Has QuickBooks or Xero experience; knows the month-end close checklist by heart.
- Pain: "Every month-end I'm chasing time entries, checking if bills are approved, and manually reconciling the sub-ledger to GL. It takes 3 days."
- Goal: An AI-guided close that surfaces what's missing before they have to hunt for it, cuts close time from 3 days to half a day.

### Persona C — The External CPA / Bookkeeper
- Serves multiple clients; may access Aethos PS via a client login.
- Needs audit-quality journal trails — who posted what, when, and why.
- Goal: Trust the GL. Have a clean audit trail for every manual entry. Export-ready reports.

---

## 3. Current State & Gap Analysis

| Capability | v1 State | Gap |
|---|---|---|
| Chart of Accounts (COA) | `accounts` table with `type` field (`asset`/`liability`/`equity`/`revenue`/`expense`) | No sub-type classification (current vs. non-current); no `is_contra` flag |
| GL Journals | Auto-posted via DB triggers; `accounting_guardian` validates | Present and working |
| Period Locks | `period_locks` table; API enforces | Present |
| AR/AP Aging | Available as v1 reports | Present |
| Project P&L | Available as v1 report | Present |
| WIP Report | Available as v1 report | Present |
| Balance Sheet | Not implemented | Missing |
| Cash Flow Statement | Not implemented | Missing |
| Financial Close Process | No structured close flow | Missing |
| Year-End Close entries | Not implemented | Missing |
| Manual Journal Audit Trail | Partial — reason field and `manual_journal.posted` event evidence implemented in #333 | Incomplete — no approval threshold, reversal workflow, or full state-change log |
| Retained Earnings account | Not seeded | Missing — must be seeded at tenant creation |

---

## 4. Feature Set Summary

| Feature | Priority | Ships In |
|---|---|---|
| F1: Balance Sheet Report | Must | v1.1 |
| F2: Cash Flow Statement (Operating only, indirect method) | Must | v1.1 |
| F3: Financial Close Automation (wizard + close_assist_agent) | Must | v1.1 |
| F4: Year-End Close (closing entries) | Must | v1.1 |
| F5: Manual Journal Audit Trail Enhancement | Must | v1.1 |
| F6: Cash Flow — Investing Activities | Should | v1.2 |
| F7: Cash Flow — Financing Activities | Should | v1.2 |
| F8: Consolidated P&L + BS across currency (multi-entity) | Could | v1.2 |
| F9: Comparative periods on Balance Sheet | Could | v1.2 |
| F10: Automated accrual schedules (recurring) | Could | v1.2 |

---

## 5. Feature 1 — Balance Sheet Report

### 5.1 User Stories

**US-BS-01**: As a **firm owner**, I want to view a Balance Sheet as of any date so that I can understand my firm's net asset position and share it with my CPA at quarter-end.

**US-BS-02**: As a **senior accountant**, I want the Balance Sheet to pull directly from posted GL journal lines (no separate calculation table) so that it always agrees to the general ledger without reconciliation.

**US-BS-03**: As a **firm owner**, I want retained earnings on the Balance Sheet to reflect prior years' accumulated earnings plus current year net income, so that equity always balances.

**US-BS-04**: As a **senior accountant**, I want to export the Balance Sheet to PDF and CSV so that I can share it with stakeholders and import it into external tools.

**US-BS-05**: As a **firm owner** operating in multiple currencies, I want Balance Sheet amounts displayed in my tenant's base currency (FX-converted) so that the report is coherent even when some transactions are in foreign currency.

### 5.2 Functional Requirements

**FR-BS-01** The Balance Sheet is calculated as of a user-selected date (default: today). It uses `journal_lines.base_amount` (already FX-converted at posting time) for all aggregations.

**FR-BS-02** Account classification hierarchy:
```
Assets
  Current Assets
    Cash & Equivalents        (account.type=asset, sub_type=cash)
    Accounts Receivable       (account.type=asset, sub_type=accounts_receivable)
    Unbilled Revenue / WIP    (account.type=asset, sub_type=wip)
    Prepaid Expenses          (account.type=asset, sub_type=prepaid)
    Other Current Assets      (account.type=asset, sub_type=other_current_asset)
  Non-Current Assets
    Fixed Assets              (account.type=asset, sub_type=fixed_asset)
    Accumulated Depreciation  (account.type=asset, sub_type=accumulated_depreciation, is_contra=true)
    Other Non-Current Assets  (account.type=asset, sub_type=other_noncurrent_asset)
Total Assets

Liabilities
  Current Liabilities
    Accounts Payable          (account.type=liability, sub_type=accounts_payable)
    Accrued Expenses          (account.type=liability, sub_type=accrued_expense)
    Deferred Revenue          (account.type=liability, sub_type=deferred_revenue)
    Other Current Liabilities (account.type=liability, sub_type=other_current_liability)
  Long-Term Liabilities
    Long-Term Debt            (account.type=liability, sub_type=long_term_debt)
    Other Long-Term           (account.type=liability, sub_type=other_longterm_liability)
Total Liabilities

Equity
  Owner's Capital / Paid-In Capital  (account.type=equity, sub_type=paid_in_capital)
  Retained Earnings (prior periods)  (system account — see §10)
  Net Income (current period)        (calculated: revenue accounts minus expense accounts for period)
Total Equity

Total Liabilities + Equity (must equal Total Assets ± $0.01 rounding)
```

**FR-BS-03** Net Income on the Balance Sheet is the sum of all revenue account balances minus all expense account balances for journal lines posted since the last year-end close (or since tenant inception if never closed). This is a live calculation, not a cached value.

**FR-BS-04** Retained Earnings displayed on the Balance Sheet = the balance of the `retained_earnings` system account (account code `3900` by convention). This account accumulates via year-end close entries only (see F4).

**FR-BS-05** The Balance Sheet must include a balancing check: if `Total Assets - Total Liabilities - Total Equity > $0.01`, display a warning banner: "Balance Sheet is out of balance by [amount]. Contact support or check for unposted journals." This condition should never occur in normal operation (accounting_guardian ensures balanced journals) but is a safety display.

**FR-BS-06** The report title includes the tenant name and "As of [Date]" to match professional presentation standards.

**FR-BS-07** Export: PDF (Resend-templated or browser print) and CSV (two columns: account name, balance). PDF must include tenant logo if set on the tenant record.

**FR-BS-08** The Balance Sheet page shows a "Last calculated" timestamp. It is recalculated on page load (no stale cache). For large tenants (> 50,000 journal lines), the query is served via a Supabase materialized view refreshed on journal post.

### 5.3 Acceptance Criteria

**AC-BS-01** Given a tenant with posted journal entries, when I navigate to Reports > Balance Sheet and select today's date, then I see assets, liabilities, and equity sections with correct balances sourced from `journal_lines`.

**AC-BS-02** Given a Balance Sheet as of date D, when Total Assets != Total Liabilities + Total Equity by more than $0.01, then a warning banner is displayed.

**AC-BS-03** Given a year-end close was completed for year Y, when I view the Balance Sheet at the start of year Y+1, then Retained Earnings reflects the closed net income from year Y and Net Income (current year) starts at zero.

**AC-BS-04** Given a multi-currency tenant with transactions in USD and GBP, when I view the Balance Sheet, then all amounts are in the tenant's base currency using the `base_amount` field from `journal_lines`.

**AC-BS-05** Given I click "Export PDF", then a PDF downloads with tenant name, "Balance Sheet as of [date]", and all three sections.

**AC-BS-06** Given I click "Export CSV", then a CSV downloads with columns: section, account_name, account_code, balance.

---

## 6. Feature 2 — Cash Flow Statement (Indirect Method)

### 6.1 User Stories

**US-CF-01**: As a **firm owner**, I want a Cash Flow Statement for any period so that I can see whether profitability is converting to actual cash and understand why cash changed.

**US-CF-02**: As a **senior accountant**, I want the Cash Flow Statement to use the indirect method (start from net income, adjust for non-cash items and working capital) so that it is consistent with GAAP presentation and my CPA's expectations.

**US-CF-03**: As a **firm owner**, I want the Cash Flow Statement limited to Operating Activities in v1.1 so that I get the most decision-relevant view without waiting for Investing/Financing to be built.

**US-CF-04**: As a **senior accountant**, I want to select a date range (month, quarter, YTD, custom) so that I can analyze cash flow for the period I care about.

### 6.2 Functional Requirements — Operating Activities (v1.1 Scope)

**FR-CF-01** The Cash Flow Statement covers a user-selected period (start date, end date). Default: current month to date.

**FR-CF-02** Indirect method construction:

```
Operating Activities
  Net Income                                    [P&L: Revenue – Expense for period]

  Adjustments for non-cash items:
    Depreciation & Amortization               [sum of journal_lines for accounts with sub_type=accumulated_depreciation]
    Other non-cash adjustments (if any)       [journal_lines tagged as non_cash on the account]

  Changes in Working Capital:
    (Increase)/Decrease in Accounts Receivable [AR balance change: start of period vs end of period]
    Increase/(Decrease) in Accounts Payable    [AP balance change: start of period vs end of period]
    (Increase)/Decrease in Prepaid Expenses    [Prepaid balance change]
    Increase/(Decrease) in Accrued Expenses    [Accrued liabilities balance change]
    Increase/(Decrease) in Deferred Revenue    [Deferred revenue balance change]
    Other working capital changes              [Any current asset/liability not above]

Net Cash from Operating Activities            [Sum of above]

[Investing Activities — placeholder with "Coming in v1.2"]
[Financing Activities — placeholder with "Coming in v1.2"]

Net Increase/(Decrease) in Cash              [= Net Cash from Operating (v1.1)]
Beginning Cash Balance                        [Cash accounts at start of period]
Ending Cash Balance                           [Cash accounts at end of period]

Verification: Ending – Beginning should equal Net Increase/(Decrease).
If discrepancy > $0.01, show warning: "Cash reconciliation gap of [amount] — may be due to Investing or Financing activities not yet captured."
```

**FR-CF-03** All calculations use `journal_lines.base_amount` (FX-converted). Foreign currency translation gains/losses from AR/AP are classified as working capital adjustments.

**FR-CF-04** "Changes in working capital" are computed as: (account balance at period end) minus (account balance at period start). Positive working capital asset change = cash used (negative). Positive working capital liability change = cash generated (positive). The system applies the correct sign convention automatically.

**FR-CF-05** Account sub-type mapping drives the classification. `accounts.sub_type` is the single source of truth. The system does not hardcode account codes — it relies on sub_type tags.

**FR-CF-06** A "Reconciliation note" is displayed: "Investing and Financing activities are not yet captured. Cash changes from loans, owner draws, or asset purchases will show as a reconciliation gap."

**FR-CF-07** Export: PDF and CSV (same pattern as Balance Sheet).

**FR-CF-08** The `reporting_agent` can answer natural-language queries about the Cash Flow: "Why did our cash drop $20k in March?" and will reference the Cash Flow Statement line items in its response.

### 6.3 Acceptance Criteria

**AC-CF-01** Given a tenant with AR, AP, and revenue transactions, when I view the Cash Flow Statement for a period, then Net Income equals the P&L report net income for the same period.

**AC-CF-02** Given AR increased by $10,000 during the period, when I view the Cash Flow Statement, then "(Increase) in Accounts Receivable" shows $(10,000) as a use of cash.

**AC-CF-03** Given Ending Cash – Beginning Cash ≠ Net Cash from Operating within $0.01, then a reconciliation warning is displayed.

**AC-CF-04** Given Investing and Financing placeholders are shown, when I click on them, then a tooltip says "Investing and Financing activities are coming in v1.2."

**AC-CF-05** Given I export to CSV, then the CSV has columns: section, line_item, amount, and includes all three activity sections (Operating, Investing placeholder, Financing placeholder).

---

## 7. Feature 3 — Financial Close Automation (Close-Assist Agent + Wizard)

### 7.1 User Stories

**US-CL-01**: As a **senior accountant**, I want to click "Begin Close" for a period and have the system immediately tell me everything that needs attention before I can close, so that I don't spend 2 hours manually hunting for incomplete items.

**US-CL-02**: As a **senior accountant**, I want the close-assist agent to propose accrual journal entries for incomplete items (e.g. unbilled time, unpaid vendor bills) so that I can approve them with one click rather than creating them manually.

**US-CL-03**: As a **firm owner**, I want to see a close health score ("3 of 7 checks passed") so that I know at a glance how close we are to being able to lock the period.

**US-CL-04**: As a **senior accountant**, I want to override any failing check (with a mandatory reason) and proceed to period lock anyway, so that I am never held hostage by the system when I have a business reason to close.

**US-CL-05**: As a **senior accountant**, I want to see a summary of what I approved or overrode during close, so that I have a record for audit purposes.

**US-CL-06**: As a **firm owner**, I want to receive a notification when a period is successfully locked, so that I know the books are closed.

### 7.2 Close Checklist — Agent-Driven Gates

The `close_assist_agent` runs all checks when the user clicks "Begin Close". Each check is either BLOCKING (must resolve or explicitly override) or INFORMATIONAL (surfaced but does not block close).

| Check ID | Description | Type | Agent Action |
|---|---|---|---|
| CK-01 | All time entries for the period are approved | Blocking | Lists unapproved entries; proposes batch-approve action |
| CK-02 | No unbilled WIP on active engagements for the period | Informational | Shows WIP amount; proposes "Bill Now" or "Defer to next period" |
| CK-03 | All vendor bills received for the period are approved | Blocking | Lists draft/pending bills; links to Bills page |
| CK-04 | No vendor invoices stuck in extraction (failed or extracting) | Informational | Lists stuck documents; offers "Re-extract" or "Mark as irrelevant" |
| CK-05 | AR sub-ledger balance equals GL AR account balance | Blocking | Shows discrepancy if any; proposes correcting journal entry |
| CK-06 | AP sub-ledger balance equals GL AP account balance | Blocking | Shows discrepancy if any; proposes correcting journal entry |
| CK-07 | No manual journals in draft state for the period | Blocking | Lists unposted manual journals; offers "Post All" or "Discard" |
| CK-08 | Bank account balance reconciled (if bank balance entered) | Informational | Prompts user to enter bank statement balance; calculates unreconciled items |
| CK-09 | FX rates current (not older than 3 days) for all currencies used | Informational | Warns if stale; triggers `fx_refresh_worker` |
| CK-10 | Deferred revenue scheduled releases are posted | Informational | Lists unposted scheduled releases; proposes batch-post |

**FR-CL-01** The `close_assist_agent` runs all 10 checks in parallel (async) when "Begin Close" is clicked. It streams results to the wizard UI as checks complete — the user sees a live checklist populating.

**FR-CL-02** For each failed blocking check, the agent produces:
- A plain-English summary of the problem and its financial impact ("4 time entries totalling 12 hours at $150/hr = $1,800 in potential revenue not captured").
- A primary action button (the AI-recommended resolution).
- A secondary "Override with reason" button.

**FR-CL-03** Accrual proposals: for CK-01 (unapproved time) and CK-10 (deferred revenue), the agent generates draft journal entries in `agent_suggestions` with `suggestion_type=draft_journal`. These appear as approve/reject cards inline in the wizard. Approval materializes the journal and re-runs the affected check.

**FR-CL-04** Override flow: when the user clicks "Override", a modal requires a free-text reason (minimum 10 characters). The override is logged to `manual_journal_audit_log` with `action=close_override`, the check ID, the reason, and the user ID.

**FR-CL-05** The close wizard has three steps:
- Step 1: Pre-close checks (the agent runs and displays results).
- Step 2: Review & resolve (user works through each failing check: approve AI proposal, take manual action, or override).
- Step 3: Period lock confirmation (shows a final summary, asks for confirmation, then calls `POST /accounting/period-locks`).

**FR-CL-06** The period lock confirmation screen shows:
- Period being locked (e.g. "May 2026").
- Number of checks passed / overridden.
- Total revenue and expenses for the period (from P&L).
- Name of the user locking the period.
- "Lock Period" button (requires `role=admin` or `role=owner`).

**FR-CL-07** After lock, the system sends an in-app notification to all users with `role=owner` and `role=admin`: "May 2026 period locked by [User] on [Date]. [N] items were overridden."

**FR-CL-08** RBAC: only `role=owner` and `role=admin` may initiate close and lock a period. `role=member` sees a read-only view of close status.

### 7.3 Acceptance Criteria

**AC-CL-01** Given I click "Begin Close" for a period, then all 10 checks run within 10 seconds and stream results to the UI one by one as they complete.

**AC-CL-02** Given CK-01 fails (unapproved time entries exist), then the agent shows the count, total hours, and estimated revenue impact, and offers a "Approve All" button.

**AC-CL-03** Given CK-05 fails (AR sub-ledger ≠ GL AR), then the agent shows the discrepancy amount and offers a draft journal entry to correct it.

**AC-CL-04** Given I override a blocking check, then a reason field is required (enforced client-side and server-side). The override is recorded with my user ID, timestamp, check ID, and reason.

**AC-CL-05** Given all checks are passed or overridden, when I click "Lock Period", then the period lock is created and I cannot post any journal with an entry_date in that period.

**AC-CL-06** Given a period is locked, when another user tries to post a journal in that period via the API, then a 409 Conflict is returned with message "Period [start]–[end] is locked."

**AC-CL-07** Given `role=member`, when I navigate to Financial Close, then I see the close status (checklist items) but no "Begin Close" or "Lock Period" buttons.

**AC-CL-08** Given I am on the close wizard Step 2 and I approve an AI-proposed accrual journal, then the journal is posted, the affected check is re-evaluated, and the check turns green within 3 seconds.

---

## 8. Feature 4 — Year-End Close (Income Summary & Retained Earnings Roll)

### 8.1 User Stories

**US-YE-01**: As a **senior accountant**, I want to run a year-end close that automatically creates the closing journal entry (zeroing out P&L accounts and rolling net income to retained earnings) so that the new fiscal year starts with a clean P&L.

**US-YE-02**: As a **firm owner**, I want the system to warn me before running year-end close (since it is irreversible without a reversing entry) so that I don't accidentally close the wrong year.

**US-YE-03**: As a **senior accountant**, I want to be able to view historical Balance Sheets (as of the last day of a closed year) so that I can see prior-year financials correctly.

### 8.2 Functional Requirements

**FR-YE-01** Year-end close is a special close that is only available when the final period of the fiscal year is locked. The system determines the fiscal year based on `tenants.fiscal_year_start` (default: January 1).

**FR-YE-02** The year-end close creates one journal entry (`source=year_end_close`) with the entry date set to the last day of the fiscal year:
```
For each revenue account with a non-zero balance:
  DR <Revenue Account> [balance amount]
  CR Income Summary    [balance amount]

For each expense account with a non-zero balance:
  DR Income Summary    [balance amount]
  CR <Expense Account> [balance amount]

Then net Income Summary balance:
  If net income (revenue > expense):
    DR Income Summary           [net income]
    CR Retained Earnings (3900) [net income]
  If net loss (expense > revenue):
    DR Retained Earnings (3900) [net loss]
    CR Income Summary           [net loss]
```

**FR-YE-03** "Income Summary" is a temporary equity account (system account, code `3800`) created automatically at tenant setup. It is used only during year-end close and should have a zero balance after close completes.

**FR-YE-04** After year-end close, the system automatically locks the full fiscal year period (if not already locked) so no adjusting entries can be made without an explicit override.

**FR-YE-05** Year-end close posts only after a multi-step confirmation: (1) user reviews the proposed closing journal entry in the close_assist_agent wizard; (2) user types the year to confirm (e.g. "2025"); (3) system posts the entry.

**FR-YE-06** Roll-forward: the Balance Sheet's "Retained Earnings" line now shows the running balance of account 3900, which includes all prior year-end close entries.

**FR-YE-07** Year-end close is restricted to `role=owner` only.

**FR-YE-08** The `accounting_guardian` validates the closing journal entry before posting (debits = credits; all accounts valid; period not already locked by a year-end close).

### 8.3 Acceptance Criteria

**AC-YE-01** Given all periods for fiscal year 2025 are locked, when I run year-end close, then a closing journal entry is created that zeros all P&L accounts and credits Retained Earnings with the net income amount.

**AC-YE-02** Given the closing journal entry is posted, when I view the Balance Sheet as of Dec 31 2025, then Net Income (current year) shows $0 and Retained Earnings reflects the 2025 net income.

**AC-YE-03** Given the closing journal entry is posted, when I view the P&L for Jan 1 2026 onwards, then all revenue and expense accounts start at zero.

**AC-YE-04** Given I try to run year-end close when any period of the fiscal year is not locked, then the system blocks with: "Cannot run year-end close — [N] periods in fiscal year 2025 are not locked."

**AC-YE-05** Given I try to run year-end close without confirming the year (typing "2025"), then the "Confirm Close" button remains disabled.

**AC-YE-06** Given a net loss year (expenses > revenue), when I run year-end close, then Retained Earnings is debited (reduced) by the loss amount.

---

## 9. Feature 5 — Manual Journal Audit Trail Enhancement

*This feature enhances the existing manual journal capability (related to #204 / #208).*

Implementation note 2026-06-25: #333 implements the first audit slice:
`journal_entries.reason`, required service/API/UI reason capture for manual
journals, immutable `manual_journal.posted` financial-event evidence, and Inbox
compatibility for older AI draft-journal proposals. Threshold approval,
rejection workflow, reversal workflow, and full state-transition audit remain
future slices.

### 9.1 User Stories

**US-MJ-01**: As a **senior accountant**, I want every manual journal to require a reason/memo field so that the audit trail is complete and the CPA always knows why an entry was made.

**US-MJ-02**: As a **firm owner**, I want manual journals above a configurable dollar threshold to require admin approval before posting so that no one can make large unauthorized GL adjustments.

**US-MJ-03**: As an **external CPA**, I want a complete audit log showing who created, edited, approved, and posted every manual journal entry, with timestamps, so that I can satisfy audit requirements.

**US-MJ-04**: As a **firm owner**, I want to configure the approval threshold (default $10,000) in Settings so that it fits my firm's internal controls.

### 9.2 Functional Requirements

**FR-MJ-01** `journal_entries` with `source=manual` require a non-empty `reason` field (max 500 characters) on the POST request. The API returns 422 if reason is absent or blank.

**FR-MJ-02** A new `manual_journal_audit_log` table records every state change to a manual journal entry (see §10 for schema). Events recorded: `created`, `edited`, `submitted_for_approval`, `approved`, `rejected`, `posted`, `reversed`, `close_override`.

**FR-MJ-03** Approval threshold: if a manual journal's total debit amount exceeds `tenants.manual_journal_approval_threshold` (default 10,000.00 in tenant base currency), then:
- The journal is created in `status=pending_approval`.
- A `hitl_task` of kind `approve_manual_journal` is created, assigned to users with `role=admin` or `role=owner`.
- The submitting user cannot self-approve.
- If the submitter is already `role=owner`, approval is still required from a second `role=owner` if one exists, or the system logs a single-approver exception.

**FR-MJ-04** Journals below the threshold are created in `status=draft` and can be self-posted by the submitter (if they have `role=admin` or higher).

**FR-MJ-05** Rejected manual journals: the approver must supply a rejection reason (required). The journal moves to `status=rejected` and the submitter is notified in-app.

**FR-MJ-06** The Journal Entry detail screen shows a full timeline: created by X at T1, submitted for approval at T2, approved by Y at T3, posted at T4. Each event shows the user's display name and timestamp.

**FR-MJ-07** A "Manual Journals" filter in the GL Journal list (Reports > GL Journal) allows filtering to `source=manual` and filtering by `status` (draft / pending_approval / approved / posted / rejected / reversed).

**FR-MJ-08** The `tenants.manual_journal_approval_threshold` is configurable in Settings > Accounting > Internal Controls. Only `role=owner` can change it.

### 9.3 Acceptance Criteria

**AC-MJ-01** Given I create a manual journal without a reason field, then the API returns 422 Unprocessable Entity with error "Reason is required for manual journal entries."

**AC-MJ-02** Given I create a manual journal with total debits of $15,000 and the threshold is $10,000, then the journal is created with `status=pending_approval` and a HITL task appears in the approver's inbox.

**AC-MJ-03** Given I create a manual journal with total debits of $5,000, then the journal is created with `status=draft` and I can post it immediately.

**AC-MJ-04** Given an approver rejects a manual journal without supplying a reason, then the API returns 422.

**AC-MJ-05** Given a manual journal is posted, when I view its detail screen, then the full audit timeline shows all state changes with user names and timestamps.

**AC-MJ-06** Given I filter GL Journal by source=manual, then only manual journal entries are shown (not trigger-generated entries from invoices, payments, etc.).

**AC-MJ-07** Given `role=owner` changes the approval threshold to $25,000, then subsequent manual journals under $25,000 do not require approval.

---

## 10. Data Model Changes

### 10.1 New Field: `accounts.sub_type`

```sql
ALTER TABLE accounts ADD COLUMN sub_type TEXT;
-- Allowed values:
-- Assets: cash, accounts_receivable, wip, prepaid, other_current_asset,
--         fixed_asset, accumulated_depreciation, other_noncurrent_asset
-- Liabilities: accounts_payable, accrued_expense, deferred_revenue,
--              other_current_liability, long_term_debt, other_longterm_liability
-- Equity: paid_in_capital, retained_earnings, income_summary, other_equity
-- Revenue: operating_revenue, other_revenue
-- Expense: cost_of_services, operating_expense, depreciation, other_expense
```

### 10.2 New Field: `accounts.is_contra`

```sql
ALTER TABLE accounts ADD COLUMN is_contra BOOLEAN NOT NULL DEFAULT FALSE;
-- True for: accumulated_depreciation, contra-revenue accounts (discounts, returns)
-- Controls sign inversion on Balance Sheet display
```

### 10.3 New System Accounts (seeded at tenant creation)

```sql
-- These are added to the COA seed migration alongside existing system accounts:
INSERT INTO accounts (tenant_id, code, name, type, sub_type, is_system)
VALUES
  (tenant_id, '3800', 'Income Summary', 'equity', 'income_summary', TRUE),
  (tenant_id, '3900', 'Retained Earnings', 'equity', 'retained_earnings', TRUE);
-- For existing tenants (migration):
-- Run a data migration to insert these accounts for tenants where they don't exist.
```

### 10.4 New Field: `journal_entries.reason`

```sql
ALTER TABLE journal_entries ADD COLUMN reason TEXT;
-- Required (NOT NULL enforced at API layer, not DB — some trigger-generated entries
-- will populate a system reason: 'Auto-posted: invoice_sent', etc.)
-- Manual journals: enforced non-empty at service layer.
```

### 10.5 New Field: `journal_entries.status`

```sql
ALTER TABLE journal_entries ADD COLUMN status TEXT NOT NULL DEFAULT 'posted';
-- Values: draft | pending_approval | approved | posted | rejected | reversed
-- Trigger-generated journals always go direct to 'posted'.
-- Manual journals follow the approval workflow.
```

### 10.6 New Table: `manual_journal_audit_log`

```sql
CREATE TABLE manual_journal_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  journal_entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  -- Values: created | edited | submitted_for_approval | approved | rejected |
  --         posted | reversed | close_override
  performed_by_user_id UUID NOT NULL REFERENCES users(id),
  performed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reason TEXT,           -- Required for: rejected, close_override
  from_status TEXT,
  to_status TEXT,
  metadata JSONB         -- For 'edited': {fields_changed: [...], before: {...}, after: {...}}
);
-- RLS: tenant_id = current_setting('app.current_tenant_id')::UUID
CREATE INDEX ON manual_journal_audit_log (tenant_id, journal_entry_id);
CREATE INDEX ON manual_journal_audit_log (tenant_id, performed_at DESC);
```

### 10.7 New Field: `tenants.manual_journal_approval_threshold`

```sql
ALTER TABLE tenants ADD COLUMN manual_journal_approval_threshold NUMERIC(15,2) NOT NULL DEFAULT 10000.00;
ALTER TABLE tenants ADD COLUMN fiscal_year_start DATE NOT NULL DEFAULT '2025-01-01';
-- fiscal_year_start: day-of-year anchor (day and month used; year ignored).
-- Default Jan 1 covers most markets. UK tax year (Apr 6) and Indian FY (Apr 1) configurable.
```

### 10.8 New Field: `tenants.fiscal_year_start`

Already included in 10.7. `fiscal_year_start` stores the day+month of fiscal year start. At close wizard initialization, the system computes the current fiscal year bounds by combining `fiscal_year_start.month` and `fiscal_year_start.day` with the current calendar year.

### 10.9 Close Run Tracking: `period_close_runs`

```sql
CREATE TABLE period_close_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  close_type TEXT NOT NULL DEFAULT 'monthly',  -- monthly | year_end
  initiated_by_user_id UUID NOT NULL REFERENCES users(id),
  initiated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  locked_at TIMESTAMPTZ,
  locked_by_user_id UUID REFERENCES users(id),
  checks_passed INT NOT NULL DEFAULT 0,
  checks_overridden INT NOT NULL DEFAULT 0,
  checks_total INT NOT NULL DEFAULT 10,
  override_log JSONB,  -- Array of {check_id, reason, user_id, at}
  status TEXT NOT NULL DEFAULT 'in_progress',  -- in_progress | locked | abandoned
  year_end_journal_entry_id UUID REFERENCES journal_entries(id)
);
-- RLS: tenant_id = current_setting('app.current_tenant_id')::UUID
```

---

## 11. Agent Behavior Spec — close_assist_agent

### 11.1 Agent Identity

```python
# Agent registration (backend/app/agents/close_assist_agent.py)
close_assist_agent = Agent(
    name="close_assist_agent",
    model=AethosBedrock("claude-sonnet-4-6"),  # or Anthropic direct
    deps_type=CloseAssistDeps,  # tenant_id, period_start, period_end, user_id
    result_type=CloseCheckResult,
    system_prompt=CLOSE_ASSIST_SYSTEM_PROMPT,
)
# Autonomy: L2 (suggest) for all proposals. Posting only happens on explicit human approval.
# Exception: accounting_guardian runs at L3 on the proposed journal to validate before suggestion is surfaced.
```

### 11.2 Tools Available to close_assist_agent

| Tool | Purpose |
|---|---|
| `get_unapproved_time_entries(period_start, period_end)` | Returns list of time entries with `status != approved` for the period |
| `get_unbilled_wip(period_start, period_end)` | Returns WIP by engagement for the period |
| `get_pending_bills(period_start, period_end)` | Returns bills in draft/pending status with due dates in period |
| `get_stuck_documents(period_start, period_end)` | Returns documents in `status=extracting` or `status=failed` uploaded during period |
| `get_ar_subledger_balance(as_of_date)` | Sum of open invoice balances |
| `get_gl_account_balance(account_type, sub_type, as_of_date)` | GL balance for an account group |
| `get_draft_manual_journals(period_start, period_end)` | Manual journals in `status=draft` or `pending_approval` |
| `propose_accrual_journal(description, debit_account_id, credit_account_id, amount)` | Creates a `draft_journal` agent_suggestion for human approval |
| `get_fx_rate_freshness(currencies)` | Returns last refresh timestamps for each currency |
| `get_deferred_revenue_releases(period_start, period_end)` | Returns scheduled deferred revenue releases not yet posted |

### 11.3 System Prompt (condensed — full version in agent file)

```
You are the Close Assist Agent for Aethos PS. You help accountants complete their
month-end close efficiently and accurately.

When asked to run pre-close checks for a period:
1. Run all 10 checks concurrently using your tools.
2. For each failing check, explain the issue in plain English.
3. Quantify the financial impact where possible (dollar amounts, not just counts).
4. Propose the most direct resolution as your primary recommendation.
5. If a resolution involves posting a journal entry, draft it precisely
   (correct accounts, amounts, and memo) and present it for human approval.
   Never post journals autonomously — always surface for HITL approval.
6. Surface risks clearly: "If you close without resolving this, [consequence]."
7. Never threaten or refuse to let the close proceed —
   the accountant may override any check with a reason.
8. After all checks are surfaced, calculate a close health score:
   "[N of 10] checks ready."
9. Always be concise — the accountant has limited time.
   Use bullet points, not paragraphs.

Tone: professional, direct, helpful. Not alarmist. Not passive.
```

### 11.4 Sample Agent Output (CK-01 — Unapproved Time Entries)

```
Check CK-01 — Time Entry Approval
Status: NEEDS ATTENTION

4 time entries totalling 16.5 hours are not yet approved for May 2026.
Estimated unbilled revenue impact: $2,475 (at blended rate $150/hr).

Affected entries:
  · Acme Corp — Discovery Phase — 6h (May 28) — submitted by J. Torres
  · Beta Inc — Development — 5h (May 29) — submitted by A. Patel
  · Beta Inc — Development — 3.5h (May 30) — submitted by A. Patel
  · Gamma LLC — Strategy — 2h (May 31) — submitted by J. Torres

Recommended action: Approve all 4 entries.
[Approve All 4 Time Entries] [Review Individually] [Override with Reason]

Risk if overridden: May P&L will understate revenue by ~$2,475.
Next billing run will pick up these entries if approved before billing.
```

### 11.5 Sample Agent Output (CK-05 — AR Sub-Ledger Reconciliation Failure)

```
Check CK-05 — AR Sub-Ledger vs GL Reconciliation
Status: ACTION REQUIRED (BLOCKING)

AR Sub-ledger (open invoices): $84,200.00
GL Accounts Receivable balance: $83,950.00
Discrepancy: $250.00

This is likely a void-payment timing issue. I've drafted a correcting journal entry:
  DR Accounts Receivable    $250.00  |  Memo: AR reconciliation adjustment May 2026
  CR Suspense Account       $250.00  |

[Approve Correcting Journal] [Investigate Manually] [Override with Reason]

Note: If you're unsure of the cause, investigate first — a $250 discrepancy
on $84k AR is 0.3% and may be a recent payment not yet reconciled.
```

### 11.6 Agent Confidence & Fallback

- All `close_assist_agent` proposals are surfaced as `agent_suggestions` with `status=pending`.
- The agent assigns a confidence score to each proposed journal entry (0..1).
- If confidence < 0.7, the proposal is shown with a caution: "I'm less certain about this one — please review carefully."
- The agent never auto-applies any journal. Every proposal requires explicit human approval.
- If any tool call fails (DB unavailable, timeout), the agent marks that check as "Unable to verify — please check manually" and proceeds with the remaining checks.

---

## 12. UX Flow Descriptions

*For Chitra (design) and Rupa (frontend engineer) to reference.*

### 12.1 Balance Sheet Page

**Location**: Reports > Balance Sheet (new nav item in the Reports section)

**Layout**:
- Top: Date picker ("As of Date") with a default of today. Preset buttons: "Month End", "Quarter End", "Year End", "Custom".
- Below date picker: Export buttons — PDF, CSV.
- Main content: Three collapsible sections: Assets, Liabilities, Equity.
  - Each section shows account sub-type groups as rows with indentation.
  - Account-level detail is hidden by default; clicking a sub-type group expands to show individual accounts.
  - Section totals are bolded and always visible.
  - "Total Liabilities + Equity" at the bottom in a heavy-weight row.
  - If balance check fails: amber warning banner at top.
- Right side (optional, collapsed by default): "How this is calculated" drawer — explains retained earnings rollup in plain English.
- Dark slate theme (matches existing reports).

### 12.2 Cash Flow Statement Page

**Location**: Reports > Cash Flow Statement (new nav item)

**Layout**:
- Top: Period range picker (start date, end date). Presets: "This Month", "Last Month", "This Quarter", "YTD", "Custom".
- Export buttons: PDF, CSV.
- Main content: Three sections.
  - Operating Activities: fully populated in v1.1.
  - Investing Activities: shown as placeholder row "Investing Activities (coming in v1.2) — $—".
  - Financing Activities: shown as placeholder row "Financing Activities (coming in v1.2) — $—".
  - Net Change in Cash: prominent; green if positive, red if negative.
  - Beginning/Ending Cash: shown below.
  - If reconciliation gap: amber warning banner.

### 12.3 Financial Close Wizard

**Location**: Accounting > Period Close (new page) OR accessible from Reports header CTA "Close Period"

**Entry Point**: A card/banner on the Accounting dashboard: "May 2026 has not been closed. [Begin Close]"

**Step 1 — Pre-Close Checks** (the "running" view):
- Header: "Closing May 2026"
- Progress bar: 0/10 checks complete.
- As checks complete (streamed via SSE), each appears as a row:
  - Green checkmark = passed.
  - Amber warning = informational issue.
  - Red X = blocking issue.
- Each row is expandable to show the agent's plain-English description and recommended action.
- CTA at bottom: "Continue to Review" (enabled when all checks have a result, even if some are failing).

**Step 2 — Review & Resolve**:
- Shows only the failing or informational checks.
- For each, the user can:
  - Click the primary action button (e.g. "Approve 4 Time Entries") — triggers the action inline.
  - Or click "Override" — opens a modal with a required reason field.
- Resolved checks show a green checkmark and collapse.
- Live counter: "3 of 4 issues resolved."
- CTA: "Proceed to Lock Period" (enabled when all blocking checks are resolved or overridden).

**Step 3 — Lock Period Confirmation**:
- Summary box:
  - Period: May 1–31, 2026.
  - Revenue: $X.
  - Expenses: $Y.
  - Net Income: $Z.
  - Checks: 8 passed, 2 overridden.
  - Overrides: [list with reasons].
- Warning: "Locking this period is permanent. No transactions may be posted in May 2026 after lock."
- [Lock Period] button (destructive action style — requires a second click confirmation on the button itself).
- After lock: success state with confetti or a clean "May 2026 is now closed" confirmation. Link to Balance Sheet (auto-opens as of May 31).

### 12.4 Year-End Close Screen

**Location**: Accounting > Year-End Close (separate menu item, only visible to `role=owner`)

**Layout**:
- Prerequisite check: "All periods in fiscal year 2025 must be locked before year-end close." Shows which periods are still open.
- Once all periods locked: "Ready for Year-End Close — Fiscal Year 2025."
- Preview: Shows the proposed closing journal entry in a read-only table (DR/CR pairs).
- Net Income Preview: Shows the amount that will roll to Retained Earnings.
- Confirmation: Input field "Type 2025 to confirm."
- [Run Year-End Close] button. Disabled until confirmation input matches.
- After close: "Fiscal Year 2025 is closed. Retained Earnings updated to $[amount]." Link to Balance Sheet.

### 12.5 Manual Journal Entry Enhancement

**Location**: Accounting > Manual Journals > New Entry

**Changes from v1**:
- New required field: "Reason / Memo" (text area, 500 char max). Placeholder: "Why is this journal entry needed? (required)".
- If total debits exceed the approval threshold: amber banner "This journal requires admin approval before posting (threshold: $10,000)."
- Submit button label changes to "Submit for Approval" if above threshold, "Save as Draft" if below.
- After submit: if above threshold, status shows "Pending Approval" with a timeline showing "Submitted by [User] at [Time]".
- Audit timeline widget at the bottom of the journal entry detail page.

---

## 13. Phasing — v1.1 vs v1.2

### v1.1 (This PRD — all Must items)

All five features in this PRD ship together in v1.1 because they are interdependent:
- Balance Sheet requires `accounts.sub_type` and the `retained_earnings` system account.
- Cash Flow requires `accounts.sub_type` for working capital classification.
- Financial Close wizard requires Balance Sheet (post-close link) and Cash Flow (as a close artifact).
- Year-End Close requires the Retained Earnings account and a locked fiscal year.
- Manual Journal audit trail is a prerequisite for close audit log quality.

**v1.1 delivery**: 4 weeks from approval.
- Week 1: Data model migration, system account seeding, `sub_type` tagging of existing accounts.
- Week 2: Balance Sheet report (backend service + frontend page). Cash Flow report (backend service + frontend page).
- Week 3: `close_assist_agent` + pre-close check logic + wizard frontend (Steps 1 and 2).
- Week 4: Year-end close flow + manual journal audit trail + period lock confirmation (Step 3) + QA + E2E tests.

### v1.2 (Future — Should/Could items)

| Feature | Rationale for Deferral |
|---|---|
| Cash Flow — Investing Activities | Requires fixed asset tracking, which PS firms rarely need at launch. |
| Cash Flow — Financing Activities | Requires loan/equity tracking. Deferrable until design partners request it. |
| Comparative Balance Sheet | Useful for board decks; not blocking for close process. |
| Consolidated multi-currency BS | Multi-entity consolidation is complex; single-entity is sufficient for v1. |
| Automated recurring accrual schedules | Manual accrual proposals via agent cover v1.1 well enough. |
| Budget vs. Actual on BS/CF | Requires budgeting module (not yet built). |
| XBRL export | Regulatory requirement for public companies only; not in ICP. |

---

## 14. Implementation Handoff — Issue Decomposition

*Netra to file these issues after Vishwa approves this PRD.*

### Backend Issues (Karya)

| Issue | Title | Dependencies |
|---|---|---|
| B-1 | [Karya] Data migration: add sub_type, is_contra to accounts; seed retained_earnings + income_summary accounts | None |
| B-2 | [Karya] Add reason, status fields to journal_entries; create manual_journal_audit_log table + service | B-1 |
| B-3 | [Karya] Add period_close_runs table + close run service | B-1 |
| B-4 | [Karya] Balance Sheet report endpoint: GET /reports/balance-sheet?as_of={date} | B-1 |
| B-5 | [Karya] Cash Flow Statement endpoint: GET /reports/cash-flow?start={date}&end={date} | B-1 |
| B-6 | [Karya] close_assist_agent — 10 check tools + agent wiring + HITL proposal integration | B-2, B-3 |
| B-7 | [Karya] Period close API: POST /accounting/period-close/begin, POST /accounting/period-locks (enhanced) | B-3, B-6 |
| B-8 | [Karya] Year-end close service: closing journal entry generation + year-end lock | B-4, B-6 |
| B-9 | [Karya] Manual journal approval workflow: threshold check, HITL task creation, approve/reject endpoints | B-2 |
| B-10 | [Karya] tenants: add manual_journal_approval_threshold, fiscal_year_start fields + settings endpoint | B-1 |

### Frontend Issues (Rupa)

| Issue | Title | Dependencies |
|---|---|---|
| F-1 | [Rupa] Balance Sheet report page (Angular component + service) | B-4 |
| F-2 | [Rupa] Cash Flow Statement report page (Angular component + service) | B-5 |
| F-3 | [Rupa] Financial Close Wizard — Step 1 (pre-close checks with SSE streaming) | B-7 |
| F-4 | [Rupa] Financial Close Wizard — Step 2 (resolve checks, agent proposal cards) | F-3, B-6 |
| F-5 | [Rupa] Financial Close Wizard — Step 3 (lock confirmation + success state) | F-4 |
| F-6 | [Rupa] Year-End Close page (prereq check, preview journal, type-to-confirm) | B-8, F-5 |
| F-7 | [Rupa] Manual Journal — reason field, approval threshold banner, audit timeline widget | B-9 |

### QA Issues (Aksha)

| Issue | Title | Dependencies |
|---|---|---|
| Q-1 | [Aksha] E2E scenario doc for Balance Sheet + Cash Flow (docs/test/e2e_r2r_reports.md) | F-1, F-2 |
| Q-2 | [Aksha] E2E scenario doc for Financial Close wizard (docs/test/e2e_financial_close.md) | F-3, F-4, F-5 |
| Q-3 | [Aksha] E2E scenario doc for Year-End Close (docs/test/e2e_year_end_close.md) | F-6 |
| Q-4 | [Aksha] Agent eval pack for close_assist_agent (docs/test/agent_evals/close_assist_agent.yaml) | B-6 |
| Q-5 | [Aksha] Playwright specs for all 5 features | Q-1, Q-2, Q-3 |

---

## 15. Acceptance Criteria Summary (Aksha Handoff)

The following acceptance criteria must all pass before v1.1 of this feature set is closed.

### Balance Sheet
- AC-BS-01 through AC-BS-06 (see §5.3)

### Cash Flow
- AC-CF-01 through AC-CF-05 (see §6.3)

### Financial Close
- AC-CL-01 through AC-CL-08 (see §7.3)

### Year-End Close
- AC-YE-01 through AC-YE-06 (see §8.3)

### Manual Journal Audit
- AC-MJ-01 through AC-MJ-07 (see §9.3)

### Cross-Cutting
- **AC-CC-01**: All new report pages are accessible via keyboard navigation and have ARIA labels.
- **AC-CC-02**: All new report pages render correctly in the dark slate theme.
- **AC-CC-03**: All monetary values on report pages use the `| currency` Angular pipe, never `parseFloat()`.
- **AC-CC-04**: All new API endpoints are tenant-scoped (RLS + explicit `tenant_id` filter in every query).
- **AC-CC-05**: Prahari security review is completed before v1.1 ships (close wizard posts journal entries — this is a trust-boundary change).
- **AC-CC-06**: `accounting_guardian` validates the year-end closing journal before it is posted.

---

## 16. Open Questions

| # | Question | Owner | Impact if unresolved |
|---|---|---|---|
| OQ-01 | Should we allow the Balance Sheet to be viewed as of a date in a locked period? (Answer is almost certainly yes — read-only historical view.) | Vishwa/Founder | Low — likely yes, implement as read-only |
| OQ-02 | Do we need a "Trial Balance" report as an intermediate step before Balance Sheet? Some accountants expect it as a close artifact. | Netra/Design Partners | Medium — adds 1 week if yes |
| OQ-03 | For the Cash Flow Statement, how do we handle payments in foreign currency where the FX rate moved between AR posting and cash receipt? (Translation gain/loss is already in GL but needs correct CF classification.) | Vastu/Karya | Medium — needs ADR |
| OQ-04 | Should the close wizard support partial-period locks (e.g. lock Jan 1–15 for audit purposes)? | Vishwa | Low — current design assumes calendar-month periods |
| OQ-05 | Do design partners need a "soft close" (flag-only, no hard lock) before the hard period lock? | Netra to ask design partners | Low — defer to v1.2 |
| OQ-06 | Should `fiscal_year_start` be configurable per-tenant, or fixed at January 1 for v1.1 with other options in v1.2? | Vishwa | Medium — impacts year-end close logic scope |
| OQ-07 | For the manual journal approval above threshold: if there is only one `role=owner`, do they self-approve? Recommend: yes, with an audit log note "Single approver — no second signer available." | Vishwa/Prahari | Medium — security boundary |

---

## Changelog

### 2026-06-20 — Initial Draft
- Full PRD drafted for issue #216.
- Covers: Balance Sheet (F1), Cash Flow — Operating Activities (F2), Financial Close Wizard + close_assist_agent (F3), Year-End Close (F4), Manual Journal Audit Trail (F5).
- Phasing defined: all five features target v1.1; Investing/Financing CF and multi-entity consolidation deferred to v1.2.
- Data model changes: 6 schema changes + 2 new tables (`manual_journal_audit_log`, `period_close_runs`).
- 17 implementation issues identified across Karya, Rupa, and Aksha.
- 7 open questions raised for Vishwa/Founder resolution.
- Awaiting Vishwa approval before implementation issues are filed.
