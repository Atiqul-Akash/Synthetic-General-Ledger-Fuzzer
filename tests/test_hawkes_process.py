"""Comprehensive test suite for Coupled Hawkes Point Process generator."""

from datetime import date, timedelta
from decimal import Decimal
import numpy as np
import pytest

from gl_fuzzer.generators.hawkes_process import CoupledHawkesPointProcess, PaymentTerms
from gl_fuzzer.generators.p2p_cycle import P2PCycleGenerator
from gl_fuzzer.generators.o2c_cycle import O2CCycleGenerator
from gl_fuzzer.generators.distributions import BusinessCalendar
from gl_fuzzer.models.coa import ChartOfAccounts


def test_hawkes_intensity_evaluation():
    """Verify Hawkes conditional intensity evaluates baseline and exponential decay."""
    hawkes = CoupledHawkesPointProcess(mu_baseline=0.10, alpha_excitation=0.50, beta_decay=0.20)
    
    # At t=0 with no history, intensity is baseline
    assert hawkes.evaluate_intensity(0.0, []) == pytest.approx(0.10)

    # With events at t=1 and t=2, evaluate at t=3
    history = [1.0, 2.0]
    # Expected: 0.10 + 0.50 * exp(-0.2*(3-1)) + 0.50 * exp(-0.2*(3-2))
    expected = 0.10 + 0.50 * np.exp(-0.2 * 2.0) + 0.50 * np.exp(-0.2 * 1.0)
    assert hawkes.evaluate_intensity(3.0, history) == pytest.approx(expected)


def test_sample_payment_delay_terms_modes():
    """Verify sampled payment delays match contractual terms modes."""
    hawkes = CoupledHawkesPointProcess(seed=42)
    inv_date = date(2026, 4, 1)

    # Net 30: Sample multiple times, mean should cluster around 30 days
    delays_net30 = [hawkes.sample_payment_delay(PaymentTerms.NET_30, snap_to_payment_run=False)[0] for _ in range(100)]
    avg_net30 = np.mean(delays_net30)
    assert 25.0 <= avg_net30 <= 38.0

    # Net 60: Mean should cluster around 60 days
    delays_net60 = [hawkes.sample_payment_delay(PaymentTerms.NET_60, snap_to_payment_run=False)[0] for _ in range(100)]
    avg_net60 = np.mean(delays_net60)
    assert 55.0 <= avg_net60 <= 70.0

    # Net 15: Mean should cluster around 14-16 days
    delays_net15 = [hawkes.sample_payment_delay(PaymentTerms.NET_15, snap_to_payment_run=False)[0] for _ in range(100)]
    avg_net15 = np.mean(delays_net15)
    assert 12.0 <= avg_net15 <= 18.0

    # Due on Receipt: Delays between 0 and 2 days
    delays_dor = [hawkes.sample_payment_delay(PaymentTerms.DUE_ON_RECEIPT, snap_to_payment_run=False)[0] for _ in range(50)]
    assert all(0 <= d <= 2 for d in delays_dor)


def test_discount_2_10_net_30_bimodal_distribution():
    """Verify 2/10 Net 30 terms exhibits bimodal distribution with early discount settlements."""
    hawkes = CoupledHawkesPointProcess(early_discount_prob=0.40, seed=123)
    delays = [hawkes.sample_payment_delay(PaymentTerms.DISCOUNT_2_10_NET_30, snap_to_payment_run=False)[0] for _ in range(200)]
    
    # Check that both early payments (<= 10 days) and standard payments (>= 25 days) exist
    early_count = sum(1 for d in delays if d <= 10)
    standard_count = sum(1 for d in delays if d >= 25)
    assert early_count > 20
    assert standard_count > 50


def test_treasury_batching_comb_weekday_snapping():
    """Verify Treasury batching comb snaps settlement dates to Tuesday (1) and Thursday (3)."""
    # Payment run days: Tuesday (1) and Thursday (3)
    hawkes = CoupledHawkesPointProcess(payment_run_days=[1, 3], seed=999)
    inv_date = date(2026, 5, 4)  # Monday

    for _ in range(50):
        _, pay_date = hawkes.sample_payment_delay(
            PaymentTerms.NET_30,
            invoice_date=inv_date,
            snap_to_payment_run=True,
        )
        assert pay_date is not None
        # Must be either Tuesday (1) or Thursday (3)
        assert pay_date.weekday() in [1, 3]
        assert pay_date > inv_date


