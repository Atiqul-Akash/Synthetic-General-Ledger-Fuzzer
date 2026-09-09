"""EU and UK VAT localization engine with B2B Reverse Charge mechanism and Intrastat reporting."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple
import uuid

from gl_fuzzer.models.journal import DebitCredit, LineItem
from gl_fuzzer.tax.models import (
    TaxCalculationResult,
    TaxCode,
    TaxJurisdiction,
)


class EUVATEngine:
    """European Union and UK VAT localization engine."""

    # Standard and reduced VAT rates by country
    VAT_RATES: Dict[str, Dict[str, Decimal]] = {
        "DE": {"standard": Decimal("0.19"), "reduced": Decimal("0.07"), "zero": Decimal("0.00")},
        "FR": {"standard": Decimal("0.20"), "reduced": Decimal("0.055"), "zero": Decimal("0.00")},
        "IT": {"standard": Decimal("0.22"), "reduced": Decimal("0.10"), "zero": Decimal("0.00")},
        "ES": {"standard": Decimal("0.21"), "reduced": Decimal("0.10"), "zero": Decimal("0.00")},
        "NL": {"standard": Decimal("0.21"), "reduced": Decimal("0.09"), "zero": Decimal("0.00")},
        "GB": {"standard": Decimal("0.20"), "reduced": Decimal("0.05"), "zero": Decimal("0.00")},
        "UK": {"standard": Decimal("0.20"), "reduced": Decimal("0.05"), "zero": Decimal("0.00")},
    }

    def __init__(self, home_country: str = "DE"):
        self.home_country = home_country.upper()

    def get_standard_rate(self, country: Optional[str] = None) -> Decimal:
        c = (country or self.home_country).upper()
        rates = self.VAT_RATES.get(c, self.VAT_RATES["DE"])
        return rates["standard"]

    def calculate_domestic_vat(
        self,
        base_amount: Decimal,
        country: Optional[str] = None,
        rate_type: str = "standard",
        is_purchase: bool = False,
    ) -> TaxCalculationResult:
        """Calculates domestic VAT with MWSKZ code V1 (input) or A1 (output)."""
        c = (country or self.home_country).upper()
        rates = self.VAT_RATES.get(c, self.VAT_RATES["DE"])
        rate = rates.get(rate_type, rates["standard"])

        tax_amt = (base_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_amt = base_amount + tax_amt
        mwskz = "V1" if is_purchase else "A1"

        tax_code = TaxCode(
            code=mwskz,
            rate=rate,
            name=f"{c} Domestic VAT ({rate_type.capitalize()} {int(rate * 100)}%)",
            account_input="13000",
            account_output="22100",
            is_recoverable=is_purchase,
            is_reverse_charge=False,
        )

        tax_lines = []
        if tax_amt > Decimal("0.00"):
            line_id = f"VAT_{c}_{uuid.uuid4().hex[:8].upper()}"
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
                        tax_code=tax_code.code,
                        tax_jurisdiction=f"EU_{c}",
                        line_text=f"Domestic Input VAT {c} {int(rate * 100)}%",
                    )
                )
            else:
                tax_lines.append(
                    LineItem(
                        line_id=line_id,
                        entry_id="",
                        line_number=99,
                        account_code="22100",
                        account_name="Output Tax / VAT Payable",
                        debit_credit=DebitCredit.CREDIT,
                        amount=tax_amt,
                        posting_key="50",
                        tax_code=tax_code.code,
                        tax_jurisdiction=f"EU_{c}",
                        line_text=f"Domestic Output VAT {c} {int(rate * 100)}%",
                    )
                )

        jurisdiction_map = {
            "DE": TaxJurisdiction.EU_DE,
            "FR": TaxJurisdiction.EU_FR,
            "IT": TaxJurisdiction.EU_IT,
            "ES": TaxJurisdiction.EU_ES,
            "NL": TaxJurisdiction.EU_NL,
            "GB": TaxJurisdiction.UK,
            "UK": TaxJurisdiction.UK,
        }
        jurisdiction = jurisdiction_map.get(c, TaxJurisdiction.EU_DE)

        return TaxCalculationResult(
            base_amount=base_amount,
            tax_code=tax_code,
            tax_amount=tax_amt,
            total_with_tax=total_amt,
            jurisdiction=jurisdiction,
            is_reverse_charge=False,
            tax_line_items=tax_lines,
        )

    def calculate_reverse_charge(
        self,
        base_amount: Decimal,
        buyer_country: str = "DE",
        seller_country: str = "FR",
    ) -> TaxCalculationResult:
        """Calculates B2B cross-border reverse charge under EU VAT Directive Article 194.
        
        Self-assesses both Input VAT and Output VAT simultaneously:
        Dr Input VAT Recoverable (13000) / Cr Output VAT Payable (22100).
        Net cash impact is exactly 0.00 while maintaining strict double-entry balance.
        """
        buyer_c = buyer_country.upper()
        rate = self.get_standard_rate(buyer_c)
        tax_amt = (base_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        tax_code = TaxCode(
            code="RC",
            rate=rate,
            name=f"EU Cross-Border Reverse Charge ({seller_country} -> {buyer_country})",
            account_input="13000",
            account_output="22100",
            is_recoverable=True,
            is_reverse_charge=True,
        )

        tax_lines = []
        if tax_amt > Decimal("0.00"):
            uid = uuid.uuid4().hex[:8].upper()
            # 1. Debit Input VAT Recoverable
            tax_lines.append(
                LineItem(
                    line_id=f"RC_DR_{uid}",
                    entry_id="",
                    line_number=98,
                    account_code="13000",
                    account_name="Input Tax / VAT Receivable",
                    debit_credit=DebitCredit.DEBIT,
                    amount=tax_amt,
                    posting_key="40",
                    tax_code="RC",
                    tax_jurisdiction=f"EU_{buyer_c}",
                    line_text=f"Reverse Charge Input VAT ({buyer_c})",
                )
            )
            # 2. Credit Output VAT Self-Assessed
            tax_lines.append(
                LineItem(
                    line_id=f"RC_CR_{uid}",
                    entry_id="",
                    line_number=99,
                    account_code="22100",
                    account_name="Output Tax / VAT Payable",
                    debit_credit=DebitCredit.CREDIT,
                    amount=tax_amt,
                    posting_key="50",
                    tax_code="RC",
                    tax_jurisdiction=f"EU_{buyer_c}",
                    line_text=f"Reverse Charge Output VAT Self-Assessment ({buyer_c})",
                )
            )

        jurisdiction_map = {
            "DE": TaxJurisdiction.EU_DE,
            "FR": TaxJurisdiction.EU_FR,
            "IT": TaxJurisdiction.EU_IT,
            "ES": TaxJurisdiction.EU_ES,
            "NL": TaxJurisdiction.EU_NL,
            "GB": TaxJurisdiction.UK,
            "UK": TaxJurisdiction.UK,
        }
        jurisdiction = jurisdiction_map.get(buyer_c, TaxJurisdiction.EU_DE)

        return TaxCalculationResult(
            base_amount=base_amount,
            tax_code=tax_code,
            tax_amount=tax_amt,
            total_with_tax=base_amount,  # Wash legs don't distort net payable to vendor
            jurisdiction=jurisdiction,
            is_reverse_charge=True,
            tax_line_items=tax_lines,
        )
