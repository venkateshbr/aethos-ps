# Enterprise E2E Scenario Library

This library collects enterprise-readiness scenarios that should become browser
or API E2E tests as implementation slices land. It complements the launch
runbook and the workflow-specific test docs.

Related docs:

- Platform user guide: [`docs/user-guide/platform-user-guide.md`](../user-guide/platform-user-guide.md)
- Launch runbook: [`docs/qa/launch-e2e-scenario-runbook-2026-06-24.md`](launch-e2e-scenario-runbook-2026-06-24.md)
- Copilot prompt library: [`docs/copilot/prompt-library.md`](../copilot/prompt-library.md)
- Engagement to Cash: [`docs/test/e2e_engagement_to_cash.md`](../test/e2e_engagement_to_cash.md)
- Procure to Pay: [`docs/test/e2e_procure_to_pay.md`](../test/e2e_procure_to_pay.md)
- Record to Report: [`docs/test/e2e_record_to_report.md`](../test/e2e_record_to_report.md)

## Test Authoring Standard

Every new enterprise feature should define:

- persona and role;
- preconditions and seed data;
- browser entry route;
- Copilot prompt, if applicable;
- Inbox review path, if applicable;
- expected business record changes;
- expected audit, telemetry, or run-ledger evidence;
- negative path for authorization, tenant isolation, or policy denial;
- report or UI tie-out proving the result.

Prefer user-facing prompts and route names over internal tool names. Test specs
may use tool names only when they need deterministic assertions against the
agent ledger.

## Coverage Index

| ID | Scenario | Status | Tracking |
| --- | --- | --- | --- |
| ENT-DOC-001 | Platform guide links current product workflow to QA scenarios | Implemented as documentation baseline | #279 |
| ENT-DOC-002 | Full platform guide and prompt-library proof maps AI finance workflows to E2E evidence | Implemented documentation proof; static link check required | #312 |
| ENT-CTRL-001 | Approval policy routes high-risk task to required role | Browser/API proof automated in #309 | #280, #309 |
| ENT-CTRL-002 | Unauthorized approver is blocked with clean API/UI behavior | Browser/API proof automated in #309 | #280, #309 |
| ENT-AUD-001 | Inbox approval writes immutable decision event | Browser/API proof automated in #309 | #281, #309 |
| ENT-AUD-002 | Approve-with-edits preserves before/after decision summary | Browser/API proof automated in #309 | #281, #309 |
| ENT-RBAC-001 | Auditor/read-only persona can inspect but not mutate finance records | Browser/API proof automated in #309 | #282, #309 |
| ENT-AIOPS-001 | Scheduled Finance Ops Manager run creates reviewed work plan | Browser proof automated in #317 | #283, #317 |
| ENT-AIOPS-002 | Stale/high-risk Inbox work escalates to the right role | Browser proof automated in #317 | #283, #317 |
| ENT-AIOPS-003 | Admin configures scheduled Finance Ops Manager from Settings | Browser proof automated in #317 | #295, #317 |
| ENT-E2C-001 | Engagement-letter approval creates linked rate card from reviewed hints | API proof implemented in #345; browser proof target pending | #267, #345 |
| ENT-E2C-002 | Non-base-currency AR payment stores base amount and realised FX | Backend proof implemented in #349; browser/Stripe proof target pending | #349 |
| ENT-P2P-001 | Vendor invoice coding exception routes to Inbox and materializes after correction | Browser proof automated in #310 | #284, #310 |
| ENT-P2P-002 | Duplicate or mismatched vendor invoice requires explicit review | Browser proof automated in #310 | #284, #310 |
| ENT-P2P-003 | Browser AP exception card supports full vendor invoice review | Browser proof automated in #310 | #299, #310 |
| ENT-P2P-004 | Line-level PO/SO match evidence blocks mismatched bill approval | API/browser proof automated in #323 | #323 |
| ENT-P2P-005 | Bill-pay batch follows approve, export, send, and settlement controls | Browser proof automated in #325 | #325 |
| ENT-R2R-001 | Close evidence package shows AR/AP/WIP/GL readiness | Browser proof automated in #310 | #285, #310 |
| ENT-R2R-002 | Close override requires reason and is audit-visible | Browser proof automated in #310 | #285, #310 |
| ENT-R2R-003 | Close override wizard produces statement commentary with evidence | Browser proof automated in #310 | #300, #310 |
| ENT-R2R-004 | Year-end close posts retained-earnings journal evidence | API/browser proof automated in #327 | #327 |
| ENT-R2R-005 | AI year-end close routes retained-earnings posting through Inbox | API/agent proof automated in #329 | #329 |
| ENT-R2R-006 | AI financial statement package includes comparative variance commentary | API/agent proof automated in #331 | #331 |
| ENT-R2R-007 | Manual journal requires business reason and emits audit evidence | API/UI proof implemented in #333 | #333 |
| ENT-R2R-008 | High-value manual journal routes to Inbox approval | API/UI proof implemented in #335; lifecycle audit proof implemented in #339 | #335, #339 |
| ENT-R2R-009 | Posted manual journal reverses through controlled audit path | API/UI proof implemented in #337 | #337 |
| ENT-R2R-010 | Multi-currency manual journal stores tenant-base amounts and balances reports | Backend proof implemented in #347; browser/Copilot proof target pending | #347 |
| ENT-OPS-001 | Rate-limited endpoint fails safely under abuse | Browser/API proof automated in #311 | #286, #311 |
| ENT-OPS-002 | Tenant health summary exposes safe operational signals | Browser/API proof automated in #311 | #286, #311 |
| ENT-OPS-003 | Distributed limiter, health dashboard, and alert routing work together | Browser/API proof automated in #311 | #301, #311 |
| ENT-CTRL-003 | Tenant-configured approval policy drives Inbox routing | Browser/API proof automated in #309 | #296, #309 |
| ENT-AUD-003 | Business record exposes immutable decision timeline | Browser/API proof automated in #309 | #297, #309 |
| ENT-RBAC-002 | Finance-role personas are browser-proven | Browser/API proof automated in #309; full persona matrix automated in #321 | #298, #309, #321 |

## Automated Proof Commands

Run these when validating the #309 controls, audit, and RBAC proof:

```bash
cd frontend && npx playwright test e2e/enterprise-controls-audit-rbac.spec.ts --project=chromium
cd backend && uv run pytest tests/unit/test_approval_policy_api_contract.py tests/unit/test_inbox_api_contract.py tests/unit/test_financial_events_api_contract.py tests/unit/test_rbac.py -q
```

Run this when validating the #321 full finance persona matrix proof:

