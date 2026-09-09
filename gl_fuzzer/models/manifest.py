"""Audit Ground-Truth Manifest data structures with SOX control mapping and cryptographic digest."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnomalyType(str, Enum):
    SMURFING_SPLIT_APPROVAL = "SMURFING_SPLIT_APPROVAL"
    OFF_HOURS_GHOST_ENTRY = "OFF_HOURS_GHOST_ENTRY"
    BENFORD_SKEW = "BENFORD_SKEW"
    ANOMALOUS_ACCOUNT_PAIRING = "ANOMALOUS_ACCOUNT_PAIRING"
    CIRCULAR_INTERCOMPANY_ROUND_TRIP = "CIRCULAR_INTERCOMPANY_ROUND_TRIP"
    TAX_EVASION_ZERO_WHT = "TAX_EVASION_ZERO_WHT"
    PHANTOM_PO_THREE_WAY_BYPASS = "PHANTOM_PO_THREE_WAY_BYPASS"
    INVENTORY_SHRINKAGE_CONCEALMENT = "INVENTORY_SHRINKAGE_CONCEALMENT"
    SECURITY_FUZZ_BYPASS = "SECURITY_FUZZ_BYPASS"
    SECURITY_FUZZ_CRASH = "SECURITY_FUZZ_CRASH"


class SOXControlRef(str, Enum):
    P2P_DOA_LIMITS = "SOX-404-P2P-DOA: Circumvention of Delegation-of-Authority Authorization Limits"
    MJE_MANAGEMENT_OVERRIDE = "SOX-404-MJE-01: Unauthorized Manual Journal Entry & Management Override"
    FORENSIC_BENFORD = "SOX-404-DATA-INTEGRITY: Vendor Kickback / Artificial Invoice Fabrication Screening"
    GL_SUSPENSE_CONSISTENCY = "SOX-404-GL-PAIRING: Suspense Account Parking & Irregular Balance Transfers"
    INTERCOMPANY_ROUND_TRIP = "SOX-404-IC-03: Intercompany Round-Tripping & Artificial Volume Inflation"
    TAX_WITHHOLDING_COMPLIANCE = "SOX-404-TAX-01: Vendor Payment WHT Statutory Deduction Compliance"
    THREE_WAY_MATCH_BYPASS = "SOX-404-P2P-02: Unauthorized Vendor Invoice Approval Without GR/PO Match"
    INVENTORY_INTEGRITY = "SOX-404-STOCK-01: Inventory Valuation and Physical Count Reconciliation"
    CYBER_LEDGER_RESILIENCE = "SOX-404-ITGC-01: Relational Ledger Integrity & Constraint Injection Resilience"


class AnomalyRecord(BaseModel):
    """Detailed record of an individual injected anomaly for forensic evaluation."""
    anomaly_id: str = Field(..., description="Unique anomaly identifier")
    anomaly_type: AnomalyType = Field(..., description="Classification category")
    sox_control: str = Field(..., description="Target SOX / Internal Control identifier")
    audit_script: str = Field(..., description="Standard audit test script to detect this signal")
    risk_level: str = Field(default="HIGH", description="Audit risk rating: MEDIUM, HIGH, CRITICAL")
    description: str = Field(..., description="Human-readable forensic rationale")
    affected_entry_ids: List[str] = Field(default_factory=list, description="List of affected document BELNRs")
    affected_line_ids: List[str] = Field(default_factory=list, description="List of affected line item IDs")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Generator parameters used to inject anomaly")
    forensic_indicator: str = Field(..., description="Expected mathematical/forensic signal for automated detection")


class GroundTruthManifest(BaseModel):
    """Ground-truth manifest accompanying the generated General Ledger feed."""
    manifest_version: str = "1.0.0"
    dataset_id: str = Field(..., description="Unique identifier of this synthesis run")
    generated_at: str = Field(..., description="Timestamp of manifest generation")
    seed: Optional[int] = Field(default=None, description="Random seed used for reproducibility")
    total_batches: int = 0
    total_entries: int = 0
    total_lines: int = 0
    clean_entries_count: int = 0
    anomalous_entries_count: int = 0
    anomaly_rate: float = 0.0
    anomaly_breakdown: Dict[str, int] = Field(default_factory=dict)
    anomalies: List[AnomalyRecord] = Field(default_factory=list)
    dataset_sha256: str = Field(default="", description="Cryptographic SHA-256 hash of the GL feed")
    manifest_sha256: str = Field(default="", description="Cryptographic SHA-256 hash of this manifest content")