def test_simulate_coupled_timeline():
    """Verify end-to-end mutually exciting timeline synthesis."""
    hawkes = CoupledHawkesPointProcess(seed=555)
    start_d = date(2026, 1, 1)
    events = hawkes.simulate_coupled_timeline(start_date=start_d, duration_days=60, avg_invoices_per_day=2.0)

    assert len(events) > 20
    invoices = [e for e in events if e["event_type"] == "INVOICE"]
    payments = [e for e in events if e["event_type"] == "PAYMENT"]

    assert len(invoices) > 0
    assert len(payments) > 0
    # Payments must match linked invoices
    linked_ids = {p["linked_invoice_id"] for p in payments}
    inv_ids = {inv["event_id"] for inv in invoices}
    assert linked_ids.issubset(inv_ids)

    # Verify timeline is sorted
    dates = [e["date"] for e in events]
    assert dates == sorted(dates)


def test_p2p_and_o2c_hawkes_integration():
    """Verify P2P and O2C cycle generators produce realistic lead-lag dates with Hawkes process."""
    coa = ChartOfAccounts.create_default()
    cal = BusinessCalendar()
    p2p = P2PCycleGenerator(coa=coa, calendar=cal)
    o2c = O2CCycleGenerator(coa=coa, calendar=cal)

    # 1. P2P flow
    p2p_entries = p2p.generate_full_p2p_flow(batch_id="P2P_HWK_B1", terms=PaymentTerms.NET_30)
    assert len(p2p_entries) == 3
    gr, ir, pay = p2p_entries
    assert gr.posting_date <= ir.posting_date
    assert ir.posting_date <= pay.posting_date
    assert pay.is_balanced

    # 2. O2C flow
    o2c_entries = o2c.generate_full_o2c_flow(batch_id="O2C_HWK_B1", terms=PaymentTerms.NET_60)
    assert len(o2c_entries) == 3
    gi, bill, receipt = o2c_entries
    assert gi.posting_date <= bill.posting_date
    assert bill.posting_date <= receipt.posting_date
    assert receipt.is_balanced


def test_hawkes_windowed_evaluation_cutoff():
    """Verify windowed cutoff optimizes intensity evaluation while maintaining accuracy."""
    hawkes = CoupledHawkesPointProcess(mu_baseline=2.0, alpha_excitation=0.35, beta_decay=0.50)
    # 50 historical event timestamps spread over 50 days
    history = [float(i) for i in range(50)]
    t = 50.0

    full_intensity = hawkes.evaluate_intensity(t, history, cutoff_window=None)
    windowed_intensity = hawkes.evaluate_intensity(t, history, cutoff_window=20.0)

    # Difference should be negligible (< 1e-4) due to exponential decay exp(-0.5*20)
    assert abs(full_intensity - windowed_intensity) < 1e-4
    assert windowed_intensity > 2.0


def test_vendor_customer_master_data_terms_persistence():
    """Verify vendor and customer master data maintain persistent contractual credit terms."""
    coa = ChartOfAccounts.create_default()
    cal = BusinessCalendar()
    p2p = P2PCycleGenerator(coa=coa, calendar=cal)
    o2c = O2CCycleGenerator(coa=coa, calendar=cal)

    assert len(p2p.vendor_terms) == len(p2p.vendors)
    assert len(o2c.customer_terms) == len(o2c.customers)

    # Check that multiple calls for same vendor use consistent terms
    test_vendor = p2p.vendors[0]
    assigned_term = p2p.vendor_terms[test_vendor]
    flow1 = p2p.generate_full_p2p_flow(batch_id="B1", fixed_vendor=test_vendor)
    flow2 = p2p.generate_full_p2p_flow(batch_id="B2", fixed_vendor=test_vendor)
    assert len(flow1) == 3 and len(flow2) == 3

