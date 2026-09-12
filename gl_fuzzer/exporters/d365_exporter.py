"""Microsoft Dynamics 365 Finance OData V4 & $batch Exporter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from gl_fuzzer.models.journal import DebitCredit, JournalEntry


class D365Exporter:
    """Exports GL transactions as Microsoft Dynamics 365 Finance LedgerJournalTable/Trans entities."""

    @classmethod
    def export(
        cls,
        entries: List[JournalEntry],
        output_dir: str | Path,
        prefix: str = "D365",
    ) -> Dict[str, Tuple[Path, str]]:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        odata_json_path = out_dir / f"{prefix}_OData.json"
        batch_txt_path = out_dir / f"{prefix}_Batch.txt"

        # 1. Build D365 OData V4 entity structure
        tables = []
        for entry in entries:
            j_table = {
                "@odata.type": "#Microsoft.Dynamics.DataEntities.LedgerJournalTable",
                "JournalBatchNumber": f"JB-{entry.document_number}",
                "JournalName": "GEN_JRNL",
                "Description": entry.header_text or "General Journal",
                "DataAreaId": entry.company_code.lower() if len(entry.company_code) <= 4 else "usmf",
                "PostingLayer": "Current",
                "LedgerJournalTrans": [],
            }

            for line in entry.lines:
                cost_ctr = line.cost_center or "000"
                # Segmented financial dimension string: Account-Department-CostCenter
                display_val = f"{line.account_code}-001-{cost_ctr}-US"
                trans = {
                    "@odata.type": "#Microsoft.Dynamics.DataEntities.LedgerJournalTrans",
                    "LineNumber": float(line.line_number),
                    "AccountType": "Ledger",
                    "AccountDisplayValue": display_val,
                    "TransDate": f"{entry.posting_date}T00:00:00Z",
                    "AmountCurDebit": float(line.amount) if line.debit_credit == DebitCredit.DEBIT else 0.0,
                    "AmountCurCredit": float(line.amount) if line.debit_credit == DebitCredit.CREDIT else 0.0,
                    "CurrencyCode": line.currency,
                    "Text": line.line_text or line.account_name,
                    "DocumentDate": f"{entry.document_date}T00:00:00Z",
                    "Voucher": entry.document_number,
                }
                j_table["LedgerJournalTrans"].append(trans)

            tables.append(j_table)

        odata_json_str = json.dumps({"value": tables}, indent=2)
        with open(odata_json_path, "w", encoding="utf-8") as f:
            f.write(odata_json_str)

        json_hash = hashlib.sha256(odata_json_str.encode("utf-8")).hexdigest()

        # 2. Build OData $batch multipart request payload
        batch_boundary = "batch_d365_boundary_8f9c1b"
        changeset_boundary = "changeset_d365_sub_4a2d1e"

        batch_lines: List[str] = [
            f"--{batch_boundary}",
            f"Content-Type: multipart/mixed; boundary={changeset_boundary}",
            "",
        ]

        for i, table in enumerate(tables):
            batch_lines.extend([
                f"--{changeset_boundary}",
                "Content-Type: application/http",
                "Content-Transfer-Encoding: binary",
                f"Content-ID: {i+1}",
                "",
                "POST /data/LedgerJournalTables HTTP/1.1",
                "Content-Type: application/json;odata.metadata=minimal",
                "Accept: application/json",
                "",
                json.dumps(table),
                "",
            ])

        batch_lines.extend([
            f"--{changeset_boundary}--",
            f"--{batch_boundary}--",
            "",
        ])

        batch_txt_content = "\r\n".join(batch_lines)
        with open(batch_txt_path, "w", encoding="utf-8") as f:
            f.write(batch_txt_content)

        batch_hash = hashlib.sha256(batch_txt_content.encode("utf-8")).hexdigest()

        return {
            "D365_ODATA_JSON": (odata_json_path, json_hash),
            "D365_BATCH_TXT": (batch_txt_path, batch_hash),
        }
