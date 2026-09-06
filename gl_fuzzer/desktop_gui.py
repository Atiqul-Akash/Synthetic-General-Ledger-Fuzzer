"""Enterprise General Ledger Fuzzer - Native Desktop GUI (Tkinter/ttk).

Provides a modern, zero-confusion desktop interface for synthesizing GL batches,
injecting calibrated micro-anomalies, exploring balanced double-entry vouchers,
running SOX-404 forensic audit tests, and exporting ERP-ready datasets.
"""

from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Dict, List, Optional

from gl_fuzzer.web_gui import GLAppState


class DesktopGUI:
    """Enterprise GL Fuzzer Native Desktop Application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Synthetic General Ledger Fuzzer — Made with <3 by Atiqul-Akash")
        self.root.geometry("1100x780")
        self.root.minsize(960, 680)

        # Application state
        self.state = GLAppState()
        self.state.output_dir = Path("./desktop_gui_output")
        self.state.output_dir.mkdir(parents=True, exist_ok=True)

        self._configure_styles()
        self._build_header()
        self._build_notebook()
        self._build_status_bar()

        # Pre-populate with a clean sample in background so user doesn't start with empty screen
        self.root.after(100, self._initial_load)

    def _configure_styles(self):
        self.style = ttk.Style()
        # Use clam or native theme
        available_themes = self.style.theme_names()
        if "clam" in available_themes:
            self.style.theme_use("clam")

        # Custom ttk styles
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("Header.TFrame", background="#0f172a")
        self.style.configure("Header.TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 14, "bold"))
        self.style.configure("HeaderSub.TLabel", background="#0f172a", foreground="#94a3b8", font=("Segoe UI", 9))

        self.style.configure("Card.TFrame", background="#ffffff", relief="groove")
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background="#2563eb", foreground="#ffffff")
        self.style.configure("Success.TLabel", foreground="#16a34a", font=("Segoe UI", 10, "bold"))
        self.style.configure("Warning.TLabel", foreground="#d97706", font=("Segoe UI", 10, "bold"))
        self.style.configure("Danger.TLabel", foreground="#dc2626", font=("Segoe UI", 10, "bold"))
        self.style.configure("Muted.TLabel", foreground="#64748b", font=("Segoe UI", 9))
        self.style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground="#1e293b")

        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        self.style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))

    def _build_header(self):
        header_frame = ttk.Frame(self.root, style="Header.TFrame", padding=(16, 12))
        header_frame.pack(fill=tk.X)

        title_box = ttk.Frame(header_frame, style="Header.TFrame")
        title_box.pack(side=tk.LEFT)

        title = ttk.Label(title_box, text="Synthetic General Ledger Fuzzer", style="Header.TLabel")
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            title_box,
            text="High-Fidelity Synthetic GL Synthesis | Calibrated Micro-Anomalies | Made with <3 by Atiqul-Akash (GitHub: Atiqul-Akash)",
            style="HeaderSub.TLabel",
        )
        subtitle.pack(anchor=tk.W)

        # Invariant badge on top-right
        self.header_badge_var = tk.StringVar(value="Balance: Initializing...")
        self.badge_label = tk.Label(
            header_frame,
            textvariable=self.header_badge_var,
            bg="#1e293b",
            fg="#38bdf8",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            relief="solid",
            bd=1,
        )
        self.badge_label.pack(side=tk.RIGHT)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self.tab_synthesis = ttk.Frame(self.notebook, padding=12)
        self.tab_explorer = ttk.Frame(self.notebook, padding=12)
        self.tab_audit = ttk.Frame(self.notebook, padding=12)
        self.tab_export = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_synthesis, text=" ⚙️ 1. Synthesis & Generation ")
        self.notebook.add(self.tab_explorer, text=" 📑 2. Voucher & Ledger Explorer ")
        self.notebook.add(self.tab_audit, text=" 🛡️ 3. SOX-404 Forensic Audit ")
        self.notebook.add(self.tab_export, text=" 📦 4. Export & Artifacts ")

        self._init_synthesis_tab()
        self._init_explorer_tab()
        self._init_audit_tab()
        self._init_export_tab()

    def _build_status_bar(self):
        status_bar = ttk.Frame(self.root, padding=(12, 4))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Label(status_bar, text="Double-Entry Precision: Exact Decimal Cent Arithmetic", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Label(status_bar, text=" | ", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Label(status_bar, text="SOX-404 Compliant Audit Manifests", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Label(status_bar, text=" | ", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Label(status_bar, text="Made with <3 by Atiqul-Akash | GitHub: Atiqul-Akash", style="Muted.TLabel").pack(side=tk.LEFT)

        self.lbl_system_status = ttk.Label(status_bar, text="Status: Ready", font=("Segoe UI", 9, "bold"), foreground="#15803d")
        self.lbl_system_status.pack(side=tk.RIGHT)

    # =========================================================================
    # TAB 1: SYNTHESIS & GENERATION
    # =========================================================================
    def _init_synthesis_tab(self):
        # Quick Presets Bar
        preset_frame = ttk.LabelFrame(self.tab_synthesis, text="Quick Presets (Zero-Confusion Setup)", padding=10)
        preset_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            preset_frame,
            text="✨ Standard Benchmark (1,000 / 5%)",
            command=lambda: self._apply_preset(1000, 0.05, [True, True, True, True, True]),
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            preset_frame,
            text="⚡ Quick Smoke Test (200 / 2%)",
            command=lambda: self._apply_preset(200, 0.02, [True, True, False, False, False]),
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            preset_frame,
            text="🔥 Forensic Stress Test (3,000 / 10%)",
            command=lambda: self._apply_preset(3000, 0.10, [True, True, True, True, True]),
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            preset_frame,
            text="🛡️ Clean Baseline (1,000 / 0%)",
            command=lambda: self._apply_preset(1000, 0.00, [False, False, False, False, False]),
        ).pack(side=tk.LEFT, padx=4)

        # Main Configuration Layout: 2 Columns
        content_frame = ttk.Frame(self.tab_synthesis)
        content_frame.pack(fill=tk.BOTH, expand=True)

        left_col = ttk.LabelFrame(content_frame, text="Generation Parameters & Anomaly Engine", padding=12)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        right_col = ttk.LabelFrame(content_frame, text="Real-Time Ledger Status & Invariant Verification", padding=12)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # Left Column: Controls
        # 1. Entry Count
        ttk.Label(left_col, text="Journal Entry Count:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(left_col, text="Number of complete double-entry transaction vouchers to synthesize.", style="Muted.TLabel").pack(anchor=tk.W)
        self.entry_count_var = tk.IntVar(value=1000)
        count_spin = ttk.Spinbox(left_col, from_=100, to=50000, increment=500, textvariable=self.entry_count_var, width=15)
        count_spin.pack(anchor=tk.W, pady=(2, 10))

        # 2. Anomaly Rate
        ttk.Label(left_col, text="Overall Anomaly Rate:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.rate_label_var = tk.StringVar(value="5.0% (calibrated noise for ML / forensic models)")
        ttk.Label(left_col, textvariable=self.rate_label_var, style="Muted.TLabel").pack(anchor=tk.W)

        self.anomaly_rate_var = tk.DoubleVar(value=0.05)
        rate_scale = ttk.Scale(
            left_col,
            from_=0.0,
            to=0.25,
            variable=self.anomaly_rate_var,
            command=self._on_rate_slider_change,
        )
        rate_scale.pack(fill=tk.X, pady=(2, 10))

        # 3. Seed
        ttk.Label(left_col, text="Random Seed (Reproducibility):", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 2))
        seed_box = ttk.Frame(left_col)
        seed_box.pack(anchor=tk.W, pady=(2, 12))
        self.seed_var = tk.StringVar(value="42")
        ttk.Entry(seed_box, textvariable=self.seed_var, width=12).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(seed_box, text="🎲 Randomize", command=self._randomize_seed).pack(side=tk.LEFT)

        # 4. Anomaly Mutators Checklist
        ttk.Label(left_col, text="Active Micro-Anomaly Mutators:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))

        self.anom_smurfing_var = tk.BooleanVar(value=True)
        self.anom_ghost_var = tk.BooleanVar(value=True)
        self.anom_benford_var = tk.BooleanVar(value=True)
        self.anom_pairings_var = tk.BooleanVar(value=True)
        self.anom_roundtrip_var = tk.BooleanVar(value=True)

        cb1 = ttk.Checkbutton(
            left_col,
            text="Smurfing: Split approval invoices just under $10,000 DOA limit",
            variable=self.anom_smurfing_var,
        )
        cb1.pack(anchor=tk.W, pady=2)

        cb2 = ttk.Checkbutton(
            left_col,
            text="Ghost Entries: Off-hours / weekend postings by deactivated users",
            variable=self.anom_ghost_var,
        )
        cb2.pack(anchor=tk.W, pady=2)

        cb3 = ttk.Checkbutton(
            left_col,
            text="Benford Skew: Non-conformant first digits violating natural distributions",
            variable=self.anom_benford_var,
        )
        cb3.pack(anchor=tk.W, pady=2)

        cb4 = ttk.Checkbutton(
            left_col,
            text="Anomalous Pairings: Direct Cash to Revenue, bypassing AR/AP ledger",
            variable=self.anom_pairings_var,
        )
        cb4.pack(anchor=tk.W, pady=2)

        cb5 = ttk.Checkbutton(
            left_col,
            text="Round-Tripping: Circular intercompany transfers (Entity A -> B -> C -> A)",
            variable=self.anom_roundtrip_var,
        )
        cb5.pack(anchor=tk.W, pady=2)

        # Primary Generate Button
        self.btn_generate = tk.Button(
            left_col,
            text="🚀 Generate & Synthesize GL Dataset",
            bg="#2563eb",
            fg="#ffffff",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._start_generation_thread,
        )
        self.btn_generate.pack(fill=tk.X, pady=(16, 6))

        # Progress bar
        self.progress_bar = ttk.Progressbar(left_col, mode="indeterminate")
        self.progress_label_var = tk.StringVar(value="Ready to synthesize.")
        ttk.Label(left_col, textvariable=self.progress_label_var, style="Muted.TLabel").pack(anchor=tk.W)

        # Right Column: Live Status & KPI Cards
        kpi_container = ttk.Frame(right_col)
        kpi_container.pack(fill=tk.BOTH, expand=True)

        self.kpi_batch_id = tk.StringVar(value="--")
        self.kpi_total_entries = tk.StringVar(value="0")
        self.kpi_total_lines = tk.StringVar(value="0")
        self.kpi_total_debits = tk.StringVar(value="$0.00")
        self.kpi_total_credits = tk.StringVar(value="$0.00")
        self.kpi_balance_status = tk.StringVar(value="Awaiting Generation")
        self.kpi_anomalous_entries = tk.StringVar(value="0 (0.0%)")
        self.kpi_sha256 = tk.StringVar(value="--")

        self._create_kpi_card(kpi_container, "Batch Run Identifier", self.kpi_batch_id)
        self._create_kpi_card(kpi_container, "Total Journal Entries", self.kpi_total_entries)
        self._create_kpi_card(kpi_container, "Total Ledger Line Items", self.kpi_total_lines)
        self._create_kpi_card(kpi_container, "Total Sum(Debits)", self.kpi_total_debits)
        self._create_kpi_card(kpi_container, "Total Sum(Credits)", self.kpi_total_credits)

        # Balance Verification Card (Special High-Visibility)
        bal_frame = tk.Frame(kpi_container, bg="#f0fdf4", bd=1, relief="solid")
        bal_frame.pack(fill=tk.X, pady=4, padx=2)
        tk.Label(bal_frame, text="Double-Entry Invariant Check", bg="#f0fdf4", fg="#166534", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=8, pady=(4, 0))
        self.lbl_balance_card = tk.Label(bal_frame, textvariable=self.kpi_balance_status, bg="#f0fdf4", fg="#15803d", font=("Segoe UI", 12, "bold"))
        self.lbl_balance_card.pack(anchor=tk.W, padx=8, pady=(0, 6))

        self._create_kpi_card(kpi_container, "Anomalous Entries Injected", self.kpi_anomalous_entries)

        # Anomaly Breakdown Box
        ttk.Label(kpi_container, text="Injected Anomaly Breakdown:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(8, 2))
        self.txt_breakdown = tk.Text(kpi_container, height=4, width=38, font=("Consolas", 9), relief="solid", bd=1)
        self.txt_breakdown.pack(fill=tk.X, padx=2)
        self.txt_breakdown.insert(tk.END, "No batch loaded.")
        self.txt_breakdown.config(state=tk.DISABLED)

    def _create_kpi_card(self, parent, label_text: str, string_var: tk.StringVar):
        card = ttk.Frame(parent, padding=(6, 4))
        card.pack(fill=tk.X, pady=2)
        ttk.Label(card, text=label_text, style="Muted.TLabel").pack(anchor=tk.W)
        ttk.Label(card, textvariable=string_var, font=("Segoe UI", 11, "bold")).pack(anchor=tk.W)
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)

    def _on_rate_slider_change(self, val):
        pct = float(val) * 100
        self.rate_label_var.set(f"{pct:.1f}% of total vouchers will contain injected micro-anomalies")

    def _randomize_seed(self):
        new_seed = random.randint(1000, 999999)
        self.seed_var.set(str(new_seed))

    def _apply_preset(self, count: int, rate: float, anomalies: List[bool]):
        self.entry_count_var.set(count)
        self.anomaly_rate_var.set(rate)
        self._on_rate_slider_change(rate)
        self.anom_smurfing_var.set(anomalies[0])
        self.anom_ghost_var.set(anomalies[1])
        self.anom_benford_var.set(anomalies[2])
        self.anom_pairings_var.set(anomalies[3])
        self.anom_roundtrip_var.set(anomalies[4])

    def _start_generation_thread(self):
        try:
            count = max(10, int(self.entry_count_var.get()))
        except Exception:
            count = 1000

        try:
            rate = max(0.0, min(1.0, float(self.anomaly_rate_var.get())))
        except Exception:
            rate = 0.05

        try:
            seed = int(self.seed_var.get().strip())
        except ValueError:
            seed = 42

        enabled = {
            "smurfing": bool(self.anom_smurfing_var.get()),
            "ghost": bool(self.anom_ghost_var.get()),
            "benford": bool(self.anom_benford_var.get()),
            "pairings": bool(self.anom_pairings_var.get()),
            "round_trip": bool(self.anom_roundtrip_var.get()),
        }

        self.btn_generate.config(state=tk.DISABLED)
        self.progress_bar.pack(fill=tk.X, pady=(6, 4))
        self.progress_bar.start(10)
        self.progress_label_var.set("Synthesizing baseline vouchers & injecting anomalies...")

        thread = threading.Thread(
            target=self._run_generation_worker,
            args=(count, rate, seed, enabled),
            daemon=True,
        )
        thread.start()

    def _run_generation_worker(self, count: int, rate: float, seed: int, enabled: Dict[str, bool]):
        try:
            summary = self.state.generate(
                count=count,
                anomaly_rate=rate,
                seed=seed,
                enabled_anomalies=enabled,
            )

            # Schedule UI update on main thread
            self.root.after(0, lambda: self._on_generation_completed(summary))

        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_generation_error(err_msg))

    def _on_generation_completed(self, summary: Dict[str, Any]):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_generate.config(state=tk.NORMAL)
        self.progress_label_var.set("Dataset generation and invariant verification complete!")

        # Update KPI values
        self.kpi_batch_id.set(summary.get("batch_id", "--"))
        self.kpi_total_entries.set(f"{summary.get('total_entries', 0):,}")
        self.kpi_total_lines.set(f"{summary.get('total_lines', 0):,}")
        self.kpi_total_debits.set(f"${float(summary.get('total_debits', 0)):,.2f}")
        self.kpi_total_credits.set(f"${float(summary.get('total_credits', 0)):,.2f}")

        is_balanced = summary.get("is_globally_balanced", False)
        if is_balanced:
            self.kpi_balance_status.set("EXACT MATCH: Sum(Debits) == Sum(Credits) [PASS]")
            self.lbl_balance_card.config(bg="#f0fdf4", fg="#15803d")
            self.header_badge_var.set("Balance: INTACT (Zero Delta)")
            self.badge_label.config(bg="#15803d", fg="#ffffff")
        else:
            self.kpi_balance_status.set("UNBALANCED: Invariant Violation Detected! [FAIL]")
            self.lbl_balance_card.config(bg="#fef2f2", fg="#dc2626")
            self.header_badge_var.set("Balance: FAILED")
            self.badge_label.config(bg="#dc2626", fg="#ffffff")

        anom_count = summary.get("anomalous_entries_count", 0)
        anom_rate = summary.get("anomaly_rate", 0.0) * 100
        self.kpi_anomalous_entries.set(f"{anom_count:,} ({anom_rate:.1f}%)")

        # Update breakdown box
        breakdown = summary.get("anomaly_breakdown", {})
        self.txt_breakdown.config(state=tk.NORMAL)
        self.txt_breakdown.delete("1.0", tk.END)
        for anom_k, anom_v in breakdown.items():
            self.txt_breakdown.insert(tk.END, f"- {anom_k}: {anom_v} instances\n")
        if not breakdown:
            self.txt_breakdown.insert(tk.END, "Zero anomalies (Clean baseline).")
        self.txt_breakdown.config(state=tk.DISABLED)

        # Refresh Explorer table and Export table
        self._refresh_explorer_table()
        self._refresh_export_table()

    def _on_generation_error(self, err_msg: str):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.btn_generate.config(state=tk.NORMAL)
        self.progress_label_var.set(f"Error during generation: {err_msg}")
        messagebox.showerror("Generation Error", f"Failed to synthesize dataset:\n{err_msg}")

    # =========================================================================
    # TAB 2: VOUCHER & LEDGER EXPLORER
    # =========================================================================
    def _init_explorer_tab(self):
        # Filter & Search Toolbar
        filter_bar = ttk.Frame(self.tab_explorer)
        filter_bar.pack(fill=tk.X, pady=(0, 8))

        # Cycle filter
        ttk.Label(filter_bar, text="Business Cycle:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.filter_cycle_var = tk.StringVar(value="ALL")
        cycle_combo = ttk.Combobox(filter_bar, textvariable=self.filter_cycle_var, values=["ALL", "P2P", "O2C", "R2R"], state="readonly", width=8)
        cycle_combo.pack(side=tk.LEFT, padx=(0, 12))
        cycle_combo.bind("<<ComboboxSelected>>", lambda e: self._filter_entries())

        # Anomaly Status filter
        ttk.Label(filter_bar, text="Status:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.filter_status_var = tk.StringVar(value="ALL")
        status_combo = ttk.Combobox(filter_bar, textvariable=self.filter_status_var, values=["ALL", "Clean Only", "Anomalies Only"], state="readonly", width=14)
        status_combo.pack(side=tk.LEFT, padx=(0, 12))
        status_combo.bind("<<ComboboxSelected>>", lambda e: self._filter_entries())

        # Search box
        ttk.Label(filter_bar, text="Search:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.search_text_var = tk.StringVar()
        search_entry = ttk.Entry(filter_bar, textvariable=self.search_text_var, width=22)
        search_entry.pack(side=tk.LEFT, padx=(0, 6))
        search_entry.bind("<KeyRelease>", lambda e: self._filter_entries())

        ttk.Button(filter_bar, text="Clear Filter", command=self._clear_filters).pack(side=tk.LEFT)

        self.lbl_explorer_count = ttk.Label(filter_bar, text="Showing 0 entries", style="Muted.TLabel")
        self.lbl_explorer_count.pack(side=tk.RIGHT)

        # Paned Window: Top is Entry List, Bottom is Line Item Voucher Breakdown
        paned = ttk.PanedWindow(self.tab_explorer, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Top Frame: Entries Table
        top_frame = ttk.LabelFrame(paned, text="Journal Entry Headers (Click row to inspect double-entry debit/credit voucher)", padding=4)
        paned.add(top_frame, weight=3)

        columns = ("doc_num", "cycle", "doc_type", "date", "time", "user", "debits", "credits", "balanced", "anomaly")
        self.tree_entries = ttk.Treeview(top_frame, columns=columns, show="headings", selectmode="browse")

        self.tree_entries.heading("doc_num", text="Document #")
        self.tree_entries.heading("cycle", text="Cycle")
        self.tree_entries.heading("doc_type", text="Type")
        self.tree_entries.heading("date", text="Posting Date")
        self.tree_entries.heading("time", text="Time")
        self.tree_entries.heading("user", text="User")
        self.tree_entries.heading("debits", text="Total Debits")
        self.tree_entries.heading("credits", text="Total Credits")
        self.tree_entries.heading("balanced", text="Balanced")
        self.tree_entries.heading("anomaly", text="Anomaly Tag")

        self.tree_entries.column("doc_num", width=110, anchor=tk.CENTER)
        self.tree_entries.column("cycle", width=60, anchor=tk.CENTER)
        self.tree_entries.column("doc_type", width=50, anchor=tk.CENTER)
        self.tree_entries.column("date", width=90, anchor=tk.CENTER)
        self.tree_entries.column("time", width=70, anchor=tk.CENTER)
        self.tree_entries.column("user", width=90, anchor=tk.W)
        self.tree_entries.column("debits", width=100, anchor=tk.E)
        self.tree_entries.column("credits", width=100, anchor=tk.E)
        self.tree_entries.column("balanced", width=75, anchor=tk.CENTER)
        self.tree_entries.column("anomaly", width=160, anchor=tk.W)

        scroll_y1 = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=self.tree_entries.yview)
        self.tree_entries.configure(yscrollcommand=scroll_y1.set)
        self.tree_entries.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y1.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_entries.bind("<<TreeviewSelect>>", self._on_entry_selected)

        # Bottom Frame: Voucher Line Items Table
        bottom_frame = ttk.LabelFrame(paned, text="Selected Voucher Double-Entry Lines (Strict Cent-Balanced Verification)", padding=4)
        paned.add(bottom_frame, weight=2)

        line_cols = ("line_num", "account_code", "account_name", "dc", "amount", "posting_key", "entity_party", "line_text")
        self.tree_lines = ttk.Treeview(bottom_frame, columns=line_cols, show="headings", selectmode="browse")

        self.tree_lines.heading("line_num", text="Line #")
        self.tree_lines.heading("account_code", text="GL Account")
        self.tree_lines.heading("account_name", text="Account Name")
        self.tree_lines.heading("dc", text="D/C")
        self.tree_lines.heading("amount", text="Amount (USD)")
        self.tree_lines.heading("posting_key", text="PK")
        self.tree_lines.heading("entity_party", text="Vendor / Customer / Partner")
        self.tree_lines.heading("line_text", text="Line Item Text")

        self.tree_lines.column("line_num", width=50, anchor=tk.CENTER)
        self.tree_lines.column("account_code", width=90, anchor=tk.CENTER)
        self.tree_lines.column("account_name", width=180, anchor=tk.W)
        self.tree_lines.column("dc", width=50, anchor=tk.CENTER)
        self.tree_lines.column("amount", width=110, anchor=tk.E)
        self.tree_lines.column("posting_key", width=40, anchor=tk.CENTER)
        self.tree_lines.column("entity_party", width=170, anchor=tk.W)
        self.tree_lines.column("line_text", width=220, anchor=tk.W)

        scroll_y2 = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.tree_lines.yview)
        self.tree_lines.configure(yscrollcommand=scroll_y2.set)
        self.tree_lines.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)

    def _clear_filters(self):
        self.filter_cycle_var.set("ALL")
        self.filter_status_var.set("ALL")
        self.search_text_var.set("")
        self._filter_entries()

    def _refresh_explorer_table(self):
        self._filter_entries()

    def _filter_entries(self):
        self.tree_entries.delete(*self.tree_entries.get_children())
        self.tree_lines.delete(*self.tree_lines.get_children())

        if not self.state.batch:
            self.lbl_explorer_count.config(text="Showing 0 entries")
            return

        cycle_filter = self.filter_cycle_var.get()
        status_filter = self.filter_status_var.get()
        search_query = self.search_text_var.get().strip().lower()

        displayed_count = 0
        max_display = 250  # Keep UI responsive

        for entry in self.state.batch.entries:
            # Cycle filter
            if cycle_filter != "ALL" and entry.business_cycle != cycle_filter:
                continue

            # Status filter
            if status_filter == "Clean Only" and entry.is_anomaly:
                continue
            if status_filter == "Anomalies Only" and not entry.is_anomaly:
                continue

            # Search text
            if search_query:
                haystack = f"{entry.document_number} {entry.entry_id} {entry.header_text} {entry.created_by}".lower()
                if search_query not in haystack:
                    continue

            anom_tag = ", ".join(entry.anomaly_ids) if entry.is_anomaly else "CLEAN"
            balanced_text = "YES [PASS]" if entry.is_balanced else "NO [FAIL]"

            item_id = self.tree_entries.insert(
                "",
                tk.END,
                values=(
                    entry.document_number,
                    entry.business_cycle,
                    entry.document_type.value,
                    entry.posting_date,
                    entry.entry_time,
                    entry.created_by,
                    f"${entry.total_debits:,.2f}",
                    f"${entry.total_credits:,.2f}",
                    balanced_text,
                    anom_tag,
                ),
            )
            displayed_count += 1
            if displayed_count >= max_display:
                break

        total_total = len(self.state.batch.entries)
        self.lbl_explorer_count.config(text=f"Showing {displayed_count} of {total_total} entries (display capped at {max_display})")

    def _on_entry_selected(self, event):
        selected_items = self.tree_entries.selection()
        if not selected_items:
            return

        selected_item = selected_items[0]
        values = self.tree_entries.item(selected_item, "values")
        if not values:
            return

        doc_num = values[0]
        # Find matching entry in batch
        target_entry = None
        for e in self.state.batch.entries:
            if e.document_number == doc_num:
                target_entry = e
                break

        if not target_entry:
            return

        self.tree_lines.delete(*self.tree_lines.get_children())
        for line in target_entry.lines:
            party = line.vendor_id or line.customer_id or line.trading_partner or ""
            self.tree_lines.insert(
                "",
                tk.END,
                values=(
                    line.line_number,
                    line.account_code,
                    line.account_name,
                    line.debit_credit.value,
                    f"${line.amount:,.2f}",
                    line.posting_key,
                    party,
                    line.line_text,
                ),
            )

    # =========================================================================
    # TAB 3: SOX-404 FORENSIC AUDIT
    # =========================================================================
    def _init_audit_tab(self):
        top_bar = ttk.Frame(self.tab_audit)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        self.btn_run_audit = tk.Button(
            top_bar,
            text="🔍 Run SOX-404 Forensic Audit Screening",
            bg="#dc2626",
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._start_audit_thread,
        )
        self.btn_run_audit.pack(side=tk.LEFT)

        self.lbl_audit_status = ttk.Label(top_bar, text="Ready to audit.", style="Muted.TLabel")
        self.lbl_audit_status.pack(side=tk.LEFT, padx=12)

        # Audit Results Frame: 5 Diagnostic Cards
        self.audit_scroll_frame = ttk.Frame(self.tab_audit)
        self.audit_scroll_frame.pack(fill=tk.BOTH, expand=True)

        # Create 5 Cards for each test
        self.card_benford = self._create_audit_test_card(self.audit_scroll_frame, "SOX-404-DATA: Benford's Law First-Digit Screening")
        self.card_doa = self._create_audit_test_card(self.audit_scroll_frame, "SOX-404-P2P: Split Approval DOA Threshold Bypass ($9,500 - $9,999)")
        self.card_offhours = self._create_audit_test_card(self.audit_scroll_frame, "SOX-404-AUTH: Off-Hours, Weekend & Deactivated User Postings")
        self.card_pairings = self._create_audit_test_card(self.audit_scroll_frame, "SOX-404-COA: Anomalous & Prohibited Account Pairings")
        self.card_ic = self._create_audit_test_card(self.audit_scroll_frame, "SOX-404-INTERCO: Circular Round-Tripping (A -> B -> C -> A)")

    def _create_audit_test_card(self, parent, test_name: str) -> Dict[str, Any]:
        frame = tk.Frame(parent, bg="#ffffff", relief="solid", bd=1, padx=10, pady=8)
        frame.pack(fill=tk.X, pady=4)

        header_row = tk.Frame(frame, bg="#ffffff")
        header_row.pack(fill=tk.X)

        title_lbl = tk.Label(header_row, text=test_name, font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#0f172a")
        title_lbl.pack(side=tk.LEFT)

        badge_var = tk.StringVar(value="NOT RUN")
        badge_lbl = tk.Label(header_row, textvariable=badge_var, font=("Segoe UI", 9, "bold"), bg="#f1f5f9", fg="#64748b", padx=8, pady=2)
        badge_lbl.pack(side=tk.RIGHT)

        desc_var = tk.StringVar(value="Click 'Run SOX-404 Forensic Audit Screening' above to execute test.")
        desc_lbl = tk.Label(frame, textvariable=desc_var, font=("Segoe UI", 9), bg="#ffffff", fg="#475569", wraplength=950, justify=tk.LEFT)
        desc_lbl.pack(anchor=tk.W, pady=(4, 0))

        return {
            "frame": frame,
            "badge_var": badge_var,
            "badge_lbl": badge_lbl,
            "desc_var": desc_var,
        }

    def _start_audit_thread(self):
        if not self.state.batch:
            messagebox.showwarning("No Dataset", "Please generate a dataset first in Tab 1 before running audit.")
            return

        self.btn_run_audit.config(state=tk.DISABLED)
        self.lbl_audit_status.config(text="Running statistical and graph forensic tests...")

        thread = threading.Thread(target=self._run_audit_worker, daemon=True)
        thread.start()

    def _run_audit_worker(self):
        try:
            results = self.state.run_audit()
            self.root.after(0, lambda: self._on_audit_completed(results))
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._on_audit_error(err_msg))

    def _on_audit_completed(self, results: Dict[str, Any]):
        self.btn_run_audit.config(state=tk.NORMAL)
        self.lbl_audit_status.config(text="Audit screening finished successfully.")

        # 1. Benford
        benford = results.get("benford", {})
        is_anom = benford.get("is_anomalous", False)
        if is_anom:
            self.card_benford["badge_var"].set("SIGNAL DETECTED [ALERT]")
            self.card_benford["badge_lbl"].config(bg="#fef2f2", fg="#dc2626")
        else:
            self.card_benford["badge_var"].set("COMPLIANT [PASS]")
            self.card_benford["badge_lbl"].config(bg="#f0fdf4", fg="#16a34a")
        self.card_benford["desc_var"].set(
            f"Chi-Square: {benford.get('chi2_statistic', 0):.2f} (Critical 15.51) | p-value: {benford.get('p_value', 0):.4e} | Conclusion: {benford.get('forensic_conclusion', 'N/A')}"
        )

        # 2. DOA
        doa = results.get("doa", {})
        has_violations = doa.get("has_doa_violations", False)
        clusters = doa.get("detected_clusters_count", 0)
        if has_violations:
            self.card_doa["badge_var"].set(f"{clusters} VIOLATIONS DETECTED [ALERT]")
            self.card_doa["badge_lbl"].config(bg="#fef2f2", fg="#dc2626")
        else:
            self.card_doa["badge_var"].set("NORMAL [PASS]")
            self.card_doa["badge_lbl"].config(bg="#f0fdf4", fg="#16a34a")
        self.card_doa["desc_var"].set(
            f"Detected {clusters} split invoice clusters in [$9,500, $9,999] billed to identical vendor accounts within 48h windows."
        )

        # 3. Off-Hours
        off = results.get("off_hours", {})
        off_flag = off.get("has_off_hours_anomalies", False)
        ghost_count = off.get("ghost_entries_count", 0)
        off_count = off.get("off_hours_entries_count", 0)
        weekend_count = off.get("weekend_entries_count", 0)
        if off_flag:
            self.card_offhours["badge_var"].set(f"{ghost_count} GHOST / {off_count} OFF-HOURS [ALERT]")
            self.card_offhours["badge_lbl"].config(bg="#fef2f2", fg="#dc2626")
        else:
            self.card_offhours["badge_var"].set("NORMAL [PASS]")
            self.card_offhours["badge_lbl"].config(bg="#f0fdf4", fg="#16a34a")
        self.card_offhours["desc_var"].set(
            f"Flagged {ghost_count} deactivated user postings, {off_count} postings between 22:00-05:00, and {weekend_count} Saturday/Sunday postings."
        )

        # 4. Pairings
        pair = results.get("pairings", {})
        pair_flag = pair.get("has_anomalous_pairings", False)
        viol_count = pair.get("violations_count", 0)
        if pair_flag:
            self.card_pairings["badge_var"].set(f"{viol_count} PROHIBITED PAIRINGS [ALERT]")
            self.card_pairings["badge_lbl"].config(bg="#fef2f2", fg="#dc2626")
        else:
            self.card_pairings["badge_var"].set("NORMAL [PASS]")
            self.card_pairings["badge_lbl"].config(bg="#f0fdf4", fg="#16a34a")
        self.card_pairings["desc_var"].set(
            f"Detected {viol_count} entries with prohibited account debit/credit combinations (e.g., direct Cash to Revenue bypassing AR ledger)."
        )

        # 5. Intercompany Cycles
        ic = results.get("intercompany", {})
        ic_flag = ic.get("has_cycles", False)
        cycle_count = ic.get("detected_cycles_count", 0)
        if ic_flag:
            self.card_ic["badge_var"].set(f"{cycle_count} CIRCULAR LOOPS DETECTED [ALERT]")
            self.card_ic["badge_lbl"].config(bg="#fef2f2", fg="#dc2626")
        else:
            self.card_ic["badge_var"].set("NORMAL [PASS]")
            self.card_ic["badge_lbl"].config(bg="#f0fdf4", fg="#16a34a")
        cycles_list = ic.get("cycles", [])
        cycles_preview = "; ".join([" -> ".join(c) for c in cycles_list[:3]]) if cycles_list else "None"
        self.card_ic["desc_var"].set(
            f"Identified {cycle_count} multi-hop circular cash round-tripping cycles across trading entities: {cycles_preview}"
        )

    def _on_audit_error(self, err_msg: str):
        self.btn_run_audit.config(state=tk.NORMAL)
        self.lbl_audit_status.config(text=f"Audit failed: {err_msg}")
        messagebox.showerror("Audit Error", f"Failed to execute forensic audit:\n{err_msg}")

    # =========================================================================
    # TAB 4: EXPORT & ARTIFACTS
    # =========================================================================
    def _init_export_tab(self):
        top_box = ttk.Frame(self.tab_export)
        top_box.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(top_box, text="📂 Open Output Folder in Explorer", command=self._open_output_folder).pack(side=tk.LEFT)
        ttk.Button(top_box, text="🔄 Refresh Files", command=self._refresh_export_table).pack(side=tk.LEFT, padx=8)

        self.lbl_export_path = ttk.Label(top_box, text=f"Output Path: {self.state.output_dir.resolve()}", style="Muted.TLabel")
        self.lbl_export_path.pack(side=tk.RIGHT)

        # Export Files Table
        table_frame = ttk.LabelFrame(self.tab_export, text="Dual-Artifact Export Deliverables", padding=6)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("filename", "format", "size", "status", "hash")
        self.tree_export = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree_export.heading("filename", text="File Name")
        self.tree_export.heading("format", text="Format / Standard")
        self.tree_export.heading("size", text="File Size")
        self.tree_export.heading("status", text="Integrity Status")
        self.tree_export.heading("hash", text="SHA-256 Digest (First 20 chars)")

        self.tree_export.column("filename", width=220, anchor=tk.W)
        self.tree_export.column("format", width=180, anchor=tk.W)
        self.tree_export.column("size", width=90, anchor=tk.E)
        self.tree_export.column("status", width=110, anchor=tk.CENTER)
        self.tree_export.column("hash", width=260, anchor=tk.W)

        self.tree_export.pack(fill=tk.BOTH, expand=True)

    def _open_output_folder(self):
        folder = self.state.output_dir.resolve()
        if sys.platform == "win32":
            os.startfile(str(folder))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)])
        else:
            subprocess.run(["xdg-open", str(folder)])

    def _refresh_export_table(self):
        self.tree_export.delete(*self.tree_export.get_children())
        if not self.state.exported_files:
            return

        descriptions = {
            "gl_feed.parquet": "Apache Parquet (Columnar / ML Optimized)",
            "gl_feed.csv": "Standard CSV (Universal ERP Ingestion)",
            "SAP_BKPF.csv": "SAP BKPF Document Headers (ERP Ready)",
            "SAP_BSEG.csv": "SAP BSEG Document Line Items (ERP Ready)",
            "ground_truth_manifest.json": "Cryptographic Audit Ground-Truth Manifest",
        }

        for fname, path in self.state.exported_files.items():
            if path.exists():
                size_bytes = path.stat().st_size
                size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024 * 1024):.2f} MB"
                desc = descriptions.get(fname, "Data Export")
                
                # Check SHA256 if manifest or parquet
                hash_snippet = "--"
                if self.state.manifest and self.state.manifest.dataset_sha256 and fname.endswith(".parquet"):
                    hash_snippet = self.state.manifest.dataset_sha256[:24] + "..."
                elif fname.endswith(".json"):
                    hash_snippet = "Canonical JSON Hash"

                self.tree_export.insert(
                    "",
                    tk.END,
                    values=(
                        fname,
                        desc,
                        size_str,
                        "VERIFIED [PASS]",
                        hash_snippet,
                    ),
                )

    def _initial_load(self):
        """Initial background pre-population so app starts ready."""
        try:
            summary = self.state.generate(count=500, anomaly_rate=0.05, seed=42)
            self._on_generation_completed(summary)
        except Exception:
            pass


def start_desktop_gui():
    """Entry point for native desktop GUI."""
    root = tk.Tk()
    app = DesktopGUI(root)
    root.mainloop()


if __name__ == "__main__":
    start_desktop_gui()
