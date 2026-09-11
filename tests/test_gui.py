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
        self.assertIn("acdoca_feed.parquet", self.state.exported_files)
        self.assertIn("acdoca_feed.csv", self.state.exported_files)
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

    def test_state_fuzzing_campaign(self):
        res = self.state.run_fuzzing_campaign(iterations=2, count=20, target="mock")
        self.assertIn("total_entries_posted", res)
        self.assertIn("iteration_reports", res)
        self.assertEqual(res["total_entries_posted"], 40)

    def test_state_tax_report(self):
        self.state.generate(count=50, anomaly_rate=0.0, seed=42)
        res = self.state.run_tax_report(jurisdiction="EU_DE", period="2026-Q1")
        self.assertEqual(res["jurisdiction"], "EU_DE")
        self.assertIn("net_tax_payable", res)

    def test_state_apt_campaign(self):
        res = self.state.run_apt_campaign(campaign_type="INVENTORY_MAP_CREEP_AND_OBSOLESCENCE", seed=42)
        self.assertEqual(res["campaign_type"], "INVENTORY_MAP_CREEP_AND_OBSOLESCENCE")
        self.assertGreaterEqual(len(res["milestones"]), 3)
        self.assertGreater(res["vouchers_count"], 0)

    def test_state_mdm_audit(self):
        res = self.state.run_mdm_audit(seed=42, inject_anomalies=True)
        self.assertGreater(res["total_findings"], 0)
        self.assertGreater(res["vendor_count"], 0)
        self.assertIn("screening", res)


    def test_state_remediation(self):
        res = self.state.generate_remediation(rule_name="RULE_WHT_EVASION")
        self.assertIn("vulnerability_title", res)
        self.assertIn("GGB0", res["code_or_rule"])
        self.assertGreater(len(res["compensating_controls"]), 0)

    def test_state_agent_dialogue(self):
        res = self.state.run_agent_dialogue(persona="EXECUTIVE_CFO", voucher="VCH-1234", amount="$99,000.00")
        self.assertEqual(res["target_voucher_id"], "VCH-1234")
        self.assertGreaterEqual(len(res["turns"]), 4)
        self.assertIn("eml_download", res)

    def test_state_legacy_export(self):
        res_x12 = self.state.run_legacy_export(protocol="ANSI_X12_810", count=2, amount=1500.00)
        self.assertEqual(res_x12["protocol"], "ANSI_X12_810")
        self.assertFalse(res_x12["is_binary"])
        self.assertIn("BIG*", res_x12["preview"])

        res_nacha = self.state.run_legacy_export(protocol="NACHA_ACH", count=3, amount=500.00)
        self.assertEqual(res_nacha["protocol"], "NACHA_ACH")
        self.assertEqual(res_nacha["encoding"], "ascii")





