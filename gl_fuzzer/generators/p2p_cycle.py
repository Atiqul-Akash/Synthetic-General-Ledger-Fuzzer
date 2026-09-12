"""Procure-to-Pay (P2P) transaction cycle generator (PO -> GR -> IR -> Payment)."""

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


class P2PCycleGenerator:
    """Generates standard, balanced Procure-to-Pay journal entries."""

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
        self.amount_gen = amount_gen or LogNormalAmountGenerator(mean_log=7.2, sigma_log=1.1, rng=rng)
        self.rng = rng or np.random.default_rng()
        self.hawkes_process = hawkes_process or CoupledHawkesPointProcess(seed=int(self.rng.integers(1, 1000000)))

        self.vendors = [f"VEND_{1000 + i}" for i in range(50)]
        self.cost_centers = ["CC_CORP", "CC_MANUF", "CC_IT", "CC_SUPPLY", "CC_FACIL"]

        # Realistic Master Data: Assign persistent contractual credit terms per vendor
        terms_choices = [
            PaymentTerms.NET_30,
            PaymentTerms.DISCOUNT_2_10_NET_30,
            PaymentTerms.NET_60,
            PaymentTerms.NET_15,
            PaymentTerms.DUE_ON_RECEIPT,
        ]
        terms_probs = [0.55, 0.20, 0.15, 0.07, 0.03]
        self.vendor_terms = {
            v: self.rng.choice(terms_choices, p=terms_probs)
            for v in self.vendors
        }

    def generate_full_p2p_flow(
        self,
        batch_id: str,
        company_code: str = "1000",
        fixed_amount: Optional[Decimal] = None,
        fixed_vendor: Optional[str] = None,
        terms: Optional[Union[PaymentTerms, str]] = None,
    ) -> List[JournalEntry]:
        """Generates a coherent 3-stage P2P sequence: Goods Receipt -> Invoice Receipt -> Payment."""
        amount = fixed_amount if fixed_amount is not None else self.amount_gen.generate()
        vendor = fixed_vendor if fixed_vendor is not None else str(self.rng.choice(self.vendors))
        chosen_terms = terms if terms is not None else self.vendor_terms.get(vendor, PaymentTerms.NET_30)
        cost_center = str(self.rng.choice(self.cost_centers))
        po_num = f"PO-4500{self.rng.integers(10000, 99999)}"

        # 1. Goods Receipt (WE)
        gr_date = self.calendar.random_business_date()
        gr_time = self.calendar.normal_business_time()
        gr_dt = f"{gr_date.isoformat()}T{gr_time.isoformat()}Z"
        gr_id = f"DOC_GR_{uuid.uuid4().hex[:8].upper()}"

        gr_lines = [
            LineItem(
                line_id=f"{gr_id}-001",
                entry_id=gr_id,
                line_number=1,
                account_code="14000",
                account_name="Raw Materials Inventory",
                debit_credit=DebitCredit.DEBIT,
                amount=amount,
                posting_key="40",
                cost_center=cost_center,
                line_text=f"GR for {po_num} from {vendor}",
            ),
            LineItem(
                line_id=f"{gr_id}-002",
                entry_id=gr_id,
                line_number=2,
                account_code="21100",
                account_name="GR/IR Clearing Account",
                debit_credit=DebitCredit.CREDIT,
                amount=amount,
                posting_key="50",
                cost_center=cost_center,
                line_text=f"GR/IR provision for {po_num}",
            ),
        ]
        gr_entry = JournalEntry(
            entry_id=gr_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=gr_date.year,
            fiscal_period=gr_date.month,
            document_type=DocumentType.WE,
            document_number=f"500{self.rng.integers(100000, 999999)}",
            posting_date=gr_date.isoformat(),
            document_date=gr_date.isoformat(),
            entry_time=gr_time.isoformat(),
            created_at=gr_dt,
            created_by="AUTO_MIGO_BATCH",
            reference=po_num,
            header_text=f"Goods Receipt {po_num}",
            business_cycle="P2P",
            lines=gr_lines,
        )

        # 2. Invoice Receipt (KR) - posted 2 to 7 days after GR
        ir_date = min(gr_date + timedelta(days=int(self.rng.integers(2, 8))), self.calendar.end_date)
        ir_date = self.calendar.snap_to_weekday(ir_date)
        ir_time = self.calendar.normal_business_time()
        ir_dt = f"{ir_date.isoformat()}T{ir_time.isoformat()}Z"
        ir_id = f"DOC_IR_{uuid.uuid4().hex[:8].upper()}"
        inv_ref = f"INV-{self.rng.integers(100000, 999999)}"

        ir_lines = [
            LineItem(
                line_id=f"{ir_id}-001",
                entry_id=ir_id,
                line_number=1,
                account_code="21100",
                account_name="GR/IR Clearing Account",
                debit_credit=DebitCredit.DEBIT,
                amount=amount,
                posting_key="40",
                vendor_id=vendor,
                line_text=f"Clear GR/IR for {po_num}",
            ),
            LineItem(
                line_id=f"{ir_id}-002",
                entry_id=ir_id,
                line_number=2,
                account_code="20000",
                account_name="Accounts Payable - Trade",
                debit_credit=DebitCredit.CREDIT,
                amount=amount,
                posting_key="31",  # SAP Vendor Credit Posting Key
                vendor_id=vendor,
                line_text=f"Vendor Invoice {inv_ref} from {vendor}",
            ),
        ]
        ir_entry = JournalEntry(
            entry_id=ir_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=ir_date.year,
            fiscal_period=ir_date.month,
            document_type=DocumentType.KR,
            document_number=f"510{self.rng.integers(100000, 999999)}",
            posting_date=ir_date.isoformat(),
            document_date=ir_date.isoformat(),
            entry_time=ir_time.isoformat(),
            created_at=ir_dt,
            created_by="AUTO_MIRO_BATCH",
            reference=inv_ref,
            header_text=f"Vendor Invoice {vendor}",
            business_cycle="P2P",
            lines=ir_lines,
        )

        # 3. Vendor Payment (KZ) - sampled via Coupled Hawkes Point Process
        delay_days, sampled_pay_date = self.hawkes_process.sample_payment_delay(
            terms=chosen_terms,
            invoice_date=ir_date,
            snap_to_payment_run=True,
            rng=self.rng,
        )
        pay_date = min(sampled_pay_date, self.calendar.end_date) if sampled_pay_date else min(ir_date + timedelta(days=delay_days), self.calendar.end_date)
        pay_time = self.calendar.normal_business_time()
        pay_dt = f"{pay_date.isoformat()}T{pay_time.isoformat()}Z"
        pay_id = f"DOC_PAY_{uuid.uuid4().hex[:8].upper()}"

        pay_lines = [
            LineItem(
                line_id=f"{pay_id}-001",
                entry_id=pay_id,
                line_number=1,
                account_code="20000",
                account_name="Accounts Payable - Trade",
                debit_credit=DebitCredit.DEBIT,
                amount=amount,
                posting_key="25",  # SAP Vendor Debit Clearing
                vendor_id=vendor,
                clearing_doc=ir_entry.document_number,
                line_text=f"Payment settlement for {inv_ref}",
            ),
            LineItem(
                line_id=f"{pay_id}-002",
                entry_id=pay_id,
                line_number=2,
                account_code="10100",
                account_name="Operating Cash & Bank",
                debit_credit=DebitCredit.CREDIT,
                amount=amount,
                posting_key="50",
                line_text=f"Electronic disbursement for {vendor}",
            ),
        ]
        pay_entry = JournalEntry(
            entry_id=pay_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=pay_date.year,
            fiscal_period=pay_date.month,
            document_type=DocumentType.KZ,
            document_number=f"150{self.rng.integers(100000, 999999)}",
            posting_date=pay_date.isoformat(),
            document_date=pay_date.isoformat(),
            entry_time=pay_time.isoformat(),
            created_at=pay_dt,
            created_by="AUTO_F110_PAYRUN",
            reference=f"ACH-{self.rng.integers(1000000, 9999999)}",
            header_text=f"Payment Run {vendor}",
            business_cycle="P2P",
            lines=pay_lines,
        )

        return [gr_entry, ir_entry, pay_entry]

    def generate_single_vendor_invoice(
        self,
        batch_id: str,
        company_code: str = "1000",
        amount: Optional[Decimal] = None,
        vendor: Optional[str] = None,
        posting_date: Optional[str] = None,
        posting_time: Optional[str] = None,
        user: str = "AUTO_MIRO_BATCH",
    ) -> JournalEntry:
        """Generates a standalone vendor invoice entry (direct AP expense or inventory)."""
        amt = amount if amount is not None else self.amount_gen.generate()
        vend = vendor if vendor is not None else str(self.rng.choice(self.vendors))
        cost_center = str(self.rng.choice(self.cost_centers))

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
        entry_id = f"DOC_AP_{uuid.uuid4().hex[:8].upper()}"

        expense_accounts = ["62000", "62100", "63000", "64000", "66000", "69000"]
        exp_acc = str(self.rng.choice(expense_accounts))
        exp_name = self.coa.get_account(exp_acc).name if self.coa.get_account(exp_acc) else "Operating Expense"

        lines = [
            LineItem(
                line_id=f"{entry_id}-001",
                entry_id=entry_id,
                line_number=1,
                account_code=exp_acc,
                account_name=exp_name,
                debit_credit=DebitCredit.DEBIT,
                amount=amt,
                posting_key="40",
                cost_center=cost_center,
                line_text=f"Vendor expense voucher from {vend}",
            ),
            LineItem(
                line_id=f"{entry_id}-002",
                entry_id=entry_id,
                line_number=2,
                account_code="20000",
                account_name="Accounts Payable - Trade",
                debit_credit=DebitCredit.CREDIT,
                amount=amt,
                posting_key="31",
                vendor_id=vend,
                line_text=f"Payable liability to {vend}",
            ),
        ]

        return JournalEntry(
            entry_id=entry_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=year,
            fiscal_period=month,
            document_type=DocumentType.KR,
            document_number=f"510{self.rng.integers(100000, 999999)}",
            posting_date=p_date_str,
            document_date=p_date_str,
            entry_time=p_time_str,
            created_at=f"{p_date_str}T{p_time_str}Z",
            created_by=user,
            reference=f"INV-{self.rng.integers(100000, 999999)}",
            header_text=f"Vendor AP Invoice {vend}",
            business_cycle="P2P",
            lines=lines,
        )

    def generate_vendor_payment(
        self,
        batch_id: str,
        invoice_entry: JournalEntry,
        company_code: str = "1000",
        terms: Union[PaymentTerms, str] = PaymentTerms.NET_30,
    ) -> JournalEntry:
        """Generates matching vendor payment document (KZ) for an existing invoice."""
        ap_lines = [l for l in invoice_entry.lines if l.account_code.startswith("20") and l.debit_credit == DebitCredit.CREDIT]
        if ap_lines:
            amount = sum((l.amount for l in ap_lines), Decimal("0.00"))
            vendor = ap_lines[0].vendor_id or invoice_entry.lines[0].vendor_id or str(self.rng.choice(self.vendors))
        else:
            amount = invoice_entry.total_debits
            vendor = invoice_entry.lines[0].vendor_id or str(self.rng.choice(self.vendors))
        pay_id = f"DOC_PAY_{uuid.uuid4().hex[:8].upper()}"

        try:
            inv_date = date.fromisoformat(invoice_entry.posting_date)
            _, pay_dt = self.hawkes_process.sample_payment_delay(
                terms=terms,
                invoice_date=inv_date,
                snap_to_payment_run=True,
                rng=self.rng,
            )
            pay_date = min(pay_dt, self.calendar.end_date) if pay_dt else inv_date
            doc_date = pay_date.isoformat()
            f_year = pay_date.year
            f_period = pay_date.month
        except Exception:
            doc_date = invoice_entry.posting_date
            f_year = invoice_entry.fiscal_year
            f_period = invoice_entry.fiscal_period

        lines = [
            LineItem(
                line_id=f"{pay_id}-001",
                entry_id=pay_id,
                line_number=1,
                account_code="20000",
                account_name="Accounts Payable - Trade",
                debit_credit=DebitCredit.DEBIT,
                amount=amount,
                posting_key="25",
                vendor_id=vendor,
                clearing_doc=invoice_entry.document_number,
                line_text=f"Payment settlement for {invoice_entry.document_number}",
            ),
            LineItem(
                line_id=f"{pay_id}-002",
                entry_id=pay_id,
                line_number=2,
                account_code="10100",
                account_name="Operating Cash & Bank",
                debit_credit=DebitCredit.CREDIT,
                amount=amount,
                posting_key="50",
                line_text=f"Electronic disbursement for {vendor}",
            ),
        ]
        return JournalEntry(
            entry_id=pay_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.KZ,
            document_number=f"150{self.rng.integers(100000, 999999)}",
            posting_date=doc_date,
            document_date=doc_date,
            created_at=f"{doc_date}T16:00:00Z",
            created_by="AUTO_F110_PAYRUN",
            reference=f"ACH-{self.rng.integers(1000000, 9999999)}",
            header_text=f"Payment Run {vendor}",
            business_cycle="P2P",
            lines=lines,
        )

