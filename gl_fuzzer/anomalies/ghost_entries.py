"""Off-Hours / Ghost Entries Anomaly Mutator.

Simulates unauthorized Manual Journal Entries (MJEs) or management override
posted during weekends, non-working holidays, or off-hours (02:00 AM - 04:30 AM)
by dormant, service, or unauthorized administrative accounts.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List
import uuid

from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, SOXControlRef
from gl_fuzzer.anomalies.base_mutator import BaseAnomalyMutator, MutationContext


class GhostEntriesMutator(BaseAnomalyMutator):
    """Injects off-hours / weekend manual journal entries by ghost user accounts."""

    anomaly_type = AnomalyType.OFF_HOURS_GHOST_ENTRY
    sox_control = SOXControlRef.MJE_MANAGEMENT_OVERRIDE
    audit_script = "AUDIT-SCRIPT-MJE-002: Filter document type 'MJE'/'SA' with posting timestamps between 22:00-06:00 or weekends"
    risk_level = "HIGH"

    def __init__(self, ghost_users: list[str] | None = None):
        self.ghost_users = ghost_users or [
            "SVC_DORMANT_ADMIN",
            "MIGRATION_USER_99",
            "TERMINATED_USER_104",
            "EMERGENCY_PATCH_ACCT",
        ]

    def mutate(
        self,
        batch: Batch,
        context: MutationContext,
        injection_rate: float = 0.05,
    ) -> List[AnomalyRecord]:
        records: List[AnomalyRecord] = []
        num_entries = max(1, int(len(batch.entries) * injection_rate))
        company_code = batch.entries[0].company_code if batch.entries else "1000"

        for _ in range(num_entries):
            anomaly_id = f"ANOM_GHOST_{uuid.uuid4().hex[:8].upper()}"
            ghost_user = str(context.rng.choice(self.ghost_users))
            is_weekend = bool(context.rng.random() < 0.60)
            is_deep_night = True  # strictly off-hours

            timestamp = context.calendar.generate_timestamp(is_off_hours=is_deep_night, is_weekend=is_weekend)
            p_date_str = timestamp.date().isoformat()
            p_time_str = timestamp.time().strftime("%H:%M:%S")

            raw_amt = float(context.rng.uniform(15000.0, 350000.0))
            amt = Decimal(f"{raw_amt:.2f}")

            entry_id = f"DOC_GHOST_{uuid.uuid4().hex[:8].upper()}"
            line1_id = f"{entry_id}-001"
            line2_id = f"{entry_id}-002"

            # Manual adjusting entry debiting operating expense and crediting accrued liabilities
            lines = [
                LineItem(
                    line_id=line1_id,
                    entry_id=entry_id,
                    line_number=1,
                    account_code="69000",
                    account_name="Miscellaneous Operating Expense",
                    debit_credit=DebitCredit.DEBIT,
                    amount=amt,
                    posting_key="40",
                    cost_center="CC_CORP",
                    line_text="Manual adjustment per management directive",
                ),
                LineItem(
                    line_id=line2_id,
                    entry_id=entry_id,
                    line_number=2,
                    account_code="21000",
                    account_name="Accrued Operating Expenses",
                    debit_credit=DebitCredit.CREDIT,
                    amount=amt,
                    posting_key="50",
                    line_text="Manual accrual adjustment offset",
                ),
            ]

            ghost_entry = JournalEntry(
                entry_id=entry_id,
                batch_id=batch.batch_id,
                company_code=company_code,
                fiscal_year=timestamp.year,
                fiscal_period=timestamp.month,
                document_type=DocumentType.MJE,
                document_number=f"190{context.rng.integers(100000, 999999)}",
                posting_date=p_date_str,
                document_date=p_date_str,
                entry_time=p_time_str,
                created_at=f"{p_date_str}T{p_time_str}Z",
                created_by=ghost_user,
                reference="MJE-OVERRIDE",
                header_text="Manual Management Adjustment",
                business_cycle="R2R",
                lines=lines,
                is_anomaly=True,
                anomaly_ids=[anomaly_id],
            )
            batch.entries.append(ghost_entry)

            record = AnomalyRecord(
                anomaly_id=anomaly_id,
                anomaly_type=self.anomaly_type,
                sox_control=self.sox_control.value,
                audit_script=self.audit_script,
                risk_level=self.risk_level,
                description=f"Manual Journal Entry created at {p_time_str} ({'Weekend' if is_weekend else 'Weekday Off-Hours'}) by {ghost_user}",
                affected_entry_ids=[entry_id],
                affected_line_ids=[line1_id, line2_id],
                parameters={
                    "user": ghost_user,
                    "posting_time": p_time_str,
                    "posting_date": p_date_str,
                    "day_of_week": timestamp.strftime("%A"),
                    "amount": str(amt),
                },
                forensic_indicator="Non-business posting timestamp coupled with dormant/unauthorized service account credential",
            )
            records.append(record)

        return records
