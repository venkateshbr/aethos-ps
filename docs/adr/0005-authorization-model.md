# ADR 0005 — Canonical authorization model (roles, privileges, employee firewall)

- **Status:** Accepted — Founder-approved 2026-07-25 (proceed per the phased plan; each prod authz change still lands in reviewed batches)
- **Date:** 2026-07-25
- **Deciders:** Founder (approval gate) · Prahari (security) · Vastu (architecture)
- **Issue:** #378 (P0 Security) — parent #368

> This ADR is the **design review** #378 requires *before* any production
> authorization change. It ratifies what is already built, and proposes the
> remaining changes for approval. **No production authz code changes until this is
> Accepted.**

## Context

Authorization today has three layers that grew separately:

1. **Ordinal role gate** — `require_role(UserRole.x)` over an 8-value legacy enum
   (`owner > admin > manager > approver > member > viewer/auditor > employee`,
   `app/core/rbac.py`). A `>=` hierarchy check.
2. **Privilege gate** — `require_privilege("code")` resolves the caller's
   **effective privileges** from the enterprise catalogue
   (`security_roles → security_role_duties → security_duties →
   security_duty_privileges → security_privileges`, migration `0096`).
3. **RLS** — every tenant table policy calls
   `public.is_tenant_member(auth.uid(), tenant_id)` (migration `0017`).

