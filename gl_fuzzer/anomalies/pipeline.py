"""Anomaly Mutator Pipeline for orchestrating calibrated perturbation passes."""

from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType
from gl_fuzzer.generators.distributions import BusinessCalendar
from gl_fuzzer.anomalies.base_mutator import BaseAnomalyMutator, MutationContext
from gl_fuzzer.anomalies.smurfing import SmurfingMutator
from gl_fuzzer.anomalies.ghost_entries import GhostEntriesMutator
from gl_fuzzer.anomalies.benford_skew import BenfordSkewMutator
from gl_fuzzer.anomalies.anomalous_pairings import AnomalousPairingsMutator
from gl_fuzzer.anomalies.round_tripping import CircularRoundTrippingMutator


class AnomalyPipeline:
    """Coordinates and executes calibrated accounting anomaly injection passes."""

    def __init__(
        self,
        coa: Optional[ChartOfAccounts] = None,
        mutators: Optional[List[BaseAnomalyMutator]] = None,
        seed: Optional[int] = None,
    ):
        self.coa = coa or ChartOfAccounts.create_default()
        self.rng = np.random.default_rng(seed)
        self.calendar = BusinessCalendar(rng=self.rng)
        self.context = MutationContext(coa=self.coa, calendar=self.calendar, rng=self.rng)

        # Default suite with all 5 calibrated micro-anomalies
        self.mutators = mutators or [
            SmurfingMutator(),
            GhostEntriesMutator(),
            BenfordSkewMutator(),
            AnomalousPairingsMutator(),
            CircularRoundTrippingMutator(),
        ]

    def inject_anomalies(
        self,
        batch: Batch,
        overall_anomaly_rate: float = 0.05,
        rates_per_type: Optional[Dict[AnomalyType, float]] = None,
    ) -> List[AnomalyRecord]:
        """Runs the mutator pipeline on the given batch and returns all generated AnomalyRecords."""
        all_records: List[AnomalyRecord] = []
        self.context.base_entry_count = len(batch.entries)
        rates = rates_per_type or {}

        # Determine individual mutator rates (distributed evenly if not explicitly specified)
        default_per_mutator = overall_anomaly_rate / max(1, len(self.mutators))

        for mutator in self.mutators:
            rate = rates.get(mutator.anomaly_type, default_per_mutator)
            if rate <= 0.0:
                continue

            records = mutator.mutate(batch=batch, context=self.context, injection_rate=rate)
            all_records.extend(records)

        return all_records