```bash
cd frontend && npx playwright test e2e/enterprise-finance-persona-matrix.spec.ts --project=chromium
```

Run this when validating the #310 AI finance workflow browser proof:

```bash
cd frontend && npx playwright test e2e/enterprise-ai-finance-workflows.spec.ts --project=chromium
```

Run this when validating the #317 scheduled Finance Ops Manager browser proof:

```bash
cd frontend && npx playwright test e2e/enterprise-scheduled-finance-ops.spec.ts --project=chromium
```

Run this when validating the #327 R2R year-end close browser proof:

```bash
cd frontend && npx playwright test e2e/enterprise-r2r-year-end-close.spec.ts --project=chromium
```

Run this when validating the #329 AI-routed year-end close proof:

```bash
cd backend && uv run pytest tests/unit/test_year_end_close_service.py tests/unit/test_copilot_tools.py tests/unit/test_copilot_hitl_policy.py tests/unit/test_agent_run_ledger.py tests/unit/test_approval_policy.py -q
```

Run this when validating the #331 comparative statement package proof:

```bash
cd backend && uv run pytest tests/unit/test_copilot_tools.py -q
```

Run these when validating the #333 manual journal audit proof:

```bash
cd backend && uv run pytest tests/unit/test_manual_journal_service.py tests/unit/test_accounting_api_contract.py tests/unit/test_inbox_journal_materialization.py -q
cd frontend && npx tsc -p tsconfig.spec.json --noEmit
```

Run these when validating the #335 manual journal threshold approval proof:

```bash
cd backend && uv run pytest tests/unit/test_manual_journal_service.py tests/unit/test_accounting_api_contract.py tests/unit/test_approval_policy.py tests/unit/test_approval_policy_api_contract.py -q
cd frontend && npx ng test --watch=false --include src/app/features/settings/approval-policy.component.spec.ts
cd frontend && npx tsc -p tsconfig.spec.json --noEmit
```

Run these when validating the #337 manual journal reversal proof:

```bash
cd backend && uv run pytest tests/unit/test_manual_journal_service.py tests/unit/test_accounting_api_contract.py -q
cd backend && uv run ruff check app/models/accounting.py app/services/manual_journal_service.py app/api/v1/endpoints/accounting.py tests/unit/test_manual_journal_service.py tests/unit/test_accounting_api_contract.py
cd frontend && npx tsc -p tsconfig.spec.json --noEmit
```

Run these when validating the #311 operational health and distributed limiter proof:

```bash
cd backend && uv run pytest tests/unit/test_ops_hardening.py -q
cd frontend && npx playwright test e2e/enterprise-ops-health.spec.ts --project=chromium
```

## ENT-R2R-007 - Manual Journal Reason And Audit Evidence

Persona: Finance Ops Manager, Controller, CPA/auditor.

Preconditions:

- Chart of accounts has at least two active accounts.
- Current accounting period is open.
- User role is Manager or higher for manual journal posting.

Steps:

1. Open `/app/accounting/journals`.
2. Create a balanced manual journal and provide a business reason of at least 10 characters.
3. Expand the posted journal row and verify the business reason is visible.
4. Query the decision/audit timeline for the journal entry.
5. Attempt the same balanced journal without a business reason.

Expected result:

- Valid manual journal posts through `accounting_guardian`.
- `journal_entries.reason` stores the business reason.
- `financial_events` contains `manual_journal.posted` with reason, actor role, line count, and debit total metadata.
- Missing or short reason is rejected with a non-500 validation error.
- AI draft journals approved from Inbox derive a reason from proposal context if older payloads do not include one.

## ENT-R2R-008 - Manual Journal Threshold Approval

Persona: Finance Ops Manager, Controller, Admin/Owner approver.

Preconditions:

- Approval Policy Settings has a manual-journal threshold, default `10000.00`.
- Accounting required role is Admin or Owner.
- Current period is open and chart of accounts has valid debit/credit accounts.

Steps:

1. Open `/app/settings` and set the manual-journal threshold to a value below the test journal amount.
2. Open `/app/accounting/journals`.
3. Submit a balanced manual journal with a business reason and total debits at or above the threshold.
4. Verify the Accounting UI shows a pending-approval success state and does not append a posted journal row.
5. Attempt to approve the task as the same user who submitted it.
6. Open `/app/inbox` as a different user with the required Accounting approver role.
7. Approve the manual-journal review task.
8. Return to `/app/accounting/journals` and verify the journal appears exactly once with reason and audit timeline.
9. Repeat with another over-threshold manual journal and reject the Inbox task with a rejection reason.

Expected result:

- Direct submission creates `agent_suggestions` + `hitl_tasks` review rows with kind `draft_journal`.
- The pending task shows required Accounting approval role and threshold metadata.
- `financial_events` contains `manual_journal.submitted_for_approval` with task id, suggestion id, actor role, business reason, debit total, threshold, required role, and payload hash metadata.
- Same-user approval is denied, leaves the task open, and writes `manual_journal.approval_denied` with `manual_journal_self_approval_denied`.
- Approval materializes through `ManualJournalService.post_manual_journal`, not a duplicate direct-post path.
- `manual_journal.posted` financial-event evidence is written after approval.
- Rejection leaves no posted journal and writes both generic `hitl_task.rejected` evidence and manual-journal-specific `manual_journal.rejected` evidence with the rejection reason.
- Under-threshold journals continue to post immediately through the guarded direct path.

## ENT-R2R-009 - Manual Journal Reversal Workflow

Persona: Finance Ops Manager, Controller, CPA/auditor.

Preconditions:

- A posted original manual journal exists with at least two balanced lines.
- The reversal entry date is in an open accounting period.
- User role is Manager or higher.

Steps:

1. Open `/app/accounting/journals`.
2. Expand the posted manual journal row.
3. Choose Reverse, enter an open-period reversal date and business reason, and submit.
4. Verify a new reversal journal appears with `reference_type=manual_reversal`.
5. Expand the reversal and verify DR/CR are flipped from the original.
6. Inspect the journal decision timeline/audit events.
7. Attempt to reverse the same original journal again.

Expected result:

- Reversal posts as a new immutable journal and never edits original rows.
- `accounting_guardian` validates the reversal journal.
- `financial_events` contains `manual_journal.reversed` linking original and reversal ids, actor role, reason, line count, and debit total.
- Duplicate reversal is blocked with a non-500 conflict.
- Non-manual journals cannot use this manual-journal reversal path.

## ENT-R2R-010 - Multi-Currency Manual Journal FX Posting

Persona: Finance Ops Manager, Controller, CPA/auditor.

Preconditions:

