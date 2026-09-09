"""Tests for Unstructured Financial Context and Multimodal Artifact Generation."""

from decimal import Decimal
from pathlib import Path
import tempfile
import pytest

from gl_fuzzer.models.journal import JournalEntry, LineItem, DocumentType, DebitCredit
from gl_fuzzer.documents.models import DocumentArtifactType, DocumentMismatchType, SyntheticInvoiceData, DocumentItemLine
from gl_fuzzer.documents.pdf_generator import FinancialPDFGenerator
from gl_fuzzer.documents.email_generator import EmailThreadGenerator
from gl_fuzzer.documents.mismatch_injector import MultimodalMismatchInjector


def _create_sample_entry():
    entry_id = "ENT-DOC-TEST"
    lines = [
        LineItem(line_id=f"{entry_id}-1", entry_id=entry_id, line_number=1, account_code="50000",
                 debit_credit=DebitCredit.DEBIT, amount=Decimal("12000.00"),
                 amount_local=Decimal("12000.00"), amount_group=Decimal("12000.00"), currency="USD"),
        LineItem(line_id=f"{entry_id}-2", entry_id=entry_id, line_number=2, account_code="20000",
                 debit_credit=DebitCredit.CREDIT, amount=Decimal("12000.00"),
                 amount_local=Decimal("12000.00"), amount_group=Decimal("12000.00"), currency="USD"),
    ]
    return JournalEntry(
        entry_id=entry_id, batch_id="B1", company_code="1000", fiscal_year=2026,
        document_type=DocumentType.KR, document_number="1900000555", posting_date="2026-03-20",
        document_date="2026-03-20", created_at="2026-03-20T10:00:00", reference="INV-TEST-555",
        header_text="Precision Tooling & Equipment Inc", lines=lines,
    )


def test_pure_python_pdf_invoice_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = Path(tmpdir) / "test_invoice.pdf"
        gen = FinancialPDFGenerator()

        inv_data = SyntheticInvoiceData(
            invoice_number="INV-2026-001",
            invoice_date="2026-03-15",
            vendor_name="Apex Logistics Corporation",
            vendor_tax_id="12-3456781",
            vendor_routing="021000021",
            vendor_account="123456789",
            customer_name="Enterprise Holdings Inc",
            subtotal=Decimal("5000.00"),
            total_amount=Decimal("5000.00"),
            items=[
                DocumentItemLine(
                    item_no=1, description="Standard Logistics Freight Handling",
                    quantity=Decimal("1"), unit_price=Decimal("5000.00"), total_price=Decimal("5000.00")
                )
            ]
        )

        res = gen.generate_invoice_pdf(inv_data, out_pdf)
        assert out_pdf.exists()
        assert res.file_size_bytes > 500
        assert res.document_type == DocumentArtifactType.INVOICE_PDF

        # Verify PDF header magic bytes
        with open(out_pdf, "rb") as f:
            header = f.read(8)
            assert header.startswith(b"%PDF-1.4")


def test_synthetic_cfo_email_thread():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_eml = Path(tmpdir) / "cfo_override.eml"
        res = EmailThreadGenerator.generate_cfo_override_thread(out_eml, amount="$9,950.00")

        assert out_eml.exists()
        assert res.document_type == DocumentArtifactType.EMAIL_APPROVAL_THREAD
        assert "URGENT" in res.email_subject
        assert res.is_mismatched is True

        content = out_eml.read_text(encoding="utf-8")
        assert "Arthur Pendelton" in content
        assert "Chief Financial Officer" in content


def test_multimodal_ocr_amount_mismatch_injection():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = Path(tmpdir) / "mismatched_invoice.pdf"
        entry = _create_sample_entry()

        injector = MultimodalMismatchInjector(seed=42)
        doc_res, entry = injector.generate_invoice_for_entry(
            entry, out_pdf, mismatch=DocumentMismatchType.OCR_AMOUNT_MISMATCH
        )

        assert out_pdf.exists()
        assert doc_res.is_mismatched is True
        assert doc_res.mismatch_type == DocumentMismatchType.OCR_AMOUNT_MISMATCH
        assert entry.is_anomaly is True
        assert "OCR_AMOUNT_MISMATCH" in entry.anomaly_ids
        assert doc_res.invoice_data.total_amount != entry.total_debits


def test_detect_multimodal_document_mismatches_audit():
    with tempfile.TemporaryDirectory() as tmpdir:
        from gl_fuzzer.verification.audit_metrics import ForensicAuditEvaluator

        entry = _create_sample_entry()
        out_pdf = Path(tmpdir) / "test_mismatch.pdf"
        injector = MultimodalMismatchInjector(seed=42)
        doc_res, entry = injector.generate_invoice_for_entry(
            entry, out_pdf, mismatch=DocumentMismatchType.OCR_AMOUNT_MISMATCH
        )

        pairs = [(entry, doc_res)]
        audit_res = ForensicAuditEvaluator.detect_multimodal_document_mismatches(pairs)

        assert audit_res["total_pairs_checked"] == 1
        assert audit_res["flagged_mismatches_count"] == 1
        assert audit_res["has_multimodal_mismatches"] is True
        assert audit_res["flagged_mismatches"][0]["mismatch_type"] == "OCR_AMOUNT_MISMATCH"
        assert audit_res["flagged_mismatches"][0]["discrepancy"] == "2500.00"

