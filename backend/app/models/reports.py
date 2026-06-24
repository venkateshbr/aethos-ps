"""Pydantic models for financial report responses.

Money fields are serialised as two-decimal-place strings (never float)
following the Aethos money rule in CLAUDE.md.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrialBalanceLine(BaseModel):
    """One row in the trial balance — one account's DR/CR totals."""

    account_code: str
    account_name: str
    account_type: str  # asset / liability / equity / revenue / expense
    total_dr: str  # Decimal serialised as string via serialise_money()
    total_cr: str
    net: str  # positive = debit balance, negative = credit balance


class TrialBalanceReport(BaseModel):
    """Full trial balance report payload returned by the API."""

    as_of_period: str | None  # YYYY-MM or None (all-time cumulative)
    lines: list[TrialBalanceLine]
    grand_total_dr: str
    grand_total_cr: str
    is_balanced: bool  # abs(grand_total_dr - grand_total_cr) <= 0.01
    generated_at: datetime


class FinancialStatementLine(BaseModel):
    """One display line in a financial statement section."""

    account_code: str
    account_name: str
    account_type: str
    amount: str


class BalanceSheetReport(BaseModel):
    """Balance sheet as of an accounting period."""

    as_of_period: str | None
    asset_lines: list[FinancialStatementLine]
    liability_lines: list[FinancialStatementLine]
    equity_lines: list[FinancialStatementLine]
    total_assets: str
    total_liabilities: str
    total_equity: str
    liabilities_and_equity: str
    is_balanced: bool
    generated_at: datetime


class RetainedEarningsRollForwardReport(BaseModel):
    """Retained earnings movement for one accounting period."""

    period: str
    previous_period: str
    beginning_retained_earnings: str
    current_period_net_income: str
    retained_earnings_activity: str
    ending_retained_earnings: str
    generated_at: datetime


class IncomeStatementReport(BaseModel):
    """Income statement for an accounting period range."""

    period_start: str | None
    period_end: str | None
    revenue_lines: list[FinancialStatementLine]
    expense_lines: list[FinancialStatementLine]
    total_revenue: str
    total_expenses: str
    net_income: str
    generated_at: datetime


class CashFlowLine(BaseModel):
    """One cash movement line derived from posted journal activity."""

    section: str
    description: str
    amount: str
    period: str | None
    journal_entry_id: str | None
    reference_type: str | None


class CashFlowReport(BaseModel):
    """Direct cash-flow statement grouped by operating, investing, and financing."""

    period_start: str | None
    period_end: str | None
    operating_lines: list[CashFlowLine]
    investing_lines: list[CashFlowLine]
    financing_lines: list[CashFlowLine]
    net_cash_from_operating: str
    net_cash_from_investing: str
    net_cash_from_financing: str
    net_change_in_cash: str
    beginning_cash: str
    ending_cash: str
    generated_at: datetime


class StatutoryTaxCurrencyBucket(BaseModel):
    """Tax summary bucket in the source transaction currency."""

    currency: str
    output_tax_collected: str
    input_tax_recoverable: str
    net_tax_payable: str


class StatutoryTaxSummary(BaseModel):
    """Tax control totals for a statutory reporting pack."""

    tax_label: str
    tax_authority_label: str
    base_currency: str
    transaction_currency_buckets: list[StatutoryTaxCurrencyBucket]
    ledger_output_tax_payable_balance: str
    ledger_input_tax_recoverable_balance: str
    ledger_net_tax_payable: str


class StatutoryReportingPack(BaseModel):
    """Composed statutory reporting pack for a selected accounting period range."""

    period_start: str
    period_end: str
    as_of_period: str
    country: str
    market: str
    base_currency: str
    locale: str
    timezone: str
    tax_label: str
    tax_authority_label: str
    tax_collection_model: str
    reporting_periods: list[str]
    trial_balance: TrialBalanceReport
    balance_sheet: BalanceSheetReport
    income_statement: IncomeStatementReport
    cash_flow: CashFlowReport
    retained_earnings_roll_forward: RetainedEarningsRollForwardReport
    tax_summary: StatutoryTaxSummary
    generated_at: datetime
