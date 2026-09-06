"""Comprehensive unit tests for GL Fuzzer statistical and cycle generators.

Covers:
- generators.distributions: BusinessCalendar, BenfordDistribution, LogNormalAmountGenerator
- generators.base_engine: BaseSynthesisEngine
"""

from datetime import date
from decimal import Decimal
import numpy as np
import pytest

from gl_fuzzer.generators.distributions import (
    BenfordDistribution,
    BusinessCalendar,
    LogNormalAmountGenerator,
)
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine


# ==========================================
# 1. BusinessCalendar Tests
# ==========================================

def test_business_calendar_generation():
    rng = np.random.default_rng(123)
    cal = BusinessCalendar(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rng=rng,
    )

    # Random business date should be Monday-Friday (weekday < 5)
    bdate = cal.random_business_date()
    assert bdate.weekday() < 5
    assert bdate.year == 2026

    # Random weekend date should be Saturday or Sunday (weekday >= 5)
    wdate = cal.random_weekend_date()
    assert wdate.weekday() >= 5
    assert wdate.year == 2026

    # Random month end date should always be a business day (weekday < 5)
    medate = cal.random_month_end_date()
    assert medate.weekday() < 5
    assert medate.year == 2026

    # Standard business hours
    bh_time = cal.normal_business_time()
    assert 8 <= bh_time.hour <= 18

    # Off-hours time (deep night: 2am - 4am)
    oh_time = cal.off_hours_time()
    assert 2 <= oh_time.hour <= 4


# ==========================================
# 2. BenfordDistribution Tests
# ==========================================

def test_benford_distribution_properties():
    rng = np.random.default_rng(42)

    # First digit theoretical probabilities sum to 1.0
    probs = [BenfordDistribution.THEORETICAL_PROBS[d] for d in range(1, 10)]
    assert abs(sum(probs) - 1.0) < 1e-6
    # Probability of 1 is ~0.301, probability of 9 is ~0.046
    assert probs[0] > 0.30
    assert probs[8] < 0.05

    # Sample first digit produces valid digits 1-9
    sampled = [BenfordDistribution.sample_benford_first_digit(rng) for _ in range(100)]
    for d in sampled:
        assert 1 <= d <= 9

    # Synthesize amount with specified first digit
    for target_digit in range(1, 10):
        amt = BenfordDistribution.synthesize_amount_with_first_digit(target_digit, rng=rng)
        assert isinstance(amt, Decimal)
        # Verify leading non-zero digit
        s = f"{amt:.2f}".lstrip("0").lstrip(".")
        assert int(s[0]) == target_digit


# ==========================================
# 3. LogNormalAmountGenerator Tests
# ==========================================

def test_lognormal_amount_generator():
    rng = np.random.default_rng(999)
    gen = LogNormalAmountGenerator(rng=rng)

    # Sample amount generates positive Decimals quantized to cents
    for _ in range(50):
        amt = gen.generate()
        assert isinstance(amt, Decimal)
        assert amt > Decimal("0.00")
        # Ensure 2 decimal places
        assert amt == amt.quantize(Decimal("0.01"))


# ==========================================
# 4. BaseSynthesisEngine Tests
# ==========================================

def test_base_synthesis_engine_distribution():
    engine = BaseSynthesisEngine(seed=777)
    batch = engine.generate_batch(target_entry_count=100)

    assert len(batch.entries) == 100
    assert batch.is_balanced is True
    assert batch.total_debits == batch.total_credits

    # Check cycles distribution: all three cycles should be represented
    cycles = {e.business_cycle for e in batch.entries}
    assert "P2P" in cycles
    assert "O2C" in cycles
    assert "R2R" in cycles

    # Every individual entry must be balanced
    for entry in batch.entries:
        assert entry.is_balanced is True
        assert entry.balance_delta == Decimal("0.00")
