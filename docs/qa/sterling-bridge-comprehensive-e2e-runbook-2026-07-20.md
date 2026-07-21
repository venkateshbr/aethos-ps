# Sterling Bridge Advisory — Comprehensive Production E2E Runbook

> **Environment:** `https://aethos.ishirock.tech` (production) · Supabase `glcljucaayeesvrsjths`
> **Deploy SHA under test:** `3b68ee280d774d19c6e817310634fafb6da650cf`
> **Run ID:** `SB-E2E-20260720` · **Started:** 2026-07-20
> **Driver:** headless Chromium via Playwright, all product writes through the visible UI
> **Credentials:** `sterlingbridge_e2e_credentials.json` (gitignored, mode 0600) — never pasted here
> **Screenshots/evidence:** `sterlingbridge_e2e_evidence/` (gitignored)

This runbook is the founder-facing record of a full financial-operations shakedown of a
clean production tenant: reset → clean signup → firm build → O2C → P2P → R2R →
controls/AI-ops → financial statements. Each phase records what was driven in the
browser and the evidence to validate it.

## 0. How to validate this run yourself

1. Go to **https://aethos.ishirock.tech/login**.
2. Sign in as the owner: `owner-sterlingbridge-c678c9@aethos-qa.dev` — password is
   in `sterlingbridge_e2e_credentials.json` (repo root, gitignored, mode 0600).
3. Tenant: **Sterling Bridge Advisory Group** (`77dbdb2a-561e-4bb1-896f-396151247da3`).
4. Check **Invoices** (INV-0001…0007), **Bills** (BILL-0001 paid, BILL-0002
   approved), **Accounting → Journal Entries** (incl. the accrual + its reversal,
   and period 2026-05 **Locked**), and **Reports** → set both period controls to
   **June 2026** → Income Statement / Balance Sheet / Cash Flow / Trial Balance
   should show the figures in §7.
5. For RBAC: sign in as the read-only viewer `viewer-sterlingbridge@aethos-qa.dev`
   (password in the manifest) — Invoices show no Approve/Send/Pay actions.
6. Screenshots + raw statement JSON: `sterlingbridge_e2e_evidence/`.

---

## 1. The modeled firm — Sterling Bridge Advisory Group LLP

A US-headquartered professional-services firm used as the realistic test subject.

| Attribute | Value |
|---|---|
| Legal form | LLP (US) |
| Base currency | **USD** |
| Target annual revenue | **~$52.0M** (> $50M) |
| Target EBITDA | **~39% (~$20.3M)** |
| Customers (modeled) | ~100, 1–2 engagements each (~150 engagements) |
| Headcount (modeled) | ~185 billable consultants + ~35 G&A |

### 1.1 Service lines & billing mix

| Service line | Primary billing model | Modeled annual revenue |
|---|---|---|
| Management Consulting | T&M + capped-T&M | $16.0M |
| Technology Advisory | fixed-fee + milestone | $12.5M |
| Risk & Regulatory | retainer | $9.0M |
| Transaction Advisory | milestone | $8.5M |
| Managed Finance Operations | retainer + per-unit | $6.0M |
| **Total** | | **$52.0M** |

### 1.2 Target P&L bridge (how 39% EBITDA is reached)

| Line | Amount | % of revenue |
|---|---|---|
| Revenue | $52,000,000 | 100.0% |
| Direct delivery cost (consultant salaries, subcontractors) | ($24,000,000) | (46.2%) |
| **Gross profit** | **$28,000,000** | **53.8%** |
| Sales, G&A, facilities, technology, admin | ($7,700,000) | (14.8%) |
| **EBITDA** | **$20,300,000** | **39.0%** |

> **Feasibility note (browser-only constraint).** Entering ~100 customers and ~150
> engagements plus every downstream transaction *by hand through the UI* is not
> achievable in a practical unattended window. Per the agreed approach, the browser
> run drives a **representative subset** sized to complete reliably; this section is
> the full modeled firm, and §Coverage records the delta between the model and what
> was physically entered so the numbers can be validated in proportion.