class TestDesktopGUI(unittest.TestCase):
    """Test suite for native Desktop GUI."""
    root = None
    app = None

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
            cls.app = DesktopGUI(cls.root)
        except Exception as e:
            cls.root = None
            cls.app = None

    @classmethod
    def tearDownClass(cls):
        if cls.root is not None:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if self.app is None:
            self.skipTest("Tkinter GUI not available in this test environment")

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

    def test_desktop_gui_enterprise_tab(self):
        # Verify enterprise tab variables exist
        self.assertEqual(self.app.tax_jurisdiction_var.get(), "GLOBAL")
        self.assertFalse(self.app.enable_wht_var.get())
        self.assertFalse(self.app.enable_subledgers_var.get())
        self.assertEqual(self.app.fuzz_target_var.get(), "mock")

        # Test connector probe execution
        self.app._probe_connectors()
        probe_text = self.app.txt_conn_results.get("1.0", tk.END)
        self.assertIn("SAP OData API", probe_text)
        self.assertIn("Embedded Kafka", probe_text)

    def test_desktop_gui_frontier_tab(self):
        # Verify frontier tab widgets and variables
        self.assertEqual(self.app.apt_campaign_var.get(), "INVENTORY_MAP_CREEP_AND_OBSOLESCENCE")
        self.assertTrue(self.app.mdm_inject_anom_var.get())
        self.assertEqual(self.app.remediation_rule_var.get(), "RULE_WHT_EVASION")

        # Test sync completion handlers
        fake_apt = {
            "campaign_id": "APT-TEST-001",
            "campaign_type": "INVENTORY_MAP_CREEP_AND_OBSOLESCENCE",
            "total_quarters_active": 4,
            "total_diverted_amount": 42000.00,
            "actors": [{"role": "Rogue Buyer", "name": "Eve", "system_id": "U-123"}],
            "phases": [{"phase": "INFILTRATION"}],
            "vouchers": [],
            "milestones": [{"quarter": 1, "phase": "INFILTRATION", "action_summary": "Test action"}],
        }
        self.app._on_apt_completed(fake_apt)
        apt_text = self.app.txt_apt_results.get("1.0", tk.END)
        self.assertIn("APT-TEST-001", apt_text)
        self.assertIn("INVENTORY_MAP_CREEP_AND_OBSOLESCENCE", apt_text)

        fake_mdm = {
            "vendor_count": 10,
            "customer_count": 8,
            "employee_count": 12,
            "total_findings": 1,
            "findings": [{"anomaly_type": "SYBIL_VENDOR_DUPLICATE", "description": "Near-duplicate found"}],
        }
        self.app._on_mdm_completed(fake_mdm)
        mdm_text = self.app.txt_mdm_results.get("1.0", tk.END)
        self.assertIn("SYBIL_VENDOR_DUPLICATE", mdm_text)

        fake_patch = {
            "patch_id": "PATCH-001",
            "target_vulnerability": "RULE_WHT_EVASION",
            "verification_status": "VERIFIED_NEUTRALIZED",
            "remediation_type": "SAP_GGB0_VALIDATION_RULE",
            "code_or_rule_definition": "CHECK BKPF-BLART = 'KZ'",
            "compensating_control": {
                "control_id": "SOX-AP-09",
                "review_activity": "Sample disbursements",
                "frequency": "WEEKLY",
                "evidence_required": "Signoff sheet",
            },
        }
        self.app._on_remediation_completed(fake_patch)
        rem_text = self.app.txt_remediation_results.get("1.0", tk.END)
        self.assertIn("PATCH-001", rem_text)
        self.assertIn("SOX-AP-09", rem_text)

    def test_desktop_gui_agent_and_legacy_tabs(self):
        # Verify Tab 7 & Tab 8 widgets exist
        self.assertIsNotNone(self.app.tab_agents)
        self.assertIsNotNone(self.app.tab_legacy)

        fake_thread = {
            "thread_id": "SET-9999",
            "campaign_id": "CAMP-TEST",
            "persona": "EXECUTIVE_CFO",
            "pretext_scenario": "PROJECT_APOLLO",
            "subject": "Executive Authorization Override",
            "target_voucher_id": "VCH-8888",
            "audit_notes": "Bypassed SOX dual approval",
            "turns": [
                {
                    "turn_index": 1,
                    "speaker_role": "FRAUD_AGENT",
                    "speaker_name": "Arthur (CFO)",
                    "message_body": "Execute wire immediately",
                    "persuasion_tactic": "URGENCY",
                }
            ],
        }
        self.app._on_agent_dialogue_completed(fake_thread)
        agent_txt = self.app.txt_dialogue_results.get("1.0", tk.END)
        self.assertIn("SET-9999", agent_txt)
        self.assertIn("Executive Authorization Override", agent_txt)

        fake_legacy = {
            "protocol": "ANSI_X12_810",
            "byte_size": 350,
            "record_count": 12,
            "encoding": "utf-8",
            "anomalies": ["DELIMITER_CORRUPTION"],
            "preview": "ISA*00*...BIG*20260414*INV01~",
        }
        self.app._on_legacy_protocol_completed(fake_legacy)
        legacy_txt = self.app.txt_legacy_results.get("1.0", tk.END)
        self.assertIn("ANSI_X12_810", legacy_txt)
        self.assertIn("DELIMITER_CORRUPTION", legacy_txt)


if __name__ == "__main__":
    unittest.main()

