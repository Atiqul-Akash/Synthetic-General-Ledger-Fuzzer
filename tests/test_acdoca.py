"""Unit tests for SAP S/4HANA Universal Journal (ACDOCA) Exporter."""

from decimal import Decimal
from pathlib import Path
import pyarrow.parquet as pq
import pytest

from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.exporters.acdoca_exporter import SAPACDOCAExporter


@pytest.fixture
def sample_entries():
    debit_line = LineItem(
        line_id="E1-1",
        entry_id="E1",
        line_number=1,
        account_code="10000",
        account_name="Cash and Cash Equivalents",
        debit_credit=DebitCredit.DEBIT,
        amount=Decimal("5000.00"),
        amount_local=Decimal("5000.00"),
        amount_group=Decimal("5000.00"),
        currency="USD",
        cost_center="CC_OPS",
        profit_center="PC_1000",
        segment="SEG_COMMERCIAL",
        functional_area="FA_OPS",
    )
    credit_line = LineItem(
        line_id="E1-2",
        entry_id="E1",
        line_number=2,
        account_code="40000",
        account_name="Operating Revenue",
        debit_credit=DebitCredit.CREDIT,
        amount=Decimal("5000.00"),
        amount_local=Decimal("5000.00"),
        amount_group=Decimal("5000.00"),
        currency="USD",
        profit_center="PC_1000",
        segment="SEG_COMMERCIAL",
        functional_area="FA_OPS",
    )
    entry = JournalEntry(
        entry_id="E1",
        batch_id="B001",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=3,
        document_type=DocumentType.DR,
        document_number="DOC100001",
        posting_date="2026-03-20",
        document_date="2026-03-20",
        entry_time="14:30:00",
        created_at="2026-03-20T14:30:00Z",
        created_by="J_DOE",
        reference="INV-9901",
        header_text="Customer Billing",
        business_cycle="O2C",
        lines=[debit_line, credit_line],
    )
    return [entry]


def test_acdoca_schema_structure():
    """Verify ACDOCA PyArrow schema has key Universal Journal fields."""
    schema = SAPACDOCAExporter.ACDOCA_SCHEMA
    field_names = schema.names

    required_fields = [
        "RCLNT", "RLDNR", "RBUKRS", "GJAHR", "BELNR", "DOCLN", "BLART",
        "BLDAT", "BUDAT", "POPER", "CPUDT", "CPUTM", "USNAM", "XBLNR",
        "BKTXT", "BSCHL", "DRCRK", "RACCT", "TXT50", "SGTXT", "RWCUR",
        "WSL", "RHCUR", "HSL", "RKCUR", "KSL", "RCNTR", "PRCTR", "SEGMENT",
        "FKBER", "BUSINESS_CYCLE", "IS_ANOMALY", "ANOMALY_IDS",
    ]
    for rf in required_fields:
        assert rf in field_names, f"Missing required ACDOCA field: {rf}"


def test_to_acdoca_row_mapping(sample_entries):
    """Verify accurate field mapping from JournalEntry to ACDOCA dictionary."""
    entry = sample_entries[0]
    row_debit = SAPACDOCAExporter.to_acdoca_row(entry, 0, entry.lines[0])
    row_credit = SAPACDOCAExporter.to_acdoca_row(entry, 1, entry.lines[1])

    assert row_debit["RBUKRS"] == "1000"
    assert row_debit["GJAHR"] == 2026
    assert row_debit["BELNR"] == "DOC100001"
    assert row_debit["DOCLN"] == "000001"
    assert row_debit["BLART"] == "DR"
    assert row_debit["BUDAT"] == "20260320"
    assert row_debit["POPER"] == "003"
    assert row_debit["DRCRK"] == "S"  # Debit = S
    assert row_debit["WSL"] == Decimal("5000.00")
    assert row_debit["HSL"] == Decimal("5000.00")
    assert row_debit["KSL"] == Decimal("5000.00")
    assert row_debit["RCNTR"] == "CC_OPS"

    assert row_credit["DOCLN"] == "000002"
    assert row_credit["DRCRK"] == "H"  # Credit = H
    assert row_credit["RACCT"] == "40000"


def test_acdoca_export_parquet(sample_entries, tmp_path):
    """Verify Snappy-compressed Parquet export produces valid table and SHA-256."""
    out_file = tmp_path / "acdoca_test.parquet"
    ret_path, file_hash = SAPACDOCAExporter.export_parquet(sample_entries, out_file)

    assert ret_path.exists()
    assert len(file_hash) == 64

    table = pq.read_table(out_file)
    assert table.num_rows == 2
    assert "WSL" in table.column_names
    assert "HSL" in table.column_names
    assert "KSL" in table.column_names


def test_acdoca_export_csv(sample_entries, tmp_path):
    """Verify CSV export produces valid header and formatted rows."""
    out_file = tmp_path / "acdoca_test.csv"
    ret_path, file_hash = SAPACDOCAExporter.export_csv(sample_entries, out_file)

    assert ret_path.exists()
    assert len(file_hash) == 64

    lines = out_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3  # Header + 2 rows
    assert "RCLNT,RLDNR,RBUKRS" in lines[0]
    assert "DOC100001" in lines[1]
    assert "5000.00" in lines[1]
