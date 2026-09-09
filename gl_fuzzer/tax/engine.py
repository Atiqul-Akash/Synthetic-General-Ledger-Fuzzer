"""Master Tax Localization Engine facade coordinating US, EU, and Withholding sub-engines."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
import uuid

from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
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


class TaxLocalizationEngine:
    """Master facade for global enterprise tax calculations and periodic returns."""

    def __init__(
        self,
        default_jurisdiction: TaxJurisdiction = TaxJurisdiction.GLOBAL,
        default_us_state: str = "CA",
        default_eu_country: str = "DE",
    ):
        self.default_jurisdiction = default_jurisdiction
        self.us_engine = USSalesTaxEngine(default_state=default_us_state)
        self.eu_engine = EUVATEngine(home_country=default_eu_country)
        self.wht_engine = WithholdingTaxEngine()

    def get_available_jurisdictions(self) -> List[TaxJurisdiction]:
        """Returns all supported tax jurisdictions."""
        return list(TaxJurisdiction)

    def calculate_tax(
        self,
        base_amount: Decimal,
        jurisdiction: Optional[TaxJurisdiction] = None,
        is_purchase: bool = False,
        is_cross_border: bool = False,
        state_code: Optional[str] = None,
        country: Optional[str] = None,
        exemption: TaxExemptionReason = TaxExemptionReason.NONE,
    ) -> TaxCalculationResult:
        """Calculates tax for a specified jurisdiction."""
        jur = jurisdiction or self.default_jurisdiction

        if jur in (
            TaxJurisdiction.US_NATIONAL,
            TaxJurisdiction.US_CA,
            TaxJurisdiction.US_TX,
            TaxJurisdiction.US_NY,
            TaxJurisdiction.US_WA,
            TaxJurisdiction.US_FL,
            TaxJurisdiction.US_IL,
        ):
            st = state_code or jur.value.replace("US_", "")
            if len(st) != 2:
                st = "CA"
            if is_cross_border and is_purchase:
                return self.us_engine.calculate_use_tax_accrual(base_amount, state_code=st)
            return self.us_engine.calculate_sales_tax(base_amount, state_code=st, exemption=exemption, is_purchase=is_purchase)

        elif jur in (
            TaxJurisdiction.EU_DE,
            TaxJurisdiction.EU_FR,
            TaxJurisdiction.EU_IT,
            TaxJurisdiction.EU_ES,
            TaxJurisdiction.EU_NL,
            TaxJurisdiction.UK,
        ):
            c = country or jur.value.replace("EU_", "")
            if c == "UK":
                c = "GB"
            if is_cross_border:
                # Intra-community reverse charge
                seller_c = "FR" if c != "FR" else "DE"
                return self.eu_engine.calculate_reverse_charge(base_amount, buyer_country=c, seller_country=seller_c)
            return self.eu_engine.calculate_domestic_vat(base_amount, country=c, is_purchase=is_purchase)

        else:
            # GLOBAL benchmark: flat 6% standard tax
            rate = Decimal("0.0600")
            tax_amt = (base_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            mwskz = "V1" if is_purchase else "A1"
            tax_code = TaxCode(
                code=mwskz,
                rate=rate,
                name="Global Standard Sales/Purchase Tax (6%)",
                account_input="13000",
                account_output="22000",
                is_recoverable=is_purchase,
                is_reverse_charge=False,
            )
            tax_lines = []
            if tax_amt > Decimal("0.00"):
                line_id = f"TAX_GL_{uuid.uuid4().hex[:8].upper()}"
                if is_purchase:
                    tax_lines.append(
                        LineItem(
                            line_id=line_id,
                            entry_id="",
                            line_number=99,
                            account_code="13000",
                            account_name="Input Tax / VAT Receivable",
                            debit_credit=DebitCredit.DEBIT,
                            amount=tax_amt,
                            posting_key="40",
                            tax_code=mwskz,
                            line_text="Global Input Tax (6%)",
                        )
                    )
                else:
                    tax_lines.append(
                        LineItem(
                            line_id=line_id,
                            entry_id="",
                            line_number=99,
                            account_code="22000",
                            account_name="Sales Tax Payable",
                            debit_credit=DebitCredit.CREDIT,
                            amount=tax_amt,
                            posting_key="50",
                            tax_code=mwskz,
                            line_text="Global Output Tax (6%)",
                        )
                    )
            return TaxCalculationResult(
                base_amount=base_amount,
                tax_code=tax_code,
                tax_amount=tax_amt,
                total_with_tax=base_amount + tax_amt,
                jurisdiction=TaxJurisdiction.GLOBAL,
                is_reverse_charge=False,
                tax_line_items=tax_lines,
            )

    def apply_tax_to_entry(
        self,
        entry: JournalEntry,
        jurisdiction: Optional[TaxJurisdiction] = None,
        is_purchase: bool = False,
        state_code: Optional[str] = None,
        country: Optional[str] = None,
        is_cross_border: bool = False,
    ) -> JournalEntry:
        """Applies tax calculation to a journal entry, attaching legs and updating balances."""
        if not entry.lines:
            return entry

        # Identify base amount from revenue or expense leg
        base_line = None
        reconciliation_line = None

        for line in entry.lines:
            if is_purchase:
                # Purchase: Expense/Inventory is DEBIT, AP is CREDIT
                if line.debit_credit == DebitCredit.DEBIT and not line.account_code.startswith("13"):
                    base_line = line
                elif line.debit_credit == DebitCredit.CREDIT and line.account_code.startswith("20"):
                    reconciliation_line = line
            else:
                # Sale: AR is DEBIT, Revenue is CREDIT
                if line.debit_credit == DebitCredit.CREDIT and line.account_code.startswith("4"):
                    base_line = line
                elif line.debit_credit == DebitCredit.DEBIT and line.account_code.startswith("11"):
                    reconciliation_line = line

        if base_line is None or reconciliation_line is None:
            return entry


        calc = self.calculate_tax(
            base_amount=base_line.amount,
            jurisdiction=jurisdiction,
            is_purchase=is_purchase,
            is_cross_border=is_cross_border,
            state_code=state_code,
            country=country,
        )

        if not calc.tax_line_items:
            return entry

        if calc.is_reverse_charge:
            # Reverse charge wash legs: Dr Input VAT / Cr Output VAT
            # AP / AR amount remains unchanged because buyer self-assesses
            for t_line in calc.tax_line_items:
                t_line.entry_id = entry.entry_id
                t_line.line_number = len(entry.lines) + 1
                entry.lines.append(t_line)
        else:
            # Standard tax: Increase reconciliation leg (AR/AP) by tax_amount
            for t_line in calc.tax_line_items:
                t_line.entry_id = entry.entry_id
                t_line.line_number = len(entry.lines) + 1
                entry.lines.append(t_line)

            if reconciliation_line is not None:
                new_total = (reconciliation_line.amount + calc.tax_amount).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                reconciliation_line.amount = new_total
                if reconciliation_line.amount_local is not None:
                    reconciliation_line.amount_local = new_total
                if reconciliation_line.amount_group is not None:
                    reconciliation_line.amount_group = new_total

        return entry

    def generate_tax_return(
        self,
        entries: List[JournalEntry],
        jurisdiction: TaxJurisdiction,
        period_str: str,
    ) -> TaxReturnSummary:
        """Generates a periodic tax reconciliation return across a collection of journal entries."""
        taxable_sales = Decimal("0.00")
        exempt_sales = Decimal("0.00")
        output_tax = Decimal("0.00")
        taxable_purchases = Decimal("0.00")
        input_tax = Decimal("0.00")
        count = 0

        for entry in entries:
            has_tax = False
            for line in entry.lines:
                # Output Tax collected (Credits to 22000, 22100)
                if line.debit_credit == DebitCredit.CREDIT and line.account_code in ("22000", "22100"):
                    output_tax += line.amount
                    has_tax = True
                # Input Tax deductible (Debits to 13000, 13100)
                elif line.debit_credit == DebitCredit.DEBIT and line.account_code in ("13000", "13100"):
                    input_tax += line.amount
                    has_tax = True
                # Sales revenue (Credits to 4xxxx)
                elif line.debit_credit == DebitCredit.CREDIT and line.account_code.startswith("4"):
                    taxable_sales += line.amount
                # Purchases (Debits to 14xxx, 5xxxx, 6xxxx)
                elif line.debit_credit == DebitCredit.DEBIT and (
                    line.account_code.startswith("14") or line.account_code.startswith("5") or line.account_code.startswith("6")
                ):
                    taxable_purchases += line.amount

            if has_tax:
                count += 1

        net_payable = (output_tax - input_tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return TaxReturnSummary(
            jurisdiction=jurisdiction,
            period=period_str,
            taxable_sales=taxable_sales.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            exempt_sales=exempt_sales.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            output_tax_collected=output_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            taxable_purchases=taxable_purchases.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            input_tax_deductible=input_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            net_tax_payable=net_payable,
            entries_count=count,
        )
