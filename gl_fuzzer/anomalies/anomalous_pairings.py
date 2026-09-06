"""Anomalous Account Pairings Mutator.

Injects topological graph violations into the general ledger where debit/credit legs
combine accounts that should never directly interact in legitimate enterprise accounting flows:
1. Direct DR Cash offset by CR Operating Expense (bypassing Revenue and Accounts Receivable)
2. Suspense Account Parking (debiting/crediting 99999 to obscure improper journal entries)
3. Direct DR Expense offset by CR Property, Plant & Equipment (bypassing CapEx disposal workflows)
"""

from __future__ import annotations

from decimal import Decimal
from typing import List
import uuid

from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, SOXControlRef
from gl_fuzzer.anomalies.base_mutator import BaseAnomalyMutator, MutationContext


class AnomalousPairingsMutator(BaseAnomalyMutator):
    """Injects illegal or rare debit/credit account pairings while maintaining balance."""

    anomaly_type = AnomalyType.ANOMALOUS_ACCOUNT_PAIRING
    sox_control = SOXControlRef.GL_SUSPENSE_CONSISTENCY
    audit_script = "AUDIT-SCRIPT-GL-008: Bipartite graph connection testing between Asset/Expense and prohibited contra accounts"
    risk_level = "CRITICAL"

    PAIRING_SCENARIOS = [
        {
            "name": "CASH_DIRECT_EXPENSE_BYPASS",
            "debit_acc": "10100",
            "debit_name": "Operating Cash & Bank",
            "credit_acc": "69000",
            "credit_name": "Miscellaneous Operating Expense",
            "desc": "Direct Debit to Cash offset by Credit to Operating Expense (bypassing Revenue/AR)",
            "indicator": "Cash debited against expense account rather than customer receivable or revenue",
        },
        {
            "name": "SUSPENSE_ACCOUNT_PARKING",
            "debit_acc": "99999",
            "debit_name": "Suspense / Unassigned Account",
            "credit_acc": "10100",
            "credit_name": "Operating Cash & Bank",
            "desc": "Disbursement parked in unassigned Suspense account avoiding vendor matching",
            "indicator": "Cash outflow offset directly against suspense clearing account",
        },
        {
            "name": "EXPENSE_FIXED_ASSET_IMPAIRMENT_BYPASS",
            "debit_acc": "64000",
            "debit_name": "Legal & Professional Fees",
            "credit_acc": "17000",
            "credit_name": "Property, Plant & Equipment",
            "desc": "Direct debit to Legal Expense offset by credit to Capital Fixed Assets",
            "indicator": "Fixed asset reduction without formal disposal or depreciation document",
        },
    ]

    def mutate(
        self,
        batch: Batch,
        context: MutationContext,
        injection_rate: float = 0.05,
    ) -> List[AnomalyRecord]:
        records: List[AnomalyRecord] = []
        num_pairings = max(1, int(len(batch.entries) * injection_rate))
        company_code = batch.entries[0].company_code if batch.entries else "1000"

        for _ in range(num_pairings):
            anomaly_id = f"ANOM_PAIRING_{uuid.uuid4().hex[:8].upper()}"
            scenario = context.rng.choice(self.PAIRING_SCENARIOS)

            raw_amt = float(context.rng.uniform(5000.0, 150000.0))
            amt = Decimal(f"{raw_amt:.2f}")

            p_date = context.calendar.random_business_date()
            p_time = context.calendar.normal_business_time()
            p_date_str = p_date.isoformat()
            p_time_str = p_time.strftime("%H:%M:%S")

            entry_id = f"DOC_PAIR_{uuid.uuid4().hex[:8].upper()}"
            line1_id = f"{entry_id}-001"
            line2_id = f"{entry_id}-002"

            lines = [
                LineItem(
                    line_id=line1_id,
                    entry_id=entry_id,
                    line_number=1,
                    account_code=scenario["debit_acc"],
                    account_name=scenario["debit_name"],
                    debit_credit=DebitCredit.DEBIT,
                    amount=amt,
                    posting_key="40",
                    line_text=f"Anomalous debit leg: {scenario['name']}",
                ),
                LineItem(
                    line_id=line2_id,
                    entry_id=entry_id,
                    line_number=2,
                    account_code=scenario["credit_acc"],
                    account_name=scenario["credit_name"],
                    debit_credit=DebitCredit.CREDIT,
                    amount=amt,
                    posting_key="50",
                    line_text=f"Anomalous credit leg: {scenario['name']}",
                ),
            ]

            entry = JournalEntry(
                entry_id=entry_id,
                batch_id=batch.batch_id,
                company_code=company_code,
                fiscal_year=p_date.year,
                fiscal_period=p_date.month,
                document_type=DocumentType.MJE,
                document_number=f"180{context.rng.integers(100000, 999999)}",
                posting_date=p_date_str,
                document_date=p_date_str,
                entry_time=p_time_str,
                created_at=f"{p_date_str}T{p_time_str}Z",
                created_by="CONTROLLER_MANUAL_MJE",
                reference="GL-ADJ-PAIRING",
                header_text=f"Irregular Account Pairing: {scenario['name']}",
                business_cycle="R2R",
                lines=lines,
                is_anomaly=True,
                anomaly_ids=[anomaly_id],
            )
            batch.entries.append(entry)

            record = AnomalyRecord(
                anomaly_id=anomaly_id,
                anomaly_type=self.anomaly_type,
                sox_control=self.sox_control.value,
                audit_script=self.audit_script,
                risk_level=self.risk_level,
                description=f"Illegal pairing scenario {scenario['name']}: {scenario['desc']}",
                affected_entry_ids=[entry_id],
                affected_line_ids=[line1_id, line2_id],
                parameters={
                    "scenario": scenario["name"],
                    "debit_account": scenario["debit_acc"],
                    "credit_account": scenario["credit_acc"],
                    "amount": str(amt),
                },
                forensic_indicator=scenario["indicator"],
            )
            records.append(record)

        return records
