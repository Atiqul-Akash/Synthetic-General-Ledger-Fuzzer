"""High-Performance Multi-Core Parallel Synthesis Engine."""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
from decimal import Decimal
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

import pyarrow as pa
import pyarrow.parquet as pq

from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.models.journal import Batch, JournalEntry, LineItem


def _worker_generate_chunk(
    worker_id: int,
    chunk_count: int,
    worker_seed: int,
    company_code: Optional[str] = None,
) -> List[JournalEntry]:
    """Top-level module function safe for Windows spawn process start."""
    engine = BaseSynthesisEngine(seed=worker_seed)
    batch_id = f"WORKER_{worker_id}_{uuid.uuid4().hex[:6]}"
    batch = engine.generate_batch(
        batch_id=batch_id,
        target_entry_count=chunk_count,
        company_code=company_code,
    )
    return batch.entries


def _worker_write_parquet_partition(
    worker_id: int,
    chunk_count: int,
    worker_seed: int,
    partition_path_str: str,
    company_code: Optional[str] = None,
) -> str:
    """Worker function that synthesizes and writes Parquet directly to disk (zero-copy IPC)."""
    entries = _worker_generate_chunk(worker_id, chunk_count, worker_seed, company_code)

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
                "reference": entry.reference or "",
                "business_cycle": entry.business_cycle,
                "line_id": line.line_id,
                "line_number": line.line_number,
                "account_code": line.account_code,
                "account_name": line.account_name,
                "debit_credit": line.debit_credit.value,
                "amount": float(line.amount),
                "posting_key": line.posting_key or "",
                "tax_code": line.tax_code or "",
                "clearing_doc": line.clearing_doc or "",
                "currency": line.currency,
                "amount_local": float(line.amount_local) if line.amount_local is not None else float(line.amount),
                "currency_local": line.currency_local,
                "amount_group": float(line.amount_group) if line.amount_group is not None else float(line.amount),
                "currency_group": line.currency_group,
                "cost_center": line.cost_center or "",
                "vendor_id": line.vendor_id or "",
                "customer_id": line.customer_id or "",
                "is_anomaly": entry.is_anomaly,
            })

    if rows:
        table = pa.Table.from_pylist(rows)
    else:
        # Empty schema table
        schema = pa.schema([
            ("entry_id", pa.string()),
            ("batch_id", pa.string()),
            ("company_code", pa.string()),
            ("fiscal_year", pa.int64()),
            ("fiscal_period", pa.int64()),
            ("document_type", pa.string()),
            ("document_number", pa.string()),
            ("posting_date", pa.string()),
            ("document_date", pa.string()),
            ("reference", pa.string()),
            ("business_cycle", pa.string()),
            ("line_id", pa.string()),
            ("line_number", pa.int64()),
            ("account_code", pa.string()),
            ("account_name", pa.string()),
            ("debit_credit", pa.string()),
            ("amount", pa.float64()),
            ("posting_key", pa.string()),
            ("tax_code", pa.string()),
            ("clearing_doc", pa.string()),
            ("currency", pa.string()),
            ("amount_local", pa.float64()),
            ("currency_local", pa.string()),
            ("amount_group", pa.float64()),
            ("currency_group", pa.string()),
            ("cost_center", pa.string()),
            ("vendor_id", pa.string()),
            ("customer_id", pa.string()),
            ("is_anomaly", pa.bool_()),
        ])
        table = pa.Table.from_batches([], schema=schema)

    pq.write_table(table, partition_path_str, compression="SNAPPY")
    return partition_path_str


