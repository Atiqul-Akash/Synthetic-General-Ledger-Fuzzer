"""Automated unit test suite for IBM Mainframe, COBOL, EBCDIC, NACHA ACH, BAI2, and SWIFT MT940."""

from decimal import Decimal
import pytest

from gl_fuzzer.legacy_protocols.models import (
    LegacyProtocolType,
    ProtocolFuzzAnomaly,
)
from gl_fuzzer.legacy_protocols.mainframe_engine import (
    MainframeEngine,
    MainframeMutator,
    MainframeSerializer,
    pack_comp3,
    unpack_comp3,
)


class TestComp3PackedDecimal:
    """Validates COBOL COMP-3 packed decimal packing and unpacking roundtrips."""

    @pytest.mark.parametrize("val", [0, 1, 9, 12, 123, 1234, 12345, 99999, 12345678901])
    def test_comp3_roundtrip_positive(self, val):
        packed = pack_comp3(val, num_bytes=6, signed=True)
        assert len(packed) == 6
        unpacked = unpack_comp3(packed, signed=True)
        assert unpacked == val

    @pytest.mark.parametrize("val", [-1, -12, -123, -1234, -12345, -99999])
    def test_comp3_roundtrip_negative(self, val):
        packed = pack_comp3(val, num_bytes=4, signed=True)
        assert len(packed) == 4
        unpacked = unpack_comp3(packed, signed=True)
        assert unpacked == val

    def test_comp3_sign_nibble(self):
        pos_packed = pack_comp3(500, num_bytes=3, signed=True)
        # Lowest nibble of last byte should be 0xC (positive)
        assert (pos_packed[-1] & 0x0F) == 0x0C

        neg_packed = pack_comp3(-500, num_bytes=3, signed=True)
        # Lowest nibble of last byte should be 0xD (negative)
        assert (neg_packed[-1] & 0x0F) == 0x0D


class TestCOBOLSerialization:
    """Validates IBM fixed-width punched-card and line printer serializations."""

    def test_cobol_80col_punched_card(self):
        records = [
            {"doc_id": "VCH001", "date": "20260414", "account": "10100000", "dr_cr": "DR", "amount": "1250.50", "description": "CONSULTING EXPENSE"},
            {"doc_id": "VCH002", "date": "20260414", "account": "20100000", "dr_cr": "CR", "amount": "1250.50", "description": "ACCOUNTS PAYABLE"},
        ]
        text = MainframeSerializer.serialize_cobol_80col(records)
        lines = text.splitlines()
        assert len(lines) == 2
        for line in lines:
            assert len(line) == 80, f"Line length must be exactly 80 chars, got {len(line)}: '{line}'"
        assert lines[0].startswith("000001 VCH001    20260414")

    def test_cobol_132col_line_report(self):
        records = [
            {"doc_id": "VCH001", "date": "20260414", "account": "10100000", "dr_cr": "DR", "amount": "1250.50", "description": "GENERAL JOURNAL LINE"},
        ]
        text = MainframeSerializer.serialize_cobol_132col(records)
        lines = text.splitlines()
        assert len(lines) == 3  # Header + separator + record
        for line in lines:
            assert len(line) == 132, f"Line length must be exactly 132 chars, got {len(line)}"


class TestEBCDICBinarySerialization:
    """Validates IBM Mainframe CP037 binary record layout and COMP-3 amount packing."""

    def test_ebcdic_binary_32byte_records(self):
        records = [
            {"doc_id": "DOC01", "account": "10100000", "dr_cr": "DR", "amount": "5000.00"},
            {"doc_id": "DOC02", "account": "20100000", "dr_cr": "CR", "amount": "5000.00"},
        ]
        raw_bin = MainframeSerializer.serialize_ebcdic_binary(records, code_page="cp037")
        assert len(raw_bin) == 64  # 2 records * 32 bytes

        # Check record 1
        rec1 = raw_bin[:32]
        seq = int.from_bytes(rec1[0:4], byteorder="big")
        assert seq == 1

        # Decode EBCDIC fields
        doc_ebcdic = rec1[4:12].decode("cp037").strip()
        assert doc_ebcdic == "DOC01"

        acct_ebcdic = rec1[12:20].decode("cp037").strip()
        assert acct_ebcdic == "10100000"

        drcr_ebcdic = rec1[20:22].decode("cp037").strip()
        assert drcr_ebcdic == "DR"

        # Unpack COMP-3 amount (cents: 500000)
        amt_cents = unpack_comp3(rec1[22:28], signed=True)
        assert amt_cents == 500000


