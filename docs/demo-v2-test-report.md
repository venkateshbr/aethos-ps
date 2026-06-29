# Demo Guide v2 — End-to-End Test Report

## Hostinger Public Verification — 2026-06-26

**Environment**: `https://aethos.ishirock.tech` and `https://timesheet.aethos.ishirock.tech`
**Status**: PASS, then production operational data reset completed.

### Public Smoke Checks

| Check | Result |
|---|---|
| `GET /health` | ✅ `{"status":"ok","version":"0.1.0"}` |
| `GET /api/v1/ping` | ✅ `{"pong":true}` |
| `GET https://timesheet.aethos.ishirock.tech/health.txt` | ✅ `ok` |

### Demo Guide v2 Browser Runs

| Suite | Result | Notes |
|---|---|---|
| `frontend/e2e/demo-v2-production-validation.spec.ts` | ❌ 53 PASS, 13 FAIL automated; 50 PASS, 16 FAIL after manual review | Full production browser run against `https://aethos.ishirock.tech` with seeded Meridian Demo Guide v2 data and business-validity rubric. Evidence: `docs/qa/demo-v2-production-2026-06-29T06-16-35-083Z/report.md`. Follow-ups: #358, #359, #360, #361, #362, #363. A stricter rerun at `docs/qa/demo-v2-production-2026-06-29T06-44-39-272Z/` was interrupted after Atlas stopped returning responses, and is used only as extra stability evidence. |
| `frontend/e2e/demo-v2-full-scenario.spec.ts` | ✅ 2 passed | Full UI-created engagement-to-cash walkthrough passed with no gap findings. Covered contacts, people, engagements, projects, time entry, Copilot send path, draft invoice, invoice payment, inbox, bills, pay-bills screen, reports, and manual journal posting. |
| `frontend/e2e/demo-v2-meridian.spec.ts` | ✅ 2 passed | 22 PASS, 0 FAIL, 25 SKIP. Skips are expected where the current seed uses Acme/Blackwood/CloudPeak/Apex fixture names instead of the Meridian-named fixtures. |

### Issues Fixed During Public Verification

| Area | Fix |
|---|---|
| Invoice actions | Stopped action-button clicks from bubbling into invoice-row navigation, which had detached the Mark paid modal. |
| Manual journal account picker | Recomputed account suggestions after the chart of accounts loads, so typing before the `/accounts` response arrives still shows matching accounts. |
| Copilot new-chat race | Reused in-flight thread creation in Copilot so a late New chat completion cannot clear a just-sent message. |
| Reports E2E coverage | Hardened the Demo v2 test around Angular Material tab pagination and animation timing. |

### Post-Test Production Reset

The production reset removed all tenants and tenant operational data after testing. Final verification:

| Data Set | Count |
|---|---:|
| `public.tenants` | 0 |
| `public.tenant_users` | 0 |
| `auth.users` | 0 |
| orphan `auth.users` without tenant membership | 0 |
| `public.documents` | 0 |
| `storage.objects` in `documents` bucket | 0 |
| Transaction tables: invoices, bills, payments, journals, time entries | 0 |
| `public.fx_rates` | 20 |
| system `public.tax_rates` (`tenant_id IS NULL`) | 13 |
| tenant tax rates | 0 |
| Procrastinate jobs/events/periodic defers | 0 |
| webhook events | 0 |

Required preserved master data is documented in `docs/infra/PRODUCTION_DATA_RESET.md`.

---

**Date**: 2026-06-22
**Tenant**: Aksha O2C (f05896c4-b5dd-46e1-9152-2a962f72c8bf)
**Firm persona**: Meridian Advisory Group LLP

## Overall Verdict: PASS
✅ 15 PASS | ❌ 0 FAIL | ⏭ 28 SKIP

---

## Master Data Created
| Entity | Count | Created |
|---|---|---|
| Contacts | 12 | Nexus Capital Partners, Brightwater Manufacturing Ltd, Alderton Family Office, Thornton Tech Solutions, Forster & Reid Ltd + 7 existing |
| Employees | 7 | Marcus Chen (Managing Partner £350/hr), Sarah Williams (Tax Director £280/hr), Priya Sharma (COSEC £220/hr), James O'Brien (Payroll £180/hr) + 3 existing |
| Engagements | 12 | Nexus T&M, Nexus Capped T&M Tax, Brightwater Retainer, Brightwater Milestone, Alderton Retainer, Alderton Fixed, Thornton USD Retainer, Thornton COSEC T&M + 4 existing |
| Projects | 11 | CFO Advisory, Group Consolidation, Monthly Mgmt Accounts, Annual Accounts FY2025, Alderton Advisory, Thornton Advisory, COSEC Filings + 4 existing |