---

## 2. Phase 0 — Production reset (COMPLETE ✅)

Wiped all pre-existing tenants/transaction data; preserved platform config/master.

- **Tool:** `backend/scripts/reset_operational_data.py --execute --confirm DELETE_ALL_TENANTS` (via Supabase session pooler).
- **Pre-reset state:** 80 tenants, 104 auth users, 44 storage docs (all machine-generated QA/demo/e2e fixtures — captured in `docs/qa/pre-reset-manifest-2026-07-20.json`).
- **Post-reset verification:**

| Check | Result | Check | Result |
|---|---|---|---|
| tenants | 0 ✅ | fx_rates | 20 ✅ preserved |
| tenant_users | 0 ✅ | tax_rates (system) | 13 ✅ preserved |
| auth.users | 0 ✅ | security roles/duties/privileges | 22/17/73 ✅ preserved |
| orphan auth users | 0 ✅ | documents bucket | 1 ✅ (objects 0) |

---

## 3. Phase 1 — Clean tenant registration via browser (COMPLETE ✅)

Registered the firm through the public `/signup` wizard end-to-end in the browser.

- **Steps driven:** Account (firm name, owner email, password, country=US) → Plan (Growth, monthly) → Card (Stripe **test mode**, `4242…`) → **Start 14-day trial** → landed `/app/copilot`.
- **Result (verified in DB):**

| Field | Value |
|---|---|
| tenant_id | `77dbdb2a-561e-4bb1-896f-396151247da3` |
| name | Sterling Bridge Advisory Group |
| status | **active** |
| trial_ends_at | 2026-08-03 |
| base_currency | USD |
| owner | `owner-sterlingbridge-…@aethos-qa.dev` (in credentials file) |
| baseline provisioned | 24 COA accounts, 17 catalogue services |

- **Evidence:** `sterlingbridge_e2e_evidence/screenshots/` (account/plan/card/copilot-home).

---

## 4. Phase 2 — Firm master data (COMPLETE ✅)

All created through the browser UI (idempotent Playwright scripts):

| Object | Count | Detail |
|---|---|---|
| Customers | 12 | Northwind, Belmont, Cascade, Ironwood, Sterling Retail, Vertex, Harbor Point, Cedar Grove, Atlas, Meridian, Brightpath, Summit Ridge |
| Vendors | 2 | Apex Contractors, CloudScale Infrastructure |
| Services | 4 | Management Consulting, Risk & Regulatory Retainer, Transaction Advisory, Technology Advisory |
| Engagements | 5 | one per billing model: retainer ×2, T&M, fixed-fee, milestone |
| Projects | 5 (+auto) | one delivery project per engagement |
| Tax rate | 1 | US Sales Tax 0% |

## 5. Phase 3 — Order-to-Cash (COMPLETE ✅)

Five invoices drafted → approved → sent through the UI; three paid.

| Invoice | Customer | Amount | Status |
|---|---|---|---|
| INV-0001 | Northwind | $15,000 | paid |
| INV-0002 | Belmont | $48,000 | paid |
| INV-0003 | Cascade | $125,000 | sent (AR) |
| INV-0004 | Ironwood | $42,500 | sent (AR) |
| INV-0005 | Sterling Retail | $6,000 | paid |

Auto-posted journals (guarded path): DR Accounts Receivable / CR Revenue on approval
(×5 = $236,500); DR Bank / CR AR on payment (×3 = $69,000). **AR outstanding $167,500.**

## 6. Phase 4 — Procure-to-Pay (COMPLETE ✅)

| Bill | Vendor | Amount | Lifecycle |
|---|---|---|---|
| BILL-0001 | Apex Contractors | $28,000 | approved → batch → **settled** (DR Expense/CR AP, then DR AP/CR Bank) |
| BILL-0002 | CloudScale | $12,000 | approved (DR Expense/CR AP; AP outstanding) |

