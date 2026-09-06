"""Tests for Web and Desktop GUIs of the Enterprise General Ledger Fuzzer."""

from decimal import Decimal
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch, MagicMock

from gl_fuzzer.web_gui import GLAppState, GLWebRequestHandler
from gl_fuzzer.desktop_gui import DesktopGUI


class TestGLAppState(unittest.TestCase):
    """Test suite for GUI backend application state."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state = GLAppState()
        self.state.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_state_generate_and_summary(self):
        summary = self.state.generate(count=100, anomaly_rate=0.05, seed=42)

        self.assertEqual(summary["status"], "READY")
        self.assertGreaterEqual(summary["total_entries"], 90)
        self.assertGreater(summary["total_lines"], 180)
        self.assertTrue(summary["is_globally_balanced"])
        self.assertEqual(Decimal(summary["balance_delta"]), Decimal("0.00"))
        self.assertIn("sample_entries", summary)
        self.assertGreater(len(summary["sample_entries"]), 0)

        # Verify export files exist
        for fname, fpath in self.state.exported_files.items():
            self.assertTrue(fpath.exists(), f"Export file {fname} should exist")

    def test_state_audit_screening(self):
        self.state.generate(count=100, anomaly_rate=0.08, seed=42)
        audit_res = self.state.run_audit()

        self.assertIn("benford", audit_res)
        self.assertIn("doa", audit_res)
        self.assertIn("off_hours", audit_res)
        self.assertIn("pairings", audit_res)
        self.assertIn("intercompany", audit_res)

        # Check Benford fields
        self.assertIn("chi2_statistic", audit_res["benford"])
        self.assertIn("p_value", audit_res["benford"])
        self.assertIn("forensic_conclusion", audit_res["benford"])

        # Check DOA fields
        self.assertIn("has_doa_violations", audit_res["doa"])
        self.assertIn("detected_clusters_count", audit_res["doa"])

    def test_state_empty_audit(self):
        empty_state = GLAppState()
        res = empty_state.run_audit()
        self.assertIn("error", res)


class TestDesktopGUI(unittest.TestCase):
    """Test suite for native Desktop GUI."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window during tests
        self.app = DesktopGUI(self.root)

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_desktop_gui_presets(self):
        # Apply Quick Smoke Test preset
        self.app._apply_preset(200, 0.02, [True, True, False, False, False])
        self.assertEqual(self.app.entry_count_var.get(), 200)
        self.assertAlmostEqual(self.app.anomaly_rate_var.get(), 0.02)
        self.assertTrue(self.app.anom_smurfing_var.get())
        self.assertTrue(self.app.anom_ghost_var.get())
        self.assertFalse(self.app.anom_benford_var.get())

        # Apply Clean Baseline preset
        self.app._apply_preset(1000, 0.00, [False, False, False, False, False])
        self.assertEqual(self.app.entry_count_var.get(), 1000)
        self.assertEqual(self.app.anomaly_rate_var.get(), 0.00)
        self.assertFalse(self.app.anom_smurfing_var.get())

    def test_desktop_gui_filter_and_selection(self):
        summary = self.app.state.generate(count=80, anomaly_rate=0.1, seed=42)
        self.app._on_generation_completed(summary)

        # Filter by Clean Only
        self.app.filter_status_var.set("Clean Only")
        self.app._filter_entries()
        clean_count = len(self.app.tree_entries.get_children())
        self.assertGreater(clean_count, 0)

        # Filter by Anomalies Only
        self.app.filter_status_var.set("Anomalies Only")
        self.app._filter_entries()
        anom_count = len(self.app.tree_entries.get_children())

        # Reset filter
        self.app._clear_filters()
        all_count = len(self.app.tree_entries.get_children())
        self.assertEqual(clean_count + anom_count, all_count)

        # Select first item and verify line item table population
        first_item = self.app.tree_entries.get_children()[0]
        self.app.tree_entries.selection_set(first_item)
        self.app._on_entry_selected(None)
        line_items = self.app.tree_lines.get_children()
        self.assertGreaterEqual(len(line_items), 2)  # At least 1 debit and 1 credit


if __name__ == "__main__":
    unittest.main()
