"""Unit tests for Multi-Currency Triangulation Engine (ASC 830 / IAS 21)."""

from decimal import Decimal
import pytest

from gl_fuzzer.models.currency import Currency, ExchangeRateProvider
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem


def test_currency_enum_values():
    """Verify all major corporate currencies are supported in Currency enum."""
    expected = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"}
    actual = {c.value for c in Currency}
    assert expected.issubset(actual)


def test_exchange_rate_provider_usd_identity():
    """Verify USD to USD rate is always 1.000000."""
    fx = ExchangeRateProvider(seed=42, year=2026)
    rate = fx.get_rate_to_usd(Currency.USD, "2026-05-15")
    assert rate == Decimal("1.000000")

    rate_str = fx.get_rate_to_usd("USD", "2026-05-15")
    assert rate_str == Decimal("1.000000")


def test_exchange_rate_provider_fluctuation_and_reversion():
    """Verify exchange rates fluctuate around baseline and stay positive."""
    fx = ExchangeRateProvider(seed=123, year=2026)

    # EUR baseline is 1.0850
    rate_q1 = fx.get_rate_to_usd(Currency.EUR, "2026-02-15")
    rate_q3 = fx.get_rate_to_usd(Currency.EUR, "2026-08-15")

    assert rate_q1 > Decimal("0.80") and rate_q1 < Decimal("1.40")
    assert rate_q3 > Decimal("0.80") and rate_q3 < Decimal("1.40")

    # JPY baseline is 0.00675
    rate_jpy = fx.get_rate_to_usd(Currency.JPY, "2026-06-01")
    assert rate_jpy > Decimal("0.004") and rate_jpy < Decimal("0.010")


def test_exchange_rate_triangulation():
    """Verify triangulation between two non-USD currencies."""
    fx = ExchangeRateProvider(seed=42, year=2026)
    date_str = "2026-04-10"

    eur_to_usd = fx.get_rate_to_usd(Currency.EUR, date_str)
    gbp_to_usd = fx.get_rate_to_usd(Currency.GBP, date_str)
    expected_eur_to_gbp = (eur_to_usd / gbp_to_usd).quantize(Decimal("0.000001"))

    actual_eur_to_gbp = fx.get_exchange_rate(Currency.EUR, Currency.GBP, date_str)
    assert actual_eur_to_gbp == expected_eur_to_gbp

    # Same currency triangulation should be exactly 1.0
    assert fx.get_exchange_rate(Currency.EUR, Currency.EUR, date_str) == Decimal("1.000000")


def test_exchange_rate_convert():
    """Verify conversion of monetary amounts quantized to cents."""
    fx = ExchangeRateProvider(seed=42, year=2026)
    amount = Decimal("1000.00")
    converted, rate = fx.convert(amount, Currency.EUR, Currency.USD, "2026-06-15")

    assert isinstance(converted, Decimal)
    assert isinstance(rate, Decimal)
    assert converted == (amount * rate).quantize(Decimal("0.01"))


def test_line_item_multi_currency_defaults():
    """Verify LineItem defaults for multi-currency fields."""
    item = LineItem(
        line_id="L1",
        entry_id="E1",
        line_number=1,
        account_code="10000",
        debit_credit=DebitCredit.DEBIT,
        amount=Decimal("250.00"),
    )
    assert item.currency == "USD"
    assert item.currency_local == "USD"
    assert item.currency_group == "USD"
    assert item.amount_local == Decimal("250.00")
    assert item.amount_group == Decimal("250.00")
    assert item.exchange_rate_local == Decimal("1.000000")
    assert item.exchange_rate_group == Decimal("1.000000")


def test_journal_entry_multi_currency_balance():
    """Verify JournalEntry multi-currency balance properties."""
    debit_line = LineItem(
        line_id="L1",
        entry_id="E1",
        line_number=1,
        account_code="10000",
        debit_credit=DebitCredit.DEBIT,
        amount=Decimal("100.00"),
        amount_local=Decimal("110.00"),
        amount_group=Decimal("110.00"),
        currency="EUR",
        currency_local="USD",
        currency_group="USD",
    )
    credit_line = LineItem(
        line_id="L2",
        entry_id="E1",
        line_number=2,
        account_code="20000",
        debit_credit=DebitCredit.CREDIT,
        amount=Decimal("100.00"),
        amount_local=Decimal("110.00"),
        amount_group=Decimal("110.00"),
        currency="EUR",
        currency_local="USD",
        currency_group="USD",
    )

    entry = JournalEntry(
        entry_id="E1",
        batch_id="B1",
        document_number="DOC001",
        posting_date="2026-03-15",
        document_date="2026-03-15",
        created_at="2026-03-15T10:00:00Z",
        lines=[debit_line, credit_line],
    )

    assert entry.is_balanced is True
    assert entry.is_balanced_local is True
    assert entry.is_balanced_group is True
    assert entry.total_debits_local == Decimal("110.00")
    assert entry.total_credits_local == Decimal("110.00")
    assert entry.total_debits_group == Decimal("110.00")
    assert entry.total_credits_group == Decimal("110.00")


def test_journal_entry_unbalanced_local():
    """Verify unbalanced detection in local currency."""
    debit_line = LineItem(
        line_id="L1",
        entry_id="E1",
        line_number=1,
        account_code="10000",
        debit_credit=DebitCredit.DEBIT,
        amount=Decimal("100.00"),
        amount_local=Decimal("110.00"),
        amount_group=Decimal("110.00"),
    )
    credit_line = LineItem(
        line_id="L2",
        entry_id="E1",
        line_number=2,
        account_code="20000",
        debit_credit=DebitCredit.CREDIT,
        amount=Decimal("100.00"),
        amount_local=Decimal("109.99"),  # 1 cent off
        amount_group=Decimal("110.00"),
    )

    entry = JournalEntry(
        entry_id="E1",
        batch_id="B1",
        document_number="DOC001",
        posting_date="2026-03-15",
        document_date="2026-03-15",
        created_at="2026-03-15T10:00:00Z",
        lines=[debit_line, credit_line],
    )

    assert entry.is_balanced is True
    assert entry.is_balanced_local is False
    assert entry.is_balanced_group is True
