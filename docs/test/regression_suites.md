# Regression Suites — Aethos PS

Top-level regression map. Every shipped business workflow has its own scenario document; this file lists them and the quality gates each must pass before a release.

## Workflows

| # | Workflow | Document | Owner role(s) |
| --- | --- | --- | --- |
| W1 | Engagement to cash | [`e2e_engagement_to_cash.md`](e2e_engagement_to_cash.md) | Karya + Rupa; Aksha for regression |
| W2 | Procure to pay | [`e2e_procure_to_pay.md`](e2e_procure_to_pay.md) | Karya + Rupa; Aksha for regression |
| W3 | Record to report | [`e2e_record_to_report.md`](e2e_record_to_report.md) | Karya; Aksha for regression |
| W4 | Signup to first invoice | [`e2e_onboarding_signup.md`](e2e_onboarding_signup.md) | Karya + Rupa + Prahari (security); Aksha for regression |

## Accounting & invariant tests

- [`accounting_invariants.md`](accounting_invariants.md) — debits=credits, immutability, period locks, FX freeze, double-post detection, idempotency.

## Agent eval packs

One per registered agent. Located in [`agent_evals/`](agent_evals/).

| Agent | Eval pack |
| --- | --- |
| copilot_agent | [`agent_evals/copilot_agent.yaml`](agent_evals/copilot_agent.yaml) |
| engagement_letter_agent | [`agent_evals/engagement_letter_agent.yaml`](agent_evals/engagement_letter_agent.yaml) |
| vendor_invoice_agent | [`agent_evals/vendor_invoice_agent.yaml`](agent_evals/vendor_invoice_agent.yaml) |
| expense_extractor_agent | [`agent_evals/expense_extractor_agent.yaml`](agent_evals/expense_extractor_agent.yaml) |
| invoice_drafter_agent | [`agent_evals/invoice_drafter_agent.yaml`](agent_evals/invoice_drafter_agent.yaml) |
| billing_run_agent | [`agent_evals/billing_run_agent.yaml`](agent_evals/billing_run_agent.yaml) |
| project_health_agent | [`agent_evals/project_health_agent.yaml`](agent_evals/project_health_agent.yaml) |
| collections_agent | [`agent_evals/collections_agent.yaml`](agent_evals/collections_agent.yaml) |
| accounting_guardian | [`agent_evals/accounting_guardian.yaml`](agent_evals/accounting_guardian.yaml) |
| reporting_agent | [`agent_evals/reporting_agent.yaml`](agent_evals/reporting_agent.yaml) |
| intelligence_agent | [`agent_evals/intelligence_agent.yaml`](agent_evals/intelligence_agent.yaml) |
| time_entry_agent | [`agent_evals/time_entry_agent.yaml`](agent_evals/time_entry_agent.yaml) |
| revenue_recognition_agent | [`agent_evals/revenue_recognition_agent.yaml`](agent_evals/revenue_recognition_agent.yaml) |
| bill_pay_agent | [`agent_evals/bill_pay_agent.yaml`](agent_evals/bill_pay_agent.yaml) |

## Gate matrix

| Gate (from `agent-harness/core/quality-gates.md`) | W1 | W2 | W3 | W4 |
| --- | --- | --- | --- | --- |
| Confidence | ✓ | ✓ | ✓ | ✓ |
| TDD | ✓ | ✓ | ✓ | ✓ |
| Package verification | ✓ | ✓ | — | ✓ |
| Money | ✓ | ✓ | ✓ | ✓ |
| Multi-tenant | ✓ | ✓ | ✓ | ✓ |
| AI / agent | ✓ | ✓ | — | — |
| Customer onboarding / payments | ✓ (Stripe Payment Link, webhook) | ✓ (NACHA / CSV) | — | ✓ (SaaS subscription + Stripe Connect) |
| RBAC regression | ✓ | ✓ | ✓ | ✓ |
| Concurrency / idempotency | ✓ | ✓ | ✓ | ✓ |
| Observability | ✓ | ✓ | ✓ | ✓ |
| Contract | ✓ | ✓ | — | ✓ |
| E2E workflow | ✓ | ✓ | ✓ | ✓ |

## Release readiness check

For a release to be cut:

- Every workflow's scenario document is current.
- Every scenario step has at least one passing test (or a documented `xfail` for not-yet-shipped variants).
- Every agent eval pack scored ≥ threshold; drift dashboard green for 7 days.
- No P0/P1 issues open against any workflow.
- Cleanup verified — no test artifacts visible in production lists.
