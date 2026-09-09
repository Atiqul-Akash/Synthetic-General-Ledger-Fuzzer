"""Real-time event streaming module for Kafka, Kinesis, and Event Hubs."""

from gl_fuzzer.streaming.base import (
    GLStreamPublisher,
    StreamBatchResult,
    StreamPublishResult,
)
from gl_fuzzer.streaming.serializers import (
    ACDOCASerializer,
    CloudEventsSerializer,
    JSONSerializer,
)
from gl_fuzzer.streaming.kafka_publisher import (
    EmbeddedKafkaBroker,
    KafkaGLPublisher,
)
from gl_fuzzer.streaming.cloud_publishers import (
    EventHubGLPublisher,
    KinesisGLPublisher,
)

__all__ = [
    "GLStreamPublisher",
    "StreamPublishResult",
    "StreamBatchResult",
    "JSONSerializer",
    "CloudEventsSerializer",
    "ACDOCASerializer",
    "EmbeddedKafkaBroker",
    "KafkaGLPublisher",
    "KinesisGLPublisher",
    "EventHubGLPublisher",
]