- Tenant base currency is USD or another launch currency with seeded FX rates.
- Current accounting period is open.
- Chart of accounts has valid payroll expense and accrued payroll accounts.
- Manual-journal approval policy is configured so the test can exercise either
  direct post or Inbox approval.

Steps:

1. Open `/app/copilot`.
2. Ask `Prepare a GBP 1,000 month-end payroll accrual journal for June 2026.
   Show the USD base-currency impact using the posting-date FX rate, route it
   to Inbox before posting, and verify the Trial Balance remains balanced after
   approval.`
3. If routed, approve the Inbox task as a different required approver.
4. Open `/app/accounting/journals` and expand the posted journal.
5. Open Reports > Trial Balance and the close package for the same period.
6. Repeat with a currency/date pair that has no FX rate available.

Expected result:

- Posted lines retain transaction `amount` and `currency`.
- Posted lines store `base_amount` converted to tenant base currency at the
  entry date FX rate.
- Posted foreign-currency lines store `fx_rate_id` for the FX row used at
  posting time.
- `accounting_guardian` validates balance using base amounts, not just matching
  transaction amounts.
- Missing FX rate rejects the post with a non-500 validation error.
- Trial Balance and financial statement reports remain balanced in tenant base
  currency after the journal posts.
- Audit evidence still includes manual-journal reason, actor role, line count,
  and debit total.

## ENT-DOC-001 - Platform Guide And Scenario Baseline

Persona: Product owner, QA lead, implementation agent.

Preconditions:

- Enterprise parent issue #278 exists.
- Child enterprise issues exist for controls, audit, RBAC, AI Ops, P2P, R2R, and Ops/Security.

Steps:

1. Open the platform user guide.
2. Verify it explains the current product surface in user language.
3. Open this enterprise scenario library.
4. Verify every enterprise child issue has at least one scenario placeholder.
5. Open the Copilot prompt library and launch runbook from the guide links.

Expected result:

- Documentation gives users a coherent product map.
- QA has a scenario anchor for future E2E automation.
- Planned features are marked as planned, not described as already implemented.

Automation target:

- Markdown link check.
- Static assertion that every #278 child issue ID appears in either this file or
  the platform guide.

## ENT-DOC-002 - Full Platform Guide And Prompt Library Proof

Persona: Product owner, finance operator, QA lead, implementation agent.

Status: Documentation proof implemented under #312. Controls/audit/RBAC browser
automation is implemented under #309, and AI finance workflow browser proof is
implemented under #310. Live ops browser proof remains tracked by #311.

Preconditions:

- First-slice enterprise issues #279-#301 are complete.
- Third-wave proof issues #309, #310, #311, and #312 exist under parent #278,
  with #309 completed as the controls/audit/RBAC browser proof and #310
  completed as the AI finance workflow browser proof.

Steps:

1. Open the platform user guide.
2. Verify every major platform surface is covered: Copilot, Inbox, clients and
   vendors, people, engagements and projects, invoices, bills/payments,
   accounting/close, reports, documents, settings, roles, audit, and
   operational health.
3. Open the Copilot prompt library.
4. Verify prompts are written in business language and do not require users to
   name internal tools.
5. For each major workflow, confirm the guide links to at least one scenario ID
   or launch/test guide.
6. Confirm the automation/proof map is explicit: #309 completed for
   controls/audit/RBAC, #310 completed for AI finance workflows, and #311
   remaining for live ops.

Expected result:

- Users can learn how to operate the full product as an AI Finance Ops Manager
  workflow.
- QA can map every major guide area to a scenario or proof backlog item.
- Implemented behavior is separated from future depth and live automation
  follow-up work.

Automation target:

- Static markdown link check for the platform guide, prompt library, and this
  scenario library.
- Static assertion that #309, #310, #311, and #312 are referenced in the
  platform guide, prompt library, and scenario library.
- Static assertion that user-facing prompt examples do not include required
  internal tool names.

## ENT-CTRL-001 - Role-Aware Approval Routing

Persona: Controller requests a high-risk finance action; Owner approves.

Preconditions:

- Approval policy matrix exists.
- At least one money-out or accounting-sensitive task can be generated through Copilot or existing UI.
- Controller and Owner users exist in the same tenant.

Steps:

1. Controller asks Copilot to prepare a sensitive action, such as a large bill-pay batch.
2. Verify Copilot routes the action to Inbox rather than executing it directly.
3. Open Inbox as Controller and verify the card shows required approver role.
4. Open Inbox as Owner and approve the card.
5. Verify the downstream draft business record is created.

Expected result:

- Required approver role is visible.
- Controller cannot bypass owner approval when policy requires Owner.
- Owner approval proceeds through the existing materialization path.
- Inbox can filter by required approval role.

Negative path:

- Direct API approval by under-privileged user returns 403 or equivalent clean denial.
- Approve-with-edits reevaluates the corrected payload and cannot lower the approval threshold.

Evidence:

- Inbox card, policy decision, agent/tool ledger, created record, audit event.
- Automated proof: #309 verifies the owner-required Inbox card is visible to a
  manager, the manager approval control stays disabled, and backend contract
  tests enforce approval-policy routing.

## ENT-CTRL-002 - Unauthorized Approval Denial

Persona: AP Lead or manager without sufficient authority.

Steps:

1. Create a task requiring a higher approver.
2. Attempt approval from an under-privileged account in UI.
3. Attempt direct API approval using the same account.
4. Refresh Inbox and inspect task status.

Expected result:

- UI does not allow approval or shows a clear role requirement.
- API denies mutation.
- Task remains open and assigned to the correct review lane.
- Denied attempt is safe to audit when the audit slice is implemented.

Automated proof:

- #309 verifies the browser-disabled approval path for under-privileged users
  and pairs it with backend Inbox/API contract tests for 403 denial.

## ENT-CTRL-003 - Tenant Approval Policy Configuration

Persona: Admin configuring finance controls.

Status: First slice implemented. Settings exposes an Approval Policy Matrix,
`GET /api/v1/approval-policy/effective` returns tenant policy with system
defaults, `PUT /api/v1/approval-policy/default` lets Admin/Owner users raise
supported review roles, and Inbox policy metadata/enforcement uses tenant
overrides while preserving safe default floors. #309 adds browser/API proof for
Settings visibility, persisted policy shape, and owner-threshold Inbox routing.

Steps:

1. Open Settings approval policy matrix.
2. Raise bill-pay approval from Admin to Owner for high-value batches.
3. Ask Copilot to prepare a bill-pay run above the threshold.
4. Open Inbox as Admin and Owner.

Expected result:

- Tenant policy persists and is used by Copilot/Inbox routing.
- Admin can inspect but not approve work that now requires Owner.
- Owner approval materializes through the existing guarded path.
- Approve-with-edits re-evaluates the edited payload against the saved policy.

