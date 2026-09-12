"""Unit tests for Parquet, CSV, SAP BSEG, and Manifest exporters."""

from decimal import Decimal
from pathlib import Path
import json
import pyarrow.parquet as pq
import pytest

from gl_fuzzer.models.journal import Batch
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, GroundTruthManifest
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.exporters.parquet_exporter import ParquetGLExporter
from gl_fuzzer.exporters.csv_exporter import CSVGLExporter
from gl_fuzzer.exporters.sap_bseg_exporter import SAPBSEGExporter
from gl_fuzzer.exporters.manifest_exporter import ManifestExporter


@pytest.fixture
def sample_batch():
    engine = BaseSynthesisEngine(seed=42)
    return engine.generate_batch(target_entry_count=20)


def test_parquet_export(tmp_path: Path, sample_batch: Batch):
    p_path = tmp_path / "test_feed.parquet"
    out_path, sha256_hash = ParquetGLExporter.export(sample_batch.entries, p_path)

    assert out_path.exists()
    assert len(sha256_hash) == 64

    # Verify parquet readable
    table = pq.read_table(out_path)
    assert len(table) == sample_batch.total_line_count
    assert "entry_id" in table.column_names
    assert "amount" in table.column_names


def test_csv_export(tmp_path: Path, sample_batch: Batch):
    c_path = tmp_path / "test_feed.csv"
    out_path, sha256_hash = CSVGLExporter.export(sample_batch.entries, c_path)

    assert out_path.exists()
    assert len(sha256_hash) == 64

    with open(out_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # 1 header line + line items
    assert len(lines) == sample_batch.total_line_count + 1


def test_sap_bseg_export(tmp_path: Path, sample_batch: Batch):
    sap_dir = tmp_path / "sap"
    results = SAPBSEGExporter.export(sample_batch.entries, sap_dir, prefix="SAP_TEST")

    assert "BKPF" in results
    assert "BSEG" in results

    bkpf_path, bkpf_hash = results["BKPF"]
    bseg_path, bseg_hash = results["BSEG"]

    assert bkpf_path.exists()
    assert bseg_path.exists()
    assert len(bkpf_hash) == 64
    assert len(bseg_hash) == 64

    import csv
    with open(bseg_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert "DMBTR" in row
        assert "HWAER" in row
        assert "MWSKZ" in row


def test_manifest_export(tmp_path: Path):
    manifest = GroundTruthManifest(
        dataset_id="TEST_RUN_01",
        generated_at="2026-09-06T12:00:00Z",
        total_entries=10,
        total_lines=20,
        anomalies=[
            AnomalyRecord(
                anomaly_id="A1",
                anomaly_type=AnomalyType.SMURFING_SPLIT_APPROVAL,
                sox_control="SOX-404-P2P",
                audit_script="AUDIT-001",
                description="Test smurfing",
                forensic_indicator="Test signal",
            )
        ],
    )

    json_path = tmp_path / "manifest.json"
    p_path, j_hash = ManifestExporter.export_json(manifest, json_path)
    assert p_path.exists()
    assert len(j_hash) == 64

    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["dataset_id"] == "TEST_RUN_01"
    assert loaded["manifest_sha256"] == j_hash

    parquet_path = tmp_path / "manifest.parquet"
    pq_path, pq_hash = ManifestExporter.export_parquet(manifest, parquet_path)
    assert pq_path.exists()
    assert len(pq_hash) == 64