class MultiCoreSynthesisEngine:
    """Enterprise high-performance multi-threaded and multi-process synthesis engine."""

    def __init__(
        self,
        max_workers: Optional[int] = None,
        base_seed: int = 42,
    ):
        detected_cpus = os.cpu_count() or 4
        self.max_workers = max_workers if max_workers is not None and max_workers > 0 else detected_cpus
        self.base_seed = base_seed

    def generate(
        self,
        target_entry_count: int = 1000,
        company_code: Optional[str] = None,
    ) -> Batch:
        """Generates entries in parallel across all CPU cores, merging into a single Batch."""
        if target_entry_count <= 0:
            now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return Batch(batch_id=f"MC_BATCH_{uuid.uuid4().hex[:8]}", created_at=now_utc, entries=[])

        workers = min(self.max_workers, target_entry_count)
        chunk_size = math.ceil(target_entry_count / workers)

        chunks: List[int] = []
        remaining = target_entry_count
        for _ in range(workers):
            count = min(chunk_size, remaining)
            if count > 0:
                chunks.append(count)
                remaining -= count

        all_entries: List[JournalEntry] = []

        with concurrent.futures.ProcessPoolExecutor(max_workers=len(chunks)) as executor:
            futures = []
            for i, chunk_cnt in enumerate(chunks):
                worker_seed = self.base_seed + i * 1_000_000
                fut = executor.submit(
                    _worker_generate_chunk,
                    worker_id=i,
                    chunk_count=chunk_cnt,
                    worker_seed=worker_seed,
                    company_code=company_code,
                )
                futures.append(fut)

            for fut in futures:
                entries = fut.result()
                all_entries.extend(entries)

        # Sort merged worker chunks chronologically
        all_entries.sort(key=lambda e: (e.posting_date, getattr(e, "entry_time", "00:00:00") or "00:00:00"))

        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        batch_id = f"MC_BATCH_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        for entry in all_entries:
            entry.batch_id = batch_id

        return Batch(
            batch_id=batch_id,
            created_at=now_utc,
            entries=all_entries,
        )

    def generate_to_parquet(
        self,
        target_entry_count: int,
        output_dir: Path,
        filename_prefix: str = "partition",
        company_code: Optional[str] = None,
    ) -> List[Path]:
        """Generates partitioned Parquet files directly across workers."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        workers = min(self.max_workers, max(1, target_entry_count))
        chunk_size = math.ceil(target_entry_count / workers)

        chunks: List[int] = []
        remaining = target_entry_count
        for _ in range(workers):
            count = min(chunk_size, remaining)
            if count > 0:
                chunks.append(count)
                remaining -= count

        partition_paths: List[Path] = []

        with concurrent.futures.ProcessPoolExecutor(max_workers=len(chunks)) as executor:
            futures = []
            for i, chunk_cnt in enumerate(chunks):
                worker_seed = self.base_seed + i * 1_000_000
                part_file = output_dir / f"{filename_prefix}_{i:03d}.parquet"
                fut = executor.submit(
                    _worker_write_parquet_partition,
                    worker_id=i,
                    chunk_count=chunk_cnt,
                    worker_seed=worker_seed,
                    partition_path_str=str(part_file),
                    company_code=company_code,
                )
                futures.append((fut, part_file))

            for fut, part_path in futures:
                fut.result()
                partition_paths.append(part_path)

        return partition_paths

    def benchmark(self, entry_count: int = 2000) -> Dict[str, Any]:
        """Runs single-core vs multi-core benchmark to evaluate scaling speedup."""
        # 1. Single core baseline
        t0 = time.perf_counter()
        engine_1 = BaseSynthesisEngine(seed=self.base_seed)
        _ = engine_1.generate_batch(target_entry_count=entry_count)
        single_core_time = max(0.001, time.perf_counter() - t0)
        single_eps = entry_count / single_core_time

        # 2. Multi-core run
        t1 = time.perf_counter()
        _ = self.generate(target_entry_count=entry_count)
        multi_core_time = max(0.001, time.perf_counter() - t1)
        multi_eps = entry_count / multi_core_time

        speedup = multi_eps / single_eps if single_eps > 0 else 1.0

        return {
            "entry_count": entry_count,
            "workers": self.max_workers,
            "single_core_seconds": round(single_core_time, 3),
            "single_core_eps": round(single_eps, 1),
            "multi_core_seconds": round(multi_core_time, 3),
            "multi_core_eps": round(multi_eps, 1),
            "speedup_factor": round(speedup, 2),
        }
