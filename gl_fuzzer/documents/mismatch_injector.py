"""Multimodal Mismatch Injector: Pairs unstructured documents with GL vouchers and injects discrepancies."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple

from gl_fuzzer.models.journal import JournalEntry, LineItem, DocumentType, DebitCredit
from gl_fuzzer.documents.models import (
    DocumentItemLine,
    DocumentMismatchType,
    SyntheticDocumentResult,
    SyntheticInvoiceData,
)
from gl_fuzzer.documents.pdf_generator import FinancialPDFGenerator


class MultimodalMismatchInjector:
    """Pairs unstructured PDF invoices with structured GL journal entries and injects multimodal fraud."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.pdf_gen = FinancialPDFGenerator()

    def generate_invoice_for_entry(
        self,
        entry: JournalEntry,
        output_pdf_path: Path,
        mismatch: DocumentMismatchType = DocumentMismatchType.NO_MISMATCH,
    ) -> Tuple[SyntheticDocumentResult, JournalEntry]:
        """Generates a PDF invoice synchronized with a JournalEntry, optionally injecting discrepancies."""
        total_amt = entry.total_debits
        vendor_name = entry.header_text or "Apex Logistics Corporation"
        inv_num = entry.reference or f"INV-{entry.document_number}"

        items = [
            DocumentItemLine(
                item_no=1,
                description="Industrial Equipment Subassembly Components",
                quantity=Decimal("1"),
                unit_price=total_amt,
                total_price=total_amt,
            )
        ]

        inv_data = SyntheticInvoiceData(
            invoice_number=inv_num,
            invoice_date=entry.posting_date,
            vendor_name=vendor_name,
            vendor_tax_id="12-3456781",
            vendor_routing="021000021",
            vendor_account="123456789",
            customer_name=f"Enterprise Legal Entity {entry.company_code}",
            currency="USD",
            items=items,
            subtotal=total_amt,
            tax_rate=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=total_amt,
            mismatch_type=mismatch,
        )

        # Apply specific mismatch injection
        if mismatch == DocumentMismatchType.OCR_AMOUNT_MISMATCH:
            # PDF invoice states higher amount than recorded in ledger
            tampered_total = total_amt + Decimal("2500.00")
            inv_data.total_amount = tampered_total
            inv_data.items[0].total_price = tampered_total
            inv_data.subtotal = tampered_total
            inv_data.mismatch_details = (
                f"OCR Discrepancy: Physical PDF displays ${tampered_total:,.2f}, "
                f"while structured ERP voucher {entry.document_number} only booked ${total_amt:,.2f}"
            )
            entry.is_anomaly = True
            entry.anomaly_ids.append("OCR_AMOUNT_MISMATCH")

        elif mismatch == DocumentMismatchType.IBAN_MISMATCH:
            rogue_account = "998877665"
            inv_data.vendor_account = "123456789"  # Legitimate
            inv_data.mismatch_details = (
                f"Wire Diversion: PDF states legitimate Account 123456789, "
                f"but disbursement lines routed payment to unverified rogue account {rogue_account}"
            )
            entry.is_anomaly = True
            entry.anomaly_ids.append("IBAN_MISMATCH")

        doc_result = self.pdf_gen.generate_invoice_pdf(inv_data, output_pdf_path)
        return doc_result, entry
