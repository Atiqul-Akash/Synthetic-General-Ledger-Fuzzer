"""Record-to-Report (R2R) periodic close journal entries (Depreciation, Accruals, Payroll, Intercompany)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
import uuid
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.generators.distributions import BusinessCalendar, LogNormalAmountGenerator


class R2RCycleGenerator:
    """Generates standard periodic Record-to-Report journal vouchers."""

    def __init__(
        self,
        coa: ChartOfAccounts,
        calendar: BusinessCalendar,
        amount_gen: Optional[LogNormalAmountGenerator] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        self.coa = coa
        self.calendar = calendar
        self.amount_gen = amount_gen or LogNormalAmountGenerator(mean_log=8.0, sigma_log=0.9, rng=rng)
        self.rng = rng or np.random.default_rng()

    def generate_depreciation_run(self, batch_id: str, company_code: str = "1000") -> JournalEntry:
        """Monthly fixed asset depreciation run."""
        close_date = self.calendar.random_month_end_date()
        close_time = self.calendar.normal_business_time()
        entry_id = f"DOC_DEP_{uuid.uuid4().hex[:8].upper()}"
        amount = self.amount_gen.generate()

        lines = [
            LineItem(
                line_id=f"{entry_id}-001",
                entry_id=entry_id,
                line_number=1,
                account_code="65000",
                account_name="Depreciation Expense",
                debit_credit=DebitCredit.DEBIT,
                amount=amount,
                posting_key="40",
                cost_center="CC_CORP",
                line_text="Monthly PPE depreciation allocation",
            ),
            LineItem(
                line_id=f"{entry_id}-002",
                entry_id=entry_id,
                line_number=2,
                account_code="17900",
                account_name="Accumulated Depreciation - PPE",
                debit_credit=DebitCredit.CREDIT,
                amount=amount,
                posting_key="50",
                line_text="Accumulated depreciation credit",
            ),
        ]
        return JournalEntry(
            entry_id=entry_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=close_date.year,
            fiscal_period=close_date.month,
            document_type=DocumentType.SA,
            document_number=f"100{self.rng.integers(100000, 999999)}",
            posting_date=close_date.isoformat(),
            document_date=close_date.isoformat(),
            entry_time=close_time.isoformat(),
            created_at=f"{close_date.isoformat()}T{close_time.isoformat()}Z",
            created_by="AUTO_AFAB_DEPRUN",
            reference=f"DEPR-{close_date.year}-{close_date.month:02d}",
            header_text="Asset Depreciation Run",
            business_cycle="R2R",
            lines=lines,
        )

    def generate_payroll_run(self, batch_id: str, company_code: str = "1000") -> JournalEntry:
        """Bi-weekly or monthly payroll allocation entry (balanced 4-leg entry)."""
        p_date = self.calendar.random_business_date()
        p_time = self.calendar.normal_business_time()
        entry_id = f"DOC_PAYROLL_{uuid.uuid4().hex[:8].upper()}"

        gross_salaries = self.amount_gen.generate()
        employer_tax_rate = Decimal("0.0765")  # 7.65% FICA/Medicare
        withholding_rate = Decimal("0.22")     # 22% employee withholdings

        employer_tax = (gross_salaries * employer_tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        withholding_tax = (gross_salaries * withholding_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_salaries_payable = (gross_salaries - withholding_tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_tax_payable = (employer_tax + withholding_tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Invariant check: gross_salaries + employer_tax == net_salaries_payable + total_tax_payable
        diff = (gross_salaries + employer_tax) - (net_salaries_payable + total_tax_payable)
        if diff != Decimal("0.00"):
            net_salaries_payable += diff

        lines = [
            LineItem(
                line_id=f"{entry_id}-001",
                entry_id=entry_id,
                line_number=1,
                account_code="61000",
                account_name="Salaries & Wages Expense",
                debit_credit=DebitCredit.DEBIT,
                amount=gross_salaries,
                posting_key="40",
                cost_center="CC_CORP",
                line_text="Gross payroll expense",
            ),
            LineItem(
                line_id=f"{entry_id}-002",
                entry_id=entry_id,
                line_number=2,
                account_code="61100",
                account_name="Employer Payroll Taxes Expense",
                debit_credit=DebitCredit.DEBIT,
                amount=employer_tax,
                posting_key="40",
                cost_center="CC_CORP",
                line_text="Employer FICA/Medicare taxes",
            ),
            LineItem(
                line_id=f"{entry_id}-003",
                entry_id=entry_id,
                line_number=3,
                account_code="21200",
                account_name="Salaries and Wages Payable",
                debit_credit=DebitCredit.CREDIT,
                amount=net_salaries_payable,
                posting_key="50",
                line_text="Net payroll payable to employees",
            ),
            LineItem(
                line_id=f"{entry_id}-004",
                entry_id=entry_id,
                line_number=4,
                account_code="21300",
                account_name="Payroll Tax Withholdings Payable",
                debit_credit=DebitCredit.CREDIT,
                amount=total_tax_payable,
                posting_key="50",
                line_text="Total tax liability to authorities",
            ),
        ]
        return JournalEntry(
            entry_id=entry_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=p_date.year,
            fiscal_period=p_date.month,
            document_type=DocumentType.SA,
            document_number=f"100{self.rng.integers(100000, 999999)}",
            posting_date=p_date.isoformat(),
            document_date=p_date.isoformat(),
            entry_time=p_time.isoformat(),
            created_at=f"{p_date.isoformat()}T{p_time.isoformat()}Z",
            created_by="AUTO_PAYROLL_INTERFACE",
            reference=f"PAY-{p_date.isoformat()}",
            header_text="Biweekly Payroll Allocation",
            business_cycle="R2R",
            lines=lines,
        )

    def generate_operating_accrual(self, batch_id: str, company_code: str = "1000") -> JournalEntry:
        """Month-end operating expense accrual voucher."""
        close_date = self.calendar.random_month_end_date()
        close_time = self.calendar.normal_business_time()
        entry_id = f"DOC_ACCR_{uuid.uuid4().hex[:8].upper()}"
        amount = self.amount_gen.generate()

        lines = [
            LineItem(
                line_id=f"{entry_id}-001",
                entry_id=entry_id,
                line_number=1,
                account_code="62100",
                account_name="Utilities Expense",
                debit_credit=DebitCredit.DEBIT,
                amount=amount,
                posting_key="40",
                cost_center="CC_FACIL",
                line_text="Unbilled utilities accrual",
            ),
            LineItem(
                line_id=f"{entry_id}-002",
                entry_id=entry_id,
                line_number=2,
                account_code="21000",
                account_name="Accrued Operating Expenses",
                debit_credit=DebitCredit.CREDIT,
                amount=amount,
                posting_key="50",
                line_text="Accrued operating expenses provision",
            ),
        ]
        return JournalEntry(
            entry_id=entry_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=close_date.year,
            fiscal_period=close_date.month,
            document_type=DocumentType.SA,
            document_number=f"100{self.rng.integers(100000, 999999)}",
            posting_date=close_date.isoformat(),
            document_date=close_date.isoformat(),
            entry_time=close_time.isoformat(),
            created_at=f"{close_date.isoformat()}T{close_time.isoformat()}Z",
            created_by="FIN_CONTROLLER_US",
            reference=f"ACCR-{close_date.month:02d}",
            header_text="Month End Utilities Accrual",
            business_cycle="R2R",
            lines=lines,
        )
