"""Modern, user-friendly local Web GUI for the Synthetic General Ledger Fuzzer."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import http.server
import io
import json
import os
from pathlib import Path
import shutil
import socketserver
import threading
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, JournalEntry
from gl_fuzzer.models.manifest import AnomalyRecord, GroundTruthManifest
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.anomalies.pipeline import AnomalyPipeline
from gl_fuzzer.anomalies.smurfing import SmurfingMutator
from gl_fuzzer.anomalies.ghost_entries import GhostEntriesMutator
from gl_fuzzer.anomalies.benford_skew import BenfordSkewMutator
from gl_fuzzer.anomalies.anomalous_pairings import AnomalousPairingsMutator
from gl_fuzzer.anomalies.round_tripping import CircularRoundTrippingMutator
from gl_fuzzer.verification.invariants import InvariantVerifier
from gl_fuzzer.verification.audit_metrics import ForensicAuditEvaluator
from gl_fuzzer.exporters.parquet_exporter import ParquetGLExporter
from gl_fuzzer.exporters.csv_exporter import CSVGLExporter
from gl_fuzzer.exporters.sap_bseg_exporter import SAPBSEGExporter
from gl_fuzzer.exporters.acdoca_exporter import SAPACDOCAExporter
from gl_fuzzer.exporters.manifest_exporter import ManifestExporter


class GLAppState:
    """Singleton state storing current generated batch, manifest, and export files."""

    def __init__(self):
        self._lock = threading.RLock()
        self.batch: Optional[Batch] = None
        self.manifest: Optional[GroundTruthManifest] = None
        self.anomaly_records: List[AnomalyRecord] = []
        self.output_dir: Path = Path("./web_gui_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.exported_files: Dict[str, Path] = {}

    def generate(
        self,
        count: int = 1000,
        anomaly_rate: float = 0.05,
        seed: Optional[int] = 42,
        enabled_anomalies: Optional[Dict[str, bool]] = None,
        tax_jurisdiction: Optional[str] = None,
        enable_wht: bool = False,
        enable_subledgers: bool = False,
    ) -> Dict[str, Any]:
        """Synthesizes a new batch, fuzzes it, verifies invariants, and writes exports."""
        with self._lock:
            coa = ChartOfAccounts.create_default()

            tax_eng = None
            if tax_jurisdiction:
                from gl_fuzzer.tax import TaxLocalizationEngine, TaxJurisdiction
                try:
                    jur_enum = TaxJurisdiction(tax_jurisdiction.upper())
                except ValueError:
                    jur_enum = TaxJurisdiction.GLOBAL
                tax_eng = TaxLocalizationEngine(default_jurisdiction=jur_enum)

            inv = None
            twm = None
            sfe = None
            if enable_subledgers:
                from gl_fuzzer.subledgers import WarehouseInventory, ThreeWayMatchingEngine, SalesOrderFulfillmentEngine
                inv = WarehouseInventory.create_default()
                twm = ThreeWayMatchingEngine(inventory=inv, coa=coa)
                sfe = SalesOrderFulfillmentEngine(inventory=inv, coa=coa)

            engine = BaseSynthesisEngine(
                coa=coa,
                seed=seed,
                tax_engine=tax_eng,
                inventory=inv,
                three_way_match=twm,
                sales_fulfillment=sfe,
            )

            batch_id = f"WEB_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            self.batch = engine.generate_batch(batch_id=batch_id, target_entry_count=count)

            enabled = enabled_anomalies or {
                "smurfing": True,
                "ghost": True,
                "benford": True,
                "pairings": True,
                "round_trip": True,
            }

            active_mutators = []
            if enabled.get("smurfing", True):
                active_mutators.append(SmurfingMutator())
            if enabled.get("ghost", True):
                active_mutators.append(GhostEntriesMutator())
            if enabled.get("benford", True):
                active_mutators.append(BenfordSkewMutator())
            if enabled.get("pairings", True):
                active_mutators.append(AnomalousPairingsMutator())
            if enabled.get("round_trip", True):
                active_mutators.append(CircularRoundTrippingMutator())

            pipeline = AnomalyPipeline(coa=coa, mutators=active_mutators, seed=seed)
            self.anomaly_records = pipeline.inject_anomalies(self.batch, overall_anomaly_rate=anomaly_rate)

            if enable_wht:
                from gl_fuzzer.tax.withholding import WithholdingTaxEngine
                wht_eng = WithholdingTaxEngine()
                for e in self.batch.entries:
                    if e.document_type == DocumentType.KZ:
                        wht_eng.apply_wht_to_payment_entry(e)

            # Sort all batch entries chronologically for realistic general ledger posting order
            self.batch.entries.sort(key=lambda e: (e.posting_date, e.entry_time))

            # Invariant Verification
            inv_report = InvariantVerifier.verify_batch(self.batch)

            anom_entry_ids = set()
            for r in self.anomaly_records:
                anom_entry_ids.update(r.affected_entry_ids)

            anom_breakdown = dict(Counter(rec.anomaly_type.value for rec in self.anomaly_records))

            self.manifest = GroundTruthManifest(
                dataset_id=batch_id,
                generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                seed=seed,
                total_batches=1,
                total_entries=len(self.batch.entries),
                total_lines=self.batch.total_line_count,
                clean_entries_count=len(self.batch.entries) - len(anom_entry_ids),
                anomalous_entries_count=len(anom_entry_ids),
                anomaly_rate=round(len(anom_entry_ids) / len(self.batch.entries), 4) if self.batch.entries else 0.0,
                anomaly_breakdown=anom_breakdown,
                anomalies=self.anomaly_records,
            )

            # Auto-export files for instant download
            p_path = self.output_dir / "gl_feed.parquet"
            _, p_hash = ParquetGLExporter.export(self.batch.entries, p_path)
            self.manifest.dataset_sha256 = p_hash
            self.exported_files["gl_feed.parquet"] = p_path

            c_path = self.output_dir / "gl_feed.csv"
            CSVGLExporter.export(self.batch.entries, c_path)
            self.exported_files["gl_feed.csv"] = c_path

            sap_results = SAPBSEGExporter.export(self.batch.entries, self.output_dir / "sap")
            self.exported_files["SAP_BKPF.csv"] = sap_results["BKPF"][0]
            self.exported_files["SAP_BSEG.csv"] = sap_results["BSEG"][0]

            # Export SAP S/4HANA ACDOCA Universal Journal
            acdoca_p_path = self.output_dir / "acdoca_feed.parquet"
            SAPACDOCAExporter.export_parquet(self.batch.entries, acdoca_p_path)
            self.exported_files["acdoca_feed.parquet"] = acdoca_p_path

            acdoca_c_path = self.output_dir / "acdoca_feed.csv"
            SAPACDOCAExporter.export_csv(self.batch.entries, acdoca_c_path)
            self.exported_files["acdoca_feed.csv"] = acdoca_c_path

            m_path = self.output_dir / "ground_truth_manifest.json"
            ManifestExporter.export_json(self.manifest, m_path)
            self.exported_files["ground_truth_manifest.json"] = m_path

            return self.get_summary(inv_report)

    def get_summary(self, inv_report: Optional[Any] = None) -> Dict[str, Any]:
        """Returns JSON summary of current generation."""
        with self._lock:
            if not self.batch or not self.manifest:
                return {"status": "EMPTY"}

            if inv_report is None:
                inv_report = InvariantVerifier.verify_batch(self.batch)

            # Sample transactions for preview table (up to 500 entries, ensuring all anomalies are included)
            if len(self.batch.entries) <= 500:
                preview_source = self.batch.entries
            else:
                anom_entries = [e for e in self.batch.entries if e.is_anomaly]
                clean_entries = [e for e in self.batch.entries if not e.is_anomaly]
                needed_clean = max(0, 500 - len(anom_entries))
                preview_source = anom_entries + clean_entries[:needed_clean]
                preview_source.sort(key=lambda x: (x.posting_date, x.entry_time))

            sample_entries = []
            for e in preview_source:
                lines_data = []
                for l in e.lines:
                    lines_data.append({
                        "line_id": l.line_id,
                        "line_number": l.line_number,
                        "account_code": l.account_code,
                        "account_name": l.account_name,
                        "debit_credit": l.debit_credit.value,
                        "amount": f"{l.amount:.2f}",
                        "posting_key": l.posting_key,
                        "vendor_id": l.vendor_id or "",
                        "customer_id": l.customer_id or "",
                        "trading_partner": l.trading_partner or "",
                        "cost_center": l.cost_center or "",
                        "line_text": l.line_text,
                    })

                sample_entries.append({
                    "entry_id": e.entry_id,
                    "document_number": e.document_number,
                    "company_code": e.company_code,
                    "document_type": e.document_type.value,
                    "posting_date": e.posting_date,
                    "entry_time": e.entry_time,
                    "created_by": e.created_by,
                    "business_cycle": e.business_cycle,
                    "header_text": e.header_text,
                    "total_debits": f"{e.total_debits:.2f}",
                    "total_credits": f"{e.total_credits:.2f}",
                    "is_balanced": e.is_balanced,
                    "is_anomaly": e.is_anomaly,
                    "anomaly_ids": e.anomaly_ids,
                    "lines": lines_data,
                })

            return {
                "status": "READY",
                "batch_id": self.batch.batch_id,
                "total_entries": len(self.batch.entries),
                "total_lines": self.batch.total_line_count,
                "total_debits": f"{self.batch.total_debits:.2f}",
                "total_credits": f"{self.batch.total_credits:.2f}",
                "is_globally_balanced": inv_report.is_globally_balanced,
                "balance_delta": f"{self.batch.total_debits - self.batch.total_credits:.2f}",
                "clean_entries_count": self.manifest.clean_entries_count,
                "anomalous_entries_count": self.manifest.anomalous_entries_count,
                "anomaly_rate": self.manifest.anomaly_rate,
                "anomaly_breakdown": self.manifest.anomaly_breakdown,
                "sample_entries": sample_entries,
                "dataset_sha256": self.manifest.dataset_sha256,
            }

    def run_audit(self) -> Dict[str, Any]:
        """Runs the 5 SOX 404 audit screening tests on current batch."""
        with self._lock:
            if not self.batch:
                return {"error": "No dataset generated yet"}

            benford = ForensicAuditEvaluator.evaluate_benford_compliance(self.batch.entries)
            doa = ForensicAuditEvaluator.detect_doa_split_clusters(self.batch.entries)
            off_hours = ForensicAuditEvaluator.detect_off_hours_and_ghost_entries(self.batch.entries)
            pairings = ForensicAuditEvaluator.detect_anomalous_pairings(self.batch.entries)
            ic = ForensicAuditEvaluator.detect_intercompany_cycles(self.batch.entries)

            return {
                "benford": benford,
                "doa": doa,
                "off_hours": off_hours,
                "pairings": pairings,
                "intercompany": ic,
            }

    def run_fuzzing_campaign(self, iterations: int = 3, count: int = 50, target: str = "mock") -> Dict[str, Any]:
        """Runs dynamic security fuzzing feedback loop against target."""
        with self._lock:
            from gl_fuzzer.fuzzing import FuzzingCampaign, MockEnterpriseERPApplication, RelationalLedgerTarget
            coa = ChartOfAccounts.create_default()
            t = RelationalLedgerTarget(coa=coa) if target == "sqlite" else MockEnterpriseERPApplication(coa=coa)
            camp = FuzzingCampaign(target=t, coa=coa)
            report = camp.run(iterations=iterations, entries_per_iteration=count)
            return report.model_dump(mode="json")

    def run_tax_report(self, jurisdiction: str = "EU_DE", period: str = "2026-Q1") -> Dict[str, Any]:
        """Runs tax return generation on current dataset."""
        with self._lock:
            from gl_fuzzer.tax import TaxLocalizationEngine, TaxJurisdiction
            if not self.batch or not self.batch.entries:
                return {"error": "No dataset generated yet"}
            try:
                jur_enum = TaxJurisdiction(jurisdiction.upper())
            except ValueError:
                jur_enum = TaxJurisdiction.GLOBAL
            eng = TaxLocalizationEngine(default_jurisdiction=jur_enum)
            res = eng.generate_tax_return(self.batch.entries, jurisdiction=jur_enum, period_str=period)
            return res.model_dump(mode="json")

    def run_apt_campaign(self, campaign_type: str = "INVENTORY_MAP_CREEP_AND_OBSOLESCENCE", seed: int = 42) -> Dict[str, Any]:
        """Generates a multi-quarter APT adversarial narrative campaign."""
        with self._lock:
            from gl_fuzzer.campaigns import APTNarrativeOrchestrator, APTCampaignType
            coa = ChartOfAccounts.create_default()
            orch = APTNarrativeOrchestrator(coa=coa, seed=seed)
            try:
                ctype = APTCampaignType(campaign_type)
            except ValueError:
                ctype = APTCampaignType.INVENTORY_MAP_CREEP_AND_OBSOLESCENCE
            record, entries = orch.orchestrate_campaign(campaign_type=ctype)
            res = record.model_dump(mode="json")
            res["vouchers_count"] = len(entries)
            return res

    def run_mdm_audit(self, seed: int = 42, inject_anomalies: bool = True) -> Dict[str, Any]:
        """Executes deep Master Data screening across vendors, customers, and employees."""
        with self._lock:
            from gl_fuzzer.mdm import MasterDataManager
            mdm = MasterDataManager.create_default(seed=seed)
            if inject_anomalies:
                mdm.inject_sybil_vendor("VEND_001")
                mdm.tamper_vendor_bank("VEND_002", tamper_date="2026-05-01")
                mdm.inject_employee_collusion("EMP_001")
            screening = mdm.screen_mdm_anomalies()
            findings_count = (
                screening.get("sybil_duplicates_found", 0)
                + screening.get("collusions_found", 0)
                + screening.get("tampered_vendors_found", 0)
            )
            return {
                "total_findings": findings_count,
                "screening": screening,
                "vendor_count": len(mdm.vendors),
                "customer_count": len(mdm.customers),
                "employee_count": len(mdm.employees),
            }

    def generate_remediation(self, rule_name: str = "RULE_WHT_EVASION") -> Dict[str, Any]:
        """Generates automated remediation patches (SAP GGB0, ABAP BAdI, SQL, SOX controls)."""
        with self._lock:
            from gl_fuzzer.remediation import RemediationAdvisor
            patch = RemediationAdvisor.advise_for_finding({
                "finding_type": rule_name,
                "description": f"Audit vulnerability detected for {rule_name}",
            })
            return patch.model_dump(mode="json")

    def run_agent_dialogue(
        self,
        persona: str = "EXECUTIVE_CFO",
        scenario: str = "PROJECT_APOLLO",
        voucher: str = "VCH-2026-9081",
        amount: str = "$125,000.00",
        vendor: str = "Apex Strategic Advisory Partners",
        custom_objections: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generates conversational social engineering thread via Generative LLM Fraud Agent."""
        with self._lock:
            from gl_fuzzer.agents import (
                AgentPersona,
                ExecutivePretextAgent,
                CollusiveVendorAgent,
                AuditorDeceptionAgent,
                MultiTurnDialogueSimulator,
            )
            from gl_fuzzer.documents.email_generator import EmailThreadGenerator

            try:
                p_enum = AgentPersona(persona.upper())
            except ValueError:
                p_enum = AgentPersona.EXECUTIVE_CFO

            sim = MultiTurnDialogueSimulator()
            thread = sim.simulate(
                persona=p_enum,
                scenario=scenario,
                target_voucher_id=voucher,
                custom_objections=custom_objections,
            )

            # Auto-export .eml file for download
            eml_path = self.output_dir / f"{thread.thread_id}.eml"
            EmailThreadGenerator.generate_from_social_engineering_thread(eml_path, thread)
            self.exported_files[f"{thread.thread_id}.eml"] = eml_path

            res = thread.model_dump(mode="json")
            res["eml_download"] = f"/api/download/{thread.thread_id}.eml"
            return res

    def run_legacy_export(
        self,
        protocol: str = "ANSI_X12_810",
        count: int = 5,
        amount: float = 12500.50,
        anomalies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generates valid or fuzzed legacy EDI / Mainframe / Banking stream."""
        with self._lock:
            from gl_fuzzer.legacy_protocols import (
                LegacyProtocolType,
                ProtocolFuzzAnomaly,
                EDIEngine,
                MainframeEngine,
            )

            try:
                proto_enum = LegacyProtocolType(protocol.upper())
            except ValueError:
                proto_enum = LegacyProtocolType.ANSI_X12_810

            applied_anoms = []
            if anomalies:
                for a in anomalies:
                    try:
                        applied_anoms.append(ProtocolFuzzAnomaly(a.upper()))
                    except ValueError:
                        pass

            if proto_enum in (
                LegacyProtocolType.ANSI_X12_810,
                LegacyProtocolType.ANSI_X12_850,
                LegacyProtocolType.ANSI_X12_856,
                LegacyProtocolType.EDIFACT_INVOIC,
                LegacyProtocolType.EDIFACT_ORDERS,
            ):
                result = EDIEngine.generate_edi_payload(
                    protocol=proto_enum,
                    document_id="DOC-2026-9001",
                    date_str="2026-04-14",
                    sender_id="SENDER01",
                    receiver_id="RECEIVER01",
                    amount=Decimal(str(amount)),
                    anomalies=applied_anoms,
                )
                ext = ".edi"
            else:
                mock_records = []
                for i in range(1, count + 1):
                    mock_records.append({
                        "doc_id": f"VCH{i:05d}",
                        "date": "20260414",
                        "account": f"1010{i:04d}",
                        "dr_cr": "CR" if i % 2 == 0 else "DR",
                        "amount": str(amount),
                        "routing": "021000021",
                        "description": f"EXPEDITED SETTLEMENT LINE {i}",
                        "vendor_id": f"VEND{i:04d}",
                        "name": "NORTHERN INDUSTRIAL CORP",
                    })
                result = MainframeEngine.generate_payload(
                    protocol=proto_enum,
                    records=mock_records,
                    anomalies=applied_anoms,
                )
                ext = ".bin" if result.is_binary else ".txt"

            out_filename = f"legacy_payload_{proto_enum.value.lower()}{ext}"
            file_path = self.output_dir / out_filename
            if result.is_binary:
                file_path.write_bytes(result.raw_payload)
                preview_text = f"[Binary Stream: {result.byte_size} bytes in {result.encoding} - Hex: {result.raw_payload[:64].hex()}]"
            else:
                file_path.write_text(result.raw_payload, encoding=result.encoding)
                preview_text = result.raw_payload[:3000]

            self.exported_files[out_filename] = file_path

            return {
                "protocol": proto_enum.value,
                "byte_size": result.byte_size,
                "record_count": result.record_count,
                "is_binary": result.is_binary,
                "encoding": result.encoding,
                "anomalies": [a.value for a in result.applied_anomalies],
                "preview": preview_text,
                "file_path": str(file_path),
                "download_url": f"/api/download/{out_filename}",
            }





# Global app state instance
state = GLAppState()


class GLWebRequestHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP handler serving SPA frontend and REST API."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_html(HTML_DASHBOARD)
        elif path == "/api/status":
            self._send_json(state.get_summary())
        elif path.startswith("/api/download/"):
            filename = path.replace("/api/download/", "")
            file_path = state.exported_files.get(filename)
            if file_path and file_path.exists():
                self._send_file(file_path)
            else:
                self.send_error(404, f"File {filename} not found")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            raw_len = self.headers.get("Content-Length", 0)
            content_length = int(raw_len)
        except (ValueError, TypeError):
            content_length = 0

        if content_length > 10 * 1024 * 1024:
            self.send_error(413, "Payload Too Large")
            return

        try:
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = raw_body.decode("utf-8", errors="replace")
            payload = json.loads(body)
        except Exception:
            payload = {}

        try:
            if path == "/api/generate":
                try:
                    count = max(10, int(payload.get("count", 1000)))
                except Exception:
                    count = 1000
                try:
                    anomaly_rate = max(0.0, min(1.0, float(payload.get("anomaly_rate", 0.05))))
                except Exception:
                    anomaly_rate = 0.05
                seed = int(payload.get("seed", 42)) if payload.get("seed") is not None else None
                enabled_anomalies = payload.get("enabled_anomalies")

                summary = state.generate(
                    count=count,
                    anomaly_rate=anomaly_rate,
                    seed=seed,
                    enabled_anomalies=enabled_anomalies,
                    tax_jurisdiction=payload.get("tax_jurisdiction"),
                    enable_wht=bool(payload.get("enable_wht", False)),
                    enable_subledgers=bool(payload.get("enable_subledgers", False)),
                )
                self._send_json(summary)
            elif path == "/api/audit":
                audit_results = state.run_audit()
                self._send_json(audit_results)
            elif path == "/api/fuzz-loop":
                iterations = int(payload.get("iterations", 3))
                count = int(payload.get("count", 50))
                target = str(payload.get("target", "mock"))
                fuzz_results = state.run_fuzzing_campaign(iterations=iterations, count=count, target=target)
                self._send_json(fuzz_results)
            elif path == "/api/tax-report":
                jurisdiction = str(payload.get("jurisdiction", "EU_DE"))
                period = str(payload.get("period", "2026-Q1"))
                tax_results = state.run_tax_report(jurisdiction=jurisdiction, period=period)
                self._send_json(tax_results)
            elif path == "/api/campaign":
                c_type = str(payload.get("campaign_type", "INVENTORY_MAP_CREEP_AND_OBSOLESCENCE"))
                c_seed = int(payload.get("seed", 42)) if payload.get("seed") is not None else 42
                campaign_res = state.run_apt_campaign(campaign_type=c_type, seed=c_seed)
                self._send_json(campaign_res)
            elif path == "/api/mdm-audit":
                m_seed = int(payload.get("seed", 42)) if payload.get("seed") is not None else 42
                inject_anom = bool(payload.get("inject_anomalies", True))
                mdm_res = state.run_mdm_audit(seed=m_seed, inject_anomalies=inject_anom)
                self._send_json(mdm_res)
            elif path == "/api/remediation":
                rule_name = str(payload.get("rule_name", "RULE_WHT_EVASION"))
                remediation_res = state.generate_remediation(rule_name=rule_name)
                self._send_json(remediation_res)
            elif path == "/api/agent-dialogue":
                agent_res = state.run_agent_dialogue(
                    persona=str(payload.get("persona", "EXECUTIVE_CFO")),
                    scenario=str(payload.get("scenario", "PROJECT_APOLLO")),
                    voucher=str(payload.get("voucher", "VCH-2026-9081")),
                    amount=str(payload.get("amount", "$125,000.00")),
                    vendor=str(payload.get("vendor", "Apex Strategic Advisory Partners")),
                    custom_objections=payload.get("custom_objections"),
                )
                self._send_json(agent_res)
            elif path in ("/api/legacy-export", "/api/legacy-fuzz"):
                legacy_res = state.run_legacy_export(
                    protocol=str(payload.get("protocol", "ANSI_X12_810")),
                    count=int(payload.get("count", 5)),
                    amount=float(payload.get("amount", 12500.50)),
                    anomalies=payload.get("anomalies"),
                )
                self._send_json(legacy_res)
            else:
                self.send_error(404, "Unknown API endpoint")


        except Exception as e:
            self._send_json({"error": str(e), "status": "ERROR"}, status=500)

    def _send_json(self, data: Any, status: int = 200):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html_content: str):
        payload = html_content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, file_path: Path):
        file_size = file_path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        with open(file_path, "rb") as f:
            shutil.copyfileobj(f, self.wfile, length=64 * 1024)

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP logs
        return


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_web_gui(port: int = 8080, open_browser: bool = True):
    """Starts the local web GUI server and opens browser."""
    # Pre-generate a 500 entry sample so the dashboard opens pre-populated
    if not state.batch:
        state.generate(count=500, anomaly_rate=0.06, seed=42)

    httpd = None
    original_port = port
    for p in range(original_port, original_port + 10):
        try:
            httpd = ThreadedTCPServer(("", p), GLWebRequestHandler)
            port = p
            break
        except OSError:
            continue

    if httpd is None:
        raise OSError(f"Could not bind to any port in range {original_port}-{original_port + 9}")

    url = f"http://localhost:{port}"
    print(f"\n[GL Fuzzer Web GUI] Serving at {url}")
    print("Press Ctrl+C in terminal to stop server.\n")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[GL Fuzzer Web GUI] Server stopped.")
        httpd.server_close()


HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Synthetic General Ledger Fuzzer — Studio</title>
  <!-- Tailwind CSS & Chart.js -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .tab-active { border-bottom: 3px solid #2563eb; color: #2563eb; font-weight: 600; }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">

  <!-- Top Navigation Header -->
  <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-md">
          GL
        </div>
        <div>
          <h1 class="text-lg font-bold text-slate-900 leading-tight">Synthetic General Ledger Fuzzer</h1>
          <p class="text-xs text-slate-500 font-medium">Double-Entry Synthesis • Calibrated Micro-Anomalies • Made with ❤️ by <a href="https://github.com/Atiqul-Akash" target="_blank" class="text-blue-600 hover:underline font-semibold">Atiqul-Akash</a></p>
        </div>
      </div>
      <div class="flex items-center space-x-3">
        <span id="invariant-badge" class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <svg class="w-3.5 h-3.5 mr-1.5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
          </svg>
          Double-Entry: Zero-Sum Verified
        </span>
        <button onclick="triggerAudit()" class="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-lg border border-indigo-200 transition">
          Run SOX-404 Screen
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Quick Start Presets Bar -->
    <div class="bg-gradient-to-r from-blue-900 to-indigo-900 text-white rounded-2xl p-5 shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div>
        <span class="text-xs uppercase tracking-wider font-semibold text-blue-300">One-Click Configuration Presets</span>
        <h2 class="text-lg font-bold">Select an Accounting Scenario to Run</h2>
      </div>
      <div class="flex flex-wrap gap-2">
        <button onclick="applyPreset('clean')" class="px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold text-white border border-white/20 transition">
          1. Clean Baseline (0% Anom)
        </button>
        <button onclick="applyPreset('standard')" class="px-3.5 py-2 rounded-xl bg-blue-500 hover:bg-blue-600 text-xs font-semibold text-white shadow transition">
          2. SOX Audit Benchmark (6% Anom)
        </button>
        <button onclick="applyPreset('stress')" class="px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-xs font-semibold text-white shadow transition">
          3. Heavy Stress Test (15% Anom)
        </button>
      </div>
    </div>

    <!-- Parameter Configuration Form Card -->
    <div class="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      <h3 class="text-base font-bold text-slate-900 mb-4 flex items-center">
        <svg class="w-5 h-5 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path></svg>
        Synthesis & Anomaly Controls
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Entry Count Slider -->
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="text-xs font-semibold text-slate-700">Journal Entry Count</label>
            <span id="count-val" class="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">1,000</span>
          </div>
          <input type="range" id="count-slider" min="100" max="10000" step="100" value="1000" oninput="updateSliderLabels()" class="w-full h-2 bg-slate-200 rounded-lg cursor-pointer accent-blue-600">
          <p class="text-[11px] text-slate-400 mt-1">Number of balanced double-entry vouchers to synthesize.</p>
        </div>

        <!-- Anomaly Rate Slider -->
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="text-xs font-semibold text-slate-700">Anomaly Injection Rate</label>
            <span id="rate-val" class="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded">6.0%</span>
          </div>
          <input type="range" id="rate-slider" min="0" max="25" step="1" value="6" oninput="updateSliderLabels()" class="w-full h-2 bg-slate-200 rounded-lg cursor-pointer accent-amber-500">
          <p class="text-[11px] text-slate-400 mt-1">Ratio of entries perturbed by the micro-anomaly pipeline.</p>
        </div>

        <!-- Random Seed -->
        <div>
          <label class="text-xs font-semibold text-slate-700 mb-1.5 block">Deterministic Seed</label>
          <div class="flex space-x-2">
            <input type="number" id="seed-input" value="42" class="w-full px-3 py-1.5 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none">
            <button onclick="document.getElementById('seed-input').value = Math.floor(Math.random() * 100000)" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-xs font-medium rounded-lg text-slate-600">
              Roll
            </button>
          </div>
          <p class="text-[11px] text-slate-400 mt-1">Guarantees exact reproducible datasets.</p>
        </div>
      </div>

      <!-- Calibrated Micro-Anomalies Toggles -->
      <div class="mt-6 pt-5 border-t border-slate-100">
        <label class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 block">Enabled Micro-Anomalies</label>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
          <label class="flex items-center p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl cursor-pointer border border-slate-200/70 transition">
            <input type="checkbox" id="anom-smurfing" checked class="rounded text-blue-600 mr-2.5">
            <div>
              <div class="font-semibold text-slate-800">Smurfing / Split</div>
              <div class="text-[10px] text-slate-500">$9.5k-$10k DOA bypass</div>
            </div>
          </label>

          <label class="flex items-center p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl cursor-pointer border border-slate-200/70 transition">
            <input type="checkbox" id="anom-ghost" checked class="rounded text-blue-600 mr-2.5">
            <div>
              <div class="font-semibold text-slate-800">Off-Hours / Ghost</div>
              <div class="text-[10px] text-slate-500">2-4 AM & Weekend MJEs</div>
            </div>
          </label>

          <label class="flex items-center p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl cursor-pointer border border-slate-200/70 transition">
            <input type="checkbox" id="anom-benford" checked class="rounded text-blue-600 mr-2.5">
            <div>
              <div class="font-semibold text-slate-800">Benford Skew</div>
              <div class="text-[10px] text-slate-500">7, 8, 9 digit spikes</div>
            </div>
          </label>

          <label class="flex items-center p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl cursor-pointer border border-slate-200/70 transition">
            <input type="checkbox" id="anom-pairings" checked class="rounded text-blue-600 mr-2.5">
            <div>
              <div class="font-semibold text-slate-800">Anomalous Pairs</div>
              <div class="text-[10px] text-slate-500">Cash<->Expense / Suspense</div>
            </div>
          </label>

          <label class="flex items-center p-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl cursor-pointer border border-slate-200/70 transition">
            <input type="checkbox" id="anom-roundtrip" checked class="rounded text-blue-600 mr-2.5">
            <div>
              <div class="font-semibold text-slate-800">Circular Round-Trip</div>
              <div class="text-[10px] text-slate-500">A -> B -> C -> A close loop</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Action Button -->
      <div class="mt-6 flex items-center justify-end space-x-3">
        <button id="generate-btn" onclick="triggerGenerate()" class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl shadow-md transition flex items-center">
          <svg id="gen-spinner" class="hidden animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          Generate & Fuzz General Ledger
        </button>
      </div>
    </div>

    <!-- Live KPI Metric Cards -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <span class="text-xs font-medium text-slate-500">Journal Entries</span>
        <div id="metric-entries" class="text-2xl font-bold text-slate-900 mt-1">--</div>
        <span id="metric-lines" class="text-[11px] text-slate-400">-- line items</span>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <span class="text-xs font-medium text-slate-500">Total Debit Volume</span>
        <div id="metric-debits" class="text-xl font-bold text-emerald-600 mt-1">--</div>
        <span class="text-[11px] text-emerald-600 font-medium">Σ(Debits) Exact</span>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <span class="text-xs font-medium text-slate-500">Total Credit Volume</span>
        <div id="metric-credits" class="text-xl font-bold text-emerald-600 mt-1">--</div>
        <span class="text-[11px] text-emerald-600 font-medium">Σ(Credits) Exact</span>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <span class="text-xs font-medium text-slate-500">Double-Entry Delta</span>
        <div id="metric-delta" class="text-2xl font-bold text-blue-600 mt-1">$0.00</div>
        <span class="text-[11px] text-blue-500 font-medium">Strict Zero-Sum</span>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <span class="text-xs font-medium text-slate-500">Anomalies Injected</span>
        <div id="metric-anomalies" class="text-2xl font-bold text-amber-600 mt-1">--</div>
        <span id="metric-rate" class="text-[11px] text-amber-500 font-medium">--% effective</span>
      </div>
    </div>

    <!-- Tabbed Navigation Panels -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <!-- Tabs Header -->
      <div class="border-b border-slate-200 px-6 flex space-x-6 overflow-x-auto">
        <button id="tab-btn-tx" onclick="switchTab('tx')" class="py-4 text-sm font-medium text-slate-500 hover:text-slate-700 tab-active whitespace-nowrap">
          Transaction Explorer
        </button>
        <button id="tab-btn-audit" onclick="switchTab('audit')" class="py-4 text-sm font-medium text-slate-500 hover:text-slate-700 whitespace-nowrap">
          SOX 404 Forensic Screening
        </button>
        <button id="tab-btn-agent" onclick="switchTab('agent')" class="py-4 text-sm font-medium text-slate-500 hover:text-slate-700 whitespace-nowrap">
          LLM Fraud Agents Studio
        </button>
        <button id="tab-btn-legacy" onclick="switchTab('legacy')" class="py-4 text-sm font-medium text-slate-500 hover:text-slate-700 whitespace-nowrap">
          Legacy Mainframe & EDI
        </button>
        <button id="tab-btn-export" onclick="switchTab('export')" class="py-4 text-sm font-medium text-slate-500 hover:text-slate-700 whitespace-nowrap">
          Downloads & Artifacts
        </button>
      </div>


      <!-- Tab Content 1: Transaction Explorer -->
      <div id="tab-content-tx" class="p-6">
        <!-- Table Search & Filters -->
        <div class="flex flex-col sm:flex-row justify-between items-center gap-3 mb-4">
          <div class="w-full sm:w-80 relative">
            <input type="text" id="tx-search" placeholder="Search doc#, account, vendor, text..." oninput="filterTransactions()" class="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            <svg class="w-4 h-4 text-slate-400 absolute left-2.5 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          </div>
          <div class="flex items-center space-x-2 w-full sm:w-auto">
            <select id="cycle-filter" onchange="filterTransactions()" class="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none">
              <option value="ALL">All Accounting Cycles</option>
              <option value="P2P">Procure-to-Pay (P2P)</option>
              <option value="O2C">Order-to-Cash (O2C)</option>
              <option value="R2R">Record-to-Report (R2R)</option>
            </select>
            <select id="status-filter" onchange="filterTransactions()" class="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 focus:outline-none">
              <option value="ALL">All Entries</option>
              <option value="CLEAN">Clean Baseline Only</option>
              <option value="ANOMALOUS">Injected Anomalies Only</option>
            </select>
          </div>
        </div>

        <!-- Table Container -->
        <div class="overflow-x-auto border border-slate-200 rounded-xl">
          <table class="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead class="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th class="px-3.5 py-3">Doc Number</th>
                <th class="px-3.5 py-3">Type</th>
                <th class="px-3.5 py-3">Date / Time</th>
                <th class="px-3.5 py-3">Cycle</th>
                <th class="px-3.5 py-3">Header Text</th>
                <th class="px-3.5 py-3 text-right">Debit Sum</th>
                <th class="px-3.5 py-3 text-right">Credit Sum</th>
                <th class="px-3.5 py-3 text-center">Status</th>
                <th class="px-3.5 py-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody id="tx-table-body" class="divide-y divide-slate-100 bg-white">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
        <p class="text-[11px] text-slate-400 mt-2" id="explorer-note">Showing sample entries in interactive explorer.</p>
      </div>

      <!-- Tab Content 2: SOX 404 Forensic Screening -->
      <div id="tab-content-audit" class="p-6 hidden space-y-6">
        <div class="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <h4 class="text-sm font-bold text-slate-900">SOX-404 Forensic Audit Screening Results</h4>
            <p class="text-xs text-slate-500">Automated audit script execution detecting statistical, structural, and timing control bypasses.</p>
          </div>
          <button onclick="triggerAudit()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-sm transition">
            Re-Run Screening
          </button>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Benford's Law Chart Card -->
          <div class="bg-slate-50 border border-slate-200 rounded-2xl p-5">
            <div class="flex justify-between items-start mb-3">
              <div>
                <h5 class="text-xs font-bold text-slate-900">SOX-404-DATA: Benford's Law Digit Frequency</h5>
                <p id="benford-verdict" class="text-[11px] text-slate-500 mt-0.5">Evaluating Chi-Square test against log10(1 + 1/d)...</p>
              </div>
              <span id="benford-pill" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">Pending</span>
            </div>
            <div class="h-56">
              <canvas id="benfordChart"></canvas>
            </div>
          </div>

          <!-- DOA Split Clusters Card -->
          <div class="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-start mb-3">
                <div>
                  <h5 class="text-xs font-bold text-slate-900">SOX-404-P2P: Split Approvals / DOA Bypass</h5>
                  <p class="text-[11px] text-slate-500 mt-0.5">Clusters in [$9,500, $9,999] targeting identical vendor within 48h</p>
                </div>
                <span id="doa-pill" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">Pending</span>
              </div>
              <div id="doa-list" class="space-y-2 mt-3 max-h-52 overflow-y-auto">
                <p class="text-xs text-slate-400">Click 'Run SOX-404 Screen' to view findings.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Anomaly Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Off-Hours MJEs -->
          <div class="bg-slate-50 border border-slate-200 rounded-2xl p-4">
            <div class="flex justify-between items-center mb-2">
              <span class="text-xs font-bold text-slate-800">Off-Hours & Weekend MJEs</span>
              <span id="offhours-pill" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">--</span>
            </div>
            <p class="text-[11px] text-slate-500 mb-2">Manual journal entries created 2:00-4:30 AM or weekends by dormant accounts.</p>
            <div id="offhours-list" class="text-xs text-slate-700 space-y-1.5 max-h-36 overflow-y-auto"></div>
          </div>

          <!-- Prohibited Account Pairings -->
          <div class="bg-slate-50 border border-slate-200 rounded-2xl p-4">
            <div class="flex justify-between items-center mb-2">
              <span class="text-xs font-bold text-slate-800">Topological Account Violations</span>
              <span id="pairings-pill" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">--</span>
            </div>
            <p class="text-[11px] text-slate-500 mb-2">DR Cash / CR Expense bypasses, suspense account 99999 parking, CapEx skips.</p>
            <div id="pairings-list" class="text-xs text-slate-700 space-y-1.5 max-h-36 overflow-y-auto"></div>
          </div>

          <!-- Circular Intercompany Loop -->
          <div class="bg-slate-50 border border-slate-200 rounded-2xl p-4">
            <div class="flex justify-between items-center mb-2">
              <span class="text-xs font-bold text-slate-800">Circular Round-Tripping</span>
              <span id="ic-pill" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">--</span>
            </div>
            <p class="text-[11px] text-slate-500 mb-2">Directed intercompany volume loops (A -> B -> C -> A) within financial close.</p>
            <div id="ic-list" class="text-xs text-slate-700 space-y-1.5 max-h-36 overflow-y-auto"></div>
          </div>
        </div>
      </div>

      <!-- Tab Content 3: Downloads & Artifacts -->
      <div id="tab-content-export" class="p-6 hidden space-y-6">
        <div>
          <h4 class="text-sm font-bold text-slate-900">Dual-Artifact Export & Cryptographic Hashes</h4>
          <p class="text-xs text-slate-500">Every dataset is packaged with exact decimal cent double-entry balance and sealed with SHA-256 digests.</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- Parquet Download Card -->
          <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/50 flex flex-col justify-between">
            <div>
              <div class="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs mb-3">
                PQ
              </div>
              <h5 class="text-xs font-bold text-slate-900">Parquet GL Feed</h5>
              <p class="text-[11px] text-slate-500 mt-1">Snappy-compressed columnar feed optimized for high-performance ML fraud model ingestion.</p>
            </div>
            <a href="/api/download/gl_feed.parquet" class="mt-4 inline-flex items-center justify-center w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition">
              Download gl_feed.parquet
            </a>
          </div>

          <!-- CSV Download Card -->
          <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/50 flex flex-col justify-between">
            <div>
              <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs mb-3">
                CSV
              </div>
              <h5 class="text-xs font-bold text-slate-900">RFC 4180 CSV Feed</h5>
              <p class="text-[11px] text-slate-500 mt-1">Standard general ledger export compatible with Excel, Tableau, and BI warehouses.</p>
            </div>
            <a href="/api/download/gl_feed.csv" class="mt-4 inline-flex items-center justify-center w-full px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl transition">
              Download gl_feed.csv
            </a>
          </div>

          <!-- SAP BSEG / BKPF Card -->
          <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/50 flex flex-col justify-between">
            <div>
              <div class="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs mb-3">
                SAP
              </div>
              <h5 class="text-xs font-bold text-slate-900">SAP BKPF / BSEG Tables</h5>
              <p class="text-[11px] text-slate-500 mt-1">Direct SAP ERP format with BUKRS, BELNR, BUZEI, BSCHL, SHKZG, HKONT, and WRBTR fields.</p>
            </div>
            <div class="mt-4 flex space-x-2">
              <a href="/api/download/SAP_BKPF.csv" class="flex-1 text-center px-2 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition">
                BKPF.csv
              </a>
              <a href="/api/download/SAP_BSEG.csv" class="flex-1 text-center px-2 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl transition">
                BSEG.csv
              </a>
            </div>
          </div>

          <!-- SAP S/4HANA ACDOCA Universal Journal Card -->
          <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/50 flex flex-col justify-between">
            <div>
              <div class="w-8 h-8 rounded-lg bg-cyan-100 text-cyan-700 flex items-center justify-center font-bold text-xs mb-3">
                ACDOCA
              </div>
              <h5 class="text-xs font-bold text-slate-900">SAP S/4HANA Universal Journal</h5>
              <p class="text-[11px] text-slate-500 mt-1">50+ column enterprise schema (RLDNR, RBUKRS, GJAHR, BELNR, DOCLN, RACCT, WSL, TSL, KSL).</p>
            </div>
            <div class="mt-4 flex space-x-2">
              <a href="/api/download/acdoca_feed.parquet" class="flex-1 text-center px-2 py-2 bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-semibold rounded-xl transition">
                acdoca.parquet
              </a>
              <a href="/api/download/acdoca_feed.csv" class="flex-1 text-center px-2 py-2 bg-cyan-700 hover:bg-cyan-800 text-white text-xs font-semibold rounded-xl transition">
                acdoca.csv
              </a>
            </div>
          </div>

          <!-- Audit Manifest JSON Card -->
          <div class="border border-slate-200 rounded-2xl p-4 bg-slate-50/50 flex flex-col justify-between">
            <div>
              <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-xs mb-3">
                JSON
              </div>
              <h5 class="text-xs font-bold text-slate-900">Ground-Truth Manifest</h5>
              <p class="text-[11px] text-slate-500 mt-1">Audit ground-truth manifest mapping every anomaly to affected vouchers and SOX control refs.</p>
            </div>
            <a href="/api/download/ground_truth_manifest.json" class="mt-4 inline-flex items-center justify-center w-full px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-xl transition">
              Download manifest.json
            </a>
          </div>
        </div>
      </div>

      <!-- Tab Content: LLM Fraud Agents Studio -->
      <div id="tab-content-agent" class="p-6 hidden space-y-6">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
          <div>
            <h4 class="text-sm font-bold text-slate-900">Autonomous Generative LLM Social Engineering Fraud Studio</h4>
            <p class="text-xs text-slate-500">Simulate multi-turn psychological coercion, pretexting, and objection handling accompanying financial crimes.</p>
          </div>
          <span class="px-2.5 py-1 bg-purple-100 text-purple-800 font-semibold text-xs rounded-lg border border-purple-200">
            Zero-Dependency Heuristic Generative Engine Active
          </span>
        </div>

        <!-- Controls -->
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-xl text-xs border border-slate-200">
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Agent Persona</label>
            <select id="agent-persona" class="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs">
              <option value="EXECUTIVE_CFO">Executive CFO (CEO Wire Bypass / Project Apollo)</option>
              <option value="COLLUSIVE_VENDOR">Collusive Vendor (Bank Account Diversion)</option>
              <option value="AUDITOR_DECEPTOR">Auditor Deceptor (Suspense GAAP Obfuscation)</option>
            </select>
          </div>
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Target Voucher ID</label>
            <input type="text" id="agent-voucher" value="VCH-2026-9081" class="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs font-mono">
          </div>
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Disputed Amount</label>
            <input type="text" id="agent-amount" value="$125,000.00" class="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs">
          </div>
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Vendor / Counterparty</label>
            <input type="text" id="agent-vendor" value="Apex Strategic Advisory Partners" class="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs">
          </div>
        </div>

        <div class="flex justify-end space-x-3">
          <button onclick="generateAgentDialogue()" id="agent-gen-btn" class="px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white text-xs font-bold rounded-xl shadow transition flex items-center">
            <span id="agent-spinner" class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-2 hidden"></span>
            Generate Social Engineering Thread
          </button>
        </div>

        <!-- Dialogue Transcript Container -->
        <div id="agent-dialogue-box" class="border border-slate-200 rounded-xl p-4 bg-slate-900 text-slate-100 min-h-[300px] space-y-4">
          <p class="text-xs text-slate-400 text-center py-10">Configure parameters above and click "Generate Social Engineering Thread" to observe autonomous multi-turn adversarial dialogue.</p>
        </div>
      </div>

      <!-- Tab Content: Legacy Mainframe & EDI Protocol Studio -->
      <div id="tab-content-legacy" class="p-6 hidden space-y-6">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
          <div>
            <h4 class="text-sm font-bold text-slate-900">Legacy Enterprise Mainframe, Banking & Supply Chain EDI Studio</h4>
            <p class="text-xs text-slate-500">Serialize and fuzz transactions into ANSI X12, UN/EDIFACT, IBM COBOL fixed-width, EBCDIC binary, NACHA ACH, and SWIFT MT940.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl text-xs border border-slate-200">
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Legacy Protocol Target</label>
            <select id="legacy-proto" class="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs">
              <option value="ANSI_X12_810">ANSI X12 810 (Commercial Invoice)</option>
              <option value="ANSI_X12_850">ANSI X12 850 (Purchase Order)</option>
              <option value="ANSI_X12_856">ANSI X12 856 (Ship Notice / ASN)</option>
              <option value="EDIFACT_INVOIC">UN/EDIFACT INVOIC (D.96A Commercial Invoice)</option>
              <option value="EDIFACT_ORDERS">UN/EDIFACT ORDERS (Purchase Order)</option>
              <option value="COBOL_COPYBOOK_80">IBM COBOL 80-Column Punched Card Layout</option>
              <option value="COBOL_COPYBOOK_132">IBM COBOL 132-Column Line Printer Report</option>
              <option value="EBCDIC_BINARY">IBM Mainframe EBCDIC CP037 Binary Dump (COMP-3)</option>
              <option value="NACHA_ACH">NACHA ACH (US Banking 94-Char Fixed-Width Batch)</option>
              <option value="BAI2">BAI2 Cash Management Statement</option>
              <option value="SWIFT_MT940">SWIFT MT940 Customer Statement Message</option>
            </select>
          </div>
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Record Count / Items</label>
            <input type="number" id="legacy-count" value="5" min="1" max="100" class="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs">
          </div>
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Transaction Dollar Amount</label>
            <input type="number" id="legacy-amount" value="12500.50" step="0.01" class="w-full bg-white border border-slate-300 rounded-lg p-2 text-xs">
          </div>
        </div>

        <!-- Protocol Fuzzing Anomalies Multi-Select -->
        <div class="bg-amber-50/50 p-4 rounded-xl border border-amber-200">
          <span class="block text-xs font-bold text-amber-900 mb-2">Inject Protocol-Level Fuzzing Corruptions:</span>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-delim" value="DELIMITER_CORRUPTION" class="rounded text-blue-600"> <span>Delimiter Corruption</span></label>
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-env" value="ENVELOPE_TRUNCATION" class="rounded text-blue-600"> <span>Envelope Truncation</span></label>
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-seg" value="SEGMENT_COUNT_DESYNC" class="rounded text-blue-600"> <span>Segment Count Desync</span></label>
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-buf" value="BUFFER_OVERFLOW" class="rounded text-blue-600"> <span>Buffer Overflow</span></label>
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-sign" value="EBCDIC_SIGN_CORRUPTION" class="rounded text-blue-600"> <span>COMP-3 Sign Corruption</span></label>
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-hash" value="HASH_TOTAL_DESYNC" class="rounded text-blue-600"> <span>ACH Hash Total Desync</span></label>
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-width" value="FIXED_WIDTH_OVERFLOW" class="rounded text-blue-600"> <span>Fixed-Width Line Overflow</span></label>
            <label class="flex items-center space-x-2"><input type="checkbox" id="fuzz-null" value="NULL_BYTE_INJECTION" class="rounded text-blue-600"> <span>Null Byte Injection</span></label>
          </div>
        </div>

        <div class="flex justify-between items-center">
          <div id="legacy-stats" class="text-xs text-slate-500 font-mono"></div>
          <button onclick="executeLegacyProtocol()" id="legacy-gen-btn" class="px-5 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white text-xs font-bold rounded-xl shadow transition flex items-center">
            <span id="legacy-spinner" class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-2 hidden"></span>
            Serialize & Fuzz Protocol Stream
          </button>
        </div>

        <!-- Raw Payload Preview Box -->
        <div class="space-y-2">
          <div class="flex justify-between items-center text-xs">
            <span class="font-bold text-slate-700">Raw Serialized Stream Output:</span>
            <a id="legacy-download-link" href="#" class="text-blue-600 hover:underline font-semibold hidden">Download Raw Stream File</a>
          </div>
          <pre id="legacy-preview-box" class="border border-slate-200 rounded-xl p-4 bg-slate-950 text-emerald-400 font-mono text-xs overflow-x-auto max-h-96 whitespace-pre">Click "Serialize & Fuzz Protocol Stream" to view legacy formatted payload.</pre>
        </div>
      </div>
    </div>

  </main>

  <!-- Footer with Credits -->
  <footer class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-xs text-slate-500 border-t border-slate-200 mt-8">
    <p>Synthetic General Ledger Fuzzer • Made with ❤️ by <a href="https://github.com/Atiqul-Akash" target="_blank" class="text-blue-600 hover:underline font-semibold">Atiqul-Akash</a> (GitHub: <a href="https://github.com/Atiqul-Akash" target="_blank" class="text-blue-600 hover:underline font-mono">Atiqul-Akash</a>) • MIT License</p>
  </footer>

  <!-- Journal Voucher Inspect Modal -->
  <div id="voucher-modal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full p-6 space-y-4 border border-slate-200 animate-in fade-in zoom-in duration-150">
      <div class="flex justify-between items-start pb-3 border-b border-slate-100">
        <div>
          <div class="flex items-center space-x-2">
            <span id="modal-type-badge" class="px-2 py-0.5 bg-blue-100 text-blue-800 text-[10px] font-bold rounded">--</span>
            <h3 id="modal-doc-number" class="text-base font-bold text-slate-900">Document #--</h3>
          </div>
          <p id="modal-header-text" class="text-xs text-slate-500 mt-0.5">--</p>
        </div>
        <button onclick="closeModal()" class="text-slate-400 hover:text-slate-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>

      <!-- Header Meta Grid -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-xl text-xs">
        <div><span class="text-slate-400 block text-[10px]">Company Code</span><span id="modal-bukrs" class="font-semibold text-slate-700">1000</span></div>
        <div><span class="text-slate-400 block text-[10px]">Posting Date</span><span id="modal-budat" class="font-semibold text-slate-700">--</span></div>
        <div><span class="text-slate-400 block text-[10px]">Entry Timestamp</span><span id="modal-cputm" class="font-semibold text-slate-700">--</span></div>
        <div><span class="text-slate-400 block text-[10px]">Created By</span><span id="modal-usnam" class="font-semibold text-slate-700">--</span></div>
      </div>

      <!-- Double-entry lines table -->
      <div class="border border-slate-200 rounded-xl overflow-hidden">
        <table class="min-w-full text-xs text-left">
          <thead class="bg-slate-50 text-[10px] uppercase font-semibold text-slate-500">
            <tr>
              <th class="px-3 py-2">Item</th>
              <th class="px-3 py-2">PK</th>
              <th class="px-3 py-2">D/C</th>
              <th class="px-3 py-2">Account</th>
              <th class="px-3 py-2">Details</th>
              <th class="px-3 py-2 text-right">Amount</th>
            </tr>
          </thead>
          <tbody id="modal-lines-body" class="divide-y divide-slate-100">
            <!-- Dynamic lines -->
          </tbody>
        </table>
      </div>

      <div class="flex justify-between items-center pt-2">
        <div id="modal-anomaly-box" class="text-xs"></div>
        <button onclick="closeModal()" class="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 text-xs font-semibold rounded-lg text-slate-700">
          Close
        </button>
      </div>
    </div>
  </div>

  <script>
    let currentData = null;
    let benfordChartInstance = null;

    function updateSliderLabels() {
      const count = document.getElementById('count-slider').value;
      const rate = document.getElementById('rate-slider').value;
      document.getElementById('count-val').innerText = parseInt(count).toLocaleString();
      document.getElementById('rate-val').innerText = `${rate}%`;
    }

    function applyPreset(preset) {
      if (preset === 'clean') {
        document.getElementById('count-slider').value = 1000;
        document.getElementById('rate-slider').value = 0;
      } else if (preset === 'standard') {
        document.getElementById('count-slider').value = 1000;
        document.getElementById('rate-slider').value = 6;
      } else if (preset === 'stress') {
        document.getElementById('count-slider').value = 5000;
        document.getElementById('rate-slider').value = 15;
      }
      updateSliderLabels();
      triggerGenerate();
    }

    async function triggerGenerate() {
      const btn = document.getElementById('generate-btn');
      const spinner = document.getElementById('gen-spinner');
      btn.disabled = true;
      spinner.classList.remove('hidden');

      const payload = {
        count: parseInt(document.getElementById('count-slider').value),
        anomaly_rate: parseFloat(document.getElementById('rate-slider').value) / 100.0,
        seed: parseInt(document.getElementById('seed-input').value) || 42,
        enabled_anomalies: {
          smurfing: document.getElementById('anom-smurfing').checked,
          ghost: document.getElementById('anom-ghost').checked,
          benford: document.getElementById('anom-benford').checked,
          pairings: document.getElementById('anom-pairings').checked,
          round_trip: document.getElementById('anom-roundtrip').checked,
        }
      };

      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        currentData = data;
        renderDashboard(data);
      } catch (err) {
        alert('Generation failed: ' + err);
      } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
      }
    }

    function renderDashboard(data) {
      if (!data || data.status !== 'READY') return;

      document.getElementById('metric-entries').innerText = data.total_entries.toLocaleString();
      document.getElementById('metric-lines').innerText = `${data.total_lines.toLocaleString()} line items`;
      document.getElementById('metric-debits').innerText = `$${data.total_debits}`;
      document.getElementById('metric-credits').innerText = `$${data.total_credits}`;
      document.getElementById('metric-delta').innerText = `$${data.balance_delta}`;
      document.getElementById('metric-anomalies').innerText = data.anomalous_entries_count.toLocaleString();
      document.getElementById('metric-rate').innerText = `${(data.anomaly_rate * 100).toFixed(1)}% effective`;

      filterTransactions();
    }

    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function filterTransactions() {
      if (!currentData || !currentData.sample_entries) return;

      const q = (document.getElementById('tx-search').value || '').toLowerCase().trim();
      const cycle = document.getElementById('cycle-filter').value;
      const status = document.getElementById('status-filter').value;

      const tbody = document.getElementById('tx-table-body');
      tbody.innerHTML = '';

      const filtered = currentData.sample_entries.filter(e => {
        if (cycle !== 'ALL' && e.business_cycle !== cycle) return false;
        if (status === 'CLEAN' && e.is_anomaly) return false;
        if (status === 'ANOMALOUS' && !e.is_anomaly) return false;
        if (q) {
          const matchDoc = (e.document_number || '').toLowerCase().includes(q);
          const matchHead = (e.header_text || '').toLowerCase().includes(q);
          const matchLines = (e.lines || []).some(l => 
            (l.account_code || '').toLowerCase().includes(q) || 
            (l.account_name || '').toLowerCase().includes(q) || 
            (l.line_text || '').toLowerCase().includes(q) || 
            (l.vendor_id || '').toLowerCase().includes(q) || 
            (l.customer_id || '').toLowerCase().includes(q)
          );
          if (!matchDoc && !matchHead && !matchLines) return false;
        }
        return true;
      });

      filtered.forEach((e, idx) => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-slate-50 transition";
        const anomCount = (e.anomaly_ids || []).length;
        const statusBadge = e.is_anomaly
          ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">Anomaly (${anomCount})</span>`
          : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Clean</span>`;

        tr.innerHTML = `
          <td class="px-3.5 py-2.5 font-semibold text-slate-800">${escapeHtml(e.document_number)}</td>
          <td class="px-3.5 py-2.5"><span class="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-mono">${escapeHtml(e.document_type)}</span></td>
          <td class="px-3.5 py-2.5 text-slate-600">${escapeHtml(e.posting_date)} <span class="text-slate-400 text-[10px]">${escapeHtml(e.entry_time)}</span></td>
          <td class="px-3.5 py-2.5"><span class="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-md font-semibold text-[10px]">${escapeHtml(e.business_cycle)}</span></td>
          <td class="px-3.5 py-2.5 text-slate-700 truncate max-w-xs">${escapeHtml(e.header_text)}</td>
          <td class="px-3.5 py-2.5 text-right font-mono font-medium text-emerald-700">$${escapeHtml(e.total_debits)}</td>
          <td class="px-3.5 py-2.5 text-right font-mono font-medium text-emerald-700">$${escapeHtml(e.total_credits)}</td>
          <td class="px-3.5 py-2.5 text-center">${statusBadge}</td>
          <td class="px-3.5 py-2.5 text-center">
            <button onclick="inspectEntry('${escapeHtml(e.entry_id)}')" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium transition">
              Inspect
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      const note = document.getElementById('explorer-note');
      if (note && currentData) {
        const totalDataset = currentData.total_entries || currentData.sample_entries.length;
        note.innerText = `Showing ${filtered.length} of ${currentData.sample_entries.length} previewed vouchers (${currentData.anomalous_entries_count || 0} total anomalies across ${totalDataset} entries in dataset).`;
      }
    }

    function inspectEntry(entryId) {
      if (!currentData || !currentData.sample_entries) return;
      const entry = currentData.sample_entries.find(e => e.entry_id === entryId);
      if (!entry) return;

      document.getElementById('modal-doc-number').innerText = `Document #${entry.document_number}`;
      document.getElementById('modal-header-text').innerText = entry.header_text;
      document.getElementById('modal-type-badge').innerText = `${entry.business_cycle} / ${entry.document_type}`;
      document.getElementById('modal-bukrs').innerText = entry.company_code;
      document.getElementById('modal-budat').innerText = entry.posting_date;
      document.getElementById('modal-cputm').innerText = entry.entry_time;
      document.getElementById('modal-usnam').innerText = entry.created_by;

      const tbody = document.getElementById('modal-lines-body');
      tbody.innerHTML = '';
      (entry.lines || []).forEach(l => {
        const tr = document.createElement('tr');
        const dcColor = l.debit_credit === 'DEBIT' ? 'text-blue-700 bg-blue-50' : 'text-purple-700 bg-purple-50';
        const party = l.vendor_id ? 'Vendor: ' + l.vendor_id : (l.customer_id ? 'Cust: ' + l.customer_id : (l.trading_partner ? 'Partner: ' + l.trading_partner : (l.line_text || '')));
        tr.innerHTML = `
          <td class="px-3 py-2 text-slate-400">${escapeHtml(l.line_number)}</td>
          <td class="px-3 py-2 font-mono text-slate-600">${escapeHtml(l.posting_key)}</td>
          <td class="px-3 py-2"><span class="px-1.5 py-0.5 rounded font-bold text-[10px] ${dcColor}">${escapeHtml(l.debit_credit)}</span></td>
          <td class="px-3 py-2 font-mono font-semibold text-slate-800">${escapeHtml(l.account_code)} <span class="font-normal text-slate-500">(${escapeHtml(l.account_name)})</span></td>
          <td class="px-3 py-2 text-slate-600">${escapeHtml(party)}</td>
          <td class="px-3 py-2 text-right font-mono font-bold text-slate-900">$${escapeHtml(l.amount)}</td>
        `;
        tbody.appendChild(tr);
      });

      const anomBox = document.getElementById('modal-anomaly-box');
      if (entry.is_anomaly) {
        const joinedAnoms = escapeHtml((entry.anomaly_ids || []).join(', '));
        anomBox.innerHTML = `<span class="px-2.5 py-1 rounded-md bg-amber-100 text-amber-900 font-semibold text-[11px] inline-flex items-center">⚠ Injected Anomaly Signal: ${joinedAnoms}</span>`;
      } else {
        anomBox.innerHTML = `<span class="px-2.5 py-1 rounded-md bg-emerald-100 text-emerald-900 font-semibold text-[11px]">✓ Clean Baseline Journal Entry</span>`;
      }

      document.getElementById('voucher-modal').classList.remove('hidden');
    }

    function closeModal() {
      document.getElementById('voucher-modal').classList.add('hidden');
    }

    function switchTab(tabId) {
      ['tx', 'audit', 'agent', 'legacy', 'export'].forEach(t => {
        const btn = document.getElementById('tab-btn-' + t);
        const panel = document.getElementById('tab-content-' + t);
        if (btn) btn.className = "py-4 text-sm font-medium text-slate-500 hover:text-slate-700 whitespace-nowrap";
        if (panel) panel.classList.add('hidden');
      });

      const activeBtn = document.getElementById('tab-btn-' + tabId);
      const activePanel = document.getElementById('tab-content-' + tabId);
      if (activeBtn) activeBtn.className = "py-4 text-sm font-medium tab-active whitespace-nowrap";
      if (activePanel) activePanel.classList.remove('hidden');

      if (tabId === 'audit') {
        triggerAudit();
      }
    }

    async function generateAgentDialogue() {
      const btn = document.getElementById('agent-gen-btn');
      const spinner = document.getElementById('agent-spinner');
      const box = document.getElementById('agent-dialogue-box');

      btn.disabled = true;
      spinner.classList.remove('hidden');

      const persona = document.getElementById('agent-persona').value;
      const voucher = document.getElementById('agent-voucher').value;
      const amount = document.getElementById('agent-amount').value;
      const vendor = document.getElementById('agent-vendor').value;

      try {
        const res = await fetch('/api/agent-dialogue', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ persona, voucher, amount, vendor, scenario: 'APOLLO_OVERRIDE' })
        });
        const data = await res.json();

        box.innerHTML = `
          <div class="flex justify-between items-center pb-3 border-b border-slate-700 text-xs text-slate-300">
            <div>
              <span class="font-bold text-white">${data.subject}</span>
              <span class="text-slate-400 ml-2">ID: ${data.thread_id}</span>
            </div>
            <a href="${data.eml_download}" class="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded text-xs font-semibold">
              Download .EML Chain
            </a>
          </div>
        `;

        (data.turns || []).forEach(t => {
          const isAgent = t.speaker_role === 'FRAUD_AGENT';
          const cardBg = isAgent ? 'bg-purple-950/60 border-purple-800/80' : 'bg-slate-800/80 border-slate-700';
          const badge = t.persuasion_tactic 
            ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">${t.persuasion_tactic}</span>`
            : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-700 text-slate-300">OBJECTION</span>`;
          const resolvedBadge = t.objection_resolved ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 ml-1">RESOLVED</span>` : '';

          const turnCard = document.createElement('div');
          turnCard.className = `p-4 rounded-xl border ${cardBg} space-y-2 text-xs`;
          turnCard.innerHTML = `
            <div class="flex justify-between items-center">
              <span class="font-bold text-slate-200">Turn ${t.turn_index}: ${t.speaker_name} <span class="font-normal text-slate-400">(${t.speaker_role})</span></span>
              <div>${badge}${resolvedBadge}</div>
            </div>
            <div class="text-slate-300 whitespace-pre-wrap leading-relaxed">${t.message_body}</div>
          `;
          box.appendChild(turnCard);
        });

      } catch (err) {
        box.innerHTML = `<p class="text-red-400 text-xs">Failed to generate agent dialogue: ${err}</p>`;
      } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
      }
    }

    async function executeLegacyProtocol() {
      const btn = document.getElementById('legacy-gen-btn');
      const spinner = document.getElementById('legacy-spinner');
      const box = document.getElementById('legacy-preview-box');
      const stats = document.getElementById('legacy-stats');
      const dlLink = document.getElementById('legacy-download-link');

      btn.disabled = true;
      spinner.classList.remove('hidden');

      const protocol = document.getElementById('legacy-proto').value;
      const count = parseInt(document.getElementById('legacy-count').value) || 5;
      const amount = parseFloat(document.getElementById('legacy-amount').value) || 12500.50;

      const anomalies = [];
      const anomIds = ['fuzz-delim', 'fuzz-env', 'fuzz-seg', 'fuzz-buf', 'fuzz-sign', 'fuzz-hash', 'fuzz-width', 'fuzz-null'];
      anomIds.forEach(id => {
        const cb = document.getElementById(id);
        if (cb && cb.checked) anomalies.push(cb.value);
      });

      try {
        const res = await fetch('/api/legacy-export', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ protocol, count, amount, anomalies })
        });
        const data = await res.json();

        stats.innerText = `Size: ${data.byte_size.toLocaleString()} bytes | Records: ${data.record_count} | Encoding: ${data.encoding} | Binary: ${data.is_binary}`;
        box.innerText = data.preview;
        dlLink.href = data.download_url;
        dlLink.classList.remove('hidden');
      } catch (err) {
        box.innerText = `Error executing legacy protocol: ${err}`;
      } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
      }
    }


    async function triggerAudit() {
      try {
        const res = await fetch('/api/audit', { method: 'POST' });
        const audit = await res.json();
        renderAuditFindings(audit);
      } catch (err) {
        console.error('Audit failed:', err);
      }
    }

    function renderAuditFindings(audit) {
      // 1. Benford
      const b = audit.benford;
      const bPill = document.getElementById('benford-pill');
      if (b.is_anomalous) {
        bPill.innerText = "Signal Flagged";
        bPill.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800";
      } else {
        bPill.innerText = "Compliant";
        bPill.className = "text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800";
      }
      document.getElementById('benford-verdict').innerText = `Chi2 = ${b.chi2_statistic}, p-value = ${b.p_value.toExponential(3)} (${b.forensic_conclusion})`;

      // Render Benford Chart
      const digits = [1, 2, 3, 4, 5, 6, 7, 8, 9];
      const observed = digits.map(d => b.empirical_percentages[`digit_${d}`] || 0);
      const expected = digits.map(d => b.theoretical_percentages[`digit_${d}`] || 0);

      const ctx = document.getElementById('benfordChart').getContext('2d');
      if (benfordChartInstance) benfordChartInstance.destroy();

      benfordChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: digits.map(d => `Digit ${d}`),
          datasets: [
            {
              label: 'Observed %',
              data: observed,
              backgroundColor: 'rgba(234, 88, 12, 0.7)',
              borderRadius: 4,
            },
            {
              label: 'Benford Theoretical %',
              data: expected,
              type: 'line',
              borderColor: '#2563eb',
              borderWidth: 2,
              fill: false,
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } } },
          scales: { y: { beginAtZero: true, ticks: { callback: v => v + '%' } } }
        }
      });

      // 2. DOA
      const doa = audit.doa;
      const doaPill = document.getElementById('doa-pill');
      doaPill.innerText = `${doa.detected_clusters_count} Clusters`;
      doaPill.className = doa.has_doa_violations ? "text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-800" : "text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800";

      const doaList = document.getElementById('doa-list');
      doaList.innerHTML = '';
      doa.clusters.forEach(c => {
        const item = document.createElement('div');
        item.className = "p-2 bg-white rounded-lg border border-slate-200 text-xs";
        item.innerHTML = `<strong>${c.vendor}</strong>: ${c.cluster_size} invoices totaling $${c.total_amount} just below $${doa.threshold_checked} DOA limit`;
        doaList.appendChild(item);
      });

      // 3. Off-Hours
      const oh = audit.off_hours;
      document.getElementById('offhours-pill').innerText = `${oh.off_hours_flagged_count} Flagged`;
      const ohList = document.getElementById('offhours-list');
      ohList.innerHTML = '';
      oh.flagged_entries.slice(0, 5).forEach(e => {
        const d = document.createElement('div');
        d.className = "p-1.5 bg-white rounded border border-slate-200 text-[11px]";
        d.innerText = `Doc #${e.document_number} @ ${e.entry_time} (${e.is_weekend ? 'Weekend' : 'Off-Hours'}) by ${e.created_by}`;
        ohList.appendChild(d);
      });

      // 4. Pairings
      const p = audit.pairings;
      document.getElementById('pairings-pill').innerText = `${p.flagged_pairings_count} Flagged`;
      const pList = document.getElementById('pairings-list');
      pList.innerHTML = '';
      p.pairings.slice(0, 5).forEach(item => {
        const d = document.createElement('div');
        d.className = "p-1.5 bg-white rounded border border-slate-200 text-[11px]";
        d.innerText = `Doc #${item.entry_id}: ${item.type} ($${item.amount})`;
        pList.appendChild(d);
      });

      // 5. Intercompany
      const ic = audit.intercompany;
      document.getElementById('ic-pill').innerText = `${ic.detected_cycles_count} Cycles`;
      const icList = document.getElementById('ic-list');
      icList.innerHTML = '';
      ic.cycles.forEach(cyc => {
        const d = document.createElement('div');
        d.className = "p-1.5 bg-white rounded border border-slate-200 text-[11px] font-mono font-semibold text-purple-800";
        d.innerText = `Loop: ${cyc.join(' -> ')}`;
        icList.appendChild(d);
      });
    }

    // Initialize on page load
    window.addEventListener('DOMContentLoaded', async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        currentData = data;
        renderDashboard(data);
      } catch (e) {
        console.error('Initial status fetch failed:', e);
      }
    });
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    start_web_gui(port=8080)
