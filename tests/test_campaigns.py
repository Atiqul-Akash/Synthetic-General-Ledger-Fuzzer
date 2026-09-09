"""Tests for Multi-Stage Financial Adversarial Campaigns (APTs)."""

from decimal import Decimal
import pytest

from gl_fuzzer.campaigns.models import APTCampaignType, APTCampaignPhase
from gl_fuzzer.campaigns.orchestrator import APTNarrativeOrchestrator
from gl_fuzzer.verification.invariants import InvariantVerifier


def test_inventory_map_creep_campaign():
    orchestrator = APTNarrativeOrchestrator(seed=42)
    record, entries = orchestrator.orchestrate_campaign(
        campaign_type=APTCampaignType.INVENTORY_MAP_CREEP_AND_OBSOLESCENCE,
        fiscal_year=2026,
    )

    assert record.campaign_type == APTCampaignType.INVENTORY_MAP_CREEP_AND_OBSOLESCENCE
    assert len(record.milestones) == 4
    assert record.primary_adversary.role == "Senior Plant Controller"
    assert len(entries) >= 8
    assert record.total_illicit_volume > Decimal("50000.00")

    # Invariant Verification on all generated vouchers
    verifier = InvariantVerifier()
    for entry in entries:
        violations = verifier.verify_entry(entry)
        assert len(violations) == 0, f"Entry {entry.entry_id} has balance violations: {violations}"
        assert entry.is_balanced is True
        assert entry.is_balanced_local is True
        assert entry.is_balanced_group is True


def test_enron_spv_round_tripping_campaign():
    orchestrator = APTNarrativeOrchestrator(seed=42)
    record, entries = orchestrator.orchestrate_campaign(
        campaign_type=APTCampaignType.ENRON_SPV_ROUND_TRIPPING,
        fiscal_year=2026,
    )

    assert record.campaign_type == APTCampaignType.ENRON_SPV_ROUND_TRIPPING
    assert "3000" in record.target_entities
    assert len(entries) >= 5

    verifier = InvariantVerifier()
    for entry in entries:
        assert len(verifier.verify_entry(entry)) == 0


def test_doa_kickback_campaign():
    orchestrator = APTNarrativeOrchestrator(seed=42)
    record, entries = orchestrator.orchestrate_campaign(
        campaign_type=APTCampaignType.EXECUTIVE_DOA_SMURFING_WITH_KICKBACK,
        fiscal_year=2026,
    )

    assert record.campaign_type == APTCampaignType.EXECUTIVE_DOA_SMURFING_WITH_KICKBACK
    assert record.primary_adversary.role == "Director of Accounts Payable"
    assert any(m.phase == APTCampaignPhase.PHASE_3_LAUNDERING_AND_TRANSFER for m in record.milestones)

    verifier = InvariantVerifier()
    for entry in entries:
        assert len(verifier.verify_entry(entry)) == 0
