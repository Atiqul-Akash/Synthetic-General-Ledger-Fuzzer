"""Benford's Law Invalidation Anomaly Mutator.

Perturbs natural logarithmic first-digit distributions P(d) = log10(1 + 1/d)
by synthesizing unnatural uniform digit frequencies or spikes at digits 7, 8, 9,
characteristic of fabricated invoices, duplicate billing, or kickback schemes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List
import uuid

from gl_fuzzer.models.journal import Batch
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, SOXControlRef
from gl_fuzzer.anomalies.base_mutator import BaseAnomalyMutator, MutationContext
from gl_fuzzer.generators.distributions import BenfordDistribution


class BenfordSkewMutator(BaseAnomalyMutator):
    """Mutates amounts to violate Benford's Law while maintaining exact zero-sum balance."""

    anomaly_type = AnomalyType.BENFORD_SKEW
    sox_control = SOXControlRef.FORENSIC_BENFORD
    audit_script = "AUDIT-SCRIPT-DATA-001: Chi-Square / Kuiper goodness-of-fit test against Benford logarithmic distribution"
    risk_level = "HIGH"

    def __init__(self, distortion_mode: str = "spike_789"):
        """distortion_mode: 'spike_789' (spikes at 7, 8, 9) or 'uniform' (equal 1..9 frequencies)."""
        self.distortion_mode = distortion_mode

    def mutate(
        self,
        batch: Batch,
        context: MutationContext,
        injection_rate: float = 0.08,
    ) -> List[AnomalyRecord]:
        records: List[AnomalyRecord] = []
        if not batch.entries:
            return records

        target_count = max(1, int(len(batch.entries) * injection_rate))
        # Select balanced candidate entries that are not yet flagged as anomalous
        candidates = [e for e in batch.entries if not e.is_anomaly and len(e.lines) == 2]
        if not candidates:
            return records

        selected_entries = context.rng.choice(
            candidates, size=min(target_count, len(candidates)), replace=False
        )

        for entry in selected_entries:
            anomaly_id = f"ANOM_BENFORD_{uuid.uuid4().hex[:8].upper()}"

            if self.distortion_mode == "spike_789":
                target_digit = BenfordDistribution.sample_skewed_first_digit(context.rng, bias_digits=(7, 8, 9))
            else:
                target_digit = BenfordDistribution.sample_uniform_first_digit(context.rng)

            # Generate new perturbed amount with target leading digit
            new_amount = BenfordDistribution.synthesize_amount_with_first_digit(
                first_digit=target_digit,
                magnitude_min=3,  # e.g., 100s to 10,000s
                magnitude_max=5,
                rng=context.rng,
            )

            # Update all lines equally to preserve mathematical double-entry balance
            old_amount = entry.lines[0].amount
            for line in entry.lines:
                line.amount = new_amount

            entry.is_anomaly = True
            entry.anomaly_ids.append(anomaly_id)

            record = AnomalyRecord(
                anomaly_id=anomaly_id,
                anomaly_type=self.anomaly_type,
                sox_control=self.sox_control.value,
                audit_script=self.audit_script,
                risk_level=self.risk_level,
                description=f"Transaction amount perturbed from ${old_amount} to ${new_amount} with forced leading digit {target_digit}",
                affected_entry_ids=[entry.entry_id],
                affected_line_ids=[line.line_id for line in entry.lines],
                parameters={
                    "distortion_mode": self.distortion_mode,
                    "target_leading_digit": target_digit,
                    "original_amount": str(old_amount),
                    "mutated_amount": str(new_amount),
                },
                forensic_indicator=f"Anomalous leading digit {target_digit} violating Benford's Law expected probability",
            )
            records.append(record)

        return records
