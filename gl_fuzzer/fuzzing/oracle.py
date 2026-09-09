"""Crash monitor, coverage oracle, and campaign report generation."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from gl_fuzzer.fuzzing.target import TargetExecutionResult, TargetStatus


class FuzzingCampaignReport(BaseModel):
    """Executive vulnerability and control resilience report."""
    campaign_id: str
    target_type: str
    total_iterations: int
    total_entries_posted: int
    crash_count: int
    bypass_count: int
    bypass_rate: float
    top_bypass_vectors: List[str] = Field(default_factory=list)
    top_crash_vectors: List[str] = Field(default_factory=list)
    rule_coverage_percent: float = 0.0
    uncovered_rules: List[str] = Field(default_factory=list)
    iteration_reports: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: str


class CrashMonitor:
    """Monitors, tallies, and triages execution results and server crashes."""

    def __init__(self):
        self.results: List[TargetExecutionResult] = []

    def record_result(self, res: TargetExecutionResult) -> None:
        self.results.append(res)

    def record_results(self, results: List[TargetExecutionResult]) -> None:
        self.results.extend(results)

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def crash_count(self) -> int:
        return sum(1 for r in self.results if r.status == TargetStatus.CRASH_500)

    @property
    def bypass_count(self) -> int:
        return sum(1 for r in self.results if r.status == TargetStatus.BYPASS_DETECTED)

    @property
    def bypass_rate(self) -> float:
        total = self.total_count
        return round(float(self.bypass_count / total), 4) if total > 0 else 0.0

    def get_top_bypass_vectors(self, top_n: int = 5) -> List[str]:
        bypasses = [r.bypass_vector for r in self.results if r.status == TargetStatus.BYPASS_DETECTED and r.bypass_vector]
        return [f"{vec} ({cnt}x)" for vec, cnt in Counter(bypasses).most_common(top_n)]

    def get_top_crash_vectors(self, top_n: int = 5) -> List[str]:
        crashes = [r.error_message or r.error_code or "CRASH" for r in self.results if r.status == TargetStatus.CRASH_500]
        return [f"{msg[:60]} ({cnt}x)" for msg, cnt in Counter(crashes).most_common(top_n)]


class CoverageOracle:
    """Tracks coverage of ERP validation branches and error condition rules."""

    TARGET_RULES = [
        "SAP_F5_022",              # Imbalance rejection
        "SAP_F5_201",              # Closed period lock
        "SAP_GL_ACCOUNT_NOT_FOUND",# Unknown G/L account
        "SAP_F5_019",              # Non-positive amount check
        "ENQUEUE_DUPLICATE",       # Document number uniqueness
        "SAP_F5_COBL_REQUIRED",    # Mandatory cost center
        "CREDIT_LIMIT_EXCEEDED",   # Customer credit limit check
        "SQL_CHECK_IMBALANCE",     # Relational SQL balance check
        "CRASH_500",               # Memory stress crash
    ]

    def __init__(self):
        self.exercised_rules: set[str] = set()

    def update(self, results: List[TargetExecutionResult]) -> None:
        for r in results:
            if r.error_code:
                self.exercised_rules.add(r.error_code)

    @property
    def coverage_percent(self) -> float:
        covered = sum(1 for rule in self.TARGET_RULES if rule in self.exercised_rules)
        return round(float(covered / len(self.TARGET_RULES)) * 100, 2)

    @property
    def uncovered_rules(self) -> List[str]:
        return [rule for rule in self.TARGET_RULES if rule not in self.exercised_rules]
