"""Data models for Legacy Enterprise Mainframe and Supply Chain EDI Protocols."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class LegacyProtocolType(str, Enum):
    """Supported legacy enterprise and financial interchange protocols."""
    ANSI_X12_810 = "ANSI_X12_810"            # Invoice
    ANSI_X12_850 = "ANSI_X12_850"            # Purchase Order
    ANSI_X12_856 = "ANSI_X12_856"            # Ship Notice / ASN
    EDIFACT_INVOIC = "EDIFACT_INVOIC"        # UN/EDIFACT D.96A Commercial Invoice
    EDIFACT_ORDERS = "EDIFACT_ORDERS"        # UN/EDIFACT Purchase Order
    COBOL_COPYBOOK_80 = "COBOL_COPYBOOK_80"  # IBM 80-column punch-card layout
    COBOL_COPYBOOK_132 = "COBOL_COPYBOOK_132"# IBM 132-column line layout
    EBCDIC_BINARY = "EBCDIC_BINARY"          # Binary CP037 encoded mainframe dump with COMP-3
    NACHA_ACH = "NACHA_ACH"                  # Strict 94-character US Banking ACH batch
    BAI2 = "BAI2"                            # Bank Cash Management Statement
    SWIFT_MT940 = "SWIFT_MT940"              # Customer Statement Message


class ProtocolFuzzAnomaly(str, Enum):
    """Protocol-level mutations and corruptions injected during legacy fuzzing."""
    NONE = "NONE"
    DELIMITER_CORRUPTION = "DELIMITER_CORRUPTION"        # Swapped or missing segment/element delimiters
    ENVELOPE_TRUNCATION = "ENVELOPE_TRUNCATION"          # Missing trailer envelopes (IEA, UNZ, Record 9)
    SEGMENT_COUNT_DESYNC = "SEGMENT_COUNT_DESYNC"        # Hash/trailer counts differ from actual segments
    BUFFER_OVERFLOW = "BUFFER_OVERFLOW"                  # Field length exceeds COBOL or EDI max length
    EBCDIC_SIGN_CORRUPTION = "EBCDIC_SIGN_CORRUPTION"    # Invalid COMP-3 packed decimal sign nibble
    NULL_BYTE_INJECTION = "NULL_BYTE_INJECTION"          # Raw 0x00 null bytes injected into records
    HASH_TOTAL_DESYNC = "HASH_TOTAL_DESYNC"              # NACHA Entry Hash does not match routing sum
    FIXED_WIDTH_OVERFLOW = "FIXED_WIDTH_OVERFLOW"        # Line length deviates from strict 94/80 chars


class LegacySerializationResult(BaseModel):
    """Result of serializing accounting documents into legacy EDI or mainframe formats."""
    protocol_type: LegacyProtocolType
    raw_payload: Union[str, bytes]
    is_binary: bool = False
    record_count: int = 0
    byte_size: int = 0
    applied_anomalies: List[ProtocolFuzzAnomaly] = Field(default_factory=list)
    encoding: str = "utf-8"
    metadata: Dict[str, Any] = Field(default_factory=dict)
