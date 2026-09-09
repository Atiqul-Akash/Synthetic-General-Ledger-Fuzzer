"""Models for Unstructured Financial Context and Multimodal Artifact Generation."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentArtifactType(str, Enum):
    """Types of synthetic unstructured financial documents."""
    INVOICE_PDF = "INVOICE_PDF"
    WAYBILL_PDF = "WAYBILL_PDF"
    EMAIL_APPROVAL_THREAD = "EMAIL_APPROVAL_THREAD"


class DocumentMismatchType(str, Enum):
    """Types of multimodal discrepancies between document and structured GL entry."""
    NO_MISMATCH = "NO_MISMATCH"
    OCR_AMOUNT_MISMATCH = "OCR_AMOUNT_MISMATCH"
    IBAN_MISMATCH = "IBAN_MISMATCH"
    GHOST_LINE_ITEM = "GHOST_LINE_ITEM"
    POST_DATED_SIGNATURE = "POST_DATED_SIGNATURE"


class DocumentItemLine(BaseModel):
    """Single itemized line within a financial document."""
    item_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal


class SyntheticInvoiceData(BaseModel):
    """Extracted or rendered invoice content metadata."""
    invoice_number: str
    invoice_date: str
    vendor_name: str
    vendor_tax_id: str
    vendor_routing: str
    vendor_account: str
    customer_name: str
    currency: str = "USD"
    items: List[DocumentItemLine] = Field(default_factory=list)
    subtotal: Decimal
    tax_rate: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal
    mismatch_type: DocumentMismatchType = DocumentMismatchType.NO_MISMATCH
    mismatch_details: Optional[str] = None


class SyntheticDocumentResult(BaseModel):
    """Result of document generation containing file metadata and ground-truth mismatches."""
    document_type: DocumentArtifactType
    file_path: Path
    file_size_bytes: int
    invoice_data: Optional[SyntheticInvoiceData] = None
    email_subject: Optional[str] = None
    is_mismatched: bool = False
    mismatch_type: DocumentMismatchType = DocumentMismatchType.NO_MISMATCH
    mismatch_summary: str = ""
