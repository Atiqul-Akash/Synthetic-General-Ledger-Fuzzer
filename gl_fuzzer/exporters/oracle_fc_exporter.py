"""Oracle Financials Cloud (Fusion Applications) FBDI & REST Exporter."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from gl_fuzzer.models.journal import DebitCredit, JournalEntry


class OracleFCExporter:
    """Exports GL transactions formatted for Oracle Financials Cloud (FBDI CSV and REST API)."""

    FBDI_FIELDS = [
        "STATUS_CODE", "LEDGER_ID", "EFFECTIVE_DATE_OF_TRANSACTION",
        "JOURNAL_SOURCE", "JOURNAL_CATEGORY", "CURRENCY_CODE",
        "JOURNAL_ENTRY_CREATION_DATE", "ACTUAL_FLAG",
        "SEGMENT1", "SEGMENT2", "SEGMENT3", "SEGMENT4", "SEGMENT5", "SEGMENT6",
        "ENTERED_DR", "ENTERED_CR", "ACCOUNTED_DR", "ACCOUNTED_CR",
        "REFERENCE1", "REFERENCE4", "REFERENCE10"
    ]

    @classmethod
    def export(
        cls,
        entries: List[JournalEntry],
        output_dir: str | Path,
        prefix: str = "ORACLE_FC",
    ) -> Dict[str, Tuple[Path, str]]:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        fbdi_path = out_dir / f"{prefix}_FBDI.csv"
        rest_path = out_dir / f"{prefix}_REST.json"

        # 1. Build Oracle FBDI CSV Format (GlInterface table)
        with open(fbdi_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cls.FBDI_FIELDS)
            writer.writeheader()

            for entry in entries:
                # Oracle date format: YYYY/MM/DD
                try:
                    dt = datetime.fromisoformat(entry.posting_date)
                    eff_date = dt.strftime("%Y/%m/%d")
                except Exception:
                    eff_date = entry.posting_date.replace("-", "/")

                source = f"FUZZER_{entry.business_cycle}"
                category = "Manual" if entry.business_cycle == "R2R" else "Standard"

                for line in entry.lines:
                    # Oracle 6-segment Flexfield: Company-CostCenter-Account-SubAccount-Product-Intercompany
                    seg1 = entry.company_code
                    seg2 = line.cost_center or "000"
                    seg3 = line.account_code
                    seg4 = "0000"
                    seg5 = "000"
                    seg6 = line.trading_partner or "0000"

                    dr_amt = f"{line.amount:.2f}" if line.debit_credit == DebitCredit.DEBIT else ""
                    cr_amt = f"{line.amount:.2f}" if line.debit_credit == DebitCredit.CREDIT else ""
                    loc_amt = line.amount_local if line.amount_local is not None else line.amount
                    acct_dr = f"{loc_amt:.2f}" if line.debit_credit == DebitCredit.DEBIT else ""
                    acct_cr = f"{loc_amt:.2f}" if line.debit_credit == DebitCredit.CREDIT else ""

                    writer.writerow({
                        "STATUS_CODE": "NEW",
                        "LEDGER_ID": "300000001",
                        "EFFECTIVE_DATE_OF_TRANSACTION": eff_date,
                        "JOURNAL_SOURCE": source,
                        "JOURNAL_CATEGORY": category,
                        "CURRENCY_CODE": line.currency,
                        "JOURNAL_ENTRY_CREATION_DATE": eff_date,
                        "ACTUAL_FLAG": "A",
                        "SEGMENT1": seg1,
                        "SEGMENT2": seg2,
                        "SEGMENT3": seg3,
                        "SEGMENT4": seg4,
                        "SEGMENT5": seg5,
                        "SEGMENT6": seg6,
                        "ENTERED_DR": dr_amt,
                        "ENTERED_CR": cr_amt,
                        "ACCOUNTED_DR": acct_dr,
                        "ACCOUNTED_CR": acct_cr,
                        "REFERENCE1": entry.document_number,
                        "REFERENCE4": entry.header_text or "GL Batch",
                        "REFERENCE10": line.line_text or line.account_name,
                    })

        with open(fbdi_path, "rb") as f:
            fbdi_hash = hashlib.sha256(f.read()).hexdigest()

        # 2. Build Oracle REST Journal Import JSON
        batches = []
        for entry in entries:
            batches.append({
                "BatchName": f"BATCH_{entry.document_number}",
                "LedgerId": 300000001,
                "AccountingDate": entry.posting_date,
                "UserSourceName": f"GL_FUZZER_{entry.business_cycle}",
                "UserCategoryName": "Standard",
                "JournalLines": [
                    {
                        "LineNumber": line.line_number,
                        "Account": f"{entry.company_code}-{line.cost_center or '000'}-{line.account_code}-0000-000-0000",
                        "EnteredDebit": float(line.amount) if line.debit_credit == DebitCredit.DEBIT else None,
                        "EnteredCredit": float(line.amount) if line.debit_credit == DebitCredit.CREDIT else None,
                        "Currency": line.currency,
                        "Description": line.line_text or line.account_name,
                    }
                    for line in entry.lines
                ],
            })

        rest_payload = {
            "OperationName": "importAndPostJournalBatches",
            "InterfaceGroupIdentifier": f"GRP_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "Batches": batches,
        }
        rest_str = json.dumps(rest_payload, indent=2)
        with open(rest_path, "w", encoding="utf-8") as f:
            f.write(rest_str)

        rest_hash = hashlib.sha256(rest_str.encode("utf-8")).hexdigest()

        return {
            "ORACLE_FC_FBDI_CSV": (fbdi_path, fbdi_hash),
            "ORACLE_FC_REST_JSON": (rest_path, rest_hash),
        }
