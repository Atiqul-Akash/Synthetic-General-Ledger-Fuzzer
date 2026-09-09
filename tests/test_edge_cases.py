"""Regression and edge case tests verifying bug fixes and forensic fidelity."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import numpy as np
import pytest

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.generators.distributions import BusinessCalendar
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.anomalies.pipeline import AnomalyPipeline
from gl_fuzzer.verification.audit_metrics import ForensicAuditEvaluator
from gl_fuzzer.exporters.csv_exporter import CSVGLExporter
from gl_fuzzer.cli import _load_entries_from_file


def test_calendar_month_end_always_business_day():
    """Verify that random_month_end_date never returns a weekend day."""
    calendar = BusinessCalendar(rng=np.random.default_rng(42))
    for _ in range(100):
        d = calendar.random_month_end_date()
        assert d.weekday() < 5, f"Date {d} is a weekend (weekday {d.weekday()})"


def test_calendar_reaches_end_of_year():
    """Verify that total_days includes December 31."""
    calendar = BusinessCalendar(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rng=np.random.default_rng(42),
    )
    # Check that total_days is 365
    assert calendar.total_days == 365


def test_csv_is_anomaly_boolean_roundtrip(tmp_path: Path):
    """Verify that loading entries from CSV preserves correct boolean is_anomaly flags."""
    # Create batch with 1 clean entry and 1 anomalous entry
    clean_entry = JournalEntry(
        entry_id="DOC_CLEAN_01",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_type=DocumentType.SA,
        document_number="100001",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="10:00:00",
        created_at="2026-09-06T10:00:00Z",
        created_by="AUTO",
        is_anomaly=False,
        anomaly_ids=[],
        lines=[
            LineItem(
                line_id="L1",
                entry_id="DOC_CLEAN_01",
                line_number=1,
                account_code="10100",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("100.00"),
            ),
            LineItem(
                line_id="L2",
                entry_id="DOC_CLEAN_01",
                line_number=2,
                account_code="40000",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("100.00"),
            ),
        ],
    )

    anom_entry = JournalEntry(
        entry_id="DOC_ANOM_01",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_type=DocumentType.MJE,
        document_number="190001",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="03:00:00",
        created_at="2026-09-06T03:00:00Z",
        created_by="GHOST_USER",
        is_anomaly=True,
        anomaly_ids=["ANOM_GHOST_1"],
        lines=[
            LineItem(
                line_id="L3",
                entry_id="DOC_ANOM_01",
                line_number=1,
                account_code="69000",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("500.00"),
            ),
            LineItem(
                line_id="L4",
                entry_id="DOC_ANOM_01",
                line_number=2,
                account_code="21000",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("500.00"),
            ),
        ],
    )

    csv_path = tmp_path / "test_roundtrip.csv"
    CSVGLExporter.export([clean_entry, anom_entry], csv_path)

    reloaded = _load_entries_from_file(csv_path)
    assert len(reloaded) == 2

    reloaded_clean = next(e for e in reloaded if e.entry_id == "DOC_CLEAN_01")
    reloaded_anom = next(e for e in reloaded if e.entry_id == "DOC_ANOM_01")

    # Critical check: clean entry must NOT be converted to True
    assert reloaded_clean.is_anomaly is False
    assert len(reloaded_clean.anomaly_ids) == 0

    assert reloaded_anom.is_anomaly is True
    assert "ANOM_GHOST_1" in reloaded_anom.anomaly_ids


def test_intercompany_no_false_2_hop_cycles():
    """Verify that a legitimate intercompany transfer (with mirror entries) does NOT trigger false 2-hop cycles."""
    # Entity 1000 transfers cash to Entity 2000
    sender_entry = JournalEntry(
        entry_id="IC_SEND_01",
        batch_id="B_IC",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_type=DocumentType.IC,
        document_number="700001",
        posting_date="2026-09-28",
        document_date="2026-09-28",
        entry_time="10:00:00",
        created_at="2026-09-28T10:00:00Z",
        created_by="TREASURY",
        lines=[
            LineItem(
                line_id="L1",
                entry_id="IC_SEND_01",
                line_number=1,
                account_code="12000",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("100000.00"),
                trading_partner="2000",
            ),
            LineItem(
                line_id="L2",
                entry_id="IC_SEND_01",
                line_number=2,
                account_code="10100",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("100000.00"),
            ),
        ],
    )

    receiver_entry = JournalEntry(
        entry_id="IC_RECV_01",
        batch_id="B_IC",
        company_code="2000",
        fiscal_year=2026,
        fiscal_period=9,
        document_type=DocumentType.IC,
        document_number="710001",
        posting_date="2026-09-28",
        document_date="2026-09-28",
        entry_time="10:00:00",
        created_at="2026-09-28T10:00:00Z",
        created_by="TREASURY",
        lines=[
            LineItem(
                line_id="L3",
                entry_id="IC_RECV_01",
                line_number=1,
                account_code="10100",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("100000.00"),
            ),
            LineItem(
                line_id="L4",
                entry_id="IC_RECV_01",
                line_number=2,
                account_code="23000",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("100000.00"),
                trading_partner="1000",
            ),
        ],
    )

    res = ForensicAuditEvaluator.detect_intercompany_cycles([sender_entry, receiver_entry])
    # Must NOT detect a cycle between 1000 and 2000
    assert res["has_circular_round_tripping"] is False
    assert res["detected_cycles_count"] == 0


def test_doa_clustering_requires_distinct_documents():
    """Verify that a single entry with multiple $9,800 lines does not trigger a DOA cluster alert."""
    single_multi_line_entry = JournalEntry(
        entry_id="DOC_SINGLE_MULTI",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_type=DocumentType.KR,
        document_number="510001",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="11:00:00",
        created_at="2026-09-06T11:00:00Z",
        lines=[
            LineItem(
                line_id="L1",
                entry_id="DOC_SINGLE_MULTI",
                line_number=1,
                account_code="64000",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("9800.00"),
                vendor_id="VEND_TEST",
            ),
            LineItem(
                line_id="L2",
                entry_id="DOC_SINGLE_MULTI",
                line_number=2,
                account_code="64000",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("9800.00"),
                vendor_id="VEND_TEST",
            ),
            LineItem(
                line_id="L3",
                entry_id="DOC_SINGLE_MULTI",
                line_number=3,
                account_code="20000",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("19600.00"),
                vendor_id="VEND_TEST",
            ),
        ],
    )

    res = ForensicAuditEvaluator.detect_doa_split_clusters([single_multi_line_entry])
    assert res["has_doa_violations"] is False
    assert res["detected_clusters_count"] == 0


def test_contra_account_normal_balance_comprehensive():
    """Verify that contra accounts validate properly under normal balance rules."""
    coa = ChartOfAccounts.create_default()

    # 11500 Allowance for Doubtful Accounts (Asset, Contra, Credit Normal)
    acc_11500 = coa.get_account("11500")
    assert acc_11500 is not None
    assert acc_11500.is_contra is True
    assert acc_11500.validate_normal_balance() is True

    # 17900 Accumulated Depreciation (Asset, Contra, Credit Normal)
    acc_17900 = coa.get_account("17900")
    assert acc_17900 is not None
    assert acc_17900.is_contra is True
    assert acc_17900.validate_normal_balance() is True

    # 43000 Sales Discounts Allowed (Revenue, Contra, Debit Normal)
    acc_43000 = coa.get_account("43000")
    assert acc_43000 is not None
    assert acc_43000.is_contra is True
    assert acc_43000.validate_normal_balance() is True

    # Standard non-contra asset (10100)
    acc_10100 = coa.get_account("10100")
    assert acc_10100 is not None
    assert acc_10100.is_contra is False
    assert acc_10100.validate_normal_balance() is True


def test_doa_mixed_timezone_sorting():
    """Verify that detect_doa_split_clusters does not crash with mixed timezone/naive timestamps."""
    entry_aware = JournalEntry(
        entry_id="DOC_AWARE_1",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_type=DocumentType.KR,
        document_number="510001",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="10:00:00",
        created_at="2026-09-06T10:00:00Z",  # Has Z
        lines=[
            LineItem(
                line_id="L1",
                entry_id="DOC_AWARE_1",
                line_number=1,
                account_code="64000",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("9800.00"),
                vendor_id="VEND_AWARE",
            ),
            LineItem(
                line_id="L2",
                entry_id="DOC_AWARE_1",
                line_number=2,
                account_code="20000",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("9800.00"),
                vendor_id="VEND_AWARE",
            ),
        ],
    )

    entry_naive = JournalEntry(
        entry_id="DOC_NAIVE_2",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_type=DocumentType.KR,
        document_number="510002",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="11:00:00",
        created_at="2026-09-06 11:00:00",  # Naive format without Z or offset
        lines=[
            LineItem(
                line_id="L3",
                entry_id="DOC_NAIVE_2",
                line_number=1,
                account_code="64000",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("9850.00"),
                vendor_id="VEND_AWARE",
            ),
            LineItem(
                line_id="L4",
                entry_id="DOC_NAIVE_2",
                line_number=2,
                account_code="20000",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("9850.00"),
                vendor_id="VEND_AWARE",
            ),
        ],
    )

    res = ForensicAuditEvaluator.detect_doa_split_clusters([entry_aware, entry_naive])
    assert res["has_doa_violations"] is True
    assert res["detected_clusters_count"] == 1


def test_exchange_rate_provider_compact_sap_dates():
    """Verify that get_rate_to_usd resolves compact 8-digit SAP BUDAT dates."""
    from gl_fuzzer.models.currency import Currency, ExchangeRateProvider
    fx = ExchangeRateProvider(seed=42, year=2026)

    rate_iso = fx.get_rate_to_usd(Currency.EUR, "2026-05-18")
    rate_compact = fx.get_rate_to_usd(Currency.EUR, "20260518")

    assert rate_iso == rate_compact
    assert rate_compact != Decimal("1.080000")


def test_o2c_single_customer_invoice_generation():
    """Verify that O2CCycleGenerator can generate single balanced customer invoices."""
    from gl_fuzzer.generators.o2c_cycle import O2CCycleGenerator
    coa = ChartOfAccounts.create_default()
    cal = BusinessCalendar(rng=np.random.default_rng(42))
    gen = O2CCycleGenerator(coa=coa, calendar=cal, rng=np.random.default_rng(42))

    inv = gen.generate_single_customer_invoice(batch_id="TEST_B1", company_code="1000", amount=Decimal("1500.00"))
    assert inv.is_balanced is True
    assert inv.business_cycle == "O2C"
    assert inv.document_type == DocumentType.DR
    assert len(inv.lines) == 2
    assert inv.lines[0].account_code == "11000"
    assert inv.lines[0].debit_credit == DebitCredit.DEBIT
    assert inv.lines[1].account_code in ("40000", "41000")
    assert inv.lines[1].debit_credit == DebitCredit.CREDIT


def test_batch_multi_currency_properties():
    """Verify that Batch accurately computes multi-currency aggregates."""
    l1 = LineItem(
        line_id="L1", entry_id="E1", line_number=1, account_code="10100",
        debit_credit=DebitCredit.DEBIT, amount=Decimal("100.00"),
        amount_local=Decimal("110.00"), amount_group=Decimal("110.00"),
    )
    l2 = LineItem(
        line_id="L2", entry_id="E1", line_number=2, account_code="40000",
        debit_credit=DebitCredit.CREDIT, amount=Decimal("100.00"),
        amount_local=Decimal("110.00"), amount_group=Decimal("110.00"),
    )
    entry = JournalEntry(
        entry_id="E1", batch_id="B1", company_code="1000", fiscal_year=2026, fiscal_period=9,
        document_number="1001", posting_date="2026-09-06", document_date="2026-09-06",
        created_at="2026-09-06T10:00:00Z", lines=[l1, l2],
    )
    batch = Batch(batch_id="B1", created_at="2026-09-06T10:00:00Z", entries=[entry])

    assert batch.total_debits_local == Decimal("110.00")
    assert batch.total_credits_local == Decimal("110.00")
    assert batch.is_balanced_local is True
    assert batch.total_debits_group == Decimal("110.00")
    assert batch.total_credits_group == Decimal("110.00")
    assert batch.is_balanced_group is True


def test_streaming_parquet_close_empty(tmp_path: Path):
    """Verify that StreamingParquetExporter closes cleanly without errors when 0 entries are appended."""
    from gl_fuzzer.exporters.streaming_parquet import StreamingParquetExporter
    p_path = tmp_path / "empty_stream.parquet"
    with StreamingParquetExporter(p_path) as exporter:
        pass  # No entries appended

    assert p_path.exists()
    assert p_path.stat().st_size > 0


def test_sap_bseg_exporter_none_guards(tmp_path: Path):
    """Verify that SAPBSEGExporter handles None fields gracefully without raising TypeError."""
    from gl_fuzzer.exporters.sap_bseg_exporter import SAPBSEGExporter
    entry = JournalEntry(
        entry_id="E_NONE",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_number="8001",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        created_at="2026-09-06T10:00:00Z",
        created_by="SYSTEM",
        reference="",
        header_text="",
        lines=[
            LineItem(
                line_id="L1", entry_id="E_NONE", line_number=1, account_code="10100",
                debit_credit=DebitCredit.DEBIT, amount=Decimal("50.00"), line_text="",
            ),
            LineItem(
                line_id="L2", entry_id="E_NONE", line_number=2, account_code="40000",
                debit_credit=DebitCredit.CREDIT, amount=Decimal("50.00"), line_text="",
            ),
        ],
    )
    object.__setattr__(entry, 'created_by', None)
    object.__setattr__(entry, 'reference', None)
    object.__setattr__(entry, 'header_text', None)
    object.__setattr__(entry.lines[0], 'line_text', None)

    out_dir = tmp_path / "sap_none"
    results = SAPBSEGExporter.export([entry], out_dir)
    assert "BKPF" in results
    assert "BSEG" in results
    assert results["BKPF"][0].exists()
    assert results["BSEG"][0].exists()


def test_benford_synthesize_amount_never_exceeds_digit():
    """Verify that synthesize_amount_with_first_digit never overflows into the next leading digit."""
    from gl_fuzzer.generators.distributions import BenfordDistribution
    rng = np.random.default_rng(12345)
    for digit in range(1, 10):
        for mag in range(2, 6):
            for _ in range(50):
                amt = BenfordDistribution.synthesize_amount_with_first_digit(
                    first_digit=digit, magnitude_min=mag, magnitude_max=mag, rng=rng
                )
                amt_str = str(amt)
                assert int(amt_str[0]) == digit, f"Expected leading digit {digit}, got {amt_str}"


def test_subledger_three_way_match_overinvoicing_does_not_overclear():
    """Verify that over-invoiced quantities cap GR/IR clearing to received_qty, preserving balance and bridge."""
    from gl_fuzzer.subledgers.three_way_match import ThreeWayMatchingEngine, MatchResult
    twm = ThreeWayMatchingEngine()
    po = twm.create_purchase_order(
        vendor_id="VEND_01",
        material_number="MAT-1001",
        ordered_qty=Decimal("10.00"),
        po_unit_price=Decimal("45.00"),
    )
    gr, we_entry = twm.post_goods_receipt(po, received_qty=Decimal("10.00"))
    assert we_entry.is_balanced is True

    # Over-invoiced: 15 units billed instead of 10
    ir, re_entry, match_st = twm.post_invoice_receipt(
        po, gr, invoiced_qty=Decimal("15.00"), invoiced_unit_price=Decimal("50.00")
    )
    assert match_st == MatchResult.DUAL_VARIANCE
    assert re_entry.is_balanced is True

    gr_leg = [l for l in re_entry.lines if l.account_code == "21150"][0]
    # GR/IR clearing should only clear the 10 units received ($450.00), not 15 ($675.00)
    assert gr_leg.amount == Decimal("450.00")
    ap_leg = [l for l in re_entry.lines if l.account_code == "20000"][0]
    assert ap_leg.amount == Decimal("750.00")  # 15 * $50


def test_subledger_order_fulfillment_overdelivery_capped_billing():
    """Verify that billing quantity is capped to ordered_qty if delivery attempts over-shipping."""
    from gl_fuzzer.subledgers.order_fulfillment import SalesOrderFulfillmentEngine, DeliveryWaybill
    sfe = SalesOrderFulfillmentEngine()
    so = sfe.create_sales_order(
        customer_id="CUST_01",
        material_number="MAT-1001",
        ordered_qty=Decimal("10.00"),
        unit_price=Decimal("100.00"),
    )
    # Simulate delivery of 15 units
    waybill = DeliveryWaybill(
        waybill_number="WA_TEST_01",
        so_number=so.so_number,
        shipped_qty=Decimal("15.00"),
        cogs_valuation=Decimal("675.00"),
        shipping_date="2026-04-05",
    )
    rv = sfe.post_billing_document(so, waybill)
    assert rv.is_balanced is True
    # Billed amount capped at 10 * 100 = 1000.00
    assert rv.total_debits == Decimal("1000.00")


def test_mock_erp_mixed_currency_rejection():
    """Verify that MockERPConnector rejects entries with mismatched line-item currencies."""
    from gl_fuzzer.connectors.mock_erp import MockERPConnector
    connector = MockERPConnector()
    connector.connect()

    l1 = LineItem(line_id="L1", entry_id="E1", line_number=1, account_code="10100",
                  debit_credit=DebitCredit.DEBIT, amount=Decimal("100.00"), currency="USD")
    l2 = LineItem(line_id="L2", entry_id="E1", line_number=2, account_code="20000",
                  debit_credit=DebitCredit.CREDIT, amount=Decimal("100.00"), currency="EUR")
    entry = JournalEntry(
        entry_id="E1", batch_id="B1", company_code="1000", fiscal_year=2026, fiscal_period=1,
        document_number="100001", posting_date="2026-01-15", document_date="2026-01-15",
        created_at="2026-01-15T10:00:00Z", lines=[l1, l2],
    )
    res = connector.post_journal_entry(entry)
    assert res.success is False
    assert res.error_code == "SAP_F5_MIXED_CURRENCY"


def test_mock_erp_multi_open_item_clearing():
    """Verify that MockERPConnector iterates and clears multiple open items on a single payment."""
    from gl_fuzzer.connectors.mock_erp import MockERPConnector
    connector = MockERPConnector()
    connector.connect()

    def _post_kr(doc_num, amt):
        l1 = LineItem(line_id=f"{doc_num}_1", entry_id=doc_num, line_number=1, account_code="14000",
                      debit_credit=DebitCredit.DEBIT, amount=amt)
        l2 = LineItem(line_id=f"{doc_num}_2", entry_id=doc_num, line_number=2, account_code="20000",
                      debit_credit=DebitCredit.CREDIT, amount=amt, vendor_id="VEND_MULTI")
        e = JournalEntry(entry_id=doc_num, batch_id="B1", company_code="1000", fiscal_year=2026, fiscal_period=1,
                         document_type=DocumentType.KR, document_number=doc_num, posting_date="2026-01-15",
                         document_date="2026-01-15", created_at="2026-01-15T10:00:00Z", lines=[l1, l2])
        return connector.post_journal_entry(e)

    _post_kr("KR_01", Decimal("300.00"))
    _post_kr("KR_02", Decimal("400.00"))

    open_items = connector.fetch_open_items("1000")
    assert len(open_items) == 2

    # Single payment of $700.00
    l_kz1 = LineItem(line_id="KZ_1", entry_id="KZ_DOC", line_number=1, account_code="20000",
                     debit_credit=DebitCredit.DEBIT, amount=Decimal("700.00"), vendor_id="VEND_MULTI")
    l_kz2 = LineItem(line_id="KZ_2", entry_id="KZ_DOC", line_number=2, account_code="10100",
                     debit_credit=DebitCredit.CREDIT, amount=Decimal("700.00"))
    kz = JournalEntry(entry_id="KZ_DOC", batch_id="B1", company_code="1000", fiscal_year=2026, fiscal_period=1,
                      document_type=DocumentType.KZ, document_number="KZ_DOC", posting_date="2026-01-20",
                      document_date="2026-01-20", created_at="2026-01-20T10:00:00Z", lines=[l_kz1, l_kz2])
    res = connector.post_journal_entry(kz)
    assert res.success is True

    # Both open items must be cleared
    open_items_after = connector.fetch_open_items("1000")
    assert len(open_items_after) == 0


def test_mdm_tamper_vendor_bank_model_copy():
    """Verify that BankRoutingTamperingMutator does not mutate original VendorMaster object in place."""
    from gl_fuzzer.mdm.models import VendorMaster
    from gl_fuzzer.mdm.mutators import BankRoutingTamperingMutator
    orig_vendor = VendorMaster(
        vendor_id="VEND_IMMUTABLE",
        name="Immutable Tech Ltd",
        tax_id="12-9999999",
        bank_routing_number="021000021",
        bank_account_number="123456789",
    )
    tampered, record = BankRoutingTamperingMutator.mutate(orig_vendor, tamper_date="2026-04-14")
    assert tampered.bank_routing_number != orig_vendor.bank_routing_number
    assert orig_vendor.bank_routing_number == "021000021"
    assert orig_vendor.bank_account_number == "123456789"


def test_remediation_strict_sql_balance():
    """Verify that RemediationAdvisor enforces strict zero-sum SQL balance equality."""
    from gl_fuzzer.remediation.engine import RemediationAdvisor
    patch = RemediationAdvisor.advise_for_finding({"finding_type": "IMBALANCE", "description": "Debits do not match credits"})
    assert "CHECK (total_debits = total_credits)" in patch.code_or_rule
    assert "0.0001" not in patch.code_or_rule


def test_pdf_invoice_courier_fonts(tmp_path: Path):
    """Verify that FinancialPDFGenerator outputs Courier monospace fonts for exact column alignment."""
    from gl_fuzzer.documents.models import SyntheticInvoiceData, DocumentItemLine
    from gl_fuzzer.documents.pdf_generator import FinancialPDFGenerator
    gen = FinancialPDFGenerator()
    inv_data = SyntheticInvoiceData(
        invoice_number="INV-FONT-TEST",
        invoice_date="2026-03-15",
        vendor_name="Test Monospace Corp",
        vendor_tax_id="12-3456781",
        vendor_routing="021000021",
        vendor_account="123456789",
        customer_name="Client Corp",
        subtotal=Decimal("100.00"),
        total_amount=Decimal("100.00"),
        items=[DocumentItemLine(item_no=1, description="Part A", quantity=Decimal("1"),
                                unit_price=Decimal("100.00"), total_price=Decimal("100.00"))]
    )
    out_pdf = tmp_path / "font_test.pdf"
    gen.generate_invoice_pdf(inv_data, out_pdf)
    content = out_pdf.read_bytes()
    assert b"/BaseFont /Courier-Bold" in content
    assert b"/BaseFont /Courier" in content
    assert b"Helvetica" not in content

