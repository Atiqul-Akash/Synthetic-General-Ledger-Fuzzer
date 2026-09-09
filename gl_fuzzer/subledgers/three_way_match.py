"""Stateful 3-way matching engine linking PO, Goods Receipt, and Invoice Receipt."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyType
from gl_fuzzer.subledgers.inventory import WarehouseInventory


class MatchResult(str, Enum):
    PERFECT_MATCH = "PERFECT_MATCH"
    QUANTITY_VARIANCE = "QUANTITY_VARIANCE"
    PRICE_VARIANCE = "PRICE_VARIANCE"
    DUAL_VARIANCE = "DUAL_VARIANCE"
    PHANTOM_INVOICE = "PHANTOM_INVOICE"


class PurchaseOrder(BaseModel):
    po_number: str
    vendor_id: str
    material_number: str
    ordered_qty: Decimal
    po_unit_price: Decimal
    company_code: str = "1000"
    posting_date: str
    currency: str = "USD"

    @property
    def total_commitment(self) -> Decimal:
        return (self.ordered_qty * self.po_unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class GoodsReceipt(BaseModel):
    gr_number: str
    po_number: str
    received_qty: Decimal
    actual_unit_cost: Decimal
    gr_date: str
    material_document: str


class InvoiceReceipt(BaseModel):
    invoice_number: str
    po_number: str
    invoiced_qty: Decimal
    invoiced_unit_price: Decimal
    invoice_date: str


class ThreeWayMatchingEngine:
    """Operational P2P 3-way matching engine generating realistic GR/IR clearing and PPV vouchers."""

    def __init__(self, inventory: Optional[WarehouseInventory] = None, coa: Optional[ChartOfAccounts] = None):
        self.inventory = inventory or WarehouseInventory.create_default()
        self.coa = coa or ChartOfAccounts.create_default()
        self.purchase_orders: Dict[str, PurchaseOrder] = {}
        self.goods_receipts: Dict[str, List[GoodsReceipt]] = {}  # po_number -> list of GRs
        self.invoices: Dict[str, List[InvoiceReceipt]] = {}

    def create_purchase_order(
        self,
        vendor_id: str,
        material_number: str,
        ordered_qty: Decimal | int | float,
        po_unit_price: Optional[Decimal | int | float] = None,
        company_code: str = "1000",
        posting_date: str = "2026-03-10",
    ) -> PurchaseOrder:
        """Issues an official corporate purchase order."""
        mat = self.inventory.get_material(material_number)
        ordered_qty_dec = Decimal(str(ordered_qty))
        price = Decimal(str(po_unit_price)) if po_unit_price is not None else (mat.moving_avg_price if mat else Decimal("50.00"))

        po = PurchaseOrder(
            po_number=f"PO_{uuid.uuid4().hex[:8].upper()}",
            vendor_id=vendor_id,
            material_number=material_number,
            ordered_qty=ordered_qty_dec,
            po_unit_price=price,
            company_code=company_code,
            posting_date=posting_date,
        )
        self.purchase_orders[po.po_number] = po
        self.goods_receipts[po.po_number] = []
        self.invoices[po.po_number] = []
        return po

    def post_goods_receipt(
        self,
        po: PurchaseOrder,
        received_qty: Decimal | int | float,
        actual_unit_cost: Optional[Decimal | int | float] = None,
        gr_date: str = "2026-03-15",
    ) -> Tuple[GoodsReceipt, JournalEntry]:
        """Receives goods at warehouse dock, updates physical inventory, and generates WE voucher."""
        rec_qty_dec = Decimal(str(received_qty))
        unit_cost = Decimal(str(actual_unit_cost)) if actual_unit_cost is not None else po.po_unit_price
        mvt = self.inventory.receive_goods(
            material_number=po.material_number,
            quantity=rec_qty_dec,
            unit_cost=unit_cost,
        )

        gr = GoodsReceipt(
            gr_number=f"WE_{uuid.uuid4().hex[:8].upper()}",
            po_number=po.po_number,
            received_qty=received_qty,
            actual_unit_cost=unit_cost,
            gr_date=gr_date,
            material_document=mvt.movement_id,
        )
        self.goods_receipts[po.po_number].append(gr)

        # Generate accounting voucher: Dr Raw Materials (14000) / Cr GR/IR Clearing (21150)
        total_val = (received_qty * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        doc_num = f"WE_{uuid.uuid4().hex[:8].upper()}"

        lines = [
            LineItem(
                line_id=f"{doc_num}_1",
                entry_id=doc_num,
                line_number=1,
                account_code="14000",
                account_name="Raw Materials Inventory",
                debit_credit=DebitCredit.DEBIT,
                amount=total_val,
                posting_key="89",
                material_number=po.material_number,
                vendor_id=po.vendor_id,
                line_text=f"GR for {po.material_number} - {po.po_number}",
            ),
            LineItem(
                line_id=f"{doc_num}_2",
                entry_id=doc_num,
                line_number=2,
                account_code="21150",
                account_name="GR/IR Subledger Bridge Clearing",
                debit_credit=DebitCredit.CREDIT,
                amount=total_val,
                posting_key="96",
                material_number=po.material_number,
                vendor_id=po.vendor_id,
                line_text=f"GR/IR Provision for {po.po_number}",
            ),
        ]

        entry = JournalEntry(
            entry_id=doc_num,
            batch_id="SUBLEDGER_P2P",
            company_code=po.company_code,
            document_type=DocumentType.WE,
            document_number=doc_num,
            posting_date=gr_date,
            document_date=gr_date,
            created_at=f"{gr_date}T10:00:00Z",
            created_by="WAREHOUSE_MGR",
            reference=po.po_number,
            header_text=f"Goods Receipt PO {po.po_number}",
            business_cycle="P2P",
            lines=lines,
        )
        return gr, entry

    def post_invoice_receipt(
        self,
        po: PurchaseOrder,
        gr: Optional[GoodsReceipt],
        invoiced_qty: Decimal | int | float,
        invoiced_unit_price: Decimal | int | float,
        invoice_date: str = "2026-03-20",
    ) -> Tuple[InvoiceReceipt, JournalEntry, MatchResult]:
        """Evaluates 3-way match, handles Price Variance (PPV), and generates RE voucher."""
        doc_num = f"RE_{uuid.uuid4().hex[:8].upper()}"
        inv_qty_dec = Decimal(str(invoiced_qty))
        inv_price_dec = Decimal(str(invoiced_unit_price))

        inv = InvoiceReceipt(
            invoice_number=doc_num,
            po_number=po.po_number,
            invoiced_qty=inv_qty_dec,
            invoiced_unit_price=inv_price_dec,
            invoice_date=invoice_date,
        )
        self.invoices[po.po_number].append(inv)

        # Check match status
        if gr is None:
            match_status = MatchResult.PHANTOM_INVOICE
        else:
            qty_var = inv_qty_dec != gr.received_qty
            price_var = inv_price_dec != po.po_unit_price
            if qty_var and price_var:
                match_status = MatchResult.DUAL_VARIANCE
            elif price_var:
                match_status = MatchResult.PRICE_VARIANCE
            elif qty_var:
                match_status = MatchResult.QUANTITY_VARIANCE
            else:
                match_status = MatchResult.PERFECT_MATCH

        # Valuation legs
        gr_base_price = po.po_unit_price
        gr_clearing_qty = min(inv_qty_dec, gr.received_qty) if gr is not None else inv_qty_dec
        gr_clearing_amount = (gr_clearing_qty * gr_base_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_vendor_due = (inv_qty_dec * inv_price_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ppv_delta = total_vendor_due - gr_clearing_amount

        lines = [
            # Leg 1: Clear GR/IR Account at standard PO expected cost
            LineItem(
                line_id=f"{doc_num}_1",
                entry_id=doc_num,
                line_number=1,
                account_code="21150",
                account_name="GR/IR Subledger Bridge Clearing",
                debit_credit=DebitCredit.DEBIT,
                amount=gr_clearing_amount,
                posting_key="86",
                vendor_id=po.vendor_id,
                material_number=po.material_number,
                line_text=f"GR/IR Clear for PO {po.po_number}",
            )
        ]

        # Leg 2: Price Variance (PPV) allocation if price discrepancy exists
        if ppv_delta > Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{doc_num}_2",
                    entry_id=doc_num,
                    line_number=2,
                    account_code="52100",
                    account_name="Purchase Price Variance - Materials",
                    debit_credit=DebitCredit.DEBIT,
                    amount=ppv_delta,
                    posting_key="40",
                    cost_center="CC_MFG",
                    vendor_id=po.vendor_id,
                    line_text=f"PPV Unfavorable Variance PO {po.po_number}",
                )
            )
        elif ppv_delta < Decimal("0.00"):
            lines.append(
                LineItem(
                    line_id=f"{doc_num}_2",
                    entry_id=doc_num,
                    line_number=2,
                    account_code="52100",
                    account_name="Purchase Price Variance - Materials",
                    debit_credit=DebitCredit.CREDIT,
                    amount=abs(ppv_delta),
                    posting_key="50",
                    cost_center="CC_MFG",
                    vendor_id=po.vendor_id,
                    line_text=f"PPV Favorable Variance PO {po.po_number}",
                )
            )

        # Leg 3: Credit Accounts Payable - Trade
        lines.append(
            LineItem(
                line_id=f"{doc_num}_3",
                entry_id=doc_num,
                line_number=len(lines) + 1,
                account_code="20000",
                account_name="Accounts Payable - Trade",
                debit_credit=DebitCredit.CREDIT,
                amount=total_vendor_due,
                posting_key="31",
                vendor_id=po.vendor_id,
                line_text=f"Vendor Invoice PO {po.po_number}",
            )
        )

        entry = JournalEntry(
            entry_id=doc_num,
            batch_id="SUBLEDGER_P2P",
            company_code=po.company_code,
            document_type=DocumentType.RE,
            document_number=doc_num,
            posting_date=invoice_date,
            document_date=invoice_date,
            created_at=f"{invoice_date}T14:30:00Z",
            created_by="AP_CLERK",
            reference=po.po_number,
            header_text=f"Invoice Receipt PO {po.po_number} ({match_status.value})",
            business_cycle="P2P",
            lines=lines,
        )

        if match_status == MatchResult.PHANTOM_INVOICE:
            entry.is_anomaly = True
            entry.anomaly_ids.append(AnomalyType.PHANTOM_PO_THREE_WAY_BYPASS.value)
            entry.header_text += " [ANOM_PHANTOM_PO]"

        return inv, entry, match_status
