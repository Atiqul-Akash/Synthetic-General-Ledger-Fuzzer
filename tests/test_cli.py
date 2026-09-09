"""Integration tests for gl_fuzzer CLI commands."""

from pathlib import Path
from typer.testing import CliRunner
from gl_fuzzer.cli import app

runner = CliRunner()


def test_cli_generate_and_verify(tmp_path: Path):
    out_dir = tmp_path / "cli_output"

    # Test generate
    gen_result = runner.invoke(
        app,
        [
            "generate",
            "--count", "100",
            "--anomaly-rate", "0.05",
            "--seed", "123",
            "--out-dir", str(out_dir),
            "--export-formats", "parquet,csv,sap",
        ],
    )
    assert gen_result.exit_code == 0
    assert "Invariant Verified" in gen_result.output

    parquet_file = out_dir / "gl_feed.parquet"
    manifest_file = out_dir / "ground_truth_manifest.json"
    assert parquet_file.exists()
    assert manifest_file.exists()

    # Test verify
    verify_result = runner.invoke(
        app,
        [
            "verify",
            "--dataset", str(parquet_file),
            "--manifest", str(manifest_file),
        ],
    )
    assert verify_result.exit_code == 0
    assert "PASS" in verify_result.output

    # Test audit-report
    audit_result = runner.invoke(
        app,
        [
            "audit-report",
            "--dataset", str(parquet_file),
            "--manifest", str(manifest_file),
        ],
    )
    assert audit_result.exit_code == 0
    assert "SOX 404 / Forensic Audit Test Results" in audit_result.output


def test_cli_benchmark():
    result = runner.invoke(app, ["benchmark", "--count", "500"])
    assert result.exit_code == 0
    assert "Benchmark Results" in result.output


def test_cli_generate_acdoca_streaming_multi_currency(tmp_path: Path):
    out_dir = tmp_path / "stream_cli_out"
    result = runner.invoke(
        app,
        [
            "generate",
            "--count", "150",
            "--stream-chunks", "50",
            "--acdoca",
            "--multi-currency",
            "--seasonality",
            "--out-dir", str(out_dir),
        ],
    )
    assert result.exit_code == 0
    assert "ACDOCA" in result.output
    assert (out_dir / "acdoca_feed.parquet").exists()
    assert (out_dir / "acdoca_feed.csv").exists()
    assert (out_dir / "ground_truth_manifest.json").exists()

