"""Standard RFC-4180 CSV general ledger feed exporter."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import List, Tuple

from gl_fuzzer.models.journal import JournalEntry


class CSVGLExporter:
    """Exports GL transactions to standardized CSV files."""

    CSV_HEADERS = [
        "entry_id", "batch_id", "company_code", "fiscal_year", "fiscal_period",
        "document_type", "document_number", "posting_date", "document_date",
        "entry_time", "created_at", "created_by", "reference", "header_text",
        "business_cycle", "line_id", "line_number", "account_code", "account_name",
        "debit_credit", "amount", "currency", "amount_local", "currency_local",
        "amount_group", "currency_group", "posting_key", "cost_center",
        "profit_center", "segment", "vendor_id", "customer_id", "trading_partner",
        "clearing_doc", "line_text", "tax_code", "is_anomaly", "anomaly_ids",
    ]

    @classmethod
    def export(cls, entries: List[JournalEntry], output_path: str | Path) -> Tuple[Path, str]:
        """Writes journal entries to standard CSV with SHA-256 verification digest."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cls.CSV_HEADERS)
            writer.writeheader()

            for entry in entries:
                for line in entry.lines:
                    writer.writerow({
                        "entry_id": entry.entry_id,
                        "batch_id": entry.batch_id,
                        "company_code": entry.company_code,
                        "fiscal_year": entry.fiscal_year,
                        "fiscal_period": entry.fiscal_period,
                        "document_type": entry.document_type.value,
                        "document_number": entry.document_number,
                        "posting_date": entry.posting_date,
                        "document_date": entry.document_date,
                        "entry_time": entry.entry_time,
                        "created_at": entry.created_at,
                        "created_by": entry.created_by,
                        "reference": entry.reference or "",
                        "header_text": entry.header_text or "",
                        "business_cycle": entry.business_cycle,
                        "line_id": line.line_id,
                        "line_number": line.line_number,
                        "account_code": line.account_code,
                        "account_name": line.account_name,
                        "debit_credit": line.debit_credit.value,
                        "amount": f"{line.amount:.2f}",
                        "currency": line.currency,
                        "amount_local": f"{line.amount_local:.2f}" if line.amount_local is not None else f"{line.amount:.2f}",
                        "currency_local": line.currency_local or line.currency,
                        "amount_group": f"{line.amount_group:.2f}" if line.amount_group is not None else f"{line.amount:.2f}",
                        "currency_group": line.currency_group or line.currency,
                        "posting_key": line.posting_key or "",
                        "cost_center": line.cost_center or "",
                        "profit_center": line.profit_center or "",
                        "segment": line.segment or "",
                        "vendor_id": line.vendor_id or "",
                        "customer_id": line.customer_id or "",
                        "trading_partner": line.trading_partner or "",
                        "clearing_doc": line.clearing_doc or "",
                        "line_text": line.line_text or "",
                        "tax_code": line.tax_code or "",
                        "is_anomaly": entry.is_anomaly,
                        "anomaly_ids": ",".join(entry.anomaly_ids) if entry.anomaly_ids else "",
                    })

        hasher = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return out_path, hasher.hexdigest()
