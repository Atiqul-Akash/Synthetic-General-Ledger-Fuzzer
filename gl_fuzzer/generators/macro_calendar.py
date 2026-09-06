"""Macro-economic calendar and seasonal transaction volume modulator.

Simulates enterprise accounting seasonality:
- Quarter-end "hockey stick" surges (Q1, Q2, Q3 +40%)
- Q4 fiscal year-end close and holiday retail push (+80%)
- Day-of-week enterprise cadence (Tue-Thu peak, weekend dip)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional
import numpy as np


class MacroCalendarModulator:
    """Modulates transaction volume probabilities based on macro-economic cycles and financial closing periods."""

    def __init__(self, year: int = 2026, rng: Optional[np.random.Generator] = None):
        self.year = year
        self.rng = rng if rng is not None else np.random.default_rng(42)
        self.start_date = date(year, 1, 1)
        self.end_date = date(year, 12, 31)
        self.total_days = (self.end_date - self.start_date).days + 1

        self.all_dates: List[date] = [self.start_date + timedelta(days=i) for i in range(self.total_days)]
        self.business_dates: List[date] = [d for d in self.all_dates if d.weekday() < 5]
        self.weekend_dates: List[date] = [d for d in self.all_dates if d.weekday() >= 5]

        # Calculate seasonal weights
        self.daily_weights = np.array([self._compute_date_weight(d) for d in self.all_dates], dtype=np.float64)
        self.daily_probs = self.daily_weights / np.sum(self.daily_weights)

        # Business day normalized probabilities
        biz_weights = np.array([self._compute_date_weight(d) for d in self.business_dates], dtype=np.float64)
        self.biz_probs = biz_weights / np.sum(biz_weights)

        # Weekend normalized probabilities
        weekend_weights = np.array([self._compute_date_weight(d) for d in self.weekend_dates], dtype=np.float64)
        self.weekend_probs = weekend_weights / np.sum(weekend_weights)

    def _compute_date_weight(self, d: date) -> float:
        """Calculates relative transaction probability weight for a given date."""
        weight = 1.0

        # 1. Day of Week Modulation
        # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        weekday = d.weekday()
        if weekday in (1, 2, 3):  # Tue, Wed, Thu (Peak corporate posting days)
            weight *= 1.25
        elif weekday in (0, 4):   # Mon, Fri
            weight *= 0.95
        else:                     # Weekends (Automated system batches only)
            weight *= 0.15

        # 2. Quarter-End Hockey-Stick Surges
        # Q1 close: March 24-31
        if d.month == 3 and d.day >= 24:
            weight *= 1.45
        # Q2 close: June 24-30
        elif d.month == 6 and d.day >= 24:
            weight *= 1.45
        # Q3 close: September 24-30
        elif d.month == 9 and d.day >= 24:
            weight *= 1.45
        # Q4 Year-End Close & Holiday Push: December 15-31
        elif d.month == 12 and d.day >= 15:
            weight *= 1.85
        # Post-holiday January lull: Jan 1-7
        elif d.month == 1 and d.day <= 7:
            weight *= 0.65

        return weight

    def sample_business_date(self) -> date:
        """Samples a business day weighted by corporate quarterly seasonality."""
        idx = int(self.rng.choice(len(self.business_dates), p=self.biz_probs))
        return self.business_dates[idx]

    def sample_weekend_date(self) -> date:
        """Samples a weekend date weighted by seasonal activity."""
        idx = int(self.rng.choice(len(self.weekend_dates), p=self.weekend_probs))
        return self.weekend_dates[idx]

    def sample_any_date(self) -> date:
        """Samples any calendar date weighted by overall macro seasonality."""
        idx = int(self.rng.choice(len(self.all_dates), p=self.daily_probs))
        return self.all_dates[idx]

    def get_seasonality_multiplier(self, d: date) -> float:
        """Returns the volume multiplier for a specific calendar date."""
        return self._compute_date_weight(d)
