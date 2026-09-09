"""Models for Automated Remediation Oracles and the Healing Loop."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RemediationTargetType(str, Enum):
    """Target systems and layers for automated financial remediation."""
    SAP_SUBST_RULE = "SAP_SUBST_RULE"           # SAP S/4HANA Validation / Substitution (GGB0 / FINS_REV_SUBST)
    SAP_ABAP_BADI = "SAP_ABAP_BADI"             # SAP NetWeaver ABAP BAdI (BADI_ACC_DOCUMENT)
    SQL_CONSTRAINT = "SQL_CONSTRAINT"           # Relational SQL DDL / Table Check Constraint
    SOX_COMPENSATING_CONTROL = "SOX_POLICY"      # Internal Controls / SOX 404 Compensating Control


class PatchVerificationStatus(str, Enum):
    """Lifecycle status of an automated remediation patch."""
    PENDING = "PENDING"
    VERIFIED_HEALED = "VERIFIED_HEALED"
    REJECTED_REGRESSION = "REJECTED_REGRESSION"
    PARTIAL = "PARTIAL"


class CompensatingControl(BaseModel):
    """Formal audit narrative specifying a compensating internal control."""
    control_id: str = Field(..., description="Unique control identifier (e.g. SOX-COMP-P2P-01)")
    title: str = Field(..., description="Concise control title")
    control_type: str = Field(default="PREVENTIVE", description="PREVENTIVE or DETECTIVE")
    frequency: str = Field(default="PER_TRANSACTION", description="PER_TRANSACTION, DAILY, or MONTHLY")
    sox_reference: str = Field(..., description="Mapped SOX section (e.g. SOX-404-P2P)")
    control_activity: str = Field(..., description="Detailed policy description of the control procedure")
    responsible_role: str = Field(..., description="Role responsible for execution (e.g., Accounts Payable Manager)")


class RemediationPatch(BaseModel):
    """Self-contained, deployable remediation patch addressing an identified vulnerability."""
    patch_id: str = Field(..., description="Unique patch identifier (e.g. PATCH_F5_201_A)")
    vulnerability_id: str = Field(..., description="Vulnerability or finding identifier addressed")
    vulnerability_title: str = Field(..., description="Concise description of the vulnerability")
    target_type: RemediationTargetType = Field(..., description="System architecture tier targeted")
    code_or_rule: str = Field(..., description="Deployable code, SQL DDL, or SAP rule syntax")
    explanation: str = Field(..., description="Technical explanation of how this patch closes the vector")
    verification_status: PatchVerificationStatus = Field(default=PatchVerificationStatus.PENDING)
    verification_notes: str = Field(default="", description="Results of the automated healing re-test")
    compensating_controls: List[CompensatingControl] = Field(default_factory=list)
