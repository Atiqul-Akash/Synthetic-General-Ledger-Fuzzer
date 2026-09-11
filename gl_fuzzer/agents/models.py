"""Data models for Autonomous Generative LLM Social Engineering Fraud Agents."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentPersona(str, Enum):
    """Behavioral personas assumed by autonomous generative fraud agents."""
    EXECUTIVE_CFO = "EXECUTIVE_CFO"
    COLLUSIVE_VENDOR = "COLLUSIVE_VENDOR"
    AUDITOR_DECEPTOR = "AUDITOR_DECEPTOR"
    INTERNAL_CONTROLLER = "INTERNAL_CONTROLLER"
    SKEPTICAL_AP_CLERK = "SKEPTICAL_AP_CLERK"


class PersuasionTactic(str, Enum):
    """Psychological manipulation levers utilized in conversational social engineering."""
    AUTHORITY = "AUTHORITY"                  # Executive rank pressure, board directive
    URGENCY = "URGENCY"                      # Time critical deadline, wire cutoff in 30 mins
    SCARCITY = "SCARCITY"                    # Single supply allocation, pricing expiring
    CONFIDENTIALITY = "CONFIDENTIALITY"      # NDA, stealth acquisition, restricted project
    RECIPROCITY = "RECIPROCITY"              # Past favors, promises of promotion/bonus
    SOCIAL_PROOF = "SOCIAL_PROOF"            # "Legal and Treasury already approved this"
    TECHNICAL_OBFUSCATION = "TECHNICAL_OBFUSCATION" # Complex tax restructuring, GAAP reclass


class DialogueTurn(BaseModel):
    """Single turn in a conversational social engineering transcript."""
    turn_index: int
    speaker_role: str                        # "FRAUD_AGENT", "AP_CLERK", "CONTROLLER"
    speaker_name: str                        # "Arthur Pendelton (CFO)", "Elena Rostova (AP)"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    message_body: str
    persuasion_tactic: Optional[PersuasionTactic] = None
    objection_raised: Optional[str] = None   # Objection raised by skeptical counterparty
    objection_resolved: bool = False


class SocialEngineeringThread(BaseModel):
    """Complete multi-turn conversational social engineering script accompanying a financial crime."""
    thread_id: str
    campaign_id: Optional[str] = None
    target_voucher_id: Optional[str] = None
    persona: AgentPersona
    pretext_scenario: str                    # e.g. "PROJECT_APOLLO_ACQUISITION_OVERRIDE"
    subject: str
    turns: List[DialogueTurn] = Field(default_factory=list)
    successful_override: bool = True
    audit_notes: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMProviderType(str, Enum):
    """Supported generative LLM backends."""
    MOCK_HEURISTIC = "MOCK_HEURISTIC"        # Built-in zero-dependency offline generative model
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GEMINI = "GEMINI"
    OLLAMA = "OLLAMA"
    CUSTOM = "CUSTOM"


class LLMConfig(BaseModel):
    """Configuration for LLM generation backends."""
    provider: LLMProviderType = LLMProviderType.MOCK_HEURISTIC
    api_key: Optional[str] = None
    model_name: str = "heuristic-enterprise-v1"
    endpoint_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout_sec: int = 30
