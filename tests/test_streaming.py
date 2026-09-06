"""Unit tests for Streaming Parquet Exporter and Chunked Synthesis Engine."""

from decimal import Decimal
from pathlib import Path
import pyarrow.parquet as pq
import pytest

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.exporters.streaming_parquet import StreamingParquetExporter
from gl_fuzzer.generators.streaming_engine import ChunkedSynthesisEngine


def _create_dummy_entry(entry_id: str, amount: Decimal = Decimal("100.00")) -> JournalEntry:
    d_line = LineItem(
        line_id=f"{entry_id}-1",
        entry_id=entry_id,
        line_number=1,
        account_code="10000",
        debit_credit=DebitCredit.DEBIT,
        amount=amount,
    )
    c_line = LineItem(
        line_id=f"{entry_id}-2",
        entry_id=entry_id,
        line_number=2,
        account_code="20000",
        debit_credit=DebitCredit.CREDIT,
        amount=amount,
    )
    return JournalEntry(
        entry_id=entry_id,
        batch_id="B_STREAM",
        document_number=entry_id,
        posting_date="2026-04-01",
        document_date="2026-04-01",
        created_at="2026-04-01T10:00:00Z",
        lines=[d_line, c_line],
    )


def test_streaming_parquet_exporter_gl(tmp_path):
    """Verify incremental writing of GL chunks to Parquet."""
    out_file = tmp_path / "streaming_gl.parquet"

    chunk1 = [_create_dummy_entry(f"E{i}") for i in range(1, 4)]
    chunk2 = [_create_dummy_entry(f"E{i}") for i in range(4, 7)]

    with StreamingParquetExporter(out_file, is_acdoca=False) as exporter:
        exporter.append_entries(chunk1)
        exporter.append_entries(chunk2)
        ret_path, file_hash = exporter.close()

    assert ret_path.exists()
    assert len(file_hash) == 64

    pq_file = pq.ParquetFile(out_file)
    assert pq_file.num_row_groups == 2
    assert pq_file.metadata.num_rows == 12  # 6 entries * 2 lines each


def test_streaming_parquet_exporter_acdoca(tmp_path):
    """Verify incremental writing of ACDOCA Universal Journal chunks."""
    out_file = tmp_path / "streaming_acdoca.parquet"

    chunk = [_create_dummy_entry("ACDOCA_E1")]

    with StreamingParquetExporter(out_file, is_acdoca=True) as exporter:
        exporter.append_entries(chunk)
        ret_path, file_hash = exporter.close()

    assert ret_path.exists()
    table = pq.read_table(out_file)
    assert table.num_rows == 2
    assert "WSL" in table.column_names
    assert "DOCLN" in table.column_names


def test_chunked_synthesis_engine_basic():
    """Verify chunked synthesis yields expected total entries across batches."""
    engine = ChunkedSynthesisEngine(seed=42)
    total_requested = 75
    chunk_size = 30

    chunks_collected = []
    total_entries_count = 0

    for entries, anoms in engine.stream_chunks(total_entries=total_requested, chunk_size=chunk_size, anomaly_rate=0.0):
        chunks_collected.append(entries)
        total_entries_count += len(entries)
        # Verify all generated entries in each chunk strictly balance
        for entry in entries:
            assert entry.is_balanced is True
            assert entry.balance_delta == Decimal("0.00")

    assert len(chunks_collected) == 3  # 30, 30, 15
    assert [len(c) for c in chunks_collected] == [30, 30, 15]
    assert total_entries_count == total_requested


def test_chunked_synthesis_engine_multi_currency_and_seasonality():
    """Verify multi-currency conversion maintains exact zero-sum balance in all valuations."""
    engine = ChunkedSynthesisEngine(
        seed=123,
        multi_currency=True,
        macro_seasonality=True,
    )

    all_entries = []
    for entries, _ in engine.stream_chunks(total_entries=50, chunk_size=25, anomaly_rate=0.0):
        all_entries.extend(entries)

    assert len(all_entries) == 50

    foreign_currencies_found = set()
    for entry in all_entries:
        # Check double-entry invariant across all 3 currencies
        assert entry.is_balanced is True
        assert entry.is_balanced_local is True
        assert entry.is_balanced_group is True

        for line in entry.lines:
            foreign_currencies_found.add(line.currency)
            assert line.amount_local is not None
            assert line.amount_group is not None
            assert line.exchange_rate_local > Decimal("0.00")
            assert line.exchange_rate_group > Decimal("0.00")

        # Check date is in 2026
        assert entry.posting_date.startswith("2026-")

    # Verify at least one foreign currency was synthesized (35% probability over 50 entries)
    assert len(foreign_currencies_found) > 1


def test_chunked_synthesis_engine_with_anomalies():
    """Verify anomaly injection within chunked synthesis."""
    engine = ChunkedSynthesisEngine(seed=42, multi_currency=True)
    all_anoms = []
    all_entries = []

    for entries, anoms in engine.stream_chunks(total_entries=100, chunk_size=50, anomaly_rate=0.10):
        all_entries.extend(entries)
        all_anoms.extend(anoms)

    assert len(all_anoms) > 0
    anomalous_entries = [e for e in all_entries if e.is_anomaly]
    assert len(anomalous_entries) > 0

    # Ensure all entries remain balanced even after perturbation and currency conversion
    for entry in all_entries:
        assert entry.is_balanced is True
        assert entry.is_balanced_local is True
        assert entry.is_balanced_group is True
