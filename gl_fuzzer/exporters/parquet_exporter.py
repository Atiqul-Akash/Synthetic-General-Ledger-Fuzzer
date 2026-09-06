"""High-performance Parquet GL dataset exporter using PyArrow / Polars."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Tuple
import pyarrow as pa
import pyarrow.parquet as pq

from gl_fuzzer.models.journal import JournalEntry


class ParquetGLExporter:
    """Exports GL transactions to standardized, partitioned or flat Parquet files."""

    GL_SCHEMA = pa.schema([
        ("entry_id", pa.string()),
        ("batch_id", pa.string()),
        ("company_code", pa.string()),
        ("fiscal_year", pa.int32()),
        ("fiscal_period", pa.int32()),
        ("document_type", pa.string()),
        ("document_number", pa.string()),
        ("posting_date", pa.string()),
        ("document_date", pa.string()),
        ("entry_time", pa.string()),
        ("created_at", pa.string()),
        ("created_by", pa.string()),
        ("reference", pa.string()),
        ("header_text", pa.string()),
        ("business_cycle", pa.string()),
        ("line_id", pa.string()),
        ("line_number", pa.int32()),
        ("account_code", pa.string()),
        ("account_name", pa.string()),
        ("debit_credit", pa.string()),
        ("amount", pa.decimal128(18, 2)),
        ("currency", pa.string()),
        ("posting_key", pa.string()),
        ("cost_center", pa.string()),
        ("profit_center", pa.string()),
        ("vendor_id", pa.string()),
        ("customer_id", pa.string()),
        ("trading_partner", pa.string()),
        ("line_text", pa.string()),
        ("tax_code", pa.string()),
        ("is_anomaly", pa.bool_()),
        ("anomaly_ids", pa.string()),
    ])

    @classmethod
    def export(cls, entries: List[JournalEntry], output_path: str | Path) -> Tuple[Path, str]:
        """Flattens journal entries into tabular rows and writes a compressed Parquet file.
        
        Returns a tuple of (written_path, sha256_hash).
        """
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for entry in entries:
            for line in entry.lines:
                rows.append({
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
                    "reference": entry.reference,
                    "header_text": entry.header_text,
                    "business_cycle": entry.business_cycle,
                    "line_id": line.line_id,
                    "line_number": line.line_number,
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "debit_credit": line.debit_credit.value,
                    "amount": line.amount,
                    "currency": line.currency,
                    "posting_key": line.posting_key,
                    "cost_center": line.cost_center or "",
                    "profit_center": line.profit_center or "",
                    "vendor_id": line.vendor_id or "",
                    "customer_id": line.customer_id or "",
                    "trading_partner": line.trading_partner or "",
                    "line_text": line.line_text,
                    "tax_code": line.tax_code or "",
                    "is_anomaly": entry.is_anomaly,
                    "anomaly_ids": ",".join(entry.anomaly_ids) if entry.anomaly_ids else "",
                })

        table = pa.Table.from_pylist(rows, schema=cls.GL_SCHEMA)
        pq.write_table(table, out_path, compression="snappy")

        # Compute SHA-256
        hasher = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return out_path, hasher.hexdigest()
