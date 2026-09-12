"""Coupled Hawkes Point Process Generator for Invoice-to-Payment Lead Times.

Models mutually exciting temporal point processes where invoice generation events
excite subsequent payment clearance intensities according to contractual credit terms
(Net 30, Net 60, 2/10 Net 30) and weekly corporate Treasury disbursement runs (e.g. SAP F110).
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class PaymentTerms(str, Enum):
    """Standard corporate payment and credit terms."""
    DUE_ON_RECEIPT = "DUE_ON_RECEIPT"     # Immediate settlement (0-2 days)
    NET_15 = "NET_15"                     # Net 15 days
    NET_30 = "NET_30"                     # Standard corporate Net 30
    NET_60 = "NET_60"                     # Extended supply chain Net 60
    DISCOUNT_2_10_NET_30 = "2_10_NET_30"  # 2% cash discount if paid in 10 days, otherwise Net 30


class CoupledHawkesPointProcess:
    """Coupled (bivariate / mutually exciting) Hawkes point process generator.
    
    In corporate accounting, invoices (Type 1) excite payment events (Type 2) via
    a delayed intensity kernel centered on contractual terms:
    
        lambda_payment(t) = mu_0 + sum_{t_i < t} alpha * kappa(t - t_i; Terms)
    
    where kappa(tau) is a terms-specific probability density with discrete weekly
    Treasury payment batching (e.g. Tuesday / Thursday disbursement runs).
    """

    def __init__(
        self,
        mu_baseline: float = 2.0,
        alpha_excitation: float = 0.35,
        beta_decay: float = 0.50,
        payment_run_days: Optional[List[int]] = None,
        early_discount_prob: float = 0.40,
        late_payment_prob: float = 0.18,
        seed: Optional[int] = 42,
    ):
        """
        Args:
            mu_baseline: Background baseline intensity for spontaneous invoices.
            alpha_excitation: Excitation coefficient transferring invoice activity to payments.
            beta_decay: Temporal decay parameter for Hawkes intensity.
            payment_run_days: Weekdays when automated Treasury payment batches execute.
                              (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday).
                              Defaults to [1, 3] (Tuesday and Thursday payment runs).
            early_discount_prob: Probability of paying within 10 days for 2/10 Net 30 terms.
            late_payment_prob: Probability of delinquency / delayed payment past contractual terms.
            seed: Random seed for reproducible generation.
        """
        self.mu_baseline = mu_baseline
        self.alpha_excitation = alpha_excitation
        self.beta_decay = beta_decay
        self.payment_run_days = payment_run_days if payment_run_days is not None else [1, 3]
        self.early_discount_prob = early_discount_prob
        self.late_payment_prob = late_payment_prob
        self.rng = np.random.default_rng(seed)

    def evaluate_intensity(
        self,
        t: float,
        event_history: List[float],
        cutoff_window: Optional[float] = None,
    ) -> float:
        """Evaluates Hawkes conditional intensity lambda(t) given past invoice timestamps.
        
        Args:
            t: Current time offset in days.
            event_history: Chronological list of historical event timestamps.
            cutoff_window: Optional lookback window (in days) to truncate decayed events
                           where exp(-beta * tau) < 1e-5. Ensures O(k) speed for long timelines.
        """
        intensity = self.mu_baseline
        min_t = (t - cutoff_window) if cutoff_window is not None else None
        for t_i in reversed(event_history):
            if min_t is not None and t_i < min_t:
                break
            if t_i < t:
                intensity += self.alpha_excitation * math.exp(-self.beta_decay * (t - t_i))
        return intensity

    def sample_payment_delay(
        self,
        terms: Union[PaymentTerms, str] = PaymentTerms.NET_30,
        invoice_date: Optional[date] = None,
        snap_to_payment_run: bool = True,
        rng: Optional[np.random.Generator] = None,
    ) -> Tuple[int, Optional[date]]:
        """Samples realistic invoice-to-payment delay days and computes settlement date.
        
        Returns:
            Tuple of (delay_days, settlement_date). If invoice_date is None, settlement_date is None.
        """
        local_rng = rng or self.rng

        if isinstance(terms, str):
            clean_terms = terms.strip().upper().replace("/", "_").replace(" ", "_").replace("-", "_")
            if clean_terms in PaymentTerms.__members__:
                terms = PaymentTerms[clean_terms]
            else:
                try:
                    terms = PaymentTerms(terms.upper())
                except ValueError:
                    terms = PaymentTerms.NET_30

        if terms == PaymentTerms.DUE_ON_RECEIPT:
            raw_delay = int(local_rng.integers(0, 3))

        elif terms == PaymentTerms.NET_15:
            # Mode at 14 days, std 1.5 days
            is_late = bool(local_rng.random() < self.late_payment_prob)
            if is_late:
                raw_delay = int(local_rng.normal(20.0, 3.0))
            else:
                raw_delay = int(local_rng.normal(14.0, 1.5))
            raw_delay = max(1, raw_delay)

        elif terms == PaymentTerms.DISCOUNT_2_10_NET_30:
            # Bimodal: early discount cluster vs standard Net 30 cluster
            takes_discount = bool(local_rng.random() < self.early_discount_prob)
            if takes_discount:
                # Early discount taken: payment executes days 7-10
                raw_delay = int(local_rng.integers(7, 11))
            else:
                # Standard Net 30 cluster
                is_late = bool(local_rng.random() < self.late_payment_prob)
                if is_late:
                    raw_delay = int(local_rng.normal(42.0, 6.0))
                else:
                    raw_delay = int(local_rng.normal(29.0, 2.0))
            raw_delay = max(2, raw_delay)

        elif terms == PaymentTerms.NET_60:
            is_late = bool(local_rng.random() < self.late_payment_prob)
            if is_late:
                raw_delay = int(local_rng.normal(74.0, 8.0))
            else:
                raw_delay = int(local_rng.normal(59.0, 2.5))
            raw_delay = max(10, raw_delay)

        else:
            # Default NET_30
            is_late = bool(local_rng.random() < self.late_payment_prob)
            is_early = bool(local_rng.random() < 0.08)
            if is_late:
                # Late payment tail: 35-55 days
                raw_delay = int(local_rng.normal(42.0, 5.0))
            elif is_early:
                # Early clearance: 14-22 days
                raw_delay = int(local_rng.normal(18.0, 3.0))
            else:
                # Terms modal spike around day 28-31
                raw_delay = int(local_rng.normal(29.5, 2.0))
            raw_delay = max(3, raw_delay)

        if invoice_date is None:
            return raw_delay, None

        # Calculate raw calendar date
        target_date = invoice_date + timedelta(days=raw_delay)

        # Snap to Treasury batch run day and avoid weekends (strictly weekday 0-4)
        valid_run_days = [d for d in self.payment_run_days if 0 <= d <= 4] if self.payment_run_days else []
        if snap_to_payment_run and valid_run_days:
            while target_date.weekday() >= 5 or target_date.weekday() not in valid_run_days:
                target_date += timedelta(days=1)
        else:
            # Standard business day snap: weekend moves to Monday
            while target_date.weekday() >= 5:
                target_date += timedelta(days=1)

        final_delay = max(0, (target_date - invoice_date).days)
        return final_delay, target_date

    def simulate_coupled_timeline(
        self,
        start_date: date,
        duration_days: int = 90,
        avg_invoices_per_day: float = 3.0,
        max_daily_invoices: int = 150,
        terms_weights: Optional[Dict[PaymentTerms, float]] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> List[Dict[str, Any]]:
        """Simulates an end-to-end mutually exciting invoice and payment timeline."""
        local_rng = rng or self.rng
        weights = terms_weights or {
            PaymentTerms.NET_30: 0.55,
            PaymentTerms.DISCOUNT_2_10_NET_30: 0.20,
            PaymentTerms.NET_60: 0.15,
            PaymentTerms.NET_15: 0.07,
            PaymentTerms.DUE_ON_RECEIPT: 0.03,
        }
        if not weights or sum(weights.values()) <= 0:
            raise ValueError("terms_weights must be a non-empty mapping with positive sum.")
        terms_list = list(weights.keys())
        terms_probs = np.array(list(weights.values()), dtype=np.float64)
        terms_probs /= terms_probs.sum()

        events: List[Dict[str, Any]] = []
        invoice_history_days: List[float] = []

        for day_offset in range(duration_days):
            current_date = start_date + timedelta(days=day_offset)
            if current_date.weekday() >= 5:
                continue  # No invoices created on weekends

            # Evaluate current Hawkes intensity with exponential lookback window
            intensity = self.evaluate_intensity(float(day_offset), invoice_history_days, cutoff_window=25.0)
            scale = avg_invoices_per_day / max(0.1, self.mu_baseline)
            lambda_day = min(max(0.5, float(intensity) * scale), float(max_daily_invoices))
            num_invoices = min(int(local_rng.poisson(lambda_day)), max_daily_invoices)

            for inv_idx in range(num_invoices):
                invoice_history_days.append(float(day_offset))
                selected_terms = local_rng.choice(terms_list, p=terms_probs)
                terms_str = selected_terms.value if hasattr(selected_terms, "value") else str(selected_terms)
                inv_id = f"INV_HWK_{day_offset:03d}_{inv_idx:02d}"

                delay_days, pay_date = self.sample_payment_delay(
                    terms=selected_terms,
                    invoice_date=current_date,
                    snap_to_payment_run=True,
                    rng=local_rng,
                )

                events.append({
                    "event_id": inv_id,
                    "event_type": "INVOICE",
                    "date": current_date.isoformat(),
                    "terms": terms_str,
                    "delay_days": delay_days,
                    "payment_date": pay_date.isoformat() if pay_date else None,
                })

                if pay_date:
                    events.append({
                        "event_id": f"PAY_FOR_{inv_id}",
                        "event_type": "PAYMENT",
                        "date": pay_date.isoformat(),
                        "linked_invoice_id": inv_id,
                        "terms": terms_str,
                    })

        # Sort all events chronologically
        events.sort(key=lambda ev: (ev["date"], 0 if ev["event_type"] == "INVOICE" else 1))
        return events
