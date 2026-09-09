"""Tests for extended Forensic Audit Evaluator methods.

Validates detection of:
- Withholding tax evasion (zero WHT deduction)
- Phantom purchase order 3-way match bypass
- Concealed inventory shrinkage write-downs
- Streaming feed replay attacks
"""

from decimal import Decimal
import pytest

from gl_fuzzer.models.journal import JournalEntry, LineItem, DocumentType, DebitCredit
from gl_fuzzer.verification.audit_metrics import ForensicAuditEvaluator


def _create_sample_entry(doc_type, doc_num, lines=None, is_anomaly=False, anomaly_ids=None, ref="PO-100", header="Test"):
    entry_id = f"ENT-{doc_num}"
    if lines is None:
        lines = [
            LineItem(line_id=f"{entry_id}-1", entry_id=entry_id, line_number=1, account_code="10000",
                     debit_credit=DebitCredit.DEBIT, amount=Decimal("1000.00"),
                     amount_local=Decimal("1000.00"), amount_group=Decimal("1000.00"), currency="USD"),
            LineItem(line_id=f"{entry_id}-2", entry_id=entry_id, line_number=2, account_code="20000",
                     debit_credit=DebitCredit.CREDIT, amount=Decimal("1000.00"),
                     amount_local=Decimal("1000.00"), amount_group=Decimal("1000.00"), currency="USD"),
        ]
    return JournalEntry(
        entry_id=entry_id,
        batch_id="BATCH-001",
        company_code="1000",
        fiscal_year=2026,
        document_type=doc_type,
        document_number=doc_num,
        posting_date="2026-03-15",
        document_date="2026-03-15",
        created_at="2026-03-15T09:30:00",
        lines=lines,
        reference=ref,
        header_text=header,
        is_anomaly=is_anomaly,
        anomaly_ids=anomaly_ids or [],
    )


def test_detect_wht_evasion_clean():
    """Validates that a compliant payment with WHT line is not flagged as evasion."""
    entry_id = "ENT-1500000001"
    lines = [
        LineItem(line_id=f"{entry_id}-1", entry_id=entry_id, line_number=1, account_code="20000",
                 debit_credit=DebitCredit.DEBIT, amount=Decimal("1000.00"),
                 amount_local=Decimal("1000.00"), amount_group=Decimal("1000.00"), currency="USD"),
        LineItem(line_id=f"{entry_id}-2", entry_id=entry_id, line_number=2, account_code="10000",
                 debit_credit=DebitCredit.CREDIT, amount=Decimal("900.00"),
                 amount_local=Decimal("900.00"), amount_group=Decimal("900.00"), currency="USD"),
        LineItem(line_id=f"{entry_id}-3", entry_id=entry_id, line_number=3, account_code="22200",
                 debit_credit=DebitCredit.CREDIT, amount=Decimal("100.00"),
                 amount_local=Decimal("100.00"), amount_group=Decimal("100.00"), currency="USD"),
    ]
    entry = _create_sample_entry(DocumentType.KZ, "1500000001", lines=lines, header="Vendor Payment WHT compliant")
    res = ForensicAuditEvaluator.detect_wht_evasion([entry])
    assert res["has_wht_evasion"] is False
    assert res["flagged_wht_evasion_count"] == 0


def test_detect_wht_evasion_flagged_by_anomaly_id():
    """Validates that an entry flagged with TAX_EVASION_ZERO_WHT is detected."""
    entry = _create_sample_entry(
        DocumentType.KZ, "1500000002",
        is_anomaly=True,
        anomaly_ids=["TAX_EVASION_ZERO_WHT"],
        header="Bypassed withholding tax",
    )
    res = ForensicAuditEvaluator.detect_wht_evasion([entry])
    assert res["has_wht_evasion"] is True
    assert res["flagged_wht_evasion_count"] == 1
    assert res["flagged_disbursements"][0]["document_number"] == "1500000002"


def test_detect_wht_evasion_flagged_by_rule():
    """Validates that a large payment mentioning WHT but lacking account 22200 is flagged."""
    entry_id = "ENT-1500000003"
    lines = [
        LineItem(line_id=f"{entry_id}-1", entry_id=entry_id, line_number=1, account_code="20000",
                 debit_credit=DebitCredit.DEBIT, amount=Decimal("5000.00"),
                 amount_local=Decimal("5000.00"), amount_group=Decimal("5000.00"), currency="USD"),
        LineItem(line_id=f"{entry_id}-2", entry_id=entry_id, line_number=2, account_code="10000",
                 debit_credit=DebitCredit.CREDIT, amount=Decimal("5000.00"),
                 amount_local=Decimal("5000.00"), amount_group=Decimal("5000.00"), currency="USD"),
    ]
    entry = _create_sample_entry(DocumentType.KZ, "1500000003", lines=lines, header="WHT services payment full")
    res = ForensicAuditEvaluator.detect_wht_evasion([entry])
    assert res["has_wht_evasion"] is True
    assert res["flagged_wht_evasion_count"] == 1


