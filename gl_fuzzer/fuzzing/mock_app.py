"""Stateful mock enterprise ERP application target enforcing industrial posting rules."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import JournalEntry
from gl_fuzzer.connectors.mock_erp import MockERPConnector
from gl_fuzzer.fuzzing.target import ERPExecutionTarget, TargetExecutionResult, TargetStatus


class MockEnterpriseERPApplication(ERPExecutionTarget):
    """Realistic enterprise ERP posting target tracking control bypasses and server crashes."""

    def __init__(self, coa: Optional[ChartOfAccounts] = None):
        self.coa = coa or ChartOfAccounts.create_default()
        self.erp = MockERPConnector(coa=self.coa)
        self.erp.connect()
        self.execution_count = 0

    def reset_target(self) -> None:
        self.erp = MockERPConnector(coa=self.coa)
        self.erp.connect()
        self.execution_count = 0

    def get_health(self) -> Dict[str, Any]:
        return {
            "status": "UP",
            "type": "MockEnterpriseERPApplication",
            "total_executed": self.execution_count,
            "posted_count": len(self.erp.posted_documents),
        }

    def execute_entry(self, entry: JournalEntry) -> TargetExecutionResult:
        self.execution_count += 1
        start = time.perf_counter()

        # Compute payload hash
        payload_hash = hashlib.sha256(entry.model_dump_json().encode("utf-8")).hexdigest()

        # Post to ERP state engine
        res = self.erp.post_journal_entry(entry)
        elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))

        # Check for crash
        if res.error_code == "CRASH_500":
            return TargetExecutionResult(
                entry_id=entry.entry_id,
                status=TargetStatus.CRASH_500,
                status_code=500,
                error_code="CRASH_500",
                error_message=res.error_message,
                response_ms=elapsed_ms,
                payload_hash=payload_hash,
            )

        # Check for Security / Control Bypass:
        # If the entry was injected with an anomaly, but the ERP accepted it silently:
        if entry.is_anomaly and res.success:
            return TargetExecutionResult(
                entry_id=entry.entry_id,
                status=TargetStatus.BYPASS_DETECTED,
                status_code=200,
                response_ms=elapsed_ms,
                payload_hash=payload_hash,
                bypass_vector=",".join(entry.anomaly_ids) if entry.anomaly_ids else "UNSPECIFIED_ANOMALY",
            )

        if res.success:
            return TargetExecutionResult(
                entry_id=entry.entry_id,
                status=TargetStatus.ACCEPTED,
                status_code=200,
                response_ms=elapsed_ms,
                payload_hash=payload_hash,
            )
        else:
            # Differentiate constraint vs validation rejection
            is_constraint = res.error_code in ("ENQUEUE_DUPLICATE", "SAP_GL_ACCOUNT_NOT_FOUND", "SAP_F5_019")
            st = TargetStatus.REJECTED_CONSTRAINT if is_constraint else TargetStatus.REJECTED_VALIDATION
            return TargetExecutionResult(
                entry_id=entry.entry_id,
                status=st,
                status_code=res.status_code,
                error_code=res.error_code,
                error_message=res.error_message,
                response_ms=elapsed_ms,
                payload_hash=payload_hash,
            )
