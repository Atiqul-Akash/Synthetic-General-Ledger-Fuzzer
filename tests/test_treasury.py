"""Test suite for Treasury subledger, debt facilities, EIR amortization, and covenants."""

from decimal import Decimal
import pytest

from gl_fuzzer.subledgers.treasury import (
    BenchmarkRate,
    CorporateBond,
    CouponType,
    CovenantSuppressionMutator,
    DebtFacility,
    DebtRolloverConcealment,
    FacilityType,
    HedgeIneffectivenessConcealment,
    InterestRateSwap,
    Seniority,
    TreasurySubledger,
)


def test_issue_debt_facility_discount():
    subledger = TreasurySubledger()
    facility, entry = subledger.issue_facility(
        facility_id="BOND-2026-01",
        facility_type=FacilityType.CORPORATE_BOND,
        principal=Decimal("1000000.00"),
        issuance_price=Decimal("950000.00"),  # 50,000 discount
        coupon_rate=Decimal("0.05"),
        tenor_months=60,
        issuance_date="2026-01-01",
        maturity_date="2031-01-01",
    )
    assert facility.unamortized_discount == Decimal("50000.00")
    assert facility.carrying_value == Decimal("950000.00")
    assert entry.is_balanced
    assert entry.total_debits == Decimal("1000000.00")
    assert entry.total_credits == Decimal("1000000.00")


def test_issue_debt_facility_premium():
    subledger = TreasurySubledger()
    facility, entry = subledger.issue_facility(
        facility_id="BOND-2026-02",
        facility_type=FacilityType.CORPORATE_BOND,
        principal=Decimal("1000000.00"),
        issuance_price=Decimal("1030000.00"),  # 30,000 premium
        coupon_rate=Decimal("0.06"),
        tenor_months=60,
        issuance_date="2026-01-01",
        maturity_date="2031-01-01",
    )
    assert facility.unamortized_discount == Decimal("-30000.00")
    assert facility.carrying_value == Decimal("1030000.00")
    assert entry.is_balanced
    assert entry.total_debits == Decimal("1030000.00")
    assert entry.total_credits == Decimal("1030000.00")


def test_amortize_monthly_interest():
    subledger = TreasurySubledger()
    facility, _ = subledger.issue_facility(
        facility_id="LOAN-2026",
        facility_type=FacilityType.TERM_LOAN,
        principal=Decimal("500000.00"),
        issuance_price=Decimal("480000.00"),
        coupon_rate=Decimal("0.06"),
        tenor_months=60,
        issuance_date="2026-01-01",
        maturity_date="2031-01-01",
        effective_interest_rate=Decimal("0.068"),
    )

    entry = subledger.amortize_monthly_interest("LOAN-2026", "2026-01-31")
    assert entry is not None
    assert entry.is_balanced
    assert any(line.account_code == "68000" for line in entry.lines)
    assert any(line.account_code == "10100" for line in entry.lines)


def test_evaluate_covenants_healthy():
    subledger = TreasurySubledger()
    result = subledger.evaluate_covenants(
        total_debt=Decimal("2000000.00"),
        ebitda=Decimal("1000000.00"),  # Leverage = 2.0x <= 4.5x
        ebit=Decimal("800000.00"),
        interest_expense=Decimal("160000.00"),  # ICR = 5.0x >= 3.0x
        total_liabilities=Decimal("3000000.00"),
        total_equity=Decimal("2500000.00"),  # D/E = 1.2x <= 2.0x
    )
    assert not result.is_breached
    assert len(result.breach_reasons) == 0


def test_evaluate_covenants_breached():
    subledger = TreasurySubledger()
    result = subledger.evaluate_covenants(
        total_debt=Decimal("5000000.00"),
        ebitda=Decimal("1000000.00"),  # Leverage = 5.0x > 4.5x (Breach)
        ebit=Decimal("200000.00"),
        interest_expense=Decimal("150000.00"),  # ICR = 1.33x < 3.0x (Breach)
        total_liabilities=Decimal("6000000.00"),
        total_equity=Decimal("2000000.00"),  # D/E = 3.0x > 2.0x (Breach)
    )
    assert result.is_breached
    assert len(result.breach_reasons) == 3


def test_interest_rate_swap_cash_flow_hedge():
    subledger = TreasurySubledger()
    subledger.register_interest_rate_swap(
        swap_id="SWAP-01",
        notional=Decimal("1000000.00"),
        fixed_rate=Decimal("0.04"),
        is_cash_flow_hedge=True,
    )

    # MTM Gain with 90% effectiveness (10% ineffective to P&L)
    entry = subledger.mark_to_market_swap(
        swap_id="SWAP-01",
        new_market_value=Decimal("10000.00"),
        period_date="2026-03-31",
        effectiveness_ratio=Decimal("0.90"),
    )
    assert entry is not None
    assert entry.is_balanced
    assert any(line.account_code == "32000" and line.amount == Decimal("9000.00") for line in entry.lines)
    assert any(line.account_code == "48100" and line.amount == Decimal("1000.00") for line in entry.lines)


def test_covenant_suppression_mutator():
    subledger = TreasurySubledger()
    subledger.issue_facility(
        facility_id="BOND-TARGET",
        facility_type=FacilityType.CORPORATE_BOND,
        principal=Decimal("1000000.00"),
        issuance_price=Decimal("1000000.00"),
        coupon_rate=Decimal("0.05"),
        tenor_months=60,
        issuance_date="2026-01-01",
        maturity_date="2031-01-01",
    )
    entry = CovenantSuppressionMutator.mutate(subledger, "BOND-TARGET", Decimal("400000.00"), "2026-06-30")
    assert entry is not None
    assert entry.is_balanced
    assert entry.is_anomaly
    assert "ANOM_COVENANT_SUPPRESSION_DEBT_RECLASSIFICATION" in entry.anomaly_ids


def test_hedge_ineffectiveness_concealment():
    subledger = TreasurySubledger()
    entry = HedgeIneffectivenessConcealment.mutate(subledger, "SWAP-01", Decimal("15000.00"), "2026-06-30")
    assert entry is not None
    assert entry.is_balanced
    assert entry.is_anomaly
    assert "ANOM_HEDGE_INEFFECTIVENESS_CONCEALMENT" in entry.anomaly_ids


def test_debt_rollover_concealment():
    subledger = TreasurySubledger()
    facility, _ = subledger.issue_facility(
        facility_id="CP-2026",
        facility_type=FacilityType.COMMERCIAL_PAPER,
        principal=Decimal("200000.00"),
        issuance_price=Decimal("198000.00"),
        coupon_rate=Decimal("0.04"),
        tenor_months=6,
        issuance_date="2026-01-01",
        maturity_date="2026-07-01",
    )
    entry = DebtRolloverConcealment.mutate(subledger, "CP-2026", "2026-06-30")
    assert entry is not None
    assert entry.is_balanced
    assert entry.is_anomaly
    assert "ANOM_DEBT_ROLLOVER_CONCEALMENT" in entry.anomaly_ids