Automation target:

- Component: load default matrix, save admin edits, and block Manager save.
- API: reject unsafe downgrade of money-out default role below Admin.
- API/Inbox: save external-send role as Admin, open a `send_email` task, and
  assert `required_approval_role=admin`.

## ENT-AUD-001 - Immutable Decision Event

Persona: Controller approving an AI-created draft.

Status: First slice implemented. Inbox approve/reject/approval-denial paths
append `financial_events` records, and Inbox Done/All status views display the
recent decision timeline. #309 adds browser/API proof for resolved Inbox
decision history.

Steps:

1. Use Copilot to create an Inbox-reviewed finance action.
2. Approve the task.
3. Open Inbox with Done or All status selected.
4. Inspect decision history.

Expected result:

- Decision history includes actor role, timestamp, action, source suggestion, source task, policy metadata, event hash, and safe payload summary.
- The event includes payload hashes and materialized entity references where available.
- Normal update paths cannot mutate the original audit event.

Negative path:

- Attempt to edit audit event through normal API or repository code fails.
- Under-privileged approval attempts append a denied decision event and leave the task open.

Automation target:

- Browser: create or seed a task, approve it, switch Inbox to Done, and assert
  the decision-history panel appears on the resolved card.
- API: assert `GET /api/v1/financial-events?entity_type=hitl_task&entity_id=<task_id>`
  returns the corresponding `hitl_task.approved` event.

## ENT-AUD-002 - Approve-With-Edits Audit

Persona: AP Lead correcting an extracted vendor invoice.

Status: First slice implemented. Approve-with-edits writes before/after safe
summaries and hashes to the immutable financial event ledger. Browser
proof for before/after decision summaries is automated in #309.

Steps:

1. Upload or create a draft that routes to Inbox.
2. Use approve-with-edits to correct a field such as amount, project, account, or date.
3. Open decision history.

Expected result:

- Decision history distinguishes original AI proposal from reviewed payload.
- Sensitive raw document data is not overexposed.
- Materialized record reflects the reviewed payload, not the unedited proposal.

Evidence:

- `hitl_task.approved_with_edits` event has original and corrected safe payload
  summaries, different payload hashes when the payload changed, source
  suggestion id, actor role, and policy metadata.
- `agent_corrections` still stores the training signal for the edited output.

## ENT-AUD-003 - Business Record Decision Timeline

Persona: Controller reviewing an invoice, bill, journal, payment, or close record.

Status: First slice implemented. HITL decision events are now projected onto
materialized business records and exposed through a viewer-accessible
record-scoped API. Bill, invoice, engagement, bill-payment batch, journal,
month-end close, and source-document surfaces render a reusable decision
timeline when events exist. #309 adds browser/API proof for bill decision
timeline visibility from outside Inbox.

Steps:

1. Create a finance record from an Inbox-approved AI proposal.
2. Navigate away from Inbox to the materialized business record.
3. Open the record decision timeline.
4. Compare approve, approve-with-edits, reject, and approval-denial history.

Expected result:

- Business record detail pages expose immutable decision events relevant to the
  record.
- Timeline entries include actor role, decision type, timestamp, related Inbox
  task, and before/after summary when available.
- Read-only users can inspect permitted audit metadata but cannot mutate.

Automation target:

- API: approve an Inbox task that materializes a bill or invoice, then assert
  `/financial-events/business-records/<entity>/<id>/decisions` is accessible to
  a viewer and includes the related Inbox task id, actor role, action, safe
  before/after hashes, and event hash.
- Browser: approve and approve-with-edits from Inbox, navigate to Bill or
  Invoice detail, and verify the decision timeline appears after leaving Inbox.
- Browser: reject a document-driven proposal, navigate to Documents, open the
  document decision timeline, and verify the rejected event is still visible
  after leaving Inbox.

## ENT-RBAC-001 - Auditor Read-Only Persona

Persona: External CPA or auditor.

Status: Implemented. The dedicated `auditor` role is read-only, separate from
the executive `viewer` role. API tests prove read-only access to reports,
bills/procurement, and Inbox while denying mutating finance actions. Bills/AP UI
disables create, approval, conversion, and Pay Bills entry actions for
read-only users. Browser proof for Settings, Inbox, and Bill-detail read-only
behavior is automated in #309, with distinct approver/auditor role proof added
under #364.

Steps:

1. Sign in as auditor/read-only persona.
2. Open reports, invoices, bills, procurement, journals, documents, Inbox Done/All history, and permitted dashboards.
3. Attempt to approve an Inbox task, create a bill, create or approve a procurement document, convert a purchase request, send an invoice, and approve a payment batch.
4. Attempt to list admin-only financial events directly.

Expected result:

- Read access matches the role definition.
- Mutating actions are hidden or disabled in UI.
- Direct API mutation attempts fail cleanly.
- Admin-only audit export/list endpoints remain blocked for viewer users.
- Cross-tenant access still returns 404/403 without leaking data.

Automation target:

- Browser: login as viewer, open Bills, verify New Procurement, New Bill, Pay
  Bills, Approve, and Convert controls are disabled.
- API: verify viewer can read Bills/Procurement/Inbox/Reports but receives 403
  for create/approve/edit/reject/convert actions and for financial-events list/export.

## ENT-RBAC-002 - Finance Role Persona Proof

Persona: AP Lead, AR Lead, Controller, Auditor, Executive, and Owner/Admin.

Status: Full matrix browser proof implemented. The backend exposes a viewer-readable
finance-persona catalog at `GET /api/v1/tenants/finance-personas`, maps
product-facing finance labels onto existing enforced roles, and unit/API tests
prove the mapping does not add new permissions. Settings now shows Finance role
personas under Approval Controls and highlights the personas compatible with the
current tenant role. #309 adds browser/API proof for Owner/Admin, Manager, and
Viewer paths; #321 adds browser proof across Owner/Admin, Controller, AP Lead,
AR Lead, Auditor, and Executive routes/actions.

Steps:

1. Sign in as each finance persona.
2. Open Settings -> Approval Controls -> Finance role personas and verify the
   current enforced role plus compatible persona chips.
3. Open Inbox, Bills/AP, Invoices/AR, Reports, Accounting, and Settings.
4. Attempt persona-appropriate and persona-restricted actions.
5. Repeat direct API attempts for restricted money, posting, send, lock, and settings actions.

Expected result:

- Product-facing finance personas map to enforced backend roles without
  weakening current RBAC.
