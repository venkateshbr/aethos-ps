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
| ENT-P2P-001 | Vendor invoice coding exception routes to Inbox and materializes after correction | Implemented first slice; browser automation pending | #284 |
| ENT-P2P-002 | Duplicate or mismatched vendor invoice requires explicit review | Implemented first slice; browser automation pending | #284 |
| ENT-R2R-001 | Close evidence package shows AR/AP/WIP/GL readiness | Planned | #285 |
| ENT-R2R-002 | Close override requires reason and is audit-visible | Planned | #285 |
| ENT-OPS-001 | Rate-limited endpoint fails safely under abuse | Planned | #286 |
| ENT-OPS-002 | Tenant health summary exposes safe operational signals | Planned | #286 |

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

## ENT-AIOPS-001 - Scheduled Finance Ops Manager Run

Persona: Owner/Admin configuring AI operations.

Status: First slice implemented. Admins can configure the tenant cadence through
`GET/PUT /api/v1/agents/finance-ops/schedule`. The hourly Procrastinate worker
creates a `scheduled_finance_ops_manager` workflow run and a reviewed
`copilot_create_finance_ops_action_plan` Inbox task when the cadence is due.
Browser automation is still pending.

Steps:

1. Configure or seed a daily Finance Ops Manager run.
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
- Browser: open Settings workflow runs, filter for scheduled Finance Ops
  Manager, open Inbox, approve the plan, and verify Plan Items were created.
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

## ENT-R2R-001 - Close Evidence Package

Persona: Controller.

Steps:

1. Generate close readiness for a period.
2. Open close evidence package.
3. Inspect AR, AP, WIP, journal, and approval blockers.
4. Follow links to supporting records.

Expected result:

- Evidence package is built from real records.
- Blockers are actionable.
- Package ties to reports and journal evidence.

## ENT-R2R-002 - Close Override With Reason

Persona: Owner/Admin.

Steps:

1. Create a close blocker that would normally prevent locking.
2. Attempt close as Controller.
3. Attempt authorized override as Owner/Admin with a reason.
4. Inspect decision history and close package.

Expected result:

- Unauthorized close remains blocked.
- Authorized override requires reason.
- Override is visible in close evidence and audit trail.

## ENT-OPS-001 - Rate-Limited Endpoint

Persona: Security reviewer.

Steps:

1. Exercise a rate-limited public/auth endpoint repeatedly from the same client context.
2. Verify normal traffic succeeds under the threshold.
3. Verify excess traffic fails with a safe response.

Expected result:

- Rate-limit response does not leak internals.
- Tests can reset or isolate rate-limit state.
- Legitimate E2E setup is not made flaky.

## ENT-OPS-002 - Tenant Health Summary

Persona: Internal operator.

Steps:

1. Open or call tenant health summary.
2. Verify safe checks for runtime config, migrations, queues, provider readiness, and recent failures.
3. Confirm no secrets or raw credentials are exposed.

Expected result:

- Operators get useful health signals.
- Tenant users do not see unauthorized operational data.
- Health output is stable enough for support runbooks.
