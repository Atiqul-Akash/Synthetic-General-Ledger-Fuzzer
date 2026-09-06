"""Comprehensive unit tests for GL Fuzzer data models.

Covers:
- models.coa: Account, AccountType, NormalBalance, ChartOfAccounts
- models.journal: DebitCredit, DocumentType, LineItem, JournalEntry, Batch
- models.manifest: AnomalyType, AnomalyRecord, GroundTruthManifest
"""

from decimal import Decimal
import pytest

from gl_fuzzer.models.coa import (
    Account,
    AccountType,
    ChartOfAccounts,
    NormalBalance,
)
from gl_fuzzer.models.journal import (
    Batch,
    DebitCredit,
    DocumentType,
    JournalEntry,
    LineItem,
)
from gl_fuzzer.models.manifest import (
    AnomalyRecord,
    AnomalyType,
    GroundTruthManifest,
)


# ==========================================
# 1. Chart of Accounts Models Tests
# ==========================================

def test_account_creation_and_attributes():
    acc = Account(
        code="10100",
        name="Cash and Cash Equivalents",
        account_type=AccountType.ASSET,
        normal_balance=NormalBalance.DEBIT,
        parent_code="10000",
        description="Main operating checking account",
    )
    assert acc.code == "10100"
    assert acc.name == "Cash and Cash Equivalents"
    assert acc.account_type == AccountType.ASSET
    assert acc.normal_balance == NormalBalance.DEBIT
    assert acc.is_reconciliation is False
    assert acc.validate_normal_balance() is True


def test_contra_account_normal_balance():
    contra = Account(
        code="17900",
        name="Accumulated Depreciation",
        account_type=AccountType.ASSET,
        normal_balance=NormalBalance.CREDIT,
        description="Contra-asset account",
    )
    assert contra.code == "17900"
    assert contra.account_type == AccountType.ASSET
    assert contra.normal_balance == NormalBalance.CREDIT


def test_default_chart_of_accounts_coverage():
    coa = ChartOfAccounts.create_default()
    assert len(coa.accounts) >= 30

    # Test key account types exist
    asset_accs = coa.get_accounts_by_type(AccountType.ASSET)
    liability_accs = coa.get_accounts_by_type(AccountType.LIABILITY)
    equity_accs = coa.get_accounts_by_type(AccountType.EQUITY)
    rev_accs = coa.get_accounts_by_type(AccountType.REVENUE)
    exp_accs = coa.get_accounts_by_type(AccountType.EXPENSE)

    assert len(asset_accs) > 0
    assert len(liability_accs) > 0
    assert len(equity_accs) > 0
    assert len(rev_accs) > 0
    assert len(exp_accs) > 0

    # Non-existent account returns None
    assert coa.get_account("999999") is None


def test_coa_add_account():
    coa = ChartOfAccounts()
    acc = Account(
        code="10100",
        name="Cash",
        account_type=AccountType.ASSET,
        normal_balance=NormalBalance.DEBIT,
    )
    coa.add_account(acc)
    assert coa.get_account("10100") == acc


# ==========================================
# 2. Journal & LineItem Models Tests
# ==========================================

def test_line_item_quantization():
    line = LineItem(
        line_id="L1",
        entry_id="E1",
        line_number=1,
        account_code="10100",
        debit_credit=DebitCredit.DEBIT,
        amount=Decimal("123.4567"),
    )
    # Quantized to 2 decimal places with ROUND_HALF_UP -> 123.46
    assert line.amount == Decimal("123.46")


def test_line_item_posting_key_auto_assignment():
    debit_line = LineItem(
        line_id="L1",
        entry_id="E1",
        line_number=1,
        account_code="10100",
        debit_credit=DebitCredit.DEBIT,
        amount=Decimal("100.00"),
    )
    assert debit_line.posting_key == "40"

    credit_line = LineItem(
        line_id="L2",
        entry_id="E1",
        line_number=2,
        account_code="40000",
        debit_credit=DebitCredit.CREDIT,
        amount=Decimal("100.00"),
    )
    assert credit_line.posting_key == "50"


def test_journal_entry_balanced_delta():
    lines = [
        LineItem(
            line_id="L1",
            entry_id="E1",
            line_number=1,
            account_code="10100",
            debit_credit=DebitCredit.DEBIT,
            amount=Decimal("500.00"),
        ),
        LineItem(
            line_id="L2",
            entry_id="E1",
            line_number=2,
            account_code="40000",
            debit_credit=DebitCredit.CREDIT,
            amount=Decimal("500.00"),
        ),
    ]
    entry = JournalEntry(
        entry_id="E1",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_number="100001",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="12:00:00",
        created_at="2026-09-06T12:00:00Z",
        lines=lines,
    )
    assert entry.is_balanced is True
    assert entry.balance_delta == Decimal("0.00")
    assert entry.total_debits == Decimal("500.00")
    assert entry.total_credits == Decimal("500.00")


