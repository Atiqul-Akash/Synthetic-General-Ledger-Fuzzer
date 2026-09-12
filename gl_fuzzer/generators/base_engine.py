"""Master Base Synthesis Engine orchestrating clean, balanced GL transaction batches."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
import uuid
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, JournalEntry
from gl_fuzzer.generators.distributions import BusinessCalendar, LogNormalAmountGenerator
from gl_fuzzer.generators.p2p_cycle import P2PCycleGenerator
from gl_fuzzer.generators.o2c_cycle import O2CCycleGenerator
from gl_fuzzer.generators.r2r_cycle import R2RCycleGenerator


class BaseSynthesisEngine:
    """Master engine for synthesizing baseline, perfectly balanced GL batches."""

    def __init__(
        self,
        coa: Optional[ChartOfAccounts] = None,
        seed: Optional[int] = None,
        company_codes: Optional[List[str]] = None,
        tax_engine: Optional[Any] = None,
        inventory: Optional[Any] = None,
        three_way_match: Optional[Any] = None,
        sales_fulfillment: Optional[Any] = None,
        erp_connector: Optional[Any] = None,
    ):
        self.company_codes = company_codes or ["1000", "2000", "3000"]
        if erp_connector is not None:
            self.coa = erp_connector.fetch_chart_of_accounts(self.company_codes[0])
        else:
            self.coa = coa or ChartOfAccounts.create_default()

        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.tax_engine = tax_engine
        self.inventory = inventory
        self.three_way_match = three_way_match
        self.sales_fulfillment = sales_fulfillment
        self.erp_connector = erp_connector

        self.calendar = BusinessCalendar(rng=self.rng)
        self.amount_gen = LogNormalAmountGenerator(rng=self.rng)

        self.p2p_gen = P2PCycleGenerator(coa=self.coa, calendar=self.calendar, amount_gen=self.amount_gen, rng=self.rng)
        self.o2c_gen = O2CCycleGenerator(coa=self.coa, calendar=self.calendar, amount_gen=self.amount_gen, rng=self.rng)
        self.r2r_gen = R2RCycleGenerator(coa=self.coa, calendar=self.calendar, amount_gen=self.amount_gen, rng=self.rng)

    def generate_batch(
        self,
        batch_id: Optional[str] = None,
        target_entry_count: int = 100,
        company_code: Optional[str] = None,
    ) -> Batch:
        """Generates a batch of valid, balanced journal entries across all standard accounting cycles."""
        b_id = batch_id or f"BATCH_{uuid.uuid4().hex[:8].upper()}"
        cmp = company_code or str(self.rng.choice(self.company_codes))
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entries: List[JournalEntry] = []

        while len(entries) < target_entry_count:
            # Accounting cycle distribution: ~45% P2P, ~45% O2C, ~10% R2R
            roll = self.rng.random()
            if roll < 0.45:
                # P2P: Either full 3-step flow or single invoice
                if self.rng.random() < 0.60 and (target_entry_count - len(entries)) >= 3:
                    if self.three_way_match is not None:
                        mat_keys = list(self.inventory.materials.keys()) if self.inventory else ["MAT-1001"]
                        mat_id = str(self.rng.choice(mat_keys))
                        qty = Decimal(str(int(self.rng.integers(5, 50))))
                        po = self.three_way_match.create_purchase_order(
                            vendor_id=f"VEND_{self.rng.integers(100, 200)}",
                            material_number=mat_id,
                            ordered_qty=qty,
                            company_code=cmp,
                        )
                        gr, we = self.three_way_match.post_goods_receipt(po, qty)
                        ir, re, _ = self.three_way_match.post_invoice_receipt(po, gr, qty, po.po_unit_price)
                        kz = self.p2p_gen.generate_vendor_payment(batch_id=b_id, invoice_entry=re, company_code=cmp)
                        entries.extend([we, re, kz])
                    else:
                        p2p_entries = self.p2p_gen.generate_full_p2p_flow(batch_id=b_id, company_code=cmp)
                        entries.extend(p2p_entries)
                else:
                    entry = self.p2p_gen.generate_single_vendor_invoice(batch_id=b_id, company_code=cmp)
                    if self.tax_engine is not None:
                        entry = self.tax_engine.apply_tax_to_entry(entry, is_purchase=True)
                    entries.append(entry)
            elif roll < 0.90:
                # O2C: Full 3-step flow or single customer invoice
                if (target_entry_count - len(entries)) >= 3:
                    if self.rng.random() < 0.70:
                        if self.sales_fulfillment is not None:
                            mat_keys = list(self.inventory.materials.keys()) if self.inventory else ["MAT-1001"]
                            mat_id = str(self.rng.choice(mat_keys))
                            qty = Decimal(str(int(self.rng.integers(2, 20))))
                            so = self.sales_fulfillment.create_sales_order(
                                customer_id=f"CUST_{self.rng.integers(100, 200)}",
                                material_number=mat_id,
                                ordered_qty=qty,
                                unit_price=Decimal("120.00"),
                                company_code=cmp,
                            )
                            wb, wa = self.sales_fulfillment.post_goods_issue(so, qty)
                            rv = self.sales_fulfillment.post_billing_document(so, wb)
                            if self.tax_engine is not None:
                                rv = self.tax_engine.apply_tax_to_entry(rv, is_purchase=False)
                            dz = self.sales_fulfillment.post_customer_payment(rv)
                            entries.extend([wa, rv, dz])
                        else:
                            o2c_entries = self.o2c_gen.generate_full_o2c_flow(batch_id=b_id, company_code=cmp)
                            entries.extend(o2c_entries)
                    else:
                        entry = self.o2c_gen.generate_single_customer_invoice(batch_id=b_id, company_code=cmp)
                        if self.tax_engine is not None:
                            entry = self.tax_engine.apply_tax_to_entry(entry, is_purchase=False)
                        entries.append(entry)
                else:
                    # fallback single customer invoice
                    entry = self.o2c_gen.generate_single_customer_invoice(batch_id=b_id, company_code=cmp)
                    if self.tax_engine is not None:
                        entry = self.tax_engine.apply_tax_to_entry(entry, is_purchase=False)
                    entries.append(entry)
            else:
                # R2R: Depreciation, Accrual, Payroll, or FAGL_FCV FX Revaluation
                rem = target_entry_count - len(entries)
                r2r_choice = self.rng.integers(0, 4) if rem >= 2 else self.rng.integers(0, 3)
                if r2r_choice == 0:
                    entries.append(self.r2r_gen.generate_depreciation_run(batch_id=b_id, company_code=cmp))
                elif r2r_choice == 1:
                    entries.append(self.r2r_gen.generate_operating_accrual(batch_id=b_id, company_code=cmp))
                elif r2r_choice == 2:
                    entries.append(self.r2r_gen.generate_payroll_run(batch_id=b_id, company_code=cmp))
                else:
                    entries.extend(self.r2r_gen.generate_fagl_fcv_run(batch_id=b_id, company_code=cmp))

        # Trim exact target count if slightly exceeded
        batch_entries = entries[:target_entry_count]

        # Order entries chronologically across business cycles
        batch_entries.sort(key=lambda e: (e.posting_date, getattr(e, "entry_time", "00:00:00") or "00:00:00"))

        return Batch(
            batch_id=b_id,
            source_system="SAP_S4HANA_SIM",
            created_at=now_iso,
            entries=batch_entries,
        )

    def generate_multiple_batches(self, num_batches: int = 5, entries_per_batch: int = 200) -> List[Batch]:
        """Generates multiple sequential batches."""
        batches = []
        for i in range(num_batches):
            b_id = f"BATCH_{20260900 + i:08d}"
            cmp = self.company_codes[i % len(self.company_codes)]
            batches.append(self.generate_batch(batch_id=b_id, target_entry_count=entries_per_batch, company_code=cmp))
        return batches
