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
| 6 | Controller | `/copilot` → "Prepare month-end close for April 2026" | Copilot routes a close package to Inbox. The package includes AR, AP, WIP, GL, approvals, unposted journals, incomplete close tasks, close blockers, and recorded override evidence. |
| 7 | Owner/Admin | Reviews close package and resolves blockers | Sub-ledger, trial-balance, unposted-journal, close-review, and close-task blockers must be resolved or explicitly overridden with a reason and actor. |
| 8 | system | Insert `period_locks` row | Subsequent posts dated in that period are rejected by `accounting_guardian` |
| 8a | Owner/Admin | `/accounting/journals` -> Year-end close | Posts `year_end_close` journal for the selected fiscal year, reversing posted revenue/expense balances and offsetting net income or loss to `3000 Retained Earnings`. Duplicate and locked-year attempts are rejected. |
| 8b | Finance Ops Manager | `/copilot` -> "Prepare year-end close for fiscal year 2026..." then approve `/inbox` task | Copilot creates a `copilot_prepare_year_end_close` review task with retained-earnings posting preview, blockers, P&L activity, and current-vs-prior statement commentary. Approval posts through the same year-end close service. |

### §1.3 Reports

| # | Report | Expected behavior |
| --- | --- | --- |
| 9 | P&L by engagement | Revenue, direct cost, gross margin per engagement; multi-currency toggle |
| 10 | AR aging | 0-30 / 31-60 / 61-90 / 90+ buckets; matches `invoices` table |
| 11 | AP aging | 0-30 / 31-60 / 61-90 / 90+ buckets; matches `bills` table |
| 12 | Utilization | Billable hours / available hours per employee |
| 13 | WIP | Unbilled effort × rate per project |
| 14 | Trial balance | DR total = CR total for the period; if not, raise alarm |

### §1.4 AI Finance Ops Manager command center

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 15a | Admin | `/settings` -> Agent Autonomy -> Finance Ops Manager Schedule; saves cadence, period mode, work-item limit, and stale escalation windows | `PUT /agents/finance-ops/schedule` persists tenant cadence; scheduled execution still creates reviewed Inbox action plans instead of directly changing finance records |
| 15 | Finance ops manager | `/copilot` → "Run today's finance ops check" | `copilot_agent` invokes `run_finance_ops_check` and records the invocation in `agent_tool_invocations` as `read_only` |
| 16 | system | Summarise AR, AP, WIP, close readiness, action queue, and recent agent/workflow status | Response separates `read_only_findings` from `recommended_actions`; write-capable recommendations are marked as requiring Inbox approval |
| 17 | Finance ops manager | `/copilot` → "Create the next recommended finance ops work items" | `copilot_agent` invokes `create_finance_ops_action_plan`; Inbox receives a manager action-plan task with domain, recommendation, specialist tool, risk class, rationale, and review path |
| 18 | Finance ops manager | Approves the action-plan task, then approves a Plan Item in `/inbox` | Action-plan approval creates one `finance_ops_action_item` child Inbox task per review-required recommendation. Plan Item approval dispatches the mapped specialist workflow, creating the next specialist review task where applicable; invoices, payments, journals, statements, and emails remain behind specialist approval flows |

### §1.5 AI collections reminders through Inbox

| # | Actor | Action | System effect |
| --- | --- | --- | --- |
| 19 | Finance ops manager | `/copilot` → "Draft reminders for invoices overdue more than 30 days" | `copilot_agent` invokes `draft_collection_reminders`; `collections_agent` discovers live overdue invoices, drafts deterministic reminder payloads, and records read/draft/send ledger steps |
| 20 | system | Create one Inbox task per eligible invoice | Each `send_email` task includes invoice, customer, recipient, tone, subject, body, confidence, and eligibility rationale; no email is sent before approval |
| 21 | Finance ops manager | Approves or rejects the Inbox task | Approval materialises through the existing collections email send path; rejection records a correction/audit signal and sends nothing |

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
| §3.9 | Close blocker overridden without reason | 422 `close_override_reason_required`; period remains unlocked |
| §3.10 | Lock attempted with unposted journal and no override | 409 `unposted_journals_pending`; response lists affected draft journals |

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
- `accounting_close_overrides`: close blocker code, reason, actor, timestamp, and blocker evidence for explicit overrides
- `close_package.readiness_evidence`: AR/AP/WIP/GL/approval evidence and recorded overrides shown to the reviewer

## §6.1 Automated Browser Proof

The #310 browser proof covers a deterministic R2R slice with user-facing
Copilot prompts:

```bash
cd frontend && npx playwright test e2e/enterprise-ai-finance-workflows.spec.ts --project=chromium
```

Coverage: month-end close readiness prompt, close Inbox approval, close package
AR/AP/WIP/GL evidence, named override reason capture, close approval timeline,
financial statement tabs, and Settings Agent Run Ledger evidence.

The #327 browser proof covers year-end retained-earnings posting:

```bash
cd frontend && npx playwright test e2e/enterprise-r2r-year-end-close.spec.ts --project=chromium
```

Coverage: Accounting close panel year-end action, `year_end_close` journal
evidence, retained-earnings amount, and refreshed journal list. AI-orchestrated
year-end close approval is covered by #329 backend agent/service proof; manual
journal audit enhancements remain future R2R depth.

The #329 backend proof covers AI-routed year-end close approval:

```bash
cd backend && uv run pytest tests/unit/test_year_end_close_service.py tests/unit/test_copilot_tools.py tests/unit/test_copilot_hitl_policy.py tests/unit/test_agent_run_ledger.py tests/unit/test_approval_policy.py -q
```

Coverage: `prepare_year_end_close` tool contract, accounting HITL routing,
Inbox materialisation, Finance Ops Plan Item dispatch, non-mutating preview
blockers, retained-earnings posting metadata, and comparative statement
commentary.

The #317 browser proof covers the scheduled Finance Ops Manager setup and
review boundary:

```bash
cd frontend && npx playwright test e2e/enterprise-scheduled-finance-ops.spec.ts --project=chromium
```

Coverage: Settings schedule save/read-only behavior, reviewed scheduled
action-plan Inbox task, separate stale high-risk escalation notice, and
`scheduled_finance_ops_manager` workflow telemetry.

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
