"""Pure NumPy Tabular Variational Autoencoder (TVAE) Engine for GL Synthesis & Anomaly Injection."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem


class TabularVAESynthesizer:
    """Tabular Variational Autoencoder (TVAE) implemented with analytical gradients in pure NumPy."""

    def __init__(
        self,
        input_dim: int = 4,
        latent_dim: int = 2,
        hidden_dim: int = 16,
        learning_rate: float = 0.01,
        beta_kl: float = 0.1,
        seed: Optional[int] = 42,
    ):
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.learning_rate = learning_rate
        self.beta_kl = beta_kl
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Normalization parameters
        self.mean_x: Optional[np.ndarray] = None
        self.std_x: Optional[np.ndarray] = None

        # Weights initialization (Xavier / He)
        scale_enc = np.sqrt(2.0 / (input_dim + hidden_dim))
        self.W_enc = self.rng.normal(0, scale_enc, (input_dim, hidden_dim))
        self.b_enc = np.zeros(hidden_dim)

        scale_mu = np.sqrt(2.0 / (hidden_dim + latent_dim))
        self.W_mu = self.rng.normal(0, scale_mu, (hidden_dim, latent_dim))
        self.b_mu = np.zeros(latent_dim)

        self.W_logvar = self.rng.normal(0, scale_mu, (hidden_dim, latent_dim))
        self.b_logvar = np.zeros(latent_dim)

        scale_dec = np.sqrt(2.0 / (latent_dim + hidden_dim))
        self.W_dec = self.rng.normal(0, scale_dec, (latent_dim, hidden_dim))
        self.b_dec = np.zeros(hidden_dim)

        scale_out = np.sqrt(2.0 / (hidden_dim + input_dim))
        self.W_out = self.rng.normal(0, scale_out, (hidden_dim, input_dim))
        self.b_out = np.zeros(input_dim)

        # Adam optimizer moments
        self.m: Dict[str, np.ndarray] = {}
        self.v: Dict[str, np.ndarray] = {}
        for param in ["W_enc", "b_enc", "W_mu", "b_mu", "W_logvar", "b_logvar", "W_dec", "b_dec", "W_out", "b_out"]:
            shape = getattr(self, param).shape
            self.m[param] = np.zeros(shape)
            self.v[param] = np.zeros(shape)
        self.t: int = 0
        self.is_fitted: bool = False

    def _encode(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        h = np.tanh(X @ self.W_enc + self.b_enc)
        mu = h @ self.W_mu + self.b_mu
        logvar = np.clip(h @ self.W_logvar + self.b_logvar, -10.0, 10.0)
        return h, mu, logvar

    def _decode(self, z: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        h_dec = np.tanh(z @ self.W_dec + self.b_dec)
        x_recon = h_dec @ self.W_out + self.b_out
        return h_dec, x_recon

    def fit(self, X: Optional[np.ndarray] = None, epochs: int = 25, batch_size: int = 32) -> TabularVAESynthesizer:
        """Trains the TVAE parameters via mini-batch SGD with Adam optimizer."""
        if X is None or len(X) < 10:
            # Synthetic feature matrix: [log_amount, line_count, day_of_month, cycle_idx]
            n_samples = 300
            log_amt = self.rng.normal(7.5, 1.2, (n_samples, 1))
            line_cnt = self.rng.choice([2.0, 4.0, 6.0], size=(n_samples, 1), p=[0.7, 0.2, 0.1])
            days = self.rng.uniform(1.0, 28.0, (n_samples, 1))
            cycles = self.rng.choice([0.0, 1.0, 2.0], size=(n_samples, 1))
            X = np.hstack([log_amt, line_cnt, days, cycles])

        self.mean_x = np.mean(X, axis=0)
        self.std_x = np.std(X, axis=0)
        self.std_x[self.std_x == 0] = 1.0
        X_norm = (X - self.mean_x) / self.std_x

        n_samples = len(X_norm)
        beta1, beta2, eps = 0.9, 0.999, 1e-8

        for _ in range(epochs):
            indices = self.rng.permutation(n_samples)
            X_shuffled = X_norm[indices]

            for b in range(0, n_samples, batch_size):
                xb = X_shuffled[b : b + batch_size]
                bsize = len(xb)
                if bsize == 0:
                    continue

                # Forward pass
                h_enc, mu, logvar = self._encode(xb)
                std = np.exp(0.5 * logvar)
                eps_noise = self.rng.normal(0, 1, mu.shape)
                z = mu + std * eps_noise
                h_dec, x_recon = self._decode(z)

                # Gradients: Loss = 0.5 * MSE + beta_kl * KL
                # dL / dx_recon
                dx_recon = (x_recon - xb) / bsize

                # Decoder gradients
                dW_out = h_dec.T @ dx_recon
                db_out = np.sum(dx_recon, axis=0)

                dh_dec = dx_recon @ self.W_out.T * (1.0 - h_dec**2)
                dW_dec = z.T @ dh_dec
                db_dec = np.sum(dh_dec, axis=0)

                dz = dh_dec @ self.W_dec.T

                # KL divergence gradients: dKL/dmu = mu, dKL/dlogvar = 0.5 * (exp(logvar) - 1)
                dmu = dz + self.beta_kl * mu / bsize
                dlogvar = dz * (std * eps_noise * 0.5) + self.beta_kl * 0.5 * (np.exp(logvar) - 1.0) / bsize

                # Encoder gradients
                dh_enc = (dmu @ self.W_mu.T + dlogvar @ self.W_logvar.T) * (1.0 - h_enc**2)
                dW_mu = h_enc.T @ dmu
                db_mu = np.sum(dmu, axis=0)

                dW_logvar = h_enc.T @ dlogvar
                db_logvar = np.sum(dlogvar, axis=0)

                dW_enc = xb.T @ dh_enc
                db_enc = np.sum(dh_enc, axis=0)

                # Adam update
                self.t += 1
                grads = {
                    "W_enc": dW_enc, "b_enc": db_enc,
                    "W_mu": dW_mu, "b_mu": db_mu,
                    "W_logvar": dW_logvar, "b_logvar": db_logvar,
                    "W_dec": dW_dec, "b_dec": db_dec,
                    "W_out": dW_out, "b_out": db_out,
                }
                for k, g in grads.items():
                    # Clip gradients for stability
                    g = np.clip(g, -5.0, 5.0)
                    self.m[k] = beta1 * self.m[k] + (1 - beta1) * g
                    self.v[k] = beta2 * self.v[k] + (1 - beta2) * (g**2)
                    m_hat = self.m[k] / (1 - beta1**self.t)
                    v_hat = self.v[k] / (1 - beta2**self.t)
                    param = getattr(self, k)
                    param -= self.learning_rate * m_hat / (np.sqrt(v_hat) + eps)

        self.is_fitted = True
        return self

    def sample(self, count: int = 50, perturb_manifold: bool = False, perturbation_scale: float = 3.0) -> np.ndarray:
        """Samples synthetic GL features from standard normal prior p(z) or adversarial boundary."""
        if not self.is_fitted:
            self.fit()

        if perturb_manifold:
            # Boundary manifold perturbation: sample outside 2.5 sigma
            z = self.rng.normal(0, 1, (count, self.latent_dim))
            direction = z / np.linalg.norm(z, axis=1, keepdims=True)
            z = direction * perturbation_scale
        else:
            z = self.rng.normal(0, 1, (count, self.latent_dim))

        _, x_norm = self._decode(z)
        # Denormalize
        x = x_norm * self.std_x + self.mean_x
        return x

    def synthesize_adversarial_vouchers(
        self,
        count: int = 20,
        coa: Optional[ChartOfAccounts] = None,
        company_code: str = "1000",
    ) -> List[JournalEntry]:
        """Synthesizes adversarial journal vouchers from perturbed TVAE latent space."""
        features = self.sample(count=count, perturb_manifold=True, perturbation_scale=3.2)
        entries: List[JournalEntry] = []
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        for i, row in enumerate(features):
            log_amt, line_cnt, day, cyc_idx = row
            amt = Decimal(str(max(10.0, round(float(np.exp(log_amt)), 2)))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            day_clamped = max(1, min(28, int(round(day))))
            doc_date = f"2026-09-{day_clamped:02d}"
            entry_id = f"DOC_TVAE_ADV_{i+1:05d}"

            entry = JournalEntry(
                entry_id=entry_id,
                batch_id=f"BATCH_TVAE_{20260900 + day_clamped}",
                company_code=company_code,
                document_type=DocumentType.MJE,
                document_number=f"TV{i+1:08d}",
                posting_date=doc_date,
                document_date=doc_date,
                created_at=now_utc,
                header_text=f"TVAE Latent Adversarial Voucher #{i+1}",
                business_cycle="R2R",
                is_anomaly=True,
                anomaly_ids=["ANOM_TVAE_LATENT_MANIFOLD_PERTURBATION"],
                lines=[
                    LineItem(
                        line_id=f"{entry_id}-001",
                        entry_id=entry_id,
                        line_number=1,
                        account_code="69000",
                        account_name="Miscellaneous Operating Expense",
                        debit_credit=DebitCredit.DEBIT,
                        amount=amt,
                        line_text="TVAE adversarial debit leg",
                    ),
                    LineItem(
                        line_id=f"{entry_id}-002",
                        entry_id=entry_id,
                        line_number=2,
                        account_code="10100",
                        account_name="Operating Cash & Bank",
                        debit_credit=DebitCredit.CREDIT,
                        amount=amt,
                        line_text="TVAE adversarial credit leg",
                    ),
                ],
            )
            entries.append(entry)

        return entries
