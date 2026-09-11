"""Apache Kafka stream publisher with zero-dependency embedded mock broker fallback."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from gl_fuzzer.models.journal import Batch, JournalEntry
from gl_fuzzer.models.manifest import AnomalyRecord
from gl_fuzzer.streaming.base import (
    GLStreamPublisher,
    StreamBatchResult,
    StreamPublishResult,
)
from gl_fuzzer.streaming.serializers import CloudEventsSerializer, JSONSerializer


class EmbeddedKafkaBroker:
    """Thread-safe in-memory Kafka broker simulator supporting topic partitions and offsets."""

    def __init__(self, default_partitions: int = 4):
        self.default_partitions = default_partitions
        self._lock = threading.Lock()
        # topic -> partition_id -> list of records
        self._topics: Dict[str, Dict[int, List[Dict[str, Any]]]] = defaultdict(
            lambda: {p: [] for p in range(self.default_partitions)}
        )

    def produce(
        self,
        topic: str,
        key: str,
        value: bytes,
        partition: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Appends record to partition and returns (partition_id, offset)."""
        with self._lock:
            parts = self._topics[topic]
            if partition is None:
                # Deterministic hash partitioning
                hash_int = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
                p_id = hash_int % len(parts)
            else:
                p_id = partition % len(parts)

            records = parts[p_id]
            offset = len(records)
            records.append({
                "offset": offset,
                "key": key,
                "value": value,
                "timestamp_ms": int(time.time() * 1000),
            })
            return p_id, offset

    def get_message_count(self, topic: str) -> int:
        with self._lock:
            if topic not in self._topics:
                return 0
            return sum(len(recs) for recs in self._topics[topic].values())

    def consume(
        self,
        topic: str,
        partition: int = 0,
        start_offset: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            if topic not in self._topics or partition not in self._topics[topic]:
                return []
            recs = self._topics[topic][partition]
            return recs[start_offset : start_offset + limit]


class KafkaGLPublisher(GLStreamPublisher):
    """Kafka stream publisher integrating live broker or embedded simulation."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        num_partitions: int = 4,
        use_cloudevents: bool = True,
    ):
        super().__init__()
        self.bootstrap_servers = bootstrap_servers
        self.num_partitions = num_partitions
        self.use_cloudevents = use_cloudevents
        self.embedded_broker = EmbeddedKafkaBroker(default_partitions=num_partitions)
        self.use_live = False
        self.live_producer = None

        # Check for live Kafka drivers
        try:
            from confluent_kafka import Producer  # type: ignore
            if bootstrap_servers not in ("localhost:9092", "embedded"):
                self.live_producer = Producer({"bootstrap.servers": bootstrap_servers})
                self.use_live = True
        except ImportError:
            try:
                from kafka import KafkaProducer  # type: ignore
                if bootstrap_servers not in ("localhost:9092", "embedded"):
                    self.live_producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
                    self.use_live = True
            except ImportError:
                self.use_live = False

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> None:
        self.flush()
        self.is_connected = False

    def publish_entry(self, entry: JournalEntry, topic: str = "gl.transactions.v1") -> StreamPublishResult:
        start = time.perf_counter()
        if self.use_cloudevents:
            payload = CloudEventsSerializer.serialize_entry(entry)
        else:
            payload = JSONSerializer.serialize_entry(entry)

        key = f"{entry.company_code}:{entry.document_number}"

        try:
            if self.use_live and self.live_producer:
                self.live_producer.produce(topic, key=key.encode("utf-8"), value=payload)
                partition, offset = 0, 0
            else:
                partition, offset = self.embedded_broker.produce(topic=topic, key=key, value=payload)

            latency = int((time.perf_counter() - start) * 1000)
            return StreamPublishResult(
                success=True,
                offset=offset,
                partition=partition,
                topic=topic,
                message_id=entry.entry_id,
                latency_ms=latency,
            )
        except Exception as ex:
            latency = int((time.perf_counter() - start) * 1000)
            return StreamPublishResult(
                success=False,
                topic=topic,
                message_id=entry.entry_id,
                latency_ms=latency,
                error=str(ex),
            )

    def publish_batch(
        self,
        batch: Batch,
        topic: str = "gl.transactions.v1",
        rate_limit_eps: Optional[int] = None,
    ) -> StreamBatchResult:
        start = time.perf_counter()
        results: List[StreamPublishResult] = []
        delay = (1.0 / rate_limit_eps) if (rate_limit_eps and rate_limit_eps > 0) else 0.0

        for entry in batch.entries:
            res = self.publish_entry(entry, topic=topic)
            results.append(res)
            if delay > 0:
                time.sleep(delay)

        self.flush()
        elapsed = time.perf_counter() - start
        succ = sum(1 for r in results if r.success)
        fail = len(results) - succ
        rate = len(results) / elapsed if elapsed > 0 else 0.0

        return StreamBatchResult(
            total_published=succ,
            total_failed=fail,
            total_anomalies_published=sum(1 for e in batch.entries if e.is_anomaly),
            publish_rate_eps=round(rate, 2),
            results=results,
        )

    def publish_anomaly(self, anomaly: AnomalyRecord, topic: str = "gl.anomalies.v1") -> StreamPublishResult:
        start = time.perf_counter()
        if self.use_cloudevents:
            payload = CloudEventsSerializer.serialize_anomaly(anomaly)
        else:
            payload = JSONSerializer.serialize_anomaly(anomaly)

        key = anomaly.anomaly_id
        partition, offset = self.embedded_broker.produce(topic=topic, key=key, value=payload)
        latency = int((time.perf_counter() - start) * 1000)

        return StreamPublishResult(
            success=True,
            offset=offset,
            partition=partition,
            topic=topic,
            message_id=anomaly.anomaly_id,
            latency_ms=latency,
        )

    def flush(self) -> None:
        if self.use_live and self.live_producer and hasattr(self.live_producer, "flush"):
            self.live_producer.flush()

    def close(self) -> None:
        self.disconnect()
