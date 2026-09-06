"""Unit tests for Chart of Accounts and Journal Entry models."""

from decimal import Decimal
import pytest
from gl_fuzzer.models.coa import Account, AccountType, ChartOfAccounts, NormalBalance
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem


def test_coa_creation_and_lookup():
    coa = ChartOfAccounts.create_default()
    assert len(coa.accounts) >= 20

    cash_acc = coa.get_account("10100")
    assert cash_acc is not None
    assert cash_acc.account_type == AccountType.ASSET
    assert cash_acc.normal_balance == NormalBalance.DEBIT
    assert cash_acc.validate_normal_balance() is True

    rev_acc = coa.get_account("40000")
    assert rev_acc is not None
    assert rev_acc.account_type == AccountType.REVENUE
    assert rev_acc.normal_balance == NormalBalance.CREDIT
    assert rev_acc.validate_normal_balance() is True


def test_journal_entry_balance_properties():
    lines = [
        LineItem(
            line_id="L1",
            entry_id="E1",
            line_number=1,
            account_code="10100",
            debit_credit=DebitCredit.DEBIT,
            amount=Decimal("1520.50"),
        ),
        LineItem(
            line_id="L2",
            entry_id="E1",
            line_number=2,
            account_code="40000",
            debit_credit=DebitCredit.CREDIT,
            amount=Decimal("1520.50"),
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
        entry_time="10:00:00",
        created_at="2026-09-06T10:00:00Z",
        lines=lines,
    )

    assert entry.total_debits == Decimal("1520.50")
    assert entry.total_credits == Decimal("1520.50")
    assert entry.balance_delta == Decimal("0.00")
    assert entry.is_balanced is True


def test_journal_entry_unbalanced():
    lines = [
        LineItem(
            line_id="L1",
            entry_id="E2",
            line_number=1,
            account_code="10100",
            debit_credit=DebitCredit.DEBIT,
            amount=Decimal("100.00"),
        ),
        LineItem(
            line_id="L2",
            entry_id="E2",
            line_number=2,
            account_code="40000",
            debit_credit=DebitCredit.CREDIT,
            amount=Decimal("99.99"),
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
        entry_time="10:00:00",
        created_at="2026-09-06T10:00:00Z",
        lines=lines,
    )

    assert entry.is_balanced is False
    assert entry.balance_delta == Decimal("0.01")
