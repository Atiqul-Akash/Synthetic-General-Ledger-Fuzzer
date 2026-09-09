"""US Sales and Use Tax localization engine with state economic nexus matrices."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple
import uuid

from gl_fuzzer.models.journal import DebitCredit, LineItem
from gl_fuzzer.tax.models import (
    TaxCalculationResult,
    TaxCode,
    TaxExemptionReason,
    TaxJurisdiction,
)


class USSalesTaxEngine:
    """US state-by-state economic nexus and sales/use tax engine."""

    # 50 States + DC baseline + average local sales tax rates (2026 combined benchmarks)
    STATE_RATES: Dict[str, Decimal] = {
        "AL": Decimal("0.0924"), "AK": Decimal("0.0176"), "AZ": Decimal("0.0840"),
        "AR": Decimal("0.0947"), "CA": Decimal("0.0868"), "CO": Decimal("0.0772"),
        "CT": Decimal("0.0635"), "DE": Decimal("0.0000"), "DC": Decimal("0.0600"),
        "FL": Decimal("0.0705"), "GA": Decimal("0.0732"), "HI": Decimal("0.0444"),
        "ID": Decimal("0.0602"), "IL": Decimal("0.0881"), "IN": Decimal("0.0700"),
        "IA": Decimal("0.0694"), "KS": Decimal("0.0868"), "KY": Decimal("0.0600"),
        "LA": Decimal("0.0955"), "ME": Decimal("0.0550"), "MD": Decimal("0.0600"),
        "MA": Decimal("0.0625"), "MI": Decimal("0.0600"), "MN": Decimal("0.0749"),
        "MS": Decimal("0.0707"), "MO": Decimal("0.0829"), "MT": Decimal("0.0000"),
        "NE": Decimal("0.0694"), "NV": Decimal("0.0823"), "NH": Decimal("0.0000"),
        "NJ": Decimal("0.0663"), "NM": Decimal("0.0772"), "NY": Decimal("0.0852"),
        "NC": Decimal("0.0698"), "ND": Decimal("0.0696"), "OH": Decimal("0.0725"),
        "OK": Decimal("0.0898"), "OR": Decimal("0.0000"), "PA": Decimal("0.0600"),
        "RI": Decimal("0.0700"), "SC": Decimal("0.0744"), "SD": Decimal("0.0640"),
        "TN": Decimal("0.0955"), "TX": Decimal("0.0825"), "UT": Decimal("0.0719"),
        "VT": Decimal("0.0624"), "VA": Decimal("0.0575"), "WA": Decimal("0.0938"),
        "WV": Decimal("0.0655"), "WI": Decimal("0.0543"), "WY": Decimal("0.0536"),
    }

    # Economic nexus thresholds: annual revenue $100k or 200 transactions
    ECONOMIC_NEXUS_THRESHOLD_USD = Decimal("100000.00")

    def __init__(self, default_state: str = "CA"):
        self.default_state = default_state.upper()

    def get_rate_for_state(self, state_code: str) -> Decimal:
        """Returns the effective combined state and local sales tax rate."""
        st = state_code.upper().strip()
        return self.STATE_RATES.get(st, self.STATE_RATES.get(self.default_state, Decimal("0.0600")))

    def calculate_sales_tax(
        self,
        base_amount: Decimal,
        state_code: Optional[str] = None,
        exemption: TaxExemptionReason = TaxExemptionReason.NONE,
        is_purchase: bool = False,
    ) -> TaxCalculationResult:
        """Calculates US sales tax and returns formatted tax legs."""
        st = (state_code or self.default_state).upper()
        rate = self.get_rate_for_state(st)

        if exemption != TaxExemptionReason.NONE:
            rate = Decimal("0.0000")

        tax_amt = (base_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_amt = base_amount + tax_amt

        tax_code = TaxCode(
            code=f"US_{st}",
            rate=rate,
            name=f"US Sales Tax - {st}" + (f" ({exemption.value})" if exemption != TaxExemptionReason.NONE else ""),
            account_input="13000",
            account_output="22000",
            is_recoverable=is_purchase,
            is_reverse_charge=False,
        )

        # Build tax line item
        tax_lines = []
        if tax_amt > Decimal("0.00"):
            line_id = f"TAX_US_{uuid.uuid4().hex[:8].upper()}"
            if is_purchase:
                # Purchase (P2P): Debit Input Tax / Sales Tax Expense
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
                        tax_jurisdiction=st,
                        line_text=f"US Sales Tax ({st})",
                    )
                )
            else:
                # Sale (O2C): Credit Sales Tax Payable
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
                        tax_code=tax_code.code,
                        tax_jurisdiction=st,
                        line_text=f"US Sales Tax Payable ({st})",
                    )
                )

        jurisdiction_map = {
            "CA": TaxJurisdiction.US_CA,
            "TX": TaxJurisdiction.US_TX,
            "NY": TaxJurisdiction.US_NY,
            "WA": TaxJurisdiction.US_WA,
            "FL": TaxJurisdiction.US_FL,
            "IL": TaxJurisdiction.US_IL,
        }
        jurisdiction = jurisdiction_map.get(st, TaxJurisdiction.US_NATIONAL)

        return TaxCalculationResult(
            base_amount=base_amount,
            tax_code=tax_code,
            tax_amount=tax_amt,
            total_with_tax=total_amt,
            jurisdiction=jurisdiction,
            is_reverse_charge=False,
            tax_line_items=tax_lines,
        )

    def calculate_use_tax_accrual(
        self,
        base_amount: Decimal,
        state_code: Optional[str] = None,
    ) -> TaxCalculationResult:
        """Calculates out-of-state vendor purchase Use Tax accrual.
        
        Generates balanced self-assessed double-entry wash legs:
        Dr Use Tax Receivable (13100) / Cr Use Tax Payable (22300).
        """
        st = (state_code or self.default_state).upper()
        rate = self.get_rate_for_state(st)
        tax_amt = (base_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        tax_code = TaxCode(
            code=f"USE_{st}",
            rate=rate,
            name=f"US Use Tax Accrual - {st}",
            account_input="13100",
            account_output="22300",
            is_recoverable=True,
            is_reverse_charge=True,
        )

        tax_lines = []
        if tax_amt > Decimal("0.00"):
            uid = uuid.uuid4().hex[:8].upper()
            # Debit Use Tax Receivable
            tax_lines.append(
                LineItem(
                    line_id=f"USE_DR_{uid}",
                    entry_id="",
                    line_number=98,
                    account_code="13100",
                    account_name="Use Tax Receivable",
                    debit_credit=DebitCredit.DEBIT,
                    amount=tax_amt,
                    posting_key="40",
                    tax_code=tax_code.code,
                    tax_jurisdiction=st,
                    line_text=f"Use Tax Accrual Debit ({st})",
                )
            )
            # Credit Use Tax Payable
            tax_lines.append(
                LineItem(
                    line_id=f"USE_CR_{uid}",
                    entry_id="",
                    line_number=99,
                    account_code="22300",
                    account_name="Use Tax Payable",
                    debit_credit=DebitCredit.CREDIT,
                    amount=tax_amt,
                    posting_key="50",
                    tax_code=tax_code.code,
                    tax_jurisdiction=st,
                    line_text=f"Use Tax Accrual Credit ({st})",
                )
            )

        return TaxCalculationResult(
            base_amount=base_amount,
            tax_code=tax_code,
            tax_amount=tax_amt,
            total_with_tax=base_amount,  # Wash legs don't distort net invoice total
            jurisdiction=TaxJurisdiction.US_NATIONAL,
            is_reverse_charge=True,
            tax_line_items=tax_lines,
        )
