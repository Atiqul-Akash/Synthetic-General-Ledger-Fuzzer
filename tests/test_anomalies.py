"""Unit tests for the Calibrated Micro-Anomaly Library."""

from decimal import Decimal
import numpy as np
import pytest

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DocumentType
from gl_fuzzer.models.manifest import AnomalyType
from gl_fuzzer.generators.distributions import BusinessCalendar
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.anomalies.base_mutator import MutationContext
from gl_fuzzer.anomalies.smurfing import SmurfingMutator
from gl_fuzzer.anomalies.ghost_entries import GhostEntriesMutator
from gl_fuzzer.anomalies.benford_skew import BenfordSkewMutator
from gl_fuzzer.anomalies.anomalous_pairings import AnomalousPairingsMutator
from gl_fuzzer.anomalies.round_tripping import CircularRoundTrippingMutator
from gl_fuzzer.anomalies.pipeline import AnomalyPipeline


@pytest.fixture
def base_batch():
    engine = BaseSynthesisEngine(seed=42)
    return engine.generate_batch(target_entry_count=60)


@pytest.fixture
def mutation_context():
    coa = ChartOfAccounts.create_default()
    rng = np.random.default_rng(42)
    calendar = BusinessCalendar(rng=rng)
    return MutationContext(coa=coa, calendar=calendar, rng=rng)


def test_smurfing_mutator(base_batch, mutation_context):
    mutator = SmurfingMutator(threshold=Decimal("10000.00"))
    records = mutator.mutate(batch=base_batch, context=mutation_context, injection_rate=0.1)

    assert len(records) > 0
    rec = records[0]
    assert rec.anomaly_type == AnomalyType.SMURFING_SPLIT_APPROVAL
    assert len(rec.affected_entry_ids) >= 3

    # Verify all generated cluster entries are within [$9500, $9999] and strictly balanced
    for eid in rec.affected_entry_ids:
        entry = next(e for e in base_batch.entries if e.entry_id == eid)
        assert entry.is_balanced
        assert Decimal("9500.00") <= entry.lines[0].amount <= Decimal("9999.00")
        assert entry.lines[1].vendor_id == rec.parameters["target_vendor"]


def test_ghost_entries_mutator(base_batch, mutation_context):
    mutator = GhostEntriesMutator()
    records = mutator.mutate(batch=base_batch, context=mutation_context, injection_rate=0.1)

    assert len(records) > 0
    rec = records[0]
    assert rec.anomaly_type == AnomalyType.OFF_HOURS_GHOST_ENTRY

    entry = next(e for e in base_batch.entries if e.entry_id == rec.affected_entry_ids[0])
    assert entry.is_balanced
    assert entry.created_by in mutator.ghost_users
    # Check off-hours time format
    hour = int(entry.entry_time.split(":")[0])
    assert 2 <= hour <= 4


def test_benford_skew_mutator(base_batch, mutation_context):
    mutator = BenfordSkewMutator(distortion_mode="spike_789")
    records = mutator.mutate(batch=base_batch, context=mutation_context, injection_rate=0.1)

    assert len(records) > 0
    rec = records[0]
    assert rec.anomaly_type == AnomalyType.BENFORD_SKEW
    entry = next(e for e in base_batch.entries if e.entry_id == rec.affected_entry_ids[0])
    assert entry.is_balanced
    first_digit = int(str(abs(entry.lines[0].amount)).replace(".", "").lstrip("0")[0])
    assert first_digit in (1, 2, 3, 4, 5, 6, 7, 8, 9)


def test_anomalous_pairings_mutator(base_batch, mutation_context):
    mutator = AnomalousPairingsMutator()
    records = mutator.mutate(batch=base_batch, context=mutation_context, injection_rate=0.1)

    assert len(records) > 0
    rec = records[0]
    assert rec.anomaly_type == AnomalyType.ANOMALOUS_ACCOUNT_PAIRING
    entry = next(e for e in base_batch.entries if e.entry_id == rec.affected_entry_ids[0])
    assert entry.is_balanced
    debit_codes = [l.account_code for l in entry.lines if l.debit_credit.value == "DEBIT"]
    credit_codes = [l.account_code for l in entry.lines if l.debit_credit.value == "CREDIT"]
    valid_pairs = [("10100", "69000"), ("99999", "10100"), ("64000", "17000")]
    assert any((d, c) in valid_pairs for d in debit_codes for c in credit_codes)


def test_circular_round_tripping_mutator(base_batch, mutation_context):
    mutator = CircularRoundTrippingMutator(entities=["1000", "2000", "3000"])
    records = mutator.mutate(batch=base_batch, context=mutation_context, injection_rate=0.1)

    assert len(records) > 0
    rec = records[0]
    assert rec.anomaly_type == AnomalyType.CIRCULAR_INTERCOMPANY_ROUND_TRIP
    # 3 hops * 2 entries per hop (sender + receiver) = 6 entries
    assert len(rec.affected_entry_ids) == 6

    # Verify each entry is individually balanced and represents intercompany transfers
    cycle_entries = [e for e in base_batch.entries if e.entry_id in rec.affected_entry_ids]
    assert len(cycle_entries) == 6
    for entry in cycle_entries:
        assert entry.is_balanced
        assert entry.document_type == DocumentType.IC


def test_full_pipeline_preserves_double_entry():
    engine = BaseSynthesisEngine(seed=99)
    batch = engine.generate_batch(target_entry_count=100)
    pipeline = AnomalyPipeline(seed=99)

    records = pipeline.inject_anomalies(batch, overall_anomaly_rate=0.10)
    assert len(records) >= 5
    assert batch.is_balanced
    assert batch.total_debits == batch.total_credits
