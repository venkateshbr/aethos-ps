"""E2E test skeleton for the engagement-to-cash workflow.

Source spec: docs/test/e2e_engagement_to_cash.md
Every test corresponds to a section ID in the spec. Drift between this file
and the spec is a QA gate failure.

All tests are `xfail(strict=True)` until the underlying feature ships. When
a feature lands, remove the marker and the test must pass for the right reason.

Test naming convention: `test_<section_id_with_underscores>_<short_slug>`.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

NOT_IMPL = "not yet implemented — see docs/test/e2e_engagement_to_cash.md"


# ===========================================================================
# §1 Happy Path — Time & Materials, single-currency
# ===========================================================================


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_1_step_1_drop_engagement_letter():
    """§1.1 step 1 — Alice drops engagement_letter PDF; document row written; extraction enqueued."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_1_step_2_engagement_letter_agent_produces_suggestion():
    """§1.1 step 2 — engagement_letter_agent emits typed EngagementDraft + hitl_task if conf < 0.9."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_1_step_3_approve_extracted_engagement():
    """§1.1 step 3 — Alice approves; client + engagement + rate_card materialised."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_2_step_4_log_time_from_chat():
    """§1.2 step 4 — time_entry_agent parses unambiguous 3.5h; auto-applies at L3."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_2_step_5_expense_extractor_auto_applies():
    """§1.2 step 5 — receipt extraction conf > 0.9; agent_suggestion=auto_applied."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_3_step_7_invoice_drafter_produces_card():
    """§1.3 step 7 — Bob asks for invoice; agent assembles lines from time + expenses."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_3_step_8_approve_invoice_posts_balanced_journal():
    """§1.3 step 8 — approve invoice; accounting_guardian validates; DR AR / CR Revenue."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_4_step_9_send_invoice_creates_stripe_payment_link():
    """§1.4 step 9 — POST /invoices/{id}/send creates Product+Price+PaymentLink with on_behalf_of."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_4_step_10_public_invoice_view_renders():
    """§1.4 step 10 — public /p/{token} renders branded invoice without auth."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_5_step_11_stripe_webhook_marks_paid_and_posts_journal():
    """§1.5 step 11 — checkout.session.completed → payment row → trigger posts DR Bank / CR AR."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_1_5_step_13_ar_aging_drops_paid_invoice():
    """§1.5 step 13 — paid invoice no longer in AR aging buckets."""
    raise NotImplementedError


# ===========================================================================
# §2 Variants
# ===========================================================================


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_1_fixed_fee_engagement():
    """§2.1 — Fixed-fee invoice with milestones (no time entries)."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_2_milestone_billing():
    """§2.2 — One invoice per milestone."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_3_monthly_retainer_billing_run():
    """§2.3 — billing_run_agent auto-proposes monthly retainer invoices."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_4_retainer_draw_floor_alert():
    """§2.4 — Drawing on retainer; project_health_agent alerts at floor."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_5_capped_tm_invoice_capped():
    """§2.5 — Capped T&M caps invoice; excess marked non_billable_overflow."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_6_mixed_model_invoice():
    """§2.6 — One invoice with both fixed-fee and T&M lines."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_7_multi_currency_engagement():
    """§2.7 — Tenant USD, engagement GBP; journal stores both amount and base_amount."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_2_8_no_stripe_connect_pdf_only():
    """§2.8 — No Connect → send produces PDF + mark-paid link, no Payment Link."""
    raise NotImplementedError


# ===========================================================================
# §3 Unhappy Paths
# ===========================================================================


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_1_extraction_missing_client_forces_hitl():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_2_invoice_missing_tax_rate_blocks_post():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_3_webhook_delay_reconciled_by_nightly_worker():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_4_invalid_webhook_signature_returns_400():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_5_llm_unavailable_graceful_degradation():
    """§3.5 — Anthropic API 500 → manual invoice form remains usable."""
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_6_viewer_cannot_approve_invoice():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_7_cross_tenant_invoice_returns_404():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_8_concurrent_approve_race_loser_409():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_9_invoice_number_monotonic_under_concurrency():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_10_imbalanced_journal_rejected():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_11_period_locked_post_rejected():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_12_stale_fx_rate_warns_user():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_13_low_confidence_routes_to_hitl():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_14_prompt_injection_in_document_no_compliance():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_15_autonomy_demotion_on_bad_streak():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_16_stripe_webhook_idempotent():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_3_17_posted_journal_edit_blocked():
    raise NotImplementedError


# ===========================================================================
# §4 Edge Cases
# ===========================================================================


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e1_zero_amount_invoice_void():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e2_negative_invoice_credit_note():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e3_unsupported_currency_refused():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e4_time_entry_timezone_handling():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e5_fx_moved_between_send_and_pay():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e6_public_token_rotated_mid_payment():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e7_delete_project_with_unbilled_blocks():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e8_max_precision_overflow_rejected():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e9_currency_roundtrip_residual_to_fx_gain_loss():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_4_e10_dst_transition_no_lost_or_dup_time_entries():
    raise NotImplementedError


# ===========================================================================
# §5 RBAC matrix — one test per role x write-action cell
# ===========================================================================


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_5_rbac_owner_can_send_invoice():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_5_rbac_manager_cannot_send_invoice_403():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_5_rbac_viewer_cannot_log_time_403():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_5_rbac_other_tenant_user_gets_404():
    raise NotImplementedError


# ===========================================================================
# §6 Audit Trail
# ===========================================================================


@pytest.mark.xfail(strict=True, reason=NOT_IMPL)
def test_6_audit_trail_complete_after_happy_path():
    """§6 — all expected events + agent_suggestions + webhook_events written."""
    raise NotImplementedError
