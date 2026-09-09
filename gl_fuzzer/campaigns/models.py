"""Models for Multi-Stage Financial Adversarial Campaigns (APTs)."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class APTCampaignType(str, Enum):
    """Archetypes of multi-quarter corporate financial conspiracies."""
    INVENTORY_MAP_CREEP_AND_OBSOLESCENCE = "INVENTORY_MAP_CREEP_AND_OBSOLESCENCE"
    ENRON_SPV_ROUND_TRIPPING = "ENRON_SPV_ROUND_TRIPPING"
    EXECUTIVE_DOA_SMURFING_WITH_KICKBACK = "EXECUTIVE_DOA_SMURFING_WITH_KICKBACK"


class APTCampaignPhase(str, Enum):
    """Chronological execution phase in an adversarial campaign."""
    PHASE_1_RECONNAISSANCE_AND_SEED = "PHASE_1_RECONNAISSANCE_AND_SEED"
    PHASE_2_STAGING_AND_MANIPULATION = "PHASE_2_STAGING_AND_MANIPULATION"
    PHASE_3_LAUNDERING_AND_TRANSFER = "PHASE_3_LAUNDERING_AND_TRANSFER"
    PHASE_4_YEAR_END_CONCEALMENT = "PHASE_4_YEAR_END_CONCEALMENT"


class APTActor(BaseModel):
    """Fictitious insider or rogue actor executing the campaign."""
    actor_id: str = Field(..., description="User identifier (USNAM)")
    name: str = Field(..., description="Actor legal name")
    role: str = Field(..., description="Corporate role (e.g., Plant Controller, AP Supervisor)")
    company_code: str = Field(default="1000", description="Primary company code")
    access_level: str = Field(default="ELEVATED_FINANCE", description="Authorization profile")


class APTPhaseMilestone(BaseModel):
    """Milestone within a fiscal quarter of an APT campaign."""
    phase: APTCampaignPhase
    fiscal_period: int
    quarter: str
    description: str
    target_accounts: List[str]
    entry_ids: List[str] = Field(default_factory=list)
    micro_anomalies_injected: List[str] = Field(default_factory=list)
    illicit_volume: Decimal = Field(default=Decimal("0.00"))


class APTCampaignRecord(BaseModel):
    """Complete multi-quarter record of a coordinated financial APT campaign."""
    campaign_id: str = Field(..., description="Unique campaign identifier")
    title: str = Field(..., description="Descriptive title of the adversarial narrative")
    campaign_type: APTCampaignType
    fiscal_year: int = Field(default=2026)
    primary_adversary: APTActor
    target_entities: List[str] = Field(default_factory=list)
    narrative_summary: str = Field(...)
    milestones: List[APTPhaseMilestone] = Field(default_factory=list)
    total_entries_generated: int = Field(default=0)
    total_illicit_volume: Decimal = Field(default=Decimal("0.00"))
    is_concealed_at_close: bool = Field(default=True)
