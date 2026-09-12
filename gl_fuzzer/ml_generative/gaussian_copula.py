"""Gaussian Copula Generative ML Synthesizer for multivariate tabular GL distributions."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
import uuid
import numpy as np
from scipy import stats

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem


class GaussianCopulaSynthesizer:
    """Generative tabular synthesizer modeling non-linear joint dependency structures via Gaussian Copula."""

    def __init__(self, seed: Optional[int] = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.feature_names: List[str] = ["amount", "line_count", "day_of_month"]
        self.marginal_data: Dict[str, np.ndarray] = {}
        self.cov_matrix: Optional[np.ndarray] = None
        self.is_fitted: bool = False
        self.categories: Dict[str, List[str]] = {
            "business_cycle": ["P2P", "O2C", "R2R"],
            "currency": ["USD", "EUR", "GBP"],
        }
        self.cat_probs: Dict[str, np.ndarray] = {}

    def fit(self, entries: List[JournalEntry]) -> GaussianCopulaSynthesizer:
        """Fits empirical marginal distributions and normal correlation matrix from baseline entries."""
        if not entries:
            # Generate default baseline observations if empty
            amounts = np.array([float(np.exp(self.rng.normal(7.5, 1.2))) for _ in range(200)])
            line_counts = np.array([float(self.rng.choice([2, 4, 6, 8], p=[0.7, 0.15, 0.1, 0.05])) for _ in range(200)])
            days = np.array([float(self.rng.integers(1, 29)) for _ in range(200)])
        else:
            amounts = []
            line_counts = []
            days = []
            cycle_counts: Dict[str, int] = {c: 0 for c in self.categories["business_cycle"]}

            for entry in entries:
                amounts.append(float(entry.total_debits))
                line_counts.append(float(len(entry.lines)))
                try:
                    dt = datetime.fromisoformat(entry.posting_date)
                    days.append(float(dt.day))
                except Exception:
                    days.append(15.0)

                cyc = entry.business_cycle if entry.business_cycle in cycle_counts else "R2R"
                cycle_counts[cyc] += 1

            amounts = np.array(amounts)
            line_counts = np.array(line_counts)
            days = np.array(days)

            # Fit categorical probabilities
            total_cyc = sum(cycle_counts.values()) or 1
            self.cat_probs["business_cycle"] = np.array([cycle_counts[c] / total_cyc for c in self.categories["business_cycle"]])

        self.marginal_data["amount"] = np.sort(amounts)
        self.marginal_data["line_count"] = np.sort(line_counts)
        self.marginal_data["day_of_month"] = np.sort(days)

        # 1. Map to Uniform via empirical rank transform (Probability Integral Transform)
        n = len(amounts)
        u_matrix = np.zeros((n, len(self.feature_names)))

        for i, col in enumerate(self.feature_names):
            ranks = stats.rankdata(self.marginal_data[col])
            # Scale to (0, 1) strictly avoiding boundary 0 and 1
            u_matrix[:, i] = (ranks - 0.5) / n

        # 2. Map Uniform to standard Normal scores: Z = Phi^-1(U)
        z_matrix = stats.norm.ppf(u_matrix)

        # 3. Estimate Covariance / Correlation Matrix with Tikhonov regularization
        corr = np.corrcoef(z_matrix, rowvar=False)
        # Ensure positive semi-definite
        corr = (corr + corr.T) / 2.0
        np.fill_diagonal(corr, 1.0)
        corr += 1e-4 * np.eye(len(self.feature_names))

        self.cov_matrix = corr
        self.is_fitted = True
        return self

    def sample(self, count: int = 100, perturb_latent: bool = False, perturbation_scale: float = 2.5) -> List[Dict[str, Any]]:
        """Samples synthetic feature tuples from the fitted Gaussian Copula."""
        if not self.is_fitted:
            self.fit([])

        d = len(self.feature_names)
        mean = np.zeros(d)
        if perturb_latent:
            # Shift latent mean to low-density tail regions
            mean = self.rng.choice([-1.0, 1.0], size=d) * perturbation_scale

        # 1. Sample Z from multivariate normal N(mean, cov)
        z_samples = self.rng.multivariate_normal(mean=mean, cov=self.cov_matrix, size=count)

        # 2. Invert to Uniform via standard normal CDF: U = Phi(Z)
        u_samples = stats.norm.cdf(z_samples)
        # Clip to prevent out-of-range indexing
        u_samples = np.clip(u_samples, 1e-5, 1.0 - 1e-5)

        records: List[Dict[str, Any]] = []
        for row in range(count):
            item = {}
            for col_idx, col_name in enumerate(self.feature_names):
                sorted_vals = self.marginal_data[col_name]
                q = u_samples[row, col_idx]
                val = float(np.quantile(sorted_vals, q))
                if col_name == "line_count":
                    item[col_name] = max(2, int(round(val)) // 2 * 2)  # Ensure even line count
                elif col_name == "day_of_month":
                    item[col_name] = max(1, min(28, int(round(val))))
                else:
                    item[col_name] = max(10.0, round(val, 2))

            # Sample categorical cycle
            probs = self.cat_probs.get("business_cycle", np.array([0.4, 0.4, 0.2]))
            item["business_cycle"] = str(self.rng.choice(self.categories["business_cycle"], p=probs))
            item["is_perturbed"] = perturb_latent
            records.append(item)

        return records

    def synthesize_journal_entries(
        self,
        count: int = 100,
        perturb_latent: bool = False,
        perturbation_scale: float = 2.5,
        coa: Optional[ChartOfAccounts] = None,
        company_code: str = "1000",
    ) -> List[JournalEntry]:
        """Synthesizes balanced double-entry vouchers from copula samples."""
        coa = coa or ChartOfAccounts.create_default()
        samples = self.sample(count=count, perturb_latent=perturb_latent, perturbation_scale=perturbation_scale)

        entries: List[JournalEntry] = []
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Map cycles to typical accounts
        cycle_account_map = {
            "P2P": ("50000", "Cost of Goods Sold - Materials", "20000", "Accounts Payable - Trade"),
            "O2C": ("11000", "Accounts Receivable - Trade", "40000", "Gross Product Sales Revenue"),
            "R2R": ("61000", "Salaries & Wages Expense", "10100", "Operating Cash & Bank"),
        }

        for i, s in enumerate(samples):
            amt = Decimal(str(s["amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            day = s["day_of_month"]
            cyc = s["business_cycle"]
            is_anom = s.get("is_perturbed", False)

            dr_acc, dr_name, cr_acc, cr_name = cycle_account_map.get(cyc, cycle_account_map["R2R"])
            doc_date = f"2026-09-{day:02d}"
            entry_id = f"DOC_COPULA_{i+1:06d}"

            entry = JournalEntry(
                entry_id=entry_id,
                batch_id=f"BATCH_COPULA_{20260900 + day}",
                company_code=company_code,
                document_type=DocumentType.SA,
                document_number=f"CP{i+1:08d}",
                posting_date=doc_date,
                document_date=doc_date,
                created_at=now_utc,
                header_text=f"Copula Synthesized Voucher #{i+1}",
                business_cycle=cyc,
                is_anomaly=is_anom,
                anomaly_ids=["ANOM_LATENT_MANIFOLD_PERTURBATION"] if is_anom else [],
                lines=[
                    LineItem(
                        line_id=f"{entry_id}-001",
                        entry_id=entry_id,
                        line_number=1,
                        account_code=dr_acc,
                        account_name=dr_name,
                        debit_credit=DebitCredit.DEBIT,
                        amount=amt,
                        line_text=f"Copula leg debit: {cyc}",
                    ),
                    LineItem(
                        line_id=f"{entry_id}-002",
                        entry_id=entry_id,
                        line_number=2,
                        account_code=cr_acc,
                        account_name=cr_name,
                        debit_credit=DebitCredit.CREDIT,
                        amount=amt,
                        line_text=f"Copula leg credit: {cyc}",
                    ),
                ],
            )
            entries.append(entry)

        return entries
