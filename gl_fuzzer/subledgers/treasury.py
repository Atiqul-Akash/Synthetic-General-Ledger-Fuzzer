"""Treasury & Corporate Debt Facilities Subledger (IFRS 9 / ASC 835)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import uuid
from pydantic import BaseModel, Field

from gl_fuzzer.models.journal import (
    DebitCredit,
    DocumentType,
    JournalEntry,
    LineItem,
)


class FacilityType(str, Enum):
    TERM_LOAN = "TERM_LOAN"
    REVOLVING_CREDIT = "REVOLVING_CREDIT"
    CORPORATE_BOND = "CORPORATE_BOND"
    COMMERCIAL_PAPER = "COMMERCIAL_PAPER"


class CouponType(str, Enum):
    FIXED = "FIXED"
    FLOATING = "FLOATING"


class Seniority(str, Enum):
    SENIOR_SECURED = "SENIOR_SECURED"
    SENIOR_UNSECURED = "SENIOR_UNSECURED"
    SUBORDINATED = "SUBORDINATED"
    MEZZANINE = "MEZZANINE"


class BenchmarkRate(str, Enum):
    SOFR = "SOFR"
    EURIBOR = "EURIBOR"
    SONIA = "SONIA"
    TONA = "TONA"


class DebtFacility(BaseModel):
    """Corporate debt facility or bond issuance complying with IFRS 9 amortized cost."""
    facility_id: str = Field(..., description="Unique Facility Identifier (e.g. 'DEBT-2026-01')")
    facility_type: FacilityType = Field(default=FacilityType.CORPORATE_BOND)
    principal: Decimal = Field(..., description="Face value / principal borrowed")
    issuance_price: Decimal = Field(..., description="Net proceeds received at issue")
    coupon_rate: Decimal = Field(..., description="Annual contractual coupon rate (e.g. 0.05 for 5%)")
    coupon_type: CouponType = Field(default=CouponType.FIXED)
    benchmark: Optional[BenchmarkRate] = None
    spread_bps: int = Field(default=0, description="Spread in basis points over benchmark")
    seniority: Seniority = Field(default=Seniority.SENIOR_UNSECURED)
    issuance_date: str = Field(..., description="YYYY-MM-DD")
    maturity_date: str = Field(..., description="YYYY-MM-DD")
    tenor_months: int = Field(..., description="Original maturity in months")
    effective_interest_rate: Decimal = Field(..., description="Annual Effective Interest Rate (EIR)")
    unamortized_discount: Decimal = Field(default=Decimal("0.00"), description="Positive indicates discount, negative indicates premium")
    is_active: bool = Field(default=True)

    @property
    def carrying_value(self) -> Decimal:
        """Carrying value under IFRS 9 amortized cost = Principal - Discount (+ Premium)."""
        cv = self.principal - self.unamortized_discount
        return cv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


CorporateBond = DebtFacility


class DebtCovenantThresholds(BaseModel):
    """Financial covenants mandated in corporate debt indentures."""
    max_leverage_ratio: Decimal = Field(default=Decimal("4.50"), description="Max Debt / EBITDA")
    min_interest_coverage: Decimal = Field(default=Decimal("3.00"), description="Min EBIT / Interest")
    max_debt_to_equity: Decimal = Field(default=Decimal("2.00"), description="Max Liabilities / Equity")


class CovenantCheckResult(BaseModel):
    """Result of continuous debt covenant monitoring."""
    leverage_ratio: Decimal
    interest_coverage: Decimal
    debt_to_equity: Decimal
    is_breached: bool
    breach_reasons: List[str] = Field(default_factory=list)


class InterestRateSwap(BaseModel):
    """Interest rate swap instrument for IAS 39 / IFRS 9 hedge accounting."""
    swap_id: str
    notional: Decimal
    fixed_rate: Decimal
    floating_benchmark: BenchmarkRate = BenchmarkRate.SOFR
    spread_bps: int = 0
    maturity_months: int = 60
    is_cash_flow_hedge: bool = True
    current_mtm_value: Decimal = Decimal("0.00")
    hedged_facility_id: Optional[str] = None


class TreasurySubledger:
    """Stateful subledger for debt facilities, EIR amortization, and derivatives."""

    def __init__(self, company_code: str = "1000"):
        self.company_code = company_code
        self.facilities: Dict[str, DebtFacility] = {}
        self.swaps: Dict[str, InterestRateSwap] = {}
        self.covenants = DebtCovenantThresholds()
        self.voucher_sequence = 1

    def _next_doc_number(self, prefix: str = "TR") -> str:
        doc_num = f"{prefix}{self.voucher_sequence:08d}"
        self.voucher_sequence += 1
        return doc_num

    def issue_facility(
        self,
        facility_id: str,
        facility_type: FacilityType,
        principal: Decimal,
        issuance_price: Decimal,
        coupon_rate: Decimal,
        tenor_months: int,
        issuance_date: str,
        maturity_date: str,
        effective_interest_rate: Optional[Decimal] = None,
        coupon_type: CouponType = CouponType.FIXED,
        benchmark: Optional[BenchmarkRate] = None,
        spread_bps: int = 0,
        seniority: Seniority = Seniority.SENIOR_UNSECURED,
    ) -> Tuple[DebtFacility, JournalEntry]:
        """Issues a debt facility / corporate bond and books initial proceeds & discount/premium."""
        principal = Decimal(str(principal)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        issuance_price = Decimal(str(issuance_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        coupon_rate = Decimal(str(coupon_rate))

        discount = principal - issuance_price  # Positive = discount, Negative = premium

        # Approximate or specified EIR
        if effective_interest_rate is None:
            # Approximate EIR = coupon + (discount / tenor_years) / ((principal + price) / 2)
            tenor_years = Decimal(str(tenor_months)) / Decimal("12.0")
            avg_book = (principal + issuance_price) / Decimal("2.0")
            annual_amort = discount / tenor_years if tenor_years > 0 else Decimal("0.00")
            annual_coupon = principal * coupon_rate
            eir = ((annual_coupon + annual_amort) / avg_book).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        else:
            eir = Decimal(str(effective_interest_rate))

        facility = DebtFacility(
            facility_id=facility_id,
            facility_type=facility_type,
            principal=principal,
            issuance_price=issuance_price,
            coupon_rate=coupon_rate,
            coupon_type=coupon_type,
            benchmark=benchmark,
            spread_bps=spread_bps,
            seniority=seniority,
            issuance_date=issuance_date,
            maturity_date=maturity_date,
            tenor_months=tenor_months,
            effective_interest_rate=eir,
            unamortized_discount=discount,
        )
        self.facilities[facility_id] = facility

        doc_num = self._next_doc_number("TR")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        lines: List[LineItem] = []
        line_num = 1

        # 1. Cash received (Debit)
        lines.append(
            LineItem(
                line_id=f"{entry_id}-{line_num:03d}",
                entry_id=entry_id,
                line_number=line_num,
                account_code="10100",
                account_name="Operating Cash & Bank",
                debit_credit=DebitCredit.DEBIT,
                amount=issuance_price,
                line_text=f"Proceeds from debt issuance: {facility_id}",
            )
        )
        line_num += 1

        # 2. Discount (Debit) or Premium (Credit)
        if discount > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="25200",
                    account_name="Unamortized Debt Discount/Premium",
                    debit_credit=DebitCredit.DEBIT,
                    amount=discount,
                    line_text=f"Debt discount on issuance: {facility_id}",
                )
            )
            line_num += 1

        # 3. Principal liability (Credit)
        lines.append(
            LineItem(
                line_id=f"{entry_id}-{line_num:03d}",
                entry_id=entry_id,
                line_number=line_num,
                account_code="25100",
                account_name="Senior Debt & Corporate Bonds Payable",
                debit_credit=DebitCredit.CREDIT,
                amount=principal,
                line_text=f"Par debt obligation: {facility_id}",
            )
        )
        line_num += 1

        # If premium (discount < 0), add credit to 25200
        if discount < Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="25200",
                    account_name="Unamortized Debt Discount/Premium",
                    debit_credit=DebitCredit.CREDIT,
                    amount=abs(discount),
                    line_text=f"Debt premium on issuance: {facility_id}",
                )
            )

        dt_parts = issuance_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_TR_{issuance_date.replace('-', '')}",
            company_code=self.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.TR,
            document_number=doc_num,
            posting_date=issuance_date,
            document_date=issuance_date,
            created_at=now_utc,
            header_text=f"Debt Issuance: {facility_type.value} {facility_id}",
            business_cycle="R2R",
            lines=lines,
        )
        return facility, entry

    def amortize_monthly_interest(
        self,
        facility_id: str,
        period_date: str,
    ) -> Optional[JournalEntry]:
        """Calculates monthly EIR interest expense and discount/premium amortization."""
        facility = self.facilities.get(facility_id)
        if not facility or not facility.is_active:
            return None

        carrying_val = facility.carrying_value
        monthly_eir = facility.effective_interest_rate / Decimal("12.0")
        monthly_coupon_rate = facility.coupon_rate / Decimal("12.0")

        # IFRS 9 Amortized Cost:
        interest_expense = (carrying_val * monthly_eir).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cash_coupon = (facility.principal * monthly_coupon_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amortization = interest_expense - cash_coupon  # Positive: reduces discount; Negative: reduces premium

        # Cap amortization to remaining balance so it never flips or overshoots past par at maturity
        if facility.unamortized_discount > Decimal("0.00"):
            amortization = min(amortization, facility.unamortized_discount)
        elif facility.unamortized_discount < Decimal("0.00"):
            amortization = max(amortization, facility.unamortized_discount)

        # Align interest expense so debits and credits remain strictly balanced
        interest_expense = cash_coupon + amortization

        # Update facility state
        facility.unamortized_discount = (facility.unamortized_discount - amortization).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        doc_num = self._next_doc_number("EI")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        lines: List[LineItem] = []
        line_num = 1

        # 1. Dr Interest Expense (P&L)
        lines.append(
            LineItem(
                line_id=f"{entry_id}-{line_num:03d}",
                entry_id=entry_id,
                line_number=line_num,
                account_code="68000",
                account_name="Interest Expense on Corporate Debt",
                debit_credit=DebitCredit.DEBIT,
                amount=interest_expense,
                line_text=f"Monthly EIR interest expense: {facility_id}",
            )
        )
        line_num += 1

        # 2. Cr Cash (Coupon paid) - only if non-zero (avoids $0.00 cash lines on zero-coupon debt)
        if cash_coupon > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="10100",
                    account_name="Operating Cash & Bank",
                    debit_credit=DebitCredit.CREDIT,
                    amount=cash_coupon,
                    line_text=f"Monthly coupon disbursement: {facility_id}",
                )
            )
            line_num += 1

        # 3. Balancing Leg: Discount Amortization (Credit) or Premium Amortization (Debit)
        if amortization > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="25200",
                    account_name="Unamortized Debt Discount/Premium",
                    debit_credit=DebitCredit.CREDIT,
                    amount=amortization,
                    line_text=f"Discount accretion: {facility_id}",
                )
            )
        elif amortization < Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="25200",
                    account_name="Unamortized Debt Discount/Premium",
                    debit_credit=DebitCredit.DEBIT,
                    amount=abs(amortization),
                    line_text=f"Premium amortization: {facility_id}",
                )
            )

        dt_parts = period_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_EIR_{period_date.replace('-', '')}",
            company_code=self.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.TR,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"EIR Interest Amortization: {facility_id}",
            business_cycle="R2R",
            lines=lines,
        )
        return entry

    def register_interest_rate_swap(
        self,
        swap_id: str,
        notional: Decimal,
        fixed_rate: Decimal,
        maturity_months: int = 60,
        is_cash_flow_hedge: bool = True,
        hedged_facility_id: Optional[str] = None,
    ) -> InterestRateSwap:
        """Registers an IRS hedging instrument."""
        swap = InterestRateSwap(
            swap_id=swap_id,
            notional=Decimal(str(notional)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            fixed_rate=Decimal(str(fixed_rate)),
            maturity_months=maturity_months,
            is_cash_flow_hedge=is_cash_flow_hedge,
            hedged_facility_id=hedged_facility_id,
        )
        self.swaps[swap_id] = swap
        return swap

    def mark_to_market_swap(
        self,
        swap_id: str,
        new_market_value: Decimal,
        period_date: str,
        effectiveness_ratio: Decimal = Decimal("1.00"),
    ) -> Optional[JournalEntry]:
        """MTM accounting for interest rate swap under IAS 39 / IFRS 9."""
        swap = self.swaps.get(swap_id)
        if not swap:
            return None

        target_mtm = Decimal(str(new_market_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        delta_mtm = target_mtm - swap.current_mtm_value
        if delta_mtm == Decimal("0.00"):
            return None

        swap.current_mtm_value = target_mtm
        doc_num = self._next_doc_number("HD")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        lines: List[LineItem] = []
        line_num = 1

        # Effective ratio determines OCI vs P&L split for cash flow hedges
        eff = max(Decimal("0.00"), min(Decimal("1.00"), effectiveness_ratio))

        if swap.is_cash_flow_hedge:
            effective_portion = (abs(delta_mtm) * eff).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ineffective_portion = (abs(delta_mtm) - effective_portion).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if delta_mtm > Decimal("0.00"):  # Gain on derivative
                lines.append(
                    LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code="25400",
                        account_name="Derivative Hedging Asset/Liability",
                        debit_credit=DebitCredit.DEBIT,
                        amount=abs(delta_mtm),
                        line_text=f"Gain on swap asset: {swap_id}",
                    )
                )
                line_num += 1
                if effective_portion > Decimal("0.00"):
                    lines.append(
                        LineItem(
                            line_id=f"{entry_id}-{line_num:03d}",
                            entry_id=entry_id,
                            line_number=line_num,
                            account_code="32000",
                            account_name="AOCI - Cash Flow Hedges",
                            debit_credit=DebitCredit.CREDIT,
                            amount=effective_portion,
                            line_text=f"Effective hedge gain to OCI: {swap_id}",
                        )
                    )
                    line_num += 1
                if ineffective_portion > Decimal("0.00"):
                    lines.append(
                        LineItem(
                            line_id=f"{entry_id}-{line_num:03d}",
                            entry_id=entry_id,
                            line_number=line_num,
                            account_code="48100",
                            account_name="Unrealized Gain on Derivative Instruments",
                            debit_credit=DebitCredit.CREDIT,
                            amount=ineffective_portion,
                            line_text=f"Ineffective hedge gain to P&L: {swap_id}",
                        )
                    )
            else:  # Loss on derivative
                if effective_portion > Decimal("0.00"):
                    lines.append(
                        LineItem(
                            line_id=f"{entry_id}-{line_num:03d}",
                            entry_id=entry_id,
                            line_number=line_num,
                            account_code="32000",
                            account_name="AOCI - Cash Flow Hedges",
                            debit_credit=DebitCredit.DEBIT,
                            amount=effective_portion,
                            line_text=f"Effective hedge loss to OCI: {swap_id}",
                        )
                    )
                    line_num += 1
                if ineffective_portion > Decimal("0.00"):
                    lines.append(
                        LineItem(
                            line_id=f"{entry_id}-{line_num:03d}",
                            entry_id=entry_id,
                            line_number=line_num,
                            account_code="68100",
                            account_name="Derivative Ineffectiveness & MTM Loss",
                            debit_credit=DebitCredit.DEBIT,
                            amount=ineffective_portion,
                            line_text=f"Ineffective hedge loss to P&L: {swap_id}",
                        )
                    )
                    line_num += 1
                lines.append(
                    LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code="25400",
                        account_name="Derivative Hedging Liability / MTM",
                        debit_credit=DebitCredit.CREDIT,
                        amount=abs(delta_mtm),
                        line_text=f"Loss on swap liability: {swap_id}",
                    )
                )
        else:
            # Fair Value Hedge: straight through P&L
            if delta_mtm > Decimal("0.00"):
                lines.append(
                    LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code="25400",
                        account_name="Derivative Hedging Asset/Liability",
                        debit_credit=DebitCredit.DEBIT,
                        amount=abs(delta_mtm),
                        line_text=f"FV Derivative asset MTM: {swap_id}",
                    )
                )
                line_num += 1
                lines.append(
                    LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code="48100",
                        account_name="Unrealized Gain on Derivative Instruments",
                        debit_credit=DebitCredit.CREDIT,
                        amount=abs(delta_mtm),
                        line_text=f"FV Hedge MTM gain: {swap_id}",
                    )
                )
            else:
                lines.append(
                    LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code="68100",
                        account_name="Derivative Ineffectiveness & MTM Loss",
                        debit_credit=DebitCredit.DEBIT,
                        amount=abs(delta_mtm),
                        line_text=f"FV Hedge MTM loss: {swap_id}",
                    )
                )
                line_num += 1
                lines.append(
                    LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code="25400",
                        account_name="Derivative Hedging Liability / MTM",
                        debit_credit=DebitCredit.CREDIT,
                        amount=abs(delta_mtm),
                        line_text=f"FV Derivative liability MTM: {swap_id}",
                    )
                )

        dt_parts = period_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_HD_{period_date.replace('-', '')}",
            company_code=self.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.TR,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"Hedge MTM Valuation: {swap_id}",
            business_cycle="R2R",
            lines=lines,
        )
        return entry

    def evaluate_covenants(
        self,
        total_debt: Decimal,
        ebitda: Decimal,
        ebit: Decimal,
        interest_expense: Decimal,
        total_liabilities: Decimal,
        total_equity: Decimal,
    ) -> CovenantCheckResult:
        """Evaluates financial health against contractual debt covenants."""
        total_debt = Decimal(str(total_debt))
        ebitda = Decimal(str(ebitda))
        ebit = Decimal(str(ebit))
        interest_expense = Decimal(str(interest_expense))
        total_liabilities = Decimal(str(total_liabilities))
        total_equity = Decimal(str(total_equity))

        # Ratios - robust handling of edge cases
        if total_debt == Decimal("0.00"):
            lev = Decimal("0.00")
        elif ebitda > Decimal("0.00"):
            lev = (total_debt / ebitda).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            lev = Decimal("99.99")

        if interest_expense > Decimal("0.00"):
            icr = (ebit / interest_expense).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            icr = Decimal("0.00") if ebit <= Decimal("0.00") else Decimal("99.99")

        if total_liabilities == Decimal("0.00"):
            dte = Decimal("0.00")
        elif total_equity > Decimal("0.00"):
            dte = (total_liabilities / total_equity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            dte = Decimal("99.99")

        breaches: List[str] = []
        if lev > self.covenants.max_leverage_ratio:
            breaches.append(f"Leverage Ratio breached: {lev:.2f}x > max {self.covenants.max_leverage_ratio:.2f}x")
        if icr < self.covenants.min_interest_coverage:
            breaches.append(f"Interest Coverage Ratio breached: {icr:.2f}x < min {self.covenants.min_interest_coverage:.2f}x")
        if dte > self.covenants.max_debt_to_equity:
            breaches.append(f"Debt-to-Equity breached: {dte:.2f}x > max {self.covenants.max_debt_to_equity:.2f}x")

        return CovenantCheckResult(
            leverage_ratio=lev,
            interest_coverage=icr,
            debt_to_equity=dte,
            is_breached=len(breaches) > 0,
            breach_reasons=breaches,
        )


# ---------------------------------------------------------------------------
# Calibrated Fraud Anomaly Mutators for Treasury
# ---------------------------------------------------------------------------

class CovenantSuppressionMutator:
    """Fraud Mutator: Artificially reclassifies senior debt to equity to hide covenant breach."""

    @staticmethod
    def mutate(
        subledger: TreasurySubledger,
        facility_id: str,
        suppression_amount: Decimal,
        period_date: str,
    ) -> Optional[JournalEntry]:
        facility = subledger.facilities.get(facility_id)
        if not facility:
            return None

        amt = Decimal(str(suppression_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        doc_num = subledger._next_doc_number("FC")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_FRAUD_COV_{period_date.replace('-', '')}",
            company_code=subledger.company_code,
            document_type=DocumentType.TR,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"FRAUD_COVENANT_SUPPRESSION: {facility_id}",
            business_cycle="R2R",
            is_anomaly=True,
            anomaly_ids=["ANOM_COVENANT_SUPPRESSION_DEBT_RECLASSIFICATION"],
            lines=[
                LineItem(
                    line_id=f"{entry_id}-001",
                    entry_id=entry_id,
                    line_number=1,
                    account_code="25100",
                    account_name="Senior Debt & Corporate Bonds Payable",
                    debit_credit=DebitCredit.DEBIT,
                    amount=amt,
                    line_text=f"Fraudulent debt reclass debit: {facility_id}",
                ),
                LineItem(
                    line_id=f"{entry_id}-002",
                    entry_id=entry_id,
                    line_number=2,
                    account_code="31000",
                    account_name="Additional Paid-in Capital",
                    debit_credit=DebitCredit.CREDIT,
                    amount=amt,
                    line_text=f"Fictitious equity reclass credit: {facility_id}",
                ),
            ],
        )
        return entry


class HedgeIneffectivenessConcealment:
    """Fraud Mutator: Routes 100% of derivative losses to OCI, concealing P&L damage."""

    @staticmethod
    def mutate(
        subledger: TreasurySubledger,
        swap_id: str,
        loss_amount: Decimal,
        period_date: str,
    ) -> Optional[JournalEntry]:
        amt = Decimal(str(loss_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        doc_num = subledger._next_doc_number("FI")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_FRAUD_HEDGE_{period_date.replace('-', '')}",
            company_code=subledger.company_code,
            document_type=DocumentType.TR,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"FRAUD_HEDGE_INEFFECTIVENESS_CONCEALMENT: {swap_id}",
            business_cycle="R2R",
            is_anomaly=True,
            anomaly_ids=["ANOM_HEDGE_INEFFECTIVENESS_CONCEALMENT"],
            lines=[
                LineItem(
                    line_id=f"{entry_id}-001",
                    entry_id=entry_id,
                    line_number=1,
                    account_code="32000",
                    account_name="AOCI - Cash Flow Hedges",
                    debit_credit=DebitCredit.DEBIT,
                    amount=amt,
                    line_text=f"Concealed ineffectiveness booked to OCI: {swap_id}",
                ),
                LineItem(
                    line_id=f"{entry_id}-002",
                    entry_id=entry_id,
                    line_number=2,
                    account_code="25400",
                    account_name="Derivative Hedging Liability / MTM",
                    debit_credit=DebitCredit.CREDIT,
                    amount=amt,
                    line_text=f"Derivative liability credit: {swap_id}",
                ),
            ],
        )
        return entry


class DebtRolloverConcealment:
    """Fraud Mutator: Conceals impending short-term debt maturity to hide liquidity strain."""

    @staticmethod
    def mutate(
        subledger: TreasurySubledger,
        maturing_facility_id: str,
        period_date: str,
    ) -> Optional[JournalEntry]:
        facility = subledger.facilities.get(maturing_facility_id)
        if not facility:
            return None

        # Reclassify from Current to Long-term to deceive working capital audits
        amt = facility.principal
        doc_num = subledger._next_doc_number("FR")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_FRAUD_ROLL_{period_date.replace('-', '')}",
            company_code=subledger.company_code,
            document_type=DocumentType.TR,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"FRAUD_DEBT_ROLLOVER_CONCEALMENT: {maturing_facility_id}",
            business_cycle="R2R",
            is_anomaly=True,
            anomaly_ids=["ANOM_DEBT_ROLLOVER_CONCEALMENT"],
            lines=[
                LineItem(
                    line_id=f"{entry_id}-001",
                    entry_id=entry_id,
                    line_number=1,
                    account_code="25000",
                    account_name="Current Portion of Long Term Debt",
                    debit_credit=DebitCredit.DEBIT,
                    amount=amt,
                    line_text=f"Reverse current debt liability: {maturing_facility_id}",
                ),
                LineItem(
                    line_id=f"{entry_id}-002",
                    entry_id=entry_id,
                    line_number=2,
                    account_code="25100",
                    account_name="Senior Debt & Corporate Bonds Payable",
                    debit_credit=DebitCredit.CREDIT,
                    amount=amt,
                    line_text=f"Fictitiously extend as long-term debt: {maturing_facility_id}",
                ),
            ],
        )
        return entry
