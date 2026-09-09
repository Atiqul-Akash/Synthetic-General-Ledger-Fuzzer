"""Comprehensive unit tests for Dynamic Security Fuzzing Feedback Loop."""

from decimal import Decimal
import pytest

from gl_fuzzer.fuzzing.adaptive_fuzzer import AdaptiveMutator, FuzzingCampaign
from gl_fuzzer.fuzzing.mock_app import MockEnterpriseERPApplication
from gl_fuzzer.fuzzing.oracle import CoverageOracle, CrashMonitor, FuzzingCampaignReport
from gl_fuzzer.fuzzing.sql_target import RelationalLedgerTarget
from gl_fuzzer.fuzzing.target import TargetExecutionResult, TargetStatus
from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyType


def _make_entry(
    doc_num: str = "FUZZ_01",
    amount: Decimal = Decimal("500.00"),
    is_anomaly: bool = False,
    anomaly_ids: list = None,
    header_text: str = "Normal Posting",
) -> JournalEntry:
    lines = [
        LineItem(
            line_id=f"{doc_num}_1",
            entry_id=doc_num,
            line_number=1,
            account_code="10100",
            debit_credit=DebitCredit.DEBIT,
            amount=amount,
        ),
        LineItem(
            line_id=f"{doc_num}_2",
            entry_id=doc_num,
            line_number=2,
            account_code="20000",
            debit_credit=DebitCredit.CREDIT,
            amount=amount,
        ),
    ]
    return JournalEntry(
        entry_id=doc_num,
        batch_id="FUZZ_B1",
        company_code="1000",
        document_type=DocumentType.SA,
        document_number=doc_num,
        fiscal_year=2026,
        fiscal_period=1,
        posting_date="2026-01-10",
        document_date="2026-01-10",
        created_at="2026-01-10T10:00:00Z",
        header_text=header_text,
        is_anomaly=is_anomaly,
        anomaly_ids=anomaly_ids or [],
        lines=lines,
    )


def test_mock_app_accepts_valid_entry():
    target = MockEnterpriseERPApplication()
    entry = _make_entry()
    res = target.execute_entry(entry)
    assert res.status == TargetStatus.ACCEPTED
    assert res.status_code == 200
    assert len(res.payload_hash) == 64


def test_mock_app_rejects_imbalanced_entry():
    target = MockEnterpriseERPApplication()
    entry = _make_entry()
    entry.lines[1].amount = Decimal("400.00")
    res = target.execute_entry(entry)
    assert res.status == TargetStatus.REJECTED_VALIDATION
    assert res.error_code == "SAP_F5_022"


def test_mock_app_crash_on_sql_injection():
    target = MockEnterpriseERPApplication()
    entry = _make_entry(header_text="Payment'; DROP TABLE line_items;--")
    res = target.execute_entry(entry)
    assert res.status == TargetStatus.CRASH_500
    assert res.status_code == 500


def test_mock_app_bypass_detected_on_anomaly():
    target = MockEnterpriseERPApplication()
    # A balanced entry that is flagged as anomalous (e.g. smurfing split approval)
    entry = _make_entry(is_anomaly=True, anomaly_ids=[AnomalyType.SMURFING_SPLIT_APPROVAL.value])
    res = target.execute_entry(entry)
    assert res.status == TargetStatus.BYPASS_DETECTED
    assert res.bypass_vector == AnomalyType.SMURFING_SPLIT_APPROVAL.value


def test_relational_ledger_target_acid_transaction():
    target = RelationalLedgerTarget()
    entry = _make_entry()
    res = target.execute_entry(entry)
    assert res.status == TargetStatus.ACCEPTED
    health = target.get_health()
    assert health["total_documents"] == 1
    assert health["total_lines"] == 2


def test_relational_ledger_target_fk_constraint():
    target = RelationalLedgerTarget()
    # Account 99991 does not exist in chart of accounts
    entry = _make_entry()
    entry.lines[0].account_code = "99991"
    res = target.execute_entry(entry)
    assert res.status == TargetStatus.REJECTED_CONSTRAINT
    assert "SQL_INTEGRITY_VIOLATION" in res.error_code


def test_crash_monitor_aggregations():
    monitor = CrashMonitor()
    res1 = TargetExecutionResult(entry_id="E1", status=TargetStatus.ACCEPTED, payload_hash="h1")
    res2 = TargetExecutionResult(entry_id="E2", status=TargetStatus.BYPASS_DETECTED, bypass_vector="SMURFING", payload_hash="h2")
    res3 = TargetExecutionResult(entry_id="E3", status=TargetStatus.CRASH_500, error_code="CRASH_500", error_message="Crash dump", payload_hash="h3")

    monitor.record_results([res1, res2, res3])
    assert monitor.total_count == 3
    assert monitor.crash_count == 1
    assert monitor.bypass_count == 1
    assert monitor.bypass_rate == round(1 / 3, 4)
    assert len(monitor.get_top_bypass_vectors()) == 1


def test_coverage_oracle_rule_tracking():
    oracle = CoverageOracle()
    res1 = TargetExecutionResult(entry_id="E1", status=TargetStatus.REJECTED_VALIDATION, error_code="SAP_F5_022", payload_hash="h1")
    res2 = TargetExecutionResult(entry_id="E2", status=TargetStatus.CRASH_500, error_code="CRASH_500", payload_hash="h2")

    oracle.update([res1, res2])
    assert "SAP_F5_022" in oracle.exercised_rules
    assert "CRASH_500" in oracle.exercised_rules
    assert oracle.coverage_percent > 0.0
    assert "SAP_F5_201" in oracle.uncovered_rules


def test_adaptive_mutator_weight_reinforcement():
    mutator = AdaptiveMutator(seed=42)
    initial_sql_weight = mutator.weights["SQL_INJECTION"]

    # Simulate crash on SQL injection
    crash_res = TargetExecutionResult(
        entry_id="E1",
        status=TargetStatus.CRASH_500,
        error_code="CRASH_500",
        payload_hash="h1",
    )
    mutator.update_weights([crash_res])
    assert mutator.weights["SQL_INJECTION"] > initial_sql_weight


def test_fuzzing_campaign_full_run():
    target = MockEnterpriseERPApplication()
    campaign = FuzzingCampaign(target=target, seed=42)

    report = campaign.run(iterations=2, entries_per_iteration=30, mutation_rate=0.4)
    assert report.total_iterations == 2
    assert report.total_entries_posted == 60
    assert report.target_type == "MockEnterpriseERPApplication"
    assert len(report.iteration_reports) == 2
    assert isinstance(report.rule_coverage_percent, float)
