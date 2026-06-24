# Enterprise E2E Scenario Library

This library collects enterprise-readiness scenarios that should become browser
or API E2E tests as implementation slices land. It complements the launch
runbook and the workflow-specific test docs.

Related docs:

- Platform user guide: [`docs/user-guide/platform-user-guide.md`](../user-guide/platform-user-guide.md)
- Launch runbook: [`docs/qa/launch-e2e-scenario-runbook-2026-06-24.md`](launch-e2e-scenario-runbook-2026-06-24.md)
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
| ENT-CTRL-001 | Approval policy routes high-risk task to required role | Implemented first slice; browser automation pending | #280 |
| ENT-CTRL-002 | Unauthorized approver is blocked with clean API/UI behavior | Implemented first slice; browser automation pending | #280 |
| ENT-AUD-001 | Inbox approval writes immutable decision event | Implemented first slice; browser automation pending | #281 |
| ENT-AUD-002 | Approve-with-edits preserves before/after decision summary | Implemented first slice; browser automation pending | #281 |
| ENT-RBAC-001 | Auditor/read-only persona can inspect but not mutate finance records | Implemented first slice; browser automation pending | #282 |
| ENT-AIOPS-001 | Scheduled Finance Ops Manager run creates reviewed work plan | Implemented first slice; browser automation pending | #283 |
| ENT-AIOPS-002 | Stale/high-risk Inbox work escalates to the right role | Implemented first slice; browser automation pending | #283 |
| ENT-AIOPS-003 | Admin configures scheduled Finance Ops Manager from Settings | Implemented first slice; Playwright automation pending | #295 |
| ENT-P2P-001 | Vendor invoice coding exception routes to Inbox and materializes after correction | Implemented first slice; browser automation pending | #284 |
| ENT-P2P-002 | Duplicate or mismatched vendor invoice requires explicit review | Implemented first slice; browser automation pending | #284 |
| ENT-P2P-003 | Browser AP exception card supports full vendor invoice review | Implemented first slice; Playwright automation pending | #299 |
| ENT-R2R-001 | Close evidence package shows AR/AP/WIP/GL readiness | Implemented first slice; browser automation pending | #285 |
| ENT-R2R-002 | Close override requires reason and is audit-visible | Implemented first slice; browser automation pending | #285 |
| ENT-R2R-003 | Close override wizard produces statement commentary with evidence | Implemented first slice; browser automation pending | #300 |
| ENT-OPS-001 | Rate-limited endpoint fails safely under abuse | Implemented first slice; browser/API automation pending | #286 |
| ENT-OPS-002 | Tenant health summary exposes safe operational signals | Implemented first slice; browser/API automation pending | #286 |
| ENT-OPS-003 | Distributed limiter, health dashboard, and alert routing work together | Planned | #301 |
| ENT-CTRL-003 | Tenant-configured approval policy drives Inbox routing | Implemented first slice; Playwright automation pending | #296 |
| ENT-AUD-003 | Business record exposes immutable decision timeline | Planned | #297 |
| ENT-RBAC-002 | Finance-role personas are browser-proven | Planned | #298 |

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

## ENT-CTRL-003 - Tenant Approval Policy Configuration

Persona: Admin configuring finance controls.

Status: First slice implemented. Settings exposes an Approval Policy Matrix,
`GET /api/v1/approval-policy/effective` returns tenant policy with system
defaults, `PUT /api/v1/approval-policy/default` lets Admin/Owner users raise
supported review roles, and Inbox policy metadata/enforcement uses tenant
overrides while preserving safe default floors.

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
recent decision timeline. Browser automation is still pending.

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
automation is still pending.

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

Status: Planned under #297.

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

## ENT-RBAC-001 - Auditor Read-Only Persona

Persona: External CPA or auditor.

Status: First slice implemented. Current `viewer` role maps to auditor/read-only
personas; API tests prove read-only access to reports, bills/procurement, and
Inbox while denying mutating finance actions. Bills/AP UI disables create,
approval, conversion, and Pay Bills entry actions for read-only users. Browser
automation is still pending.

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

Status: Planned under #298.

Steps:

1. Sign in as each finance persona.
2. Open Inbox, Bills/AP, Invoices/AR, Reports, Accounting, and Settings.
3. Attempt persona-appropriate and persona-restricted actions.
4. Repeat direct API attempts for restricted money, posting, send, and settings actions.

Expected result:

