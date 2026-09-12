"""Statistical distributions and business temporal generators for synthetic accounting data."""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
import numpy as np


class BenfordDistribution:
    """Utilities for Benford's Law generation and statistical profiling."""

    # Benford theoretical first-digit probabilities: P(d) = log10(1 + 1/d)
    THEORETICAL_PROBS = {
        d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)
    }

    @classmethod
    def get_theoretical_array(cls) -> np.ndarray:
        """Returns array of probabilities for digits 1..9."""
        return np.array([cls.THEORETICAL_PROBS[d] for d in range(1, 10)], dtype=np.float64)

    @classmethod
    def sample_benford_first_digit(cls, rng: np.random.Generator) -> int:
        """Draw a leading digit (1-9) adhering to Benford's Law."""
        digits = np.arange(1, 10)
        probs = cls.get_theoretical_array()
        return int(rng.choice(digits, p=probs))

    @classmethod
    def sample_uniform_first_digit(cls, rng: np.random.Generator) -> int:
        """Draw an unnatural uniform first digit (1-9) with equal ~11.11% probability."""
        return int(rng.integers(1, 10))

    @classmethod
    def sample_skewed_first_digit(cls, rng: np.random.Generator, bias_digits: Tuple[int, ...] = (7, 8, 9)) -> int:
        """Draw a leading digit heavily biased towards 7, 8, or 9 (typical fraud signal)."""
        if rng.random() < 0.75:
            return int(rng.choice(bias_digits))
        return int(rng.integers(1, 10))

    @classmethod
    def synthesize_amount_with_first_digit(
        cls, first_digit: int, magnitude_min: int = 2, magnitude_max: int = 5, rng: Optional[np.random.Generator] = None
    ) -> Decimal:
        """Synthesize an amount whose leading digit is explicitly set to first_digit."""
        if rng is None:
            rng = np.random.default_rng()
        magnitude = rng.integers(magnitude_min, magnitude_max + 1)
        low_cents = first_digit * (10 ** (magnitude - 1)) * 100
        high_cents = ((first_digit + 1) * (10 ** (magnitude - 1)) * 100) - 1
        cents_int = int(rng.integers(low_cents, high_cents + 1))
        return (Decimal(cents_int) / Decimal(100)).quantize(Decimal("0.01"))



class LogNormalAmountGenerator:
    """Generates monetary amounts following empirical log-normal accounting distributions."""

    def __init__(
        self,
        mean_log: float = 7.5,    # exp(7.5) ~ $1,808 median
        sigma_log: float = 1.3,   # moderate dispersion
        min_amount: Decimal = Decimal("10.00"),
        max_amount: Decimal = Decimal("5000000.00"),
        rng: Optional[np.random.Generator] = None,
    ):
        self.mean_log = mean_log
        self.sigma_log = sigma_log
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.rng = rng if rng is not None else np.random.default_rng()

    def generate(self) -> Decimal:
        """Generate a single positive monetary amount rounded to 2 decimal places."""
        raw = self.rng.lognormal(self.mean_log, self.sigma_log)
        val = Decimal(f"{raw:.2f}").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if val < self.min_amount:
            val = self.min_amount
        elif val > self.max_amount:
            val = self.max_amount
        return val


class BusinessCalendar:
    """Generates corporate business timestamps, working hours, and off-hour windows."""

    def __init__(
        self,
        start_date: date = date(2026, 1, 1),
        end_date: date = date(2026, 12, 31),
        rng: Optional[np.random.Generator] = None,
    ):
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")
        self.start_date = start_date
        self.end_date = end_date
        self.rng = rng if rng is not None else np.random.default_rng()
        self.total_days = (end_date - start_date).days + 1

        all_dates = [self.start_date + timedelta(days=i) for i in range(self.total_days)]
        self.business_dates = [d for d in all_dates if d <= self.end_date and d.weekday() < 5]
        self.weekend_dates = [d for d in all_dates if d <= self.end_date and d.weekday() >= 5]

        # Fallbacks in case an extreme custom range with only weekends or only weekdays is provided
        if not self.business_dates:
            self.business_dates = all_dates
        if not self.weekend_dates:
            self.weekend_dates = all_dates

    def random_business_date(self) -> date:
        """Returns a random weekday (Monday-Friday) within the fiscal calendar in O(1) time."""
        idx = int(self.rng.integers(0, len(self.business_dates)))
        return self.business_dates[idx]

    def snap_to_weekday(self, target_date: date) -> date:
        """Snaps a date to the nearest weekday (Monday-Friday) within calendar bounds."""
        d = target_date
        while d.weekday() >= 5:
            d += timedelta(days=1)
        if d > self.end_date:
            d = target_date
            while d.weekday() >= 5:
                d -= timedelta(days=1)
        return min(max(d, self.start_date), self.end_date)

    def random_weekend_date(self) -> date:
        """Returns a Saturday or Sunday within the fiscal calendar in O(1) time."""
        idx = int(self.rng.integers(0, len(self.weekend_dates)))
        return self.weekend_dates[idx]

    def random_month_end_date(self) -> date:
        """Returns a business date within the last 3 business days of a month (financial close)."""
        year_months = sorted(list({(d.year, d.month) for d in self.business_dates}))
        if not year_months:
            year_months = [(self.start_date.year, int(self.rng.integers(1, 13)))]

        ym_idx = int(self.rng.integers(0, len(year_months)))
        year, month = year_months[ym_idx]

        # Find last calendar day of the selected year and month
        if month == 12:
            last_day = date(year, 12, 31)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        biz_set = set(self.business_dates)
        biz_days = []
        curr = min(last_day, self.end_date)
        while len(biz_days) < 3 and curr.month == month and curr >= self.start_date:
            if curr in biz_set:
                biz_days.append(curr)
            curr -= timedelta(days=1)

        if not biz_days:
            return self.random_business_date() if self.business_dates else last_day
        idx = int(self.rng.integers(0, len(biz_days)))
        return biz_days[idx]

    def normal_business_time(self) -> time:
        """Normal posting hours: 08:00:00 to 18:00:00."""
        hour = int(self.rng.integers(8, 18))
        minute = int(self.rng.integers(0, 60))
        second = int(self.rng.integers(0, 60))
        return time(hour, minute, second)

    def off_hours_time(self) -> time:
        """Off-hours anomaly window: 02:00:00 to 04:30:00."""
        hour = int(self.rng.integers(2, 5))
        if hour == 4:
            minute = int(self.rng.integers(0, 31))
            second = 0 if minute == 30 else int(self.rng.integers(0, 60))
        else:
            minute = int(self.rng.integers(0, 60))
            second = int(self.rng.integers(0, 60))
        return time(hour, minute, second)

    def generate_timestamp(self, is_off_hours: bool = False, is_weekend: bool = False) -> datetime:
        """Generate a complete datetime timestamp."""
        if is_weekend:
            d = self.random_weekend_date()
        else:
            d = self.random_business_date()

        if is_off_hours:
            t = self.off_hours_time()
        else:
            t = self.normal_business_time()

        return datetime.combine(d, t)
