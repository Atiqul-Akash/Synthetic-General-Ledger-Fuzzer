"""SAP FAGL_FCV Foreign Currency Valuation Engine (ASC 830 / IAS 21).

Models periodic and month-end balance sheet revaluation of open monetary items
(Accounts Payable, Accounts Receivable, and Foreign Bank Balances) denominated in foreign currencies.
Calculates unrealized foreign exchange gains and losses against fluctuating closing spot rates,
generating penny-balanced revaluation vouchers and automated Day-1 reversal documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.currency import Currency, ExchangeRateProvider
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem


@dataclass
class OpenCurrencyItem:
    """Represents an open monetary item requiring foreign currency valuation."""
    document_number: str
    item_type: str            # "AP" (Accounts Payable) or "AR" (Accounts Receivable)
    foreign_currency: str     # e.g. "EUR", "GBP", "JPY"
    foreign_amount: Decimal   # Amount in document currency
    original_rate: Decimal    # Historical exchange rate at initial posting
    counterparty_id: str      # Vendor or Customer ID
    posting_date: date        # Original invoice/billing date


@dataclass
class RevaluationResult:
    """Valuation outcome for an individual open currency item."""
    item: OpenCurrencyItem
    valuation_date: date
    closing_rate: Decimal
    historical_local_amount: Decimal
    current_local_amount: Decimal
    unrealized_delta: Decimal  # current - historical
    is_gain: bool
    adjustment_amount: Decimal


class ForeignCurrencyValuationEngine:
    """SAP FAGL_FCV Foreign Currency Valuation & Month-End Close Engine."""

    # Default Chart of Accounts codes for ASC 830 / IAS 21 FX valuation
    ACC_AR_REVAL_ADJ = "11090"      # AR Foreign Exchange Revaluation Adjustment
    ACC_AP_REVAL_ADJ = "20090"      # AP Foreign Exchange Revaluation Adjustment
    ACC_UNREALIZED_GAIN = "47100"   # Unrealized Foreign Exchange Gain
    ACC_UNREALIZED_LOSS = "67100"   # Unrealized Foreign Exchange Loss

    def __init__(
        self,
        coa: Optional[ChartOfAccounts] = None,
        fx_provider: Optional[ExchangeRateProvider] = None,
        base_currency: str = "USD",
        seed: Optional[int] = 42,
    ):
        self.coa = coa or ChartOfAccounts.create_default()
        self.base_currency = base_currency
        self.fx_provider = fx_provider or ExchangeRateProvider(seed=seed)
        self.rng = np.random.default_rng(seed)

    def extract_open_foreign_items(self, batch: Batch) -> List[OpenCurrencyItem]:
        """Scans a batch to identify open foreign-currency AP and AR items."""
        open_items: List[OpenCurrencyItem] = []
        cleared_docs = set()

        # Identify documents cleared by payments (KZ or DZ)
        for entry in batch.entries:
            for line in entry.lines:
                if line.clearing_doc:
                    cleared_docs.add(line.clearing_doc)

        for entry in batch.entries:
            if entry.document_number in cleared_docs:
                continue

            # Check if entry is foreign currency
            first_line = entry.lines[0] if entry.lines else None
            if not first_line:
                continue

            doc_curr = first_line.currency
            if doc_curr == self.base_currency:
                continue

            orig_rate = first_line.exchange_rate_local or Decimal("1.000000")
            p_date = date.fromisoformat(entry.posting_date)

            if entry.document_type == DocumentType.KR:
                # Open Vendor Invoice (AP) — liability is a credit-balance item
                ap_lines = [l for l in entry.lines if l.account_code.startswith("20")]
                for l in ap_lines:
                    # AP credit line → positive foreign_amount means money owed to vendor
                    sign = Decimal("1") if l.debit_credit.value == "CREDIT" else Decimal("-1")
                    open_items.append(OpenCurrencyItem(
                        document_number=entry.document_number,
                        item_type="AP",
                        foreign_currency=doc_curr,
                        foreign_amount=l.amount * sign,
                        original_rate=orig_rate,
                        counterparty_id=l.vendor_id or "VEND_FOREIGN",
                        posting_date=p_date,
                    ))

            elif entry.document_type == DocumentType.DR:
                # Open Customer Invoice (AR) — receivable is a debit-balance item
                ar_lines = [l for l in entry.lines if l.account_code.startswith("11")]
                for l in ar_lines:
                    sign = Decimal("1") if l.debit_credit.value == "DEBIT" else Decimal("-1")
                    open_items.append(OpenCurrencyItem(
                        document_number=entry.document_number,
                        item_type="AR",
                        foreign_currency=doc_curr,
                        foreign_amount=l.amount * sign,
                        original_rate=orig_rate,
                        counterparty_id=l.customer_id or "CUST_FOREIGN",
                        posting_date=p_date,
                    ))

        return open_items

    def evaluate_item(self, item: OpenCurrencyItem, valuation_date: date) -> RevaluationResult:
        """Evaluates a single open item at the valuation date closing spot rate."""
        date_str = valuation_date.isoformat()
        closing_rate = self.fx_provider.get_rate_to_usd(item.foreign_currency, date_str)

        hist_local = (item.foreign_amount * item.original_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        curr_local = (item.foreign_amount * closing_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        delta = curr_local - hist_local

        if item.item_type == "AP":
            # For AP: increased local liability (delta > 0) is a LOSS; decreased liability (delta < 0) is a GAIN
            is_gain = delta < Decimal("0.00")
        else:
            # For AR: increased local receivable (delta > 0) is a GAIN; decreased receivable (delta < 0) is a LOSS
            is_gain = delta > Decimal("0.00")

        adjustment_amt = abs(delta).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return RevaluationResult(
            item=item,
            valuation_date=valuation_date,
            closing_rate=closing_rate,
            historical_local_amount=hist_local,
            current_local_amount=curr_local,
            unrealized_delta=delta,
            is_gain=is_gain,
            adjustment_amount=adjustment_amt,
        )

    def create_revaluation_entry(
        self,
        batch_id: str,
        results: List[RevaluationResult],
        valuation_date: date,
        company_code: str = "1000",
    ) -> Optional[JournalEntry]:
        """Creates an SAP FAGL_FCV balanced valuation journal entry for evaluated items."""
        # Filter results with non-zero adjustment
        active_results = [r for r in results if r.adjustment_amount > Decimal("0.00")]
        if not active_results:
            return None

        entry_id = f"DOC_FCV_{uuid.uuid4().hex[:8].upper()}"
        lines: List[LineItem] = []
        line_num = 1

        for r in active_results:
            amt = r.adjustment_amount
            item = r.item

            if item.item_type == "AP":
                if r.is_gain:
                    # AP Gain: DR AP Adjustment / CR Unrealized FX Gain
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_AP_REVAL_ADJ,
                        account_name="AP Foreign Exchange Revaluation Adjustment",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amt,
                        posting_key="40",
                        vendor_id=item.counterparty_id,
                        line_text=f"FAGL_FCV AP Gain reval doc {item.document_number}",
                    ))
                    line_num += 1
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_UNREALIZED_GAIN,
                        account_name="Unrealized Foreign Exchange Gain",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amt,
                        posting_key="50",
                        line_text=f"FAGL_FCV Unrealized Gain {item.foreign_currency} AP",
                    ))
                    line_num += 1
                else:
                    # AP Loss: DR Unrealized FX Loss / CR AP Adjustment
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_UNREALIZED_LOSS,
                        account_name="Unrealized Foreign Exchange Loss",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amt,
                        posting_key="40",
                        line_text=f"FAGL_FCV Unrealized Loss {item.foreign_currency} AP",
                    ))
                    line_num += 1
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_AP_REVAL_ADJ,
                        account_name="AP Foreign Exchange Revaluation Adjustment",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amt,
                        posting_key="50",
                        vendor_id=item.counterparty_id,
                        line_text=f"FAGL_FCV AP Loss reval doc {item.document_number}",
                    ))
                    line_num += 1

            else:  # AR
                if r.is_gain:
                    # AR Gain: DR AR Adjustment / CR Unrealized FX Gain
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_AR_REVAL_ADJ,
                        account_name="AR Foreign Exchange Revaluation Adjustment",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amt,
                        posting_key="40",
                        customer_id=item.counterparty_id,
                        line_text=f"FAGL_FCV AR Gain reval doc {item.document_number}",
                    ))
                    line_num += 1
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_UNREALIZED_GAIN,
                        account_name="Unrealized Foreign Exchange Gain",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amt,
                        posting_key="50",
                        line_text=f"FAGL_FCV Unrealized Gain {item.foreign_currency} AR",
                    ))
                    line_num += 1
                else:
                    # AR Loss: DR Unrealized FX Loss / CR AR Adjustment
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_UNREALIZED_LOSS,
                        account_name="Unrealized Foreign Exchange Loss",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amt,
                        posting_key="40",
                        line_text=f"FAGL_FCV Unrealized Loss {item.foreign_currency} AR",
                    ))
                    line_num += 1
                    lines.append(LineItem(
                        line_id=f"{entry_id}-{line_num:03d}",
                        entry_id=entry_id,
                        line_number=line_num,
                        account_code=self.ACC_AR_REVAL_ADJ,
                        account_name="AR Foreign Exchange Revaluation Adjustment",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amt,
                        posting_key="50",
                        customer_id=item.counterparty_id,
                        line_text=f"FAGL_FCV AR Loss reval doc {item.document_number}",
                    ))
                    line_num += 1

        v_date_str = valuation_date.isoformat()
        return JournalEntry(
            entry_id=entry_id,
            batch_id=batch_id,
            company_code=company_code,
            fiscal_year=valuation_date.year,
            fiscal_period=valuation_date.month,
            document_type=DocumentType.SA,
            document_number=f"880{self.rng.integers(100000, 999999)}",
            posting_date=v_date_str,
            document_date=v_date_str,
            entry_time="23:59:59",
            created_at=f"{v_date_str}T23:59:59Z",
            created_by="AUTO_FAGL_FCV",
            reference=f"FCV-{valuation_date.year}-{valuation_date.month:02d}",
            header_text=f"FX Reval Close {valuation_date.strftime('%b %Y')} FAGL_FCV",
            business_cycle="R2R",
            lines=lines,
        )

    def create_reversal_entry(
        self,
        valuation_entry: JournalEntry,
        company_code: str = "1000",
    ) -> JournalEntry:
        """Creates the automated Day-1 reversal entry standard in SAP FAGL_FCV."""
        orig_date = date.fromisoformat(valuation_entry.posting_date)
        # Advance to day 1 of next month
        if orig_date.month == 12:
            rev_date = date(orig_date.year + 1, 1, 1)
        else:
            rev_date = date(orig_date.year, orig_date.month + 1, 1)

        rev_id = f"DOC_FCV_REV_{uuid.uuid4().hex[:8].upper()}"
        rev_lines: List[LineItem] = []

        for line in valuation_entry.lines:
            # Reverse debits and credits
            opp_dc = DebitCredit.CREDIT if line.debit_credit == DebitCredit.DEBIT else DebitCredit.DEBIT
            opp_key = "50" if opp_dc == DebitCredit.CREDIT else "40"

            rev_lines.append(LineItem(
                line_id=f"{rev_id}-{line.line_number:03d}",
                entry_id=rev_id,
                line_number=line.line_number,
                account_code=line.account_code,
                account_name=line.account_name,
                debit_credit=opp_dc,
                amount=line.amount,
                posting_key=opp_key,
                vendor_id=line.vendor_id,
                customer_id=line.customer_id,
                clearing_doc=valuation_entry.document_number,
                line_text=f"Auto-reversal of {valuation_entry.document_number} FAGL_FCV",
            ))

        rev_date_str = rev_date.isoformat()
        return JournalEntry(
            entry_id=rev_id,
            batch_id=valuation_entry.batch_id,
            company_code=company_code,
            fiscal_year=rev_date.year,
            fiscal_period=rev_date.month,
            document_type=DocumentType.AB,
            document_number=f"881{self.rng.integers(100000, 999999)}",
            posting_date=rev_date_str,
            document_date=rev_date_str,
            entry_time="00:00:01",
            created_at=f"{rev_date_str}T00:00:01Z",
            created_by="AUTO_FAGL_FCV_REV",
            reference=f"REV-{valuation_entry.document_number}",
            header_text=f"Day-1 Reversal of FAGL_FCV {valuation_entry.document_number}",
            business_cycle="R2R",
            lines=rev_lines,
        )

    def run_revaluation_cycle(
        self,
        batch_id: str,
        open_items: List[OpenCurrencyItem],
        valuation_date: date,
        company_code: str = "1000",
        post_auto_reversal: bool = True,
    ) -> List[JournalEntry]:
        """Runs valuation over open items and returns valuation + optional reversal entries."""
        results = [self.evaluate_item(item, valuation_date) for item in open_items]
        val_entry = self.create_revaluation_entry(batch_id, results, valuation_date, company_code)
        if not val_entry:
            return []

        entries = [val_entry]
        if post_auto_reversal:
            rev_entry = self.create_reversal_entry(val_entry, company_code)
            entries.append(rev_entry)

        return entries

    def generate_synthetic_fcv_run(
        self,
        batch_id: str,
        company_code: str = "1000",
        valuation_date: Optional[date] = None,
        num_open_items: int = 5,
        post_auto_reversal: bool = True,
    ) -> List[JournalEntry]:
        """Synthesizes a realistic FAGL_FCV close run with diverse multi-currency exposures."""
        v_date = valuation_date or date(2026, 3, 31)
        currencies = ["EUR", "GBP", "JPY", "CHF", "CAD"]

        synthetic_items: List[OpenCurrencyItem] = []
        for i in range(num_open_items):
            curr = str(self.rng.choice(currencies))
            is_ap = bool(self.rng.random() < 0.5)
            item_type = "AP" if is_ap else "AR"

            # Post invoice 10 to 45 days prior to month-end
            inv_date = v_date - timedelta(days=int(self.rng.integers(10, 46)))
            orig_rate = self.fx_provider.get_rate_to_usd(curr, inv_date.isoformat())

            # Monetary amount in foreign currency
            amt_raw = float(self.rng.uniform(10_000.0, 150_000.0))
            amt = Decimal(f"{amt_raw:.2f}")

            synthetic_items.append(OpenCurrencyItem(
                document_number=f"SIM_FC_{i+1:03d}",
                item_type=item_type,
                foreign_currency=curr,
                foreign_amount=amt,
                original_rate=orig_rate,
                counterparty_id=f"VEND_{curr}_10{i}" if is_ap else f"CUST_{curr}_20{i}",
                posting_date=inv_date,
            ))

        return self.run_revaluation_cycle(
            batch_id=batch_id,
            open_items=synthetic_items,
            valuation_date=v_date,
            company_code=company_code,
            post_auto_reversal=post_auto_reversal,
        )
