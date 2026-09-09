"""Stream event serialization engines supporting JSON, CloudEvents v1.0, and SAP ACDOCA."""

from __future__ import annotations

import json
from typing import Any, Dict
from gl_fuzzer.models.journal import JournalEntry
from gl_fuzzer.models.manifest import AnomalyRecord
from gl_fuzzer.exporters.acdoca_exporter import SAPACDOCAExporter


class JSONSerializer:
    """Canonical JSON event serializer preserving exact decimal representations."""

    @classmethod
    def serialize_entry(cls, entry: JournalEntry) -> bytes:
        return entry.model_dump_json().encode("utf-8")

    @classmethod
    def serialize_anomaly(cls, anomaly: AnomalyRecord) -> bytes:
        return anomaly.model_dump_json().encode("utf-8")


class CloudEventsSerializer:
    """Standard CloudEvents v1.0 specification compliant envelope serializer."""

    @classmethod
    def serialize_entry(cls, entry: JournalEntry) -> bytes:
        envelope = {
            "specversion": "1.0",
            "id": entry.entry_id,
            "source": f"/finance/company/{entry.company_code}",
            "type": "com.finance.gl.journal_entry.posted",
            "datacontenttype": "application/json",
            "time": entry.created_at,
            "subject": entry.document_number,
            "data": entry.model_dump(mode="json"),
        }
        return json.dumps(envelope, ensure_ascii=False).encode("utf-8")

    @classmethod
    def serialize_anomaly(cls, anomaly: AnomalyRecord) -> bytes:
        envelope = {
            "specversion": "1.0",
            "id": anomaly.anomaly_id,
            "source": "/finance/audit/anomaly_engine",
            "type": f"com.finance.audit.anomaly.{anomaly.anomaly_type.lower()}",
            "datacontenttype": "application/json",
            "subject": anomaly.sox_control,
            "data": anomaly.model_dump(mode="json"),
        }
        return json.dumps(envelope, ensure_ascii=False).encode("utf-8")


class ACDOCASerializer:
    """Serializes journal entry lines into individual SAP S/4HANA ACDOCA Universal Journal events."""

    @classmethod
    def serialize_line(cls, entry: JournalEntry, line_idx: int) -> bytes:
        row = SAPACDOCAExporter.to_acdoca_row(entry, line_idx, entry.lines[line_idx])
        # Convert Decimals to string representation
        row["WSL"] = str(row["WSL"])
        row["HSL"] = str(row["HSL"])
        row["KSL"] = str(row["KSL"])
        return json.dumps(row, ensure_ascii=False).encode("utf-8")
