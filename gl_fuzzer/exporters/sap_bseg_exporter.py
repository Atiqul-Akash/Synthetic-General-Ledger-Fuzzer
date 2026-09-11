"""SAP ECC / S/4HANA standard BKPF (Document Header) and BSEG (Document Line Item) exporter."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

from gl_fuzzer.models.journal import DebitCredit, JournalEntry


class SAPBSEGExporter:
    """Exports GL transactions formatted as native SAP BKPF (Header) and BSEG (Segment) tables."""

    BKPF_FIELDS = [
        "BUKRS", "BELNR", "GJAHR", "BLART", "BLDAT", "BUDAT",
        "MONAT", "CPUTM", "USNAM", "XBLNR", "BKTXT", "WAERS"
    ]

    BSEG_FIELDS = [
        "BUKRS", "BELNR", "GJAHR", "BUZEI", "BSCHL", "SHKZG",
        "HKONT", "WRBTR", "WAERS", "KOSTL", "PRCTR", "LIFNR",
        "KUNNR", "VBUND", "SGTXT"
    ]

    @classmethod
    def export(
        cls,
        entries: List[JournalEntry],
        output_dir: str | Path,
        prefix: str = "SAP",
    ) -> Dict[str, Tuple[Path, str]]:
        """Writes both BKPF.csv and BSEG.csv to the specified directory.
        
        Returns dictionary mapping table name to (file_path, sha256_hash).
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        bkpf_path = out_dir / f"{prefix}_BKPF.csv"
        bseg_path = out_dir / f"{prefix}_BSEG.csv"

        # Write BKPF Header
        with open(bkpf_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cls.BKPF_FIELDS)
            writer.writeheader()

            for entry in entries:
                bldat = entry.document_date.replace("-", "") if entry.document_date else "20260101"
                budat = entry.posting_date.replace("-", "") if entry.posting_date else "20260101"
                cputm = entry.entry_time.replace(":", "") if entry.entry_time else "090000"

                writer.writerow({
                    "BUKRS": entry.company_code,
                    "BELNR": entry.document_number,
                    "GJAHR": str(entry.fiscal_year),
                    "BLART": entry.document_type.value,
                    "BLDAT": bldat,
                    "BUDAT": budat,
                    "MONAT": f"{entry.fiscal_period:02d}",
                    "CPUTM": cputm,
                    "USNAM": (entry.created_by or "SYSTEM")[:12],
                    "XBLNR": (entry.reference or "")[:16],
                    "BKTXT": (entry.header_text or "")[:25],
                    "WAERS": entry.lines[0].currency if entry.lines and entry.lines[0].currency else "USD",
                })

        # Write BSEG Segment
        with open(bseg_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cls.BSEG_FIELDS)
            writer.writeheader()

            for entry in entries:
                for line in entry.lines:
                    # SAP German debit/credit: S = Soll (Debit), H = Haben (Credit)
                    shkzg = "S" if line.debit_credit == DebitCredit.DEBIT else "H"

                    writer.writerow({
                        "BUKRS": entry.company_code,
                        "BELNR": entry.document_number,
                        "GJAHR": str(entry.fiscal_year),
                        "BUZEI": f"{min(max(1, line.line_number), 999):03d}",
                        "BSCHL": line.posting_key or ("40" if line.debit_credit == DebitCredit.DEBIT else "50"),
                        "SHKZG": shkzg,
                        "HKONT": f"{line.account_code:0>10}",
                        "WRBTR": f"{line.amount:.2f}",
                        "WAERS": line.currency,
                        "KOSTL": line.cost_center or "",
                        "PRCTR": line.profit_center or "",
                        "LIFNR": line.vendor_id or "",
                        "KUNNR": line.customer_id or "",
                        "VBUND": line.trading_partner or "",
                        "SGTXT": (line.line_text or "")[:50],
                    })

        # Calculate hashes
        results = {}
        for name, p in [("BKPF", bkpf_path), ("BSEG", bseg_path)]:
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            results[name] = (p, hasher.hexdigest())

        return results
