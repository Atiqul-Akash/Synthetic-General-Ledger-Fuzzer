"""Remediation Advisor: Generates concrete ERP and database patches for identified audit gaps."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from gl_fuzzer.remediation.models import (
    CompensatingControl,
    PatchVerificationStatus,
    RemediationPatch,
    RemediationTargetType,
)


class RemediationAdvisor:
    """Expert system producing deployable ERP patches, SQL constraints, and SOX controls."""

    @classmethod
    def advise_for_finding(cls, finding: Dict[str, Any]) -> RemediationPatch:
        """Analyzes a vulnerability or audit breach and generates a self-contained RemediationPatch."""
        ftype = str(finding.get("finding_type", "")).upper()
        desc = str(finding.get("description", ""))
        vuln_id = str(finding.get("finding_id", f"VULN_{hashlib.md5(desc.encode()).hexdigest()[:8]}"))

        if "ZERO_WHT" in ftype or "TAX_EVASION" in ftype or "WHT" in desc.upper():
            return cls._remediate_wht_evasion(vuln_id, desc)
        elif "PHANTOM_PO" in ftype or "THREE_WAY" in ftype or "3-WAY" in desc.upper():
            return cls._remediate_phantom_po(vuln_id, desc)
        elif "SHRINKAGE" in ftype or "INVENTORY" in desc.upper():
            return cls._remediate_inventory_shrinkage(vuln_id, desc)
        elif "SQL" in ftype or "INJECTION" in desc.upper():
            return cls._remediate_sql_injection(vuln_id, desc)
        elif "DOA" in ftype or "SMURFING" in ftype or "SPLIT" in desc.upper():
            return cls._remediate_doa_smurfing(vuln_id, desc)
        elif "ROUND_TRIP" in ftype or "CIRCULAR" in desc.upper() or "INTERCOMPANY" in desc.upper():
            return cls._remediate_round_tripping(vuln_id, desc)
        else:
            return cls._remediate_generic_imbalance(vuln_id, desc)

    @classmethod
    def _remediate_wht_evasion(cls, vuln_id: str, desc: str) -> RemediationPatch:
        rule_code = (
            "# SAP S/4HANA Validation Rule: GGB0 / Financial Accounting\n"
            "PREREQUISITE:\n"
            "  BKPF-BLART = 'KZ' AND BSEG-BSCHL = '25' AND BSEG-WRBTR >= 500.00\n"
            "CHECK:\n"
            "  BSEG-QSSKZ IN ('194C', '194J', 'W1', 'W2') AND\n"
            "  EXISTS_LINE( BKPF-BELNR, HKONT = '22200', SHKZG = 'H' )\n"
            "ERROR:\n"
            "  MESSAGE E901(ZFI) WITH 'Statutory Withholding Tax deduction required for disbursements >= $500.00'\n"
        )
        ctrl = CompensatingControl(
            control_id="SOX-COMP-TAX-WHT-01",
            title="Mandatory Automated WHT Split on P2P Disbursements",
            control_type="PREVENTIVE",
            frequency="PER_TRANSACTION",
            sox_reference="SOX-404-TAX-WHT",
            control_activity="The ERP payment program (F110) automatically calculates and deducts statutory withholding tax into GL Account 22200 prior to clearing vendor liability.",
            responsible_role="Tax Compliance Director",
        )
        return RemediationPatch(
            patch_id=f"PATCH_WHT_{vuln_id[:6]}",
            vulnerability_id=vuln_id,
            vulnerability_title="Statutory Withholding Tax Deduction Omission",
            target_type=RemediationTargetType.SAP_SUBST_RULE,
            code_or_rule=rule_code,
            explanation="Enforces automatic validation error E901 whenever a vendor payment voucher (KZ) exceeds $500 without crediting withholding tax payable (Account 22200).",
            compensating_controls=[ctrl],
        )

    @classmethod
    def _remediate_phantom_po(cls, vuln_id: str, desc: str) -> RemediationPatch:
        abap_code = (
            "* SAP ABAP Enhancement: BAdI BADI_ACC_DOCUMENT (Method CHANGE)\n"
            "METHOD if_ex_badi_acc_document~change.\n"
            "  DATA: lt_mseg TYPE TABLE OF mseg,\n"
            "        lv_po   TYPE ebeln.\n"
            "  LOOP AT c_accit ASSIGNING FIELD-SYMBOL(<fs_line>) WHERE bschl = '31'.\n"
            "    lv_po = <fs_line>-ebeln.\n"
            "    IF lv_po IS INITIAL.\n"
            "      MESSAGE e052(zmm) WITH 'Vendor invoice rejected: Missing referenced Purchase Order'.\n"
            "    ENDIF.\n"
            "    SELECT SINGLE mblnr FROM mseg INTO @DATA(lv_mblnr) WHERE ebeln = @lv_po AND bwart = '101'.\n"
            "    IF sy-subrc <> 0.\n"
            "      MESSAGE e053(zmm) WITH 'Vendor invoice rejected: No matching Goods Receipt (WE) found for PO' lv_po.\n"
            "    ENDIF.\n"
            "  ENDLOOP.\n"
            "ENDMETHOD.\n"
        )
        ctrl = CompensatingControl(
            control_id="SOX-COMP-P2P-3WM-01",
            title="Automated 3-Way Match Verification Gate",
            control_type="PREVENTIVE",
            frequency="PER_TRANSACTION",
            sox_reference="SOX-404-P2P-3WM",
            control_activity="Invoices submitted without a recorded Goods Receipt (Movement Type 101) in table MSEG are automatically quarantined in invoice park state.",
            responsible_role="Procurement Operations Lead",
        )
        return RemediationPatch(
            patch_id=f"PATCH_3WM_{vuln_id[:6]}",
            vulnerability_id=vuln_id,
            vulnerability_title="Phantom Purchase Order 3-Way Match Bypass",
            target_type=RemediationTargetType.SAP_ABAP_BADI,
            code_or_rule=abap_code,
            explanation="Injects an ABAP BAdI verification routine into the accounting document posting pipeline, verifying that every invoice item has a corresponding Goods Receipt.",
            compensating_controls=[ctrl],
        )

    @classmethod
    def _remediate_inventory_shrinkage(cls, vuln_id: str, desc: str) -> RemediationPatch:
        sql_rule = (
            "-- SQL DDL Hardening: Constraint on Inventory Adjusting Entries\n"
            "ALTER TABLE journal_lines ADD CONSTRAINT chk_inventory_clearing\n"
            "CHECK (\n"
            "  NOT (account_code LIKE '14%' AND debit_credit = 'CREDIT' AND (\n"
            "    entry_id IN (\n"
            "      SELECT entry_id FROM journal_lines WHERE account_code IN ('99999', '33000')\n"
            "    )\n"
            "  ))\n"
            ");\n"
        )
        ctrl = CompensatingControl(
            control_id="SOX-COMP-INV-SHRINK-01",
            title="Mandatory Two-Person Rule for Inventory Write-Downs",
            control_type="PREVENTIVE",
            frequency="PER_TRANSACTION",
            sox_reference="SOX-404-INV-SHRINK",
            control_activity="Inventory discrepancies must be routed exclusively to Inventory Shrinkage (50100) and require counter-signature by the Plant Controller.",
            responsible_role="Warehouse Operations Controller",
        )
        return RemediationPatch(
            patch_id=f"PATCH_SHRINK_{vuln_id[:6]}",
            vulnerability_id=vuln_id,
            vulnerability_title="Concealed Inventory Shrinkage into Suspense",
            target_type=RemediationTargetType.SQL_CONSTRAINT,
            code_or_rule=sql_rule,
            explanation="Prohibits direct credits to raw or finished goods inventory that debit suspense (99999) or retained earnings (33000), forcing reconciliation through dedicated shrinkage accounts.",
            compensating_controls=[ctrl],
        )

    @classmethod
    def _remediate_sql_injection(cls, vuln_id: str, desc: str) -> RemediationPatch:
        code_str = (
            "# Python / SQLAlchemy Prepared Statement Implementation\n"
            "# Replace dynamic string concatenation with bound parameters:\n"
            "stmt = text('''\n"
            "  INSERT INTO journal_entries (entry_id, company_code, document_number, header_text, reference)\n"
            "  VALUES (:entry_id, :company_code, :document_number, :header_text, :reference)\n"
            "''')\n"
            "session.execute(stmt, {\n"
            "  'entry_id': entry.entry_id,\n"
            "  'company_code': entry.company_code,\n"
            "  'document_number': entry.document_number,\n"
            "  'header_text': entry.header_text,\n"
            "  'reference': entry.reference\n"
            "})\n"
        )
        return RemediationPatch(
            patch_id=f"PATCH_SQLI_{vuln_id[:6]}",
            vulnerability_id=vuln_id,
            vulnerability_title="SQL Injection / Unescaped String Concatenation",
            target_type=RemediationTargetType.SQL_CONSTRAINT,
            code_or_rule=code_str,
            explanation="Eliminates raw string interpolations in accounting document headers and reference fields by enforcing parameterized queries.",
        )

    @classmethod
    def _remediate_doa_smurfing(cls, vuln_id: str, desc: str) -> RemediationPatch:
        subst_code = (
            "# SAP Workflow Rule: WS00000038 / Dual Approval Trigger\n"
            "CONDITION:\n"
            "  SUM( BSEG-WRBTR WHERE LIFNR = $CURRENT_VENDOR AND CPUDT >= SY-DATUM - 2 ) >= 10000.00\n"
            "ACTION:\n"
            "  SET BKPF-BSTAT = 'V'  \" Park Document\n"
            "  TRIGGER WORKFLOW 'WF_CFO_DUAL_SIGN' WITH PRIORITY = 'HIGH'\n"
        )
        ctrl = CompensatingControl(
            control_id="SOX-COMP-P2P-DOA-01",
            title="Rolling 48-Hour Vendor Aggregation Limit Check",
            control_type="PREVENTIVE",
            frequency="DAILY",
            sox_reference="SOX-404-P2P-DOA",
            control_activity="Automated batch monitoring scans all invoices under $10,000 posted to identical vendors within 48 hours and holds payments pending Controller review.",
            responsible_role="Internal Audit Manager",
        )
        return RemediationPatch(
            patch_id=f"PATCH_DOA_{vuln_id[:6]}",
            vulnerability_id=vuln_id,
            vulnerability_title="Delegation-of-Authority (DOA) Smurfing Bypass",
            target_type=RemediationTargetType.SAP_SUBST_RULE,
            code_or_rule=subst_code,
            explanation="Replaces point-in-time threshold checks with a 48-hour rolling temporal window, parking clustered invoices for secondary CFO approval.",
            compensating_controls=[ctrl],
        )

    @classmethod
    def _remediate_round_tripping(cls, vuln_id: str, desc: str) -> RemediationPatch:
        rule_code = (
            "# SAP Intercompany Matching Rule: IC_ELIM_01\n"
            "PREREQUISITE:\n"
            "  BKPF-BLART = 'IC' AND BSEG-VBUND <> ''\n"
            "CHECK:\n"
            "  NOT IS_DIRECTED_CYCLE( ORIGIN = BKPF-BUKRS, TRADING_PARTNER = BSEG-VBUND, FISCAL_PERIOD = BKPF-MONAT )\n"
            "ERROR:\n"
            "  MESSAGE E099(ZIC) WITH 'Circular intercompany volume inflation detected across entity group'\n"
        )
        return RemediationPatch(
            patch_id=f"PATCH_IC_{vuln_id[:6]}",
            vulnerability_id=vuln_id,
            vulnerability_title="Circular Intercompany Round-Tripping Cycle",
            target_type=RemediationTargetType.SAP_SUBST_RULE,
            code_or_rule=rule_code,
            explanation="Maintains an in-memory directed graph of intercompany vouchers during month-end closing, terminating cycles before ledger commitment.",
        )

    @classmethod
    def _remediate_generic_imbalance(cls, vuln_id: str, desc: str) -> RemediationPatch:
        sql_ddl = (
            "ALTER TABLE journal_entries ADD CONSTRAINT chk_zero_sum_balance\n"
            "CHECK (abs(total_debits - total_credits) < 0.0001);\n"
        )
        return RemediationPatch(
            patch_id=f"PATCH_BAL_{vuln_id[:6]}",
            vulnerability_id=vuln_id,
            vulnerability_title="Accounting Invariant Imbalance",
            target_type=RemediationTargetType.SQL_CONSTRAINT,
            code_or_rule=sql_ddl,
            explanation="Enforces database engine zero-sum mathematical invariant constraint at transaction commit time.",
        )
