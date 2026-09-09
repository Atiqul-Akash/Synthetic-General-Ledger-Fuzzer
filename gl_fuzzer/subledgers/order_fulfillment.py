"""Stateful O2C sales order fulfillment linked to warehouse inventory and COGS."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.subledgers.inventory import WarehouseInventory


class SalesOrder(BaseModel):
    so_number: str
    customer_id: str
    material_number: str
    ordered_qty: Decimal
    unit_price: Decimal
    company_code: str = "1000"
    order_date: str
    currency: str = "USD"

    @property
    def total_order_value(self) -> Decimal:
        return (self.ordered_qty * self.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class DeliveryWaybill(BaseModel):
    waybill_number: str
    so_number: str
    shipped_qty: Decimal
    cogs_valuation: Decimal
    shipping_date: str


class SalesOrderFulfillmentEngine:
    """Operational O2C fulfillment simulator deriving authentic COGS and inventory decrements."""

    def __init__(self, inventory: Optional[WarehouseInventory] = None, coa: Optional[ChartOfAccounts] = None):
        self.inventory = inventory or WarehouseInventory.create_default()
        self.coa = coa or ChartOfAccounts.create_default()
        self.sales_orders: Dict[str, SalesOrder] = {}
        self.deliveries: Dict[str, List[DeliveryWaybill]] = {}

    def create_sales_order(
        self,
        customer_id: str,
        material_number: str,
        ordered_qty: Decimal | int | float,
        unit_price: Decimal | int | float,
        company_code: str = "1000",
        order_date: str = "2026-04-01",
    ) -> SalesOrder:
        so = SalesOrder(
            so_number=f"SO_{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            material_number=material_number,
            ordered_qty=Decimal(str(ordered_qty)),
            unit_price=Decimal(str(unit_price)),
            company_code=company_code,
            order_date=order_date,
        )
        self.sales_orders[so.so_number] = so
        self.deliveries[so.so_number] = []
        return so

    def post_goods_issue(
        self,
        so: SalesOrder,
        shipped_qty: Decimal | int | float,
        shipping_date: str = "2026-04-05",
    ) -> Tuple[DeliveryWaybill, JournalEntry]:
        """Issues goods out of warehouse, decrements stock, and computes COGS at actual moving average cost."""
        shipped_qty_dec = Decimal(str(shipped_qty))
        mvt = self.inventory.issue_goods(
            material_number=so.material_number,
            quantity=shipped_qty_dec,
        )

        cogs_amount = mvt.total_valuation
        doc_num = f"WA_{uuid.uuid4().hex[:8].upper()}"

        waybill = DeliveryWaybill(
            waybill_number=doc_num,
            so_number=so.so_number,
            shipped_qty=shipped_qty_dec,
            cogs_valuation=cogs_amount,
            shipping_date=shipping_date,
        )
        self.deliveries[so.so_number].append(waybill)

        # Voucher: Dr COGS - Inventory (50100) / Cr Finished Goods Inventory (14100)
        lines = [
            LineItem(
                line_id=f"{doc_num}_1",
                entry_id=doc_num,
                line_number=1,
                account_code="50100",
                account_name="Cost of Goods Sold - Inventory",
                debit_credit=DebitCredit.DEBIT,
                amount=cogs_amount,
                posting_key="40",
                cost_center="CC_OPS",
                material_number=so.material_number,
                customer_id=so.customer_id,
                line_text=f"COGS for Delivery {doc_num} (SO {so.so_number})",
            ),
            LineItem(
                line_id=f"{doc_num}_2",
                entry_id=doc_num,
                line_number=2,
                account_code="14100",
                account_name="Finished Goods Inventory",
                debit_credit=DebitCredit.CREDIT,
                amount=cogs_amount,
                posting_key="50",
                material_number=so.material_number,
                line_text=f"Stock Depletion for Delivery {doc_num}",
            ),
        ]

        entry = JournalEntry(
            entry_id=doc_num,
            batch_id="SUBLEDGER_O2C",
            company_code=so.company_code,
            document_type=DocumentType.WA,
            document_number=doc_num,
            posting_date=shipping_date,
            document_date=shipping_date,
            created_at=f"{shipping_date}T11:00:00Z",
            created_by="SHIPPING_LOGISTICS",
            reference=so.so_number,
            header_text=f"Goods Issue Delivery {doc_num}",
            business_cycle="O2C",
            lines=lines,
        )
        return waybill, entry

    def post_billing_document(
        self,
        so: SalesOrder,
        delivery: DeliveryWaybill,
        billing_date: str = "2026-04-06",
    ) -> JournalEntry:
        """Posts customer billing invoice (RV) matching delivery quantity."""
        gross_sales = (delivery.shipped_qty * so.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        doc_num = f"RV_{uuid.uuid4().hex[:8].upper()}"

        lines = [
            LineItem(
                line_id=f"{doc_num}_1",
                entry_id=doc_num,
                line_number=1,
                account_code="11000",
                account_name="Accounts Receivable - Trade",
                debit_credit=DebitCredit.DEBIT,
                amount=gross_sales,
                posting_key="01",
                customer_id=so.customer_id,
                line_text=f"Billing for SO {so.so_number} Delivery {delivery.waybill_number}",
            ),
            LineItem(
                line_id=f"{doc_num}_2",
                entry_id=doc_num,
                line_number=2,
                account_code="40000",
                account_name="Gross Product Sales Revenue",
                debit_credit=DebitCredit.CREDIT,
                amount=gross_sales,
                posting_key="50",
                customer_id=so.customer_id,
                material_number=so.material_number,
                line_text=f"Revenue recognition SO {so.so_number}",
            ),
        ]

        return JournalEntry(
            entry_id=doc_num,
            batch_id="SUBLEDGER_O2C",
            company_code=so.company_code,
            document_type=DocumentType.RV,
            document_number=doc_num,
            posting_date=billing_date,
            document_date=billing_date,
            created_at=f"{billing_date}T15:00:00Z",
            created_by="AR_BILLING_CLERK",
            reference=so.so_number,
            header_text=f"Billing Document SO {so.so_number}",
            business_cycle="O2C",
            lines=lines,
        )

    def post_customer_payment(
        self,
        billing_doc: JournalEntry,
        payment_date: str = "2026-04-20",
    ) -> JournalEntry:
        """Posts customer remittance payment (DZ), referencing and clearing the billing invoice."""
        payment_amount = billing_doc.total_debits
        doc_num = f"DZ_{uuid.uuid4().hex[:8].upper()}"
        customer_id = billing_doc.lines[0].customer_id if billing_doc.lines else None

        lines = [
            LineItem(
                line_id=f"{doc_num}_1",
                entry_id=doc_num,
                line_number=1,
                account_code="10100",
                account_name="Operating Cash & Bank",
                debit_credit=DebitCredit.DEBIT,
                amount=payment_amount,
                posting_key="40",
                line_text=f"Remittance clearing for {billing_doc.document_number}",
            ),
            LineItem(
                line_id=f"{doc_num}_2",
                entry_id=doc_num,
                line_number=2,
                account_code="11000",
                account_name="Accounts Receivable - Trade",
                debit_credit=DebitCredit.CREDIT,
                amount=payment_amount,
                posting_key="15",
                customer_id=customer_id,
                clearing_doc=billing_doc.document_number,
                line_text=f"AR Settled by {doc_num}",
            ),
        ]

        return JournalEntry(
            entry_id=doc_num,
            batch_id="SUBLEDGER_O2C",
            company_code=billing_doc.company_code,
            document_type=DocumentType.DZ,
            document_number=doc_num,
            posting_date=payment_date,
            document_date=payment_date,
            created_at=f"{payment_date}T09:15:00Z",
            created_by="TREASURY_CLERK",
            reference=billing_doc.document_number,
            header_text=f"Customer Remittance {billing_doc.document_number}",
            business_cycle="O2C",
            lines=lines,
        )
