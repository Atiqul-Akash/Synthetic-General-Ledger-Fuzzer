"""Smurfing / Split Approvals Anomaly Mutator.

Circumvents Delegation of Authority (DOA) dual-authorization limits (e.g. $10,000 threshold)
by splitting large payments or invoices into clusters of transactions between $9,500 and $9,999
to the same vendor within 48 hours.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import uuid

from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, SOXControlRef
from gl_fuzzer.anomalies.base_mutator import BaseAnomalyMutator, MutationContext


class SmurfingMutator(BaseAnomalyMutator):
    """Injects split transactions just below approval thresholds (DOA evasion)."""

    anomaly_type = AnomalyType.SMURFING_SPLIT_APPROVAL
    sox_control = SOXControlRef.P2P_DOA_LIMITS
    audit_script = "AUDIT-SCRIPT-P2P-004: Multi-invoice vendor clustering within 5% of approval threshold within 48hr window"
    risk_level = "CRITICAL"

    def __init__(self, threshold: Decimal = Decimal("10000.00"), cluster_size_range: tuple[int, int] = (3, 6)):
        self.threshold = threshold
        self.cluster_size_range = cluster_size_range

    def mutate(
        self,
        batch: Batch,
        context: MutationContext,
        injection_rate: float = 0.05,
    ) -> List[AnomalyRecord]:
        records: List[AnomalyRecord] = []
        base_len = getattr(context, "base_entry_count", 0) or len(batch.entries)
        num_clusters = max(1, int(base_len * injection_rate / 4))

        target_vendors = ["VEND_CORRUPT_701", "VEND_SHELL_992", "VEND_SPLIT_404"]

        for c_idx in range(num_clusters):
            anomaly_id = f"ANOM_SMURF_{uuid.uuid4().hex[:8].upper()}"
            cluster_size = int(context.rng.integers(self.cluster_size_range[0], self.cluster_size_range[1] + 1))
            vendor = str(context.rng.choice(target_vendors))
            company_code = batch.entries[0].company_code if batch.entries else "1000"

            base_date = context.calendar.random_business_date()
            base_time = context.calendar.normal_business_time()
            base_dt = datetime.combine(base_date, base_time)

            cluster_entry_ids = []
            cluster_line_ids = []
            amounts_injected = []

            for i in range(cluster_size):
                # Amount strictly in [$9,500.00, $9,999.00]
                raw_amt = float(context.rng.uniform(9500.0, 9999.0))
                amt = Decimal(f"{raw_amt:.2f}")
                amounts_injected.append(str(amt))

                # Perturb time within 48 hours
                offset_minutes = int(context.rng.integers(10, 48 * 60))
                item_dt = base_dt + timedelta(minutes=offset_minutes)
                p_date_str = item_dt.date().isoformat()
                p_time_str = item_dt.time().strftime("%H:%M:%S")

                entry_id = f"DOC_SMURF_{uuid.uuid4().hex[:8].upper()}"
                line1_id = f"{entry_id}-001"
                line2_id = f"{entry_id}-002"
                cluster_entry_ids.append(entry_id)
                cluster_line_ids.extend([line1_id, line2_id])

                lines = [
                    LineItem(
                        line_id=line1_id,
                        entry_id=entry_id,
                        line_number=1,
                        account_code="64000",
                        account_name="Legal & Professional Fees",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amt,
                        posting_key="40",
                        cost_center="CC_CORP",
                        line_text=f"Consulting invoice leg {i+1} for {vendor}",
                    ),
                    LineItem(
                        line_id=line2_id,
                        entry_id=entry_id,
                        line_number=2,
                        account_code="20000",
                        account_name="Accounts Payable - Trade",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amt,
                        posting_key="31",
                        vendor_id=vendor,
                        line_text=f"Split approval payable to {vendor}",
                    ),
                ]

                anom_entry = JournalEntry(
                    entry_id=entry_id,
                    batch_id=batch.batch_id,
                    company_code=company_code,
                    fiscal_year=item_dt.year,
                    fiscal_period=item_dt.month,
                    document_type=DocumentType.KR,
                    document_number=f"510{context.rng.integers(100000, 999999)}",
                    posting_date=p_date_str,
                    document_date=p_date_str,
                    entry_time=p_time_str,
                    created_at=f"{p_date_str}T{p_time_str}Z",
                    created_by="ROGUE_BUYER_03",
                    reference=f"SPLIT-{i+1:02d}-{vendor}",
                    header_text=f"Consulting Services - {vendor}",
                    business_cycle="P2P",
                    lines=lines,
                    is_anomaly=True,
                    anomaly_ids=[anomaly_id],
                )
                batch.entries.append(anom_entry)

            record = AnomalyRecord(
                anomaly_id=anomaly_id,
                anomaly_type=self.anomaly_type,
                sox_control=self.sox_control.value,
                audit_script=self.audit_script,
                risk_level=self.risk_level,
                description=f"Cluster of {cluster_size} invoices to {vendor} just below ${self.threshold} DOA threshold within 48h",
                affected_entry_ids=cluster_entry_ids,
                affected_line_ids=cluster_line_ids,
                parameters={
                    "doa_threshold": str(self.threshold),
                    "cluster_size": cluster_size,
                    "target_vendor": vendor,
                    "amounts": amounts_injected,
                    "time_span_hours": 48,
                },
                forensic_indicator="Dense temporal concentration of amounts in [$9,500, $9,999] targeting identical vendor ID",
            )
            records.append(record)

        return records