class TestNACHAACHSerialization:
    """Validates strict NACHA ACH 94-character batch file invariants."""

    def test_nacha_ach_94_char_invariant(self):
        entries = [
            {"routing": "021000021", "account": "987654321", "amount": "100.00", "dr_cr": "CR", "vendor_id": "VEND01", "name": "ALPHA CORP"},
            {"routing": "021000021", "account": "112233445", "amount": "200.00", "dr_cr": "DR", "vendor_id": "VEND02", "name": "BETA CORP"},
            {"routing": "121000358", "account": "556677889", "amount": "150.00", "dr_cr": "CR", "vendor_id": "VEND03", "name": "GAMMA CORP"},
        ]
        text = MainframeSerializer.serialize_nacha_ach(entries)
        lines = text.splitlines()

        # Invariant 1: All lines must be strictly 94 characters
        for i, line in enumerate(lines, start=1):
            assert len(line) == 94, f"NACHA line {i} must be exactly 94 chars, got {len(line)}: '{line}'"

        # Invariant 2: Total file lines must be a multiple of 10 (blocking factor 10)
        assert len(lines) % 10 == 0

        # Invariant 3: Record types order: 1 (File Header), 5 (Batch Header), 6s (Entries), 8 (Batch Control), 9 (File Control)
        assert lines[0][0] == "1"
        assert lines[1][0] == "5"
        assert lines[2][0] == "6"
        assert lines[3][0] == "6"
        assert lines[4][0] == "6"
        assert lines[5][0] == "8"
        assert lines[6][0] == "9"
        # Remaining lines padded with all 9s
        for p in lines[7:]:
            assert p == "9" * 94

        # Invariant 4: Entry Hash calculation in Record 8 and 9
        # Sum of 8-digit routing IDs: 02100002 + 02100002 + 12100035 = 16300039
        expected_hash = "0016300039"
        rec8 = lines[5]
        entry_hash_in_8 = rec8[10:20]
        assert entry_hash_in_8 == expected_hash

        rec9 = lines[6]
        entry_hash_in_9 = rec9[21:31]
        assert entry_hash_in_9 == expected_hash


class TestBAI2AndSWIFTSerialization:
    """Validates banking cash management and statement serializations."""

    def test_serialize_bai2(self):
        entries = [
            {"amount": "500.00", "dr_cr": "CR", "doc_id": "WIRE001"},
            {"amount": "250.00", "dr_cr": "DR", "doc_id": "WIRE002"},
        ]
        text = MainframeSerializer.serialize_bai2(entries)
        lines = text.splitlines()
        assert lines[0].startswith("01,")
        assert lines[1].startswith("02,")
        assert lines[2].startswith("03,")
        assert lines[3].startswith("16,195,50000,")
        assert lines[4].startswith("16,495,25000,")
        assert lines[-1].startswith("99,")

    def test_serialize_swift_mt940(self):
        entries = [
            {"amount": "12500.00", "dr_cr": "CR", "doc_id": "VCH9001", "description": "VENDOR SETTLEMENT"},
        ]
        text = MainframeSerializer.serialize_swift_mt940(entries, opening_balance=Decimal("10000.00"))
        lines = text.splitlines()
        assert any(l.startswith(":20:") for l in lines)
        assert any(l.startswith(":25:") for l in lines)
        assert any(l.startswith(":60F:C260414USD10000,00") for l in lines)
        assert any(l.startswith(":61:") for l in lines)
        assert any(l.startswith(":86:/BENM/VENDOR SETTLEMENT") for l in lines)
        assert any(l.startswith(":62F:C260414USD22500,00") for l in lines)
        assert lines[-1] == "-"


class TestMainframeMutatorAndEngine:
    """Validates protocol fuzzing anomalies applied to Mainframe and Banking streams."""

    def test_nacha_hash_total_desync(self):
        entries = [{"routing": "021000021", "account": "123", "amount": "10.00", "dr_cr": "CR"}]
        res = MainframeEngine.generate_payload(
            protocol=LegacyProtocolType.NACHA_ACH,
            records=entries,
            anomalies=[ProtocolFuzzAnomaly.HASH_TOTAL_DESYNC],
        )
        lines = res.raw_payload.splitlines()
        rec8 = [l for l in lines if l.startswith("8")][0]
        # Entry hash should be tampered to 9999999999
        assert rec8[10:20] == "9999999999"

    def test_ebcdic_sign_corruption(self):
        records = [{"doc_id": "D1", "account": "A1", "dr_cr": "DR", "amount": "100.00"}]
        res = MainframeEngine.generate_payload(
            protocol=LegacyProtocolType.EBCDIC_BINARY,
            records=records,
            anomalies=[ProtocolFuzzAnomaly.EBCDIC_SIGN_CORRUPTION],
        )
        assert res.is_binary is True
        # Nibble at offset 27 corrupted
        sign_nibble = res.raw_payload[27] & 0x0F
        assert sign_nibble != 0x0C  # Corrupted away from valid positive sign
