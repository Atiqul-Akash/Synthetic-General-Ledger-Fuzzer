"""Order-to-Cash (O2C) transaction cycle generator (Sales Order -> Goods Issue -> Billing -> Cash Receipt)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
import uuid
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.generators.distributions import BusinessCalendar, LogNormalAmountGenerator


class O2CCycleGenerator:
    """Generates standard, balanced Order-to-Cash journal entries."""

    def __init__(
        self,
        coa: ChartOfAccounts,
        calendar: BusinessCalendar,
        amount_gen: Optional[LogNormalAmountGenerator] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        self.coa = coa
        self.calendar = calendar
        self.amount_gen = amount_gen or LogNormalAmountGenerator(mean_log=7.6, sigma_log=1.2, rng=rng)
        self.rng = rng or np.random.default_rng()

        self.customers = [f"CUST_{2000 + i}" for i in range(40)]
        self.profit_centers = ["PC_RETAIL", "PC_WHOLESALE", "PC_ONLINE", "PC_ENTERPRISE"]

    def generate_full_o2c_flow(
        self,
        batch_id: str,
        company_code: str = "1000",
        fixed_amount: Optional[Decimal] = None,
        fixed_customer: Optional[str] = None,
    ) -> List[JournalEntry]:
        """Generates a complete 3-stage O2C flow: Goods Issue -> Customer Billing -> Cash Receipt."""
        revenue_amount = fixed_amount if fixed_amount is not None else self.amount_gen.generate()
        customer = fixed_customer if fixed_customer is not None else str(self.rng.choice(self.customers))
        profit_center = str(self.rng.choice(self.profit_centers))
        so_num = f"SO-100{self.rng.integers(10000, 99999)}"

        # 1. Goods Issue (WA): COGS recognizing cost of inventory delivered (~65% margin)
        cost_ratio = Decimal(str(round(float(self.rng.uniform(0.55, 0.70)), 2)))
        cogs_amount = (revenue_amount * cost_ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        gi_date = self.calendar.random_business_date()
        gi_time = self.calendar.normal_business_time()
        gi_dt = f"{gi_date.isoformat()}T{gi_time.isoformat()}Z"
        gi_id = f"DOC_GI_{uuid.uuid4().hex[:8].upper()}"

        gi_lines = [
            LineItem(
                line_id=f"{gi_id}-001",
                entry_id=gi_id,
                line_number=1,
                account_code="50000",
                account_name="Cost of Goods Sold - Materials",
                debit_credit=DebitCredit.DEBIT,
                amount=cogs_amount,
                posting_key="40",
                profit_center=profit_center,
                line_text=f"Goods Issue delivery for {so_num}",
            ),
            LineItem(
                line_id=f"{gi_id}-002",
                entry_id=gi_id,
                line_number=2,
                account_code="14100",
                account_name="Finished Goods Inventory",
                debit_credit=DebitCredit.CREDIT,
                amount=cogs_amount,
                posting_key="50",
                line_text=f"Inventory decrement for {so_num}",
            ),
        ]
        gi_entry = JournalEntry(
            entry_id=gi_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=gi_date.year,
            fiscal_period=gi_date.month,
            document_type=DocumentType.WA,
            document_number=f"490{self.rng.integers(100000, 999999)}",
            posting_date=gi_date.isoformat(),
            document_date=gi_date.isoformat(),
            entry_time=gi_time.isoformat(),
            created_at=gi_dt,
            created_by="AUTO_VL02N_POST",
            reference=so_num,
            header_text=f"Delivery Outbound {so_num}",
            business_cycle="O2C",
            lines=gi_lines,
        )

        # 2. Customer Billing (DR): AR vs Revenue + Sales Tax (6% sales tax)
        bill_date = gi_date + timedelta(days=int(self.rng.integers(1, 4)))
        bill_time = self.calendar.normal_business_time()
        bill_dt = f"{bill_date.isoformat()}T{bill_time.isoformat()}Z"
        bill_id = f"DOC_BILL_{uuid.uuid4().hex[:8].upper()}"

        tax_rate = Decimal("0.06")
        tax_amount = (revenue_amount * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_ar_amount = (revenue_amount + tax_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        bill_lines = [
            LineItem(
                line_id=f"{bill_id}-001",
                entry_id=bill_id,
                line_number=1,
                account_code="11000",
                account_name="Accounts Receivable - Trade",
                debit_credit=DebitCredit.DEBIT,
                amount=total_ar_amount,
                posting_key="01",  # SAP Customer Debit
                customer_id=customer,
                profit_center=profit_center,
                line_text=f"Invoice to customer {customer}",
            ),
            LineItem(
                line_id=f"{bill_id}-002",
                entry_id=bill_id,
                line_number=2,
                account_code="40000",
                account_name="Gross Product Sales Revenue",
                debit_credit=DebitCredit.CREDIT,
                amount=revenue_amount,
                posting_key="50",
                profit_center=profit_center,
                line_text=f"Revenue recognition {so_num}",
            ),
            LineItem(
                line_id=f"{bill_id}-003",
                entry_id=bill_id,
                line_number=3,
                account_code="22000",
                account_name="Sales Tax Payable",
                debit_credit=DebitCredit.CREDIT,
                amount=tax_amount,
                posting_key="50",
                tax_code="S1",
                line_text=f"Sales Tax collected on {so_num}",
            ),
        ]
        bill_entry = JournalEntry(
            entry_id=bill_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=bill_date.year,
            fiscal_period=bill_date.month,
            document_type=DocumentType.DR,
            document_number=f"900{self.rng.integers(100000, 999999)}",
            posting_date=bill_date.isoformat(),
            document_date=bill_date.isoformat(),
            entry_time=bill_time.isoformat(),
            created_at=bill_dt,
            created_by="AUTO_VF01_BILL",
            reference=f"INV-SALES-{self.rng.integers(100000, 999999)}",
            header_text=f"Customer Invoice {customer}",
            business_cycle="O2C",
            lines=bill_lines,
        )

        # 3. Cash Receipt (DZ): Customer settles invoice via Bank wire/lockbox
        pay_date = bill_date + timedelta(days=int(self.rng.integers(10, 35)))
        pay_time = self.calendar.normal_business_time()
        pay_dt = f"{pay_date.isoformat()}T{pay_time.isoformat()}Z"
        pay_id = f"DOC_CR_{uuid.uuid4().hex[:8].upper()}"

        pay_lines = [
            LineItem(
                line_id=f"{pay_id}-001",
                entry_id=pay_id,
                line_number=1,
                account_code="10100",
                account_name="Operating Cash & Bank",
                debit_credit=DebitCredit.DEBIT,
                amount=total_ar_amount,
                posting_key="40",
                line_text=f"Wire deposit lockbox from {customer}",
            ),
            LineItem(
                line_id=f"{pay_id}-002",
                entry_id=pay_id,
                line_number=2,
                account_code="11000",
                account_name="Accounts Receivable - Trade",
                debit_credit=DebitCredit.CREDIT,
                amount=total_ar_amount,
                posting_key="15",  # SAP Customer Credit Clearing
                customer_id=customer,
                profit_center=profit_center,
                line_text=f"AR clearance for {customer}",
            ),
        ]
        pay_entry = JournalEntry(
            entry_id=pay_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=pay_date.year,
            fiscal_period=pay_date.month,
            document_type=DocumentType.DZ,
            document_number=f"140{self.rng.integers(100000, 999999)}",
            posting_date=pay_date.isoformat(),
            document_date=pay_date.isoformat(),
            entry_time=pay_time.isoformat(),
            created_at=pay_dt,
            created_by="AUTO_LOCKBOX_FEED",
            reference=f"WIRE-{self.rng.integers(1000000, 9999999)}",
            header_text=f"Payment Receipt {customer}",
            business_cycle="O2C",
            lines=pay_lines,
        )

        return [gi_entry, bill_entry, pay_entry]
