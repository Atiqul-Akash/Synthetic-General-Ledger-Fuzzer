"""Double-entry Journal Entry and Ledger models with exact decimal precision."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DebitCredit(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class DocumentType(str, Enum):
    SA = "SA"  # Standard G/L Account Document
    KR = "KR"  # Vendor Invoice (P2P)
    KZ = "KZ"  # Vendor Payment (P2P)
    DR = "DR"  # Customer Invoice (O2C)
    DZ = "DZ"  # Customer Payment (O2C)
    WA = "WA"  # Goods Issue (O2C)
    WE = "WE"  # Goods Receipt (P2P)
    MJE = "MJE"  # Manual Adjusting Journal Entry
    IC = "IC"  # Intercompany Transfer Document


class LineItem(BaseModel):
    """Represents a single debit or credit line in a journal entry (SAP BSEG equivalent)."""
    line_id: str = Field(..., description="Unique line item identifier")
    entry_id: str = Field(..., description="Parent document identifier")
    line_number: int = Field(..., description="Item sequence number within document (BUZEI)")
    account_code: str = Field(..., description="GL account number (HKONT)")
    account_name: str = Field(default="", description="Account name description")
    debit_credit: DebitCredit = Field(..., description="DEBIT or CREDIT indicator (SHKZG: S=Debit, H=Credit)")
    amount: Decimal = Field(..., description="Monetary amount in document currency (WRBTR)")
    currency: str = Field(default="USD", description="Currency code (WAERS)")
    posting_key: str = Field(default="40", description="SAP Posting Key (BSCHL: 40=Debit GL, 50=Credit GL, etc.)")
    cost_center: Optional[str] = Field(default=None, description="Cost Center (KOSTL)")
    profit_center: Optional[str] = Field(default=None, description="Profit Center (PRCTR)")
    vendor_id: Optional[str] = Field(default=None, description="Vendor master ID (LIFNR)")
    customer_id: Optional[str] = Field(default=None, description="Customer master ID (KUNNR)")
    trading_partner: Optional[str] = Field(default=None, description="Trading partner company code for intercompany (VBUND)")
    line_text: str = Field(default="", description="Item text (SGTXT)")
    tax_code: Optional[str] = Field(default=None, description="Sales/Purchase Tax Code (MWSKZ)")

    def model_post_init(self, __context) -> None:
        # Quantize amount to exactly 2 decimal places to prevent floating-point drift
        object.__setattr__(self, 'amount', self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        # Ensure correct SAP posting key default if not explicitly provided
        if self.posting_key in ("40", "50"):
            expected_key = "40" if self.debit_credit == DebitCredit.DEBIT else "50"
            object.__setattr__(self, 'posting_key', expected_key)


class JournalEntry(BaseModel):
    """Represents a multi-leg double-entry journal voucher (SAP BKPF header + BSEG items)."""
    entry_id: str = Field(..., description="Unique document ID (BELNR / UUID)")
    batch_id: str = Field(..., description="Batch identifier")
    company_code: str = Field(default="1000", description="Company code / legal entity (BUKRS)")
    fiscal_year: int = Field(default=2026, description="Fiscal year (GJAHR)")
    fiscal_period: int = Field(default=9, description="Fiscal posting period (MONAT)")
    document_type: DocumentType = Field(default=DocumentType.SA, description="Document type (BLART)")
    document_number: str = Field(..., description="Accounting document number")
    posting_date: str = Field(..., description="Posting date YYYY-MM-DD (BUDAT)")
    document_date: str = Field(..., description="Document date YYYY-MM-DD (BLDAT)")
    entry_time: str = Field(default="09:30:00", description="Entry timestamp HH:MM:SS (CPUTM)")
    created_at: str = Field(..., description="Full ISO timestamp of creation")
    created_by: str = Field(default="SYSTEM_AUTO", description="User ID / Service account (USNAM)")
    reference: str = Field(default="", description="Reference document number (XBLNR)")
    header_text: str = Field(default="", description="Document header text (BKTXT)")
    business_cycle: str = Field(default="R2R", description="Originating accounting cycle (P2P, O2C, R2R)")
    lines: List[LineItem] = Field(default_factory=list, description="Line item legs")
    is_anomaly: bool = Field(default=False, description="Whether this entry contains an injected anomaly")
    anomaly_ids: List[str] = Field(default_factory=list, description="IDs of anomalies affecting this entry")

    @property
    def total_debits(self) -> Decimal:
        """Total debit sum rounded to cents."""
        debits = [line.amount for line in self.lines if line.debit_credit == DebitCredit.DEBIT]
        total = sum(debits, Decimal("0.00"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_credits(self) -> Decimal:
        """Total credit sum rounded to cents."""
        credits = [line.amount for line in self.lines if line.debit_credit == DebitCredit.CREDIT]
        total = sum(credits, Decimal("0.00"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def balance_delta(self) -> Decimal:
        """Difference between debits and credits. Must equal 0.00 for balanced entries."""
        return (self.total_debits - self.total_credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def is_balanced(self) -> bool:
        """Double-entry invariant: Total Debits == Total Credits."""
        return self.balance_delta == Decimal("0.00")


class Batch(BaseModel):
    """Collection of journal entries posted together as an atomic processing batch."""
    batch_id: str
    source_system: str = "SAP_ERP_FI"
    created_at: str
    entries: List[JournalEntry] = Field(default_factory=list)

    @property
    def total_debits(self) -> Decimal:
        total = sum((entry.total_debits for entry in self.entries), Decimal("0.00"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_credits(self) -> Decimal:
        total = sum((entry.total_credits for entry in self.entries), Decimal("0.00"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits

    @property
    def total_line_count(self) -> int:
        return sum(len(entry.lines) for entry in self.entries)
