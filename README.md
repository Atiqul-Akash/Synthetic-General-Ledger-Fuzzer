# Synthetic General Ledger Fuzzer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
  <img src="https://img.shields.io/badge/Tests-150%20Passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="150 Tests Passed" />
  <img src="https://img.shields.io/badge/Version-0.3.0%20Enterprise-blueviolet?style=for-the-badge" alt="v0.3.0 Enterprise" />
  <img src="https://img.shields.io/badge/Double--Entry-Zero--Sum%20Verified-emerald?style=for-the-badge" alt="Double-Entry Invariant" />
  <img src="https://img.shields.io/badge/SOX-404-Compliant-indigo?style=for-the-badge" alt="SOX-404 Compliant" />
  <img src="https://img.shields.io/badge/Author-Atiqul--Akash-orange?style=for-the-badge&logo=github&logoColor=white" alt="Atiqul-Akash" />
</p>

<p align="center">
  <strong>Enterprise-Grade Synthetic General Ledger (GL) Fuzzer & Calibrated Anomaly Engine</strong><br>
  <em>Designed for forensic accounting research, financial ML model training, dynamic security auditing, and SOX-404 compliance testing.</em>
</p>

<p align="center">
  <strong>Made with ❤️ by <a href="https://github.com/Atiqul-Akash">Atiqul-Akash</a></strong> (GitHub: <a href="https://github.com/Atiqul-Akash">@Atiqul-Akash</a>)
