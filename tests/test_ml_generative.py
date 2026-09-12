"""Test suite for Generative Tabular Machine Learning (Gaussian Copula & TVAE)."""

from decimal import Decimal
import numpy as np
import pytest

from gl_fuzzer.ml_generative.gaussian_copula import GaussianCopulaSynthesizer
from gl_fuzzer.ml_generative.tvae_engine import TabularVAESynthesizer


def test_gaussian_copula_fitting_and_sampling():
    copula = GaussianCopulaSynthesizer(seed=42)
    copula.fit([])
    assert copula.is_fitted
    assert copula.cov_matrix is not None
    assert copula.cov_matrix.shape == (3, 3)

    samples = copula.sample(count=25)
    assert len(samples) == 25
    for s in samples:
        assert s["amount"] > 0
        assert s["line_count"] % 2 == 0
        assert 1 <= s["day_of_month"] <= 28
        assert s["business_cycle"] in ["P2P", "O2C", "R2R"]


def test_gaussian_copula_voucher_synthesis_balanced():
    copula = GaussianCopulaSynthesizer(seed=99)
    entries = copula.synthesize_journal_entries(count=15, perturb_latent=False)
    assert len(entries) == 15
    for e in entries:
        assert e.is_balanced
        assert not e.is_anomaly


def test_gaussian_copula_latent_perturbation():
    copula = GaussianCopulaSynthesizer(seed=101)
    perturbed_entries = copula.synthesize_journal_entries(count=10, perturb_latent=True)
    assert len(perturbed_entries) == 10
    for e in perturbed_entries:
        assert e.is_balanced
        assert e.is_anomaly
        assert "ANOM_LATENT_MANIFOLD_PERTURBATION" in e.anomaly_ids


def test_tvae_engine_training_and_reconstruction():
    tvae = TabularVAESynthesizer(input_dim=4, latent_dim=2, hidden_dim=8, seed=42)
    tvae.fit(epochs=15, batch_size=16)
    assert tvae.is_fitted

    features = tvae.sample(count=10)
    assert features.shape == (10, 4)


def test_tvae_adversarial_voucher_synthesis():
    tvae = TabularVAESynthesizer(seed=55)
    tvae.fit(epochs=10)
    adv_entries = tvae.synthesize_adversarial_vouchers(count=8)
    assert len(adv_entries) == 8
    for e in adv_entries:
        assert e.is_balanced
        assert e.is_anomaly
        assert "ANOM_TVAE_LATENT_MANIFOLD_PERTURBATION" in e.anomaly_ids
