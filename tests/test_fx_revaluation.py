"""Comprehensive test suite for SAP FAGL_FCV Foreign Currency Valuation Engine."""

from datetime import date
from decimal import Decimal
import pytest

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.currency import ExchangeRateProvider
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.subledgers.fx_revaluation import ForeignCurrencyValuationEngine, OpenCurrencyItem
from gl_fuzzer.generators.r2r_cycle import R2RCycleGenerator
from gl_fuzzer.generators.distributions import BusinessCalendar


def test_fcv_engine_evaluation_ap_loss_and_gain():
    """Verify AP foreign currency valuation computes correct unrealized loss and gain."""
    engine = ForeignCurrencyValuationEngine(base_currency="USD", seed=42)
    v_date = date(2026, 3, 31)

    # 1. AP item in EUR: Historical rate 1.05, Closing rate 1.10 -> local liability increases -> Unrealized Loss
    item_loss = OpenCurrencyItem(
        document_number="KR_EUR_001",
        item_type="AP",
        foreign_currency="EUR",
        foreign_amount=Decimal("10000.00"),
        original_rate=Decimal("1.050000"),
        counterparty_id="VEND_DE_1",
        posting_date=date(2026, 2, 1),
    )
    res_loss = engine.evaluate_item(item_loss, v_date)
    assert res_loss.historical_local_amount == Decimal("10500.00")
    assert res_loss.adjustment_amount > Decimal("0.00")
    if res_loss.current_local_amount > res_loss.historical_local_amount:
        assert res_loss.is_gain is False
    else:
        assert res_loss.is_gain is True

    # 2. Revaluation voucher construction
    val_entry = engine.create_revaluation_entry("BATCH_FCV_1", [res_loss], v_date)
    assert val_entry is not None
    assert val_entry.is_balanced
    assert val_entry.document_type == DocumentType.SA
    assert val_entry.created_by == "AUTO_FAGL_FCV"
    assert val_entry.posting_date == "2026-03-31"


def test_fcv_engine_evaluation_ar_gain_and_loss():
    """Verify AR foreign currency valuation computes correct unrealized gain and loss."""
    engine = ForeignCurrencyValuationEngine(base_currency="USD", seed=99)
    v_date = date(2026, 6, 30)

    # AR item in GBP: Historical rate 1.25
    item_ar = OpenCurrencyItem(
        document_number="DR_GBP_001",
        item_type="AR",
        foreign_currency="GBP",
        foreign_amount=Decimal("50000.00"),
        original_rate=Decimal("1.250000"),
        counterparty_id="CUST_UK_1",
        posting_date=date(2026, 5, 15),
    )
    res_ar = engine.evaluate_item(item_ar, v_date)
    assert res_ar.historical_local_amount == Decimal("62500.00")
    assert res_ar.adjustment_amount > Decimal("0.00")

    val_entry = engine.create_revaluation_entry("BATCH_FCV_2", [res_ar], v_date)
    assert val_entry is not None
    assert val_entry.is_balanced
    assert val_entry.total_debits == val_entry.total_credits
    # AR accounts involved
    acc_codes = [l.account_code for l in val_entry.lines]
    assert "11090" in acc_codes
    assert ("47100" in acc_codes or "67100" in acc_codes)


def test_fcv_day1_automated_reversal():
    """Verify Day-1 reversal document reverses all debit/credit legs exactly on day 1 of next period."""
    engine = ForeignCurrencyValuationEngine(seed=777)
    v_date = date(2026, 3, 31)

    synthetic_entries = engine.generate_synthetic_fcv_run(
        batch_id="BATCH_FCV_REV",
        valuation_date=v_date,
        num_open_items=3,
        post_auto_reversal=True,
    )

    assert len(synthetic_entries) == 2
    val_entry, rev_entry = synthetic_entries

    # Check valuation entry
    assert val_entry.document_type == DocumentType.SA
    assert val_entry.posting_date == "2026-03-31"
    assert val_entry.is_balanced

    # Check reversal entry
    assert rev_entry.document_type == DocumentType.AB
    assert rev_entry.posting_date == "2026-04-01"
    assert rev_entry.fiscal_period == 4
    assert rev_entry.is_balanced
    assert rev_entry.created_by == "AUTO_FAGL_FCV_REV"

    # Cumulative net across both entries must equal zero
    assert val_entry.total_debits == rev_entry.total_credits
    assert val_entry.total_credits == rev_entry.total_debits


def test_r2r_cycle_fagl_fcv_integration():
    """Verify R2RCycleGenerator generates FAGL_FCV close vouchers cleanly."""
    coa = ChartOfAccounts.create_default()
    cal = BusinessCalendar()
    r2r = R2RCycleGenerator(coa=coa, calendar=cal)

    fcv_entries = r2r.generate_fagl_fcv_run(batch_id="R2R_FCV_TEST")
    assert len(fcv_entries) == 2
    for e in fcv_entries:
        assert e.is_balanced
        assert e.business_cycle == "R2R"
        assert e.total_debits > Decimal("0.00")