- Product-facing finance personas map to enforced backend roles without
  weakening current RBAC.
- Browser controls are hidden or disabled consistently with API enforcement.
- Auditor and Executive personas remain read-only for finance mutation paths.
- Owner/Admin can still perform settings and final approval workflows.

## ENT-AIOPS-001 - Scheduled Finance Ops Manager Run

Persona: Owner/Admin configuring AI operations.

Status: First slice implemented. Admins can configure the tenant cadence through
Settings or `GET/PUT /api/v1/agents/finance-ops/schedule`. The hourly
Procrastinate worker creates a `scheduled_finance_ops_manager` workflow run and
a reviewed `copilot_create_finance_ops_action_plan` Inbox task when the cadence
is due. Browser automation is still pending.

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

## ENT-AIOPS-002 - Inbox Escalation

Persona: Controller with stale high-risk work.

Status: First slice implemented. The scheduled Finance Ops Manager creates
separate `finance_ops_escalation` Inbox notices for stale or high-risk source
tasks. The notice payload summarizes safe metadata and points back to the
source task; it does not copy the full source payload.

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

Status: First slice implemented. Settings now exposes Finance Ops Manager
cadence, enabled state, period mode, work item limit, stale-approval windows,
and escalation toggle. Admin/Owner users can save changes; Manager users can
inspect but not edit.

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

## ENT-P2P-001 - Vendor Invoice Coding Exception

Persona: AP Lead.

Status: First slice implemented. Vendor invoice extraction now serializes vendor
match, GL coding suggestions, match/coding status, and review exceptions into
the Inbox payload. Approval materializes bills through the Bills service path,
creates reviewed bill lines, preserves source document linkage, and stores
`vendor_invoice_review` evidence on the bill. Browser automation is still
pending.

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

## ENT-P2P-002 - Duplicate Or Mismatch Review

Persona: AP Lead and Controller.

Status: First slice implemented. Possible duplicate vendor invoice drafts are
blocked on approve-as-is. They require approve-with-edits with
`duplicate_review.approved_duplicate=true` and a reason. PO mismatch validation
continues to run through the Bills service path during materialization and bill
approval.

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

## ENT-P2P-003 - Browser Vendor Invoice Exception Review

Persona: AP Lead and Controller.

Status: First slice implemented. Inbox vendor invoice cards now expose AP review
evidence including vendor match, duplicate guard, source document, GL coding
suggestions, project/customer hints, and required correction exceptions. Possible
duplicates open the edit drawer for a reviewer-entered reason before approval.
Bill detail shows the preserved `vendor_invoice_review` evidence after
materialization. Playwright automation is still pending.

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

## ENT-R2R-001 - Close Evidence Package

Persona: Controller.

Status: First slice implemented. Close package responses now include
`readiness_evidence` for AR, AP, WIP, GL, approvals, and overrides. Close status
also includes unposted journals, incomplete close tasks, and recorded overrides
so the package and lock guard share the same readiness model. Browser automation
is still pending.

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

## ENT-R2R-002 - Close Override With Reason

Persona: Owner/Admin.

Status: First slice implemented. Close overrides are durable rows with blocker
code, reason, actor, timestamp, and blocker evidence. The period-lock API still
returns the existing blocker errors unless the matching override is recorded
or submitted with the lock request. Override evidence is visible in the close
package.

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
- Browser: record override reason from close review UI once the richer close
  wizard exists, then verify the close package displays it.

## ENT-R2R-003 - Close Wizard And Statement Commentary

Persona: Controller and Owner/Admin.

Status: First slice implemented. The Accounting close package panel now lets
Admin/Owner users record a blocker-specific override reason, override evidence
includes actor role, close package commentary carries structured evidence, and
Copilot financial statement packages include close-readiness warnings plus
management commentary sourced from the close package.

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

## ENT-OPS-001 - Rate-Limited Endpoint

Persona: Security reviewer.

Status: First slice implemented. App-level in-process rate limiting protects
signup and public invoice token reads. Excess traffic returns a safe `429`
body with `Retry-After`, `X-RateLimit-Limit`, and
`X-RateLimit-Remaining` headers. The limiter is path-scoped so normal
authenticated workflows are not made flaky.

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

Status: First slice implemented. Tenant health summarizes runtime settings,
table/migration reachability, sanitized request/background failure counters,
and recent agent run, agent tool, and workflow failure counts. Output is scoped
to the current tenant and safe for internal operators.

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

Status: Planned under #301.

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
