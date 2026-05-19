# E2E Scenario — Record to Report

> Sub-ledger events → GL postings → period close → reports.
> Standard: [`agent-harness/core/e2e-workflow-standard.md`](../../agent-harness/core/e2e-workflow-standard.md).

## Workflow

- **Name**: record-to-report
- **Entry point**: implicit — every sub-ledger write triggers a GL posting. Reports surfaced at `/reports/*`.
- **Exit state**: balanced GL; period locked; reports render with multi-currency toggle.

## Pre-conditions

- Engagements, invoices, bills, payments, expenses exist in seed data (run W1/W2 first).
- Chart of accounts seeded per market (US-GAAP-like default).
- `accounting_guardian` agent live at L3 (cannot be disabled).
- At least one closed period exists for period-lock tests.

---

## §1 Happy Path

### §1.1 Auto-posting via triggers

For each sub-ledger event (invoice approved, payment received, bill approved, bill paid, expense recorded):

| # | Event | Expected journal |
| --- | --- | --- |
| 1 | Invoice approved | DR `1200 AR` / CR `4000 Revenue` (+ CR `2300 Tax Payable` if any) |
| 2 | Payment received | DR `1100 Bank` / CR `1200 AR` |
| 3 | Bill approved | DR `5000 Expense` (or `1500 Asset`) / CR `2000 AP` (+ DR `1300 Input Tax` if any) |
| 4 | Bill paid | DR `2000 AP` / CR `1100 Bank` |
| 5 | Expense recorded (non-billable, paid by employee, awaiting reimbursement) | DR `5100 Expense` / CR `2100 Accrued Reimbursement` |

After each event, the test asserts: `sum(debits) == sum(credits)` for that journal entry and at the tenant level.

### §1.2 Period close

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 6 | Owner | `/settings/accounting/periods` → "Close April 2026" | All sub-ledgers must be reconciled (AR aging matches invoice rows; AP aging matches bill rows); if not, close is rejected with the reconciliation diff |
| 7 | system | Insert `period_locks` row | Subsequent posts dated in that period are rejected by `accounting_guardian` |

### §1.3 Reports

| # | Report | Expected behavior |
| --- | --- | --- |
| 8 | P&L by engagement | Revenue, direct cost, gross margin per engagement; multi-currency toggle |
| 9 | AR aging | 0-30 / 31-60 / 61-90 / 90+ buckets; matches `invoices` table |
| 10 | AP aging | 0-30 / 31-60 / 61-90 / 90+ buckets; matches `bills` table |
| 11 | Utilization | Billable hours / available hours per employee |
| 12 | WIP | Unbilled effort × rate per project |
| 13 | Trial balance | DR total = CR total for the period; if not, raise alarm |

---

## §2 Variants

- **§2.1 Multi-currency toggle**: P&L and AR aging render in tenant base by default; toggle to engagement / invoice currency.
- **§2.2 Mid-month report**: WIP and AR aging accept any date range; period close not required.
- **§2.3 Comparative report**: side-by-side last month vs. this month.

---

## §3 Unhappy Paths

| ID | Trigger | Expected behavior |
| --- | --- | --- |
| §3.1 | Sub-ledger event with imbalanced amounts (force via test) | Trigger refuses; sub-ledger event rolled back |
| §3.2 | Posting dated in a closed period | 422 `period_locked` |
| §3.3 | Trial balance does not balance after a batch of events | P0 alert fires; `reporting_agent` refuses to render reports until reconciled; runbook entry created |
| §3.4 | FX rate retroactively changed (operational error) | Rejected — FX rate at journal post time is frozen; any change is a new reversing entry |
| §3.5 | Cross-tenant report attempt | 404 |
| §3.6 | Reporting agent (LLM) hallucinates a number | Eval case: numbers in report response must reconcile with API totals. LLM cannot make up money totals; numbers are tool-call outputs only |
| §3.7 | Concurrent close + post | Race: post-loser gets 422 `period_locked`; period_locks insertion is atomic |
| §3.8 | Account deleted that has historical entries | Block delete; allow "deactivate" only |

---

## §4 Edge Cases

| # | Edge case | Expected behavior |
| --- | --- | --- |
| E1 | Period closed with cents of FX residual | Auto-route residual to `7900 Realized FX Gain/Loss` |
| E2 | Year-end close (December 2026) | Roll P&L → Retained Earnings; net income = 0 going into Jan 2027 |
| E3 | Voiding an invoice in a closed period | Allowed only via reversing entry dated in the open period |
| E4 | Manual journal entry (rare, owner-only) | Allowed; double approval (owner + admin); `accounting_guardian` still validates balance |
| E5 | Reports request a million-row range | API paginates; UI streams; no OOM |

---

## §5 RBAC Matrix

| Action | Owner | Admin | Manager | Member | Viewer |
| --- | --- | --- | --- | --- | --- |
| View P&L | ✅ | ✅ | ✅ (assigned engagements only) | ❌ | ✅ (assigned engagements only) |
| View AR/AP aging | ✅ | ✅ | ✅ | ❌ | ✅ |
| View trial balance | ✅ | ✅ | ❌ | ❌ | ❌ |
| Close period | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reopen period | ✅ | ❌ | ❌ | ❌ | ❌ |
| Create manual journal | ✅ | ✅ (with second approver) | ❌ | ❌ | ❌ |

---

## §6 Audit Trail

- `events`: `period.closed`, `period.reopened`, `journal.posted`, `journal.reversed`
- `audit_log`: every period close logs reconciliation snapshot
- `agent_suggestions`: `reporting_agent` rows for natural-language Q&A

## §7 Performance Budget

| Operation | Soft budget |
| --- | --- |
| Single sub-ledger event → journal | p95 < 100ms |
| AR aging render (10k invoices) | p95 < 2s |
| Trial balance for full year | p95 < 5s |
| Reporting agent NL query | p95 < 4s (first token) |

## §8 Cleanup

- Period close on test tenant is a hard delete after tests; no archival needed for test data.
- `eval_runs` for `reporting_agent` retained for drift analysis.

## §9 Executable Test Mapping

```
backend/tests/e2e/test_record_to_report.py::test_§<id>_<slug>
backend/tests/property/test_journal_balance.py::test_property_<invariant>
backend/tests/property/test_trial_balance.py::test_property_<invariant>
```
