"""Models for Enterprise Master Data Management (MDM) and Integrity Fuzzing."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MDMAnomalyType(str, Enum):
    """Categories of Master Data Management fraud vectors and integrity corruptions."""
    DUPLICATE_SYBIL_VENDOR = "DUPLICATE_SYBIL_VENDOR"
    BANK_ROUTING_TAMPERING_24H = "BANK_ROUTING_TAMPERING_24H"
    EMPLOYEE_VENDOR_COLLUSION = "EMPLOYEE_VENDOR_COLLUSION"
    MULTI_TENANT_POLICY_DRIFT = "MULTI_TENANT_POLICY_DRIFT"


class VendorMaster(BaseModel):
    """Vendor master profile (SAP LFA1 / LFB1 equivalent)."""
    vendor_id: str = Field(..., description="Unique vendor ID (LIFNR)")
    name: str = Field(..., description="Legal company name")
    tax_id: str = Field(..., description="Tax identification number (EIN / TIN)")
    country: str = Field(default="US")
    bank_country: str = Field(default="US")
    bank_routing_number: str = Field(..., description="Routing transit number (ABA / BLZ)")
    bank_account_number: str = Field(..., description="Bank account number (BANKN)")
    iban: Optional[str] = Field(default=None)
    swift_bic: Optional[str] = Field(default=None)
    payment_terms: str = Field(default="NT30")
    is_approved: bool = Field(default=True)
    created_date: str = Field(default="2026-01-01")
    last_modified_date: str = Field(default="2026-01-01")


class CustomerMaster(BaseModel):
    """Customer master profile (SAP KNA1 / KNB1 equivalent)."""
    customer_id: str = Field(..., description="Unique customer ID (KUNNR)")
    name: str = Field(..., description="Customer legal name")
    tax_id: str = Field(..., description="Tax identification number")
    country: str = Field(default="US")
    credit_limit: Decimal = Field(default=Decimal("100000.00"))
    payment_terms: str = Field(default="NT30")
    resale_exemption_certificate: Optional[str] = Field(default=None)


class EmployeeMaster(BaseModel):
    """Employee payroll profile (SAP PA0002 / PA0006 equivalent)."""
    employee_id: str = Field(..., description="Unique employee identifier (PERNR)")
    name: str = Field(..., description="Full legal name")
    bank_routing_number: str = Field(...)
    bank_account_number: str = Field(...)
    tax_id: str = Field(..., description="SSN / National Tax Identifier")
    department: str = Field(default="FINANCE")


class MDMAnomalyRecord(BaseModel):
    """Detailed audit record of an injected master data anomaly."""
    anomaly_id: str = Field(..., description="Unique anomaly ID")
    anomaly_type: MDMAnomalyType
    target_id: str = Field(..., description="Target vendor, customer, or employee ID")
    entity_type: str = Field(default="VENDOR")
    description: str = Field(...)
    audit_evidence: Dict[str, Any] = Field(default_factory=dict)
    detection_rule: str = Field(default="")
