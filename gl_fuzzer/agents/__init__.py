"""Autonomous Generative LLM Social Engineering Fraud Agent Package."""

from gl_fuzzer.agents.models import (
    AgentPersona,
    PersuasionTactic,
    DialogueTurn,
    SocialEngineeringThread,
    LLMProviderType,
    LLMConfig,
)
from gl_fuzzer.agents.engine import (
    BaseLLMProvider,
    MockHeuristicProvider,
    ExternalAPIProvider,
    HeuristicGenerativeEngine,
    ExecutivePretextAgent,
    CollusiveVendorAgent,
    AuditorDeceptionAgent,
    MultiTurnDialogueSimulator,
)

__all__ = [
    "AgentPersona",
    "PersuasionTactic",
    "DialogueTurn",
    "SocialEngineeringThread",
    "LLMProviderType",
    "LLMConfig",
    "BaseLLMProvider",
    "MockHeuristicProvider",
    "ExternalAPIProvider",
    "HeuristicGenerativeEngine",
    "ExecutivePretextAgent",
    "CollusiveVendorAgent",
    "AuditorDeceptionAgent",
    "MultiTurnDialogueSimulator",
]
