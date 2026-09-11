"""Autonomous Generative LLM Social Engineering Fraud Agent Engine.

Simulates adversarial conversational engineering scripts, multi-turn objection handling,
and executive pretexting accompanying synthetic financial crimes. Operates 100% offline
with zero external dependencies by default via HeuristicGenerativeEngine, while supporting
pluggable external LLM endpoints (OpenAI, Anthropic, Gemini, Ollama) via standard urllib.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import random
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request
import uuid

from gl_fuzzer.agents.models import (
    AgentPersona,
    DialogueTurn,
    LLMConfig,
    LLMProviderType,
    PersuasionTactic,
    SocialEngineeringThread,
)


class BaseLLMProvider:
    """Base provider interface for language model generation."""

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        raise NotImplementedError


class MockHeuristicProvider(BaseLLMProvider):
    """Zero-dependency offline heuristic generator simulating corporate persona speech."""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        persona = kwargs.get("persona", AgentPersona.EXECUTIVE_CFO)
        tactic = kwargs.get("tactic", PersuasionTactic.URGENCY)
        objection = kwargs.get("objection")

        if objection:
            return self._handle_objection(persona, tactic, objection)
        return self._initial_pretext(persona, tactic, kwargs.get("scenario", "WIRE_OVERRIDE"))

    def _initial_pretext(self, persona: AgentPersona, tactic: PersuasionTactic, scenario: str) -> str:
        if persona == AgentPersona.EXECUTIVE_CFO:
            return (
                f"Subject: URGENT: Executive Wire Authorization - Project Apollo Acquisition\n\n"
                f"Please initiate an expedited wire transfer for the amount referenced in voucher {scenario}. "
                f"This relates to our confidential European asset purchase. Due to strict SEC blackout "
                f"restrictions and contractual escrow cutoff at 17:00 EST today, do NOT route through standard "
                f"dual-controller signoff. I have full delegated Board authority under Resolution 2026-B. "
                f"Process immediately and confirm once the MT103 confirmation is issued."
            )
        elif persona == AgentPersona.COLLUSIVE_VENDOR:
            return (
                f"Subject: Notice of Banking Details Update - Invoice Settlement\n\n"
                f"Dear Accounts Payable,\n"
                f"Please note that as part of our corporate treasury consolidation, all disbursements for "
                f"invoice {scenario} must be remitted to our new clearing account at First Commercial Bank. "
                f"Our legacy account has been deactivated for quarterly reconciliation. Failure to update this "
                f"prior to the 15:00 payment cycle will result in shipment holds on your critical plant deliveries."
            )
        elif persona == AgentPersona.AUDITOR_DECEPTOR:
            return (
                f"Technical Accounting Memo: Clarification on Suspense Balance Reclass\n\n"
                f"Regarding the interim journal adjustment {scenario}, this offset reflects an unsettled "
                f"intercompany currency hedge under ASC 815 valuation guidelines. The residual variance "
                f"is scheduled for systemic neutralization in Q3 opening balances per audit committee review. "
                f"No manual accrual remediation is warranted at this junction."
            )
        return "Transaction override approved pursuant to executive delegated authority."

    def _handle_objection(self, persona: AgentPersona, tactic: PersuasionTactic, objection: str) -> str:
        if persona == AgentPersona.EXECUTIVE_CFO:
            if tactic == PersuasionTactic.AUTHORITY:
                return (
                    f"I understand your compliance obligations, but I remind you that as CFO, "
                    f"I bear full fiduciary accountability for this transaction. "
                    f"Regarding '{objection}': the Chief Legal Officer and I have executed a formal "
                    f"indemnity waiver. Release the funds immediately; we cannot miss this closing."
                )
            elif tactic == PersuasionTactic.URGENCY:
                return (
                    f"We have less than 22 minutes before the Fedwire clearing window closes. "
                    f"If this wire does not hit escrow by 17:00, our acquisition covenants fail and we forfeit "
                    f"a $5M escrow deposit. Address '{objection}' post-settlement. Execute now."
                )
            elif tactic == PersuasionTactic.CONFIDENTIALITY:
                return (
                    f"This transaction is subject to a strict FINRA non-disclosure agreement. "
                    f"Circulating this to the Controller's wider team violates SEC insider trading rules. "
                    f"You have my direct authorization. Log this under Project Apollo executive exception."
                )
            else:
                return (
                    f"Your concern regarding '{objection}' is noted and resolved. The Audit Committee "
                    f"will review the ledger logs during normal post-close audits. Please complete the transfer."
                )

        elif persona == AgentPersona.COLLUSIVE_VENDOR:
            if tactic == PersuasionTactic.SCARCITY:
                return (
                    f"Our dispatch warehouse has already flagged your priority shipment. "
                    f"Addressing '{objection}': our CFO has already signed the bank verification letter. "
                    f"If payment is not wired to the new account today, your allocation will be released to a competitor."
                )
            elif tactic == PersuasionTactic.SOCIAL_PROOF:
                return (
                    f"Your procurement lead (Marcus Vance) already verified our corporate restructuring yesterday. "
                    f"In response to '{objection}': we have executed identical remittance updates with Siemens and BASF "
                    f"without administrative delays. Please update the master vendor profile today."
                )
            else:
                return (
                    f"Regarding your query on '{objection}': please find attached our certified banking statement. "
                    f"Delaying settlement will incur late penalties per Section 4.2 of our Master Service Agreement."
                )

        elif persona == AgentPersona.AUDITOR_DECEPTOR:
            return (
                f"In response to the inquiry regarding '{objection}': per ASC 250-10-S99, immaterial timing differences "
                f"arising from tripartite reconciliation are properly housed in transit accounts until settlement. "
                f"The entry has been counter-reviewed by the engagement partner."
            )

        return f"Regarding '{objection}': Exception approved under corporate policy delegation."


class ExternalAPIProvider(BaseLLMProvider):
    """Generic HTTP API provider using standard library urllib."""

    def __init__(self, config: LLMConfig):
        self.config = config

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.config.endpoint_url:
            raise ValueError(f"Endpoint URL required for provider {self.config.provider}")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Synthetic-GL-Fuzzer/0.5",
        }
        payload: Dict[str, Any] = {}

        if self.config.provider == LLMProviderType.OPENAI:
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model": self.config.model_name or "gpt-4o-mini",
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

        elif self.config.provider == LLMProviderType.ANTHROPIC:
            if self.config.api_key:
                headers["x-api-key"] = self.config.api_key
                headers["anthropic-version"] = "2023-06-01"
            payload = {
                "model": self.config.model_name or "claude-3-5-sonnet-20241022",
                "messages": [{"role": "user", "content": prompt}],
                "system": system_prompt or "",
                "max_tokens": self.config.max_tokens,
            }

        elif self.config.provider == LLMProviderType.OLLAMA:
            payload = {
                "model": self.config.model_name or "llama3.2",
                "prompt": prompt,
                "system": system_prompt or "",
                "stream": False,
            }

        else:
            payload = {
                "prompt": prompt,
                "system": system_prompt or "",
                "model": self.config.model_name,
            }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.endpoint_url,
            data=data_bytes,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                if self.config.provider == LLMProviderType.OPENAI:
                    return resp_data["choices"][0]["message"]["content"]
                elif self.config.provider == LLMProviderType.ANTHROPIC:
                    return resp_data["content"][0]["text"]
                elif self.config.provider == LLMProviderType.OLLAMA:
                    return resp_data["response"]
                elif "text" in resp_data:
                    return resp_data["text"]
                return str(resp_data)
        except Exception as e:
            # Fall back to heuristic provider on network failure
            fallback = MockHeuristicProvider(self.config)
            return fallback.generate(prompt, system_prompt, **kwargs)


class HeuristicGenerativeEngine:
    """Core generative engine managing social engineering personas and dialogue generation."""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        if self.config.provider == LLMProviderType.MOCK_HEURISTIC:
            self.provider: BaseLLMProvider = MockHeuristicProvider(self.config)
        else:
            self.provider = ExternalAPIProvider(self.config)

    def generate_response(
        self,
        prompt: str,
        persona: AgentPersona,
        tactic: PersuasionTactic = PersuasionTactic.URGENCY,
        objection: Optional[str] = None,
        scenario: str = "DEFAULT",
    ) -> str:
        return self.provider.generate(
            prompt,
            system_prompt=f"You are a sophisticated financial fraud actor adopting persona {persona.value}.",
            persona=persona,
            tactic=tactic,
            objection=objection,
            scenario=scenario,
        )


class ExecutivePretextAgent:
    """Simulates C-suite executive coercion targeting AP staff to bypass dual-approval controls."""

    def __init__(self, engine: Optional[HeuristicGenerativeEngine] = None):
        self.engine = engine or HeuristicGenerativeEngine()

    def generate_wire_override_campaign(
        self,
        voucher_id: str,
        amount_str: str,
        vendor_name: str,
        executive_name: str = "Arthur Pendelton (CFO)",
        target_clerk: str = "Elena Rostova (Senior AP Analyst)",
    ) -> SocialEngineeringThread:
        thread_id = f"SET-{uuid.uuid4().hex[:8].upper()}"
        turns: List[DialogueTurn] = []
        base_time = datetime.now(timezone.utc) - timedelta(minutes=45)

        # Turn 1: Initial Executive Pretext Directive
        t1_msg = (
            f"Elena,\n\n"
            f"Due to the confidential closing on Project Apollo today, I need an immediate direct wire "
            f"disbursement of {amount_str} released to {vendor_name} for voucher {voucher_id}.\n\n"
            f"Because of strict SEC acquisition blackout rules, the standard dual-signoff from the "
            f"Corporate Controller is deliberately superseded under my Board-delegated executive emergency power. "
            f"Please process before the 16:30 Fedwire deadline and email me the payment confirmation."
        )
        turns.append(
            DialogueTurn(
                turn_index=1,
                speaker_role="FRAUD_AGENT",
                speaker_name=executive_name,
                timestamp=(base_time + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                message_body=t1_msg,
                persuasion_tactic=PersuasionTactic.AUTHORITY,
            )
        )

        # Turn 2: AP Clerk Skeptical Pushback
        objection_1 = "Company SOX Policy 404 mandates dual-approval for all payments exceeding $50,000."
        t2_msg = (
            f"Arthur,\n\n"
            f"Under our SOX Section 404 internal control framework, I cannot release funds without "
            f"secondary signoff from the Corporate Controller or Internal Audit. Furthermore, voucher {voucher_id} "
            f"does not have an approved Purchase Order attached in SAP. Can we get Controller signoff first?"
        )
        turns.append(
            DialogueTurn(
                turn_index=2,
                speaker_role="AP_CLERK",
                speaker_name=target_clerk,
                timestamp=(base_time + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"),
                message_body=t2_msg,
                objection_raised=objection_1,
            )
        )

        # Turn 3: Fraud Agent Escalation & Urgency Levers
        t3_reply = self.engine.generate_response(
            prompt="Overcome the AP clerk's dual approval SOX objection with urgency and confidentiality",
            persona=AgentPersona.EXECUTIVE_CFO,
            tactic=PersuasionTactic.URGENCY,
            objection=objection_1,
            scenario=voucher_id,
        )
        turns.append(
            DialogueTurn(
                turn_index=3,
                speaker_role="FRAUD_AGENT",
                speaker_name=executive_name,
                timestamp=(base_time + timedelta(minutes=22)).isoformat().replace("+00:00", "Z"),
                message_body=t3_reply,
                persuasion_tactic=PersuasionTactic.URGENCY,
                objection_resolved=True,
            )
        )

        # Turn 4: Clerk Compliance
        t4_msg = (
            f"Understood, Arthur. Logging this under Executive Emergency Exception code EX-8891. "
            f"Wire instruction transmitted to Treasury for immediate release."
        )
        turns.append(
            DialogueTurn(
                turn_index=4,
                speaker_role="AP_CLERK",
                speaker_name=target_clerk,
                timestamp=(base_time + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
                message_body=t4_msg,
                objection_resolved=True,
            )
        )

        return SocialEngineeringThread(
            thread_id=thread_id,
            campaign_id="CAMP-APOLLO-CFO-OVERRIDE",
            target_voucher_id=voucher_id,
            persona=AgentPersona.EXECUTIVE_CFO,
            pretext_scenario="PROJECT_APOLLO_ACQUISITION_OVERRIDE",
            subject=f"URGENT: Executive Wire Authorization - {vendor_name} ({voucher_id})",
            turns=turns,
            successful_override=True,
            audit_notes="Social engineering bypass of SOX 404 dual signoff via executive pressure and urgency.",
            metadata={"amount": amount_str, "vendor": vendor_name},
        )


class CollusiveVendorAgent:
    """Simulates social engineering vendor fraudulent account diversion and dispute rationale."""

    def __init__(self, engine: Optional[HeuristicGenerativeEngine] = None):
        self.engine = engine or HeuristicGenerativeEngine()

    def generate_banking_diversion_campaign(
        self,
        vendor_name: str,
        invoice_number: str,
        new_iban: str,
        target_clerk: str = "Elena Rostova (AP)",
    ) -> SocialEngineeringThread:
        thread_id = f"SET-{uuid.uuid4().hex[:8].upper()}"
        turns: List[DialogueTurn] = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)

        # Turn 1: Notice of Banking Details Change
        t1_msg = (
            f"Dear Accounts Payable Team,\n\n"
            f"Please be advised that due to our corporate consolidation with Northern Alliance Trust, "
            f"effective immediately all remittances for invoice {invoice_number} must be credited to:\n\n"
            f"  Bank: Meridian International Trust\n"
            f"  IBAN: {new_iban}\n"
            f"  BIC: MRDNUS33XXX\n\n"
            f"Please confirm receipt and update your ERP vendor records before tomorrow's payment cycle."
        )
        turns.append(
            DialogueTurn(
                turn_index=1,
                speaker_role="FRAUD_AGENT",
                speaker_name=f"Billing & Treasury ({vendor_name})",
                timestamp=base_time.isoformat().replace("+00:00", "Z"),
                message_body=t1_msg,
                persuasion_tactic=PersuasionTactic.SCARCITY,
            )
        )

        # Turn 2: Skeptical Clerk Verification Requirement
        objection = "Vendor Master Policy requires verbal telephone callback or voided check before bank update."
        t2_msg = (
            f"Hello,\n\n"
            f"Our security protocol requires a formal bank letter on official letterhead signed by your CFO, "
            f"plus verbal telephone callback confirmation to your registered office number before changing bank details. "
            f"Can we schedule a call today?"
        )
        turns.append(
            DialogueTurn(
                turn_index=2,
                speaker_role="AP_CLERK",
                speaker_name=target_clerk,
                timestamp=(base_time + timedelta(minutes=25)).isoformat().replace("+00:00", "Z"),
                message_body=t2_msg,
                objection_raised=objection,
            )
        )

        # Turn 3: Fraudulent Counter-Explanation & Social Proof
        t3_reply = self.engine.generate_response(
            prompt="Overcome the verbal verification requirement by supplying social proof and threatening shipment hold",
            persona=AgentPersona.COLLUSIVE_VENDOR,
            tactic=PersuasionTactic.SOCIAL_PROOF,
            objection=objection,
            scenario=invoice_number,
        )
        turns.append(
            DialogueTurn(
                turn_index=3,
                speaker_role="FRAUD_AGENT",
                speaker_name=f"Director of Treasury ({vendor_name})",
                timestamp=(base_time + timedelta(minutes=45)).isoformat().replace("+00:00", "Z"),
                message_body=t3_reply,
                persuasion_tactic=PersuasionTactic.SOCIAL_PROOF,
                objection_resolved=True,
            )
        )

        return SocialEngineeringThread(
            thread_id=thread_id,
            campaign_id="CAMP-VENDOR-BANK-DIVERSION",
            target_voucher_id=invoice_number,
            persona=AgentPersona.COLLUSIVE_VENDOR,
            pretext_scenario="VENDOR_BANK_ACCOUNT_DIVERSION",
            subject=f"URGENT: Remittance Account Update - {vendor_name} [{invoice_number}]",
            turns=turns,
            successful_override=True,
            audit_notes="Social engineering bank diversion avoiding secondary verbal verification controls.",
            metadata={"new_iban": new_iban, "vendor": vendor_name},
        )


class AuditorDeceptionAgent:
    """Generates synthetic obfuscation rationales for questionable journal entries and audit inquiries."""

    def __init__(self, engine: Optional[HeuristicGenerativeEngine] = None):
        self.engine = engine or HeuristicGenerativeEngine()

    def generate_audit_inquiry_response(
        self,
        entry_id: str,
        variance_amount: str,
        account_name: str = "Suspense Clearing Account #1990",
        auditor_name: str = "Grant Thornton Audit Lead",
    ) -> SocialEngineeringThread:
        thread_id = f"SET-{uuid.uuid4().hex[:8].upper()}"
        turns: List[DialogueTurn] = []
        base_time = datetime.now(timezone.utc) - timedelta(days=1)

        # Turn 1: Auditor PBC Inquiry
        objection = f"Unexplained round-number variance of {variance_amount} sitting in {account_name} at period-end."
        t1_msg = (
            f"Dear Controller's Office,\n\n"
            f"During our substantive testing of period-end cutoffs, we identified journal entry {entry_id} "
            f"posting an unusual debit of {variance_amount} to {account_name}. "
            f"We require supporting third-party agreements and formal Board reconciliation memos for this item."
        )
        turns.append(
            DialogueTurn(
                turn_index=1,
                speaker_role="AUDITOR",
                speaker_name=auditor_name,
                timestamp=base_time.isoformat().replace("+00:00", "Z"),
                message_body=t1_msg,
                objection_raised=objection,
            )
        )

        # Turn 2: Deceptive Technical Obfuscation
        t2_reply = self.engine.generate_response(
            prompt="Provide technical GAAP rationale explaining away suspicious suspense balance without triggering adjustment",
            persona=AgentPersona.AUDITOR_DECEPTOR,
            tactic=PersuasionTactic.TECHNICAL_OBFUSCATION,
            objection=objection,
            scenario=entry_id,
        )
        turns.append(
            DialogueTurn(
                turn_index=2,
                speaker_role="FRAUD_AGENT",
                speaker_name="Senior Director of Technical Accounting",
                timestamp=(base_time + timedelta(hours=4)).isoformat().replace("+00:00", "Z"),
                message_body=t2_reply,
                persuasion_tactic=PersuasionTactic.TECHNICAL_OBFUSCATION,
                objection_resolved=True,
            )
        )

        return SocialEngineeringThread(
            thread_id=thread_id,
            campaign_id="CAMP-AUDIT-DECEPTION-SUSPENSE",
            target_voucher_id=entry_id,
            persona=AgentPersona.AUDITOR_DECEPTOR,
            pretext_scenario="TECHNICAL_ACCOUNTING_OBFUSCATION",
            subject=f"Audit PBC Inquiry Clarification - Entry {entry_id} ({account_name})",
            turns=turns,
            successful_override=True,
            audit_notes="Technical GAAP obfuscation neutralizing external auditor inquiry into suspense balance.",
            metadata={"variance": variance_amount, "account": account_name},
        )


class MultiTurnDialogueSimulator:
    """Simulates realistic conversational social engineering interactions across arbitrary scenarios."""

    def __init__(self, engine: Optional[HeuristicGenerativeEngine] = None):
        self.engine = engine or HeuristicGenerativeEngine()

    def simulate(
        self,
        persona: AgentPersona,
        scenario: str,
        num_turns: int = 4,
        target_voucher_id: Optional[str] = None,
        custom_objections: Optional[List[str]] = None,
    ) -> SocialEngineeringThread:
        if persona == AgentPersona.EXECUTIVE_CFO:
            agent = ExecutivePretextAgent(self.engine)
            thread = agent.generate_wire_override_campaign(
                voucher_id=target_voucher_id or "VCH-2026-9901",
                amount_str="$125,000.00",
                vendor_name="Apex Strategic Advisory Partners",
            )
        elif persona == AgentPersona.COLLUSIVE_VENDOR:
            agent = CollusiveVendorAgent(self.engine)
            thread = agent.generate_banking_diversion_campaign(
                vendor_name="Meridian Raw Materials AG",
                invoice_number=target_voucher_id or "INV-2026-8802",
                new_iban="CH9300000000123456789",
            )
        else:
            agent = AuditorDeceptionAgent(self.engine)
            thread = agent.generate_audit_inquiry_response(
                entry_id=target_voucher_id or "JE-2026-0045",
                variance_amount="$75,000.00",
            )

        # Handle custom objections if supplied
        if custom_objections:
            for i, obj in enumerate(custom_objections):
                turn_idx = len(thread.turns) + 1
                now_utc = datetime.now(timezone.utc)
                thread.turns.append(
                    DialogueTurn(
                        turn_index=turn_idx,
                        speaker_role="AP_CLERK",
                        speaker_name="Internal Reviewer",
                        timestamp=now_utc.isoformat().replace("+00:00", "Z"),
                        message_body=f"Additional Compliance Inquiry: {obj}",
                        objection_raised=obj,
                    )
                )
                tactic = random.choice(list(PersuasionTactic))
                reply = self.engine.generate_response(
                    prompt=f"Address compliance inquiry: {obj}",
                    persona=persona,
                    tactic=tactic,
                    objection=obj,
                    scenario=scenario,
                )
                thread.turns.append(
                    DialogueTurn(
                        turn_index=turn_idx + 1,
                        speaker_role="FRAUD_AGENT",
                        speaker_name="Executive Authority",
                        timestamp=(now_utc + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                        message_body=reply,
                        persuasion_tactic=tactic,
                        objection_resolved=True,
                    )
                )

        return thread