</p>

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Enterprise Architecture (v0.3)](#enterprise-architecture-v20)
- [Five Enterprise Architectural Pillars (v0.3)](#five-enterprise-architectural-pillars-v20)
  - [1. Stateful, Bidirectional ERP Synchronization](#1-stateful-bidirectional-erp-synchronization)
  - [2. Multi-Jurisdictional Tax Localization Engine](#2-multi-jurisdictional-tax-localization-engine)
  - [3. Dynamic Security Fuzzing Feedback Loop](#3-dynamic-security-fuzzing-feedback-loop)
  - [4. Operational Logistics & Stateful Subledgers](#4-operational-logistics--stateful-subledgers)
  - [5. Real-Time Event Streaming Sinks](#5-real-time-event-streaming-sinks)
- [Core Business Cycles](#core-business-cycles)
  - [Procure-to-Pay (P2P)](#1-procure-to-pay-p2p)
  - [Order-to-Cash (O2C)](#2-order-to-cash-o2c)
  - [Record-to-Report (R2R)](#3-record-to-report-r2r)
- [Calibrated Micro-Anomaly Library](#calibrated-micro-anomaly-library)
- [Multi-Currency Triangulation Engine (ASC 830 / IAS 21)](#multi-currency-triangulation-engine-asc-830--ias-21)
- [Macro-Economic Seasonality Modulator](#macro-economic-seasonality-modulator)
- [SAP S/4HANA Universal Journal (ACDOCA)](#sap-s4hana-universal-journal-acdoca)
- [Double-Entry Mathematical Invariant Gate](#double-entry-mathematical-invariant-gate)
- [Dual Graphical User Interfaces](#dual-graphical-user-interfaces)
  - [1. Modern Web GUI (Browser-Based)](#1-modern-web-gui)
  - [2. Native Windows Desktop GUI (Offline Tkinter v0.3)](#2-native-windows-desktop-gui)
- [Quick Start & One-Click Launchers](#quick-start--one-click-launchers)
- [CLI Reference](#cli-reference)
- [Dual-Artifact Export Formats](#dual-artifact-export-formats)
- [Automated Forensic Audit Screening (SOX-404)](#automated-forensic-audit-screening)
- [Automated Test Suite (150 Tests)](#automated-test-suite)
- [Repository Structure](#repository-structure)
- [Contributing & License](#contributing--license)

---

## Executive Summary

Building enterprise fraud-detection models, validating accounting automation systems, and auditing ERP integrity faces a notorious **cold-start dilemma**: real-world general ledger transaction feeds containing verified financial crimes or edge cases are confidential, legally restricted, and exceptionally rare.

The **Synthetic General Ledger Fuzzer (v0.3 Enterprise)** bridges this gap by providing an end-to-end framework capable of:
1. **Mathematical Invariant Rigor**: Every synthesized transaction voucher strictly enforces $\sum \text{Debits} \equiv \sum \text{Credits}$ across document, functional/local, and group consolidation currencies at exact cent precision (`Decimal("0.01")`).
2. **Stateful ERP Interoperability**: Bi-directionally reads master data and balances from live or simulated SAP S/4HANA (OData V4, NetWeaver RFC) and Oracle Fusion Cloud REST environments.
3. **Multi-Jurisdictional Tax Compliance**: Evaluates nexus, VAT reverse charges, and statutory withholding taxes across 50 US states, 27 EU member nations, the UK HMRC, and India TDS.
4. **Dynamic Security Auditing**: Employs adaptive grammar-based mutators, crash monitoring, and coverage oracles to fuzz relational databases and ERP API endpoints.
5. **Operational Subledger Integrity**: Simulates warehouse inventory stock, Moving Average Price (MAP) updates, and 3-Way Matching (PO $\rightarrow$ Goods Receipt $\rightarrow$ Invoice Receipt).
6. **Real-Time Streaming**: Directly streams double-entry journal events to Apache Kafka, AWS Kinesis, and Azure Event Hubs with CloudEvents v1.0 compliance.

---

## Enterprise Architecture (v0.3)

```
                            [ Live ERP System / Mock Sandbox ]
                         (SAP S/4HANA OData / RFC | Oracle REST)
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │    1. ERP Connector Gateway     │
                         │    (gl_fuzzer/connectors/)      │
                         │ Reads COA, Open Items, Periods  │
                         └────────────────┬────────────────┘
                                          │
                                          ▼
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │                        2. Core Generation Engine                                │
 │   Synthesizes balanced multi-leg vouchers with subledgers & tax localization:   │
 │   ├── Subledger Engine:  Material Master, MAP, 3-Way Match, Purchase Variance   │
 │   ├── Global Tax Engine: US Nexus (50 states), EU VAT, UK HMRC, India TDS/WHT   │
 │   ├── Multi-Currency:    ASC 830 / IAS 21 Stochastic Triangulation (12 Currs)   │
 │   └── Macro Modulator:   Hockey-Stick Surges, Q4 Year-End Rush, Day-of-Week     │
 └────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                                          ▼
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │                       3. Calibrated Anomaly Engine                              │
 │   Injects forensic micro-anomalies & dynamic security attack payloads:          │
 │   ├── Smurfing (DOA Split Approvals)       ├── Benford's Law First-Digit Skew   │
 │   ├── Ghost Entries & Off-Hours Postings   ├── Topological Pairings (Suspense)  │
 │   ├── Circular Intercompany Round-Tripping ├── Withholding Tax Evasion          │
 │   ├── Phantom PO 3-Way Match Bypass        └── SQL Injection / Unicode Overflow │
 └────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                                          ▼
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │                  4. Mathematical Invariant Verification Gate                    │
 │   Hard Decimal Cent Check: Σ(Debits) - Σ(Credits) == $0.000000000000            │
 │   Guarantees zero-sum balance across Doc, Local, and Group consolidation legs   │
 └────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
             ┌────────────────────────────┴────────────────────────────┐
             ▼                                                         ▼
┌───────────────────────────────┐                       ┌───────────────────────────────┐
│     5. Real-Time Streaming    │                       │     6. Dual-Artifact Export   │
│   (gl_fuzzer/streaming/)      │                       │   (gl_fuzzer/exporters/)      │
│ ├── Apache Kafka Publisher    │                       │ ├── SAP ACDOCA (Parquet/CSV)  │
│ ├── AWS Kinesis Streams       │                       │ ├── Standard GL (Parquet/CSV) │
│ ├── Azure Event Hubs          │                       │ ├── SAP BKPF / BSEG Tables    │
│ └── CloudEvents v1.0 / ACDOCA │                       │ └── Ground-Truth Manifest     │
└───────────────────────────────┘                       └───────────────────────────────┘
```

---

## Five Enterprise Architectural Pillars (v0.3)

### 1. Stateful, Bidirectional ERP Synchronization
*Package: `gl_fuzzer/connectors/`*

Enables the fuzzer to synchronize with active enterprise environments instead of merely generating isolated files:
- **SAP S/4HANA OData V4 (`odata_connector.py`)**: Interacts with the standard `API_JOURNALENTRYCREATEREQUEST` service. Extracts company code charts of accounts, open items (`BSID`/`BSIK`), account balances, and period statuses (`T001B`).
- **SAP NetWeaver RFC (`rfc_connector.py`)**: Supports low-level RFC invocation (`RFC_READ_TABLE`, `BAPI_ACC_DOCUMENT_POST`) with automatic graceful fallback when `pyrfc` is absent.
- **Oracle Fusion Cloud REST (`oracle_connector.py`)**: Synchronizes with Oracle ERP Cloud financial REST endpoints (`/fscmRestApi/resources/11.13.18.05/invoices`).
- **Automated Sandbox Fallback (`mock_erp.py`)**: Operates 100% offline out-of-the-box with an in-memory ERP database simulating realistic posting latencies, open item tracking, and period locks.

### 2. Multi-Jurisdictional Tax Localization Engine
*Package: `gl_fuzzer/tax/`*

Replaces flat tax estimations with a comprehensive multi-tier global tax engine:
- **US Multi-State Nexus (`us_sales_tax.py`)**: Implements physical and economic nexus rules for **all 50 US states** (plus DC). Handles resale exemption certificates (`ST-120`), freight taxability, and consumer use tax accruals (`Accrued Use Tax 22100`).
- **EU VAT & OSS (`eu_vat.py`)**: Covers **all 27 EU member states** with standard and reduced VAT rates. Implements cross-border B2B **Reverse Charge** mechanisms with dual self-assessing wash legs (Input VAT debit vs Output VAT credit) that maintain exact ledger balance.
- **UK HMRC VAT (`eu_vat.py`)**: Standard 20% and 5% domestic fuel/power rates according to HMRC Notice 700.
- **Statutory Withholding Tax / TDS (`withholding.py`)**: Implements Indian Income Tax Act Section 194C (Contractors) and Section 194J (Professional fees) withholding at source, deducting tax directly from vendor disbursements into withholding payable accounts (`22200`).
- **Statutory Tax Return Generator (`engine.py`)**: Aggregates taxable transactions across a fiscal period, computing gross taxable revenue, output tax, deductible input tax, and net statutory tax payable or refundable.

### 3. Dynamic Security Fuzzing Feedback Loop
*Package: `gl_fuzzer/fuzzing/`*

Brings dynamic software security testing into financial accounting systems:
- **Adaptive Transactional Fuzzer (`adaptive_fuzzer.py`)**: Uses multi-armed bandit reinforcement learning to dynamically adjust mutation operator weights based on vulnerability discovery feedback.
- **Security Mutation Operators**:
  - `BOUNDARY_DOA`: Generates transactions hitting authorization ceiling limits (`$9,999.99`).
  - `SQL_INJECTION`: Injects SQL escape syntax into line item texts and document references (`' OR '1'='1`, `'); DROP TABLE BKPF;--`).
  - `UNICODE_OVERFLOW`: Tests database buffer handling using deep multibyte strings and zero-width joiners.
  - `NULL_BYTE_INJECTION`: Tests C-layer string termination vulnerabilities (`PO-100\x00-PAYLOAD`).
  - `CLOSED_PERIOD_PROBE`: Attempts posting to locked prior fiscal periods.
- **Target Harnesses (`target.py`, `mock_app.py`, `sql_target.py`)**: Tests both simulated ERP applications and real SQLite relational databases enforcing ACID constraints and foreign keys.
- **Crash Monitor & Coverage Oracle (`oracle.py`)**: Aggregates unhandled database crashes, integrity bypasses, and tracks rule coverage across 10+ standard financial posting checks.

### 4. Operational Logistics & Stateful Subledgers
*Package: `gl_fuzzer/subledgers/`*

Simulates underlying warehouse logistics and operational subledger flows:
- **Material Master & Inventory (`inventory.py`)**: Maintains real-time warehouse inventory across plants, storage locations, and bins. Recalculates inventory valuation upon every goods receipt using the **Moving Average Price (MAP)** formula:
  $$\text{New MAP} = \frac{(\text{Current Stock} \times \text{Current MAP}) + (\text{Received Qty} \times \text{Received Price})}{\text{Current Stock} + \text{Received Qty}}$$
- **3-Way Matching Engine (`three_way_match.py`)**: Reconciles Purchase Order (`PO`), Goods Receipt (`WE`), and Invoice Receipt (`RE`). Automatically detects and posts **Purchase Price Variance (PPV Account 52100)** when invoice unit prices diverge from purchase orders.
- **Sales Order Fulfillment (`order_fulfillment.py`)**: Couples customer billing (`DR`) with goods delivery (`WA`), dynamically deriving Cost of Goods Sold (`50000`) directly from the moving average price of the warehouse inventory.
- **Physical Count Shrinkage Adjustment**: Accurately handles periodic stock takes, crediting damaged or missing inventory (`14000`) into Inventory Shrinkage (`50100`).

### 5. Real-Time Event Streaming Sinks
*Package: `gl_fuzzer/streaming/`*

Enables continuous streaming of double-entry financial events into modern distributed architectures:
- **Apache Kafka (`kafka_publisher.py`)**: Streams journal entries to partitioned topics (`gl.transactions.v1`, `gl.anomalies.v1`) with MD5 document key hashing for partition affinity.
- **Cloud Streaming Sinks (`cloud_publishers.py`)**: Integrates with **AWS Kinesis Data Streams** and **Azure Event Hubs**.
- **Embedded In-Memory Broker**: Includes a thread-safe, multi-partition in-memory Kafka broker simulator (`EmbeddedKafkaBroker`), ensuring full local execution without requiring an active external Kafka cluster.
- **Multi-Schema Serializers (`serializers.py`)**: Supports JSON, **CloudEvents v1.0** compliance (`specversion: 1.0`, `type: com.enterprise.gl.journalentry`), and SAP S/4HANA ACDOCA flat dictionary format.

---

## Core Business Cycles

The engine models three comprehensive business accounting cycles according to standard ERP practices (such as SAP S/4HANA and Oracle Financials):

### 1. Procure-to-Pay (P2P)
Simulates end-to-end vendor procurement across three linked documents:
- **Goods Receipt (`WE`)**: Debits Inventory (`14000`), Credits GR/IR Clearing (`21100`).
- **Invoice Receipt (`KR` / `RE`)**: Debits GR/IR Clearing (`21100`), posts Purchase Price Variance (`52100`) if applicable, Credits Accounts Payable Trade (`20000`).
- **Vendor Payment (`KZ`)**: Debits AP Trade (`20000`), Credits Operating Cash (`10100`), with optional statutory withholding tax (`22200`).
- **Standalone Vendor Invoice**: Direct expense voucher generation debiting departmental expenses (`62000`–`69000`) and crediting Accounts Payable (`20000`).

### 2. Order-to-Cash (O2C)
Simulates commercial customer sales lifecycle with multi-leg sales tax calculation:
- **Goods Issue (`WA`)**: Debits Cost of Goods Sold (`50000`), Credits Finished Goods Inventory (`14100`).
- **Customer Billing (`DR` / `RV`)**: Multi-leg split entry debiting Accounts Receivable Trade (`11000`) for full invoice amount, crediting Sales Revenue (`40000`) and localized Sales Tax Payable (`22000`).
- **Cash Receipt (`DZ`)**: Debits Operating Cash (`10100`), Credits AR Trade (`11000`).
- **Standalone Customer Invoice**: Direct billing voucher synthesis debiting AR Trade (`11000`) and crediting Sales/Service Revenue (`40000`/`41000`).

### 3. Record-to-Report (R2R)
Simulates periodic closing, asset valuation, and operational entries:
- **Depreciation Run**: Debits Depreciation Expense (`65000`), Credits Accumulated Depreciation contra-asset (`17900`).
- **4-Leg Payroll Run**: Debits Salaries Expense (`61000`) and Payroll Tax Expense (`61100`), while crediting Salaries Payable (`21200`) and Tax Withholding Payable (`21300`).
- **Month-End Accruals**: Reversible closing adjustments across operating expense lines.

---

## Calibrated Micro-Anomaly Library

The fuzzer injects calibrated forensic accounting micro-anomalies mapped to internal control targets:

| Anomaly Pattern | Forensic Mechanics | Injected Forensic Signal | SOX-404 Control Reference |
| :--- | :--- | :--- | :--- |
| **Smurfing / Split Approvals** | Circumvents Delegations-of-Authority (DOA) limits requiring dual authorization. | Invoices split into clusters between **\$9,500 and \$9,999** targeting the same vendor within **48 hours**. | **SOX-404-P2P-DOA**: Circumvention of authorization limits. |
| **Off-Hours & Ghost Entries** | Simulates unauthorized management override and backdoor ledger postings. | Manual journal entries posted deep at night (**02:00–04:30 AM**) or on **weekends** by dormant service accounts (`SVC_DORMANT_ADMIN`). | **SOX-404-MJE-01**: Unauthorized manual journal entries. |
| **Benford's Law Invalidation** | Models artificial invoice fabrication and vendor kickback schemes. | Perturbs leading digit distribution $P(d) = \log_{10}(1 + 1/d)$, introducing uniform distributions or heavy spikes at digits **7, 8, 9**. | **SOX-404-DATA-INTEGRITY**: Kickback & invoice fabrication screening. |
| **Anomalous Account Pairings** | Topographical bypass of subledgers and unauthorized balance parking. | Direct **Debit Cash $\leftrightarrow$ Credit Expense**, unapproved parking into **Suspense Account (`99999`)**, or **Debit Expense $\leftrightarrow$ Credit Fixed Asset**. | **SOX-404-GL-PAIRING**: Suspense parking & unauthorized transfers. |
| **Circular Intercompany Loops** | Round-tripping cash transfers between subsidiaries to inflate artificial volume. | Directed transfer cycles across 3+ company codes: $\text{Entity}_A \rightarrow \text{Entity}_B \rightarrow \text{Entity}_C \rightarrow \text{Entity}_A$ within the same financial close window. | **SOX-404-IC-03**: Intercompany elimination and round-tripping. |
| **Withholding Tax Evasion** | Vendor payment disbursed in full without mandatory statutory tax withholding. | Bypasses Account `22200` on qualifying disbursements ($\ge \$500$). | **SOX-404-TAX-WHT**: Statutory tax deduction bypass. |
| **Phantom PO 3-Way Match Bypass** | Direct invoice booking without an approved purchase order or goods receipt. | Vendor invoice posted directly to AP without a matching Goods Receipt (`WE`) voucher. | **SOX-404-P2P-3WM**: 3-way matching purchase bypass. |
| **Inventory Shrinkage Concealment** | Unauthorized write-off of warehouse inventory into suspense or retained earnings. | Inventory credited directly against suspense (`99999`) bypassing shrinkage clearing (`50100`). | **SOX-404-INV-SHRINK**: Unauthorized inventory write-down. |

---

## Multi-Currency Triangulation Engine (ASC 830 / IAS 21)

Enterprise multinationals require reporting across multiple currency ledgers with differing functional and consolidation currencies. The engine implements an automated **ASC 830 / IAS 21 compliant valuation triad**:

- **Stochastic Spot Rates**: Daily fluctuating exchange rates modeled using a mean-reverting **Geometric Brownian Motion (Ornstein-Uhlenbeck drift)** pulling towards corporate baseline pegs.
- **Triangulation Engine**: Triangulates cross-rates between USD, EUR, GBP, JPY, CHF, CAD, AUD, BRL, INR, CNY, MXN, SGD, and AED.
- **Valuation Triad**:
  - `amount` / `WSL`: Transaction Document Currency amount.
  - `amount_local` / `HSL`: Company code functional operating currency (e.g. USD).
  - `amount_group` / `KSL`: Global corporate consolidation currency (e.g. USD).
- **Exact Cent Invariant Safeguard**: Fractional-cent exchange rate conversion rounding deltas are automatically absorbed into offsetting credit legs to maintain $\sum \text{Debits} == \sum \text{Credits} \equiv 0.00$ in all three valuation currencies simultaneously (`is_balanced_local` & `is_balanced_group`).

---

## Macro-Economic Seasonality Modulator

Real enterprise accounting volumes follow pronounced temporal patterns rather than uniform random spreads. The `MacroCalendarModulator` introduces:

- **Quarter-End "Hockey Stick" Surges**: Corporate sales reps and billing departments rush to close revenue before quarter-end dates (March 24-31, June 24-30, September 24-30: **+45% volume surge**).
- **Q4 Fiscal Year-End Close**: Annual financial closing and holiday push (December 15-31: **+85% volume surge**).
- **January Post-Close Lull**: Early January posting slowdown (-35% volume).
- **Enterprise Day-of-Week Cadence**: Corporate posting peaks mid-week (Tuesday through Thursday at $1.25\times$), with weekend automated system batches suppressed ($0.15\times$).

---

## SAP S/4HANA Universal Journal (ACDOCA)

For modern enterprise ERP integration and ML training against next-generation financial architectures, the engine features a dedicated exporter for **SAP S/4HANA Table ACDOCA (Universal Journal)** with 50+ enterprise dimensions:

| Field | SAP Technical Name | Description |
| :--- | :--- | :--- |
| **Client** | `RCLNT` | SAP Client partition (e.g. `100`) |
| **Ledger Group** | `RLDNR` | Target General Ledger (`0L` Leading Ledger) |
| **Company Code** | `RBUKRS` | Legal Entity identifier (`1000`) |
| **Fiscal Year / Period** | `GJAHR` / `POPER` | Fiscal Year (2026) and Period (`001` - `016`) |
| **Document Number** | `BELNR` | Accounting document number |
| **Line Item** | `DOCLN` | 6-digit line item sequence (`000001`, `000002`) |
| **Doc / Local / Group Amounts** | `WSL` / `HSL` / `KSL` | Triple-valuation amounts in `decimal128(18, 2)` |
| **Currencies** | `RWCUR` / `RHCUR` / `RKCUR` | Transaction, Local, and Group currency codes |
| **Controlling Objects** | `RCNTR` / `PRCTR` | Cost Center (`KOSTL`) and Profit Center (`PRCTR`) |
| **Segment Reporting** | `SEGMENT` | IFRS 8 / ASC 280 Operating Segment |
| **Functional Area** | `FKBER` | Cost of Sales Functional Area (`FA_OPS`, `FA_ADMIN`) |
| **Ground-Truth Flags** | `IS_ANOMALY` / `ANOMALY_IDS` | ML training labels and anomaly IDs |

---

## Double-Entry Mathematical Invariant Gate

Unlike simplistic random generators that use IEEE 754 floating-point numbers (`float64`), this engine enforces **Python `Decimal` cent-level quantization (`ROUND_HALF_UP`)** across all transactions.

$$\sum_{i=1}^{N_{\text{debits}}} \text{Debit}_i - \sum_{j=1}^{M_{\text{credits}}} \text{Credit}_j \equiv 0.00$$

- **Parquet Export Precision**: Columns utilize PyArrow `pa.decimal128(18, 2)` to eliminate precision degradation when saved to disk.
- **Automated Invariant Gate**: Every batch passes through `InvariantVerifier` prior to export. If a single entry deviates by even $\$0.01$, the pipeline aborts immediately.
- **Multi-Currency Invariant Gate**: Validates `is_balanced_local` and `is_balanced_group` to guarantee that international currency conversion legs do not leak fractional pennies.
- **Streaming Zero-OOM Engine**: `ChunkedSynthesisEngine` and `StreamingParquetExporter` stream multi-million-row datasets sequentially in configurable row-group chunks to disk with zero memory leaks.

---

## Dual Graphical User Interfaces

The project includes two complete graphical user interfaces tailored for developers, data scientists, and forensic auditors:

### 1. Modern Web GUI
- **Stack**: Pure Python built-in HTTP server (`http.server`), Tailwind CSS, and Chart.js.
- **Endpoints**: Interactive endpoints for `/api/generate`, `/api/audit`, `/api/fuzz-loop`, and `/api/tax-report`.
- **Features**:
  - Live **Zero-Sum Balance Monitor Badge**.
  - **Quick Start Presets**: *Standard Benchmark*, *Quick Smoke Test*, *Forensic Stress*, *Clean Baseline*.
  - **Interactive Voucher Explorer**: Search, filter, and inspect debit/credit line items and counterparty IDs.
  - **SOX-404 Screening Center**: Visual Benford curve comparison chart, DOA cluster breakdowns, off-hours distribution, and intercompany loops.
  - **One-Click Downloads**: Direct browser downloads for Parquet, CSV, SAP BSEG/BKPF, **SAP S/4HANA ACDOCA (Parquet & CSV)**, and JSON manifests.

### 2. Native Windows Desktop GUI (Offline Tkinter v0.3)
- **Stack**: Native Python `tkinter` and `ttk` with styled widgets.
- **100% Offline**: Operates completely disconnected from the internet.
- **Thread-Safe**: Background worker execution with synchronized state locking.
- **5 Dedicated Workspaces**:
  1. *⚙️ 1. Synthesis & Generation*: Sliders, anomaly toggles, tax jurisdiction, withholding tax, and subledger matching toggles.
  2. *📑 2. Voucher & Ledger Explorer*: Paginated table with drilldown into debit/credit line items.
  3. *🛡️ 3. SOX-404 Forensic Audit*: Diagnostic cards with status badges and forensic findings.
  4. *📦 4. Export & Artifacts*: Target folder picker, format descriptions, and direct file opener.
  5. *⚡ 5. Enterprise & Dynamic Fuzzing*: Dynamic security fuzzing campaigns (Mock ERP vs SQLite ACID target), statutory tax return computation, and live ERP connector probing.

---

## Quick Start & One-Click Launchers

### Option A: Double-Click Launcher (Windows)
Double-click **`run.bat`** in the project root:
```
===============================================================================
              SYNTHETIC GENERAL LEDGER (GL) FUZZER
       Double-Entry Accounting Synthesis & Calibrated Anomaly Studio
            Made with ❤️ by Atiqul-Akash | GitHub: Atiqul-Akash
===============================================================================

  [1] Modern Web GUI (Recommended - Browser at http://localhost:8080)
  [2] Native Windows Desktop GUI (Offline Window)
  [3] Generate Synthetic Dataset (CLI - 1,000 entries)
  [4] Run SOX-404 Forensic Audit on Generated Dataset
  [5] Run Complete Automated Test Suite (150 tests)
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
# 1. Standard Dataset Generation
python -m gl_fuzzer.cli generate --count 5000 --anomaly-rate 0.05 --out-dir ./output --export-formats parquet,csv,sap

# 2. Enterprise Synthesis: ACDOCA + Multi-Currency + Subledgers + Tax Engine
python -m gl_fuzzer.cli generate --count 10000 --anomaly-rate 0.05 --acdoca --multi-currency --seasonality --tax-jurisdiction EU_DE --enable-wht --enable-subledgers --out-dir ./enterprise_output

# 3. Dynamic Security Fuzzing Feedback Campaign
python -m gl_fuzzer.cli fuzz-loop --iterations 5 --count 50 --target mock --out-dir ./fuzz_reports

# 4. Multi-Jurisdictional Statutory Tax Return Report
python -m gl_fuzzer.cli tax-report --dataset ./enterprise_output/acdoca_feed.parquet --jurisdiction EU_DE --period 2026-Q1

# 5. Real-Time Event Streaming Feed (Kafka / Kinesis / EventHub)
python -m gl_fuzzer.cli stream-feed --sink kafka --count 500 --topic gl.transactions.v1 --format cloudevents

# 6. Verify Double-Entry Balance and Manifest Integrity
python -m gl_fuzzer.cli verify --dataset ./output/gl_feed.parquet --manifest ./output/ground_truth_manifest.json

# 7. Run Automated SOX-404 Forensic Audit Screening
python -m gl_fuzzer.cli audit-report --dataset ./enterprise_output/acdoca_feed.parquet --manifest ./enterprise_output/ground_truth_manifest.json

# 8. Benchmark Generation and Fuzzing Throughput
python -m gl_fuzzer.cli benchmark --count 10000 --anomaly-rate 0.05

# 9. Launch Graphical Interfaces
python -m gl_fuzzer.cli gui --port 8080          # Web GUI
python -m gl_fuzzer.cli gui --mode desktop      # Desktop GUI
```

---

## Dual-Artifact Export Formats

Generated datasets are exported with full audit trail documentation:

1. **SAP S/4HANA Universal Journal (`acdoca_feed.parquet` & `acdoca_feed.csv`)**: 50+ enterprise dimension ACDOCA table formatted with `decimal128(18, 2)` Snappy compression and CSV.
2. **Parquet Feed (`gl_feed.parquet`)**: High-performance columnar storage using `decimal128(18, 2)` for amounts and Snappy compression.
3. **CSV Feed (`gl_feed.csv`)**: RFC-4180 compliant tabular ledger format.
4. **SAP ERP Standard Tables**:
   - **`BKPF.csv`**: SAP Accounting Document Header (`BUKRS`, `BELNR`, `GJAHR`, `BLART`, `BLDAT`, `BUDAT`, `USNAM`, `XBLNR`, `BKTXT`).
   - **`BSEG.csv`**: SAP Accounting Document Line Item Segment (`BUKRS`, `BELNR`, `GJAHR`, `BUZEI`, `BSCHL`, `SHKZG`, `HKONT`, `WRBTR`, `WAERS`, `KOSTL`, `PRCTR`, `LIFNR`, `KUNNR`, `VBUND`, `SGTXT`).
5. **Ground-Truth Audit Manifest (`ground_truth_manifest.json` & `.parquet`)**: Complete mapping of every injected anomaly, affected document numbers, line items, mathematical parameters, and forensic signals.
6. **Cryptographic SHA-256 Digest (`.sha256`)**: Detached checksums verifying dataset integrity.

---

## Automated Forensic Audit Screening (SOX-404)

The framework includes built-in detection algorithms evaluating datasets against SOX-404 compliance rules:

- **Benford's Law Chi-Square Test**: Calculates $\chi^2 = \sum \frac{(O_i - E_i)^2}{E_i}$ against expected $\log_{10}(1 + 1/d)$ frequencies ($\alpha = 0.05$, Critical Value = $15.51$).
- **DOA Split Approval Clustering**: Sliding temporal window identifying multiple invoices under $\$10,000$ to the same vendor within 48 hours.
- **Off-Hours Detection**: Filters manual entries posted between 02:00 and 04:30 AM, or during weekend cycles by non-standard users.
- **Topological Pairing Inspector**: Flags forbidden bipartite subledger bypasses (e.g. Operating Expense directly offsetting Cash).
- **Intercompany Cycle Detection**: Depth-First Search (DFS) on directed subsidiary trading graphs to uncover circular volume-inflation loops.
- **Withholding Tax Evasion Detection**: Identifies qualifying disbursements ($\ge \$500$) omitting statutory WHT deduction account `22200`.
- **Phantom PO 3-Way Match Bypass**: Detects vendor invoices cleared without corresponding Goods Receipt (`WE`) vouchers.
- **Inventory Shrinkage Concealment**: Catches unauthorized stock write-offs credited into suspense (`99999`) or retained earnings (`33000`).
- **Streaming Feed Replay Detection**: Identifies duplicated document identifiers or replayed transactions across event stream feeds.

---

## Automated Test Suite

The codebase features an extensive test suite with **150 automated unit, regression, and integration tests achieving 100% pass rate**:

```bash
python -m pytest -v
```

```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\PROJECT\PYTHON
configfile: pyproject.toml
collected 150 items

tests/test_acdoca.py ....                                                [  2%]
tests/test_anomalies.py ......                                           [  6%]
tests/test_audit_metrics.py .....                                        [ 10%]
tests/test_cli.py ...                                                    [ 12%]
tests/test_coa_models.py ...                                             [ 14%]
tests/test_connectors.py ..............                                  [ 23%]
tests/test_cycles.py ....                                                [ 26%]
tests/test_edge_cases.py ............                                    [ 34%]
tests/test_exporters.py ....                                             [ 36%]
tests/test_forensic_ext.py .........                                     [ 42%]
tests/test_fuzzing.py ..........                                         [ 49%]
tests/test_generators.py ....                                            [ 52%]
tests/test_gui.py ........                                               [ 57%]
tests/test_invariants.py ....                                            [ 60%]
tests/test_macro_calendar.py .....                                       [ 63%]
tests/test_models.py ...........                                         [ 70%]
tests/test_multi_currency.py ........                                    [ 76%]
tests/test_streaming.py .....                                            [ 79%]
tests/test_streaming_sinks.py .........                                  [ 85%]
tests/test_subledgers.py .........                                       [ 91%]
tests/test_tax.py .............                                          [100%]

============================= 150 passed in 3.25s =============================
```

---

## Repository Structure

```
Synthetic-General-Ledger-Fuzzer/
├── gl_fuzzer/
│   ├── __init__.py                # Package root (v0.3.0 Enterprise)
│   ├── cli.py                     # Typer / Rich command-line interface
│   ├── web_gui.py                 # Modern browser dashboard with ACDOCA cards & endpoints
│   ├── desktop_gui.py             # Native offline Tkinter v0.3 GUI (5 tabs, Thread-safe)
│   ├── connectors/                # [Pillar 1] Stateful Bidirectional ERP Connectors
│   │   ├── base.py                # Abstract ERPConnector & Pydantic sync models
│   │   ├── mock_erp.py            # Offline simulated ERP database & sandbox fallback
│   │   ├── odata_connector.py     # SAP S/4HANA OData V4 client (API_JOURNALENTRYCREATEREQUEST)
│   │   ├── rfc_connector.py       # SAP NetWeaver RFC interface (RFC_READ_TABLE, BAPI)
│   │   └── oracle_connector.py    # Oracle Fusion Cloud Financials REST API connector
│   ├── tax/                       # [Pillar 2] Multi-Jurisdictional Tax Engine
│   │   ├── models.py              # TaxLine, TaxResult, TaxReturnSummary models
│   │   ├── us_sales_tax.py        # US 50-State nexus, resale exemption, use tax accrual
│   │   ├── eu_vat.py              # EU 27-State VAT, UK HMRC VAT, Reverse Charge wash
│   │   ├── withholding.py         # Statutory Withholding Tax (TDS Section 194C/J)
│   │   └── engine.py              # TaxLocalizationEngine facade & tax return generator
│   ├── fuzzing/                   # [Pillar 3] Dynamic Security Fuzzing Feedback Loop
│   │   ├── target.py              # Target application & database abstractions
│   │   ├── mock_app.py            # Simulated ERP target with 10+ business posting rules
│   │   ├── sql_target.py          # SQLite relational target with ACID constraints
│   │   ├── oracle.py              # Crash monitor, coverage oracle, vulnerability findings
│   │   └── adaptive_fuzzer.py     # Adaptive mutators, feedback reinforcement, campaign runner
│   ├── subledgers/                # [Pillar 4] Operational Logistics & Stateful Subledgers
│   │   ├── inventory.py           # Material Master, moving average price (MAP), bin stock
│   │   ├── three_way_match.py     # 3-Way Match (PO -> GR/WE -> IR/RE), price variance (PPV)
│   │   └── order_fulfillment.py   # Sales Order fulfillment, delivery (GI/WA), COGS calculation
│   ├── streaming/                 # [Pillar 5] Real-Time Event Streaming Sinks
│   │   ├── base.py                # Abstract GLStreamPublisher & StreamPublishResult
│   │   ├── serializers.py         # JSON, CloudEvents v1.0, and SAP ACDOCA serializers
│   │   ├── kafka_publisher.py     # Apache Kafka publisher & EmbeddedKafkaBroker fallback
│   │   └── cloud_publishers.py    # AWS Kinesis & Azure Event Hubs publishers
│   ├── models/                    # Foundational Accounting Models
│   │   ├── coa.py                 # Chart of Accounts, Account, NormalBalance, Contra-Asset
│   │   ├── journal.py             # LineItem, JournalEntry, Batch (Multi-currency balance)
│   │   ├── currency.py            # Currency enum (12 currencies) & ExchangeRateProvider
│   │   └── manifest.py            # AnomalyRecord, GroundTruthManifest, SOXControlRef
│   ├── generators/                # Core Synthesis Generators
│   │   ├── distributions.py       # Benford, LogNormal, BusinessCalendar sampling
│   │   ├── macro_calendar.py      # Macro-economic calendar & quarterly seasonality
│   │   ├── streaming_engine.py    # Chunked synthesis engine (Zero-OOM, streaming hook)
│   │   ├── p2p_cycle.py           # Procure-to-Pay generator (WE, KR, RE, KZ payment)
│   │   ├── o2c_cycle.py           # Order-to-Cash generator (WA, DR, DZ, single customer)
│   │   ├── r2r_cycle.py           # Record-to-Report (Depreciation, Payroll, Accrual)
│   │   └── base_engine.py         # Master synthesis engine with dependency injection
│   ├── anomalies/                 # Calibrated Micro-Anomaly Library
│   │   ├── base_mutator.py        # Abstract base class for mutators
│   │   ├── smurfing.py            # Split approval DOA bypass
│   │   ├── ghost_entries.py       # Off-hours and weekend MJEs
│   │   ├── benford_skew.py        # First-digit distribution skewing
│   │   ├── anomalous_pairings.py  # Suspense & prohibited offset pairings
│   │   ├── round_tripping.py      # Intercompany circular transfer cycles
│   │   └── pipeline.py            # Anomaly orchestration pipeline
│   ├── verification/              # Invariant & Audit Verification
│   │   ├── invariants.py          # Strict double-entry balance verifier (Doc, Local, Group)
│   │   └── audit_metrics.py       # SOX-404 automated audit detection (9 forensic methods)
│   └── exporters/                 # Output Deliverable Exporters
│       ├── parquet_exporter.py    # PyArrow Decimal128 Parquet exporter
│       ├── streaming_parquet.py   # Zero-OOM streaming row-group Parquet writer
│       ├── acdoca_exporter.py     # SAP S/4HANA Universal Journal 50+ column exporter
│       ├── csv_exporter.py        # RFC 4180 CSV exporter (None-safe)
│       ├── sap_bseg_exporter.py   # SAP BKPF / BSEG table exporter
│       └── manifest_exporter.py   # JSON & Parquet ground-truth manifest exporter
├── tests/                         # 150 automated unit, regression, and integration tests
├── pyproject.toml                 # Project configuration, dependencies, and v0.3.0 metadata
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
