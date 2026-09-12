"""Test suite for Multi-ERP Master Schemas (Workday, D365, NetSuite, Oracle FC)."""

from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import pytest

from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.exporters import (
    D365Exporter,
    NetSuiteExporter,
    OracleFCExporter,
    WorkdayExporter,
)


@pytest.fixture
def sample_batch():
    engine = BaseSynthesisEngine(seed=42)
    return engine.generate_batch(target_entry_count=5)


def test_workday_exporter(sample_batch):
    with tempfile.TemporaryDirectory() as tmpdir:
        res = WorkdayExporter.export(sample_batch.entries, tmpdir)
        assert "WORKDAY_SOAP_XML" in res
        assert "WORKDAY_RAAS_JSON" in res

        xml_path, _ = res["WORKDAY_SOAP_XML"]
        json_path, _ = res["WORKDAY_RAAS_JSON"]

        assert xml_path.exists()
        assert json_path.exists()

        # Parse XML to verify valid SOAP structure
        tree = ET.parse(xml_path)
        root = tree.getroot()
        assert "Envelope" in root.tag


def test_d365_exporter(sample_batch):
    with tempfile.TemporaryDirectory() as tmpdir:
        res = D365Exporter.export(sample_batch.entries, tmpdir)
        assert "D365_ODATA_JSON" in res
        assert "D365_BATCH_TXT" in res

        json_path, _ = res["D365_ODATA_JSON"]
        batch_path, _ = res["D365_BATCH_TXT"]

        assert json_path.exists()
        assert batch_path.exists()

        batch_content = batch_path.read_text(encoding="utf-8")
        assert "multipart/mixed" in batch_content
        assert "LedgerJournalTables" in batch_content


def test_netsuite_exporter(sample_batch):
    with tempfile.TemporaryDirectory() as tmpdir:
        res = NetSuiteExporter.export(sample_batch.entries, tmpdir)
        assert "NETSUITE_SUITETALK_JSON" in res
        assert "NETSUITE_IMPORT_CSV" in res

        json_path, _ = res["NETSUITE_SUITETALK_JSON"]
        csv_path, _ = res["NETSUITE_IMPORT_CSV"]

        assert json_path.exists()
        assert csv_path.exists()

        csv_content = csv_path.read_text(encoding="utf-8")
        assert "ExternalId,TranDate" in csv_content
        assert "PostingPeriod" in csv_content


def test_oracle_fc_exporter(sample_batch):
    with tempfile.TemporaryDirectory() as tmpdir:
        res = OracleFCExporter.export(sample_batch.entries, tmpdir)
        assert "ORACLE_FC_FBDI_CSV" in res
        assert "ORACLE_FC_REST_JSON" in res

        fbdi_path, _ = res["ORACLE_FC_FBDI_CSV"]
        rest_path, _ = res["ORACLE_FC_REST_JSON"]

        assert fbdi_path.exists()
        assert rest_path.exists()

        fbdi_content = fbdi_path.read_text(encoding="utf-8")
        assert "STATUS_CODE,LEDGER_ID" in fbdi_content
        assert "SEGMENT1,SEGMENT2" in fbdi_content
        assert "ACCOUNTED_DR,ACCOUNTED_CR" in fbdi_content
