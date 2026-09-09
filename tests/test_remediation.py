"""Tests for Automated Remediation Oracles and the Healing Loop."""

from decimal import Decimal
import pytest

from gl_fuzzer.models.journal import JournalEntry, LineItem, DocumentType, DebitCredit
from gl_fuzzer.remediation.models import RemediationTargetType, PatchVerificationStatus
from gl_fuzzer.remediation.engine import RemediationAdvisor
from gl_fuzzer.remediation.healing_loop import HealingLoopRunner


def _create_sample_entry(doc_type, lines=None, header="Test"):
    entry_id = "ENT-TEST-001"
    if lines is None:
        lines = [
            LineItem(line_id=f"{entry_id}-1", entry_id=entry_id, line_number=1, account_code="20000",
                     debit_credit=DebitCredit.DEBIT, amount=Decimal("1000.00"),
                     amount_local=Decimal("1000.00"), amount_group=Decimal("1000.00"), currency="USD"),
            LineItem(line_id=f"{entry_id}-2", entry_id=entry_id, line_number=2, account_code="10100",
                     debit_credit=DebitCredit.CREDIT, amount=Decimal("1000.00"),
                     amount_local=Decimal("1000.00"), amount_group=Decimal("1000.00"), currency="USD"),
        ]
    return JournalEntry(
        entry_id=entry_id,
        batch_id="BATCH-001",
        company_code="1000",
        fiscal_year=2026,
        document_type=doc_type,
        document_number="1500000001",
        posting_date="2026-03-15",
        document_date="2026-03-15",
        created_at="2026-03-15T09:30:00",
        lines=lines,
        header_text=header,
    )


def test_remediation_wht_evasion():
    finding = {
        "finding_type": "TAX_EVASION_ZERO_WHT",
        "description": "Vendor payment disbursed without mandatory statutory withholding tax deduction",
        "finding_id": "FIND_WHT_01",
    }
    patch = RemediationAdvisor.advise_for_finding(finding)
    assert patch.target_type == RemediationTargetType.SAP_SUBST_RULE
    assert "22200" in patch.code_or_rule
    assert len(patch.compensating_controls) == 1
    assert patch.compensating_controls[0].sox_reference == "SOX-404-TAX-WHT"

    # Test Healing Loop
    bad_entry = _create_sample_entry(DocumentType.KZ, header="Vendor Payment Missing WHT")
    res = HealingLoopRunner.verify_patch(patch, attack_entry=bad_entry)
    assert res.is_healed is True
    assert res.status == PatchVerificationStatus.VERIFIED_HEALED
    assert patch.verification_status == PatchVerificationStatus.VERIFIED_HEALED


def test_remediation_phantom_po():
    finding = {
        "finding_type": "PHANTOM_PO_THREE_WAY_BYPASS",
        "description": "Invoice cleared without matching Goods Receipt",
        "finding_id": "FIND_3WM_01",
    }
    patch = RemediationAdvisor.advise_for_finding(finding)
    assert patch.target_type == RemediationTargetType.SAP_ABAP_BADI
    assert "BADI_ACC_DOCUMENT" in patch.code_or_rule

    bad_entry = _create_sample_entry(DocumentType.RE, header="PHANTOM PO invoice bypass")
    res = HealingLoopRunner.verify_patch(patch, attack_entry=bad_entry)
    assert res.is_healed is True
    assert res.exploit_blocked is True


def test_remediation_inventory_shrinkage():
    finding = {
        "finding_type": "INVENTORY_SHRINKAGE_CONCEALMENT",
        "description": "Inventory written down directly to suspense account 99999",
        "finding_id": "FIND_SHRINK_01",
    }
    patch = RemediationAdvisor.advise_for_finding(finding)
    assert patch.target_type == RemediationTargetType.SQL_CONSTRAINT
    assert "chk_inventory_clearing" in patch.code_or_rule

    lines = [
        LineItem(line_id="L1", entry_id="ENT-1", line_number=1, account_code="99999",
                 debit_credit=DebitCredit.DEBIT, amount=Decimal("5000.00"),
                 amount_local=Decimal("5000.00"), amount_group=Decimal("5000.00"), currency="USD"),
        LineItem(line_id="L2", entry_id="ENT-1", line_number=2, account_code="14000",
                 debit_credit=DebitCredit.CREDIT, amount=Decimal("5000.00"),
                 amount_local=Decimal("5000.00"), amount_group=Decimal("5000.00"), currency="USD"),
    ]
    bad_entry = _create_sample_entry(DocumentType.SA, lines=lines)
    res = HealingLoopRunner.verify_patch(patch, attack_entry=bad_entry)
    assert res.is_healed is True


def test_remediation_sql_injection():
    finding = {
        "finding_type": "SQL_INJECTION",
        "description": "Unhandled database crash on single-quote injection in document reference",
        "finding_id": "FIND_SQLI_01",
    }
    patch = RemediationAdvisor.advise_for_finding(finding)
    assert patch.target_type == RemediationTargetType.SQL_CONSTRAINT
    assert "bind" in patch.code_or_rule or "parameter" in patch.explanation.lower()

    res = HealingLoopRunner.verify_patch(patch)
    assert res.is_healed is True
