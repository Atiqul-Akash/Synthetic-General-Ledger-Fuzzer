"""Oracle NetSuite SuiteTalk REST & CSV Import Exporter."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from gl_fuzzer.models.journal import DebitCredit, JournalEntry


class NetSuiteExporter:
    """Exports GL transactions formatted for Oracle NetSuite (SuiteTalk REST and CSV Import)."""

    CSV_FIELDS = [
        "ExternalId", "TranDate", "PostingPeriod", "Subsidiary",
        "Currency", "Memo", "LineId", "Account", "Debit", "Credit",
        "Department", "Class", "Location", "Entity"
    ]

    @classmethod
    def export(
        cls,
        entries: List[JournalEntry],
        output_dir: str | Path,
        prefix: str = "NETSUITE",
    ) -> Dict[str, Tuple[Path, str]]:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        json_path = out_dir / f"{prefix}_SuiteTalk.json"
        csv_path = out_dir / f"{prefix}_Import.csv"

        # 1. Build SuiteTalk REST format
        records = []
        for entry in entries:
            tran_date = entry.posting_date
            # NetSuite tranDate standard format: YYYY-MM-DD
            record = {
                "externalId": f"NS-JE-{entry.document_number}",
                "tranDate": tran_date,
                "subsidiary": {"id": entry.company_code},
                "memo": entry.header_text or "General Journal Entry",
                "line": {
                    "items": [
                        {
                            "line": line.line_number,
                            "account": {"id": line.account_code, "refName": line.account_name},
                            "debit": float(line.amount) if line.debit_credit == DebitCredit.DEBIT else None,
                            "credit": float(line.amount) if line.debit_credit == DebitCredit.CREDIT else None,
                            "memo": line.line_text,
                            "department": {"id": line.cost_center or "DEP_10"},
                            "class": {"id": "CLS_CORE"},
                            "location": {"id": "LOC_HQ"},
                            "entity": {"id": line.vendor_id or line.customer_id} if (line.vendor_id or line.customer_id) else None,
                        }
                        for line in entry.lines
                    ]
                },
            }
            records.append(record)

        json_str = json.dumps({"records": records}, indent=2)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        json_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        # 2. Build NetSuite CSV Import Format
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cls.CSV_FIELDS)
            writer.writeheader()

            for entry in entries:
                # MM/DD/YYYY format for NetSuite CSV
                # MM/DD/YYYY format required for NetSuite CSV import
                try:
                    from datetime import datetime as _dt
                    formatted_date = _dt.strptime(
                        str(entry.posting_date)[:10], "%Y-%m-%d"
                    ).strftime("%m/%d/%Y")
                except (ValueError, TypeError):
                    # Last-resort: emit raw value; NetSuite will reject on import
                    formatted_date = str(entry.posting_date)

                for line in entry.lines:
                    writer.writerow({
                        "ExternalId": f"NS-JE-{entry.document_number}",
                        "TranDate": formatted_date,
                        "PostingPeriod": f"Period {entry.fiscal_period} {entry.fiscal_year}",
                        "Subsidiary": entry.company_code,
                        "Currency": line.currency,
                        "Memo": entry.header_text or line.line_text,
                        "LineId": line.line_number,
                        "Account": line.account_code,
                        "Debit": f"{line.amount:.2f}" if line.debit_credit == DebitCredit.DEBIT else "",
                        "Credit": f"{line.amount:.2f}" if line.debit_credit == DebitCredit.CREDIT else "",
                        "Department": line.cost_center or "DEP_10",
                        "Class": "CLS_CORE",
                        "Location": "LOC_HQ",
                        "Entity": line.vendor_id or line.customer_id or "",
                    })

        with open(csv_path, "rb") as f:
            csv_hash = hashlib.sha256(f.read()).hexdigest()

        return {
            "NETSUITE_SUITETALK_JSON": (json_path, json_hash),
            "NETSUITE_IMPORT_CSV": (csv_path, csv_hash),
        }
