"""Static safety contract for the retained Ishantech production UI journey."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONFIG = _ROOT / "frontend" / "playwright.config.ts"
_PRODUCTION_CONFIG = _ROOT / "frontend" / "playwright.production-ui.config.ts"
_SPEC = _ROOT / "frontend" / "e2e" / "ishantech-production-ui.spec.ts"
_RUNBOOK = _ROOT / "docs" / "qa" / "ishantech-production-e2e-runbook-2026-07-11.md"


def test_ordinary_playwright_suite_cannot_discover_retained_production_journey() -> None:
    default_config = _DEFAULT_CONFIG.read_text(encoding="utf-8")

    assert "testIgnore: /ishantech-production-ui" in default_config


def test_retained_production_config_has_single_session_and_no_teardown() -> None:
    config = _PRODUCTION_CONFIG.read_text(encoding="utf-8")

    assert "https://aethos.ishirock.tech" in config
    assert "I_UNDERSTAND_THIS_MUTATES_PRODUCTION" in config
    assert "workers: 1" in config
    assert "retries: 0" in config
    assert "fullyParallel: false" in config
    assert "trace: 'on'" in config
    assert "mode: 'on'" in config
    assert "process.umask(0o077)" in config
    assert "ishantech_e2e_private_evidence" in config
    assert "globalSetup" not in config
    assert "globalTeardown" not in config


def test_retained_production_spec_has_no_non_ui_mutation_escape_hatches() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    forbidden = {
        "Playwright request fixture": r"async\s*\(\s*\{[^}]*\brequest\b",
        "page request client": r"\bpage\.request\b",
        "route interception": r"\b(?:page|context)\.route\b",
        "browser storage mutation": r"\blocalStorage\.(?:setItem|removeItem|clear)\b",
        "injected storage state": r"\bstorageState\s*\(",
        "extra page/video": r"\b(?:context|page)\.newPage\b",
    }
    for label, pattern in forbidden.items():
        assert re.search(pattern, spec) is None, label

    top_level_tests = re.findall(r"(?m)^test\(", spec)
    assert len(top_level_tests) == 1
    assert "one recorded production browser session" in spec
    assert "page.on('response'" in spec
    assert "page.on('requestfailed'" in spec
    assert "page.on('console'" in spec
    assert "intentionally non-resumable" in spec
    assert "pending_password" in spec
    assert "records: this.records" in spec
    assert "request.method() === 'GET' && detail.includes('net::ERR_ABORTED')" in spec
    assert "new URL(response.url()).pathname === '/api/v1/accounts'" in spec


def test_retained_production_journey_posts_required_manual_journals_through_ui() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    for reference in ("TX-01", "TX-16A", "TX-17", "TX-18", "TX-19"):
        assert f"reference: `${{TAG}} {reference}`" in spec

    for account_code in ("1100", "1500", "1600", "1690", "2150", "3100", "5300", "6000", "6100"):
        assert f"Code: '{account_code}'" in spec

    assert "No Owner Capital account or visible chart-of-accounts creation UI exists" not in spec
    assert "The standard chart lacks Payroll Expense and Payroll Accrual" not in spec
    assert "No fixed-asset master UI and no Equipment or Owner Capital accounts exist" not in spec
    assert "No Accumulated Depreciation or Depreciation Expense account exists" not in spec
    assert "Software Expense is absent" not in spec
    assert "['O2C-01C', 'O2C-03B', 'P2P-01D']" in spec
    assert "'P2P-05B', 'R2R-00', 'R2R-01C', 'R2R-02', 'R2R-03'" in spec
    assert "getByLabel('Manual journal currency')" in spec
    assert "toHaveValue('SGD')" in spec


def test_close_journey_requires_visible_reconciliation_before_locking() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    assert "unexpectedBlockers" in spec
    assert "ready_to_lock" in spec
    assert "Confirm lock" in spec
    assert "period_lock" in spec
    assert "status: 'waived'" not in spec
    assert "getByRole('button', { name: /^waive$/i })" not in spec
    assert "LOCK-NEGATIVE" in spec
    assert "expect(response.status()).toBe(422)" in spec
    assert "{ fatal: true }" in spec
    assert "Pre-lock statement control" in spec
    assert "Owner unlocks and relocks April through visible UI" in spec
    assert "/api/v1/accounting/periods/2026-04/unlock" in spec
    assert "concurrent period lock/write race" in spec
    assert "period lock/race/reopen" not in spec
    assert "FX rate administration/write UI" in spec
    assert "FX setup" not in spec


def test_foreign_currency_journey_uses_visible_immutable_provenance() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    assert "lookupFxProvenance" in spec
    assert "Matched FX rate provenance" in spec
    assert "FX_APPROVAL_RATE_ID" in spec
    assert "FX_PAYMENT_RATE_ID" in spec
    assert "foreignAmountForTargetBase" in spec
    assert "TX12_FX_DELTA_SGD" in spec
    assert "2026-07-12" in spec
    assert "No visible historical FX-rate create/select control exists" not in spec


def test_finance_journey_exercises_catalog_roles_without_legacy_admin_fallbacks() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    assert "Finance Approver is denied direct invoice posting by catalog policy" in spec
    assert "switchMainRole(page, credentials, 'billing_specialist')" in spec
    assert "switchMainRole(page, credentials, 'ar_manager')" in spec
    assert "switchMainRole(page, credentials, 'ap_manager')" in spec
    assert "Finance Approver is projected to legacy approver" not in spec
    assert "AR Manager is projected to legacy manager" not in spec
    assert "AP Manager is projected to legacy manager" not in spec
    assert "bills\\/[0-9a-f-]{36}\\/approve" not in spec


def test_procure_to_pay_journey_uses_catalog_role_actors_end_to_end() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    self_denial_marker = (
        "await journey.step('MD-06B', "
        "'Procurement Manager cannot self-approve its service order', async () => {"
    )
    self_denial_start = spec.index(self_denial_marker)
    self_denial_end = spec.find("\n    await journey.step(", self_denial_start + 1)
    self_denial = spec[self_denial_start:self_denial_end]
    assert "toBeDisabled()" in self_denial

    expected_steps = (
        (
            "MD-06C",
            "Finance Approver approves the Kinetic service order with catalog privilege",
            "finance_approver",
        ),
        (
            "P2P-01B",
            "AP Manager approves TX-04 and posts AP with catalog privileges",
            "ap_manager",
        ),
        (
            "P2P-01D",
            "AP Manager settles April bill as TX-05",
            "ap_manager",
        ),
        (
            "P2P-02B",
            "AP Manager approves matched TX-09 with catalog privileges",
            "ap_manager",
        ),
        (
            "P2P-03",
            "AP Manager settles Kinetic TX-09 as June payment TX-10",
            "ap_manager",
        ),
        (
            "P2P-04B",
            "AP Manager approves prepaid TX-14 with catalog privileges",
            "ap_manager",
        ),
        (
            "P2P-04C",
            "AP Manager settles prepaid TX-14 as TX-15",
            "ap_manager",
        ),
        (
            "P2P-05B",
            "AP Manager approves TX-16 at the captured SGD 1,350 base value and leaves it unpaid",
            "ap_manager",
        ),
    )
    for step_id, title, role in expected_steps:
        marker = f"await journey.step('{step_id}', '{title}', async () => {{"
        start = spec.index(marker)
        end = spec.find("\n    await journey.step(", start + len(marker))
        block = spec[start : end if end >= 0 else len(spec)]
        assert f"switchMainRole(page, credentials, '{role}')" in block

    assert "Finance Controller approves the Kinetic service order" not in spec
    assert "Finance Controller settles April bill" not in spec
    assert "Finance Controller approves matched TX-09" not in spec
    assert "Finance Controller approves prepaid TX-14" not in spec
    for visible_action in (
        "next: batch details",
        "create batch",
        "approve batch",
        "download csv",
        "mark as sent to bank",
        "confirm settlement",
    ):
        assert visible_action in spec.lower()


def test_production_journey_proves_journals_from_visible_stable_line_attributes() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    assert "async function assertVisibleJournalPosting" in spec
    for selector in (
        "journal-entry-row",
        "journal-expand-toggle",
        "journal-lines",
        "journal-line",
    ):
        assert f'data-testid="{selector}"' in spec
    for attribute in (
        "data-journal-id",
        "data-journal-reference",
        "data-reference-type",
        "data-direction",
        "data-account-code",
        "data-amount",
        "data-currency",
        "data-base-amount",
        "data-fx-rate-id",
    ):
        assert attribute in spec
    assert "toHaveCount(expected.lines.length)" in spec
    assert "toContainText(`${expectedLine.currency} ${expectedLine.amount}`)" in spec
    assert "toContainText(`Base ${expectedLine.baseAmount}`)" in spec
    assert "toContainText(`FX ${expectedLine.fxRateId}`)" in spec


def test_production_journey_records_required_transaction_journal_evidence() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    for transaction in (
        "TX08",
        "TX16",
        "TX12_PAYMENT",
        "TX12_FX",
        "TX01",
        "TX16A",
        "TX17",
        "TX18",
        "TX19",
    ):
        assert f"records.{transaction}_JOURNAL_ID" in spec
        assert f"records.{transaction}_JOURNAL_ENTRY_NUMBER" in spec

    assert "referenceId: records.TX08_ID" in spec
    assert "referenceId: records.TX16_ID" in spec
    for reference_type in ("invoice", "bill", "payment", "fx_gain_loss", "manual"):
        assert f"referenceType: '{reference_type}'" in spec
    assert spec.count("fxRateId: records.FX_APPROVAL_RATE_ID") >= 4
    assert spec.count("fxRateId: records.FX_PAYMENT_RATE_ID") >= 2
    for transaction in ("TX-01", "TX-16A", "TX-17", "TX-18", "TX-19"):
        assert f"rowText: `${{TAG}} {transaction}`" in spec


def test_runbook_requires_line_level_visible_journal_evidence() -> None:
    runbook = _RUNBOOK.read_text(encoding="utf-8")

    assert "### Line-level journal evidence gate" in runbook
    assert "account code, DR/CR direction, transaction amount and ISO currency" in runbook
    assert "base amount and immutable FX rate row ID" in runbook
    assert re.search(
        r"TX-12 requires both the receipt\s+journal and the realised\s+FX journal",
        runbook,
    )
    assert "TX-01, TX-16A, TX-17, TX-18, and TX-19" in runbook
    assert "A journal summary row or total alone is not PASS evidence" in runbook


def test_close_package_visibly_matches_period_end_ar_ap_oracle() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    assert "async function assertVisibleClosePackageOracle" in spec
    assert "Period-end AR/AP" in spec
    assert "SGD base-currency GL · as of" in spec
    assert "oracle.ar" in spec
    assert "oracle.ap" in spec
    assert "oracle.asOf" in spec
    assert "exerciseCloseChecklist(page, period, oracle)" in spec
    for as_of_date in ("2026-04-30", "2026-05-31", "2026-06-30"):
        assert f"asOf: '{as_of_date}'" in spec


def test_runbook_requires_visible_close_package_period_end_evidence() -> None:
    runbook = _RUNBOOK.read_text(encoding="utf-8")

    assert "### Close-package period-end evidence gate" in runbook
    assert "visible Period-end AR/AP card" in runbook
    assert re.search(r"April 30, May 31,\s+and June 30", runbook)
    assert "base-currency AR and AP values must equal the monthly oracle" in runbook
    assert "A current-date subledger total cannot substitute" in runbook
    assert "reopen attempt" not in runbook
    assert "concurrent lock/write race" in runbook
    assert "rate administration/write UI" in runbook


def test_current_aging_visibly_reconciles_in_sgd_after_final_transactions() -> None:
    spec = _SPEC.read_text(encoding="utf-8")

    assert "async function assertVisibleCurrentAgingOracle" in spec
    assert "getByTestId('reporting-currency')" in spec
    for report, amount, step_id in (
        ("ar", "27,250.00", "R2R-04A"),
        ("ap", "1,350.00", "R2R-04B"),
    ):
        assert f"getByTestId('{report}-aging-cards')" in spec
        assert f"getByTestId('{report}-aging-total')" in spec
        assert f"getByTestId('{report}-aging-unallocated')" in spec
        assert f"'{amount}'" in spec
        assert f"journey.step('{step_id}'" in spec
    assert "SGD base currency" in spec
    assert "CURRENT_AR_AGING_SGD" in spec
    assert "CURRENT_AP_AGING_SGD" in spec


def test_runbook_requires_visible_current_aging_sgd_evidence() -> None:
    runbook = _RUNBOOK.read_text(encoding="utf-8")

    assert "### Current aging evidence gate" in runbook
    assert "SGD 27,250.00" in runbook
    assert "SGD 1,350.00" in runbook
    assert "SGD base currency" in runbook
    assert "unallocated GL amount must be SGD 0.00" in runbook
    assert "A numeric match with a USD or missing currency label is not PASS" in runbook
