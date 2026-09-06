# Synthetic General Ledger Fuzzer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
  <img src="https://img.shields.io/badge/Tests-53%20Passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="53 Tests Passed" />
  <img src="https://img.shields.io/badge/Double--Entry-Zero--Sum%20Verified-emerald?style=for-the-badge" alt="Double-Entry Invariant" />
  <img src="https://img.shields.io/badge/SOX-404-Compliant-indigo?style=for-the-badge" alt="SOX-404 Compliant" />
  <img src="https://img.shields.io/badge/Author-Atiqul--Akash-orange?style=for-the-badge&logo=github&logoColor=white" alt="Atiqul-Akash" />
</p>

<p align="center">
  <strong>Enterprise-Grade Synthetic General Ledger (GL) Fuzzer & Calibrated Anomaly Engine</strong><br>
  <em>Designed for forensic accounting research, financial ML model training, and SOX-404 audit automation.</em>
</p>

<p align="center">
  <strong>Made with ❤️ by <a href="https://github.com/Atiqul-Akash">Atiqul-Akash</a></strong> (GitHub: <a href="https://github.com/Atiqul-Akash">@Atiqul-Akash</a>)
</p>

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [System Architecture](#system-architecture)
- [Core Business Cycles](#core-business-cycles)
  - [Procure-to-Pay (P2P)](#1-procure-to-pay-p2p)
  - [Order-to-Cash (O2C)](#2-order-to-cash-o2c)
  - [Record-to-Report (R2R)](#3-record-to-report-r2r)
- [Calibrated Micro-Anomaly Library](#calibrated-micro-anomaly-library)
- [Double-Entry Mathematical Invariant Gate](#double-entry-mathematical-invariant-gate)
- [Dual Graphical User Interfaces (Zero-Confusion)](#dual-graphical-user-interfaces)
  - [1. Modern Web GUI (Browser-Based)](#1-modern-web-gui)
  - [2. Native Windows Desktop GUI (Offline Tkinter)](#2-native-windows-desktop-gui)
- [Quick Start & One-Click Launchers](#quick-start--one-click-launchers)
- [CLI Reference](#cli-reference)
- [Dual-Artifact Export Formats](#dual-artifact-export-formats)
- [Automated Forensic Audit Screening (SOX-404)](#automated-forensic-audit-screening)
- [Automated Test Suite (53 Tests)](#automated-test-suite)
- [Repository Structure](#repository-structure)
- [Contributing & License](#contributing--license)

---

## Executive Summary

Building enterprise fraud-detection models and automated internal audit screening systems faces a notorious **cold-start dilemma**: real-world general ledger transaction feeds containing verified financial crimes are confidential, legally restricted, and exceptionally rare.

The **Synthetic General Ledger Fuzzer** resolves this constraint by synthesizing realistic, multi-million-dollar corporate accounting ledgers while solving two competing requirements:
1. **Strict Mathematical Adherence to Double-Entry Bookkeeping**: Every generated journal entry—whether clean or fraudulent—strictly enforces $\sum \text{Debits} == \sum \text{Credits}$ at exact cent-level precision (`Decimal("0.01")`).
2. **Calibrated Forensic Micro-Anomalies**: Injects subtle, real-world statistical, structural, and temporal frauds directly mapped to **Sarbanes-Oxley (SOX) Section 404** control frameworks without breaking accounting balance invariants.

---

## System Architecture

```
                      [ Enterprise Chart of Accounts (COA) ]
                      [ Log-Normal & Business Calendar Config ]
                                         │
                                         ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                       1. Base Synthesis Engine                            │
   │   Generates realistic, balanced multi-leg vouchers across 3 cycles:       │
   │   ├── Procure-to-Pay (P2P)   [45%] -> WE (GR), KR (IR), KZ (Payment)     │
   │   ├── Order-to-Cash (O2C)    [45%] -> WA (GI), DR (Billing), DZ (Receipt)│
   │   └── Record-to-Report (R2R) [10%] -> Depreciation, 4-Leg Payroll, Accrual│
   └─────────────────────────────────────┬─────────────────────────────────────┘
                                         │
                                         ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                      2. Calibrated Anomaly Layer                          │
   │   Perturbs timing, amounts, counterparties, and account pairings:        │
   │   ├── [SOX-404-P2P]  Smurfing / Split Approvals (DOA Bypass Clusters)     │
   │   ├── [SOX-404-MJE]  Off-Hours & Ghost Manual Journal Entries             │
   │   ├── [SOX-404-DATA] Benford's Law First-Digit Skew                       │
   │   ├── [SOX-404-GL]   Topological Anomalous Account Pairings (Suspense)    │
   │   └── [SOX-404-IC]   Circular Intercompany Round-Tripping (Directed Loops)│
   └─────────────────────────────────────┬─────────────────────────────────────┘
                                         │
                                         ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │             3. Mathematical Invariant Verification Gate                   │
   │   Hard Decimal Cent Check: Σ(Debits) - Σ(Credits) == $0.000000000000      │
   │   ├── Verifies each individual voucher balance                            │
   │   └── Verifies atomic batch-level zero-sum balance                        │
   └─────────────────────────────────────┬─────────────────────────────────────┘
                                         │
                                         ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                         4. Dual-Artifact Export                           │
   │   ├── ERP-Ready GL Feed: Parquet (Decimal128) / CSV (RFC 4180) / SAP BSEG │
   │   └── Audit Manifest: JSON / Parquet Ground-Truth with SHA-256 Checksums  │
   └───────────────────────────────────────────────────────────────────────────┘
```

---

## Core Business Cycles

The engine models three comprehensive business accounting cycles according to standard ERP practices (such as SAP S/4HANA and Oracle Financials):

### 1. Procure-to-Pay (P2P)
Simulates end-to-end vendor procurement across three linked documents:
- **Goods Receipt (`WE`)**: Debits Inventory (`14000`), Credits GR/IR Clearing (`21100`).
- **Invoice Receipt (`KR`)**: Debits GR/IR Clearing (`21100`), Credits Accounts Payable Trade (`20000`) with assigned Vendor ID.
- **Vendor Payment (`KZ`)**: Debits AP Trade (`20000`), Credits Operating Cash (`10100`).

### 2. Order-to-Cash (O2C)
Simulates commercial customer sales lifecycle with multi-leg sales tax calculation:
- **Goods Issue (`WA`)**: Debits Cost of Goods Sold (`50000`), Credits Finished Goods Inventory (`14100`).
- **Customer Billing (`DR`)**: Multi-leg split entry debiting Accounts Receivable Trade (`11000`) for the full invoice amount, while crediting Sales Revenue (`40000`) and Sales Tax Payable (`22000`) based on configured tax rates (default: 6%).
- **Cash Receipt (`DZ`)**: Debits Operating Cash (`10100`), Credits AR Trade (`11000`).

### 3. Record-to-Report (R2R)
Simulates periodic closing, asset valuation, and operational entries:
- **Depreciation Run**: Debits Depreciation Expense (`65000`), Credits Accumulated Depreciation contra-asset (`17900`).
- **4-Leg Payroll Run**: Debits Salaries Expense (`61000`) and Payroll Tax Expense (`61100`), while crediting Salaries Payable (`21200`) and Tax Withholding Payable (`21300`).
- **Month-End Accruals**: Reversible closing adjustments across operating expense lines.

---

## Calibrated Micro-Anomaly Library

The fuzzer injects 5 precisely calibrated forensic accounting micro-anomalies mapped to internal control targets:

| Anomaly Pattern | Forensic Mechanics | Injected Forensic Signal | SOX-404 Control Reference |
| :--- | :--- | :--- | :--- |
| **Smurfing / Split Approvals** | Circumvents Delegations-of-Authority (DOA) limits requiring dual authorization. | Invoices split into clusters between **\$9,500 and \$9,999** targeting the same vendor within **48 hours**. | **SOX-404-P2P-DOA**: Circumvention of authorization limits. |
| **Off-Hours & Ghost Entries** | Simulates unauthorized management override and backdoor ledger postings. | Manual journal entries posted deep at night (**02:00–04:30 AM**) or on **weekends** by dormant service accounts (`SVC_DORMANT_ADMIN`). | **SOX-404-MJE-01**: Unauthorized manual journal entries. |
| **Benford's Law Invalidation** | Models artificial invoice fabrication and vendor kickback schemes. | Perturbs leading digit distribution $P(d) = \log_{10}(1 + 1/d)$, introducing uniform distributions or heavy spikes at digits **7, 8, 9**. | **SOX-404-DATA-INTEGRITY**: Kickback & invoice fabrication screening. |
| **Anomalous Account Pairings** | Topographical bypass of subledgers and unauthorized balance parking. | Direct **Debit Cash $\leftrightarrow$ Credit Expense**, unapproved parking into **Suspense Account (`99999`)**, or **Debit Expense $\leftrightarrow$ Credit Fixed Asset**. | **SOX-404-GL-PAIRING**: Suspense parking & unauthorized transfers. |
| **Circular Intercompany Loops** | Round-tripping cash transfers between subsidiaries to inflate artificial volume. | Directed transfer cycles across 3+ company codes: $\text{Entity}_A \rightarrow \text{Entity}_B \rightarrow \text{Entity}_C \rightarrow \text{Entity}_A$ within the same financial close window. | **SOX-404-IC-03**: Intercompany elimination and round-tripping. |

---

## Double-Entry Mathematical Invariant Gate

Unlike simplistic random generators that use IEEE 754 floating-point numbers (`float64`), this engine enforces **Python `Decimal` cent-level quantization (`ROUND_HALF_UP`)** across all transactions.

$$\sum_{i=1}^{N_{\text{debits}}} \text{Debit}_i - \sum_{j=1}^{M_{\text{credits}}} \text{Credit}_j \equiv 0.00$$

- **Parquet Export Precision**: Columns utilize PyArrow `pa.decimal128(18, 2)` to eliminate precision degradation when saved to disk.
- **Automated Invariant Gate**: Every batch passes through `InvariantVerifier` prior to export. If a single entry deviates by even $\$0.01$, the pipeline aborts immediately.

---

## Dual Graphical User Interfaces

To make testing, analysis, and data synthesis accessible to both technical developers and non-technical forensic auditors, the project includes two complete graphical user interfaces:

### 1. Modern Web GUI
- **Stack**: Pure Python built-in HTTP server (`http.server`), modern Tailwind CSS, Chart.js.
- **Zero External Server Dependencies**: Runs locally without needing Node.js, npm, or cloud infrastructure.
- **Features**:
  - Live **Zero-Sum Balance Monitor Badge**.
  - **Quick Start Presets**: *Standard Benchmark*, *Quick Smoke Test*, *Forensic Stress*, *Clean Baseline*.
  - **Interactive Voucher Explorer**: Search, filter, and inspect debit/credit line items and counterparty IDs.
  - **SOX-404 Screening Center**: Visual Benford curve comparison chart, DOA cluster breakdowns, off-hours distribution, and intercompany loops.
  - **One-Click Downloads**: Direct browser downloads for Parquet, CSV, SAP BSEG/BKPF, and JSON manifests.

### 2. Native Windows Desktop GUI
- **Stack**: Native Python `tkinter` and `ttk` with styled widgets.
- **100% Offline**: Operates completely disconnected from the internet.
- **4 Dedicated Workspaces**:
  1. *Synthesis & Generation*: Sliders, anomaly toggles, and live progress reporting.
  2. *Voucher & Ledger Explorer*: Paginated table with double-click drilldown into line items.
  3. *SOX-404 Forensic Audit*: Diagnostic cards with status badges and forensic findings.
  4. *Export & Artifacts*: Target folder picker and format selection.

---

## Quick Start & One-Click Launchers

### Option A: Double-Click Launcher (Windows)
Double-click **`run.bat`** in the project root. An interactive menu will appear:
```
===============================================================================
              SYNTHETIC GENERAL LEDGER (GL) FUZZER
       Double-Entry Accounting Synthesis & Calibrated Anomaly Studio
            Made with <3 by Atiqul-Akash | GitHub: Atiqul-Akash
===============================================================================

  [1] Modern Web GUI (Recommended - Browser at http://localhost:8080)
  [2] Native Windows Desktop GUI (Offline Window)
  [3] Generate Synthetic Dataset (CLI - 1,000 entries)
  [4] Run SOX-404 Forensic Audit on Generated Dataset
  [5] Run Complete Automated Test Suite (53 tests)
  [6] Exit
```

### Option B: Cross-Platform Python Launcher
```bash
python run.py             # Launches interactive menu
python run.py --web       # Directly launches Modern Web GUI
python run.py --desktop   # Directly launches Native Desktop GUI
python run.py --test      # Executes automated pytest suite
```

---

## CLI Reference

The fuzzer provides a high-performance CLI powered by Typer and Rich:

```bash
# 1. Synthesize 5,000 journal entries with 5% anomaly rate
python -m gl_fuzzer.cli generate --count 5000 --anomaly-rate 0.05 --out-dir ./output --export-formats parquet,csv,sap

# 2. Verify double-entry balance and manifest checksums
python -m gl_fuzzer.cli verify --dataset ./output/gl_feed.parquet --manifest ./output/ground_truth_manifest.json

# 3. Run automated SOX-404 forensic audit screening
python -m gl_fuzzer.cli audit-report --dataset ./output/gl_feed.parquet --manifest ./output/ground_truth_manifest.json

# 4. Benchmark generation and fuzzing throughput
python -m gl_fuzzer.cli benchmark --count 10000 --anomaly-rate 0.05

# 5. Launch graphical interface
python -m gl_fuzzer.cli gui --port 8080          # Web GUI
python -m gl_fuzzer.cli gui --mode desktop      # Desktop GUI
```

---

## Dual-Artifact Export Formats

Generated datasets are exported with full audit trail documentation:

1. **Parquet Feed (`gl_feed.parquet`)**: High-performance columnar storage using `decimal128(18, 2)` for amounts and Snappy compression.
2. **CSV Feed (`gl_feed.csv`)**: RFC-4180 compliant tabular ledger format.
3. **SAP ERP Standard Tables**:
   - **`BKPF.csv`**: SAP Accounting Document Header (`BUKRS`, `BELNR`, `GJAHR`, `BLART`, `BLDAT`, `BUDAT`, `USNAM`, `XBLNR`, `BKTXT`).
   - **`BSEG.csv`**: SAP Accounting Document Line Item Segment (`BUKRS`, `BELNR`, `GJAHR`, `BUZEI`, `BSCHL`, `SHKZG`, `HKONT`, `WRBTR`, `WAERS`, `KOSTL`, `PRCTR`, `LIFNR`, `KUNNR`, `VBUND`, `SGTXT`).
4. **Ground-Truth Audit Manifest (`ground_truth_manifest.json` & `.parquet`)**: Complete mapping of every injected anomaly, affected document numbers, line items, mathematical parameters, and forensic signals.
5. **Cryptographic SHA-256 Digest (`.sha256`)**: Detached checksums verifying dataset integrity.

---

## Automated Forensic Audit Screening

The framework includes built-in detection algorithms evaluating datasets against SOX-404 compliance rules:

- **Benford's Law Chi-Square Test**: Calculates $\chi^2 = \sum \frac{(O_i - E_i)^2}{E_i}$ against expected $\log_{10}(1 + 1/d)$ frequencies ($\alpha = 0.05$, Critical Value = $15.51$).
- **DOA Split Approval Clustering**: Sliding temporal window identifying multiple invoices under $\$10,000$ to the same vendor within 48 hours.
- **Off-Hours Detection**: Filters manual entries posted between 02:00 and 04:30 AM, or during weekend cycles by non-standard users.
- **Topological Pairing Inspector**: Flags forbidden bipartite subledger bypasses (e.g. Operating Expense directly offsetting Cash).
- **Intercompany Cycle Detection**: Depth-First Search (DFS) on directed subsidiary trading graphs to uncover circular volume-inflation loops.

---

## Automated Test Suite

The codebase includes an automated test suite with **53 comprehensive unit and integration tests**:

```bash
python -m pytest -v
```

```
tests/test_anomalies.py ......                     [ 11%]
tests/test_audit_metrics.py .....                  [ 20%]
tests/test_cli.py ..                              [ 24%]
tests/test_coa_models.py ...                       [ 30%]
tests/test_cycles.py ....                          [ 37%]
tests/test_edge_cases.py .....                     [ 47%]
tests/test_exporters.py ....                       [ 54%]
tests/test_generators.py ....                      [ 62%]
tests/test_gui.py .....                            [ 71%]
tests/test_invariants.py ....                      [ 79%]
tests/test_models.py ...........                  [100%]

============================= 53 passed in 2.35s ==============================
```

---

## Repository Structure

```
Synthetic-General-Ledger-Fuzzer/
├── gl_fuzzer/
│   ├── __init__.py
│   ├── cli.py                     # Typer / Rich command-line interface
│   ├── web_gui.py                 # Modern browser-based dashboard (Tailwind + Chart.js)
│   ├── desktop_gui.py             # Native offline Tkinter application
│   ├── models/
│   │   ├── coa.py                 # Chart of Accounts, Account, NormalBalance
│   │   ├── journal.py             # LineItem, JournalEntry, Batch (Decimal cent logic)
│   │   └── manifest.py            # AnomalyRecord, GroundTruthManifest
│   ├── generators/
│   │   ├── distributions.py       # Benford, LogNormal, BusinessCalendar
│   │   ├── p2p_cycle.py           # Procure-to-Pay generator (WE, KR, KZ)
│   │   ├── o2c_cycle.py           # Order-to-Cash generator (WA, DR, DZ)
│   │   ├── r2r_cycle.py           # Record-to-Report (Depreciation, Payroll, Accrual)
│   │   └── base_engine.py         # Master synthesis engine
│   ├── anomalies/
│   │   ├── base_mutator.py        # Abstract base class for mutators
│   │   ├── smurfing.py            # Split approval DOA bypass
│   │   ├── ghost_entries.py       # Off-hours and weekend MJEs
│   │   ├── benford_skew.py        # First-digit distribution skewing
│   │   ├── anomalous_pairings.py  # Suspense & prohibited offset pairings
│   │   ├── round_tripping.py      # Intercompany circular transfer cycles
│   │   └── pipeline.py            # Anomaly orchestration pipeline
│   ├── verification/
│   │   ├── invariants.py          # Strict double-entry balance verifier
│   │   └── audit_metrics.py       # SOX-404 automated audit detection algorithms
│   └── exporters/
│       ├── parquet_exporter.py    # PyArrow Decimal128 Parquet exporter
│       ├── csv_exporter.py        # RFC 4180 CSV exporter
│       ├── sap_bseg_exporter.py   # SAP BKPF / BSEG table exporter
│       └── manifest_exporter.py   # JSON & Parquet manifest exporter
├── tests/                         # 53 automated unit and integration tests
├── pyproject.toml                 # Project configuration and dependencies
├── run.bat                        # Windows 1-click launcher
├── run.py                         # Cross-platform interactive launcher
├── LICENSE                        # MIT License
└── README.md                      # Comprehensive documentation
```

---

## Contributing & License

Contributions, issue reports, and feature suggestions are welcome! Please feel free to open a pull request or issue on GitHub.

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

<p align="center">
  <strong>Synthetic General Ledger Fuzzer</strong><br>
  Made with ❤️ by <a href="https://github.com/Atiqul-Akash">Atiqul-Akash</a>
</p>
