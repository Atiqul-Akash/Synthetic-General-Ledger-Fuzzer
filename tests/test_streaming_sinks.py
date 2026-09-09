"""Comprehensive unit tests for Real-Time Event Streaming Sinks."""

from decimal import Decimal
import json
import pytest

from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyRecord, AnomalyType, SOXControlRef
from gl_fuzzer.streaming.base import GLStreamPublisher, StreamBatchResult, StreamPublishResult
from gl_fuzzer.streaming.cloud_publishers import EventHubGLPublisher, KinesisGLPublisher
from gl_fuzzer.streaming.kafka_publisher import EmbeddedKafkaBroker, KafkaGLPublisher
from gl_fuzzer.streaming.serializers import (
    ACDOCASerializer,
    CloudEventsSerializer,
    JSONSerializer,
)


def _make_sample_entry(doc_num: str = "STREAM_DOC_1") -> JournalEntry:
    lines = [
        LineItem(
            line_id=f"{doc_num}_1",
            entry_id=doc_num,
            line_number=1,
            account_code="10100",
            debit_credit=DebitCredit.DEBIT,
            amount=Decimal("1500.25"),
        ),
        LineItem(
            line_id=f"{doc_num}_2",
            entry_id=doc_num,
            line_number=2,
            account_code="40000",
            debit_credit=DebitCredit.CREDIT,
            amount=Decimal("1500.25"),
        ),
    ]
    return JournalEntry(
        entry_id=doc_num,
        batch_id="STREAM_B1",
        company_code="1000",
        document_type=DocumentType.DR,
        document_number=doc_num,
        fiscal_year=2026,
        fiscal_period=1,
        posting_date="2026-01-15",
        document_date="2026-01-15",
        created_at="2026-01-15T10:00:00Z",
        lines=lines,
    )


def test_embedded_kafka_broker_produce_consume():
    broker = EmbeddedKafkaBroker(default_partitions=4)
    p_id, offset = broker.produce(topic="test.topic", key="key1", value=b'{"val": 1}')
    assert 0 <= p_id < 4
    assert offset == 0
    assert broker.get_message_count("test.topic") == 1

    messages = broker.consume(topic="test.topic", partition=p_id, start_offset=0)
    assert len(messages) == 1
    assert messages[0]["key"] == "key1"
    assert messages[0]["value"] == b'{"val": 1}'


def test_kafka_publisher_publish_entry():
    publisher = KafkaGLPublisher()
    assert publisher.connect() is True

    entry = _make_sample_entry()
    res = publisher.publish_entry(entry, topic="gl.transactions.v1")

    assert res.success is True
    assert res.topic == "gl.transactions.v1"
    assert res.message_id == entry.entry_id
    assert res.offset is not None
    assert publisher.embedded_broker.get_message_count("gl.transactions.v1") == 1


def test_kafka_publisher_publish_batch():
    publisher = KafkaGLPublisher()
    entries = [_make_sample_entry(f"DOC_{i}") for i in range(10)]
    batch = Batch(batch_id="B1", created_at="2026-01-15T10:00:00Z", entries=entries)

    batch_res = publisher.publish_batch(batch, topic="gl.batch.topic")
    assert batch_res.total_published == 10
    assert batch_res.total_failed == 0
    assert batch_res.publish_rate_eps > 0.0


def test_kafka_publisher_publish_anomaly():
    publisher = KafkaGLPublisher()
    anom = AnomalyRecord(
        anomaly_id="ANOM_001",
        anomaly_type=AnomalyType.SMURFING_SPLIT_APPROVAL,
        sox_control=SOXControlRef.P2P_DOA_LIMITS.value,
        audit_script="audit_test_doa",
        description="DOA limit evasion",
        forensic_indicator="Cluster of payments below $10,000",
    )
    res = publisher.publish_anomaly(anom, topic="gl.anomalies.v1")
    assert res.success is True
    assert res.message_id == "ANOM_001"


def test_kinesis_publisher_embedded_fallback():
    publisher = KinesisGLPublisher(stream_name="gl-kinesis-test")
    assert publisher.connect() is True

    entry = _make_sample_entry()
    res = publisher.publish_entry(entry)
    assert res.success is True
    assert res.topic == "gl-kinesis-test"
    assert publisher.embedded_queue.size() == 1


def test_eventhub_publisher_embedded_fallback():
    publisher = EventHubGLPublisher(eventhub_name="gl-eventhub-test")
    assert publisher.connect() is True

    entry = _make_sample_entry()
    res = publisher.publish_entry(entry)
    assert res.success is True
    assert res.topic == "gl-eventhub-test"
    assert publisher.embedded_queue.size() == 1


def test_json_serializer_decimal_precision():
    entry = _make_sample_entry()
    serialized = JSONSerializer.serialize_entry(entry)
    data = json.loads(serialized.decode("utf-8"))
    assert str(data["lines"][0]["amount"]) == "1500.25"


def test_cloudevents_serializer_schema_compliance():
    entry = _make_sample_entry()
    raw = CloudEventsSerializer.serialize_entry(entry)
    ce = json.loads(raw.decode("utf-8"))

    assert ce["specversion"] == "1.0"
    assert ce["id"] == entry.entry_id
    assert ce["type"] == "com.finance.gl.journal_entry.posted"
    assert ce["datacontenttype"] == "application/json"
    assert "data" in ce
    assert ce["subject"] == entry.document_number


def test_acdoca_serializer_field_mapping():
    entry = _make_sample_entry()
    raw = ACDOCASerializer.serialize_line(entry, line_idx=0)
    acdoca = json.loads(raw.decode("utf-8"))

    assert acdoca["RCLNT"] == "100"
    assert acdoca["RBUKRS"] == "1000"
    assert acdoca["BELNR"] == entry.document_number
    assert acdoca["RACCT"] == "10100"
    assert acdoca["DRCRK"] == "S"  # Debit