Vendor payment batch ran the full **prepare → approve → export CSV → mark-sent →
settle** lifecycle through the Pay Bills wizard. **Expenses $40,000; AP outstanding $12,000.**

## 7. Phase 5 — Record-to-Report — financial statements (COMPLETE ✅)

Trial balance (base USD), captured from the GL — **balanced**:

| Account | Net |
|---|---|
| 1100 Bank | $41,000 |
| 1200 Accounts Receivable | $167,500 |
| 2000 Accounts Payable | $(12,000) |
| 4000 Revenue | $(236,500) |
| 5000 Expenses | $40,000 |
| **Totals** | **DR $373,500 = CR $373,500 ✅** |

Statements rendered by the Reports UI for period **2026-06** (evidence:
`sterlingbridge_e2e_evidence/statements-2026-06_2026-06.json`):

| Income Statement | | Balance Sheet (as-of 2026-06) | | Cash Flow (2026-06) | |
|---|---|---|---|---|---|
| Total Revenue | $236,500.00 | Total Assets | $208,500.00 | Operating | $41,000.00 |
| Total Expenses | $40,000.00 | Total Liabilities | $12,000.00 | Investing | $0.00 |
| **Net Income** | **$196,500.00** | Total Equity | $196,500.00 | Financing | $0.00 |
| | | (A = L + E ✅) | | Ending cash | $41,000.00 |

The statements match the trial balance to the cent, and the accounting identity
holds: **Assets $208,500 = Liabilities $12,000 + Equity $196,500.**

## 8. Coverage map — modeled firm vs browser-entered

Per the agreed approach (browser-only, representative subset, delta flagged):

| Dimension | Modeled ($52M firm) | Entered via browser | Rationale for delta |
|---|---|---|---|
| Customers | ~100 | 12 | UI-time bound; covers all segments |
| Engagements | ~150 | 5 | one per billing model (retainer/T&M/fixed/milestone) |
| Revenue booked | $52.0M / yr | $236,500 (one month, sample) | proportional slice, not full run-rate |
| Billing models exercised | all 6 | 4 (retainer, T&M, fixed-fee, milestone) | capped-T&M and mixed not yet run |
| Currencies | USD + 4 | USD + **GBP** | GBP invoice with FX provenance (§10.3) |
| Tax | inclusive | **0% and 8.875%** | tax split → Sales Tax Payable (§10.1) |
| R2R controls | manual JE, reversal, lock | **all ✅** | §10.2 |
| RBAC / SoD | 22 roles | owner + Executive Viewer | least-privilege proven (§10.4) |
| Cycles proven end-to-end | O2C, P2P, R2R | **all three ✅** | full double-entry → statements |

> The point of this slice was **correctness of the full financial-operations
> chain**, which is proven end-to-end. Scaling the dataset toward the full
> ~100-customer / $52M model is additional browser runtime, not additional
> product coverage.

## 9. Remaining (not yet run)

- **Aethos Nous answering** — blocked by **F-3** (no assistant response); the
  agent-first copilot flows (document-drop extraction → Inbox, AI billing-run,
  AI collections drafting) cannot be demonstrated until that is fixed.
- Collections **send** (reminders were prompted read-only; drafting/sending to
  Inbox not exercised).
- Dataset scale-up toward ~100 customers / $52M; capped-T&M and mixed billing.
- Time entries → timesheet approval → WIP (invoices here used direct line items).
- Bill-pay CSV/NACHA field validation; Stripe payment-link / Connect payout path.

---

## 10. Extended scenarios (Task 8) — appended live

### 10.1 Tax-inclusive invoice (COMPLETE ✅)

Created a non-zero US sales tax and drafted a tax-inclusive invoice on the Belmont
T&M engagement, approved + sent.

| Invoice | Subtotal | Tax | Total | Journal |
|---|---|---|---|---|
| INV-0006 | $20,000.00 | $1,776.00 | $21,776.00 | DR 1200 AR $21,776 / CR 4000 Revenue $20,000 / **CR 2300 Sales Tax Payable $1,776** |