The launch audit (#378) found: specialized roles projected onto a small legacy
set, many routes requiring only authentication, authorization trusting a global
JWT role before resolving active-tenant membership, and RLS not implementing the
documented employee firewall.

### What is already true in code (this ADR ratifies it)

| # | Audit requirement | Current state |
|---|---|---|
| AC-2 | Resolve permissions from **active-tenant membership** every request | **Done** — `_resolve_role` (`rbac.py`) makes the `tenant_users` row for the *targeted* tenant authoritative; a tenant the caller isn't an active member of resolves to `viewer` (no authority). |
| AC-2 | **Reject** JWT role claims that disagree with membership | **Done** — `_coerce_role` ignores the JWT `app_metadata.role` in favour of membership and logs `jwt_role_membership_mismatch`. The JWT role is used only when there is **no** tenant context to verify against. |
| AC-7 | Route/method/role/data-scope matrix **executable in CI** | **Done** — `require_role`/`require_privilege` expose `aethos_min_role`/`aethos_privilege`; `tests/unit/test_authz_matrix.py` asserts each sensitive handler's gate by signature introspection (no live stack). |
| AC-3 | 22 tenant-visible roles enforced as explicit capabilities | **Partial** — the 22 catalogue roles (`0096`) each map through duties to an explicit **privilege set** *and* a `legacy_role`. Where a route uses `require_privilege`, the distinct capability bites; where it uses `require_role`, the 22 collapse onto the 8-level ordinal. |
| AC-4 | Employee limited to timesheets/self at **API and RLS** | **API: done** — `employee` sits at hierarchy 0, rejected by every ERP `require_role` gate; timesheet routes use `get_current_employee`. **RLS: NOT done** — `is_tenant_member` is true for *any* active member including `timesheet_employee`, so a portal login can read ERP tables directly via PostgREST. |
| AC-6 | Frontend nav reflects server perms, never substitutes | **Endpoint done** — `GET` effective permissions (`security.py` → `effective_permissions`). Frontend must consume it and never gate on hidden nav alone. |

So the sharp remaining work is **AC-3 (canonical gate), AC-4 (RLS employee
firewall), AC-5 (the negative-path test matrix), and AC-6 (frontend consumes
server perms).**

## Decision (proposed)

### D1 — Privilege is canonical; ordinal role is a bounded legacy fallback

`require_privilege(code)` over the `0096` catalogue is the **canonical**
authorization primitive. `require_role` remains only for (a) coarse tenant-admin
gates and (b) downstream *business* thresholds (e.g. procurement amount bands)
that legitimately need the projected legacy role. **No new sensitive route may
gate on `require_role` alone**; sensitive money/close/security routes migrate to
`require_privilege`. This resolves AC-3: every tenant-visible role's authority is
its **explicit privilege set**, not an ordinal rank.

### D2 — The 22 roles are the supported set; none are removed

All 22 `is_system` roles in `0096` are retained and each is defined by its duties
→ privileges. Their `legacy_role` projection is an **interop shim** for `require_role`
gates and business thresholds, not the authority of record. AC-3 is satisfied by
D1 + the executable matrix (AC-7) asserting each sensitive route's required
privilege.

### D3 — Tenant-switch & stale-token semantics (ratify current behaviour)

For every tenant-scoped request the effective authority is the caller's **active
membership row for the `X-Tenant-ID` being targeted**. Consequences, all already
enforced and now policy:
- A stale/cross-tenant JWT `role` claim is never trusted over membership.
- Switching tenants requires an active membership in the target tenant; otherwise
  authority is `viewer` (read-only, and still RLS-bounded).
- Deactivation (`tenant_users` inactive) removes authority on the next request —
  no session to revoke.

### D4 — Employee firewall at the RLS layer (**the main new work**)

Introduce an RLS-level distinction between a **full member** and a **timesheet
employee**, so the database enforces the firewall even on direct PostgREST access:

- New SQL helper `public.is_tenant_erp_member(uid, tenant_id)` → true only when the
  membership's resolved `legacy_role` is **not** `employee` (i.e. a real ERP role).
- ERP table policies switch their membership check from `is_tenant_member` to
  `is_tenant_erp_member`. Timesheet/self tables (`time_entries` for own employee
  row, own `employees` profile projection) keep a **self-scoped** policy keyed on
  the caller's `employees.user_id`.
- `is_tenant_member` remains for genuinely shared, non-ERP reads (e.g. the tenant
  row itself, security catalogue reads).

This is a **Tier-1 RLS change across many tables** — it ships behind an audit that
proves no current employee-role user relies on ERP read access, and per-table in
reviewable batches, never as one sweeping migration.

### D5 — Frontend consumes server permissions (AC-6)

The SPA gates actionable UI on the effective-privileges response, and the server
re-checks on every mutation. Hidden navigation is a UX affordance, never a control.

## Options considered

- **Collapse to the 8 legacy roles only** — simplest, but loses the segregation-of-
  duties the 22 roles exist for; rejected (fails AC-3 intent).
- **Privilege-only, delete `require_role`** — cleanest end state, but a large,
  risky one-shot migration of every route + loss of the business-threshold role;
  rejected in favour of D1's bounded coexistence.
- **API-only employee firewall (leave RLS as members)** — rejected: the audit
  explicitly requires the firewall at the RLS layer (direct-DB path).

## Consequences

- **Positive:** one canonical authority (privileges); the DB enforces the employee
  firewall even outside the API; tenant-switch/stale-token semantics are explicit
  and tested; the authz matrix stays executable in CI.
- **Negative / risk:** D4 touches RLS on many tables — a policy error could deny
  legitimate reads. Mitigated by the pre-change access audit, per-table batches,
  and the AC-5 test matrix run against a live test DB before each batch.
- **Deferred:** impersonation-with-audit and a full platform-admin plane (#278/
  LR-19) build on this but are out of scope here.

## Implementation plan (each phase gated on this ADR being Accepted)

1. **Ratify (docs only, this ADR)** — no code.
2. **AC-3 authz coverage gate (done 2026-07-25)** — `test_authz_mutation_coverage.py`
   enumerates every mutating v1 route, classifies its gate from the full dependency
   tree, and fails CI if any mutation ships with only-authentication/public unless
   it is on a small reviewed allowlist (17 self-service/public routes, each
   justified). Directly enforces the "many routes require only authentication"
   finding. *(unit-testable, no live stack)*
2b. **AC-3 route migration (deferred — needs live DB)** — moving sensitive
   `require_role` routes to `require_privilege` changes *who* has access (the
   privilege→role grants live in `tenant_user_effective_privileges`), so it is
   verified against a live test DB per batch to avoid lockouts. Sequenced with
   Phases 3–4.
3. **AC-4 RLS firewall** — add `is_tenant_erp_member`; migrate ERP table policies
   in reviewed batches behind a pre-change access audit. *(needs a live test DB)*
4. **AC-5 negative-path matrix** — cross-tenant, stale-token, tenant-switch, invite,
   deactivation, service-role, and direct-DB tests. *(needs a live test DB)*
5. **AC-6 frontend** — consume effective privileges; e2e proof.

## Acceptance criteria mapping (#378)

| AC | Resolved by |
|---|---|
| Resolve from active membership every request | Already done (ratified: D3) |
| Reject JWT claims disagreeing with membership | Already done (ratified: D3) |
| 22 roles as explicit capabilities or documented | D1 + D2 |
| Employee limited to timesheets/self (API **and** RLS) | API done; **D4** for RLS |
| Cross-tenant/stale/switch/invite/deactivation/service-role/direct-DB tests | Plan step 4 (AC-5) |
| Frontend reflects but never substitutes for server perms | D5 |
| Route/method/role/data-scope matrix executable in CI | Already done (ratified: AC-7) |