def test_journal_entry_unbalanced_delta():
    lines = [
        LineItem(
            line_id="L1",
            entry_id="E2",
            line_number=1,
            account_code="10100",
            debit_credit=DebitCredit.DEBIT,
            amount=Decimal("500.00"),
        ),
        LineItem(
            line_id="L2",
            entry_id="E2",
            line_number=2,
            account_code="40000",
            debit_credit=DebitCredit.CREDIT,
            amount=Decimal("499.00"),
        ),
    ]
    entry = JournalEntry(
        entry_id="E2",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_number="100002",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="12:00:00",
        created_at="2026-09-06T12:00:00Z",
        lines=lines,
    )
    assert entry.is_balanced is False
    assert entry.balance_delta == Decimal("1.00")


def test_batch_totals_and_properties():
    lines1 = [
        LineItem(
            line_id="L1",
            entry_id="E1",
            line_number=1,
            account_code="10100",
            debit_credit=DebitCredit.DEBIT,
            amount=Decimal("100.00"),
        ),
        LineItem(
            line_id="L2",
            entry_id="E1",
            line_number=2,
            account_code="40000",
            debit_credit=DebitCredit.CREDIT,
            amount=Decimal("100.00"),
        ),
    ]
    lines2 = [
        LineItem(
            line_id="L3",
            entry_id="E2",
            line_number=1,
            account_code="50000",
            debit_credit=DebitCredit.DEBIT,
            amount=Decimal("250.50"),
        ),
        LineItem(
            line_id="L4",
            entry_id="E2",
            line_number=2,
            account_code="14100",
            debit_credit=DebitCredit.CREDIT,
            amount=Decimal("250.50"),
        ),
    ]
    e1 = JournalEntry(
        entry_id="E1",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_number="100001",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="10:00:00",
        created_at="2026-09-06T10:00:00Z",
        lines=lines1,
    )
    e2 = JournalEntry(
        entry_id="E2",
        batch_id="B1",
        company_code="1000",
        fiscal_year=2026,
        fiscal_period=9,
        document_number="100002",
        posting_date="2026-09-06",
        document_date="2026-09-06",
        entry_time="11:00:00",
        created_at="2026-09-06T11:00:00Z",
        lines=lines2,
    )

    batch = Batch(
        batch_id="B1",
        created_at="2026-09-06T12:00:00Z",
        entries=[e1, e2],
    )
    assert len(batch.entries) == 2
    assert batch.total_line_count == 4
    assert batch.total_debits == Decimal("350.50")
    assert batch.total_credits == Decimal("350.50")
    assert batch.is_balanced is True


# ==========================================
# 3. Manifest Models Tests
# ==========================================

def test_anomaly_record_model():
    record = AnomalyRecord(
        anomaly_id="ANOM_001",
        anomaly_type=AnomalyType.BENFORD_SKEW,
        sox_control="SOX-404-JE-03",
        audit_script="AUDIT-BENFORD-01",
        affected_entry_ids=["E1", "E2"],
        affected_line_ids=["L1", "L3"],
        parameters={"digit": 9, "multiplier": 3.5},
        description="Injected excess first digit 9 entries",
        forensic_indicator="Chi-square test p < 0.05",
    )
    assert record.anomaly_id == "ANOM_001"
    assert record.anomaly_type == AnomalyType.BENFORD_SKEW
    assert len(record.affected_entry_ids) == 2
    assert record.parameters["digit"] == 9

    # Model serialization to dict
    d = record.model_dump()
    assert d["anomaly_id"] == "ANOM_001"
    assert d["anomaly_type"] == "BENFORD_SKEW"


def test_ground_truth_manifest_model():
    manifest = GroundTruthManifest(
        dataset_id="DS_TEST_2026",
        generated_at="2026-09-06T12:00:00Z",
        total_entries=500,
        total_lines=1200,
        seed=42,
        anomalies=[],
    )
    assert manifest.dataset_id == "DS_TEST_2026"
    assert manifest.total_entries == 500
    assert manifest.total_lines == 1200
    assert manifest.seed == 42
    assert len(manifest.anomalies) == 0

    record = AnomalyRecord(
        anomaly_id="ANOM_100",
        anomaly_type=AnomalyType.OFF_HOURS_GHOST_ENTRY,
        sox_control="SOX-404-JE-01",
        audit_script="AUDIT-GHOST-01",
        affected_entry_ids=["E99"],
        description="Ghost MJE",
        forensic_indicator="Off-hours timestamp",
    )
    manifest.anomalies.append(record)
    assert len(manifest.anomalies) == 1
