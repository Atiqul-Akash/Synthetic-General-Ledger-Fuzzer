"""Base streaming publisher abstractions and event result models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from gl_fuzzer.models.journal import Batch, JournalEntry
from gl_fuzzer.models.manifest import AnomalyRecord


class StreamPublishResult(BaseModel):
    """Result of publishing a single event message to a streaming broker."""
    success: bool
    offset: Optional[int] = None
    partition: Optional[int] = None
    topic: str
    message_id: str
    latency_ms: int = 0
    error: Optional[str] = None


class StreamBatchResult(BaseModel):
    """Aggregate result from publishing a batch of streaming events."""
    total_published: int = 0
    total_failed: int = 0
    total_anomalies_published: int = 0
    publish_rate_eps: float = 0.0  # Events per second achieved
    results: List[StreamPublishResult] = Field(default_factory=list)


class GLStreamPublisher(ABC):
    """Abstract base class for real-time general ledger stream sinks."""

    def __init__(self):
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Connects to streaming cluster / message bus."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnects and releases network sockets."""
        pass

    @abstractmethod
    def publish_entry(self, entry: JournalEntry, topic: str = "gl.transactions.v1") -> StreamPublishResult:
        """Streams a single journal entry event."""
        pass

    @abstractmethod
    def publish_batch(
        self,
        batch: Batch,
        topic: str = "gl.transactions.v1",
        rate_limit_eps: Optional[int] = None,
    ) -> StreamBatchResult:
        """Streams an entire batch of journal entries, optionally rate throttled."""
        pass

    @abstractmethod
    def publish_anomaly(self, anomaly: AnomalyRecord, topic: str = "gl.anomalies.v1") -> StreamPublishResult:
        """Streams a ground-truth anomaly signal event."""
        pass

    @abstractmethod
    def flush(self) -> None:
        """Flushes in-flight producer buffer."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Flushes and closes the publisher."""
        pass
