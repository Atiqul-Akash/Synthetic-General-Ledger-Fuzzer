"""Zero-OOM streaming Parquet exporter appending table row-groups chunk by chunk."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Optional, Tuple
import pyarrow as pa
import pyarrow.parquet as pq

from gl_fuzzer.models.journal import JournalEntry
from gl_fuzzer.exporters.parquet_exporter import ParquetGLExporter
from gl_fuzzer.exporters.acdoca_exporter import SAPACDOCAExporter


class StreamingParquetExporter:
    """Incremental Parquet writer that flushes row-groups sequentially to disk without accumulating RAM."""

    def __init__(
        self,
        output_path: str | Path,
        schema: Optional[pa.Schema] = None,
        is_acdoca: bool = False,
        compression: str = "snappy",
    ):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.is_acdoca = is_acdoca
        self.compression = compression

        if schema is not None:
            self.schema = schema
        else:
            self.schema = SAPACDOCAExporter.ACDOCA_SCHEMA if is_acdoca else ParquetGLExporter.GL_SCHEMA

        self.writer: Optional[pq.ParquetWriter] = None
        self.total_entries_written = 0
        self.total_lines_written = 0

    def append_entries(self, entries: List[JournalEntry]) -> None:
        """Flattens a chunk of journal entries and writes an atomic row-group to disk."""
        if not entries:
            return

        rows = []
        for entry in entries:
            for idx, line in enumerate(entry.lines):
                if self.is_acdoca:
                    row = SAPACDOCAExporter.to_acdoca_row(entry, idx, line)
                else:
                    row = {
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
                        "created_by": entry.created_by or "SYSTEM",
                        "reference": entry.reference or "",
                        "header_text": entry.header_text or "",
                        "business_cycle": entry.business_cycle,
                        "line_id": line.line_id,
                        "line_number": line.line_number,
                        "account_code": line.account_code,
                        "account_name": line.account_name or "",
                        "debit_credit": line.debit_credit.value,
                        "amount": line.amount,
                        "currency": line.currency,
                        "posting_key": line.posting_key or ("40" if line.debit_credit == DebitCredit.DEBIT else "50"),
                        "cost_center": line.cost_center or "",
                        "profit_center": line.profit_center or "",
                        "vendor_id": line.vendor_id or "",
                        "customer_id": line.customer_id or "",
                        "trading_partner": line.trading_partner or "",
                        "line_text": line.line_text or "",
                        "tax_code": line.tax_code or "",
                        "is_anomaly": entry.is_anomaly,
                        "anomaly_ids": ",".join(entry.anomaly_ids) if entry.anomaly_ids else "",
                    }
                rows.append(row)

        table = pa.Table.from_pylist(rows, schema=self.schema)

        if self.writer is None:
            self.writer = pq.ParquetWriter(self.output_path, self.schema, compression=self.compression)

        self.writer.write_table(table)
        self.total_entries_written += len(entries)
        self.total_lines_written += len(rows)

    def close(self) -> Tuple[Path, str]:
        """Closes the Parquet writer and returns (path, sha256_hash)."""
        if self.writer is not None:
            self.writer.close()
            self.writer = None
        elif not self.output_path.exists():
            empty_table = pa.Table.from_pylist([], schema=self.schema)
            pq.write_table(empty_table, self.output_path, compression=self.compression)

        hasher = hashlib.sha256()
        with open(self.output_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)

        return self.output_path, hasher.hexdigest()

    def __enter__(self) -> StreamingParquetExporter:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
