"""Comprehensive unit tests for Operational Logistics & Stateful Subledgers."""

from decimal import Decimal
import pytest

from gl_fuzzer.models.journal import DebitCredit, DocumentType
from gl_fuzzer.models.manifest import AnomalyType
from gl_fuzzer.subledgers.inventory import (
    MaterialMasterItem,
    WarehouseInventory,
)
from gl_fuzzer.subledgers.three_way_match import (
    MatchResult,
    ThreeWayMatchingEngine,
)
from gl_fuzzer.subledgers.order_fulfillment import (
    SalesOrderFulfillmentEngine,
)
from gl_fuzzer.verification.invariants import InvariantVerifier


def test_material_master_creation():
    inv = WarehouseInventory.create_default()
    mat = inv.get_material("MAT-1001")
    assert mat is not None
    assert mat.standard_price == Decimal("45.00")
    assert mat.moving_avg_price == Decimal("45.00")


def test_warehouse_receive_goods_map_recalculation():
    inv = WarehouseInventory()
    mat = MaterialMasterItem(
        material_number="MAT-TEST",
        description="Test Component",
        standard_price=Decimal("10.00"),
        moving_avg_price=Decimal("10.00"),
    )
    inv.register_material(mat)

    # Initial receipt: 100 units at $10.00
    inv.receive_goods("MAT-TEST", quantity=Decimal("100"), unit_cost=Decimal("10.00"))
    assert mat.moving_avg_price == Decimal("10.00")

    # Second receipt: 100 units at $20.00
    # MAP = (100 * 10 + 100 * 20) / 200 = 3000 / 200 = $15.00
    inv.receive_goods("MAT-TEST", quantity=Decimal("100"), unit_cost=Decimal("20.00"))
    assert mat.moving_avg_price == Decimal("15.00")
    assert inv.get_total_quantity_on_hand("MAT-TEST") == Decimal("200.00")


def test_warehouse_issue_goods_decrements_stock():
    inv = WarehouseInventory.create_default()
    initial_qty = inv.get_total_quantity_on_hand("MAT-1001")

    mvt = inv.issue_goods("MAT-1001", quantity=Decimal("50.00"))
    assert mvt.quantity == Decimal("50.00")
    assert inv.get_total_quantity_on_hand("MAT-1001") == initial_qty - Decimal("50.00")


def test_warehouse_insufficient_stock_error():
    inv = WarehouseInventory.create_default()
    with pytest.raises(ValueError, match="Insufficient inventory"):
        inv.issue_goods("MAT-1001", quantity=Decimal("999999.00"))


def test_warehouse_physical_count_shrinkage_adjustment():
    inv = WarehouseInventory.create_default()
    # Count 480 instead of 500
    var_qty, var_val, mvt = inv.physical_inventory_count("MAT-1001", counted_quantity=Decimal("480.00"))
    assert var_qty == Decimal("-20.00")  # 20 units shrinkage
    assert mvt.movement_type == "702_SHRINKAGE_ADJUST"
    assert inv.get_total_quantity_on_hand("MAT-1001") == Decimal("480.00")


def test_three_way_match_perfect_match():
    twm = ThreeWayMatchingEngine()
    po = twm.create_purchase_order(vendor_id="VEND_01", material_number="MAT-1001", ordered_qty=Decimal("20.00"))

    gr, we_entry = twm.post_goods_receipt(po, received_qty=Decimal("20.00"))
    assert we_entry.is_balanced is True
    assert len(InvariantVerifier.verify_entry(we_entry)) == 0

    ir, re_entry, match_st = twm.post_invoice_receipt(
        po, gr, invoiced_qty=Decimal("20.00"), invoiced_unit_price=po.po_unit_price
    )
    assert match_st == MatchResult.PERFECT_MATCH
    assert re_entry.is_balanced is True
    assert len(InvariantVerifier.verify_entry(re_entry)) == 0


def test_three_way_match_price_variance_ppv_posting():
    twm = ThreeWayMatchingEngine()
    po = twm.create_purchase_order(
        vendor_id="VEND_01",
        material_number="MAT-1001",
        ordered_qty=Decimal("10.00"),
        po_unit_price=Decimal("45.00"),
    )
    gr, we = twm.post_goods_receipt(po, received_qty=Decimal("10.00"))

    # Invoice billed at $50.00 instead of $45.00 ($5.00/unit price variance)
    ir, re, match_st = twm.post_invoice_receipt(
        po, gr, invoiced_qty=Decimal("10.00"), invoiced_unit_price=Decimal("50.00")
    )
    assert match_st == MatchResult.PRICE_VARIANCE
    assert re.is_balanced is True

    ppv_leg = [l for l in re.lines if l.account_code == "52100"][0]
    assert ppv_leg.debit_credit == DebitCredit.DEBIT
    assert ppv_leg.amount == Decimal("50.00")  # 10 units * ($50 - $45)
    assert len(InvariantVerifier.verify_entry(re)) == 0


def test_three_way_match_phantom_invoice_anomaly_flag():
    twm = ThreeWayMatchingEngine()
    po = twm.create_purchase_order(vendor_id="VEND_01", material_number="MAT-1001", ordered_qty=Decimal("10.00"))

    # Invoice receipt with NO goods receipt (gr=None)
    ir, re, match_st = twm.post_invoice_receipt(
        po, gr=None, invoiced_qty=Decimal("10.00"), invoiced_unit_price=po.po_unit_price
    )
    assert match_st == MatchResult.PHANTOM_INVOICE
    assert re.is_anomaly is True
    assert AnomalyType.PHANTOM_PO_THREE_WAY_BYPASS.value in re.anomaly_ids


def test_sales_order_goods_issue_cogs_from_map():
    sfe = SalesOrderFulfillmentEngine()
    so = sfe.create_sales_order(
        customer_id="CUST_01",
        material_number="MAT-1001",
        ordered_qty=Decimal("10.00"),
        unit_price=Decimal("100.00"),
    )
    wb, wa = sfe.post_goods_issue(so, shipped_qty=Decimal("10.00"))
    assert wa.is_balanced is True
    assert wa.document_type == DocumentType.WA
    assert len(InvariantVerifier.verify_entry(wa)) == 0

    rv = sfe.post_billing_document(so, wb)
    assert rv.is_balanced is True
    assert rv.document_type == DocumentType.RV
    assert len(InvariantVerifier.verify_entry(rv)) == 0

    dz = sfe.post_customer_payment(rv)
    assert dz.is_balanced is True
    assert dz.document_type == DocumentType.DZ
    assert len(InvariantVerifier.verify_entry(dz)) == 0