- Browser controls are hidden or disabled consistently with API enforcement.
- Auditor and Executive personas remain read-only for finance mutation paths.
- Owner/Admin can still perform settings and final approval workflows.
- Settings gives users a self-serve explanation of the finance persona mapping
  without exposing admin-only permission controls to viewer users.

Automation:

- Browser: `frontend/e2e/enterprise-finance-persona-matrix.spec.ts` signs in as
  each named finance persona through the current enforced-role mapping, opens
  Settings, Inbox, Bills/AP, Invoices/AR, Accounting, and Reports, and verifies
  persona-appropriate controls.
- Browser: Auditor and Executive paths assert create, approve, post, pay, send,
  close, and settings mutation controls are disabled or absent.
- API: call `/api/v1/tenants/finance-personas` as Viewer and assert the catalog
  is readable; repeat restricted money/post/send/settings calls and assert 403.

## ENT-AIOPS-001 - Scheduled Finance Ops Manager Run

Persona: Owner/Admin configuring AI operations.

Status: Browser proof automated in #317. Admins can configure the tenant
cadence through Settings or `GET/PUT /api/v1/agents/finance-ops/schedule`. The
hourly Procrastinate worker creates a `scheduled_finance_ops_manager` workflow
run and a reviewed `copilot_create_finance_ops_action_plan` Inbox task when the
cadence is due.

Steps:

1. Open Settings and configure a daily Finance Ops Manager run.
2. Wait for or trigger the scheduled run.
3. Open Copilot/Inbox/Settings run ledger.
4. Verify findings and reviewed action plan are created.

Expected result:

- Read-only findings are generated from live data.
- Recommended write actions remain behind Inbox.
- Run is idempotent for the same tenant/period/cadence window.
- Settings workflow-run telemetry shows `scheduled_finance_ops_manager`.
- Approving the scheduled plan fans out Plan Items only; specialist actions
  keep their own Inbox gates.

Automation target:

- API: `PUT /api/v1/agents/finance-ops/schedule`, call the worker helper or
  trigger the Procrastinate task, then assert one open scheduled action-plan
  task and one workflow run.
- Browser: open Settings, save schedule cadence, open Settings workflow runs,
  filter for scheduled Finance Ops Manager, open Inbox, approve the plan, and
  verify Plan Items were created.
- Idempotency: rerun the worker for the same tenant/cadence bucket and assert a
  duplicate open plan is not created.

Automated proof:

```bash
cd frontend && npx playwright test e2e/enterprise-scheduled-finance-ops.spec.ts --project=chromium
```

## ENT-AIOPS-002 - Inbox Escalation

Persona: Controller with stale high-risk work.

Status: Browser proof automated in #317. The scheduled Finance Ops Manager
creates separate `finance_ops_escalation` Inbox notices for stale or high-risk
source tasks. The notice payload summarizes safe metadata and points back to
the source task; it does not copy the full source payload.

Steps:

1. Seed or create an overdue high-priority Inbox task.
2. Run escalation logic.
3. Open Inbox as assigned role and as unrelated role.

Expected result:

- Stale task is surfaced to the correct role.
- Unrelated roles do not gain access.
- Escalation is visible in task metadata and run ledger.
- The original task remains open and must still be reviewed through its own
  approval path.
- High-value money-out tasks route escalation to Owner/Admin depth according to
  the approval policy matrix.

Automation target:

- API: seed a high-risk open task older than `high_risk_stale_after_hours`,
  trigger the worker, and assert a `finance_ops_escalation` task assigned to an
  eligible reviewer.
- Payload safety: assert the escalation payload includes source task id, title,
  risk class, required approval role, age, and a safe payload summary, but does
  not duplicate arbitrary source payload fields.
- Browser: open Inbox as the assigned role, verify the escalation notice, then
  open the source task and approve/reject it separately.

## ENT-AIOPS-003 - Settings Schedule Configuration

Persona: Admin configuring AI operations; Manager inspecting schedule.

Status: Browser proof automated in #317. Settings now exposes Finance Ops
Manager cadence, enabled state, period mode, work item limit, stale-approval
windows, and escalation toggle. Admin/Owner users can save changes; Manager
users can inspect but not edit.

Steps:

1. Open Settings as Admin or Owner.
2. In Agent Autonomy, edit Finance Ops Manager Schedule to weekly, a specific
   UTC run hour/day, previous-month period mode, and escalation windows.
3. Save the schedule.
4. Refresh the card and confirm the saved values remain.
5. Re-open Settings as Manager and confirm the card is read-only.

Expected result:

- Schedule loads from `GET /api/v1/agents/finance-ops/schedule`.
- Save sends the existing `PUT /api/v1/agents/finance-ops/schedule` contract.
- High-risk stale hours cannot exceed stale hours.
- Manager users can inspect schedule state but cannot save edits.
- Schedule changes do not execute finance actions directly; scheduled runs
  still create reviewed Inbox action plans.

Automation target:

- Component: load seeded default, save admin edits, and block Manager save.
- Browser: login as Admin, save weekly schedule, verify success state, then
  login as Manager and assert form controls are disabled.

## ENT-E2C-001 - Engagement-Letter Rate Card Materialization

Persona: Engagement Manager, Finance Ops Manager, Billing Lead.

Preconditions:

- An engagement-letter or SOW document includes role/rate terms.
- Copilot/document extraction creates a `create_engagement_draft` Inbox task
  with reviewed `rate_card_hints`.

Steps:

1. Upload or seed an engagement-letter draft payload with at least two role/rate
   hints.
2. Review the Inbox task and approve, or approve with edits.
3. Open the created engagement and first project.
4. Open Settings/Rate Cards or query the API for the created rate card.
5. Draft a future invoice for the engagement and confirm rates resolve from the
   linked card.

Expected result:

- Approval creates the customer, draft engagement, first project, and one rate
  card from the reviewed hints.
- The engagement references the created `rate_card_id`, and the first project
  is created under that engagement.
- Duplicate or malformed hint rows are ignored rather than blocking onboarding.
- Inbox materialization evidence includes `rate_card_id` and
  `rate_card_line_count`.

## ENT-E2C-002 - Multi-Currency AR Payment Settlement

Persona: Billing Lead, Finance Ops Manager, Controller.

Preconditions:

- Tenant base currency is USD or another launch currency with seeded FX rates.
- A sent or approved customer invoice exists in a non-base currency.
- The invoice has `base_total` set from the invoice-date FX rate.

Steps:

1. Open `/app/copilot` or `/app/invoices`.
2. Ask `Review the latest GBP customer payment. Confirm the transaction amount,
   USD base amount, realised FX gain or loss, and whether AR Aging and Cash Flow
   will update after settlement.`
3. Record the payment through Stripe checkout/reconciliation or the manual
   payment action.
