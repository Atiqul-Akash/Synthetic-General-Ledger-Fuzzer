"""Tax and compliance data models for multi-jurisdictional localizations."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from gl_fuzzer.models.journal import LineItem


class TaxJurisdiction(str, Enum):
    US_NATIONAL = "US_NATIONAL"
    US_CA = "US_CA"
    US_TX = "US_TX"
    US_NY = "US_NY"
    US_WA = "US_WA"
    US_FL = "US_FL"
    US_IL = "US_IL"
    EU_DE = "EU_DE"
    EU_FR = "EU_FR"
    EU_IT = "EU_IT"
    EU_ES = "EU_ES"
    EU_NL = "EU_NL"
    UK = "UK"
    GLOBAL = "GLOBAL"


class TaxExemptionReason(str, Enum):
    RESALE = "RESALE"
    GOVERNMENT = "GOVERNMENT"
    MANUFACTURING = "MANUFACTURING"
    CHARITY = "CHARITY"
    EXPORT = "EXPORT"
    NONE = "NONE"


class TaxCode(BaseModel):
    """Represents a tax code definition (SAP MWSKZ)."""
    code: str = Field(..., description="Tax code symbol (e.g. 'V1', 'A1', 'RC')")
    rate: Decimal = Field(..., description="Tax rate fraction (e.g. 0.19 for 19%)")
    name: str = Field(..., description="Description of tax code")
    account_input: str = Field(default="13000", description="Input Tax account")
    account_output: str = Field(default="22100", description="Output Tax account")
    is_recoverable: bool = Field(default=True, description="Whether input tax is recoverable")
    is_reverse_charge: bool = Field(default=False, description="B2B reverse charge self-assessment")


class TaxCalculationResult(BaseModel):
    """Result of tax calculation on an invoice base amount."""
    base_amount: Decimal
    tax_code: TaxCode
    tax_amount: Decimal
    total_with_tax: Decimal
    jurisdiction: TaxJurisdiction
    is_reverse_charge: bool = False
    tax_line_items: List[LineItem] = Field(default_factory=list)


class TaxReturnSummary(BaseModel):
    """Periodic tax reconciliation return (VAT Form 200 / US State Sales Tax Return)."""
    jurisdiction: TaxJurisdiction
    period: str
    taxable_sales: Decimal = Decimal("0.00")
    exempt_sales: Decimal = Decimal("0.00")
    output_tax_collected: Decimal = Decimal("0.00")
    taxable_purchases: Decimal = Decimal("0.00")
    input_tax_deductible: Decimal = Decimal("0.00")
    net_tax_payable: Decimal = Decimal("0.00")
    entries_count: int = 0
