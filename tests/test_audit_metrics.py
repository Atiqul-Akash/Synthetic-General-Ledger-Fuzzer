"""Unit tests for the Forensic Audit Evaluator screening functions."""

from decimal import Decimal
import numpy as np
import pytest

from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.anomalies.pipeline import AnomalyPipeline
from gl_fuzzer.verification.audit_metrics import ForensicAuditEvaluator


def test_benford_law_evaluation():
    engine = BaseSynthesisEngine(seed=42)
    batch = engine.generate_batch(target_entry_count=200)

    # Evaluate clean batch
    res_clean = ForensicAuditEvaluator.evaluate_benford_compliance(batch.entries)
    assert "chi2_statistic" in res_clean
    assert res_clean["total_observations"] > 0


def test_doa_split_detection():
    engine = BaseSynthesisEngine(seed=42)
    batch = engine.generate_batch(target_entry_count=100)
    pipeline = AnomalyPipeline(seed=42)
    # Inject smurfing
    pipeline.inject_anomalies(batch, overall_anomaly_rate=0.15)

    doa_res = ForensicAuditEvaluator.detect_doa_split_clusters(batch.entries)
    assert doa_res["has_doa_violations"] is True
    assert doa_res["detected_clusters_count"] >= 1


def test_off_hours_detection():
    engine = BaseSynthesisEngine(seed=42)
    batch = engine.generate_batch(target_entry_count=100)
    pipeline = AnomalyPipeline(seed=42)
    pipeline.inject_anomalies(batch, overall_anomaly_rate=0.15)

    off_res = ForensicAuditEvaluator.detect_off_hours_and_ghost_entries(batch.entries)
    assert off_res["has_unauthorized_mj_entries"] is True
    assert off_res["off_hours_flagged_count"] >= 1


def test_anomalous_pairings_detection():
    engine = BaseSynthesisEngine(seed=42)
    batch = engine.generate_batch(target_entry_count=100)
    pipeline = AnomalyPipeline(seed=42)
    pipeline.inject_anomalies(batch, overall_anomaly_rate=0.15)

    pair_res = ForensicAuditEvaluator.detect_anomalous_pairings(batch.entries)
    assert pair_res["has_topological_violations"] is True
    assert pair_res["flagged_pairings_count"] >= 1


def test_intercompany_cycle_detection():
    engine = BaseSynthesisEngine(seed=42)
    batch = engine.generate_batch(target_entry_count=100)
    pipeline = AnomalyPipeline(seed=42)
    pipeline.inject_anomalies(batch, overall_anomaly_rate=0.15)

    ic_res = ForensicAuditEvaluator.detect_intercompany_cycles(batch.entries)
    assert ic_res["has_circular_round_tripping"] is True
    assert ic_res["detected_cycles_count"] >= 1