4. Open `/app/payments` and the paid invoice.
5. Open Reports > AR Aging, Cash Flow, Trial Balance, and Income Statement.
6. Repeat with a payment date/currency pair that has no FX rate.

Expected result:

- `payments.amount` and `payments.currency` retain the transaction receipt.
- `payments.base_amount` stores tenant-base value at the payment-date FX rate.
- `payments.fx_rate_id` references the immutable FX row used for conversion
  when the payment currency differs from tenant base currency.
- The DR Bank / CR AR journal retains transaction currency and stores matching
  base amounts plus the FX rate id used for conversion.
- Realised FX gain/loss uses `payment_base_amount - invoice.base_total`.
- Missing payment FX rate rejects or aborts before an incorrect payment row is
  inserted.
- AR Aging, Cash Flow, Trial Balance, and Income Statement consume base amounts
  consistently after settlement.

## ENT-P2P-001 - Vendor Invoice Coding Exception

Persona: AP Lead.

Status: First slice implemented. Vendor invoice extraction now serializes vendor
match, GL coding suggestions, match/coding status, and review exceptions into
the Inbox payload. Approval materializes bills through the Bills service path,
creates reviewed bill lines, preserves source document linkage, and stores
`vendor_invoice_review` evidence on the bill. #310 adds browser proof for a
business-language Copilot prompt, Inbox AP exception review, approve-with-edits
materialization, Bill detail AP evidence, and the separate payment proposal
review.

Steps:

1. Upload a vendor invoice with ambiguous project/account coding.
2. Review the extracted payload in Inbox.
3. Correct the coding.
4. Approve the bill.
5. Open Bills and Project P&L/AP Aging.

Expected result:

- Exception is explicit in Inbox.
- Approval materializes the corrected bill.
- Source document and coding evidence are preserved.
- Reports reflect the reviewed coding.

Automation target:

- API/unit: seed a vendor invoice payload with low-confidence or corrected
  account coding, approve-with-edits, and assert `bill_lines.account_id`,
  `bills.source_document_id`, and `bills.vendor_invoice_review`.
- Browser: upload invoice, open Inbox bill task, verify match/coding status and
  exception count, edit coding, approve, then open Bill detail and verify lines.
- Browser: `frontend/e2e/enterprise-ai-finance-workflows.spec.ts` covers the
  deterministic #310 proof with mocked API contracts and user-facing prompts.

## ENT-P2P-002 - Duplicate Or Mismatch Review

Persona: AP Lead and Controller.

Status: First slice implemented. Possible duplicate vendor invoice drafts are
blocked on approve-as-is. They require approve-with-edits with
`duplicate_review.approved_duplicate=true` and a reason. PO mismatch validation
continues to run through the Bills service path during materialization and bill
approval. #310 adds browser proof that duplicate evidence opens the edit drawer,
captures a reviewer reason, and persists that reason into Bill detail evidence.

Steps:

1. Upload a vendor invoice that appears to duplicate an existing vendor invoice number or conflicts with expected match criteria.
2. Open Inbox review card.
3. Attempt to approve without override reason if policy requires one.
4. Approve with explicit reason or reject.

Expected result:

- Duplicate/mismatch is flagged before bill creation.
- Approval requires explicit review and reason where configured.
- Rejection creates no bill.

Automation target:

- API: approve-as-is for a `possible_duplicate=true` bill task returns 409 with
  `duplicate_vendor_invoice_review_required`.
- API: approve-with-edits including duplicate override reason materializes the
  bill and persists the duplicate review evidence.
- Browser: duplicate card displays match/coding exception summary before review.
- Browser: #310 verifies duplicate card evidence, duplicate reason validation,
  approve-with-edits, and post-review Bill detail evidence.

## ENT-P2P-003 - Browser Vendor Invoice Exception Review

Persona: AP Lead and Controller.

Status: First slice implemented. Inbox vendor invoice cards now expose AP review
evidence including vendor match, duplicate guard, source document, GL coding
suggestions, project/customer hints, and required correction exceptions. Possible
duplicates open the edit drawer for a reviewer-entered reason before approval.
Bill detail shows the preserved `vendor_invoice_review` evidence after
materialization. #310 adds Playwright proof for the AP review card, duplicate
reason capture, Bill detail evidence, and separate bill-pay proposal review.
#323 adds line-level PO/service-order match evidence for linked bills through
the Bills service path.

Steps:

1. Upload a vendor invoice with vendor ambiguity, duplicate evidence, and coding
   exceptions.
2. Open the Inbox/AP review card.
3. Review source document, vendor match, duplicate guard, GL/project coding
   suggestions, and required corrections.
4. Approve intake/coding review, then keep payment approval separate.

Expected result:

- Review card exposes exception evidence without requiring raw payload reading.
- Duplicate approval requires a reviewer reason.
- Intake/coding approval and payment approval are separate guarded decisions.
- Bill evidence preserves source document and reviewer decisions.

Automation target:

- API/unit: duplicate invoice approve-with-edits persists
  `duplicate_review.reason`, source document linkage, GL suggestions, and
  project/customer hints into `bills.vendor_invoice_review`.
- Browser: seed or upload a duplicate/ambiguous invoice, verify Inbox AP review
  evidence and duplicate reason validation, approve with reason, then open Bill
  detail and verify the same evidence appears before selecting the bill for a
  separate payment batch.