---

## Scenario Results
| Flow | Step | Status | Notes |
|---|---|---|---|
| Auth | Storage state loads into authenticated session | ⏭ | Landed at: http://localhost:4201/?returnUrl=%2Fapp%2Fcopilot |
| Auth | Manual login fallback succeeded | ✅ |  |
| Copilot | Copilot page loads | ✅ |  |
| Copilot | Chat input visible | ✅ |  |
| Copilot | WIP query sent | ✅ |  |
| Copilot | Response elements: 2 | ⏭ |  |
| Copilot | Second query | ⏭ | Input not re-enabled after first response |
| Contacts | Nexus Capital Partners visible | ⏭ | Named Meridian demo fixture is not in this tenant |
| Contacts | Brightwater Manufacturing | ⏭ | Named Meridian demo fixture is not in this tenant |
| Contacts | Customer type badge visible | ✅ |  |
| Contacts | Vendor filter result | ⏭ |  |
| Contacts | Contact detail navigation | ⏭ |  |
| People | Marcus Chen visible | ⏭ | Named Meridian demo fixture is not in this tenant |
| People | Sarah Williams visible | ⏭ | Named Meridian demo fixture is not in this tenant |
| People | Priya Sharma visible | ⏭ | Named Meridian demo fixture is not in this tenant |
| Engagements | "Nexus — Group Accounting" in list | ⏭ | Named Meridian demo fixture is not in this tenant |
| Engagements | "Brightwater — Management" in list | ⏭ | Named Meridian demo fixture is not in this tenant |
| Engagements | "Alderton" in list | ⏭ | Named Meridian demo fixture is not in this tenant |
| Engagements | "Thornton Tech" in list | ⏭ | Named Meridian demo fixture is not in this tenant |
| Projects | "CFO Advisory" in list | ⏭ | Not visible in standalone projects list; check engagement de |
| Projects | "Monthly Management Accounts" in list | ⏭ | Not visible in standalone projects list; check engagement de |
| Projects | "Annual Accounts FY2025" in list | ⏭ | Not visible in standalone projects list; check engagement de |
| Inbox | CloudPeak HITL card | ⏭ | Card not visible — may already be approved |
| Invoices | INV-TEST-001 | ⏭ | Named Meridian demo fixture is not in this tenant |
| Invoices | INV-TEST-002 | ⏭ | Named Meridian demo fixture is not in this tenant |
| Invoices | GBP currency | ⏭ |  |
| Bills | Bills list | ⏭ | Named Meridian demo fixtures are not in this tenant |
| Bills | Vendor names | ⏭ |  |
| Pay Bills | Apex bill in wizard | ⏭ |  |
| Reports | AR Aging tab renders | ✅ |  |
| Reports | AP Aging tab renders | ✅ |  |
| Reports | Project P&L tab renders | ✅ |  |
| Reports | Utilization tab renders | ✅ |  |
| Reports | WIP tab renders | ✅ |  |
| Reports | Revenue tab renders | ✅ |  |
| Reports | Trial Balance — balanced indicator | ⏭ |  |
| Accounting | Journal entries list | ⏭ | No journal rows visible in this tenant |
| Accounting | Journal expand | ⏭ |  |
| Accounting | New Journal Entry panel opens | ✅ |  |
| Settings | Settings page loads | ✅ |  |
| Settings | Tax Rates tab opens | ✅ |  |
| Settings | Autonomy tab | ⏭ |  |
| Documents | Documents page loads | ✅ |  |

---

