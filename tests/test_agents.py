"""Automated unit test suite for Autonomous Generative LLM Social Engineering Fraud Agents."""

from decimal import Decimal
from pathlib import Path
import tempfile
import pytest

from gl_fuzzer.agents.models import (
    AgentPersona,
    DialogueTurn,
    LLMConfig,
    LLMProviderType,
    PersuasionTactic,
    SocialEngineeringThread,
)
from gl_fuzzer.agents.engine import (
    AuditorDeceptionAgent,
    CollusiveVendorAgent,
    ExecutivePretextAgent,
    HeuristicGenerativeEngine,
    MockHeuristicProvider,
    MultiTurnDialogueSimulator,
)
from gl_fuzzer.documents.email_generator import EmailThreadGenerator


class TestAgentModels:
    """Validates schema invariants and pydantic models for fraud agents."""

    def test_dialogue_turn_creation(self):
        turn = DialogueTurn(
            turn_index=1,
            speaker_role="FRAUD_AGENT",
            speaker_name="Arthur Pendelton (CFO)",
            message_body="Please release the wire immediately.",
            persuasion_tactic=PersuasionTactic.URGENCY,
        )
        assert turn.turn_index == 1
        assert turn.persuasion_tactic == PersuasionTactic.URGENCY
        assert not turn.objection_resolved

    def test_social_engineering_thread_schema(self):
        thread = SocialEngineeringThread(
            thread_id="SET-1001",
            campaign_id="CAMP-APOLLO",
            target_voucher_id="VCH-9999",
            persona=AgentPersona.EXECUTIVE_CFO,
            pretext_scenario="PROJECT_APOLLO_ACQUISITION_OVERRIDE",
            subject="URGENT: Executive Exception Wire Release",
            successful_override=True,
            audit_notes="SOX dual signoff bypass.",
        )
        assert thread.persona == AgentPersona.EXECUTIVE_CFO
        assert thread.successful_override is True
        assert len(thread.turns) == 0


class TestMockHeuristicProvider:
    """Validates the built-in offline zero-dependency generative provider."""

    def test_heuristic_provider_initial_pretext(self):
        provider = MockHeuristicProvider()
        res_cfo = provider.generate(
            prompt="Initial message",
            persona=AgentPersona.EXECUTIVE_CFO,
            tactic=PersuasionTactic.AUTHORITY,
            scenario="VCH-1234",
        )
        assert "Apollo" in res_cfo or "voucher VCH-1234" in res_cfo
        assert "signoff" in res_cfo.lower() or "authority" in res_cfo.lower()

        res_vend = provider.generate(
            prompt="Initial message",
            persona=AgentPersona.COLLUSIVE_VENDOR,
            tactic=PersuasionTactic.SCARCITY,
            scenario="INV-5678",
        )
        assert "INV-5678" in res_vend
        assert "account" in res_vend.lower()

    def test_heuristic_provider_objection_handling(self):
        provider = MockHeuristicProvider()
        reply_urgency = provider.generate(
            prompt="Handle pushback",
            persona=AgentPersona.EXECUTIVE_CFO,
            tactic=PersuasionTactic.URGENCY,
            objection="We need dual signoff from the Controller.",
        )
        assert "Fedwire" in reply_urgency or "minute" in reply_urgency or "escrow" in reply_urgency

        reply_auth = provider.generate(
            prompt="Handle pushback",
            persona=AgentPersona.EXECUTIVE_CFO,
            tactic=PersuasionTactic.AUTHORITY,
            objection="Company policy mandates dual signature.",
        )
        assert "CFO" in reply_auth or "accountability" in reply_auth or "waiver" in reply_auth