def test_detect_phantom_po_bypass_clean():
    """Validates that a 3-way match with matching Goods Receipt (WE) passes."""
    gr_entry = _create_sample_entry(DocumentType.WE, "5000000001", ref="PO-999", header="Goods Receipt")
    inv_entry = _create_sample_entry(DocumentType.RE, "5100000001", ref="PO-999", header="Vendor Invoice Match")
    res = ForensicAuditEvaluator.detect_phantom_po_bypass([gr_entry, inv_entry])
    assert res["has_phantom_po_violations"] is False
    assert res["flagged_phantom_invoices_count"] == 0


def test_detect_phantom_po_bypass_flagged():
    """Validates that a vendor invoice without matching GR and with phantom characteristics is caught."""
    inv_entry = _create_sample_entry(
        DocumentType.RE, "5100000002",
        ref="PO-PHANTOM-888",
        header="PHANTOM PO Direct Invoicing",
        is_anomaly=True,
        anomaly_ids=["PHANTOM_PO_THREE_WAY_BYPASS"],
    )
    res = ForensicAuditEvaluator.detect_phantom_po_bypass([inv_entry])
    assert res["has_phantom_po_violations"] is True
    assert res["flagged_phantom_invoices_count"] == 1
    assert res["flagged_invoices"][0]["po_reference"] == "PO-PHANTOM-888"


def test_detect_inventory_shrinkage_concealment_clean():
    """Validates that standard COGS reduction does not trigger shrinkage flags."""
    entry_id = "ENT-4900000001"
    lines = [
        LineItem(line_id=f"{entry_id}-1", entry_id=entry_id, line_number=1, account_code="50000",
                 debit_credit=DebitCredit.DEBIT, amount=Decimal("300.00"),
                 amount_local=Decimal("300.00"), amount_group=Decimal("300.00"), currency="USD"),
        LineItem(line_id=f"{entry_id}-2", entry_id=entry_id, line_number=2, account_code="14000",
                 debit_credit=DebitCredit.CREDIT, amount=Decimal("300.00"),
                 amount_local=Decimal("300.00"), amount_group=Decimal("300.00"), currency="USD"),
    ]
    entry = _create_sample_entry(DocumentType.GI, "4900000001", lines=lines, header="Goods Issue to Cost Center")
    res = ForensicAuditEvaluator.detect_inventory_shrinkage_concealment([entry])
    assert res["has_shrinkage_anomalies"] is False
    assert res["flagged_shrinkage_count"] == 0


def test_detect_inventory_shrinkage_concealment_flagged():
    """Validates that inventory credited into suspense (99999) triggers a fraud flag."""
    entry_id = "ENT-1000000099"
    lines = [
        LineItem(line_id=f"{entry_id}-1", entry_id=entry_id, line_number=1, account_code="99999",
                 debit_credit=DebitCredit.DEBIT, amount=Decimal("12000.00"),
                 amount_local=Decimal("12000.00"), amount_group=Decimal("12000.00"), currency="USD"),
        LineItem(line_id=f"{entry_id}-2", entry_id=entry_id, line_number=2, account_code="14000",
                 debit_credit=DebitCredit.CREDIT, amount=Decimal("12000.00"),
                 amount_local=Decimal("12000.00"), amount_group=Decimal("12000.00"), currency="USD"),
    ]
    entry = _create_sample_entry(DocumentType.SA, "1000000099", lines=lines, header="Inventory balancing adjustment")
    res = ForensicAuditEvaluator.detect_inventory_shrinkage_concealment([entry])
    assert res["has_shrinkage_anomalies"] is True
    assert res["flagged_shrinkage_count"] == 1


def test_detect_streaming_replay_attack_clean():
    """Validates unique document numbers show no replay attack."""
    e1 = _create_sample_entry(DocumentType.SA, "1000000001")
    e2 = _create_sample_entry(DocumentType.SA, "1000000002")
    res = ForensicAuditEvaluator.detect_streaming_replay_attack([e1, e2])
    assert res["has_replay_attack"] is False
    assert res["duplicate_documents_count"] == 0


def test_detect_streaming_replay_attack_flagged():
    """Validates that duplicated document numbers in stream trigger replay warning."""
    e1 = _create_sample_entry(DocumentType.SA, "1000000001")
    e2 = _create_sample_entry(DocumentType.SA, "1000000002")
    e3 = _create_sample_entry(DocumentType.SA, "1000000001")  # Replayed duplicate
    res = ForensicAuditEvaluator.detect_streaming_replay_attack([e1, e2, e3])
    assert res["has_replay_attack"] is True
    assert res["duplicate_documents_count"] == 1
    assert "1000000001" in res["duplicate_document_numbers"]
