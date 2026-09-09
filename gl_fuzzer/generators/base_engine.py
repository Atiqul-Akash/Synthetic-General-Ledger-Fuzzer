"""Master Base Synthesis Engine orchestrating clean, balanced GL transaction batches."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
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
    ):
        self.coa = coa or ChartOfAccounts.create_default()
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.company_codes = company_codes or ["1000", "2000", "3000"]

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
        now_iso = datetime.now().isoformat()

        entries: List[JournalEntry] = []

        while len(entries) < target_entry_count:
            # Accounting cycle distribution: ~45% P2P, ~45% O2C, ~10% R2R
            roll = self.rng.random()
            if roll < 0.45:
                # P2P: Either full 3-step flow or single invoice
                if self.rng.random() < 0.60 and (target_entry_count - len(entries)) >= 3:
                    p2p_entries = self.p2p_gen.generate_full_p2p_flow(batch_id=b_id, company_code=cmp)
                    entries.extend(p2p_entries)
                else:
                    entry = self.p2p_gen.generate_single_vendor_invoice(batch_id=b_id, company_code=cmp)
                    entries.append(entry)
            elif roll < 0.90:
                # O2C: Full 3-step flow or single customer invoice
                if (target_entry_count - len(entries)) >= 3:
                    if self.rng.random() < 0.70:
                        o2c_entries = self.o2c_gen.generate_full_o2c_flow(batch_id=b_id, company_code=cmp)
                        entries.extend(o2c_entries)
                    else:
                        entry = self.o2c_gen.generate_single_customer_invoice(batch_id=b_id, company_code=cmp)
                        entries.append(entry)
                else:
                    # fallback single customer invoice
                    entry = self.o2c_gen.generate_single_customer_invoice(batch_id=b_id, company_code=cmp)
                    entries.append(entry)
            else:
                # R2R: Depreciation, Accrual, or Payroll
                r2r_choice = self.rng.integers(0, 3)
                if r2r_choice == 0:
                    entries.append(self.r2r_gen.generate_depreciation_run(batch_id=b_id, company_code=cmp))
                elif r2r_choice == 1:
                    entries.append(self.r2r_gen.generate_operating_accrual(batch_id=b_id, company_code=cmp))
                else:
                    entries.append(self.r2r_gen.generate_payroll_run(batch_id=b_id, company_code=cmp))

        # Trim exact target count if slightly exceeded
        batch_entries = entries[:target_entry_count]

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
