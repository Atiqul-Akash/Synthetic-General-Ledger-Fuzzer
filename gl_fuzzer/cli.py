"""Enterprise GL Fuzzer CLI powered by Typer and Rich."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import time
from typing import Optional
import pyarrow.parquet as pq
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import GroundTruthManifest
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.anomalies.pipeline import AnomalyPipeline
from gl_fuzzer.verification.invariants import InvariantVerifier
from gl_fuzzer.verification.audit_metrics import ForensicAuditEvaluator
from gl_fuzzer.exporters.parquet_exporter import ParquetGLExporter
from gl_fuzzer.exporters.csv_exporter import CSVGLExporter
from gl_fuzzer.exporters.sap_bseg_exporter import SAPBSEGExporter
from gl_fuzzer.exporters.manifest_exporter import ManifestExporter
from gl_fuzzer.exporters.acdoca_exporter import SAPACDOCAExporter
from gl_fuzzer.exporters.streaming_parquet import StreamingParquetExporter
from gl_fuzzer.generators.streaming_engine import ChunkedSynthesisEngine

app = typer.Typer(help="Synthetic General Ledger Fuzzer & Calibrated Anomaly Engine | Made with <3 by Atiqul-Akash (GitHub: Atiqul-Akash)")
console = Console()


@app.command()
def generate(
    count: int = typer.Option(1000, "--count", "-n", help="Target number of baseline journal entries to synthesize"),
    anomaly_rate: float = typer.Option(0.05, "--anomaly-rate", "-r", help="Target anomaly injection rate (0.0 to 1.0)"),
    seed: Optional[int] = typer.Option(42, "--seed", "-s", help="Random seed for reproducible generation"),
    out_dir: Path = typer.Option(Path("./output"), "--out-dir", "-o", help="Directory for exported artifacts"),
    export_formats: str = typer.Option("parquet,csv,sap", "--export-formats", "-f", help="Comma-separated formats: parquet,csv,sap,acdoca"),
    acdoca: bool = typer.Option(False, "--acdoca", help="Export SAP S/4HANA Universal Journal (ACDOCA) 50+ column format"),
    multi_currency: bool = typer.Option(False, "--multi-currency", help="Enable ASC 830 / IAS 21 multi-currency triangulation"),
    seasonality: bool = typer.Option(False, "--seasonality", help="Enable macro-economic quarter-end hockey stick and seasonality"),
    stream_chunks: Optional[int] = typer.Option(None, "--stream-chunks", help="Stream generation in chunks to bound RAM usage"),
):
    """Synthesizes balanced GL batches, injects calibrated micro-anomalies, and exports dual artifacts."""
    console.print(Panel.fit(
        "[bold cyan]Synthetic General Ledger Fuzzer[/bold cyan]\n"
        "[dim]Double-Entry Synthesis & Calibrated Anomaly Engine[/dim]\n"
        "[italic magenta]Made with <3 by Atiqul-Akash | GitHub: Atiqul-Akash[/italic magenta]"
    ))

    start_time = time.perf_counter()
    coa = ChartOfAccounts.create_default()

    if multi_currency or seasonality or stream_chunks:
        console.print(f"[green][Step 1] Synthesizing {count:,} baseline journal entries via Chunked Engine (Multi-Currency={multi_currency}, Seasonality={seasonality})...[/green]")
        engine = ChunkedSynthesisEngine(
            coa=coa,
            seed=seed,
            multi_currency=multi_currency,
            macro_seasonality=seasonality,
        )
        chunk_sz = stream_chunks or min(count, 10000)
        batch_entries = []
        anomaly_records = []
        for c_entries, c_anoms in engine.stream_chunks(total_entries=count, chunk_size=chunk_sz, anomaly_rate=anomaly_rate):
            batch_entries.extend(c_entries)
            anomaly_records.extend(c_anoms)

        batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch = Batch(batch_id=batch_id, created_at=datetime.now().isoformat(), entries=batch_entries)
    else:
        engine = BaseSynthesisEngine(coa=coa, seed=seed)
        console.print(f"[green][Step 1] Synthesizing {count:,} clean baseline journal entries across P2P, O2C, and R2R...[/green]")
        batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        batch = engine.generate_batch(batch_id=batch_id, target_entry_count=count)

        console.print(f"[yellow][Step 2] Injecting calibrated micro-anomalies at target rate {anomaly_rate:.1%}...[/yellow]")
        pipeline = AnomalyPipeline(coa=coa, seed=seed)
        anomaly_records = pipeline.inject_anomalies(batch=batch, overall_anomaly_rate=anomaly_rate)

    # 3. Mathematical Invariant Verification Gate
    console.print("[blue][Step 3] Invariant Gate: Verifying Debits == Credits across all batches and entries...[/blue]")
    invariant_report = InvariantVerifier.verify_batch(batch)

    if not invariant_report.is_globally_balanced or invariant_report.unbalanced_entries_count > 0:
        console.print(f"[bold red][FAIL] INVARIANT ERROR: Found {invariant_report.unbalanced_entries_count} unbalanced entries![/bold red]")
        for v in invariant_report.violations[:5]:
            console.print(f"  - {v.entry_id}: {v.message}")
        raise typer.Exit(code=1)

    console.print(f"[bold green][PASS] Invariant Verified:[/bold green] All {len(batch.entries):,} entries strictly balanced. Total Debits == Total Credits == ${batch.total_debits:,.2f}")

    # 4. Prepare Ground-Truth Manifest
    out_dir.mkdir(parents=True, exist_ok=True)
    anom_breakdown = dict(Counter(rec.anomaly_type.value for rec in anomaly_records))

    anomalous_entry_ids = set()
    for rec in anomaly_records:
        anomalous_entry_ids.update(rec.affected_entry_ids)

    manifest = GroundTruthManifest(
        dataset_id=batch_id,
        generated_at=datetime.now().isoformat(),
        seed=seed,
        total_batches=1,
        total_entries=len(batch.entries),
        total_lines=batch.total_line_count,
        clean_entries_count=len(batch.entries) - len(anomalous_entry_ids),
        anomalous_entries_count=len(anomalous_entry_ids),
        anomaly_rate=round(len(anomalous_entry_ids) / len(batch.entries), 4) if batch.entries else 0.0,
        anomaly_breakdown=anom_breakdown,
        anomalies=anomaly_records,
    )

    # 5. Dual-Artifact Export
    console.print(f"[magenta][Step 4] Exporting artifacts to {out_dir.resolve()}...[/magenta]")
    formats = [f.strip().lower() for f in export_formats.split(",") if f.strip()]

    export_summary = []

    # Parquet Feed
    parquet_path = out_dir / "gl_feed.parquet"
    if "parquet" in formats:
        _, p_hash = ParquetGLExporter.export(batch.entries, parquet_path)
        manifest.dataset_sha256 = p_hash
        export_summary.append(("Parquet GL Feed", str(parquet_path), p_hash[:16] + "..."))

    # CSV Feed
    csv_path = out_dir / "gl_feed.csv"
    if "csv" in formats:
        _, c_hash = CSVGLExporter.export(batch.entries, csv_path)
        if not manifest.dataset_sha256:
            manifest.dataset_sha256 = c_hash
        export_summary.append(("CSV GL Feed", str(csv_path), c_hash[:16] + "..."))

    # SAP BKPF / BSEG Format
    if "sap" in formats:
        sap_results = SAPBSEGExporter.export(batch.entries, out_dir / "sap")
        for table_name, (sp_path, s_hash) in sap_results.items():
            export_summary.append((f"SAP {table_name}", str(sp_path), s_hash[:16] + "..."))

    # SAP S/4HANA ACDOCA Universal Journal Format
    if acdoca or "acdoca" in formats:
        acdoca_pq_path = out_dir / "acdoca_feed.parquet"
        _, a_p_hash = SAPACDOCAExporter.export_parquet(batch.entries, acdoca_pq_path)
        export_summary.append(("SAP ACDOCA (Parquet)", str(acdoca_pq_path), a_p_hash[:16] + "..."))

        acdoca_csv_path = out_dir / "acdoca_feed.csv"
        _, a_c_hash = SAPACDOCAExporter.export_csv(batch.entries, acdoca_csv_path)
        export_summary.append(("SAP ACDOCA (CSV)", str(acdoca_csv_path), a_c_hash[:16] + "..."))

    # Export Manifests (JSON & Parquet)
    json_manifest_path = out_dir / "ground_truth_manifest.json"
    _, m_hash = ManifestExporter.export_json(manifest, json_manifest_path)
    export_summary.append(("Audit Manifest (JSON)", str(json_manifest_path), m_hash[:16] + "..."))

    parquet_manifest_path = out_dir / "ground_truth_manifest.parquet"
    _, mp_hash = ManifestExporter.export_parquet(manifest, parquet_manifest_path)
    export_summary.append(("Audit Manifest (Parquet)", str(parquet_manifest_path), mp_hash[:16] + "..."))

    elapsed = time.perf_counter() - start_time

    # Display Generation Summary
    summary_table = Table(title="Generation & Verification Summary", show_header=True, header_style="bold cyan")
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", justify="right")

    summary_table.add_row("Total Journal Entries", f"{len(batch.entries):,}")
    summary_table.add_row("Total Line Items", f"{batch.total_line_count:,}")
    summary_table.add_row("Total Debit Volume", f"${batch.total_debits:,.2f}")
    summary_table.add_row("Total Credit Volume", f"${batch.total_credits:,.2f}")
    summary_table.add_row("Double-Entry Delta", f"${batch.total_debits - batch.total_credits:.2f} (Zero Sum)")
    summary_table.add_row("Clean Entries", f"{manifest.clean_entries_count:,}")
    summary_table.add_row("Anomalous Entries", f"{manifest.anomalous_entries_count:,}")
    summary_table.add_row("Effective Anomaly Rate", f"{manifest.anomaly_rate:.2%}")
    summary_table.add_row("Elapsed Time", f"{elapsed:.2f}s ({len(batch.entries)/elapsed:,.0f} entries/s)")
    console.print(summary_table)

    # Anomaly Breakdown Table
    anom_table = Table(title="Calibrated Micro-Anomalies Injected", show_header=True, header_style="bold yellow")
    anom_table.add_column("Anomaly Type", style="bold")
    anom_table.add_column("Incidents", justify="right")
    for a_type, c_count in manifest.anomaly_breakdown.items():
        anom_table.add_row(a_type, str(c_count))
    console.print(anom_table)

    # Artifacts Table
    art_table = Table(title="Dual-Artifact Export Manifest", show_header=True, header_style="bold magenta")
    art_table.add_column("Artifact", style="bold")
    art_table.add_column("Path")
    art_table.add_column("SHA-256 Digest (Truncated)")
    for a_name, a_path, a_h in export_summary:
        art_table.add_row(a_name, a_path, a_h)
    console.print(art_table)


@app.command()
def verify(
    dataset: Path = typer.Option(..., "--dataset", "-d", help="Path to gl_feed.parquet or gl_feed.csv"),
    manifest: Optional[Path] = typer.Option(None, "--manifest", "-m", help="Optional path to ground_truth_manifest.json"),
):
    """Verifies strict double-entry balance and validates ground-truth manifest linkage."""
    console.print(Panel.fit("[bold blue]General Ledger Invariant Verification[/bold blue]"))

    if not dataset.exists():
        console.print(f"[bold red]Dataset not found: {dataset}[/bold red]")
        raise typer.Exit(code=1)

    # Load entries
    entries = _load_entries_from_file(dataset)
    report = InvariantVerifier.verify_entries(entries)

    table = Table(title="Mathematical Invariant Verification Results")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    table.add_row(
        "Sum(Debits) == Sum(Credits)",
        "[green]PASS[/green]" if report.is_globally_balanced else "[red]FAIL[/red]",
        f"Debits: ${report.total_debits:,.2f} | Credits: ${report.total_credits:,.2f}",
    )
    table.add_row(
        "Individual Entry Balance",
        "[green]PASS[/green]" if report.unbalanced_entries_count == 0 else "[red]FAIL[/red]",
        f"{report.total_entries_checked - report.unbalanced_entries_count} / {report.total_entries_checked} balanced",
    )
    console.print(table)

    if manifest and manifest.exists():
        with open(manifest, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        console.print(f"[cyan]Manifest Linked: {len(manifest_data.get('anomalies', []))} anomaly records documented.[/cyan]")


@app.command()
def audit_report(
    dataset: Path = typer.Option(..., "--dataset", "-d", help="Path to gl_feed.parquet or gl_feed.csv"),
    manifest: Optional[Path] = typer.Option(None, "--manifest", "-m", help="Optional ground truth manifest to calculate detection accuracy"),
):
    """Runs automated forensic audit scripts (SOX 404 tests) to detect anomalies in the dataset."""
    console.print(Panel.fit("[bold red]Forensic Audit Screening Report[/bold red]\n[dim]SOX-404 Automated Audit Testing Suite[/dim]"))

    entries = _load_entries_from_file(dataset)

    # 1. Benford's Law Chi-Square Test
    benford_res = ForensicAuditEvaluator.evaluate_benford_compliance(entries)

    # 2. DOA Split Approval Clusters
    doa_res = ForensicAuditEvaluator.detect_doa_split_clusters(entries)

    # 3. Off-Hours and Ghost Manual Entries
    off_hours_res = ForensicAuditEvaluator.detect_off_hours_and_ghost_entries(entries)

    # 4. Anomalous Account Pairings
    pairings_res = ForensicAuditEvaluator.detect_anomalous_pairings(entries)

    # 5. Intercompany Circular Round-Tripping
    ic_res = ForensicAuditEvaluator.detect_intercompany_cycles(entries)

    # Render Audit Table
    report_table = Table(title="SOX 404 / Forensic Audit Test Results", show_header=True, header_style="bold red")
    report_table.add_column("Audit Control / Test", style="bold")
    report_table.add_column("Signal Injected / Detected", justify="center")
    report_table.add_column("Findings & Metric Details")

    # Benford
    b_status = "[bold red]SIGNAL DETECTED[/bold red]" if benford_res["is_anomalous"] else "[green]NORMAL[/green]"
    report_table.add_row(
        "SOX-404-DATA: Benford Law First-Digit Screening",
        b_status,
        f"Chi2: {benford_res['chi2_statistic']}, p-val: {benford_res['p_value']:.4e} ({benford_res['forensic_conclusion']})"
    )

    # DOA
    d_status = f"[bold red]{doa_res['detected_clusters_count']} CLUSTERS[/bold red]" if doa_res["has_doa_violations"] else "[green]NORMAL[/green]"
    report_table.add_row(
        "SOX-404-P2P: Split Approval DOA Threshold Bypass",
        d_status,
        f"Found {doa_res['detected_clusters_count']} clusters in [$9,500, $9,999] targeting identical vendors within 48h"
    )

    # Off-hours
    o_status = f"[bold red]{off_hours_res['off_hours_flagged_count']} ENTRIES[/bold red]" if off_hours_res["has_unauthorized_mj_entries"] else "[green]NORMAL[/green]"
    report_table.add_row(
        "SOX-404-MJE: Unauthorized Off-Hours / Weekend MJEs",
        o_status,
        f"{off_hours_res['off_hours_flagged_count']} manual journal entries posted 02:00-04:30 or on weekends by dormant accounts"
    )

    # Pairings
    p_status = f"[bold red]{pairings_res['flagged_pairings_count']} VIOLATIONS[/bold red]" if pairings_res["has_topological_violations"] else "[green]NORMAL[/green]"
    report_table.add_row(
        "SOX-404-GL: Topological Anomalous Account Pairings",
        p_status,
        f"Found {pairings_res['flagged_pairings_count']} prohibited pairings (Cash<->Expense bypass, Suspense 99999, PPE bypass)"
    )

    # Round trip
    ic_status = f"[bold red]{ic_res['detected_cycles_count']} CYCLES[/bold red]" if ic_res["has_circular_round_tripping"] else "[green]NORMAL[/green]"
    report_table.add_row(
        "SOX-404-IC: Circular Intercompany Round-Tripping",
        ic_status,
        f"Detected {ic_res['detected_cycles_count']} directed loops across subsidiaries: {ic_res['cycles'][:2]}"
    )

    console.print(report_table)


@app.command()
def benchmark(
    count: int = typer.Option(10000, "--count", "-n", help="Number of entries to benchmark"),
    anomaly_rate: float = typer.Option(0.05, "--anomaly-rate", "-r", help="Anomaly rate"),
):
    """Benchmarks transaction synthesis and anomaly fuzzing throughput."""
    console.print(f"[bold cyan]Running throughput benchmark for {count:,} transactions...[/bold cyan]")
    start = time.perf_counter()

    coa = ChartOfAccounts.create_default()
    engine = BaseSynthesisEngine(coa=coa, seed=42)
    batch = engine.generate_batch(target_entry_count=count)
    gen_time = time.perf_counter() - start

    fuzz_start = time.perf_counter()
    pipeline = AnomalyPipeline(coa=coa, seed=42)
    records = pipeline.inject_anomalies(batch, overall_anomaly_rate=anomaly_rate)
    fuzz_time = time.perf_counter() - fuzz_start

    inv_start = time.perf_counter()
    report = InvariantVerifier.verify_batch(batch)
    inv_time = time.perf_counter() - inv_start

    total_time = time.perf_counter() - start
    total_lines = batch.total_line_count

    bench_table = Table(title=f"Benchmark Results ({count:,} entries, {total_lines:,} lines)")
    bench_table.add_column("Pipeline Stage", style="bold")
    bench_table.add_column("Time Elapsed", justify="right")
    bench_table.add_column("Throughput", justify="right")

    bench_table.add_row("1. Base Synthesis", f"{gen_time:.3f}s", f"{count/gen_time:,.0f} entries/s ({total_lines/gen_time:,.0f} lines/s)")
    bench_table.add_row("2. Anomaly Injection", f"{fuzz_time:.3f}s", f"{len(records)/fuzz_time:,.0f} anomalies/s")
    bench_table.add_row("3. Invariant Verification", f"{inv_time:.3f}s", f"{count/inv_time:,.0f} entries/s")
    bench_table.add_row("Total End-to-End", f"{total_time:.3f}s", f"{count/total_time:,.0f} entries/s")

    console.print(bench_table)


@app.command()
def gui(
    mode: str = typer.Option("web", "--mode", "-m", help="Interface mode: 'web' (modern browser app) or 'desktop' (native Windows window)"),
    port: int = typer.Option(8080, "--port", "-p", help="Port for web GUI server (used in web mode)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not automatically open default web browser"),
):
    """Launches the user-friendly Graphical User Interface (Modern Web or Native Desktop)."""
    if mode.lower() == "desktop":
        console.print("[bold cyan]Launching Synthetic General Ledger Fuzzer Native Desktop GUI...[/bold cyan]\n[italic magenta]Made with <3 by Atiqul-Akash | GitHub: Atiqul-Akash[/italic magenta]")
        from gl_fuzzer.desktop_gui import start_desktop_gui
        start_desktop_gui()
    else:
        console.print(f"[bold cyan]Launching Synthetic General Ledger Fuzzer Modern Web GUI on port {port}...[/bold cyan]\n[italic magenta]Made with <3 by Atiqul-Akash | GitHub: Atiqul-Akash[/italic magenta]")
        from gl_fuzzer.web_gui import start_web_gui
        start_web_gui(port=port, open_browser=not no_browser)


def _load_entries_from_file(path: Path) -> list[JournalEntry]:
    """Helper to reconstruct JournalEntry list from Parquet or CSV."""
    if path.suffix == ".parquet":
        table = pq.read_table(path)
        pydict = table.to_pylist()
    elif path.suffix == ".csv":
        import csv
        with open(path, "r", encoding="utf-8") as f:
            pydict = list(csv.DictReader(f))
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    # Group lines by entry_id / BELNR
    first_row = pydict[0] if pydict else {}
    is_acdoca = "BELNR" in first_row and "DOCLN" in first_row and "WSL" in first_row

    entries_map = {}
    for row in pydict:
        if is_acdoca:
            eid = row["BELNR"]
            if eid not in entries_map:
                doc_type_val = row.get("BLART", "SA")
                try:
                    dtype = DocumentType(doc_type_val)
                except Exception:
                    dtype = DocumentType.SA

                is_anom_raw = row.get("IS_ANOMALY", False)
                if isinstance(is_anom_raw, str):
                    is_anomaly_val = is_anom_raw.strip().lower() in ("true", "1", "yes")
                else:
                    is_anomaly_val = bool(is_anom_raw)

                anom_ids = [x for x in str(row.get("ANOMALY_IDS", "")).split(",") if x] if is_anomaly_val else []
                bdate_raw = str(row.get("BUDAT", "20260101"))
                p_date = f"{bdate_raw[:4]}-{bdate_raw[4:6]}-{bdate_raw[6:8]}" if len(bdate_raw) == 8 else bdate_raw

                entries_map[eid] = {
                    "header": {
                        "entry_id": eid,
                        "batch_id": f"BATCH_{row.get('GJAHR', 2026)}",
                        "company_code": row.get("RBUKRS", "1000"),
                        "fiscal_year": int(row.get("GJAHR", 2026)),
                        "fiscal_period": int(row.get("POPER", 9)),
                        "document_type": dtype,
                        "document_number": eid,
                        "posting_date": p_date,
                        "document_date": p_date,
                        "entry_time": row.get("CPUTM", "09:30:00"),
                        "created_at": f"{p_date}T{row.get('CPUTM', '09:30:00')}Z",
                        "created_by": row.get("USNAM", "SYSTEM"),
                        "reference": row.get("XBLNR", ""),
                        "header_text": row.get("BKTXT", ""),
                        "business_cycle": row.get("BUSINESS_CYCLE", "R2R"),
                        "is_anomaly": is_anomaly_val,
                        "anomaly_ids": anom_ids,
                    },
                    "lines": [],
                }

            dc_val = row.get("DRCRK", "S")
            dc = DebitCredit.DEBIT if dc_val.upper() in ("DEBIT", "S") else DebitCredit.CREDIT

            raw_amount = row["WSL"]
            if isinstance(raw_amount, Decimal):
                amount_val = raw_amount
            elif isinstance(raw_amount, float):
                amount_val = Decimal(f"{raw_amount:.2f}")
            else:
                amount_val = Decimal(str(raw_amount))

            entries_map[eid]["lines"].append(
                LineItem(
                    line_id=f"{eid}-{row['DOCLN']}",
                    entry_id=eid,
                    line_number=int(row["DOCLN"]),
                    account_code=row["RACCT"],
                    account_name=row.get("TXT50", ""),
                    debit_credit=dc,
                    amount=amount_val,
                    currency=row.get("RWCUR", "USD"),
                    posting_key=row.get("BSCHL", "40"),
                    cost_center=row.get("RCNTR") or None,
                    profit_center=row.get("PRCTR") or None,
                    vendor_id=row.get("LIFNR") or None,
                    customer_id=row.get("KUNNR") or None,
                    trading_partner=row.get("VBUND") or None,
                    line_text=row.get("SGTXT", ""),
                    tax_code=row.get("MWSKZ") or None,
                    amount_local=Decimal(str(row["HSL"])) if row.get("HSL") is not None else amount_val,
                    currency_local=row.get("RHCUR", "USD"),
                    amount_group=Decimal(str(row["KSL"])) if row.get("KSL") is not None else amount_val,
                    currency_group=row.get("RKCUR", "USD"),
                    ledger_group=row.get("RLDNR", "0L"),
                    segment=row.get("SEGMENT") or None,
                    functional_area=row.get("FKBER") or None,
                    wbs_element=row.get("PS_POSID") or None,
                    asset_number=row.get("ANLN1") or None,
                    asset_subnumber=row.get("ANLN2") or None,
                    material_number=row.get("MATNR") or None,
                    plant=row.get("WERKS") or None,
                    tax_jurisdiction=row.get("TXJCD") or None,
                    clearing_doc=row.get("AUGBL") or None,
                )
            )
        else:
            eid = row["entry_id"]
            if eid not in entries_map:
                doc_type_val = row["document_type"]
                try:
                    dtype = DocumentType(doc_type_val)
                except Exception:
                    dtype = DocumentType.SA

                is_anom_raw = row.get("is_anomaly", False)
                if isinstance(is_anom_raw, str):
                    is_anomaly_val = is_anom_raw.strip().lower() in ("true", "1", "yes")
                else:
                    is_anomaly_val = bool(is_anom_raw)

                anom_ids = [x for x in str(row.get("anomaly_ids", "")).split(",") if x] if is_anomaly_val else []

                entries_map[eid] = {
                    "header": {
                        "entry_id": eid,
                        "batch_id": row["batch_id"],
                        "company_code": row["company_code"],
                        "fiscal_year": int(row["fiscal_year"]),
                        "fiscal_period": int(row["fiscal_period"]),
                        "document_type": dtype,
                        "document_number": row["document_number"],
                        "posting_date": row["posting_date"],
                        "document_date": row["document_date"],
                        "entry_time": row["entry_time"],
                        "created_at": row["created_at"],
                        "created_by": row["created_by"],
                        "reference": row["reference"],
                        "header_text": row["header_text"],
                        "business_cycle": row["business_cycle"],
                        "is_anomaly": is_anomaly_val,
                        "anomaly_ids": anom_ids,
                    },
                    "lines": [],
                }

            dc_val = row["debit_credit"]
            dc = DebitCredit.DEBIT if dc_val.upper() in ("DEBIT", "S") else DebitCredit.CREDIT

            raw_amount = row["amount"]
            if isinstance(raw_amount, Decimal):
                amount_val = raw_amount
            elif isinstance(raw_amount, float):
                amount_val = Decimal(f"{raw_amount:.2f}")
            else:
                amount_val = Decimal(str(raw_amount))

            entries_map[eid]["lines"].append(
                LineItem(
                    line_id=row["line_id"],
                    entry_id=eid,
                    line_number=int(row["line_number"]),
                    account_code=row["account_code"],
                    account_name=row.get("account_name", ""),
                    debit_credit=dc,
                    amount=amount_val,
                    currency=row.get("currency", "USD"),
                    posting_key=row.get("posting_key", "40"),
                    cost_center=row.get("cost_center") or None,
                    profit_center=row.get("profit_center") or None,
                    vendor_id=row.get("vendor_id") or None,
                    customer_id=row.get("customer_id") or None,
                    trading_partner=row.get("trading_partner") or None,
                    line_text=row.get("line_text", ""),
                    tax_code=row.get("tax_code") or None,
                )
            )

    result = []
    for data in entries_map.values():
        entry = JournalEntry(**data["header"], lines=data["lines"])
        result.append(entry)

    return result


if __name__ == "__main__":
    app()
