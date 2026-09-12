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


def test_cli_agent_dialogue_json_and_eml(tmp_path: Path):
    eml_file = tmp_path / "agent_thread.eml"
    res_eml = runner.invoke(
        app,
        [
            "agent-dialogue",
            "--persona", "EXECUTIVE_CFO",
            "--format", "eml",
            "--out-file", str(eml_file),
        ],
    )
    assert res_eml.exit_code == 0
    assert eml_file.exists()
    assert "RFC-2822 Email Thread saved to:" in res_eml.output

    res_json = runner.invoke(
        app,
        [
            "agent-dialogue",
            "--persona", "COLLUSIVE_VENDOR",
            "--format", "json",
        ],
    )
    assert res_json.exit_code == 0
    assert "CAMP-VENDOR-BANK-DIVERSION" in res_json.output


def test_cli_legacy_export_and_fuzz(tmp_path: Path):
    edi_file = tmp_path / "invoice.edi"
    res_export = runner.invoke(
        app,
        [
            "legacy-export",
            "--protocol", "X12_810",
            "--count", "3",
            "--out-file", str(edi_file),
        ],
    )
    assert res_export.exit_code == 0
    assert edi_file.exists()
    assert "Successfully exported ANSI_X12_810" in res_export.output

    fuzz_file = tmp_path / "fuzzed.ach"
    res_fuzz = runner.invoke(
        app,
        [
            "legacy-fuzz",
            "--protocol", "NACHA_ACH",
            "--anomalies", "HASH_TOTAL_DESYNC,FIXED_WIDTH_OVERFLOW",
            "--out-file", str(fuzz_file),
        ],
    )
    assert res_fuzz.exit_code == 0
    assert fuzz_file.exists()
    assert "HASH_TOTAL_DESYNC" in res_fuzz.output


def test_cli_multicore_generate(tmp_path: Path):
    out_dir = tmp_path / "mc_out"
    res = runner.invoke(app, ["multicore-generate", "--count", "50", "--workers", "2", "--out-dir", str(out_dir)])
    assert res.exit_code == 0
    assert "Multi-Core Parallel Execution Summary" in res.output
    assert len(list(out_dir.glob("*.parquet"))) > 0


def test_cli_generative_ml(tmp_path: Path):
    out_dir = tmp_path / "ml_out"
    res = runner.invoke(app, ["generative-ml", "--count", "10", "--model", "copula", "--out-dir", str(out_dir)])
    assert res.exit_code == 0
    assert "Generative ML Output (COPULA)" in res.output


def test_cli_erp_export(tmp_path: Path):
    out_dir = tmp_path / "erp_out"
    res = runner.invoke(app, ["erp-export", "--erp", "workday", "--count", "5", "--out-dir", str(out_dir)])
    assert res.exit_code == 0
    assert "WORKDAY_SOAP_XML" in res.output


def test_cli_dlt_verify(tmp_path: Path):
    out_dir = tmp_path / "dlt_out"
    res = runner.invoke(app, ["dlt-verify", "--count", "10", "--out-dir", str(out_dir)])
    assert res.exit_code == 0
    assert "Cryptographic Triple-Entry Ledger Report" in res.output
    assert (out_dir / "sample_triple_entry_receipt.json").exists()