- Browser: #310 uses the business prompt `Process this vendor invoice for Aster
  Cloud Services...` and asserts that no internal tool name is required in the
  user prompt.

## ENT-P2P-004 - Line-Level PO/SO Match Evidence

Persona: AP Lead and Controller.

Status: Implemented in #323. Linked bills now compare bill lines against the
approved purchase order or service order by description, quantity, unit price,
amount, and service period where applicable. The API records `line_matches` and
`line_exceptions` in `po_match_summary`, and non-matched line/service-period
statuses block bill approval through the existing AP approval gate. Bills list
and Bill detail expose the exception evidence.

Steps:

1. Create or load an approved purchase order or service order with line-level
   details.
2. Create a linked vendor bill with a matching line and verify the bill records
   line evidence as matched.
3. Repeat with quantity, unit-price, unmatched-line, and service-period
   mismatches.
4. Attempt to approve the mismatched bill.
5. Open `/app/bills` and the bill detail route to verify visible exception
   evidence.

Expected result:

- Matched bills show line-level PO/SO evidence.
- Quantity, unit-price, unmatched-line, and service-period exceptions are
  recorded with readable evidence.
- Mismatched linked bills remain draft and approval fails with the match
  summary.
- Browser users can see the exception without reading raw JSON.

Automation target:

- API/unit: `cd backend && uv run pytest tests/unit/test_bills_api_contract.py -q`
- Browser: `cd frontend && npx playwright test e2e/enterprise-p2p-line-match-evidence.spec.ts --project=chromium`

## ENT-P2P-005 - Bill-Pay Lifecycle Controls

Persona: Controller and AP Lead.

Status: Implemented in #325. Pay Bills now consumes the approved-bills API
response reliably, creates a draft batch, requires explicit approval before
export, records CSV/NACHA export state before mark-sent, and exposes settlement
confirmation with settled-count and journal evidence from the existing
bill-payment settlement endpoint.

Steps:

1. Open `/app/billing-runs` with at least one approved unpaid bill.
2. Select approved bills and create a payment batch.
3. Approve the draft batch.
4. Download CSV or NACHA export and verify the UI records export state.
5. Mark the batch sent to bank.
6. Confirm settlement.

Expected result:

- Draft/unapproved batches cannot be exported from the UI.
- A batch cannot be marked sent until an export has completed.
- Settlement remains a separate explicit confirmation after sent-to-bank.
- Settlement displays count and returned journal IDs.

Automation target:

- Browser: `cd frontend && npx playwright test e2e/enterprise-bill-pay-lifecycle.spec.ts --project=chromium`

## ENT-R2R-001 - Close Evidence Package

Persona: Controller.

Status: First slice implemented. Close package responses now include
`readiness_evidence` for AR, AP, WIP, GL, approvals, and overrides. Close status
also includes unposted journals, incomplete close tasks, and recorded overrides
so the package and lock guard share the same readiness model. #310 adds browser
proof for business-language close prep, Inbox close approval, Accounting close
package evidence, and statement report tie-out.

Steps:

1. Generate close readiness for a period.
2. Open close evidence package.
3. Inspect AR, AP, WIP, journal, and approval blockers.
4. Follow links to supporting records.

Expected result:

- Evidence package is built from real records.
- Blockers are actionable.
- Package ties to reports and journal evidence.

Automation target:

- API: seed AR/AP reconciliation findings, WIP rows, an unposted journal, and
  pending close tasks; assert `close-package.readiness_evidence` categorizes
  each area and includes supporting record references.
- Browser: open Accounting > Journal Entries close package, verify AR/AP/WIP/GL
  metrics and close commentary render without requiring tool names.
- Browser: `frontend/e2e/enterprise-ai-finance-workflows.spec.ts` covers the
  deterministic #310 R2R proof with mocked public API contracts.

## ENT-R2R-002 - Close Override With Reason

Persona: Owner/Admin.

Status: First slice implemented. Close overrides are durable rows with blocker
code, reason, actor, timestamp, and blocker evidence. The period-lock API still
returns the existing blocker errors unless the matching override is recorded
or submitted with the lock request. Override evidence is visible in the close
package. #310 adds browser proof for recording a named close blocker override
reason and seeing it persist in the close package.

Steps:

1. Create a close blocker that would normally prevent locking.
2. Attempt close as Controller.
3. Attempt authorized override as Owner/Admin with a reason.
4. Inspect decision history and close package.

Expected result:

- Unauthorized close remains blocked.
- Authorized override requires reason.
- Override is visible in close evidence and audit trail.

Automation target:

- API: attempt lock with an unposted journal and no override; assert 409.
- API: attempt lock with a short override reason; assert 422.
- API: attempt lock with a valid `unposted_journals` override; assert period is
  locked and `accounting_close_overrides` contains reason and actor.
- Browser: record override reason from close review UI and verify the close
  package displays the reason, actor role, and approval timeline evidence.

## ENT-R2R-003 - Close Wizard And Statement Commentary

Persona: Controller and Owner/Admin.

Status: First slice implemented. The Accounting close package panel now lets
Admin/Owner users record a blocker-specific override reason, override evidence
includes actor role, close package commentary carries structured evidence, and
Copilot financial statement packages include close-readiness warnings plus
management commentary sourced from the close package. #310 adds browser proof
for statement tabs and Agent Run Ledger evidence after the close workflow.

Steps:

1. Open Accounting close review for a period with AR/AP/WIP/GL blockers.
2. Review blocker evidence and enter a reasoned override for a named blocker.
3. Generate the financial statement package.
4. Inspect management commentary and material variance explanations.

Expected result:

- Close wizard prevents silent locks and requires named override reasons.
- Override evidence appears in the close package.
- Statement commentary is grounded in reports and close readiness evidence.
- Missing close prerequisites remain visible in the statement package.

Automation target:

- Browser: load close package, choose a blocked checklist item, record a reason,
  refresh, and assert the override appears with role and timestamp.
- API: create a close override and assert `created_by_role` is persisted.
- Copilot/API: generate financial statements and assert close warnings plus
  evidence-backed commentary are present.
- Browser: #310 uses the business prompt `Run month-end close readiness for
  June 2026...` and verifies Reports Balance Sheet, Income Statement, Statutory
  Pack, and Settings Agent Run Ledger tool evidence.

## ENT-R2R-004 - Year-End Close Retained-Earnings Posting

Persona: Controller and Owner/Admin.

Status: Implemented in #327. Accounting exposes a year-end close action that
posts a balanced `year_end_close` journal for the selected fiscal year. The
backend reverses posted revenue and expense balances for January through
December, offsets net income or loss to seeded account `3000 Retained
Earnings`, blocks duplicate closes, and refuses to post while any period in the
target year is locked.

Steps:

1. Complete reviewed month-end activity for the fiscal year.
2. Open Accounting > Journal Entries.
3. In Month-end close, post the year-end close for the selected fiscal year.
4. Inspect the resulting journal evidence and retained-earnings amount.
5. Re-open Balance Sheet and retained-earnings roll-forward for the year-end
   period.

Expected result:

- The closing journal is balanced and has `reference_type=year_end_close`.
- Revenue and expense accounts are closed to zero for the fiscal year.
- Net income credits Retained Earnings; net loss debits Retained Earnings.
- Duplicate close attempts and locked-year attempts fail with readable errors.
- The posted journal is visible in Accounting and ties to the retained-earnings
  statement evidence.

Automation target:

- API: assert the service posts the expected revenue, expense, and retained
  earnings lines for net income and net loss.
- API: assert duplicate, missing-account, no-activity, and locked-period guards.
- Browser: `frontend/e2e/enterprise-r2r-year-end-close.spec.ts` covers the
  Accounting close panel action, retained-earnings evidence, and refreshed
  journal list.

## ENT-R2R-005 - AI Year-End Close Inbox Approval

Persona: AI Finance Ops Manager, Controller, and Admin approver.

Status: Implemented in #329. Copilot can interpret a business-language request
to prepare year-end close, build a retained-earnings posting preview, route the
accounting-risk action to Inbox as `copilot_prepare_year_end_close`, and only
post the `year_end_close` journal after approval.

Steps:

1. `/app/copilot`: ask `Prepare year-end close for fiscal year 2026. Check
   retained earnings setup, duplicate close risk, locked periods, P&L activity,
   and comparative statement movement. Route the posting to Inbox for approval.`
2. Verify Copilot creates an Inbox review task instead of posting a journal.
3. Inspect the Inbox payload for year, period, readiness blockers, closing
   accounts, net income, retained-earnings direction/amount, and
   current-vs-prior year statement commentary.
4. Approve the Inbox task as an Admin/Owner.
5. Confirm approval calls the existing year-end close service and returns the
   posted journal metadata.

Expected result:

- The tool is classified as `accounting` risk and uses
  `copilot_prepare_year_end_close`.
- The preview is non-mutating and exposes blockers rather than hiding them.
- Approval posts through the same service used by the Accounting close panel.
- Finance Ops Plan Item dispatch can start the same specialist year-end review
  workflow without directly posting the journal from the manager action plan.

Automation target:

- API/agent: assert Copilot exposes `prepare_year_end_close`, routes it to HITL,
  creates the expected review payload, and materializes approval through
  `YearEndCloseService.post_year_end_close`.
- API/agent: assert Finance Ops Plan Item dispatch maps
  `prepare_year_end_close` to a downstream specialist review task.

## ENT-R2R-006 - Comparative AI Financial Statement Package

Persona: Controller, CFO, and AI Finance Ops Manager.

Status: Implemented in #331. Copilot-generated financial statement packages
include a deterministic comparative statement section built from posted
report-service outputs. The package remains read-only and does not require
Inbox approval because no accounting records are created or changed.

Steps:

1. `/app/copilot`: ask `Generate the financial statement package for Q2 2026
   and compare it to Q2 2025. Include close-readiness warnings and
   evidence-backed variance commentary.`
2. Verify Copilot uses `generate_financial_statement_package`.
3. Inspect the result for current period, comparison period, statement summary,
   variances, and commentary.
4. Cross-check the statement tabs in Reports for the current period.

Expected result:

- If no comparison period is supplied, the package compares against the
  immediately preceding window of the same length.
- If a comparison period is supplied, the package uses that explicit window.
- Revenue, expenses, net income, cash, retained earnings, and balance status
  come from report-service outputs rather than model-invented values.
- Invalid comparison ranges return readable validation errors.

Automation target:

- API/agent: assert default prior-period comparison for a one-month package.
- API/agent: assert explicit multi-month comparison window support.
- API/agent: assert invalid comparison end without start returns a readable
  error.

## ENT-OPS-001 - Rate-Limited Endpoint

Persona: Security reviewer.

Status: Browser/API proof automated in #311. App-level in-process and
Supabase-backed rate limiting protects signup and public invoice token reads.
Excess traffic returns a safe `429` body with `Retry-After`,
`X-RateLimit-Limit`, and `X-RateLimit-Remaining` headers. The limiter is
path-scoped so normal authenticated workflows are not made flaky.

Steps:

1. Exercise a rate-limited public/auth endpoint repeatedly from the same client context.
2. Verify normal traffic succeeds under the threshold.
3. Verify excess traffic fails with a safe response.

Expected result:

- Rate-limit response does not leak internals.
- Tests can reset or isolate rate-limit state.
- Legitimate E2E setup is not made flaky.

Automation target:

- API: configure a low threshold in test, call `POST /api/v1/auth/signup`
  twice from the same client, and assert the second response is 429 with safe
  detail and retry headers.
- API: repeat for `GET /api/v1/public/invoices/{token}` with a fake token and
  assert the response path does not expose the raw token in telemetry.

## ENT-OPS-002 - Tenant Health Summary

Persona: Internal operator.

Status: Browser/API proof automated in #311. Tenant health summarizes runtime
settings, table/migration reachability, sanitized request/background failure
counters, and recent agent run, agent tool, and workflow failure counts. Output
is scoped to the current tenant and safe for internal operators.

Steps:

1. Open or call tenant health summary.
2. Verify safe checks for runtime config, migrations, queues, provider readiness, and recent failures.
3. Confirm no secrets or raw credentials are exposed.

Expected result:

- Operators get useful health signals.
- Tenant users do not see unauthorized operational data.
- Health output is stable enough for support runbooks.

Automation target:

- API: seed failed `agent_runs`, `agent_tool_invocations`, and
  `agent_workflow_runs`; call `/api/v1/tenants/health`; assert counts and
  table checks are present.
- API: assert health output includes no API keys, JWTs, raw invoice public
  tokens, request payloads, or document text.

## ENT-OPS-003 - Distributed Ops Protection And Alerts

Persona: Internal operator and security reviewer.

Status: Browser/API proof automated in #311. `RATE_LIMIT_BACKEND=supabase`
activates a Postgres-backed limiter using hashed subjects and the same safe
`429` response contract. The backend proof exercises shared limiter state
across simulated app instances, fallback-to-memory telemetry, and deny-safely
mode when fallback is disabled. Settings exposes an Operational Health
dashboard backed by `/api/v1/tenants/health`, including table/migration checks,
rate-limit backend status, sanitized failure counters, agent/tool/workflow
failure breakdowns, and routed alert items.

Steps:

1. Configure distributed rate limiting for the environment.
2. Generate excess public endpoint traffic across more than one app instance.
3. Open tenant health dashboard.
4. Trigger repeated background or agent workflow failures.
5. Inspect alert routing evidence.

Expected result:

- Distributed limiter preserves the safe 429 response contract.
- Tenant health dashboard shows sanitized operational signals.
- Alert thresholds route degraded health or abuse to the configured support or
  runbook channel.
- Telemetry never emits raw tokens, JWTs, API keys, document text, or request
  payloads.

Automation target:

- API: lower thresholds, configure Supabase limiter, and assert the second
  process sees the same limit state while preserving the safe `429` body and
  headers.
- API: force distributed limiter RPC failure and assert fallback mode is used,
  no exception leaks, and a sanitized `rate_limit_distributed_backend`
  background failure is visible in tenant health.
- Browser: open Settings -> Operational Health as Admin/Owner and verify table
  checks, rate-limit backend, request failures, background failures, agent/tool
  failures, workflow failures, and routed alerts render without raw sensitive
  values.

Automated proof:

```bash
cd backend && uv run pytest tests/unit/test_ops_hardening.py -q
cd frontend && npx playwright test e2e/enterprise-ops-health.spec.ts --project=chromium
```
