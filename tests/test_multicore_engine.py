"""Test suite for High-Performance MultiCoreSynthesisEngine."""

from pathlib import Path
import tempfile
import pyarrow.parquet as pq
import pytest

from gl_fuzzer.generators.parallel_engine import MultiCoreSynthesisEngine


def test_multicore_generation_in_memory():
    engine = MultiCoreSynthesisEngine(max_workers=2, base_seed=123)
    batch = engine.generate(target_entry_count=20)
    assert len(batch.entries) == 20
    assert batch.is_balanced
    assert batch.total_debits > 0
    # Verify entries are sorted chronologically
    for i in range(len(batch.entries) - 1):
        curr = (batch.entries[i].posting_date, getattr(batch.entries[i], "entry_time", "") or "")
        nxt = (batch.entries[i + 1].posting_date, getattr(batch.entries[i + 1], "entry_time", "") or "")
        assert curr <= nxt, f"Multicore order violation at {i}: {curr} > {nxt}"


def test_multicore_partitioned_parquet():
    engine = MultiCoreSynthesisEngine(max_workers=2, base_seed=456)
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        part_paths = engine.generate_to_parquet(target_entry_count=20, output_dir=out_dir)
        assert len(part_paths) == 2
        for p in part_paths:
            assert p.exists()
            table = pq.read_table(p)
            assert table.num_rows > 0
            assert "entry_id" in table.column_names
            assert "amount" in table.column_names


def test_multicore_benchmark():
    engine = MultiCoreSynthesisEngine(max_workers=2, base_seed=789)
    bench = engine.benchmark(entry_count=10)
    assert "single_core_eps" in bench
    assert "multi_core_eps" in bench
    assert bench["entry_count"] == 10
