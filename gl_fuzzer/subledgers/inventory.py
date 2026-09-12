"""Stateful warehouse inventory, physical bin tracking, and Moving Average Price (MAP) valuation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import uuid
from pydantic import BaseModel, Field


class CostingMethod(str, Enum):
    MOVING_AVERAGE = "MOVING_AVERAGE"
    STANDARD_COST = "STANDARD_COST"
    FIFO = "FIFO"


class MaterialMasterItem(BaseModel):
    """Represents an active material SKU in the enterprise material master catalogue."""
    material_number: str = Field(..., description="Unique material identifier (MATNR, e.g. 'MAT-1001')")
    description: str = Field(..., description="Product description")
    unit_of_measure: str = Field(default="EA", description="Base Unit of Measure (MEINS)")
    standard_price: Decimal = Field(..., description="Standard cost benchmark (STPRS)")
    moving_avg_price: Decimal = Field(..., description="Moving Average Unit Cost (VERPR)")
    safety_stock_qty: int = Field(default=100, description="Minimum safety stock threshold")
    reorder_point_qty: int = Field(default=250, description="Replenishment trigger point")
    costing_method: CostingMethod = Field(default=CostingMethod.MOVING_AVERAGE)


class BinLocation(BaseModel):
    """Represents a physical storage bin in a warehouse facility."""
    plant: str = Field(default="1000", description="Plant / Facility Code (WERKS)")
    storage_location: str = Field(default="0001", description="Storage Location (LGORT)")
    bin_id: str = Field(default="BIN-A1-01", description="Physical shelf/bin identifier")
    qty_on_hand: Decimal = Field(default=Decimal("0.00"), description="Unrestricted physical stock")
    reserved_qty: Decimal = Field(default=Decimal("0.00"), description="Allocated to outbound deliveries")


class StockMovement(BaseModel):
    """Audit log of physical and valuation movement in the warehouse."""
    movement_id: str
    material_number: str
    movement_type: str  # 101_GR_PO, 201_GI_COST_CENTER, 601_GI_SALES_ORDER, 701_PHYSICAL_COUNT_ADJUST
    quantity: Decimal
    unit_cost: Decimal
    total_valuation: Decimal
    plant: str
    storage_location: str
    bin_id: str
    timestamp: str


class WarehouseInventory:
    """Stateful physical warehouse simulator managing bins and dynamic moving average costs."""

    def __init__(self):
        self.materials: Dict[str, MaterialMasterItem] = {}
        self.bins: Dict[Tuple[str, str, str, str], BinLocation] = {}  # (plant, sloc, bin_id, matnr)
        self.movements: List[StockMovement] = []

    def register_material(self, item: MaterialMasterItem) -> None:
        self.materials[item.material_number] = item

    def get_material(self, material_number: str) -> Optional[MaterialMasterItem]:
        return self.materials.get(material_number)

    def _get_or_create_bin(self, plant: str, storage_location: str, bin_id: str, material_number: str) -> BinLocation:
        key = (plant, storage_location, bin_id, material_number)
        if key not in self.bins:
            self.bins[key] = BinLocation(plant=plant, storage_location=storage_location, bin_id=bin_id)
        return self.bins[key]

    def get_total_quantity_on_hand(self, material_number: str) -> Decimal:
        """Returns total stock quantity across all plants and bins for a material."""
        tot = Decimal("0.00")
        for m in self.movements:
            if m.material_number == material_number:
                if m.movement_type in ("101_GR_PO", "701_SURPLUS_ADJUST"):
                    tot += m.quantity
                elif m.movement_type in ("201_GI_COST_CENTER", "601_GI_SALES_ORDER", "702_SHRINKAGE_ADJUST"):
                    tot -= m.quantity
        return max(Decimal("0.00"), tot)

    def receive_goods(
        self,
        material_number: str,
        quantity: Decimal | int | float,
        unit_cost: Decimal | int | float,
        plant: str = "1000",
        storage_location: str = "0001",
        bin_id: str = "BIN-A1-01",
    ) -> StockMovement:
        """Processes goods receipt (Movement 101), updating bin stock and recalculating MAP."""
        mat = self.materials.get(material_number)
        if not mat:
            raise ValueError(f"Material {material_number} not found in Material Master")

        qty_dec = Decimal(str(quantity))
        cost_dec = Decimal(str(unit_cost))

        bin_loc = self._get_or_create_bin(plant, storage_location, bin_id, material_number)
        current_total_qty = self.get_total_quantity_on_hand(material_number)
        current_map = mat.moving_avg_price

        # Recalculate Moving Average Price: (old_total_val + new_val) / (old_qty + new_qty)
        if current_total_qty + qty_dec > Decimal("0.00"):
            old_valuation = current_total_qty * current_map
            new_valuation = qty_dec * cost_dec
            new_map = ((old_valuation + new_valuation) / (current_total_qty + qty_dec)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            mat.moving_avg_price = new_map

        bin_loc.qty_on_hand += qty_dec
        total_val = (qty_dec * cost_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        m = StockMovement(
            movement_id=f"MVT_{uuid.uuid4().hex[:8].upper()}",
            material_number=material_number,
            movement_type="101_GR_PO",
            quantity=qty_dec,
            unit_cost=cost_dec,
            total_valuation=total_val,
            plant=plant,
            storage_location=storage_location,
            bin_id=bin_id,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        self.movements.append(m)
        return m

    def issue_goods(
        self,
        material_number: str,
        quantity: Decimal | int | float,
        plant: str = "1000",
        storage_location: str = "0001",
        bin_id: str = "BIN-A1-01",
    ) -> StockMovement:
        """Processes goods issue (Movement 601), decrements bin stock, and computes COGS at current MAP."""
        mat = self.materials.get(material_number)
        if not mat:
            raise ValueError(f"Material {material_number} not found in Material Master")

        qty_dec = Decimal(str(quantity))
        bin_loc = self._get_or_create_bin(plant, storage_location, bin_id, material_number)
        if bin_loc.qty_on_hand < qty_dec:
            raise ValueError(
                f"Insufficient inventory for {material_number} in bin {bin_id}. Available: {bin_loc.qty_on_hand}, Requested: {qty_dec}"
            )

        # Respect configured costing method for COGS valuation
        costing_method = getattr(mat, "costing_method", "MAP")
        if costing_method == "STANDARD_COST" and mat.standard_price and mat.standard_price > Decimal("0"):
            unit_cost = mat.standard_price
        elif costing_method == "FIFO" and getattr(mat, "fifo_layers", None):
            # Use the price of the oldest FIFO layer
            unit_cost = mat.fifo_layers[0].unit_price if mat.fifo_layers else mat.moving_avg_price
        else:
            unit_cost = mat.moving_avg_price
        total_val = (qty_dec * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        m = StockMovement(
            movement_id=f"MVT_{uuid.uuid4().hex[:8].upper()}",
            material_number=material_number,
            movement_type="601_GI_SALES_ORDER",
            quantity=qty_dec,
            unit_cost=unit_cost,
            total_valuation=total_val,
            plant=plant,
            storage_location=storage_location,
            bin_id=bin_id,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        self.movements.append(m)
        bin_loc.qty_on_hand -= qty_dec
        return m

    def physical_inventory_count(
        self,
        material_number: str,
        counted_quantity: Decimal | int | float,
        plant: str = "1000",
        storage_location: str = "0001",
        bin_id: str = "BIN-A1-01",
    ) -> Tuple[Decimal, Decimal, StockMovement]:
        """Reconciles physical count against book inventory, computing shrinkage or surplus."""
        mat = self.materials.get(material_number)
        if not mat:
            raise ValueError(f"Material {material_number} not found in Material Master")

        counted_dec = Decimal(str(counted_quantity))
        bin_loc = self._get_or_create_bin(plant, storage_location, bin_id, material_number)
        book_qty = bin_loc.qty_on_hand
        variance_qty = counted_dec - book_qty
        unit_cost = mat.moving_avg_price
        variance_val = (variance_qty * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        bin_loc.qty_on_hand = counted_dec
        mvt_type = "701_SURPLUS_ADJUST" if variance_qty >= 0 else "702_SHRINKAGE_ADJUST"

        m = StockMovement(
            movement_id=f"MVT_{uuid.uuid4().hex[:8].upper()}",
            material_number=material_number,
            movement_type=mvt_type,
            quantity=abs(variance_qty),
            unit_cost=unit_cost,
            total_valuation=abs(variance_val),
            plant=plant,
            storage_location=storage_location,
            bin_id=bin_id,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        self.movements.append(m)
        return variance_qty, variance_val, m

    def get_total_stock_value(self) -> Decimal:
        """Computes aggregate warehouse valuation at current moving average prices."""
        total = Decimal("0.00")
        for mat_id, mat in self.materials.items():
            qty = self.get_total_quantity_on_hand(mat_id)
            total += (qty * mat.moving_avg_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return total

    @classmethod
    def create_default(cls) -> WarehouseInventory:
        """Creates pre-seeded warehouse inventory with enterprise materials."""
        inv = cls()
        default_items = [
            MaterialMasterItem(
                material_number="MAT-1001",
                description="High-Precision Aluminum Alloy Sheet",
                standard_price=Decimal("45.00"),
                moving_avg_price=Decimal("45.00"),
                safety_stock_qty=500,
                reorder_point_qty=1000,
            ),
            MaterialMasterItem(
                material_number="MAT-1002",
                description="Titanium Fastener Assembly Pack",
                standard_price=Decimal("12.50"),
                moving_avg_price=Decimal("12.50"),
                safety_stock_qty=2000,
                reorder_point_qty=5000,
            ),
            MaterialMasterItem(
                material_number="MAT-2001",
                description="Industrial Servo Motor 2.5kW",
                standard_price=Decimal("420.00"),
                moving_avg_price=Decimal("420.00"),
                safety_stock_qty=50,
                reorder_point_qty=150,
            ),
            MaterialMasterItem(
                material_number="MAT-3001",
                description="Commercial Sensor Motherboard Unit",
                standard_price=Decimal("185.00"),
                moving_avg_price=Decimal("185.00"),
                safety_stock_qty=100,
                reorder_point_qty=300,
            ),
        ]
        for item in default_items:
            inv.register_material(item)
            # Initialize with opening stock
            inv.receive_goods(
                material_number=item.material_number,
                quantity=Decimal("500.00"),
                unit_cost=item.moving_avg_price,
            )
        return inv
