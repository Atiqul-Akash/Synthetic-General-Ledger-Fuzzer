"""Circular Intercompany Round-Tripping Anomaly Mutator.

Simulates circular cash and volume fabrication across corporate subsidiaries:
Entity A -> Entity B -> Entity C -> Entity A
executed within the same financial close window to artificially inflate operating cash flows,
turnover volume, or short-term liquidity ratios.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import uuid

from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, SOXControlRef
from gl_fuzzer.anomalies.base_mutator import BaseAnomalyMutator, MutationContext


class CircularRoundTrippingMutator(BaseAnomalyMutator):
    """Injects circular multi-entity fund transfer loops (A -> B -> C -> A)."""

    anomaly_type = AnomalyType.CIRCULAR_INTERCOMPANY_ROUND_TRIP
    sox_control = SOXControlRef.INTERCOMPANY_ROUND_TRIP
    audit_script = "AUDIT-SCRIPT-IC-003: Directed graph cycle detection on intercompany trading partner flows within close period"
    risk_level = "CRITICAL"

    def __init__(self, entities: list[str] | None = None):
        self.entities = entities or ["1000", "2000", "3000"]

    def mutate(
        self,
        batch: Batch,
        context: MutationContext,
        injection_rate: float = 0.05,
    ) -> List[AnomalyRecord]:
        records: List[AnomalyRecord] = []
        if len(self.entities) < 3:
            return records

        num_cycles = max(1, int(len(batch.entries) * injection_rate / 6))

        for _ in range(num_cycles):
            anomaly_id = f"ANOM_ROUNDTRIP_{uuid.uuid4().hex[:8].upper()}"
            amount_raw = float(context.rng.uniform(100000.0, 2500000.0))
            amount = Decimal(f"{amount_raw:.2f}")

            # Financial close period (month end)
            close_date = context.calendar.random_month_end_date()
            base_time = context.calendar.normal_business_time()

            cycle_entries: List[JournalEntry] = []
            cycle_entry_ids: List[str] = []
            cycle_line_ids: List[str] = []

            # Define directed cycle: Entity 0 -> Entity 1 -> Entity 2 -> Entity 0
            entity_cycle = [self.entities[0], self.entities[1], self.entities[2], self.entities[0]]

            base_dt = datetime.combine(close_date, base_time)

            for hop_idx in range(len(entity_cycle) - 1):
                sender_entity = entity_cycle[hop_idx]
                receiver_entity = entity_cycle[hop_idx + 1]

                hop_dt = base_dt + timedelta(hours=int(hop_idx * 4))
                hop_date = hop_dt.date()
                p_date_str = hop_date.isoformat()
                p_time_str = hop_dt.time().strftime("%H:%M:%S")

                # Sender entity records: DR Intercompany Due From (12000), CR Cash (10100)
                sender_entry_id = f"DOC_IC_SEND_{uuid.uuid4().hex[:8].upper()}"
                s_l1 = f"{sender_entry_id}-001"
                s_l2 = f"{sender_entry_id}-002"
                cycle_entry_ids.append(sender_entry_id)
                cycle_line_ids.extend([s_l1, s_l2])

                sender_lines = [
                    LineItem(
                        line_id=s_l1,
                        entry_id=sender_entry_id,
                        line_number=1,
                        account_code="12000",
                        account_name="Intercompany Receivables",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amount,
                        posting_key="40",
                        trading_partner=receiver_entity,
                        line_text=f"IC cash loan transfer to Entity {receiver_entity}",
                    ),
                    LineItem(
                        line_id=s_l2,
                        entry_id=sender_entry_id,
                        line_number=2,
                        account_code="10100",
                        account_name="Operating Cash & Bank",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amount,
                        posting_key="50",
                        line_text=f"Wire transfer outbound to Entity {receiver_entity}",
                    ),
                ]
                sender_entry = JournalEntry(
                    entry_id=sender_entry_id,
                    batch_id=batch.batch_id,
                    company_code=sender_entity,
                    fiscal_year=hop_date.year,
                    fiscal_period=hop_date.month,
                    document_type=DocumentType.IC,
                    document_number=f"700{context.rng.integers(100000, 999999)}",
                    posting_date=p_date_str,
                    document_date=p_date_str,
                    entry_time=p_time_str,
                    created_at=f"{p_date_str}T{p_time_str}Z",
                    created_by="CORP_TREASURY_MGR",
                    reference=f"IC-WIRE-{sender_entity}-{receiver_entity}",
                    header_text=f"Treasury Pool Loan {sender_entity}->{receiver_entity}",
                    business_cycle="R2R",
                    lines=sender_lines,
                    is_anomaly=True,
                    anomaly_ids=[anomaly_id],
                )

                # Receiver entity records: DR Cash (10100), CR Intercompany Due To (23000)
                recv_entry_id = f"DOC_IC_RECV_{uuid.uuid4().hex[:8].upper()}"
                r_l1 = f"{recv_entry_id}-001"
                r_l2 = f"{recv_entry_id}-002"
                cycle_entry_ids.append(recv_entry_id)
                cycle_line_ids.extend([r_l1, r_l2])

                recv_lines = [
                    LineItem(
                        line_id=r_l1,
                        entry_id=recv_entry_id,
                        line_number=1,
                        account_code="10100",
                        account_name="Operating Cash & Bank",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amount,
                        posting_key="40",
                        line_text=f"Wire transfer receipt from Entity {sender_entity}",
                    ),
                    LineItem(
                        line_id=r_l2,
                        entry_id=recv_entry_id,
                        line_number=2,
                        account_code="23000",
                        account_name="Intercompany Payables",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amount,
                        posting_key="50",
                        trading_partner=sender_entity,
                        line_text=f"IC loan liability to Entity {sender_entity}",
                    ),
                ]
                recv_entry = JournalEntry(
                    entry_id=recv_entry_id,
                    batch_id=batch.batch_id,
                    company_code=receiver_entity,
                    fiscal_year=hop_date.year,
                    fiscal_period=hop_date.month,
                    document_type=DocumentType.IC,
                    document_number=f"710{context.rng.integers(100000, 999999)}",
                    posting_date=p_date_str,
                    document_date=p_date_str,
                    entry_time=p_time_str,
                    created_at=f"{p_date_str}T{p_time_str}Z",
                    created_by="CORP_TREASURY_MGR",
                    reference=f"IC-WIRE-{sender_entity}-{receiver_entity}",
                    header_text=f"Treasury Pool Deposit from {sender_entity}",
                    business_cycle="R2R",
                    lines=recv_lines,
                    is_anomaly=True,
                    anomaly_ids=[anomaly_id],
                )

                cycle_entries.extend([sender_entry, recv_entry])

            batch.entries.extend(cycle_entries)

            record = AnomalyRecord(
                anomaly_id=anomaly_id,
                anomaly_type=self.anomaly_type,
                sox_control=self.sox_control.value,
                audit_script=self.audit_script,
                risk_level=self.risk_level,
                description=f"Circular intercompany fund round-trip: {' -> '.join(entity_cycle)} totaling ${amount} within month-end close",
                affected_entry_ids=cycle_entry_ids,
                affected_line_ids=cycle_line_ids,
                parameters={
                    "cycle_path": entity_cycle,
                    "hop_count": len(entity_cycle) - 1,
                    "round_trip_amount": str(amount),
                    "close_window_date": close_date.isoformat(),
                },
                forensic_indicator="Directed cycle in intercompany trading topology returning to originator entity within financial close",
            )
            records.append(record)

        return records
