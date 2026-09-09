"""Comprehensive unit tests for ERP connectors and high-fidelity mock simulator."""

from decimal import Decimal
import pytest

from gl_fuzzer.connectors.base import (
    ERPConnectionConfig,
    ERPConnector,
    ERPPostingResult,
    OpenItem,
)
from gl_fuzzer.connectors.mock_erp import MockERPConnector
from gl_fuzzer.connectors.odata_connector import ODataV4Connector
from gl_fuzzer.connectors.oracle_connector import OracleRESTConnector
from gl_fuzzer.connectors.rfc_connector import SAPRFCConnector
from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem


def _make_sample_entry(
    doc_num: str = "DOC_1001",
    amount: Decimal = Decimal("1000.00"),
    doc_type: DocumentType = DocumentType.SA,
    period: int = 1,
    cost_center: str = "CC_CORP",
    header_text: str = "Test Entry",
    dr_account: str = "10100",
    cr_account: str = "20000",
) -> JournalEntry:
    lines = [
        LineItem(
            line_id=f"{doc_num}_1",
            entry_id=doc_num,
            line_number=1,
            account_code=dr_account,
            debit_credit=DebitCredit.DEBIT,
            amount=amount,
            cost_center=cost_center,
            customer_id="CUST_101" if doc_type == DocumentType.DR else None,
            vendor_id="VEND_101" if doc_type == DocumentType.KZ else None,
        ),
        LineItem(
            line_id=f"{doc_num}_2",
            entry_id=doc_num,
            line_number=2,
            account_code=cr_account,
            debit_credit=DebitCredit.CREDIT,
            amount=amount,
            cost_center=cost_center,
            vendor_id="VEND_101" if doc_type == DocumentType.KR else None,
            customer_id="CUST_101" if doc_type == DocumentType.DZ else None,
        ),
    ]
    return JournalEntry(
        entry_id=doc_num,
        batch_id="TEST_B1",
        company_code="1000",
        document_type=doc_type,
        document_number=doc_num,
        fiscal_year=2026,
        fiscal_period=period,
        posting_date="2026-01-15",
        document_date="2026-01-15",
        created_at="2026-01-15T10:00:00Z",
        header_text=header_text,
        lines=lines,
    )


def test_mock_erp_connect_and_coa_fetch():
    connector = MockERPConnector()
    assert connector.connect() is True
    assert connector.is_connected is True

    health = connector.test_connection()
    assert health["status"] == "HEALTHY"
    assert health["system_id"] == "S4H"

    coa = connector.fetch_chart_of_accounts("1000")
    assert len(coa.accounts) >= 35
    assert coa.get_account("10100") is not None


def test_mock_erp_accepts_valid_entry():
    connector = MockERPConnector()
    connector.connect()
    entry = _make_sample_entry()
    res = connector.post_journal_entry(entry)
    assert res.success is True
    assert res.status_code == 200
    assert res.document_number == entry.document_number


def test_mock_erp_posting_period_lock_rejection():
    connector = MockERPConnector()
    connector.connect()
    connector.lock_period(3)

    entry = _make_sample_entry(period=3)
    res = connector.post_journal_entry(entry)
    assert res.success is False
    assert res.error_code == "SAP_F5_201"
    assert "closed" in res.error_message


def test_mock_erp_balance_check_rejection():
    connector = MockERPConnector()
    connector.connect()

    entry = _make_sample_entry()
    # Induce imbalance
    entry.lines[1].amount = Decimal("999.00")
    assert not entry.is_balanced

    res = connector.post_journal_entry(entry)
    assert res.success is False
    assert res.error_code == "SAP_F5_022"


def test_mock_erp_duplicate_document_rejection():
    connector = MockERPConnector()
    connector.connect()

    entry1 = _make_sample_entry(doc_num="BELNR_UNIQUE_1")
    entry2 = _make_sample_entry(doc_num="BELNR_UNIQUE_1")

    res1 = connector.post_journal_entry(entry1)
    assert res1.success is True

    res2 = connector.post_journal_entry(entry2)
    assert res2.success is False
    assert res2.error_code == "ENQUEUE_DUPLICATE"


