"""Comprehensive unit tests for Multi-Jurisdictional Tax Localization Engine."""

from decimal import Decimal
import pytest

from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyType
from gl_fuzzer.tax.models import (
    TaxCalculationResult,
    TaxCode,
    TaxExemptionReason,
    TaxJurisdiction,
    TaxReturnSummary,
)
from gl_fuzzer.tax.us_sales_tax import USSalesTaxEngine
from gl_fuzzer.tax.eu_vat import EUVATEngine
from gl_fuzzer.tax.withholding import WithholdingTaxEngine
from gl_fuzzer.tax.engine import TaxLocalizationEngine
from gl_fuzzer.verification.invariants import InvariantVerifier


def test_us_sales_tax_california_rate():
    engine = USSalesTaxEngine(default_state="CA")
    base = Decimal("1000.00")
    res = engine.calculate_sales_tax(base, state_code="CA", is_purchase=False)

    assert res.tax_amount == Decimal("86.80")  # 8.68%
    assert res.total_with_tax == Decimal("1086.80")
    assert len(res.tax_line_items) == 1
    assert res.tax_line_items[0].account_code == "22000"
    assert res.tax_line_items[0].debit_credit == DebitCredit.CREDIT


def test_us_sales_tax_resale_exemption_zero_tax():
    engine = USSalesTaxEngine()
    base = Decimal("5000.00")
    res = engine.calculate_sales_tax(base, state_code="CA", exemption=TaxExemptionReason.RESALE)

    assert res.tax_amount == Decimal("0.00")
    assert res.total_with_tax == Decimal("5000.00")
    assert len(res.tax_line_items) == 0


def test_us_sales_tax_use_tax_accrual_double_entry_balance():
    engine = USSalesTaxEngine()
    base = Decimal("2000.00")
    res = engine.calculate_use_tax_accrual(base, state_code="TX")

    assert res.is_reverse_charge is True
    assert res.tax_amount == Decimal("165.00")  # 8.25%
    assert len(res.tax_line_items) == 2

    dr_leg = [l for l in res.tax_line_items if l.debit_credit == DebitCredit.DEBIT][0]
    cr_leg = [l for l in res.tax_line_items if l.debit_credit == DebitCredit.CREDIT][0]

    assert dr_leg.account_code == "13100"  # Use Tax Receivable
    assert cr_leg.account_code == "22300"  # Use Tax Payable
    assert dr_leg.amount == cr_leg.amount == Decimal("165.00")


def test_us_nexus_all_50_states_rates_present():
    engine = USSalesTaxEngine()
    assert len(engine.STATE_RATES) >= 51  # 50 states + DC
    assert engine.get_rate_for_state("NY") == Decimal("0.0852")
    assert engine.get_rate_for_state("WA") == Decimal("0.0938")
    assert engine.get_rate_for_state("OR") == Decimal("0.0000")  # No sales tax state


def test_eu_vat_germany_standard_rate():
    engine = EUVATEngine(home_country="DE")
    base = Decimal("10000.00")
    res = engine.calculate_domestic_vat(base, country="DE", is_purchase=False)

    assert res.tax_amount == Decimal("1900.00")  # 19% standard German VAT
    assert res.total_with_tax == Decimal("11900.00")
    assert res.tax_code.code == "A1"
    assert res.tax_line_items[0].account_code == "22100"


def test_eu_vat_reverse_charge_wash_legs_balance():
    engine = EUVATEngine()
    base = Decimal("50000.00")
    res = engine.calculate_reverse_charge(base, buyer_country="DE", seller_country="FR")

    assert res.is_reverse_charge is True
    assert res.tax_code.code == "RC"
    assert res.tax_amount == Decimal("9500.00")  # 19%
    assert len(res.tax_line_items) == 2

    dr_leg = [l for l in res.tax_line_items if l.debit_credit == DebitCredit.DEBIT][0]
    cr_leg = [l for l in res.tax_line_items if l.debit_credit == DebitCredit.CREDIT][0]

    assert dr_leg.account_code == "13000"  # Input VAT Recoverable
    assert cr_leg.account_code == "22100"  # Output VAT Self-Assessed
    assert dr_leg.amount == cr_leg.amount == Decimal("9500.00")


def test_uk_vat_standard_rate():
    engine = EUVATEngine()
    base = Decimal("1000.00")
    res = engine.calculate_domestic_vat(base, country="UK", is_purchase=True)

    assert res.tax_amount == Decimal("200.00")  # 20% UK standard VAT
    assert res.tax_code.code == "V1"
    assert res.tax_line_items[0].account_code == "13000"


def test_wht_section_194j_deduction():
    engine = WithholdingTaxEngine()
    gross = Decimal("10000.00")
    net_cash, wht_amt, res = engine.calculate_withholding(gross, schedule_name="SEC_194J_PROFESSIONAL")

    assert wht_amt == Decimal("1000.00")  # 10%
    assert net_cash == Decimal("9000.00")
    assert len(res.tax_line_items) == 1
    assert res.tax_line_items[0].account_code == "22200"  # Withholding Tax Payable
    assert res.tax_line_items[0].amount == Decimal("1000.00")


