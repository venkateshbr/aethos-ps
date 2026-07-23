# ADR 0003 — Period-end FX remeasurement of open foreign balances

- **Status:** Accepted
- **Date:** 2026-07-23
- **Deciders:** Founder (approved defaults 2026-07-23) + Vastu (architecture); accounting review
- **Issue:** #376 (AC 2 — required period-end remeasurement)

## Context

Multi-currency was enabled day one: invoices and bills can be denominated in any
of the five launch currencies, and every journal line stores both the
transaction amount and its base-currency equivalent (`base_amount`) at the rate
on the booking date. Realized FX gain/loss is already posted at settlement
(`fx_gain_loss_service`, account `7900`).

What was missing (#376 AC 2): **period-end remeasurement**. Between booking and
settlement, an open foreign-currency monetary balance (an unpaid AR invoice or AP
bill) is still carried at its *booking-date* base value. If the rate has moved by
period end, the reported AR/AP — and therefore the balance sheet and income
statement — are stale. GAAP/IFRS (ASC 830 / IAS 21) require monetary items to be
remeasured to the closing rate at each reporting date, with the movement booked
as an **unrealized** FX gain/loss.

## Decision

Add an `fx_remeasurement_agent` that, at month-end close, revalues open
foreign-currency AR/AP to the period-end rate and drafts the unrealized FX
gain/loss journal. It follows the existing close-agent pattern (accrual /
prepaid / recurring / revenue-recognition): it **only drafts** L2 HITL
suggestions — posting still flows through the Inbox + `ManualJournalService`, so
the accounting guardian and period lock stay authoritative. It is wired into
`close_scheduler_worker._PROPOSAL_STEPS` and registered as a money agent.

**Approved defaults (v1):**
- **Accounts:** new `7910 Unrealized FX Gain/Loss` (migration `0110`, seeded for
  new tenants + backfilled), kept separate from realized `7900`. Controls: AR
  `1200`, AP `2000`.
- **Scope:** AR + AP **fully-open** balances only. Items with any payment applied
  are skipped (partial-payment remainders and foreign cash/bank revaluation are
  deferred follow-ups) so a face-value remeasurement can never overstate a
  partly-settled balance.
- **Materiality:** skip `|delta| < 1.00` base.
- **Reversal:** each entry reverses on the first day of the next period (standard
  remeasurement) so only *realized* gain/loss persists at settlement. The
  reversal date is carried on the proposal as `reverses_on` and in the journal
  description.

Double-entry (delta = remeasured_base − booked_base, in base currency):

| Balance | delta | Journal |
|---|---|---|
| AR (asset) | > 0 gain | DR 1200 / CR 7910 |
| AR | < 0 loss | DR 7910 / CR 1200 |
| AP (liability) | > 0 loss | DR 7910 / CR 2000 |
| AP | < 0 gain | DR 2000 / CR 7910 |

If no period-end rate exists for a currency, that currency is skipped (the rate
lookup raises `FxRateNotFoundError`) rather than posting an unpriced entry.

## Options considered

- **New close agent (chosen)** — reuses the proven draft→HITL→post pattern; the
  human review gate catches any mis-priced proposal before it touches the GL.
- **Auto-posting remeasurement at close** — rejected: money-critical journals
  should not post without the same review every other close journal gets.
- **Reuse `7900` for unrealized** — rejected: conflates realized vs unrealized,
  which must be separable for disclosure.

## Consequences

- **Positive:** open foreign AR/AP are reported at closing rates; unrealized vs
  realized FX are separable (7910 vs 7900); the reversal keeps only realized G/L
  at settlement.
- **Negative / deferred:** v1 skips partially-paid remainders and foreign
  cash/bank balances; the reversal is captured as metadata/description and is not
  yet auto-posted (the reviewer/next close applies it) — both tracked as
  follow-ups on #376.
- **Migration:** `0110` adds/backfills `7910` (idempotent).
- **Verification:** `tests/unit/test_fx_remeasurement_agent.py` (9) — AR/AP
  gain+loss sign conventions, balance, materiality, same-currency, paid/draft
  skips, missing-account error. Full backend suite green.