def test_mock_erp_cost_center_required_on_pnl():
    connector = MockERPConnector()
    connector.connect()

    # 61000 is Salaries Expense (P&L account)
    entry = _make_sample_entry(dr_account="61000", cr_account="21200", cost_center="")
    # Clear cost center on line 1
    entry.lines[0].cost_center = None

    res = connector.post_journal_entry(entry)
    assert res.success is False
    assert res.error_code == "SAP_F5_COBL_REQUIRED"


def test_mock_erp_non_positive_amount_rejection():
    connector = MockERPConnector()
    connector.connect()

    entry = _make_sample_entry()
    entry.lines[0].amount = Decimal("0.00")
    entry.lines[1].amount = Decimal("0.00")

    res = connector.post_journal_entry(entry)
    assert res.success is False
    assert res.error_code == "SAP_F5_019"


def test_mock_erp_unknown_account_rejection():
    connector = MockERPConnector()
    connector.connect()

    entry = _make_sample_entry(dr_account="98765")
    res = connector.post_journal_entry(entry)
    assert res.success is False
    assert res.error_code == "SAP_GL_ACCOUNT_NOT_FOUND"


def test_mock_erp_crash_on_sql_injection_payload():
    connector = MockERPConnector()
    connector.connect()

    entry = _make_sample_entry(header_text="Vendor'; DROP TABLE BSEG;--")
    res = connector.post_journal_entry(entry)
    assert res.success is False
    assert res.error_code == "CRASH_500"
    assert res.status_code == 500


def test_mock_erp_stateful_open_item_clearing():
    connector = MockERPConnector()
    connector.connect()

    # Post vendor invoice KR
    kr_entry = _make_sample_entry(doc_num="KR_001", doc_type=DocumentType.KR, dr_account="14000", cr_account="20000")
    res_kr = connector.post_journal_entry(kr_entry)
    assert res_kr.success is True

    open_items = connector.fetch_open_items("1000")
    assert len(open_items) == 1
    assert open_items[0].partner_id == "VEND_101"
    assert not open_items[0].is_cleared

    # Post payment KZ matching the vendor
    kz_entry = _make_sample_entry(doc_num="KZ_001", doc_type=DocumentType.KZ, dr_account="20000", cr_account="10100")
    res_kz = connector.post_journal_entry(kz_entry)
    assert res_kz.success is True

    open_items_after = connector.fetch_open_items("1000")
    assert len(open_items_after) == 0


def test_mock_erp_credit_limit_exceeded():
    connector = MockERPConnector()
    connector.connect()
    connector.customer_credit_limits["CUST_VIP"] = Decimal("5000.00")

    # Invoice exceeding limit
    dr_entry = _make_sample_entry(
        doc_num="DR_001",
        doc_type=DocumentType.DR,
        amount=Decimal("6000.00"),
        dr_account="11000",
        cr_account="40000",
    )
    dr_entry.lines[0].customer_id = "CUST_VIP"

    res = connector.post_journal_entry(dr_entry)
    assert res.success is False
    assert res.error_code == "CREDIT_LIMIT_EXCEEDED"


def test_odata_connector_fallback_to_mock():
    conn = ODataV4Connector(config=ERPConnectionConfig(host="localhost"))
    assert conn.connect() is True
    test_res = conn.test_connection()
    assert test_res["mode"] == "odata_v4_sandbox"
    coa = conn.fetch_chart_of_accounts("1000")
    assert len(coa.accounts) >= 35


def test_rfc_connector_fallback_when_pyrfc_absent():
    conn = SAPRFCConnector(config=ERPConnectionConfig(host="localhost"))
    assert conn.connect() is True
    test_res = conn.test_connection()
    assert "simulated_rfc" in test_res["mode"]
    assert "BAPI_ACC_DOCUMENT_POST" in test_res["bapis_supported"]


def test_oracle_connector_fallback_to_mock():
    conn = OracleRESTConnector(config=ERPConnectionConfig(host="localhost"))
    assert conn.connect() is True
    test_res = conn.test_connection()
    assert "oracle_fusion_rest_sandbox" in test_res["mode"]
    assert test_res["system_id"] == "ORACLE_ERP_CLOUD"
