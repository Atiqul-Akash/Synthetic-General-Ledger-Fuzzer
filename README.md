# Synthetic General Ledger Fuzzer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
  <img src="https://img.shields.io/badge/Tests-294%20Passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="294 Tests Passed" />
  <img src="https://img.shields.io/badge/Version-0.6.0%20Enterprise-blueviolet?style=for-the-badge" alt="v0.6.0 Enterprise" />
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
- [Enterprise Architecture](#enterprise-architecture)
- [Five Enterprise Architectural Pillars](#five-enterprise-architectural-pillars)
  - [1. Stateful, Bidirectional ERP Synchronization](#1-stateful-bidirectional-erp-synchronization)
  - [2. Multi-Jurisdictional Tax Localization Engine](#2-multi-jurisdictional-tax-localization-engine)
  - [3. Dynamic Security Fuzzing Feedback Loop](#3-dynamic-security-fuzzing-feedback-loop)
  - [4. Operational Logistics & Stateful Subledgers](#4-operational-logistics--stateful-subledgers)
  - [5. Real-Time Event Streaming Sinks](#5-real-time-event-streaming-sinks)
- [Five Advanced Architectural Frontiers](#five-advanced-architectural-frontiers)
  - [1. Automated Remediation Oracles & Healing Loop](#1-automated-remediation-oracles--healing-loop)
  - [2. Multi-Stage Financial APT Campaign Orchestration](#2-multi-stage-financial-apt-campaign-orchestration)
  - [3. Deep Master Data Management (MDM) Integrity & Sybil Fuzzing](#3-deep-master-data-management-mdm-integrity--sybil-fuzzing)
  - [4. Unstructured Financial Context & Multimodal Artifacts](#4-unstructured-financial-context--multimodal-artifacts)
  - [5. Turnkey Infrastructure Orchestration & CLI Cluster Management](#5-turnkey-infrastructure-orchestration--cli-cluster-management)
- [Autonomous Generative LLM Fraud Agent Framework](#autonomous-generative-llm-fraud-agent-framework)
- [Legacy Mainframe & Supply Chain EDI Protocol Engine](#legacy-mainframe--supply-chain-edi-protocol-engine)
- [Enterprise Simulation & Realism Frontiers (v0.6)](#enterprise-simulation--realism-frontiers-v06)
  - [1. Balance Sheet Subledgers (Fixed Assets IAS 16/36, Treasury IFRS 9 & FAGL_FCV FX Revaluation)](#1-balance-sheet-subledgers-fixed-assets-ias-1636-treasury-ifrs-9--fagl_fcv-fx-revaluation)
  - [2. High-Performance Multi-Core Parallel Engine](#2-high-performance-multi-core-parallel-engine)
  - [3. Generative Tabular Machine Learning](#3-generative-tabular-machine-learning)
  - [4. Multi-ERP Master Schemas (Workday, D365, NetSuite, Oracle Cloud)](#4-multi-erp-master-schemas)
  - [5. Cryptographic Triple-Entry & DLT Consensus Drivers](#5-cryptographic-triple-entry--dlt-consensus-drivers)
  - [6. Coupled Hawkes Point Process Lead-Time Generator](#6-coupled-hawkes-point-process-lead-time-generator)
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
  - [2. Native Windows Desktop GUI (Offline Tkinter 8-Tab Interface)](#2-native-windows-desktop-gui)
- [Quick Start & One-Click Launchers](#quick-start--one-click-launchers)
- [CLI Reference](#cli-reference)
- [Dual-Artifact Export Formats](#dual-artifact-export-formats)

- [Automated Forensic Audit Screening (SOX-404)](#automated-forensic-audit-screening)
- [Automated Test Suite (294 Tests)](#automated-test-suite)
- [Repository Structure](#repository-structure)
- [Contributing & License](#contributing--license)


---

## Executive Summary

Building enterprise fraud-detection models, validating accounting automation systems, and auditing ERP integrity faces a notorious **cold-start dilemma**: real-world general ledger transaction feeds containing verified financial crimes or edge cases are confidential, legally restricted, and exceptionally rare.

The **Synthetic General Ledger Fuzzer (v0.6.0 Enterprise)** bridges this gap by providing an end-to-end framework capable of:
1. **Mathematical Invariant Rigor**: Every synthesized transaction voucher strictly enforces $\sum \text{Debits} \equiv \sum \text{Credits}$ across document, functional/local, and group consolidation currencies at exact cent precision (`Decimal("0.01")`).
2. **Stateful ERP Interoperability**: Bi-directionally reads master data and balances from live or simulated SAP S/4HANA (OData V4, NetWeaver RFC) and Oracle Fusion Cloud REST environments.
3. **Multi-Jurisdictional Tax Compliance**: Evaluates nexus, VAT reverse charges, and statutory withholding taxes across 50 US states, 27 EU member nations, the UK HMRC, and India TDS.
4. **Dynamic Security Auditing**: Employs adaptive grammar-based mutators, crash monitoring, and coverage oracles to fuzz relational databases and ERP API endpoints.
5. **Operational Subledger Integrity**: Simulates warehouse inventory stock, Moving Average Price (MAP) updates, and 3-Way Matching (PO $\rightarrow$ Goods Receipt $\rightarrow$ Invoice Receipt).
6. **Real-Time Streaming**: Directly streams double-entry journal events to Apache Kafka, AWS Kinesis, and Azure Event Hubs with CloudEvents v1.0 compliance.

---

## Enterprise Architecture (v0.4)

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

## Five Enterprise Architectural Pillars (v0.4)

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

## Five Advanced Architectural Frontiers

Beyond the core pillars, the fuzzer introduces five cutting-edge enterprise capabilities addressing real-world corporate defense, multi-quarter adversarial persistent threats, master data compromise, unstructured document cross-checks, and turnkey cluster orchestration:

### 1. Automated Remediation Oracles & Healing Loop
*Package: `gl_fuzzer/remediation/`*

Closes the audit loop by providing defense-side automated repair:
- **Remediation Advisor (`engine.py`)**: Translates exposed vulnerabilities into concrete, deployable defenses:
  - **SAP S/4HANA Validation & Substitution Rules (`GGB0`)**: Generates exact prerequisite/check syntax (e.g. blocking vendor payments $\ge \$500.00$ lacking statutory withholding tax).
  - **SAP NetWeaver ABAP BAdIs (`BADI_ACC_DOCUMENT`)**: Produces type-checked ABAP enhancement implementations (e.g. enforcing 3-way match Goods Receipt verification prior to invoice clearing).
  - **Relational SQL Constraints**: Emits DDL check constraints (`CHECK (amount > 0 AND ...)`) neutralizing balance or injection attacks.
  - **SOX-404 Compensating Controls**: Formal internal control narratives (ID, frequency, review procedure, audit evidence required).
- **Closed-Loop Healing Runner (`healing_loop.py`)**: Re-runs the exploit generator against simulated patched environments to programmatically verify that the attack vector is neutralized without introducing regressions.

### 2. Multi-Stage Financial APT Campaign Orchestration
*Package: `gl_fuzzer/campaigns/`*

Real-world corporate financial crimes are coordinated, multi-quarter conspiracies rather than isolated events:
- **Narrative Orchestrator (`orchestrator.py`)**: Coordinates multi-phase adversarial campaigns across 4 sequential fiscal quarters:
  - **Phase 1: Infiltration & Seeding**: Unauthorized micro-adjustments or small test transactions.
  - **Phase 2: Staging & Manipulation**: Material Moving Average Price (MAP) creep, phantom inventory accumulation, or threshold smurfing.
  - **Phase 3: Laundering & Capital Transfer**: Cross-company transfers through Special Purpose Vehicles (SPVs) or offshore shell entities.
  - **Phase 4: Year-End Concealment**: Washing illicit balances into suspense accounts (`99999`) or write-downs just before annual audit close.
- **Narrative Templates**:
  - `INVENTORY_MAP_CREEP_AND_OBSOLESCENCE`: Plant controller gradually inflates unit costs, creating fictitious asset value before booking year-end write-offs.
  - `ENRON_SPV_ROUND_TRIPPING`: Circular multi-hop intercompany transfers (`A -> B -> C -> A`) to fabricate operational revenue.
  - `EXECUTIVE_DOA_SMURFING_WITH_KICKBACK`: Coordinated invoice splitting under approval thresholds coupled with vendor kickbacks.
- **Invariant Integrity**: All campaign vouchers strictly adhere to zero-sum double-entry balance across all 3 currency legs.

### 3. Deep Master Data Management (MDM) Integrity & Sybil Fuzzing
*Package: `gl_fuzzer/mdm/`*

Detects and injects stealthy compromises residing in enterprise master registries before transactional postings occur:
- **Master Data Manager (`engine.py`)**: Unified registry managing Vendor Master, Customer Master, and Employee Master records.
- **Master Data Mutation Operators (`mutators.py`)**:
  - **Sybil Vendor Clones (`VendorSybilMutator`)**: Injects near-duplicate vendor entities with shifted corporate suffixes (`"Logistics LLC"` $\leftrightarrow$ `"Logistics Corp"`) and mutated tax IDs.
  - **24–48h Pre-Disbursement Bank Routing Tampering (`BankRoutingTamperingMutator`)**: Simulates insider or compromised credential attacks where bank routing/account numbers are updated immediately prior to automated payment runs (`F110`).
  - **Employee-Vendor Collusion (`EmployeeVendorCollusionMutator`)**: Establishes clandestine ties between internal employees and external vendors (identical bank accounts or physical street addresses).
- **Integrity Screening**: Evaluates Levenshtein/SequenceMatcher fuzzy name similarity, detects bank routing update temporal proximity, and performs bipartite graph matching across employee and vendor directories.

### 4. Unstructured Financial Context & Multimodal Artifacts
*Package: `gl_fuzzer/documents/`*

Financial forensics requires verifying structured ledger vouchers against their corresponding unstructured source documents:
- **Zero-Dependency PDF 1.4 Generator (`pdf_generator.py`)**: A pure-Python binary PDF serialization engine that builds valid, renderable PDF invoices with itemized tables, corporate headers, subtotal/tax calculations, and vector rules—with zero external C-libraries or system packages.
- **Corporate Approval Email Chains (`email_generator.py`)**: Generates compliant RFC-2822 `.eml` and text email threads simulating urgent CFO/controller override approvals and audit paper trails.
- **Multimodal Mismatch Injector (`mismatch_injector.py`)**: Synchronizes PDF invoices with structured GL journal entries and injects multimodal discrepancies:
  - **OCR Amount Mismatches**: PDF invoice states a different amount than booked in the general ledger.
  - **IBAN/Routing Divergence**: PDF displays legitimate vendor payment instructions while structured payment vouchers route funds to an unauthorized account.
  - **Audit Detection**: Evaluated via `ForensicAuditEvaluator.detect_multimodal_document_mismatches`.

### 5. Turnkey Infrastructure Orchestration & CLI Cluster Management
*Package: `docker/`, `docker-compose.yml`, `cli.py`*

Deploy full-scale enterprise simulation sandboxes with a single command:
- **Docker Compose Stack (`docker-compose.yml`)**:
  - **Redpanda Kafka**: Ultra-fast Kafka-compatible streaming message broker in KRaft mode (no Zookeeper required).
  - **Mock SAP S/4HANA OData Gateway**: Lightweight Python container exposing live `/health`, `/sap/opu/odata4/.../JournalEntry`, and CSRF token endpoints.
  - **LocalStack**: Local AWS Kinesis simulation.
  - **GL-Fuzzer Worker**: Pre-configured container for streaming ingestion.
- **CLI Cluster Management**:
  - `gl-fuzzer cluster status`: Real-time socket and HTTP probing of all streaming and ERP services.
  - `gl-fuzzer cluster probe`: Validates OData, RFC, and Kafka broker endpoints.
  - `gl-fuzzer cluster start | stop`: Launches or tears down the Docker Compose environment.

---

## Autonomous Generative LLM Fraud Agent Framework
*Package: `gl_fuzzer/agents/`*

Simulates high-fidelity conversational social engineering scripts, pretexting, and objection handling that accompany modern financial crimes. Operates **100% offline with zero external dependencies** via a built-in `HeuristicGenerativeEngine`, while providing pluggable adapters for cloud LLMs (OpenAI, Anthropic, Gemini, Ollama) via standard Python `urllib.request`.

- **Autonomous Personas (`gl_fuzzer/agents/engine.py`)**:
  - `ExecutivePretextAgent`: Simulates C-suite executive coercion targeting Accounts Payable analysts to bypass SOX-404 dual signoff (e.g. Project Apollo confidential stealth acquisition, board emergency resolution).
  - `CollusiveVendorAgent`: Simulates vendor social engineering (e.g. urgent remittance banking changes before payment cutoffs, corporate reorganization pretext, shipment hold threats).
  - `AuditorDeceptionAgent`: Crafts deceptive technical accounting memos explaining away suspicious suspense balance debits (`99999`) and timing variances under ASC 815 / ASC 250 rules.
- **Multi-Turn Dialogue Simulation (`MultiTurnDialogueSimulator`)**:
  - Engages skeptical AP clerks across 4+ turns.
  - Dynamically responds to procedural objections (e.g. dual signature mandates, verbal callback requirements, missing Purchase Orders) by deploying calibrated psychological manipulation levers (`AUTHORITY`, `URGENCY`, `CONFIDENTIALITY`, `SCARCITY`, `SOCIAL_PROOF`, `TECHNICAL_OBFUSCATION`).
- **RFC-2822 Forensic Email Serialization**:
  - Automatically serializes full multi-turn conversational threads into forensic `.eml` format with proper `Message-ID`, `In-Reply-To`, `References`, and nested quoted history headers.

---

## Legacy Mainframe & Supply Chain EDI Protocol Engine
*Package: `gl_fuzzer/legacy_protocols/`*

Enterprise supply chains and core banking infrastructure often rely on decades-old protocols that modern API fuzzers cannot test. The Legacy Protocol Engine provides comprehensive serialization, format parsing, and security fuzzing across legacy enterprise standards:

- **Supply Chain EDI Protocols (`edi_engine.py`)**:
  - **ANSI X12**: Full standard serialization for **810 (Commercial Invoice)**, **850 (Purchase Order)**, and **856 (Ship Notice / ASN)** with valid `ISA`, `GS`, `ST`, `BIG`/`BEG`/`BSN`, `IT1`/`PO1`, `TDS`, `CTT`, `SE`, `GE`, `IEA` envelopes.
  - **UN/EDIFACT**: Full standard serialization for **INVOIC (D.96A)** and **ORDERS** with `UNA`, `UNB`, `UNH`, `BGM`, `DTM`, `NAD`, `LIN`, `QTY`, `PRI`, `MOA`, `UNT`, `UNZ` segments.
- **IBM Mainframe & COBOL Layouts (`mainframe_engine.py`)**:
  - **COBOL Copybook 80-Column**: Fixed-width 80-character punched-card layout format (`PIC 9(6)`, `PIC X(10)`, `PIC 9(8)`, `PIC 9(10)V99`).
  - **COBOL Copybook 132-Column**: Fixed-width 132-character line printer ledger report layout.
  - **IBM Mainframe EBCDIC Binary (CP037)**: 32-byte binary records encoded in native IBM EBCDIC `cp037` code page with packed decimal **COMP-3** amount fields (odd/even digit support with standard `0xC` positive / `0xD` negative sign nibbles).
- **Core Banking Interchange Protocols**:
  - **NACHA ACH**: Strict 94-character fixed-width US banking batch format across record types `1` (File Header), `5` (Batch Header), `6` (Entry Detail), `8` (Batch Control), and `9` (File Control) with mathematical **Entry Hash** verification and **Block-10** padding (`9999...`).
  - **BAI2**: Cash Management Account Statement records (`01`, `02`, `03`, `16`, `49`, `98`, `99`).
  - **SWIFT MT940**: Customer Statement Message with `:20:`, `:25:`, `:28C:`, `:60F:`, `:61:`, `:86:`, and `:62F:` balance reconciliation tags.
- **Protocol-Level Fuzzing & Mutation (`EDIMutator`, `MainframeMutator`)**:
  - `DELIMITER_CORRUPTION`: Swaps or inverts element separators (`*` $\rightarrow$ `:`) and segment terminators (`~` $\rightarrow$ `^`).
  - `ENVELOPE_TRUNCATION`: Drops trailer control envelopes (`IEA`, `UNZ`, Record `9`).
  - `SEGMENT_COUNT_DESYNC`: Corrupts count fields in `SE`, `UNT`, and NACHA control records.
  - `BUFFER_OVERFLOW`: Injects multi-kilobyte overflow strings into constrained fixed fields.
  - `EBCDIC_SIGN_CORRUPTION`: Flips COMP-3 packed decimal sign nibbles to invalid hexadecimal values.
  - `HASH_TOTAL_DESYNC`: Modifies routing transit entry hashes to trigger bank clearing rejection.
  - `FIXED_WIDTH_OVERFLOW`: Violates strict 80-char or 94-char fixed-width buffer boundaries.
  - `NULL_BYTE_INJECTION`: Injects raw `0x00` null bytes into payload streams.

---

## Enterprise Simulation & Realism Frontiers (v0.6)

### 1. Balance Sheet Subledgers (Fixed Assets IAS 16/36, Treasury IFRS 9 & FAGL_FCV FX Revaluation)
*Package: `gl_fuzzer/subledgers/` (`fixed_assets.py`, `treasury.py`, `fx_revaluation.py`)*

Expands beyond operational supply chain subledgers into long-term balance sheet cycles:
- **Fixed Asset Life Management (`FixedAssetSubledger`)**:
  - Full support for **IAS 16 Property, Plant & Equipment** and **IFRS 16 Leases** (Right-of-Use assets).
  - Multiple depreciation engines: **Straight-Line (SL)**, **Double Declining Balance (DDB)**, **Units of Production (UOP)**, and multi-component depreciation with mid-life switches.
  - **IAS 36 Impairment Testing**: Continuous testing against recoverable amount ($\max(\text{FVLCTS}, \text{VIU})$) with automated balanced write-downs (`Dr 65100 / Cr 17800`).
  - **Capitalization Threshold Guard**: Automatically expenses purchases below threshold (default: \$2,500) directly to operating expenses (`69000`).
  - **Multi-Asset Retirement & Derecognition**: Computes exact gain or loss on asset disposal with derecognition of gross cost and accumulated depreciation/impairment.
  - **IAS 16.31 Revaluation Model**: Revalues carrying values to fair value with balanced equity credit to revaluation surplus (`31000`).
  - **Calibrated Fraud Mutators**: `ImpairmentOmissionMutator` (write-down suppression), `ZombieAssetMutator` (depreciating scrapped assets), `CapitalizationThresholdEvasionMutator` (smurfing cap-ex below threshold).
- **Treasury & Debt Facilities (`TreasurySubledger`)**:
  - Models corporate bonds, syndicated loans, commercial paper, and revolving credit facilities.
  - **IFRS 9 / ASC 835 Amortized Cost Engine**: Computes exact Effective Interest Rate (EIR) amortizations with balanced vouchers for discount accretion / premium amortization.
  - **Continuous Debt Covenant Monitoring**: Real-time evaluation of Leverage Ratio ($\text{Debt}/\text{EBITDA} \le 4.5\times$), Interest Coverage ($\text{EBIT}/\text{Interest} \ge 3.0\times$), and Debt-to-Equity ($\le 2.0\times$).
  - **Derivative Hedging (IAS 39 / IFRS 9)**: Fixed-for-floating Interest Rate Swaps (IRS), Fair Value Hedges (P&L), and Cash Flow Hedges (OCI vs P&L ineffectiveness splits).
  - **Calibrated Fraud Mutators**: `CovenantSuppressionMutator` (debt-to-equity reclass), `HedgeIneffectivenessConcealment` (hiding ineffectiveness in OCI), `DebtRolloverConcealment` (hiding short-term debt maturity).
- **Month-End Unrealized Foreign Exchange Revaluation (`FXRevaluationEngine` / FAGL_FCV)**:
  - Automates **ASC 830 / IAS 21** foreign currency revaluations on open Accounts Payable (`20000`) and Accounts Receivable (`11000`) open items.
  - Compares historical transaction spot rates against period-end closing spot rates from `ExchangeRateProvider`.
  - Books balanced unrealized P&L entries: **Unrealized FX Gain** (`71000`) or **Unrealized FX Loss** (`72000`) paired with balance sheet adjustment accounts (`11900` / `21900`).
  - Automatically schedules Day-1 subsequent month reversal vouchers ensuring zero net distortion on settled operational cash flows.

---

### 2. High-Performance Multi-Core Parallel Engine
*Package: `gl_fuzzer/generators/parallel_engine.py`*

Bypasses Python's Global Interpreter Lock (GIL) to saturate all CPU cores for high-volume enterprise dataset generation:
- **`MultiCoreSynthesisEngine`**:
  - Leverages `concurrent.futures.ProcessPoolExecutor` with automatic CPU core detection (`os.cpu_count()`).
  - Windows `spawn`-safe architecture using disjoint deterministic seeds per worker process (`seed + worker_id * 1_000_000`).
  - Generates partitioned PyArrow Parquet files directly from worker processes for zero-copy streaming disk I/O.
  - Near-linear throughput speedup ($3.5\times$ to $9\times$ scaling on modern multi-core workstations).

---

### 3. Generative Tabular Machine Learning
*Package: `gl_fuzzer/ml_generative/` (`gaussian_copula.py`, `tvae_engine.py`)*

Replaces rigid template generation with generative AI models that learn empirical joint distributions of corporate ledgers:
- **Tier 1: Gaussian Copula Synthesizer (`GaussianCopulaSynthesizer`)**:
  - Zero-dependency architecture powered by `scipy.stats` and `numpy`.
  - Estimates empirical marginal CDFs via Probability Integral Transform (PIT) and maps features to standard normal scores $\Phi^{-1}(U)$.
  - Models multivariate dependencies through covariance matrix $\Sigma$ with Tikhonov regularization.
  - **Latent Manifold Perturbation**: Perturbs normal scores into low-density tail regions ($\|Z\| > 2.5\sigma$) to synthesize subtle, organic multi-dimensional fraud patterns that evade traditional 1D threshold rules.
- **Tier 2: Tabular Variational Autoencoder (`TabularVAESynthesizer`)**:
  - Pure NumPy implementation of TVAE with dense encoder $q_\phi(z|x)$, reparameterization trick $z = \mu + \sigma \odot \epsilon$, and decoder $p_\theta(x|z)$.
  - Analytical backpropagation and Adam optimizer in pure NumPy.
  - Synthesizes non-linear, adversarial ledger vouchers from boundary latent manifolds.

---

### 4. Multi-ERP Master Schemas
*Package: `gl_fuzzer/exporters/`*

Generates native, compliant import payloads for all major enterprise ERP systems:
- **Workday Accounting Center (`workday_exporter.py`)**:
  - Workday Web Services (WWS v37.2) SOAP XML: `<bsvc:Submit_Accounting_Journal_Request>` with nested line items.
  - Workday RaaS (Reporting-as-a-Service) REST JSON payloads.
  - Full Worktag mapping: `Cost_Center`, `Spend_Category`, `Revenue_Category`, `Fund`, `Region`.
- **Microsoft Dynamics 365 Finance (`d365_exporter.py`)**:
  - OData V4 JSON entity payloads: `LedgerJournalTable` and `LedgerJournalTrans`.
  - Segmented dimension combinations: `AccountDisplayValue` (e.g., `11000-001-CC100-US`).
  - Multipart `$batch` request packaging (`--batch_...` boundary envelopes).
- **Oracle NetSuite ERP (`netsuite_exporter.py`)**:
  - SuiteTalk REST JSON format (`/services/rest/record/v1/journalentry`).
  - NetSuite CSV Import format with OneWorld multi-subsidiary classifications (`Department`, `Class`, `Location`).
- **Oracle Financials Cloud (`oracle_fc_exporter.py`)**:
  - Oracle FBDI (File-Based Data Import) standard `JournalImportTemplate.csv` for `GlInterface` uploads.
  - Oracle ERP Integration Service REST JSON (`importAndPostJournalBatches`).
  - 6-segment Accounting Flexfield mapping (`Company`, `CostCenter`, `Account`, `SubAccount`, `Product`, `Intercompany`).

---

### 5. Cryptographic Triple-Entry & DLT Consensus Drivers
*Package: `gl_fuzzer/dlt/` (`merkle_ledger.py`, `fabric_driver.py`, `evm_driver.py`)*

Triple-entry bookkeeping and decentralized enterprise ledger consensus simulation:
- **SHA-256 Binary Merkle Ledger (`MerkleLedger`)**:
  - Generates cryptographic binary Merkle trees over journal vouchers with power-of-2 leaf padding.
  - Produces $O(\log N)$ inclusion audit proofs ($\pi = \{(\text{sibling}, \text{direction})\}$) verifying whether any transaction was altered in transit.
  - Emits tamper-evident `TripleEntryReceipt` tokens for external counterparty reconciliation.
  - Automated ledger audit raises `MerkleIntegrityError` upon single-byte transaction alterations.
- **Hyperledger Fabric Simulation (`FabricLedgerSimulator`)**:
  - Models private channels, world state `VersionedValue(value, block_num, tx_num)`, and ReadWriteSets (`RWSet`).
  - Chaincode execution: `createVoucher`, `transferFunds`, `getBalance`.
  - Injects and intercepts consensus anomalies: `RWSetVersionConflict` (MVCC phantom read conflicts), `EndorsementPolicyMismatch` (signature quorum failure), and `OutdatedStateCommitment`.
- **Enterprise EVM Smart Contract Driver (`EVMSmartContractSimulator`)**:
  - Simulates tokenized settlement smart contracts (ERC-20 / ERC-1155).
  - Fuzzes smart contract vulnerabilities: **Integer Underflow/Overflow** (pre-0.8 uint256 wrapping), **Reentrancy Exploits** (recursive external call draining), **Gas Limit Exhaustion** (block gas overflow), and **Storage Slot Collisions** (proxy delegatecall corruption).

---

### 6. Coupled Hawkes Point Process Lead-Time Generator
*Package: `gl_fuzzer/generators/hawkes_process.py`*

Provides stochastic enterprise temporal dynamics modeling invoice-to-payment lead times:
- **Coupled Hawkes Process (`CoupledHawkesPointProcess`)**:
  - Models self-exciting point processes with conditional intensity $\lambda(t) = \mu + \sum_{t_i < t} \alpha e^{-\beta(t - t_i)}$ in a subcritical regime ($\alpha / \beta < 1$).
  - Evaluates commercial payment terms: $T+30$ Net 30, $T+60$ Net 60, and bimodal $2/10\text{ net }30$ early discount optimization distributions.
  - Simulates treasury payment batching combs (weekly payment disbursement runs on specific weekdays, e.g., Tuesdays/Thursdays).
  - Integrated `BusinessCalendar.snap_to_weekday()` forward and fallback snapping ensuring zero weekend payment executions.

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

### 2. Native Windows Desktop GUI (Offline Tkinter 6-Tab Interface)
- **Stack**: Native Python `tkinter` and `ttk` with styled widgets.
- **100% Offline**: Operates completely disconnected from the internet.
- **Thread-Safe**: Background worker execution with synchronized state locking.
- **6 Dedicated Workspaces**:
  1. *⚙️ 1. Synthesis & Generation*: Sliders, anomaly toggles, tax jurisdiction, withholding tax, and subledger matching toggles.
  2. *📑 2. Voucher & Ledger Explorer*: Paginated table with drilldown into debit/credit line items.
  3. *🛡️ 3. SOX-404 Forensic Audit*: Diagnostic cards with status badges and forensic findings.
  4. *📦 4. Export & Artifacts*: Target folder picker, format descriptions, and direct file opener.
  5. *⚡ 5. Enterprise & Dynamic Fuzzing*: Dynamic security fuzzing campaigns (Mock ERP vs SQLite ACID target), statutory tax return computation, and live ERP connector probing.
  6. *🧬 6. APT, MDM & Remediation*: Orchestrates multi-quarter adversarial persistent threat campaigns, deep master data integrity & sybil vendor audits, and auto-generates SAP GGB0 / ABAP / SQL / SOX remediation patches.

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
  [5] Run Complete Automated Test Suite (172 tests)
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

# 8. Turnkey Infrastructure Cluster Management
python -m gl_fuzzer.cli cluster status           # Probe all live ERP and Kafka cluster services
python -m gl_fuzzer.cli cluster probe            # Test SAP OData, RFC, Oracle, and Kafka connectivity
python -m gl_fuzzer.cli cluster start            # Spin up Docker Compose cluster
python -m gl_fuzzer.cli cluster stop             # Shut down cluster containers

# 9. Benchmark Generation and Fuzzing Throughput
python -m gl_fuzzer.cli benchmark --count 10000 --anomaly-rate 0.05

# 10. Launch Graphical Interfaces
python -m gl_fuzzer.cli gui --port 8080          # Web GUI
python -m gl_fuzzer.cli gui --mode desktop      # Desktop GUI

# 11. Autonomous Generative LLM Social Engineering Fraud Agents
python -m gl_fuzzer.cli agent-dialogue --persona EXECUTIVE_CFO --format pretty
python -m gl_fuzzer.cli agent-dialogue --persona COLLUSIVE_VENDOR --format eml --out-file ./output/phish_thread.eml
python -m gl_fuzzer.cli agent-dialogue --persona AUDITOR_DECEPTOR --format json

# 12. Legacy Mainframe & Supply Chain EDI Serialization & Fuzzing
python -m gl_fuzzer.cli legacy-export --protocol X12_810 --out-file ./output/invoice.edi
python -m gl_fuzzer.cli legacy-export --protocol NACHA_ACH --count 10 --out-file ./output/payroll.ach
python -m gl_fuzzer.cli legacy-export --protocol EBCDIC --count 5 --out-file ./output/dump.bin
python -m gl_fuzzer.cli legacy-fuzz --protocol NACHA_ACH --anomalies HASH_TOTAL_DESYNC,FIXED_WIDTH_OVERFLOW --out-file ./output/corrupt.ach
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

### Automated Test Suite (294 Tests)

The codebase features an extensive test suite with **294 automated unit, regression, and integration tests achieving 100% pass rate**:

```bash
python -m pytest -q
```

```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\PROJECT\PYTHON
configfile: pyproject.toml
collected 294 items

tests/test_acdoca.py ....                                                [  1%]
tests/test_agents.py .........                                           [  4%]
tests/test_anomalies.py ........                                         [  7%]
tests/test_audit_metrics.py .....                                        [  9%]
tests/test_campaigns.py ...                                              [ 10%]
tests/test_cli.py .........                                              [ 13%]
tests/test_coa_models.py ...                                             [ 14%]
tests/test_connectors.py ..............                                  [ 19%]
tests/test_cycles.py ......                                              [ 21%]
tests/test_dlt_triple_entry.py ..........                                [ 24%]
tests/test_documents.py ....                                             [ 25%]
tests/test_edge_cases.py .......................                         [ 33%]
tests/test_exporters.py ....                                             [ 34%]
tests/test_fixed_assets.py ............                                  [ 38%]
tests/test_forensic_ext.py .........                                     [ 41%]
tests/test_fuzzing.py ..........                                         [ 44%]
tests/test_fx_revaluation.py ....                                        [ 45%]
tests/test_generators.py ....                                            [ 47%]
tests/test_gui.py ...............                                        [ 52%]
tests/test_hawkes_process.py ........                                    [ 55%]
tests/test_invariants.py ....                                            [ 56%]
tests/test_legacy_edi.py ..........                                      [ 59%]
tests/test_legacy_mainframe.py ........................                  [ 68%]
tests/test_macro_calendar.py .....                                       [ 69%]
tests/test_mdm.py ....                                                   [ 71%]
tests/test_ml_generative.py .....                                        [ 73%]
tests/test_models.py ...........                                         [ 76%]
tests/test_multi_currency.py ........                                    [ 79%]
tests/test_multi_erp_exporters.py ....                                   [ 80%]
tests/test_multicore_engine.py ...                                       [ 81%]
tests/test_orchestration.py ...                                          [ 82%]
tests/test_remediation.py ....                                           [ 84%]
tests/test_streaming.py .....                                            [ 85%]
tests/test_streaming_sinks.py .........                                  [ 88%]
tests/test_subledgers.py .........                                       [ 91%]
tests/test_tax.py .............                                          [ 96%]
tests/test_treasury.py .........                                         [100%]

============================ 294 passed in 20.11s =============================
```

---

## Repository Structure

```
Synthetic-General-Ledger-Fuzzer/
├── gl_fuzzer/
│   ├── __init__.py                # Package root (v0.6.0 Enterprise)
│   ├── cli.py                     # Typer / Rich CLI with cluster management & legacy tools
│   ├── web_gui.py                 # Modern browser dashboard with LLM Studio & Legacy panels
│   ├── desktop_gui.py             # Native offline Tkinter GUI (8 tabs, Thread-safe)
│   ├── agents/                    # [Frontier] Autonomous Generative LLM Fraud Agents
│   │   ├── models.py              # AgentPersona, PersuasionTactic, SocialEngineeringThread
│   │   └── engine.py              # Heuristic offline generator, executive & vendor personas
│   ├── legacy_protocols/          # [Frontier] Legacy Mainframe & Supply Chain EDI Protocols
│   │   ├── models.py              # LegacyProtocolType, ProtocolFuzzAnomaly models
│   │   ├── edi_engine.py          # ANSI X12 (810/850/856), UN/EDIFACT (INVOIC/ORDERS), mutator
│   │   └── mainframe_engine.py    # COBOL 80/132-col, EBCDIC CP037 COMP-3, NACHA ACH, BAI2, MT940
│   ├── campaigns/                 # Multi-Stage Financial APT Campaigns
│   │   ├── models.py              # APTCampaignRecord, APTActor, APTPhaseMilestone
│   │   └── orchestrator.py        # Multi-quarter adversarial narrative orchestrator
│   ├── mdm/                       # Deep Master Data Management (MDM)
│   │   ├── models.py              # VendorMaster, CustomerMaster, EmployeeMaster, MDMAnomalyRecord
│   │   ├── mutators.py            # Sybil clones, 24h bank tampering, employee collusion
│   │   └── engine.py              # MasterDataManager with fuzzy screening & graph matching
│   ├── remediation/               # Automated Remediation Oracles & Healing Loop
│   │   ├── models.py              # RemediationPatch, CompensatingControl, VerificationStatus
│   │   ├── engine.py              # RemediationAdvisor (SAP GGB0, ABAP BAdI, SQL, SOX)
│   │   └── healing_loop.py        # Closed-loop exploit neutralization runner
│   ├── documents/                 # Unstructured Context & Multimodal Artifacts
│   │   ├── models.py              # SyntheticInvoiceData, DocumentMismatchType, ItemLine
│   │   ├── pdf_generator.py       # Pure-Python zero-dependency PDF 1.4 binary engine
│   │   ├── email_generator.py     # RFC-2822 .eml corporate override threads
│   │   └── mismatch_injector.py   # Ledger-to-document OCR mismatch & IBAN injection
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
│   ├── subledgers/                # [Pillar 4] Operational Logistics & Balance Sheet Subledgers
│   │   ├── fixed_assets.py        # [Frontier 1] IAS 16/36 fixed assets, depreciation (SL/DDB/UOP), impairment
│   │   ├── treasury.py            # [Frontier 1] IFRS 9 debt facilities, EIR amortized cost, covenants, IRS hedges
│   │   ├── fx_revaluation.py      # [Frontier 1] ASC 830 / IAS 21 month-end FAGL_FCV FX revaluations & Day-1 reversals
│   │   ├── inventory.py           # Material Master, moving average price (MAP), bin stock
│   │   ├── three_way_match.py     # 3-Way Match (PO -> GR/WE -> IR/RE), price variance (PPV)
│   │   └── order_fulfillment.py   # Sales Order fulfillment, delivery (GI/WA), COGS calculation
│   ├── generators/                # Core Synthesis & Parallel Engines
│   │   ├── hawkes_process.py      # [Frontier 6] Coupled Hawkes Point Process invoice-to-payment lead times
│   │   ├── parallel_engine.py     # [Frontier 2] High-performance multi-core ProcessPool parallel generation
│   │   ├── distributions.py       # Benford, LogNormal, BusinessCalendar sampling
│   │   ├── macro_calendar.py      # Macro-economic calendar & quarterly seasonality
│   │   ├── streaming_engine.py    # Chunked synthesis engine (Zero-OOM, streaming hook)
│   │   ├── p2p_cycle.py           # Procure-to-Pay generator (WE, KR, RE, KZ payment)
│   │   ├── o2c_cycle.py           # Order-to-Cash generator (WA, DR, DZ, single customer)
│   │   ├── r2r_cycle.py           # Record-to-Report (Depreciation, Payroll, Accrual)
│   │   └── base_engine.py         # Master synthesis engine with dependency injection
│   ├── ml_generative/             # [Frontier 3] Generative Tabular Machine Learning
│   │   ├── gaussian_copula.py     # Tier 1 multivariate Gaussian Copula synthesizer & latent perturbation
│   │   └── tvae_engine.py         # Tier 2 Tabular Variational Autoencoder (pure NumPy backprop)
│   ├── dlt/                       # [Frontier 5] Cryptographic Triple-Entry & DLT Consensus Drivers
│   │   ├── merkle_ledger.py       # SHA-256 binary Merkle tree, inclusion proofs, Triple-Entry receipts
│   │   ├── fabric_driver.py       # Hyperledger Fabric MVCC RWSet & consensus conflict fuzzer
│   │   └── evm_driver.py          # Enterprise EVM smart contract ERC-20/1155 settlement fuzzer
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
│   │   └── audit_metrics.py       # SOX-404 automated audit detection (10 forensic methods)
│   └── exporters/                 # Output Deliverable Exporters (Multi-ERP)
│       ├── workday_exporter.py    # [Frontier 4] Workday Accounting Center SOAP XML & RaaS JSON
│       ├── d365_exporter.py       # [Frontier 4] Dynamics 365 OData V4 JSON & multipart $batch envelopes
│       ├── netsuite_exporter.py   # [Frontier 4] NetSuite SuiteTalk REST JSON & CSV Import template
│       ├── oracle_fc_exporter.py  # [Frontier 4] Oracle Financials Cloud FBDI CSV & REST integration
│       ├── parquet_exporter.py    # PyArrow Decimal128 Parquet exporter
│       ├── streaming_parquet.py   # Zero-OOM streaming row-group Parquet writer
│       ├── acdoca_exporter.py     # SAP S/4HANA Universal Journal 50+ column exporter
│       ├── csv_exporter.py        # RFC 4180 CSV exporter (None-safe)
│       ├── sap_bseg_exporter.py   # SAP BKPF / BSEG table exporter
│       └── manifest_exporter.py   # JSON & Parquet ground-truth manifest exporter
├── docker/                        # Container Definitions & Mock Services
│   ├── Dockerfile.fuzzer          # GL-Fuzzer container definition
│   ├── Dockerfile.mock_sap        # Mock SAP S/4HANA gateway service container
│   └── mock_sap_service.py        # Mock OData V4 HTTP server
├── docker-compose.yml             # Redpanda Kafka, Mock SAP, LocalStack Kinesis compose
├── tests/                         # 294 automated unit, regression, and integration tests
├── pyproject.toml                 # Project configuration, dependencies, and v0.6.0 metadata
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
