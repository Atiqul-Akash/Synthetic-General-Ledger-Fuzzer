"""Unit tests for Macro-Economic Calendar and Seasonality Modulator."""

from datetime import date
import numpy as np
import pytest

from gl_fuzzer.generators.macro_calendar import MacroCalendarModulator


def test_macro_calendar_initialization():
    """Verify modulator initializes 365/366 day distributions summing to 1.0."""
    mod = MacroCalendarModulator(year=2026, rng=np.random.default_rng(42))

    assert len(mod.all_dates) == 365
    assert len(mod.business_dates) == 261  # 261 business days in 2026
    assert len(mod.weekend_dates) == 104   # 104 weekend days in 2026

    assert abs(float(np.sum(mod.daily_probs)) - 1.0) < 1e-6
    assert abs(float(np.sum(mod.biz_probs)) - 1.0) < 1e-6
    assert abs(float(np.sum(mod.weekend_probs)) - 1.0) < 1e-6


def test_day_of_week_modulation():
    """Verify mid-week peak and weekend volume suppression."""
    mod = MacroCalendarModulator(year=2026)

    # Wed May 13, 2026 vs Sun May 17, 2026 (both mid-quarter)
    wed_weight = mod.get_seasonality_multiplier(date(2026, 5, 13))
    sun_weight = mod.get_seasonality_multiplier(date(2026, 5, 17))

    assert wed_weight > sun_weight * 5  # 1.25 vs 0.15


def test_quarterly_hockey_stick_surge():
    """Verify Q1-Q3 and Q4 year-end volume surges."""
    mod = MacroCalendarModulator(year=2026)

    # Q1 close (March 28) vs mid-March (March 10) on same weekday
    # March 10 is Tuesday, March 24 is Tuesday
    tue_mid_mar = mod.get_seasonality_multiplier(date(2026, 3, 10))
    tue_close_mar = mod.get_seasonality_multiplier(date(2026, 3, 24))
    assert tue_close_mar == pytest.approx(tue_mid_mar * 1.45)

    # Q4 Year-End Close (Dec 22 Tuesday) vs Nov 10 Tuesday
    tue_nov = mod.get_seasonality_multiplier(date(2026, 11, 10))
    tue_dec_close = mod.get_seasonality_multiplier(date(2026, 12, 22))
    assert tue_dec_close == pytest.approx(tue_nov * 1.85)

    # Post-holiday January lull
    tue_jan_lull = mod.get_seasonality_multiplier(date(2026, 1, 6))
    assert tue_jan_lull == pytest.approx(tue_nov * 0.65)


def test_date_sampling_constraints():
    """Verify business and weekend sampling strictly respect calendar boundaries."""
    rng = np.random.default_rng(101)
    mod = MacroCalendarModulator(year=2026, rng=rng)

    # Business dates: Monday=0 through Friday=4
    for _ in range(100):
        biz_d = mod.sample_business_date()
        assert biz_d.weekday() < 5
        assert biz_d.year == 2026

    # Weekend dates: Saturday=5, Sunday=6
    for _ in range(100):
        wknd_d = mod.sample_weekend_date()
        assert wknd_d.weekday() >= 5
        assert wknd_d.year == 2026


def test_sampling_reproducibility():
    """Verify identical random seeds yield identical sampled dates."""
    mod1 = MacroCalendarModulator(year=2026, rng=np.random.default_rng(42))
    mod2 = MacroCalendarModulator(year=2026, rng=np.random.default_rng(42))

    dates1 = [mod1.sample_business_date() for _ in range(20)]
    dates2 = [mod2.sample_business_date() for _ in range(20)]

    assert dates1 == dates2