Revenue and tax are correctly split into separate GL accounts; the journal
balances. See finding **F-2** on rate precision.

### 10.2 R2R controls — manual journal, reversal, period lock (COMPLETE ✅)

- **Manual journal:** posted an accrual `JE-D31E8B0E` — DR 6000 Software Expense
  $1,500 / CR 2100 Accrued Reimbursement $1,500, with business reason, via the
  Post Manual Journal dialog.
- **Reversal (immutability):** reversed it through the visible **Reverse → reason
  → Post** flow. The original entry is preserved; `JE-7313ED05` "Reversal of
  JE-D31E8B0E" posted the opposite lines. Accounts 6000 and 2100 both net **$0.00**
  — corrections are made by reversing entry, never by editing posted history.
- **Period lock:** locked **2026-05** through the close-tasks UI (Lock period →
  confirm; HTTP 200; status shows "Locked by … 09:55 UTC"). A backdated journal
  dated `2026-05-15` was then **rejected with HTTP 422**: *"Accounting period
  2026-05 is locked. Choose an open entry date or unlock the period before
  posting."* — the Accounting Guardian enforcing the lock.

### 10.3 Multi-currency invoice + FX provenance (COMPLETE ✅)

Created a **GBP** engagement (Vertex UK Advisory, fixed-fee £10,000) and invoiced it.

| | Foreign | Base (USD) | Rate | Provenance |
|---|---|---|---|---|
| INV-0007 | £10,000.00 GBP | **$12,666.00** | GBP→USD 1.2666 | `fx_rate_id` set on invoice + both journal lines |

Journal: DR 1200 AR / CR 4000 Revenue, each storing both the £10,000 transaction
amount **and** the $12,666 base amount, linked to the immutable `fx_rates` row
(rate_date 2026-05-19). Dual-amount storage + rate provenance are auditable
source→journal→statement.

### 10.4 RBAC / segregation-of-duties — 2nd user via UI (COMPLETE ✅)

Invited a second user through **Settings → Users** and validated least-privilege.

- **User:** `viewer-sterlingbridge@aethos-qa.dev`, role **Executive Viewer**
  (credentials in the manifest).
- **Forced password change:** first login landed on `/app/profile` and required
  rotating the admin-set temporary password before use.
- **Least-privilege (verified in `tenant_user_effective_privileges`):** 20
  read-only privileges — `invoices.read`, `bills.read`, `bill_payments.read`,
  `reports.read` — and **no** write/approve/money-movement privileges.
- **UI reflects it:** as the viewer, the Invoices list exposed **zero**
  Approve / Send / Mark-paid controls; no Draft/Post/Pay actions were available.

This demonstrates the catalogue RBAC + segregation of duties: a non-owner role
can inspect permitted data but cannot act on money or the ledger.

### 10.5 Operational Health + Aethos Nous AI ops (COMPLETE ✅)

- **Operational Health (✅):** Settings → Operational Health renders — runtime
  status, finance role/privilege summary, and health surfaces are visible.
