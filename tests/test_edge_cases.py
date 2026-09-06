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
