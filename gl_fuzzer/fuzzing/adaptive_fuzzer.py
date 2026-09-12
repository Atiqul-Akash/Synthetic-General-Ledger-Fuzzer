"""Adaptive genetic mutator and closed-loop campaign orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid
from typing import Any, Dict, List, Optional
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyType
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.fuzzing.target import ERPExecutionTarget, TargetExecutionResult, TargetStatus
from gl_fuzzer.fuzzing.oracle import CoverageOracle, CrashMonitor, FuzzingCampaignReport


class AdaptiveMutator:
    """Evolutionary mutator adjusting mutation weights based on target crash and bypass signals."""

    OPERATORS = [
        "BOUNDARY_DOA",           # Amounts at $9,999.99 or $10,000.01
        "SQL_INJECTION",          # Malicious SQL payloads in text
        "UNICODE_OVERFLOW",       # Oversized multibyte Unicode/emojis
        "NULL_BYTE_INJECTION",    # Embedded \x00 strings
        "CLOSED_PERIOD_PROBE",    # Posting to locked period 13
        "DUPLICATE_KEY_COLLISION",# Duplicate document number
        "NON_POSITIVE_AMOUNT",    # Line item with <= 0.00
        "EXTREME_PRECISION",      # Sub-cent precision
        "WHT_EVASION",            # Zero-WHT disbursement
        "PHANTOM_PO",             # Invoice without GR
        "ANOMALOUS_PAIRING",      # Prohibited account pairing
        "INTERCOMPANY_ROUND_TRIP",# Circular intercompany loop
    ]

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        # Initialize uniform weights
        self.weights: Dict[str, float] = {op: 1.0 for op in self.OPERATORS}

    def update_weights(self, results: List[TargetExecutionResult]) -> None:
        """Reinforces operators that triggered crashes or control bypasses."""
        for r in results:
            if r.status == TargetStatus.BYPASS_DETECTED:
                # Strong positive reinforcement on bypass
                for op in self.OPERATORS:
                    if op in str(r.bypass_vector):
                        self.weights[op] = min(10.0, self.weights[op] * 1.5)
            elif r.status == TargetStatus.CRASH_500:
                # Strong positive reinforcement on server crash
                self.weights["SQL_INJECTION"] = min(10.0, self.weights["SQL_INJECTION"] * 1.3)
                self.weights["UNICODE_OVERFLOW"] = min(10.0, self.weights["UNICODE_OVERFLOW"] * 1.3)
                self.weights["NULL_BYTE_INJECTION"] = min(10.0, self.weights["NULL_BYTE_INJECTION"] * 1.3)
            elif r.status == TargetStatus.REJECTED_VALIDATION:
                # Slight decay on expected rejections
                for op in self.OPERATORS:
                    self.weights[op] = max(0.2, self.weights[op] * 0.95)

    def select_operator(self) -> str:
        ops = list(self.weights.keys())
        w = np.array([self.weights[op] for op in ops], dtype=np.float64)
        probs = w / np.sum(w)
        return str(self.rng.choice(ops, p=probs))

    def mutate_entry(self, entry: JournalEntry) -> JournalEntry:
        """Applies a targeted mutation vector to a deep copy of the entry based on active weights."""
        import copy
        entry = copy.deepcopy(entry)
        op = self.select_operator()

        def _tag(anomaly_value: str) -> None:
            entry.is_anomaly = True
            if entry.anomaly_ids is None:
                entry.anomaly_ids = []
            entry.anomaly_ids.append(anomaly_value)

        if op == "SQL_INJECTION":
            entry.header_text = "Vendor Settlement'; DROP TABLE line_items;--"
            _tag(AnomalyType.SECURITY_FUZZ_CRASH.value)

        elif op == "UNICODE_OVERFLOW":
            entry.header_text = "OVERFLOW_TEST_" + ("🚀🔥💥📈" * 150)
            _tag(AnomalyType.SECURITY_FUZZ_CRASH.value)

        elif op == "NULL_BYTE_INJECTION":
            entry.header_text = "Vendor Payment\x00ADMIN_OVERRIDE"
            _tag(AnomalyType.SECURITY_FUZZ_CRASH.value)

        elif op == "BOUNDARY_DOA":
            # Set to $9,999.99 (just under standard $10,000 approval limit).
            # To preserve double-entry balance, scale ALL lines by the same ratio.
            boundary_amt = Decimal("9999.99")
            if entry.lines:
                original_total = entry.total_debits  # debits == credits on a balanced entry
                if original_total and original_total != Decimal("0"):
                    scale = boundary_amt / original_total
                    for line in entry.lines:
                        line.amount = (line.amount * scale).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        if line.amount_local is not None:
                            line.amount_local = (line.amount_local * scale).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        if line.amount_group is not None:
                            line.amount_group = (line.amount_group * scale).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            _tag(AnomalyType.SMURFING_SPLIT_APPROVAL.value)

        elif op == "CLOSED_PERIOD_PROBE":
            entry.fiscal_period = 13
            _tag(AnomalyType.OFF_HOURS_GHOST_ENTRY.value)

        elif op == "WHT_EVASION":
            _tag(AnomalyType.TAX_EVASION_ZERO_WHT.value)

        elif op == "PHANTOM_PO":
            _tag(AnomalyType.PHANTOM_PO_THREE_WAY_BYPASS.value)

        elif op == "NON_POSITIVE_AMOUNT":
            for line in entry.lines:
                line.amount = Decimal("0.00")
                if line.amount_local is not None:
                    line.amount_local = Decimal("0.00")
                if line.amount_group is not None:
                    line.amount_group = Decimal("0.00")
            _tag(AnomalyType.SECURITY_FUZZ_CRASH.value)

        return entry


class FuzzingCampaign:
    """Orchestrates closed-loop dynamic fuzzing against ERP targets."""

    def __init__(
        self,
        target: ERPExecutionTarget,
        coa: Optional[ChartOfAccounts] = None,
        seed: Optional[int] = 42,
    ):
        self.target = target
        self.coa = coa or ChartOfAccounts.create_default()
        self.engine = BaseSynthesisEngine(coa=self.coa, seed=seed)
        self.mutator = AdaptiveMutator(seed=seed)
        self.crash_monitor = CrashMonitor()
        self.coverage_oracle = CoverageOracle()

    def run(
        self,
        iterations: int = 5,
        entries_per_iteration: int = 100,
        mutation_rate: float = 0.3,
    ) -> FuzzingCampaignReport:
        """Executes full closed-loop iterative testing campaign."""
        campaign_id = f"CAMP_{uuid.uuid4().hex[:8].upper()}"
        iteration_reports = []

        for it in range(1, iterations + 1):
            # 1. Reset target for isolation
            self.target.reset_target()

            # 2. Synthesize baseline batch
            batch = self.engine.generate_batch(
                batch_id=f"B_IT_{it:02d}",
                target_entry_count=entries_per_iteration,
            )

            # 3. Apply adaptive mutations
            for entry in batch.entries:
                if self.mutator.rng.random() < mutation_rate:
                    self.mutator.mutate_entry(entry)

            # 4. Execute against target
            results = self.target.execute_batch(batch)

            # 5. Update telemetry & oracle
            self.crash_monitor.record_results(results)
            self.coverage_oracle.update(results)

            # 6. Adapt mutator weights based on results
            self.mutator.update_weights(results)

            it_bypasses = sum(1 for r in results if r.status == TargetStatus.BYPASS_DETECTED)
            it_crashes = sum(1 for r in results if r.status == TargetStatus.CRASH_500)
            iteration_reports.append({
                "iteration": it,
                "entries_tested": len(results),
                "bypasses": it_bypasses,
                "crashes": it_crashes,
                "coverage_percent": self.coverage_oracle.coverage_percent,
                "top_operator_weights": {k: round(v, 2) for k, v in list(self.mutator.weights.items())[:5]},
            })

        return FuzzingCampaignReport(
            campaign_id=campaign_id,
            target_type=self.target.__class__.__name__,
            total_iterations=iterations,
            total_entries_posted=self.crash_monitor.total_count,
            crash_count=self.crash_monitor.crash_count,
            bypass_count=self.crash_monitor.bypass_count,
            bypass_rate=self.crash_monitor.bypass_rate,
            top_bypass_vectors=self.crash_monitor.get_top_bypass_vectors(),
            top_crash_vectors=self.crash_monitor.get_top_crash_vectors(),
            rule_coverage_percent=self.coverage_oracle.coverage_percent,
            uncovered_rules=self.coverage_oracle.uncovered_rules,
            iteration_reports=iteration_reports,
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