- **Aethos Nous finance-ops prompt (✅ on re-test):** a read-only prompt ("total
  outstanding AR") rendered a **correct** answer in the browser in ~9s —
  *"Your total outstanding accounts receivable is $201,942.00 … 0-30 day bucket"*
  ($201,942 = $167,500 + $21,776 + $12,666 ✅), `model=nous:hermes_agent`,
  `finish_reason=stop`, assistant message persisted. The earlier empty responses
  were a **transient AI-runtime outage** — see **F-3** for the diagnosis and the
  frontend robustness fix.

---

## 6. Findings & fixes

### F-1 (P0) — Production reset destroys system RBAC, locking out every new tenant

- **Symptom:** On the freshly-registered tenant, the owner's **Draft invoice**
  button (and every permission-gated action) was disabled with
  `title="Requires invoice draft permission"`. The owner had **0 effective
  privileges**.
- **Root cause:** `backend/scripts/reset_operational_data.py` deleted **all** rows
  of `public.security_role_duties` (94 → 0). That table has no `tenant_id` but is
  an FK-child of `security_roles` (which does), so the reset's FK-closure
  classified it as tenant-dependent and wiped the **system** role→duty mappings —
  master data, not tenant data. With roles mapped to no duties, every role grants
  zero privileges.
- **Impact:** Any production reset silently breaks RBAC for **all** future
  tenants; a brand-new tenant owner cannot draft/post/send invoices, pay bills,
  post journals, etc. The tenant is unusable for finance operations.
- **Repair (applied):** re-ran migration `0096_dynamics_style_security_catalog.sql`
  (idempotent, `ON CONFLICT DO NOTHING`) via the session pooler →
  `security_role_duties` restored to 94; owner now has **71** effective
  privileges incl. `invoices.{draft,post,send,mark_paid,read}`.
- **Source fix (applied):** added `security_role_duties`,
  `security_duty_privileges`, `security_duties`, `security_privileges` to
  `PROTECTED_PUBLIC_TABLES` in `reset_operational_data.py`; verified via dry-run
  that they are no longer targeted for deletion. Updated
  `docs/infra/PRODUCTION_DATA_RESET.md` (required master data + post-reset checks).
- **Follow-up:** if tenant-scoped **custom** roles are ever introduced, replace the
  blanket protection with a role-scoped delete of their `security_role_duties`
  rows (system-role mappings must always survive).

### F-2 (low) — Tax-rate precision rounds to 4 decimal places

- **Symptom:** entering `8.875`% stored `rate = 0.0888` (i.e. 8.88%), so a $20,000
  line taxed at "8.875%" produced **$1,776.00** rather than the exact $1,775.00.
- **Impact:** jurisdictions with 3-decimal statutory rates (e.g. NYC 8.875%) are
  rounded at the 4th decimal, causing small per-invoice tax deltas. Not a blocker;
  the split and posting are otherwise correct.
- **Recommendation:** widen the `tax_rates.rate` precision (and the input) to at
  least 5 decimals if exact statutory rates are required.

### F-3 (medium) — Copilot hangs with an empty bubble on a transient AI outage — FIXED

- **Original symptom:** three copilot prompts persisted the **user** message
  (HTTP 201) but produced **no assistant answer** — empty streaming bubble, no
  assistant row server-side, for ~175s.
- **Diagnosis (this session):** *not* a persistent failure. Driving the SAME SSE
  endpoint via the API returned a correct answer (`model=nous:hermes_agent`,
  `finish_reason=stop`), and a browser re-test rendered the answer in ~9s. The
  earlier empties were a **transient AI-runtime outage** (~10:04 UTC). The Nous
  `cts_` context-token fix is separately confirmed working (`atlas_tool_sessions`
  has live rows).
- **The real defect:** the copilot's SSE reader had **no client-side timeout**.
  When the runtime connects (HTTP 200) but then hangs without emitting a
  `delta`/`done`/`error` frame, `await reader.read()` blocks indefinitely and the
  UI shows an empty "streaming" bubble forever — looking broken instead of
  surfacing a retry-able error.
- **Fix (applied, `frontend/.../copilot.component.ts`):**
  1. a **60s idle stream watchdog** (`AbortController`) that re-arms on every data
     chunk and aborts a stalled stream, showing *"Nous took too long to respond."*;
  2. an **empty-response guard** — if the stream closes having produced nothing,
     show *"Nous is temporarily unavailable"* instead of a silent blank bubble.
  Typechecks clean (`tsc --noEmit`). Deploys with the frontend image.
- **Recommendation (infra, not code):** set `ATLAS_HERMES_FALLBACK_TO_BASIC=true`
  in production so a Hermes outage degrades to the built-in runtime (per the
  "agents never block — graceful degradation" rule) rather than erroring; and add
  an agent-eval smoke asserting an assistant message is produced.

---

_Living document — updated per phase during run `SB-E2E-20260720`._
