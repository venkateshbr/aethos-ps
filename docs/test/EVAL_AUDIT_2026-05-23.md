# Agent Eval Audit — 2026-05-23

## Unit Test Results (pre-PR vs post-PR)

| Metric | Before | After |
|---|---|---|
| Unit tests passing | 172 | 177 |
| Property xfailed (stale — see below) | 3 | 3 |
| Stripe service tests failing (pre-existing) | 3 | 3 |
| xfail stubs converted to real unit tests | 0 | 5 |
| New unit tests added this PR | 0 | 5 |

All 5 new tests are in `backend/tests/unit/test_e2c_scenarios.py`.

### Pre-existing failures (not introduced in this PR)

These 3 failures pre-date `feat/73-evals` and are tracked in `test_invoices_service.py`:
- `test_payment_idempotency_skips_duplicate` — StripeService missing method
- `test_connect_oauth_url_includes_client_id_and_state` — StripeService missing method
- `test_exchange_connect_code_returns_account_id` — StripeService missing method

These should be fixed in a separate issue against the Stripe Connect implementation (issue #62 area).

### Property tests marked xfail (to remove when implementation is complete)

Three stale xfails remain in `tests/property/` — they should be unblocked after the
`Money` domain helper and the `accounting_guardian` integration plumbing land:
- `test_accounting_guardian_accepts_balanced` (PLAN §6.2)
- `test_accounting_guardian_rejects_imbalanced` (PLAN §6.2)
- `test_money_serialises_as_string` (PLAN §3 — `app/domain/money.py`)

Note: `validate_journal` and `accounting_guardian.py` are fully implemented and
have 5 passing unit tests in `test_accounting_guardian.py`. The property xfails
reference the higher-level `post_journal()` integration path.

## Eval Pack Coverage

| Agent | Pack | Status |
|---|---|---|
| copilot_agent | docs/test/agent_evals/copilot_agent.yaml | Pack complete |
| engagement_letter_agent | docs/test/agent_evals/engagement_letter_agent.yaml | Pack complete — synthetic fixtures created; LLM run needs ANTHROPIC_API_KEY |
| vendor_invoice_agent | docs/test/agent_evals/vendor_invoice_agent.yaml | Pack complete — synthetic fixtures created |
| expense_extractor_agent | docs/test/agent_evals/expense_extractor_agent.yaml | Pack complete — synthetic fixtures created |
| invoice_drafter_agent | docs/test/agent_evals/invoice_drafter_agent.yaml | Pack complete — 5 unit tests in test_invoice_drafter.py |
| billing_run_agent | docs/test/agent_evals/billing_run_agent.yaml | Pack complete |
| project_health_agent | docs/test/agent_evals/project_health_agent.yaml | Pack complete |
| collections_agent | docs/test/agent_evals/collections_agent.yaml | Pack complete |
| accounting_guardian | docs/test/agent_evals/accounting_guardian.yaml | Pack complete — pass_rate=1.00 enforced; 5 unit tests passing in test_accounting_guardian.py |
| reporting_agent | docs/test/agent_evals/reporting_agent.yaml | Pack complete |
| intelligence_agent | docs/test/agent_evals/intelligence_agent.yaml | Pack complete |
| time_entry_agent | docs/test/agent_evals/time_entry_agent.yaml | Pack complete |
| revenue_recognition_agent | docs/test/agent_evals/revenue_recognition_agent.yaml | Pack complete (v1.1 placeholder) |
| bill_pay_agent | docs/test/agent_evals/bill_pay_agent.yaml | Pack complete — always-L2 verified in unit tests |

## Fixture scaffold

`backend/tests/fixtures/` created with:
```
engagement_letters/
  acme_tm.txt               — synthetic T&M engagement letter (Lighthouse Advisory / Acme Corp)
  red_team/                 — (empty, ready for adversarial inputs)
  hitl/                     — (empty, ready for low-confidence inputs)
receipts/
  lunch_receipt.txt         — synthetic restaurant receipt ($58.66, meals_and_entertainment)
  red_team/
  hitl/
vendor_invoices/
  aws_invoice.txt           — synthetic AWS invoice ($56.08, cloud infrastructure)
  red_team/
  hitl/
README.md                   — fixture population instructions
```

Real PDFs (anonymised client documents) should be added to populate the LLM eval run.
See `backend/tests/fixtures/README.md` for naming conventions.

## To run full LLM evals (requires Anthropic API key + real fixtures)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
cd backend && uv run pytest tests/evals/ -v
```

## xfail to real test conversions

These 5 tests were converted from `xfail(strict=True)` stubs in
`tests/e2e/test_engagement_to_cash.py` to real passing unit tests in
`tests/unit/test_e2c_scenarios.py`:

| Spec ID | Test name | What it validates |
|---|---|---|
| §3.10 | test_3_10_imbalanced_journal_rejected | accounting_guardian rejects DR≠CR by >0.01 |
| §3.11 | test_3_11_period_locked_post_rejected | accounting_guardian rejects posting into locked period |
| §3.13 | test_3_13_low_confidence_routes_to_hitl | suggestion_writer writes hitl_tasks when confidence < 0.90 |
| §3.14 | test_3_14_prompt_injection_sets_suspected_injection | EngagementDraft.suspected_injection field + mask_pii email redaction |
| §4.E1 | test_4_e1_invoice_draft_with_zero_lines_is_valid | InvoiceDraft with empty lines is a valid Pydantic model with Decimal totals |

The xfail stubs in `tests/e2e/test_engagement_to_cash.py` remain as the
skeleton for the full Playwright e2e run once the frontend login flow is wired.

## Residual risks

1. The 3 Stripe Connect unit tests are failing due to missing `StripeService` methods —
   these should be tracked and fixed before the payments milestone ships.
2. The property xfails for `accounting_guardian` and `money.py` should be unblocked
   together when `post_journal()` integration path is complete (PLAN §6.2).
3. LLM eval packs need real ANTHROPIC_API_KEY and real fixture documents to produce
   meaningful F1 scores. Current run is deterministic unit-only.
4. Red-team and HITL subdirectories in `backend/tests/fixtures/` are empty —
   adversarial PDFs should be added before pre-launch security review.
