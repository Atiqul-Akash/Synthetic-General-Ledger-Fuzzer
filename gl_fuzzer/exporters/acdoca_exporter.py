"""SAP S/4HANA Universal Journal (ACDOCA) 50+ column enterprise GL dataset exporter."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import List, Tuple
import pyarrow as pa
import pyarrow.parquet as pq

from gl_fuzzer.models.journal import DebitCredit, JournalEntry


class SAPACDOCAExporter:
    """Exports GL transactions to SAP S/4HANA Universal Journal (ACDOCA) specification."""

    ACDOCA_SCHEMA = pa.schema([
        ("RCLNT", pa.string()),            # Client (e.g. 100)
        ("RLDNR", pa.string()),            # Ledger in General Ledger (0L=Leading)
        ("RBUKRS", pa.string()),           # Company Code
        ("GJAHR", pa.int32()),             # Fiscal Year
        ("BELNR", pa.string()),            # Accounting Document Number
        ("DOCLN", pa.string()),            # 6-digit Line Item Number (e.g. 000001)
        ("BLART", pa.string()),            # Document Type (SA, KR, WE, etc.)
        ("BLDAT", pa.string()),            # Document Date YYYYMMDD
        ("BUDAT", pa.string()),            # Posting Date YYYYMMDD
        ("POPER", pa.string()),            # Posting Period (001-016)
        ("CPUDT", pa.string()),            # Day on which Accounting Document Entered
        ("CPUTM", pa.string()),            # Time of Entry HHMMSS
        ("USNAM", pa.string()),            # User Name
        ("XBLNR", pa.string()),            # Reference Document Number
        ("BKTXT", pa.string()),            # Document Header Text
        ("BSCHL", pa.string()),            # Posting Key (40=Debit, 50=Credit, etc.)
        ("DRCRK", pa.string()),            # Debit/Credit Indicator (S=Debit, H=Credit)
        ("RACCT", pa.string()),            # General Ledger Account
        ("TXT50", pa.string()),            # GL Account Long Description
        ("SGTXT", pa.string()),            # Line Item Text
        ("RWCUR", pa.string()),            # Document Currency
        ("WSL", pa.decimal128(18, 2)),     # Amount in Document Currency
        ("RHCUR", pa.string()),            # Company Code Local Currency
        ("HSL", pa.decimal128(18, 2)),     # Amount in Local Currency
        ("RKCUR", pa.string()),            # Group Reporting Currency
        ("KSL", pa.decimal128(18, 2)),     # Amount in Group Currency
        ("RCNTR", pa.string()),            # Cost Center
        ("PRCTR", pa.string()),            # Profit Center
        ("SEGMENT", pa.string()),          # Segment for Segment Reporting
        ("FKBER", pa.string()),            # Functional Area
        ("PS_POSID", pa.string()),         # WBS Element
        ("ANLN1", pa.string()),            # Main Asset Number
        ("ANLN2", pa.string()),            # Asset Subnumber
        ("MATNR", pa.string()),            # Material Number
        ("WERKS", pa.string()),            # Plant
        ("LIFNR", pa.string()),            # Vendor Account Number
        ("KUNNR", pa.string()),            # Customer Account Number
        ("VBUND", pa.string()),            # Trading Partner Company Code
        ("MWSKZ", pa.string()),            # Sales/Purchases Tax Code
        ("TXJCD", pa.string()),            # Tax Jurisdiction
        ("AUGBL", pa.string()),            # Clearing Document Number
        ("BUSINESS_CYCLE", pa.string()),   # Accounting Cycle Tag (P2P, O2C, R2R)
        ("IS_ANOMALY", pa.bool_()),        # Anomaly Ground-Truth Flag
        ("ANOMALY_IDS", pa.string()),      # Injected Anomaly Identifiers
    ])

    @classmethod
    def to_acdoca_row(cls, entry: JournalEntry, line_idx: int, line) -> dict:
        """Converts a JournalEntry line item to an SAP S/4HANA ACDOCA record."""
        bldat = entry.document_date.replace("-", "") if entry.document_date else "20260101"
        budat = entry.posting_date.replace("-", "") if entry.posting_date else "20260101"
        cputm = entry.entry_time.replace(":", "") if entry.entry_time else "093000"
        poper = f"{entry.fiscal_period:03d}"
        docln = f"{line.line_number:06d}"
        drcrk = "S" if line.debit_credit == DebitCredit.DEBIT else "H"

        # Derived organizational units
        prctr = line.profit_center or f"PC_{entry.company_code}"
        rcntr = line.cost_center or ("CC_CORP" if line.account_code.startswith("6") else "")
        segment = line.segment or "SEG_COMMERCIAL"
        fkber = line.functional_area or ("FA_ADMIN" if line.account_code.startswith("6") else "FA_OPS")

        return {
            "RCLNT": "100",
            "RLDNR": line.ledger_group or "0L",
            "RBUKRS": entry.company_code,
            "GJAHR": entry.fiscal_year,
            "BELNR": entry.document_number,
            "DOCLN": docln,
            "BLART": entry.document_type.value,
            "BLDAT": bldat,
            "BUDAT": budat,
            "POPER": poper,
            "CPUDT": budat,
            "CPUTM": cputm,
            "USNAM": (entry.created_by or "SYSTEM")[:12],
            "XBLNR": (entry.reference or "")[:16],
            "BKTXT": (entry.header_text or "")[:25],
            "BSCHL": line.posting_key,
            "DRCRK": drcrk,
            "RACCT": line.account_code,
            "TXT50": line.account_name[:50] if line.account_name else "",
            "SGTXT": (line.line_text or "")[:50],
            "RWCUR": line.currency,
            "WSL": line.amount,
            "RHCUR": line.currency_local,
            "HSL": line.amount_local if line.amount_local is not None else line.amount,
            "RKCUR": line.currency_group,
            "KSL": line.amount_group if line.amount_group is not None else line.amount,
            "RCNTR": rcntr,
            "PRCTR": prctr,
            "SEGMENT": segment,
            "FKBER": fkber,
            "PS_POSID": line.wbs_element or "",
            "ANLN1": line.asset_number or "",
            "ANLN2": line.asset_subnumber or "",
            "MATNR": line.material_number or "",
            "WERKS": line.plant or "",
            "LIFNR": line.vendor_id or "",
            "KUNNR": line.customer_id or "",
            "VBUND": line.trading_partner or "",
            "MWSKZ": line.tax_code or "",
            "TXJCD": line.tax_jurisdiction or "",
            "AUGBL": line.clearing_doc or "",
            "BUSINESS_CYCLE": entry.business_cycle,
            "IS_ANOMALY": entry.is_anomaly,
            "ANOMALY_IDS": ",".join(entry.anomaly_ids) if entry.anomaly_ids else "",
        }

    @classmethod
    def export_parquet(cls, entries: List[JournalEntry], output_path: str | Path) -> Tuple[Path, str]:
        """Exports entries to an SAP S/4HANA ACDOCA Snappy-compressed Parquet table."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for entry in entries:
            for idx, line in enumerate(entry.lines):
                rows.append(cls.to_acdoca_row(entry, idx, line))

        table = pa.Table.from_pylist(rows, schema=cls.ACDOCA_SCHEMA)
        pq.write_table(table, out_path, compression="snappy")

        hasher = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return out_path, hasher.hexdigest()

    @classmethod
    def export_csv(cls, entries: List[JournalEntry], output_path: str | Path) -> Tuple[Path, str]:
        """Exports entries to standard CSV in SAP ACDOCA schema."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [field.name for field in cls.ACDOCA_SCHEMA]
        hasher = hashlib.sha256()

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in entries:
                for idx, line in enumerate(entry.lines):
                    row = cls.to_acdoca_row(entry, idx, line)
                    # Convert Decimals to string for CSV
                    row["WSL"] = f"{row['WSL']:.2f}"
                    row["HSL"] = f"{row['HSL']:.2f}"
                    row["KSL"] = f"{row['KSL']:.2f}"
                    writer.writerow(row)

        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return out_path, hasher.hexdigest()