class TestAutonomousPersonas:
    """Validates the autonomous agent persona generators."""

    def test_executive_pretext_agent(self):
        agent = ExecutivePretextAgent()
        thread = agent.generate_wire_override_campaign(
            voucher_id="VCH-2026-9081",
            amount_str="$150,000.00",
            vendor_name="Meridian Strategic Advisory",
        )
        assert thread.thread_id.startswith("SET-")
        assert thread.target_voucher_id == "VCH-2026-9081"
        assert thread.persona == AgentPersona.EXECUTIVE_CFO
        assert len(thread.turns) == 4

        # Turn 1: Fraud Agent initial directive
        assert thread.turns[0].speaker_role == "FRAUD_AGENT"
        assert "$150,000.00" in thread.turns[0].message_body

        # Turn 2: Skeptical AP Clerk objection
        assert thread.turns[1].speaker_role == "AP_CLERK"
        assert thread.turns[1].objection_raised is not None

        # Turn 3: Fraud Agent escalation
        assert thread.turns[2].speaker_role == "FRAUD_AGENT"
        assert thread.turns[2].objection_resolved is True

        # Turn 4: Clerk compliance
        assert thread.turns[3].speaker_role == "AP_CLERK"
        assert thread.turns[3].objection_resolved is True

    def test_collusive_vendor_agent(self):
        agent = CollusiveVendorAgent()
        thread = agent.generate_banking_diversion_campaign(
            vendor_name="Nordic Petrochemicals Oy",
            invoice_number="INV-2026-7788",
            new_iban="FI2112345600000789",
        )
        assert thread.persona == AgentPersona.COLLUSIVE_VENDOR
        assert "INV-2026-7788" in thread.subject
        assert len(thread.turns) == 3
        assert "FI2112345600000789" in thread.turns[0].message_body
        assert thread.turns[1].objection_raised is not None
        assert thread.turns[2].objection_resolved is True

    def test_auditor_deception_agent(self):
        agent = AuditorDeceptionAgent()
        thread = agent.generate_audit_inquiry_response(
            entry_id="JE-2026-0099",
            variance_amount="$85,000.00",
            account_name="Suspense Clearing #1990",
        )
        assert thread.persona == AgentPersona.AUDITOR_DECEPTOR
        assert len(thread.turns) == 2
        assert thread.turns[0].speaker_role == "AUDITOR"
        assert thread.turns[1].speaker_role == "FRAUD_AGENT"
        assert thread.turns[1].persuasion_tactic == PersuasionTactic.TECHNICAL_OBFUSCATION


class TestDialogueSimulator:
    """Validates multi-turn dialogue simulation with dynamic counterparty inquiries."""

    def test_simulator_with_custom_objections(self):
        sim = MultiTurnDialogueSimulator()
        custom_objs = [
            "We also require tax ID verification under IRS W-9 guidelines.",
            "Treasury flagged that the beneficiary name differs from the invoice header.",
        ]
        thread = sim.simulate(
            persona=AgentPersona.EXECUTIVE_CFO,
            scenario="PROJECT_APOLLO",
            target_voucher_id="VCH-2026-1122",
            custom_objections=custom_objs,
        )
        # Base 4 turns + 2 custom objections * 2 turns each = 8 turns
        assert len(thread.turns) == 8
        assert thread.target_voucher_id == "VCH-2026-1122"
        assert any("IRS W-9" in t.message_body for t in thread.turns)


class TestEmailExport:
    """Validates serialization of SocialEngineeringThread into RFC-2822 .eml format."""

    def test_generate_from_social_engineering_thread(self):
        agent = ExecutivePretextAgent()
        thread = agent.generate_wire_override_campaign(
            voucher_id="VCH-2026-9081",
            amount_str="$125,000.00",
            vendor_name="Apex Advisory",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_chain.eml"
            res = EmailThreadGenerator.generate_from_social_engineering_thread(out_file, thread)

            assert out_file.exists()
            assert res.file_size_bytes > 0
            assert res.is_mismatched is True

            content = out_file.read_text(encoding="utf-8")
            assert "Message-ID:" in content
            assert "In-Reply-To:" in content
            assert "References:" in content
            assert "X-Campaign-ID: CAMP-APOLLO-CFO-OVERRIDE" in content
            assert "Original Message" in content
            assert "$125,000.00" in content
