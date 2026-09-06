"""Unit tests for the Mathematical Invariant Verifier."""

from decimal import Decimal
import pytest

from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.anomalies.pipeline import AnomalyPipeline
from gl_fuzzer.verification.invariants import InvariantVerifier


def test_invariant_verifier_on_clean_batch():
    engine = BaseSynthesisEngine(seed=42)
    batch = engine.generate_batch(target_entry_count=100)

    report = InvariantVerifier.verify_batch(batch)
    assert report.is_globally_balanced is True
    assert report.unbalanced_entries_count == 0
    assert len(report.violations) == 0
    assert report.total_debits == report.total_credits


def test_invariant_verifier_on_fuzzed_batch():
    engine = BaseSynthesisEngine(seed=77)
    batch = engine.generate_batch(target_entry_count=150)
    pipeline = AnomalyPipeline(seed=77)
    pipeline.inject_anomalies(batch, overall_anomaly_rate=0.15)

    report = InvariantVerifier.verify_batch(batch)
    assert report.is_globally_balanced is True
    assert report.unbalanced_entries_count == 0
    assert len(report.violations) == 0


def test_invariant_verifier_detects_unbalanced_entry():
    entry = JournalEntry(
        entry_id="BAD_ENTRY",
        batch_id="B_BAD",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_number="999999",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        created_at="2026-09-06T12:00:00Z",
        lines=[
            LineItem(
                line_id="L1",
                entry_id="BAD_ENTRY",
                line_number=1,
                account_code="10100",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("100.00"),
            ),
            LineItem(
                line_id="L2",
                entry_id="BAD_ENTRY",
                line_number=2,
                account_code="20000",
                debit_credit=DebitCredit.CREDIT,
                amount=Decimal("100.01"),  # Off by 1 cent
            ),
        ],
    )

    violations = InvariantVerifier.verify_entry(entry)
    assert len(violations) == 1
    assert violations[0].violation_type == "UNBALANCED_ENTRY"


def test_invariant_verifier_detects_missing_legs():
    entry = JournalEntry(
        entry_id="ONE_LEG_ENTRY",
        batch_id="B_BAD",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_number="999998",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        created_at="2026-09-06T12:00:00Z",
        lines=[
            LineItem(
                line_id="L1",
                entry_id="ONE_LEG_ENTRY",
                line_number=1,
                account_code="10100",
                debit_credit=DebitCredit.DEBIT,
                amount=Decimal("100.00"),
            ),
        ],
    )

    violations = InvariantVerifier.verify_entry(entry)
    assert any(v.violation_type == "MISSING_LEGS" for v in violations)
