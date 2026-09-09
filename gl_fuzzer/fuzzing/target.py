"""Abstract execution target interface and execution result data structures for ERP fuzzing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from gl_fuzzer.models.journal import Batch, JournalEntry


class TargetStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_VALIDATION = "REJECTED_VALIDATION"      # Standard accounting rule rejection
    REJECTED_CONSTRAINT = "REJECTED_CONSTRAINT"      # Relational DB constraint violation (FK/Unique/Check)
    CRASH_500 = "CRASH_500"                          # Uncaught 500 exception / memory stress crash
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    BYPASS_DETECTED = "BYPASS_DETECTED"              # High-severity: Anomaly slipped through without rejection!


class TargetExecutionResult(BaseModel):
    """Detailed response telemetry returned from target system under test."""
    entry_id: str
    status: TargetStatus
    status_code: int = 200
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    response_ms: int = 0
    payload_hash: str
    bypass_vector: Optional[str] = None


class ERPExecutionTarget(ABC):
    """Abstract target system against which the dynamic fuzzer executes test campaigns."""

    @abstractmethod
    def execute_entry(self, entry: JournalEntry) -> TargetExecutionResult:
        """Executes a single journal entry against the target application/database."""
        pass

    def execute_batch(self, batch: Batch) -> List[TargetExecutionResult]:
        """Executes an entire batch of journal entries sequentially."""
        return [self.execute_entry(entry) for entry in batch.entries]

    @abstractmethod
    def reset_target(self) -> None:
        """Resets target state (clears tables/sandboxes) for a new fuzzing iteration."""
        pass

    @abstractmethod
    def get_health(self) -> Dict[str, Any]:
        """Returns health telemetry and uptime of the target."""
        pass
