"""Unit tests for P2P, O2C, and R2R accounting cycle generators."""

from decimal import Decimal
import numpy as np
import pytest

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.generators.distributions import BusinessCalendar, LogNormalAmountGenerator
from gl_fuzzer.generators.p2p_cycle import P2PCycleGenerator
from gl_fuzzer.generators.o2c_cycle import O2CCycleGenerator
from gl_fuzzer.generators.r2r_cycle import R2RCycleGenerator
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine


@pytest.fixture
def test_setup():
    coa = ChartOfAccounts.create_default()
    rng = np.random.default_rng(42)
    calendar = BusinessCalendar(rng=rng)
    amount_gen = LogNormalAmountGenerator(rng=rng)
    return coa, calendar, amount_gen, rng


def test_p2p_full_flow(test_setup):
    coa, calendar, amount_gen, rng = test_setup
    p2p = P2PCycleGenerator(coa=coa, calendar=calendar, amount_gen=amount_gen, rng=rng)

    entries = p2p.generate_full_p2p_flow(batch_id="TEST_B1", fixed_amount=Decimal("2500.00"), fixed_vendor="VEND_TEST")
    assert len(entries) == 3

    gr, ir, pay = entries

    # Check Goods Receipt
    assert gr.document_type.value == "WE"
    assert gr.is_balanced
    assert gr.lines[0].account_code == "14000"  # Inventory
    assert gr.lines[1].account_code == "21100"  # GR/IR Clearing

    # Check Invoice Receipt
    assert ir.document_type.value == "KR"
    assert ir.is_balanced
    assert ir.lines[0].account_code == "21100"  # Clear GR/IR
    assert ir.lines[1].account_code == "20000"  # AP Trade
    assert ir.lines[1].vendor_id == "VEND_TEST"

    # Check Payment
    assert pay.document_type.value == "KZ"
    assert pay.is_balanced
    assert pay.lines[0].account_code == "20000"  # Settle AP
    assert pay.lines[0].clearing_doc == ir.document_number
    assert pay.lines[1].account_code == "10100"  # Cash


def test_o2c_full_flow(test_setup):
    coa, calendar, amount_gen, rng = test_setup
    o2c = O2CCycleGenerator(coa=coa, calendar=calendar, amount_gen=amount_gen, rng=rng)

    entries = o2c.generate_full_o2c_flow(batch_id="TEST_B1", fixed_amount=Decimal("10000.00"), fixed_customer="CUST_TEST")
    assert len(entries) == 3

    gi, bill, pay = entries

    # Check Goods Issue
    assert gi.document_type.value == "WA"
    assert gi.is_balanced
    assert gi.lines[0].account_code == "50000"  # COGS
    assert gi.lines[1].account_code == "14100"  # Inventory

    # Check Billing (Multi-leg with Sales Tax)
    assert bill.document_type.value == "DR"
    assert bill.is_balanced
    assert len(bill.lines) == 3
    assert bill.lines[0].account_code == "11000"  # AR Trade (total)
    assert bill.lines[1].account_code == "40000"  # Sales Revenue
    assert bill.lines[2].account_code == "22000"  # Sales Tax
    assert bill.lines[0].amount == Decimal("10600.00")  # 10,000 + 6% tax

    # Check Cash Receipt
    assert pay.document_type.value == "DZ"
    assert pay.is_balanced
    assert pay.lines[0].amount == Decimal("10600.00")
    assert pay.lines[1].clearing_doc == bill.document_number


def test_o2c_generate_customer_payment(test_setup):
    coa, calendar, amount_gen, rng = test_setup
    o2c = O2CCycleGenerator(coa=coa, calendar=calendar, amount_gen=amount_gen, rng=rng)

    billing = o2c.generate_single_customer_invoice(batch_id="TEST_B1", customer="CUST_ACME", amount=Decimal("4500.00"))
    assert billing.document_type.value == "DR"

    payment = o2c.generate_customer_payment(batch_id="TEST_B1", billing_entry=billing)
    assert payment.document_type.value == "DZ"
    assert payment.is_balanced
    assert payment.lines[0].amount == Decimal("4500.00")
    assert payment.lines[1].account_code == "11000"
    assert payment.lines[1].clearing_doc == billing.document_number
    assert payment.lines[1].customer_id == "CUST_ACME"


def test_calendar_snap_to_weekday(test_setup):
    from datetime import date
    coa, calendar, amount_gen, rng = test_setup
    # Saturday 2026-01-03 should snap to Monday 2026-01-05
    sat = date(2026, 1, 3)
    weekday = calendar.snap_to_weekday(sat)
    assert weekday.weekday() < 5
    assert weekday == date(2026, 1, 5)


def test_r2r_periodic_entries(test_setup):
    coa, calendar, amount_gen, rng = test_setup
    r2r = R2RCycleGenerator(coa=coa, calendar=calendar, amount_gen=amount_gen, rng=rng)

    depr = r2r.generate_depreciation_run(batch_id="TEST_B1")
    assert depr.is_balanced
    assert depr.lines[0].account_code == "65000"
    assert depr.lines[1].account_code == "17900"

    payroll = r2r.generate_payroll_run(batch_id="TEST_B1")
    assert payroll.is_balanced
    assert len(payroll.lines) == 4
    assert payroll.lines[0].account_code == "61000"  # Salaries Exp
    assert payroll.lines[1].account_code == "61100"  # Tax Exp
    assert payroll.lines[2].account_code == "21200"  # Salaries Payable
    assert payroll.lines[3].account_code == "21300"  # Tax Withholding


def test_base_synthesis_engine_batch():
    engine = BaseSynthesisEngine(seed=123)
    batch = engine.generate_batch(target_entry_count=50)

    assert len(batch.entries) == 50
    assert batch.is_balanced
    for entry in batch.entries:
        assert entry.is_balanced
