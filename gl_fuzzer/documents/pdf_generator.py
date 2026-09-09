"""Pure-Python zero-dependency PDF generator for synthetic financial invoices and waybills."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from gl_fuzzer.documents.models import (
    DocumentArtifactType,
    DocumentItemLine,
    DocumentMismatchType,
    SyntheticDocumentResult,
    SyntheticInvoiceData,
)


class MinimalPDFBuilder:
    """Zero-dependency pure-Python PDF 1.4 document composer."""

    def __init__(self):
        self.objects: List[bytes] = []

    def _add_object(self, content: bytes) -> int:
        self.objects.append(content)
        return len(self.objects)

    def build_invoice_pdf(self, invoice: SyntheticInvoiceData, output_path: Path) -> int:
        """Renders standard invoice layout into a compliant PDF 1.4 binary file."""
        # Sanitize text lines for PDF text string literal
        def _esc(s: str) -> str:
            return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        # Text stream commands (Coordinates: 0,0 is bottom-left; 612x792 is Letter)
        cmds: List[str] = [
            "BT",
            # Header
            "/F1 18 Tf",
            "50 740 Td",
            f"({_esc(invoice.vendor_name.upper())}) Tj",
            "/F2 9 Tf",
            "0 -16 Td",
            f"(Tax ID / EIN: {_esc(invoice.vendor_tax_id)}) Tj",
            "0 -12 Td",
            f"(Bank Wire Routing: {_esc(invoice.vendor_routing)} | Account: {_esc(invoice.vendor_account)}) Tj",
            # Invoice Info Box
            "/F1 14 Tf",
            "340 28 Td",  # Move right
            f"(COMMERCIAL INVOICE) Tj",
            "/F2 10 Tf",
            "0 -16 Td",
            f"(Invoice Number: {_esc(invoice.invoice_number)}) Tj",
            "0 -14 Td",
            f"(Invoice Date: {_esc(invoice.invoice_date)}) Tj",
            "0 -14 Td",
            f"(Payment Terms: Net 30 Days) Tj",
            # Bill To
            "/F1 11 Tf",
            "-340 -40 Td",
            "(BILLED TO:) Tj",
            "/F2 10 Tf",
            "0 -14 Td",
            f"({_esc(invoice.customer_name)}) Tj",
            # Table Header
            "/F1 10 Tf",
            "0 -30 Td",
            "(#   Description                                      Qty    Unit Price        Total) Tj",
            "/F2 9 Tf",
            "0 -6 Td",
            "(--------------------------------------------------------------------------------------------------) Tj",
        ]

        # Item rows
        curr_y_step = -16
        for item in invoice.items:
            desc_pad = f"{item.description:<42}"[:42]
            line_str = f"{item.item_no:<3} {desc_pad} {item.quantity:>4}  ${item.unit_price:>10.2f}  ${item.total_price:>11.2f}"
            cmds.extend([
                f"0 {curr_y_step} Td",
                f"({_esc(line_str)}) Tj",
            ])

        # Subtotal and Total
        cmds.extend([
            "0 -10 Td",
            "(--------------------------------------------------------------------------------------------------) Tj",
            "/F2 10 Tf",
            f"240 -18 Td",
            f"(Subtotal:      ${invoice.subtotal:>12.2f}) Tj",
            f"0 -14 Td",
            f"(Sales Tax:     ${invoice.tax_amount:>12.2f}) Tj",
            "/F1 12 Tf",
            f"0 -18 Td",
            f"(TOTAL DUE:     ${invoice.total_amount:>12.2f} {invoice.currency}) Tj",
            # Footer notice
            "/F2 8 Tf",
            "-240 -50 Td",
            "(Please remit payment according to wire instructions above. Electronic processing standard RFC-4180.) Tj",
            "ET",
        ])

        stream_data = "\n".join(cmds).encode("latin1", errors="replace")
        stream_len = len(stream_data)

        # PDF Object Assembly
        # Obj 1: Catalog
        # Obj 2: Pages
        # Obj 3: Page
        # Obj 4: Content Stream
        # Obj 5: Font Bold (Courier-Bold for exact monospace column alignment)
        # Obj 6: Font Regular (Courier)
        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        obj3 = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>"
        )
        obj4 = f"<< /Length {stream_len} >>\nstream\n".encode("latin1") + stream_data + b"\nendstream"
        obj5 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>"
        obj6 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"

        objs = [obj1, obj2, obj3, obj4, obj5, obj6]

        # Build output binary with xref table
        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        body = bytearray(header)
        offsets = []

        for i, obj in enumerate(objs, 1):
            offsets.append(len(body))
            body.extend(f"{i} 0 obj\n".encode("latin1"))
            body.extend(obj)
            body.extend(b"\nendobj\n")

        xref_offset = len(body)
        body.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode("latin1"))
        for off in offsets:
            body.extend(f"{off:010d} 00000 n \n".encode("latin1"))

        trailer = (
            f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin1")
        body.extend(trailer)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(body)

        return len(body)


class FinancialPDFGenerator:
    """Generates synthetic financial PDFs linked directly to GL voucher datasets."""

    def __init__(self):
        self.builder = MinimalPDFBuilder()

    def generate_invoice_pdf(
        self,
        invoice_data: SyntheticInvoiceData,
        output_file: Path,
    ) -> SyntheticDocumentResult:
        """Compiles invoice metadata and writes standard PDF document to disk."""
        size_bytes = self.builder.build_invoice_pdf(invoice_data, output_file)

        is_mismatched = invoice_data.mismatch_type != DocumentMismatchType.NO_MISMATCH
        summary = invoice_data.mismatch_details or ("Compliant invoice document matching GL entry." if not is_mismatched else "")

        return SyntheticDocumentResult(
            document_type=DocumentArtifactType.INVOICE_PDF,
            file_path=output_file,
            file_size_bytes=size_bytes,
            invoice_data=invoice_data,
            is_mismatched=is_mismatched,
            mismatch_type=invoice_data.mismatch_type,
            mismatch_summary=summary,
        )
