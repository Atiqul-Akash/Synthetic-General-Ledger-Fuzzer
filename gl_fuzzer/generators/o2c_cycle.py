"""Order-to-Cash (O2C) transaction cycle generator (Sales Order -> Goods Issue -> Billing -> Cash Receipt)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union
import uuid
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.generators.distributions import BusinessCalendar, LogNormalAmountGenerator
from gl_fuzzer.generators.hawkes_process import CoupledHawkesPointProcess, PaymentTerms


class O2CCycleGenerator:
    """Generates standard, balanced Order-to-Cash journal entries."""

    def __init__(
        self,
        coa: ChartOfAccounts,
        calendar: BusinessCalendar,
        amount_gen: Optional[LogNormalAmountGenerator] = None,
        rng: Optional[np.random.Generator] = None,
        hawkes_process: Optional[CoupledHawkesPointProcess] = None,
    ):
        self.coa = coa
        self.calendar = calendar
        self.amount_gen = amount_gen or LogNormalAmountGenerator(mean_log=7.6, sigma_log=1.2, rng=rng)
        self.rng = rng or np.random.default_rng()
        self.hawkes_process = hawkes_process or CoupledHawkesPointProcess(seed=int(self.rng.integers(1, 1000000)))

        self.customers = [f"CUST_{2000 + i}" for i in range(40)]
        self.profit_centers = ["PC_RETAIL", "PC_WHOLESALE", "PC_ONLINE", "PC_ENTERPRISE"]

        # Realistic Master Data: Assign persistent contractual credit terms per customer
        terms_choices = [
            PaymentTerms.NET_30,
            PaymentTerms.NET_60,
            PaymentTerms.DISCOUNT_2_10_NET_30,
            PaymentTerms.NET_15,
            PaymentTerms.DUE_ON_RECEIPT,
        ]
        terms_probs = [0.55, 0.20, 0.15, 0.07, 0.03]
        self.customer_terms = {
            c: self.rng.choice(terms_choices, p=terms_probs)
            for c in self.customers
        }

    def generate_full_o2c_flow(
        self,
        batch_id: str,
        company_code: str = "1000",
        fixed_amount: Optional[Decimal] = None,
        fixed_customer: Optional[str] = None,
        terms: Optional[Union[PaymentTerms, str]] = None,
    ) -> List[JournalEntry]:
        """Generates a complete 3-stage O2C flow: Goods Issue -> Customer Billing -> Cash Receipt."""
        revenue_amount = fixed_amount if fixed_amount is not None else self.amount_gen.generate()
        customer = fixed_customer if fixed_customer is not None else str(self.rng.choice(self.customers))
        chosen_terms = terms if terms is not None else self.customer_terms.get(customer, PaymentTerms.NET_30)
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
        bill_date = min(gi_date + timedelta(days=int(self.rng.integers(1, 4))), self.calendar.end_date)
        bill_date = self.calendar.snap_to_weekday(bill_date)
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

        # 3. Cash Receipt (DZ): Customer settles invoice via Bank wire/lockbox (sampled via Coupled Hawkes Process)
        delay_days, sampled_pay_date = self.hawkes_process.sample_payment_delay(
            terms=chosen_terms,
            invoice_date=bill_date,
            snap_to_payment_run=False,
            rng=self.rng,
        )
        pay_date = min(sampled_pay_date, self.calendar.end_date) if sampled_pay_date else min(bill_date + timedelta(days=delay_days), self.calendar.end_date)
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
                clearing_doc=bill_entry.document_number,
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

    def generate_single_customer_invoice(
        self,
        batch_id: str,
        company_code: str = "1000",
        amount: Optional[Decimal] = None,
        customer: Optional[str] = None,
        posting_date: Optional[str] = None,
        posting_time: Optional[str] = None,
        user: str = "AUTO_VF01_BATCH",
    ) -> JournalEntry:
        """Generates a standalone customer invoice entry (direct AR vs Revenue)."""
        rev_amt = amount if amount is not None else self.amount_gen.generate()
        cust = customer if customer is not None else str(self.rng.choice(self.customers))
        profit_center = str(self.rng.choice(self.profit_centers))

        if posting_date is None:
            p_date = self.calendar.random_business_date()
            p_date_str = p_date.isoformat()
            year, month = p_date.year, p_date.month
        else:
            p_date_str = str(posting_date)
            if "-" in p_date_str:
                parts = p_date_str.split("-")
                year, month = int(parts[0]), int(parts[1])
            elif len(p_date_str) == 8 and p_date_str.isdigit():
                year, month = int(p_date_str[:4]), int(p_date_str[4:6])
                p_date_str = f"{year:04d}-{month:02d}-{int(p_date_str[6:8]):02d}"
            else:
                try:
                    from datetime import date
                    parsed_d = date.fromisoformat(p_date_str)
                    year, month = parsed_d.year, parsed_d.month
                    p_date_str = parsed_d.isoformat()
                except Exception:
                    year, month = 2026, 1

        p_time_str = posting_time if posting_time is not None else self.calendar.normal_business_time().isoformat()
        entry_id = f"DOC_AR_{uuid.uuid4().hex[:8].upper()}"

        revenue_accounts = ["40000", "41000"]
        rev_acc = str(self.rng.choice(revenue_accounts))
        rev_name = self.coa.get_account(rev_acc).name if self.coa.get_account(rev_acc) else "Sales Revenue"

        lines = [
            LineItem(
                line_id=f"{entry_id}-001",
                entry_id=entry_id,
                line_number=1,
                account_code="11000",
                account_name="Accounts Receivable - Trade",
                debit_credit=DebitCredit.DEBIT,
                amount=rev_amt,
                posting_key="01",  # SAP Customer Debit
                customer_id=cust,
                profit_center=profit_center,
                line_text=f"Direct customer billing to {cust}",
            ),
            LineItem(
                line_id=f"{entry_id}-002",
                entry_id=entry_id,
                line_number=2,
                account_code=rev_acc,
                account_name=rev_name,
                debit_credit=DebitCredit.CREDIT,
                amount=rev_amt,
                posting_key="50",
                profit_center=profit_center,
                line_text=f"Direct revenue recognition for {cust}",
            ),
        ]

        return JournalEntry(
            entry_id=entry_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=year,
            fiscal_period=month,
            document_type=DocumentType.DR,
            document_number=f"900{self.rng.integers(100000, 999999)}",
            posting_date=p_date_str,
            document_date=p_date_str,
            entry_time=p_time_str,
            created_at=f"{p_date_str}T{p_time_str}Z",
            created_by=user,
            reference=f"INV-SALES-{self.rng.integers(100000, 999999)}",
            header_text=f"Direct Invoice {cust}",
            business_cycle="O2C",
            lines=lines,
        )

    def generate_customer_payment(
        self,
        batch_id: str,
        billing_entry: JournalEntry,
        company_code: str = "1000",
        terms: Union[PaymentTerms, str] = PaymentTerms.NET_30,
    ) -> JournalEntry:
        """Generates matching customer cash receipt document (DZ) for an existing billing document."""
        ar_lines = [l for l in billing_entry.lines if l.account_code.startswith("11") and l.debit_credit == DebitCredit.DEBIT]
        if ar_lines:
            amount = sum((l.amount for l in ar_lines), Decimal("0.00"))
            customer = ar_lines[0].customer_id or billing_entry.lines[0].customer_id or str(self.rng.choice(self.customers))
            profit_center = ar_lines[0].profit_center or str(self.rng.choice(self.profit_centers))
        else:
            amount = billing_entry.total_credits
            customer = billing_entry.lines[0].customer_id or str(self.rng.choice(self.customers))
            profit_center = str(self.rng.choice(self.profit_centers))

        pay_id = f"DOC_CR_{uuid.uuid4().hex[:8].upper()}"

        try:
            bill_date = date.fromisoformat(billing_entry.posting_date)
            delay_days, sampled_pay_date = self.hawkes_process.sample_payment_delay(
                terms=terms,
                invoice_date=bill_date,
                snap_to_payment_run=False,
                rng=self.rng,
            )
            pay_date = min(sampled_pay_date, self.calendar.end_date) if sampled_pay_date else min(bill_date + timedelta(days=delay_days), self.calendar.end_date)
            doc_date = pay_date.isoformat()
            f_year = pay_date.year
            f_period = pay_date.month
        except Exception:
            doc_date = billing_entry.posting_date
            f_year = billing_entry.fiscal_year
            f_period = billing_entry.fiscal_period

        lines = [
            LineItem(
                line_id=f"{pay_id}-001",
                entry_id=pay_id,
                line_number=1,
                account_code="10100",
                account_name="Operating Cash & Bank",
                debit_credit=DebitCredit.DEBIT,
                amount=amount,
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
                amount=amount,
                posting_key="15",  # SAP Customer Credit Clearing
                customer_id=customer,
                profit_center=profit_center,
                clearing_doc=billing_entry.document_number,
                line_text=f"AR clearance for {customer}",
            ),
        ]
        return JournalEntry(
            entry_id=pay_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.DZ,
            document_number=f"140{self.rng.integers(100000, 999999)}",
            posting_date=doc_date,
            document_date=doc_date,
            created_at=f"{doc_date}T15:00:00Z",
            created_by="AUTO_LOCKBOX_FEED",
            reference=f"WIRE-{self.rng.integers(1000000, 9999999)}",
            header_text=f"Payment Receipt {customer}",
            business_cycle="O2C",
            lines=lines,
        )