def test_wht_below_threshold_no_deduction():
    engine = WithholdingTaxEngine()
    gross = Decimal("300.00")  # Below $500 threshold
    net_cash, wht_amt, _ = engine.calculate_withholding(gross)

    assert wht_amt == Decimal("0.00")
    assert net_cash == Decimal("300.00")


def test_wht_evasion_anomaly_flag():
    engine = WithholdingTaxEngine()
    entry = JournalEntry(
        entry_id="PAY_TEST",
        batch_id="B1",
        company_code="1000",
        document_type=DocumentType.KZ,
        document_number="KZ_001",
        posting_date="2026-01-15",
        document_date="2026-01-15",
        created_at="2026-01-15T10:00:00Z",
        lines=[],
    )
    res_entry = engine.apply_wht_to_payment_entry(entry, inject_evasion_anomaly=True)
    assert res_entry.is_anomaly is True
    assert AnomalyType.TAX_EVASION_ZERO_WHT.value in res_entry.anomaly_ids


def test_tax_localization_engine_facade_route_by_jurisdiction():
    facade = TaxLocalizationEngine()
    base = Decimal("1000.00")

    # US CA
    res_us = facade.calculate_tax(base, jurisdiction=TaxJurisdiction.US_CA)
    assert res_us.tax_amount == Decimal("86.80")

    # EU DE
    res_eu = facade.calculate_tax(base, jurisdiction=TaxJurisdiction.EU_DE)
    assert res_eu.tax_amount == Decimal("190.00")

    # GLOBAL (flat 6%)
    res_gl = facade.calculate_tax(base, jurisdiction=TaxJurisdiction.GLOBAL)
    assert res_gl.tax_amount == Decimal("60.00")


def test_tax_return_summary_net_payable():
    facade = TaxLocalizationEngine()

    # Create dummy entries with output tax and input tax
    entry1 = JournalEntry(
        entry_id="E1",
        batch_id="B1",
        company_code="1000",
        document_type=DocumentType.DR,
        document_number="DR_001",
        posting_date="2026-02-01",
        document_date="2026-02-01",
        created_at="2026-02-01T10:00:00Z",
        lines=[
            LineItem(line_id="L1", entry_id="E1", line_number=1, account_code="11000", debit_credit=DebitCredit.DEBIT, amount=Decimal("1190.00")),
            LineItem(line_id="L2", entry_id="E1", line_number=2, account_code="40000", debit_credit=DebitCredit.CREDIT, amount=Decimal("1000.00")),
            LineItem(line_id="L3", entry_id="E1", line_number=3, account_code="22100", debit_credit=DebitCredit.CREDIT, amount=Decimal("190.00")),
        ],
    )
    entry2 = JournalEntry(
        entry_id="E2",
        batch_id="B1",
        company_code="1000",
        document_type=DocumentType.KR,
        document_number="KR_001",
        posting_date="2026-02-05",
        document_date="2026-02-05",
        created_at="2026-02-05T10:00:00Z",
        lines=[
            LineItem(line_id="L4", entry_id="E2", line_number=1, account_code="14000", debit_credit=DebitCredit.DEBIT, amount=Decimal("500.00")),
            LineItem(line_id="L5", entry_id="E2", line_number=2, account_code="13000", debit_credit=DebitCredit.DEBIT, amount=Decimal("95.00")),
            LineItem(line_id="L6", entry_id="E2", line_number=3, account_code="20000", debit_credit=DebitCredit.CREDIT, amount=Decimal("595.00")),
        ],
    )

    summary = facade.generate_tax_return([entry1, entry2], jurisdiction=TaxJurisdiction.EU_DE, period_str="2026-02")
    assert summary.output_tax_collected == Decimal("190.00")
    assert summary.input_tax_deductible == Decimal("95.00")
    assert summary.net_tax_payable == Decimal("95.00")
    assert summary.entries_count == 2


def test_tax_applied_to_p2p_invoice_preserves_balance():
    facade = TaxLocalizationEngine(default_jurisdiction=TaxJurisdiction.EU_DE)
    entry = JournalEntry(
        entry_id="KR_TEST",
        batch_id="B1",
        company_code="1000",
        document_type=DocumentType.KR,
        document_number="KR_100",
        posting_date="2026-03-01",
        document_date="2026-03-01",
        created_at="2026-03-01T10:00:00Z",
        lines=[
            LineItem(line_id="L1", entry_id="KR_TEST", line_number=1, account_code="64000", debit_credit=DebitCredit.DEBIT, amount=Decimal("1000.00")),
            LineItem(line_id="L2", entry_id="KR_TEST", line_number=2, account_code="20000", debit_credit=DebitCredit.CREDIT, amount=Decimal("1000.00")),
        ],
    )
    updated = facade.apply_tax_to_entry(entry, jurisdiction=TaxJurisdiction.EU_DE, is_purchase=True)
    assert updated.is_balanced is True
    assert updated.total_debits == Decimal("1190.00")
    assert updated.total_credits == Decimal("1190.00")

    verif = InvariantVerifier.verify_entry(updated)
    assert len(verif) == 0
