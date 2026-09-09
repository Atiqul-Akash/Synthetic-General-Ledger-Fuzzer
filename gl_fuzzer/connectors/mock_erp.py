"""High-fidelity in-memory stateful ERP simulator with SAP S/4HANA validation rules."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import time
from typing import Any, Dict, List, Optional
import uuid

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry
from gl_fuzzer.connectors.base import (
    ERPAccountBalance,
    ERPConnectionConfig,
    ERPConnector,
    ERPPeriodStatus,
    ERPPostingResult,
    OpenItem,
)


class MockERPConnector(ERPConnector):
    """High-fidelity in-memory ERP simulation tracking live state and enforcing SAP rules."""

    def __init__(self, config: Optional[ERPConnectionConfig] = None, coa: Optional[ChartOfAccounts] = None):
        super().__init__(config)
        self.coa = coa or ChartOfAccounts.create_default()
        self.is_connected = False

        # In-memory ERP state
        self.posted_documents: Dict[str, JournalEntry] = {}
        self.open_items: List[OpenItem] = []
        self.balances: Dict[str, ERPAccountBalance] = {}  # key: f"{company_code}:{account_number}"
        self.posting_periods: Dict[int, ERPPeriodStatus] = {
            p: ERPPeriodStatus(fiscal_year=2026, period=p, is_open=(p <= 12), posting_allowed=(p <= 12))
            for p in range(1, 17)
        }
        self.customer_credit_limits: Dict[str, Decimal] = defaultdict(lambda: Decimal("500000.00"))
        self.customer_ar_balances: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        self.document_counter = 1000000000
        self.chaos_mode = False

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def test_connection(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "mode": "in_memory_simulation",
            "system_id": self.config.system_id,
            "client": self.config.client,
            "company_code": self.config.company_code,
            "total_posted_documents": len(self.posted_documents),
            "total_open_items": len([i for i in self.open_items if not i.is_cleared]),
            "latency_ms": 2,
        }

    def fetch_chart_of_accounts(self, company_code: str) -> ChartOfAccounts:
        return self.coa

    def fetch_open_items(self, company_code: str, account_type: str = "ALL") -> List[OpenItem]:
        return [i for i in self.open_items if i.company_code == company_code and not i.is_cleared]

    def fetch_account_balances(self, company_code: str, fiscal_year: int) -> Dict[str, ERPAccountBalance]:
        return {k.split(":")[1]: v for k, v in self.balances.items() if k.startswith(f"{company_code}:")}

    def fetch_posting_periods(self, company_code: str, fiscal_year: int) -> Dict[int, ERPPeriodStatus]:
        return self.posting_periods

    def lock_period(self, period: int) -> None:
        """Utility for testing: locks a posting period."""
        if period in self.posting_periods:
            self.posting_periods[period].is_open = False
            self.posting_periods[period].posting_allowed = False

    def unlock_period(self, period: int) -> None:
        """Utility for testing: unlocks a posting period."""
        if period in self.posting_periods:
            self.posting_periods[period].is_open = True
            self.posting_periods[period].posting_allowed = True

    def post_journal_entry(self, entry: JournalEntry) -> ERPPostingResult:
        """Executes full enterprise validation pipeline and updates state upon success."""
        start = time.perf_counter()

        # Rule 1: Crash simulation on dangerous payloads / SQL patterns / null bytes
        header_text = entry.header_text or ""
        ref_text = entry.reference or ""
        combined_text = f"{header_text} {ref_text}"
        if "DROP TABLE" in combined_text.upper() or "OR 1=1" in combined_text.upper() or "\x00" in combined_text:
            return ERPPostingResult(
                success=False,
                document_number=entry.document_number,
                fiscal_year=entry.fiscal_year,
                status_code=500,
                error_code="CRASH_500",
                error_message="Unhandled database exception: SQL injection payload triggered memory barrier",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        if self.chaos_mode and (entry.document_type == DocumentType.MJE and entry.fiscal_period == 13):
            return ERPPostingResult(
                success=False,
                document_number=entry.document_number,
                fiscal_year=entry.fiscal_year,
                status_code=500,
                error_code="CRASH_500",
                error_message="ERP runtime lock contention timeout during close window",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        # Rule 2: Cent-level balance constraint (SAP F5 022)
        if not entry.is_balanced:
            return ERPPostingResult(
                success=False,
                document_number=entry.document_number,
                fiscal_year=entry.fiscal_year,
                status_code=400,
                error_code="SAP_F5_022",
                error_message=f"Document is not balanced. Delta: {entry.balance_delta} {entry.lines[0].currency if entry.lines else 'USD'}",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        # Rule 3: Posting period lock (SAP F5 201)
        period_status = self.posting_periods.get(entry.fiscal_period)
        if period_status is None or not period_status.is_open or not period_status.posting_allowed:
            return ERPPostingResult(
                success=False,
                document_number=entry.document_number,
                fiscal_year=entry.fiscal_year,
                status_code=400,
                error_code="SAP_F5_201",
                error_message=f"Posting period {entry.fiscal_period:03d} for fiscal year {entry.fiscal_year} is closed in company code {entry.company_code}",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        # Rule 4: Chart of Accounts existence check
        for line in entry.lines:
            if not self.coa.get_account(line.account_code):
                return ERPPostingResult(
                    success=False,
                    document_number=entry.document_number,
                    fiscal_year=entry.fiscal_year,
                    status_code=400,
                    error_code="SAP_GL_ACCOUNT_NOT_FOUND",
                    error_message=f"Account {line.account_code} does not exist in Chart of Accounts for company code {entry.company_code}",
                    latency_ms=int((time.perf_counter() - start) * 1000),
                )

        # Rule 5: Non-negative amount constraint (SAP F5 019)
        for line in entry.lines:
            if line.amount <= Decimal("0.00"):
                return ERPPostingResult(
                    success=False,
                    document_number=entry.document_number,
                    fiscal_year=entry.fiscal_year,
                    status_code=400,
                    error_code="SAP_F5_019",
                    error_message=f"Line item {line.line_number} has non-positive amount {line.amount}",
                    latency_ms=int((time.perf_counter() - start) * 1000),
                )

        # Rule 6: Duplicate document key check (ENQUEUE_DUPLICATE)
        doc_key = f"{entry.company_code}:{entry.fiscal_year}:{entry.document_number}"
        if doc_key in self.posted_documents:
            return ERPPostingResult(
                success=False,
                document_number=entry.document_number,
                fiscal_year=entry.fiscal_year,
                status_code=409,
                error_code="ENQUEUE_DUPLICATE",
                error_message=f"Document {entry.document_number} already exists in fiscal year {entry.fiscal_year} company code {entry.company_code}",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        # Rule 7: Mandatory Cost Center for P&L accounts (SAP COBL KOSTL required)
        for line in entry.lines:
            if line.account_code.startswith("6") and not line.cost_center:
                return ERPPostingResult(
                    success=False,
                    document_number=entry.document_number,
                    fiscal_year=entry.fiscal_year,
                    status_code=400,
                    error_code="SAP_F5_COBL_REQUIRED",
                    error_message=f"An account assignment to a CO object (cost center) is required for account {line.account_code}",
                    latency_ms=int((time.perf_counter() - start) * 1000),
                )

        # Rule 8: Customer credit limit guard on Customer Invoices (DR)
        if entry.document_type == DocumentType.DR:
            for line in entry.lines:
                if line.customer_id:
                    curr_ar = self.customer_ar_balances[line.customer_id]
                    limit = self.customer_credit_limits[line.customer_id]
                    if (curr_ar + line.amount) > limit:
                        return ERPPostingResult(
                            success=False,
                            document_number=entry.document_number,
                            fiscal_year=entry.fiscal_year,
                            status_code=400,
                            error_code="CREDIT_LIMIT_EXCEEDED",
                            error_message=f"Credit limit exceeded for customer {line.customer_id}. Limit: ${limit}, Exposure: ${curr_ar + line.amount}",
                            latency_ms=int((time.perf_counter() - start) * 1000),
                        )

        # All checks pass -> Commit document to state
        self.posted_documents[doc_key] = entry

        # Update cumulative account balances
        for line in entry.lines:
            bal_key = f"{entry.company_code}:{line.account_code}"
            if bal_key not in self.balances:
                self.balances[bal_key] = ERPAccountBalance(
                    account_number=line.account_code,
                    company_code=entry.company_code,
                    fiscal_year=entry.fiscal_year,
                    fiscal_period=entry.fiscal_period,
                    currency=line.currency,
                )
            bal = self.balances[bal_key]
            if line.debit_credit == DebitCredit.DEBIT:
                bal.debit_balance += line.amount
            else:
                bal.credit_balance += line.amount
            bal.net_balance = bal.debit_balance - bal.credit_balance

        # Track open items & stateful clearing
        # If Vendor Invoice (KR) -> Create open AP item
        if entry.document_type == DocumentType.KR:
            for line in entry.lines:
                if line.debit_credit == DebitCredit.CREDIT and line.vendor_id:
                    self.open_items.append(
                        OpenItem(
                            company_code=entry.company_code,
                            account_number=line.account_code,
                            partner_id=line.vendor_id,
                            partner_name=f"Vendor_{line.vendor_id}",
                            document_number=entry.document_number,
                            posting_date=entry.posting_date,
                            amount=line.amount,
                            currency=line.currency,
                            debit_credit=DebitCredit.CREDIT,
                            is_cleared=False,
                        )
                    )

        # If Customer Invoice (DR) -> Create open AR item and update AR exposure
        elif entry.document_type == DocumentType.DR:
            for line in entry.lines:
                if line.debit_credit == DebitCredit.DEBIT and line.customer_id:
                    self.customer_ar_balances[line.customer_id] += line.amount
                    self.open_items.append(
                        OpenItem(
                            company_code=entry.company_code,
                            account_number=line.account_code,
                            partner_id=line.customer_id,
                            partner_name=f"Customer_{line.customer_id}",
                            document_number=entry.document_number,
                            posting_date=entry.posting_date,
                            amount=line.amount,
                            currency=line.currency,
                            debit_credit=DebitCredit.DEBIT,
                            is_cleared=False,
                        )
                    )

        # If Vendor Payment (KZ) -> Match and clear open AP item
        elif entry.document_type == DocumentType.KZ:
            for line in entry.lines:
                if line.debit_credit == DebitCredit.DEBIT and line.vendor_id:
                    for item in self.open_items:
                        if (
                            not item.is_cleared
                            and item.partner_id == line.vendor_id
                            and item.debit_credit == DebitCredit.CREDIT
                        ):
                            item.is_cleared = True
                            item.clearing_doc = entry.document_number
                            break

        # If Customer Payment (DZ) -> Match and clear open AR item and reduce AR exposure
        elif entry.document_type == DocumentType.DZ:
            for line in entry.lines:
                if line.debit_credit == DebitCredit.CREDIT and line.customer_id:
                    self.customer_ar_balances[line.customer_id] = max(
                        Decimal("0.00"), self.customer_ar_balances[line.customer_id] - line.amount
                    )
                    for item in self.open_items:
                        if (
                            not item.is_cleared
                            and item.partner_id == line.customer_id
                            and item.debit_credit == DebitCredit.DEBIT
                        ):
                            item.is_cleared = True
                            item.clearing_doc = entry.document_number
                            break

        latency = int((time.perf_counter() - start) * 1000)
        return ERPPostingResult(
            success=True,
            document_number=entry.document_number,
            fiscal_year=entry.fiscal_year,
            status_code=200,
            latency_ms=latency,
            raw_response={"status": "POSTED", "document": entry.document_number},
        )
