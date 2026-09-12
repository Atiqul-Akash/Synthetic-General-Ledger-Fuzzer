"""Multi-currency support and ASC 830 / IAS 21 exchange rate triangulation."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    BRL = "BRL"
    INR = "INR"
    CNY = "CNY"
    MXN = "MXN"
    SGD = "SGD"
    AED = "AED"


class ExchangeRateProvider:
    """Provides daily fluctuating spot exchange rates modeled via mean-reverting geometric Brownian motion."""

    # Baseline peg rates to USD (1 unit of Foreign Currency = X USD)
    BASELINE_TO_USD: Dict[Currency, float] = {
        Currency.USD: 1.0000,
        Currency.EUR: 1.0850,
        Currency.GBP: 1.2820,
        Currency.JPY: 0.00675,
        Currency.CHF: 1.1350,
        Currency.CAD: 0.7380,
        Currency.AUD: 0.6550,
        Currency.BRL: 0.1850,
        Currency.INR: 0.0118,
        Currency.CNY: 0.1380,
        Currency.MXN: 0.0520,
        Currency.SGD: 0.7450,
        Currency.AED: 0.2723,
    }

    def __init__(self, seed: Optional[int] = 42, year: int = 2026, years: Optional[List[int]] = None):
        self.rng = np.random.default_rng(seed)
        self.year = year
        self.years = years if years is not None else [year - 1, year, year + 1]
        self._rate_cache: Dict[Tuple[str, Currency], Decimal] = {}
        self._precompute_annual_rates()

    def _precompute_annual_rates(self) -> None:
        """Precomputes daily spot exchange rates relative to USD for all configured fiscal years."""
        # Initialize current rate with baseline
        current_rates = {curr: base for curr, base in self.BASELINE_TO_USD.items()}
        volatility = 0.006  # ~0.6% daily volatility
        reversion_speed = 0.05  # Mean reversion pulling back to baseline

        for y in self.years:
            start_date = date(y, 1, 1)
            total_days = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365

            for day_offset in range(total_days):
                current_date = start_date + timedelta(days=day_offset)
                date_str = current_date.isoformat()

                for curr, baseline in self.BASELINE_TO_USD.items():
                    if curr == Currency.USD:
                        rate_dec = Decimal("1.000000")
                    else:
                        # Mean-reverting Ornstein-Uhlenbeck / GBM drift
                        drift = reversion_speed * (baseline - current_rates[curr])
                        shock = self.rng.normal(0, volatility * current_rates[curr])
                        new_rate = max(0.0001, current_rates[curr] + drift + shock)
                        current_rates[curr] = new_rate
                        rate_dec = Decimal(f"{new_rate:.6f}")

                    self._rate_cache[(date_str, curr)] = rate_dec

    def get_rate_to_usd(self, from_currency: Currency | str, date_str: str) -> Decimal:
        """Returns the spot conversion rate from from_currency to USD on date_str."""
        if isinstance(from_currency, str):
            try:
                from_currency = Currency(from_currency.upper())
            except ValueError:
                from_currency = Currency.USD

        if from_currency == Currency.USD:
            return Decimal("1.000000")

        clean_date = str(date_str).strip()
        if len(clean_date) == 8 and clean_date.isdigit():
            date_key = f"{clean_date[:4]}-{clean_date[4:6]}-{clean_date[6:8]}"
        else:
            date_key = clean_date[:10]  # Ensure YYYY-MM-DD
        rate = self._rate_cache.get((date_key, from_currency))
        if rate is None:
            # Fallback to baseline
            rate = Decimal(f"{self.BASELINE_TO_USD.get(from_currency, 1.0):.6f}")
        return rate

    def get_exchange_rate(
        self,
        from_currency: Currency | str,
        to_currency: Currency | str,
        date_str: str,
    ) -> Decimal:
        """Triangulates spot conversion rate between any two currencies via USD base."""
        if from_currency == to_currency:
            return Decimal("1.000000")

        from_to_usd = self.get_rate_to_usd(from_currency, date_str)
        to_to_usd = self.get_rate_to_usd(to_currency, date_str)

        if to_to_usd == Decimal("0.000000"):
            return Decimal("1.000000")

        # Rate = (From -> USD) / (To -> USD)
        triangulated = from_to_usd / to_to_usd
        return triangulated.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def convert(
        self,
        amount: Decimal,
        from_currency: Currency | str,
        to_currency: Currency | str,
        date_str: str,
    ) -> Tuple[Decimal, Decimal]:
        """Converts an amount from one currency to another.
        
        Returns: (converted_amount_quantized_to_cents, exchange_rate_used)
        """
        if from_currency == to_currency:
            return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), Decimal("1.000000")

        rate = self.get_exchange_rate(from_currency, to_currency, date_str)
        converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return converted, rate
