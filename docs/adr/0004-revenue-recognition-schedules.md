# ADR 0004 — Durable straight-line revenue-recognition schedules

- **Status:** Accepted
- **Date:** 2026-07-24
- **Deciders:** Founder (approved defaults 2026-07-24) + Vastu; accounting review
- **Issue:** #408

## Context

`revenue_recognition_agent` could release deferred revenue only for the *current*
period's net credits — it explicitly left **historical** deferred balances
untouched because there was no durable record of how a deferred amount should be
recognized over time. A retainer paid upfront (e.g. 12 months of fees credited to
`2200 Deferred Revenue`) therefore never got systematically released to `4000
Revenue` across the engagement.

## Decision

Add a durable **`revenue_recognition_schedules`** table (migration `0112`) and a
release engine the close agent reads. It follows the existing close-agent pattern
— **draft → HITL → post**, never auto-posts; `recognized_to_date` advances only
when a drafted release is approved and posted.

**Approved defaults (v1):**
- **Method:** `straight_line` — the base-currency total is split into `periods`
  equal monthly amounts (2dp; the final month absorbs rounding so the schedule
  settles exactly).
- **Base currency:** the schedule carries `base_total_amount` /
  `recognized_to_date` in the tenant base; releases are computed and **posted in
  base** (DR `2200` / CR `4000`).
- **Catch-up:** the amount due for a period is the *cumulative* scheduled target
  through that month minus what has already been recognized — so a schedule that
  missed periods catches up, and a fully-recognized one yields nothing.
- **Schedule creation:** an **on-demand service** (`create_schedule`) called by an
  endpoint/agent — **not** auto-wired into the invoice-post hot path in v1.
- **Release:** wired into `close_scheduler_worker` as the `scheduled_revenue_release`
  proposal step, drafting one balanced journal per due schedule.

## Options considered

- **Straight-line schedule table (chosen)** — durable, deterministic, HITL-safe,
  and reuses the proven close-agent draft/review/post flow.
- **Auto-generate schedules on every deferred-revenue invoice** — deferred: it
  touches the AR hot path and needs per-invoice service-period inference; kept as
  a follow-up now that the table + engine exist.
- **Milestone / percentage-of-completion** — already covered by the existing
  agent paths; the schedule is specifically for straight-line release.

## Consequences

- **Positive:** historical deferred balances are released on a durable plan;
  releases are base-currency and reviewable; the last period settles exactly.
- **Negative / deferred:** v1 requires explicit schedule creation (no auto-gen);
  only straight-line; multi-currency remeasurement of the deferred balance itself
  is out of scope (the schedule fixes the base amount at creation).
- **Migration:** `0112` adds the table (RLS tenant-isolation + member-read,
  format/bounds CHECKs, `set_updated_at`).
- **Verification:** pure straight-line/period-release math + service unit tests,
  and agent build tests (first-period, catch-up, fully-recognized, balanced
  journal). Full backend suite green.