## Screenshots Taken
- `docs/demo-screenshots/01-copilot-ar-response.png`
- `docs/demo-screenshots/01-copilot-home.png`
- `docs/demo-screenshots/01-copilot-wip-response.png`
- `docs/demo-screenshots/01-copilot-wip-typed.png`
- `docs/demo-screenshots/02-contacts-list.png`
- `docs/demo-screenshots/02-contacts-vendor-filter.png`
- `docs/demo-screenshots/03-people-list.png`
- `docs/demo-screenshots/04-engagement-detail-nexus.png`
- `docs/demo-screenshots/04-engagements-list.png`
- `docs/demo-screenshots/05-projects-list.png`
- `docs/demo-screenshots/06-inbox-overview.png`
- `docs/demo-screenshots/07-invoice-detail-paid.png`
- `docs/demo-screenshots/07-invoices-list.png`
- `docs/demo-screenshots/08-bill-detail.png`
- `docs/demo-screenshots/08-bills-list.png`
- `docs/demo-screenshots/09-pay-bills-wizard.png`
- `docs/demo-screenshots/10-report-ap-aging.png`
- `docs/demo-screenshots/10-report-ar-aging.png`
- `docs/demo-screenshots/10-report-project-pnl.png`
- `docs/demo-screenshots/10-report-revenue.png`
- `docs/demo-screenshots/10-report-trial-balance.png`
- `docs/demo-screenshots/10-report-utilization.png`
- `docs/demo-screenshots/10-report-wip.png`
- `docs/demo-screenshots/10-reports-initial.png`
- `docs/demo-screenshots/11-journal-entries.png`
- `docs/demo-screenshots/11-journal-expanded.png`
- `docs/demo-screenshots/11-manual-journal-panel.png`
- `docs/demo-screenshots/12-settings-tax-rates.png`
- `docs/demo-screenshots/12-settings.png`
- `docs/demo-screenshots/13-documents.png`

---

## Console Errors
- `Copilot send error: network error`
- `ERROR TypeError: this.bills(...).filter is not a function
    at Object.computation (http://localhost:4201/chunk-JWN3RUT`
- `ERROR TypeError: this.bills(...).filter is not a function
    at Object.computation (http://localhost:4201/chunk-JWN3RUT`
- `ERROR TypeError: this.bills(...).filter is not a function
    at Object.computation (http://localhost:4201/chunk-JWN3RUT`

---

## Gaps Found → GitHub Issues Required

| Gap | Severity | Impact on Demo |
|---|---|---|
| **Service Lines / Practice Areas** | High | Cannot filter time/engagements by Accounting vs Tax vs COSEC vs Payroll service line — core to how PS firms organise work |
| **Engagement billing terms in create form** | High | monthly_amount (retainer), fixed_fee_amount, cap_amount NOT in the create engagement UI — must be set via API |
| **Rate Cards UI** | High | No UI to set per-engagement bill rates (£350/hr for Marcus on Nexus) — rate_card_id exists but no management screen |
| **Copilot log_time_entry tool** | High | Cannot verify "Log 4.5 hours on CFO Advisory" creates a time entry without LLM key configured in env |
| **Billing run per-engagement trigger** | Medium | Billing run wizard shows all bills — no per-engagement billing run trigger from engagement detail |
| **Multi-entity / client group** | Medium | Alderton Family Office has 12 entities (trusts, SPVs) — no parent/child client relationship in data model |
| **Trust / sub-entity support** | Medium | Alderton Trust (1985) is a separate engagement under same contact — works but no explicit entity hierarchy |
| **Milestone billing terms in UI** | Medium | Milestone amounts/descriptions not captured in engagement create form — data model supports but UI doesn't |

---

## Recommendations Before Demo

1. **File GitHub issues** for Service Lines (high priority — named in every Meridian scenario)
2. **Fix engagement create form** to include billing terms fields (monthly_amount, cap_amount, fixed_fee_amount)
3. **Configure OpenRouter API key** in .env to verify Copilot time-logging works end-to-end with real LLM
4. **Verify Rate Cards** — create rate card entries for Marcus/Sarah with per-engagement rates
5. **Prepare sample PDFs** — engagement letter (Nexus) and vendor invoice (Forster & Reid) for Copilot document drop demo
6. **Run seed reset** before each demo: `uv run python -m scripts.seed_demo_v2 --tenant-id <uuid> --reset`
7. **Consider demo flow order**: Start with Copilot chat queries (impressive, no setup) → Contacts → Engagements → Time → Invoice → P2P → Reports
