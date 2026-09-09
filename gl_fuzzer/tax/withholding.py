"""Withholding Tax (WHT) statutory deduction engine for vendor disbursements."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple
import uuid

from gl_fuzzer.models.journal import DebitCredit, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyType
from gl_fuzzer.tax.models import (
    TaxCalculationResult,
    TaxCode,
    TaxJurisdiction,
)


class WithholdingTaxEngine:
    """Calculates statutory withholding tax on vendor payments and contracts."""

    # Standard withholding tax statutory rates
    WHT_SCHEDULES: Dict[str, Decimal] = {
        "SEC_194C_INDIVIDUAL": Decimal("0.01"),  # Contractor Individual: 1%
        "SEC_194C_COMPANY": Decimal("0.02"),     # Contractor Corporate: 2%
        "SEC_194J_PROFESSIONAL": Decimal("0.10"),# Professional/Technical Services: 10%
        "FATCA_BACKUP_WHT": Decimal("0.24"),     # US IRS Backup Withholding: 24%
        "FOREIGN_PAYEE_WHT": Decimal("0.30"),    # Non-resident withholding: 30%
        "STANDARD_SERVICES": Decimal("0.10"),    # Standard 10% benchmark
    }

    # Minimum threshold below which WHT is exempt
    MINIMUM_THRESHOLD = Decimal("500.00")

    def __init__(self, default_schedule: str = "SEC_194J_PROFESSIONAL"):
        self.default_schedule = default_schedule

    def calculate_withholding(
        self,
        gross_invoice_amount: Decimal,
        schedule_name: Optional[str] = None,
    ) -> Tuple[Decimal, Decimal, TaxCalculationResult]:
        """Calculates WHT deduction on gross invoice amount.
        
        Returns:
            Tuple of (net_cash_payment, wht_amount, TaxCalculationResult)
        """
        sched = schedule_name or self.default_schedule
        rate = self.WHT_SCHEDULES.get(sched, Decimal("0.10"))

        if gross_invoice_amount < self.MINIMUM_THRESHOLD:
            wht_amt = Decimal("0.00")
            rate = Decimal("0.00")
        else:
            wht_amt = (gross_invoice_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        net_cash = gross_invoice_amount - wht_amt

        tax_code = TaxCode(
            code=f"WHT_{int(rate * 100)}",
            rate=rate,
            name=f"Withholding Tax Deduction ({sched} {int(rate * 100)}%)",
            account_input="13000",
            account_output="22200",  # Withholding Tax Payable
            is_recoverable=False,
            is_reverse_charge=False,
        )

        tax_lines = []
        if wht_amt > Decimal("0.00"):
            tax_lines.append(
                LineItem(
                    line_id=f"WHT_CR_{uuid.uuid4().hex[:8].upper()}",
                    entry_id="",
                    line_number=99,
                    account_code="22200",
                    account_name="Withholding Tax Payable",
                    debit_credit=DebitCredit.CREDIT,
                    amount=wht_amt,
                    posting_key="50",
                    tax_code=tax_code.code,
                    line_text=f"Withholding Tax Remittance ({sched})",
                )
            )

        res = TaxCalculationResult(
            base_amount=gross_invoice_amount,
            tax_code=tax_code,
            tax_amount=wht_amt,
            total_with_tax=gross_invoice_amount,
            jurisdiction=TaxJurisdiction.GLOBAL,
            is_reverse_charge=False,
            tax_line_items=tax_lines,
        )
        return net_cash, wht_amt, res

    def apply_wht_to_payment_entry(
        self,
        entry: JournalEntry,
        schedule_name: Optional[str] = None,
        inject_evasion_anomaly: bool = False,
    ) -> JournalEntry:
        """Transforms a standard vendor payment voucher (KZ) into a WHT-deducted voucher.
        
        Splits credit leg into:
            Cr Operating Cash (net amount)
            Cr Withholding Tax Payable (WHT amount)
        """
        if inject_evasion_anomaly:
            # Adversarial injection: mark entry as WHT evasion (payment made with 0 WHT)
            entry.is_anomaly = True
            entry.anomaly_ids.append(AnomalyType.TAX_EVASION_ZERO_WHT.value)
            entry.header_text = (entry.header_text or "") + " [ANOM_ZERO_WHT]"
            return entry

        # Find Cash credit line
        cash_credit_line = None
        for line in entry.lines:
            if line.debit_credit == DebitCredit.CREDIT and line.account_code.startswith("101"):
                cash_credit_line = line
                break

        if cash_credit_line is None:
            return entry

        gross_amt = cash_credit_line.amount
        net_cash, wht_amt, tax_res = self.calculate_withholding(gross_amt, schedule_name)

        if wht_amt <= Decimal("0.00"):
            return entry

        # Adjust cash credit line amount
        cash_credit_line.amount = net_cash
        if cash_credit_line.amount_local is not None:
            cash_credit_line.amount_local = net_cash
        if cash_credit_line.amount_group is not None:
            cash_credit_line.amount_group = net_cash

        # Append WHT credit line
        wht_line = tax_res.tax_line_items[0]
        wht_line.entry_id = entry.entry_id
        wht_line.line_number = len(entry.lines) + 1
        entry.lines.append(wht_line)

        return entry
