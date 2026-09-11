"""Base Anomaly Mutator interface and Pipeline coordinator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, JournalEntry
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, SOXControlRef
from gl_fuzzer.generators.distributions import BusinessCalendar


class MutationContext:
    """Shared state and random generator for anomaly mutators."""

    def __init__(
        self,
        coa: ChartOfAccounts,
        calendar: BusinessCalendar,
        rng: Optional[np.random.Generator] = None,
    ):
        self.coa = coa
        self.calendar = calendar
        self.rng = rng or np.random.default_rng()
        self.base_entry_count: int = 0


class BaseAnomalyMutator(ABC):
    """Abstract base class for calibrated accounting micro-anomaly injectors."""

    anomaly_type: AnomalyType
    sox_control: SOXControlRef
    audit_script: str
    risk_level: str = "HIGH"

    @abstractmethod
    def mutate(
        self,
        batch: Batch,
        context: MutationContext,
        injection_rate: float = 0.05,
    ) -> List[AnomalyRecord]:
        """Mutates existing entries or injects new anomalous entries into the batch.
        
        Returns the list of AnomalyRecord instances describing the injected signals.
        Strictly preserves double-entry mathematical balance: Σ(Debits) == Σ(Credits).
        """
        pass
