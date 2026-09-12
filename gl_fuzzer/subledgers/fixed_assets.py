"""Fixed Asset Life Management & Subledger Engine (IAS 16, IAS 36, IFRS 16)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import uuid
from pydantic import BaseModel, Field

from gl_fuzzer.models.journal import (
    DebitCredit,
    DocumentType,
    JournalEntry,
    LineItem,
)


class AssetClass(str, Enum):
    BUILDING = "BUILDING"
    MACHINERY = "MACHINERY"
    IT_EQUIPMENT = "IT_EQUIPMENT"
    VEHICLES = "VEHICLES"
    FURNITURE = "FURNITURE"
    ROU_LEASE = "ROU_LEASE"


class DepreciationMethod(str, Enum):
    STRAIGHT_LINE = "STRAIGHT_LINE"
    DOUBLE_DECLINING = "DOUBLE_DECLINING"
    UNITS_OF_PRODUCTION = "UNITS_OF_PRODUCTION"
    COMPONENT = "COMPONENT"


class AssetStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    IMPAIRED = "IMPAIRED"
    FULLY_DEPRECIATED = "FULLY_DEPRECIATED"


class AssetComponent(BaseModel):
    """Component for component depreciation model (IAS 16.43)."""
    component_id: str
    description: str
    cost: Decimal
    salvage_value: Decimal = Decimal("0.00")
    useful_life_months: int
    accumulated_depreciation: Decimal = Decimal("0.00")
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE


class FixedAssetMaster(BaseModel):
    """Fixed asset master record complying with IAS 16 & IFRS 16."""
    asset_id: str = Field(..., description="Unique Asset ID (ANLN1)")
    description: str = Field(..., description="Asset description")
    asset_class: AssetClass = Field(default=AssetClass.MACHINERY)
    capitalization_date: str = Field(..., description="Date asset was placed in service (YYYY-MM-DD)")
    original_cost: Decimal = Field(..., description="Initial capitalized cost")
    salvage_value: Decimal = Field(default=Decimal("0.00"), description="Estimated residual value")
    useful_life_months: int = Field(..., description="Useful economic life in months")
    depreciation_method: DepreciationMethod = Field(default=DepreciationMethod.STRAIGHT_LINE)
    total_estimated_units: Optional[Decimal] = Field(default=None, description="Total units for UOP method")
    accumulated_depreciation: Decimal = Field(default=Decimal("0.00"))
    accumulated_impairment: Decimal = Field(default=Decimal("0.00"))
    revaluation_surplus: Decimal = Field(default=Decimal("0.00"))
    status: AssetStatus = Field(default=AssetStatus.ACTIVE)
    components: List[AssetComponent] = Field(default_factory=list)
    cost_center: str = Field(default="CC_OPS_100")
    cgu_id: Optional[str] = Field(default=None, description="Cash Generating Unit ID (IAS 36)")

    @property
    def carrying_value(self) -> Decimal:
        """Net Book Value (NBV) = Original Cost + Revaluation - Accum Dep - Accum Impairment."""
        nbv = (
            self.original_cost
            + self.revaluation_surplus
            - self.accumulated_depreciation
            - self.accumulated_impairment
        )
        return max(Decimal("0.00"), nbv).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def depreciable_base(self) -> Decimal:
        """Cost base subject to depreciation (net of salvage value and accumulated impairment)."""
        base = self.original_cost + self.revaluation_surplus - self.salvage_value - self.accumulated_impairment
        return max(Decimal("0.00"), base).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class FixedAssetSubledger:
    """Stateful subledger engine for fixed assets, depreciation schedules, and impairments."""

    def __init__(
        self,
        capitalization_threshold: Decimal = Decimal("2500.00"),
        company_code: str = "1000",
    ):
        self.capitalization_threshold = capitalization_threshold
        self.company_code = company_code
        self.assets: Dict[str, FixedAssetMaster] = {}
        self.voucher_sequence = 1

    def _next_doc_number(self, prefix: str = "FA") -> str:
        doc_num = f"{prefix}{self.voucher_sequence:08d}"
        self.voucher_sequence += 1
        return doc_num

    def register_asset(
        self,
        description: str,
        cost: Decimal,
        useful_life_months: int,
        capitalization_date: str,
        asset_class: AssetClass = AssetClass.MACHINERY,
        salvage_value: Decimal = Decimal("0.00"),
        depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
        cost_center: str = "CC_OPS_100",
        components: Optional[List[AssetComponent]] = None,
        total_estimated_units: Optional[Decimal] = None,
        cgu_id: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> Tuple[Optional[FixedAssetMaster], JournalEntry]:
        """Registers a newly acquired asset, enforcing capitalization threshold."""
        if useful_life_months <= 0:
            raise ValueError(f"useful_life_months must be > 0, got {useful_life_months}")
        cost = Decimal(str(cost)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        salvage_value = Decimal(str(salvage_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        aid = asset_id or f"AST-{uuid.uuid4().hex[:8].upper()}"
        doc_num = self._next_doc_number("AA")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        dt_parts = capitalization_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        # Threshold check: If cost < capitalization threshold, expense immediately (IAS 16 / US GAAP)
        if cost < self.capitalization_threshold:
            entry = JournalEntry(
                entry_id=entry_id,
                batch_id=f"BATCH_FA_{capitalization_date.replace('-', '')}",
                company_code=self.company_code,
                fiscal_year=f_year,
                fiscal_period=f_period,
                document_type=DocumentType.AA,
                document_number=doc_num,
                posting_date=capitalization_date,
                document_date=capitalization_date,
                created_at=now_utc,
                header_text=f"Direct Expense (Below Cap Threshold): {description}",
                business_cycle="R2R",
                lines=[
                    LineItem(
                        line_id=f"{entry_id}-001",
                        entry_id=entry_id,
                        line_number=1,
                        account_code="69000",
                        account_name="Miscellaneous Operating Expense",
                        debit_credit=DebitCredit.DEBIT,
                        amount=cost,
                        cost_center=cost_center,
                        line_text=f"Expensed item < threshold: {description}",
                    ),
                    LineItem(
                        line_id=f"{entry_id}-002",
                        entry_id=entry_id,
                        line_number=2,
                        account_code="20000",
                        account_name="Accounts Payable - Trade",
                        debit_credit=DebitCredit.CREDIT,
                        amount=cost,
                        line_text=f"AP for non-capitalized item: {description}",
                    ),
                ],
            )
            return None, entry

        # Capitalize asset
        asset_account = "17100" if asset_class == AssetClass.ROU_LEASE else "17000"
        asset_name = "Right-of-Use Assets - Leases" if asset_class == AssetClass.ROU_LEASE else "Property, Plant & Equipment"

        asset = FixedAssetMaster(
            asset_id=aid,
            description=description,
            asset_class=asset_class,
            capitalization_date=capitalization_date,
            original_cost=cost,
            salvage_value=salvage_value,
            useful_life_months=useful_life_months,
            depreciation_method=depreciation_method,
            total_estimated_units=total_estimated_units,
            components=components or [],
            cost_center=cost_center,
            cgu_id=cgu_id,
        )
        self.assets[aid] = asset

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_FA_{capitalization_date.replace('-', '')}",
            company_code=self.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.AA,
            document_number=doc_num,
            posting_date=capitalization_date,
            document_date=capitalization_date,
            created_at=now_utc,
            header_text=f"Capitalization: {description}",
            business_cycle="R2R",
            lines=[
                LineItem(
                    line_id=f"{entry_id}-001",
                    entry_id=entry_id,
                    line_number=1,
                    account_code=asset_account,
                    account_name=asset_name,
                    debit_credit=DebitCredit.DEBIT,
                    amount=cost,
                    asset_number=aid,
                    cost_center=cost_center,
                    line_text=f"Capitalized asset: {description}",
                ),
                LineItem(
                    line_id=f"{entry_id}-002",
                    entry_id=entry_id,
                    line_number=2,
                    account_code="20000",
                    account_name="Accounts Payable - Trade",
                    debit_credit=DebitCredit.CREDIT,
                    amount=cost,
                    line_text=f"AP Clearing for capitalized asset: {aid}",
                ),
            ],
        )
        return asset, entry

    def calculate_monthly_depreciation(
        self,
        asset_id: str,
        period_date: str,
        units_produced: Optional[Decimal] = None,
    ) -> Optional[JournalEntry]:
        """Calculates and posts monthly depreciation for an active asset."""
        asset = self.assets.get(asset_id)
        if not asset:
            return None
        if asset.status in (AssetStatus.RETIRED, AssetStatus.FULLY_DEPRECIATED):
            return None

        # Check if already at salvage value
        if asset.carrying_value <= asset.salvage_value:
            asset.status = AssetStatus.FULLY_DEPRECIATED
            return None

        dep_amount = Decimal("0.00")

        if asset.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
            monthly_dep = (asset.depreciable_base / Decimal(str(asset.useful_life_months))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            # Cap depreciation so carrying value does not breach salvage value
            max_possible = asset.carrying_value - asset.salvage_value
            dep_amount = min(monthly_dep, max_possible)

        elif asset.depreciation_method == DepreciationMethod.DOUBLE_DECLINING:
            rate = Decimal("2.0") / Decimal(str(asset.useful_life_months))
            monthly_dep = (asset.carrying_value * rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            max_possible = asset.carrying_value - asset.salvage_value
            dep_amount = min(monthly_dep, max_possible)

        elif asset.depreciation_method == DepreciationMethod.UNITS_OF_PRODUCTION:
            if not asset.total_estimated_units or asset.total_estimated_units <= 0:
                return None
            units = Decimal(str(units_produced or Decimal("0.00")))
            rate_per_unit = asset.depreciable_base / asset.total_estimated_units
            monthly_dep = (units * rate_per_unit).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            max_possible = asset.carrying_value - asset.salvage_value
            dep_amount = min(monthly_dep, max_possible)

        elif asset.depreciation_method == DepreciationMethod.COMPONENT:
            comp_allocations = []
            total_comp_dep = Decimal("0.00")
            for comp in asset.components:
                life = max(1, comp.useful_life_months)
                comp_base = max(Decimal("0.00"), comp.cost - comp.salvage_value)
                comp_dep = (comp_base / Decimal(str(life))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                comp_max = max(Decimal("0.00"), comp.cost - comp.accumulated_depreciation - comp.salvage_value)
                actual_comp_dep = min(comp_dep, comp_max)
                comp_allocations.append((comp, actual_comp_dep))
                total_comp_dep += actual_comp_dep
            max_possible = asset.carrying_value - asset.salvage_value
            dep_amount = min(total_comp_dep, max_possible)

            if dep_amount <= Decimal("0.00"):
                if asset.carrying_value <= asset.salvage_value:
                    asset.status = AssetStatus.FULLY_DEPRECIATED
                return None

            scale = (dep_amount / total_comp_dep) if total_comp_dep > Decimal("0.00") else Decimal("1.00")
            for comp, alloc in comp_allocations:
                comp.accumulated_depreciation += (alloc * scale).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if dep_amount <= Decimal("0.00"):
            if asset.carrying_value <= asset.salvage_value:
                asset.status = AssetStatus.FULLY_DEPRECIATED
            return None

        # Update asset state
        asset.accumulated_depreciation += dep_amount
        if asset.carrying_value <= asset.salvage_value:
            asset.status = AssetStatus.FULLY_DEPRECIATED

        doc_num = self._next_doc_number("DP")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        dt_parts = period_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_DEP_{period_date.replace('-', '')}",
            company_code=self.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.AA,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"Depreciation: {asset.description} ({asset.asset_id})",
            business_cycle="R2R",
            lines=[
                LineItem(
                    line_id=f"{entry_id}-001",
                    entry_id=entry_id,
                    line_number=1,
                    account_code="65000",
                    account_name="Depreciation Expense",
                    debit_credit=DebitCredit.DEBIT,
                    amount=dep_amount,
                    asset_number=asset.asset_id,
                    cost_center=asset.cost_center,
                    line_text=f"Monthly depreciation: {asset.description}",
                ),
                LineItem(
                    line_id=f"{entry_id}-002",
                    entry_id=entry_id,
                    line_number=2,
                    account_code="17900",
                    account_name="Accumulated Depreciation - PPE",
                    debit_credit=DebitCredit.CREDIT,
                    amount=dep_amount,
                    asset_number=asset.asset_id,
                    line_text=f"Accum dep: {asset.asset_id}",
                ),
            ],
        )
        return entry

    def test_impairment(
        self,
        asset_id: str,
        recoverable_amount: Decimal,
        period_date: str,
    ) -> Optional[JournalEntry]:
        """IAS 36 Impairment Test: Compares carrying value against recoverable amount."""
        asset = self.assets.get(asset_id)
        if not asset or asset.status == AssetStatus.RETIRED:
            return None

        rec_amt = Decimal(str(recoverable_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        carrying_val = asset.carrying_value

        if carrying_val > rec_amt:
            impairment_loss = (carrying_val - rec_amt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            asset.accumulated_impairment += impairment_loss
            asset.status = AssetStatus.IMPAIRED

            doc_num = self._next_doc_number("IM")
            entry_id = f"DOC_{doc_num}"
            now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            dt_parts = period_date.split("-")
            f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

            entry = JournalEntry(
                entry_id=entry_id,
                batch_id=f"BATCH_IMP_{period_date.replace('-', '')}",
                company_code=self.company_code,
                fiscal_year=f_year,
                fiscal_period=f_period,
                document_type=DocumentType.AA,
                document_number=doc_num,
                posting_date=period_date,
                document_date=period_date,
                created_at=now_utc,
                header_text=f"IAS 36 Impairment: {asset.description} ({asset.asset_id})",
                business_cycle="R2R",
                lines=[
                    LineItem(
                        line_id=f"{entry_id}-001",
                        entry_id=entry_id,
                        line_number=1,
                        account_code="65100",
                        account_name="Impairment Loss on Fixed Assets (IAS 36)",
                        debit_credit=DebitCredit.DEBIT,
                        amount=impairment_loss,
                        asset_number=asset.asset_id,
                        cost_center=asset.cost_center,
                        line_text=f"Impairment loss recognized: {asset.asset_id}",
                    ),
                    LineItem(
                        line_id=f"{entry_id}-002",
                        entry_id=entry_id,
                        line_number=2,
                        account_code="17800",
                        account_name="Accumulated Impairment - PPE",
                        debit_credit=DebitCredit.CREDIT,
                        amount=impairment_loss,
                        asset_number=asset.asset_id,
                        line_text=f"Accum impairment credit: {asset.asset_id}",
                    ),
                ],
            )
            return entry
        return None

    def retire_asset(
        self,
        asset_id: str,
        disposal_proceeds: Decimal,
        period_date: str,
    ) -> Optional[JournalEntry]:
        """Retires an asset, derecognizing cost/depreciation and posting gain/loss."""
        asset = self.assets.get(asset_id)
        if not asset or asset.status == AssetStatus.RETIRED:
            return None

        proceeds = Decimal(str(disposal_proceeds)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cost = asset.original_cost
        accum_dep = asset.accumulated_depreciation
        accum_imp = asset.accumulated_impairment
        nbv = asset.carrying_value

        # Gain or loss: Proceeds - NBV
        diff = proceeds - nbv
        gain = diff if diff > Decimal("0.00") else Decimal("0.00")
        loss = (-diff) if diff < Decimal("0.00") else Decimal("0.00")

        asset.status = AssetStatus.RETIRED

        doc_num = self._next_doc_number("RT")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        lines: List[LineItem] = []
        line_num = 1

        # 1. Cash proceeds (if any)
        if proceeds > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="10100",
                    account_name="Operating Cash & Bank",
                    debit_credit=DebitCredit.DEBIT,
                    amount=proceeds,
                    line_text=f"Disposal proceeds for {asset.asset_id}",
                )
            )
            line_num += 1

        # 2. Derecognize Accumulated Depreciation (Debit)
        if accum_dep > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="17900",
                    account_name="Accumulated Depreciation - PPE",
                    debit_credit=DebitCredit.DEBIT,
                    amount=accum_dep,
                    asset_number=asset.asset_id,
                    line_text=f"Derecognize accum dep: {asset.asset_id}",
                )
            )
            line_num += 1

        # 3. Derecognize Accumulated Impairment (Debit)
        if accum_imp > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="17800",
                    account_name="Accumulated Impairment - PPE",
                    debit_credit=DebitCredit.DEBIT,
                    amount=accum_imp,
                    asset_number=asset.asset_id,
                    line_text=f"Derecognize accum impairment: {asset.asset_id}",
                )
            )
            line_num += 1

        # 4. Loss on disposal (Debit) if any
        if loss > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="65200",
                    account_name="Loss on Disposal of Fixed Assets",
                    debit_credit=DebitCredit.DEBIT,
                    amount=loss,
                    asset_number=asset.asset_id,
                    cost_center=asset.cost_center,
                    line_text=f"Loss on asset disposal: {asset.asset_id}",
                )
            )
            line_num += 1

        # 5. Derecognize Gross Asset Cost (Credit) - includes revaluation surplus
        asset_account = "17100" if asset.asset_class == AssetClass.ROU_LEASE else "17000"
        asset_name = "Right-of-Use Assets - Leases" if asset.asset_class == AssetClass.ROU_LEASE else "Property, Plant & Equipment"
        gross_cost = cost + asset.revaluation_surplus

        lines.append(
            LineItem(
                line_id=f"{entry_id}-{line_num:03d}",
                entry_id=entry_id,
                line_number=line_num,
                account_code=asset_account,
                account_name=asset_name,
                debit_credit=DebitCredit.CREDIT,
                amount=gross_cost,
                asset_number=asset.asset_id,
                line_text=f"Derecognize gross asset cost: {asset.asset_id}",
            )
        )
        line_num += 1

        # 6. Gain on disposal (Credit) if any
        if gain > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="48000",
                    account_name="Gain on Disposal of Fixed Assets",
                    debit_credit=DebitCredit.CREDIT,
                    amount=gain,
                    asset_number=asset.asset_id,
                    line_text=f"Gain on asset disposal: {asset.asset_id}",
                )
            )
            line_num += 1

        # 7. Transfer Revaluation Surplus to Retained Earnings (IAS 16.41)
        if asset.revaluation_surplus > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="31000",
                    account_name="Additional Paid-in Capital",
                    debit_credit=DebitCredit.DEBIT,
                    amount=asset.revaluation_surplus,
                    asset_number=asset.asset_id,
                    line_text=f"Derecognize revaluation surplus on disposal: {asset.asset_id}",
                )
            )
            line_num += 1
            lines.append(
                LineItem(
                    line_id=f"{entry_id}-{line_num:03d}",
                    entry_id=entry_id,
                    line_number=line_num,
                    account_code="33000",
                    account_name="Retained Earnings",
                    debit_credit=DebitCredit.CREDIT,
                    amount=asset.revaluation_surplus,
                    asset_number=asset.asset_id,
                    line_text=f"Transfer revaluation surplus to retained earnings: {asset.asset_id}",
                )
            )
            line_num += 1

        dt_parts = period_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_RET_{period_date.replace('-', '')}",
            company_code=self.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.AA,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"Retirement & Derecognition: {asset.description} ({asset.asset_id})",
            business_cycle="R2R",
            lines=lines,
        )
        return entry

    def revalue_asset(
        self,
        asset_id: str,
        fair_value: Decimal,
        period_date: str,
    ) -> Optional[JournalEntry]:
        """IAS 16.31 Revaluation Model: Restates asset to fair value with credit to revaluation surplus."""
        asset = self.assets.get(asset_id)
        if not asset or asset.status == AssetStatus.RETIRED:
            return None

        fv = Decimal(str(fair_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        carrying_val = asset.carrying_value
        surplus_increase = (fv - carrying_val).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if surplus_increase <= Decimal("0.00"):
            return None

        asset.revaluation_surplus += surplus_increase

        doc_num = self._next_doc_number("RV")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        dt_parts = period_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_REV_{period_date.replace('-', '')}",
            company_code=self.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.AA,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"IAS 16 Revaluation Surplus: {asset.description}",
            business_cycle="R2R",
            lines=[
                LineItem(
                    line_id=f"{entry_id}-001",
                    entry_id=entry_id,
                    line_number=1,
                    account_code="17000",
                    account_name="Property, Plant & Equipment",
                    debit_credit=DebitCredit.DEBIT,
                    amount=surplus_increase,
                    asset_number=asset.asset_id,
                    line_text=f"Asset carrying value upward revaluation: {asset.asset_id}",
                ),
                LineItem(
                    line_id=f"{entry_id}-002",
                    entry_id=entry_id,
                    line_number=2,
                    account_code="31000",
                    account_name="Additional Paid-in Capital",
                    debit_credit=DebitCredit.CREDIT,
                    amount=surplus_increase,
                    line_text=f"Revaluation surplus equity credit: {asset.asset_id}",
                ),
            ],
        )
        return entry


# ---------------------------------------------------------------------------
# Calibrated Fraud Anomaly Mutators for Fixed Assets
# ---------------------------------------------------------------------------

class ImpairmentOmissionMutator:
    """Fraud Mutator: Fraudulently omits required IAS 36 write-downs to inflate assets."""

    @staticmethod
    def mutate(
        subledger: FixedAssetSubledger,
        asset_id: str,
        recoverable_amount: Decimal,
        period_date: str,
    ) -> Optional[JournalEntry]:
        asset = subledger.assets.get(asset_id)
        if not asset:
            return None
        # Intentionally suppresses the write-down: does not post impairment voucher
        return None


class ZombieAssetMutator:
    """Fraud Mutator: Continues posting depreciation charges on already retired or scrapped assets."""

    @staticmethod
    def mutate(
        subledger: FixedAssetSubledger,
        asset_id: str,
        period_date: str,
        ghost_amount: Optional[Decimal] = None,
    ) -> Optional[JournalEntry]:
        asset = subledger.assets.get(asset_id)
        if not asset:
            return None

        dep_amt = ghost_amount or Decimal("1250.00")
        doc_num = subledger._next_doc_number("ZD")
        entry_id = f"DOC_{doc_num}"
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        dt_parts = period_date.split("-")
        f_year, f_period = int(dt_parts[0]), int(dt_parts[1])

        entry = JournalEntry(
            entry_id=entry_id,
            batch_id=f"BATCH_ZOMBIE_{period_date.replace('-', '')}",
            company_code=subledger.company_code,
            fiscal_year=f_year,
            fiscal_period=f_period,
            document_type=DocumentType.AA,
            document_number=doc_num,
            posting_date=period_date,
            document_date=period_date,
            created_at=now_utc,
            header_text=f"FRAUD_ZOMBIE_ASSET_DEP: {asset.asset_id}",
            business_cycle="R2R",
            is_anomaly=True,
            anomaly_ids=["ANOM_ZOMBIE_ASSET_DEPRECIATION"],
            lines=[
                LineItem(
                    line_id=f"{entry_id}-001",
                    entry_id=entry_id,
                    line_number=1,
                    account_code="65000",
                    account_name="Depreciation Expense",
                    debit_credit=DebitCredit.DEBIT,
                    amount=dep_amt,
                    asset_number=asset.asset_id,
                    cost_center=asset.cost_center,
                    line_text=f"Fraudulent zombie depreciation: {asset.asset_id}",
                ),
                LineItem(
                    line_id=f"{entry_id}-002",
                    entry_id=entry_id,
                    line_number=2,
                    account_code="17900",
                    account_name="Accumulated Depreciation - PPE",
                    debit_credit=DebitCredit.CREDIT,
                    amount=dep_amt,
                    asset_number=asset.asset_id,
                    line_text=f"Ghost accum dep: {asset.asset_id}",
                ),
            ],
        )
        return entry


class CapitalizationThresholdEvasionMutator:
    """Fraud Mutator: Splits a large capital expenditure into multiple micro-purchases below cap threshold."""

    @staticmethod
    def mutate(
        subledger: FixedAssetSubledger,
        total_expenditure: Decimal,
        splits: int,
        period_date: str,
    ) -> List[JournalEntry]:
        if splits <= 0:
            raise ValueError(f"splits must be > 0, got {splits}")
        total = Decimal(str(total_expenditure))
        split_amt = (total / Decimal(str(splits))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        entries: List[JournalEntry] = []
        allocated = Decimal("0.00")

        for i in range(splits):
            cost_i = total - allocated if i == splits - 1 else split_amt
            allocated += cost_i
            _, entry = subledger.register_asset(
                description=f"Split Invoiced Item Part {i+1}/{splits}",
                cost=cost_i,
                useful_life_months=36,
                capitalization_date=period_date,
            )
            if entry:
                entry.is_anomaly = True
                entry.anomaly_ids.append("ANOM_CAPITALIZATION_THRESHOLD_EVASION")
                entries.append(entry)
        return entries
