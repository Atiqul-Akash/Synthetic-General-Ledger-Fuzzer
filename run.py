"""User-friendly interactive launcher for the Synthetic General Ledger Fuzzer."""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path


def print_banner():
    print(r"""
===============================================================================
              SYNTHETIC GENERAL LEDGER (GL) FUZZER
       Double-Entry Accounting Synthesis & Calibrated Anomaly Studio
            Made with <3 by Atiqul-Akash | GitHub: Atiqul-Akash
===============================================================================
""")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--web", "-w", "web"):
            from gl_fuzzer.web_gui import start_web_gui
            start_web_gui()
            return
        elif arg in ("--desktop", "-d", "desktop"):
            from gl_fuzzer.desktop_gui import start_desktop_gui
            start_desktop_gui()
            return
        elif arg in ("--test", "-t", "test"):
            subprocess.run([sys.executable, "-m", "pytest", "-v"])
            return

    print_banner()
    print("Select an option to launch:")
    print("  [1] Modern Web GUI (Interactive Dashboard in Browser - Recommended)")
    print("  [2] Native Windows Desktop GUI (Offline Window)")
    print("  [3] Generate 1,000 Sample Ledger Entries (Parquet, CSV, SAP BSEG, ACDOCA)")
    print("  [4] Run SOX-404 Forensic Audit on Generated Dataset")
    print("  [5] Run Complete Automated Test Suite (pytest - 291 tests)")
    print("  [6] Exit")
    print()

    try:
        choice = input("Enter choice (1-6) [default: 1]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return

    if not choice or choice == "1":
        print("\nLaunching Modern Web GUI at http://localhost:8080...")
        from gl_fuzzer.web_gui import start_web_gui
        start_web_gui()
    elif choice == "2":
        print("\nLaunching Native Windows Desktop GUI...")
        from gl_fuzzer.desktop_gui import start_desktop_gui
        start_desktop_gui()
    elif choice == "3":
        print("\nGenerating dataset...")
        subprocess.run([
            sys.executable, "-m", "gl_fuzzer.cli", "generate",
            "--count", "1000", "--anomaly-rate", "0.05", "--acdoca",
            "--out-dir", "./output", "--export-formats", "parquet,csv,sap"
        ])
    elif choice == "4":
        p_path = Path("./output/gl_feed.parquet")
        if not p_path.exists():
            print("\nDataset not found in ./output. Synthesizing fresh dataset first...")
            subprocess.run([
                sys.executable, "-m", "gl_fuzzer.cli", "generate",
                "--count", "1000", "--anomaly-rate", "0.05", "--acdoca",
                "--out-dir", "./output", "--export-formats", "parquet,csv,sap"
            ])
        print("\nRunning SOX-404 forensic audit...")
        subprocess.run([
            sys.executable, "-m", "gl_fuzzer.cli", "audit-report",
            "--dataset", "./output/gl_feed.parquet",
            "--manifest", "./output/ground_truth_manifest.json"
        ])
    elif choice == "5":
        print("\nRunning automated tests (228 tests)...")
        subprocess.run([sys.executable, "-m", "pytest", "-v"])
    elif choice == "6":
        print("Goodbye!")
        return
    else:
        print("Invalid selection. Defaulting to Modern Web GUI...")
        from gl_fuzzer.web_gui import start_web_gui
        start_web_gui()


if __name__ == "__main__":
    main()
