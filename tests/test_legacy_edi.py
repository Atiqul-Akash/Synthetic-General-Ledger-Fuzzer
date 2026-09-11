"""Automated unit test suite for Legacy Supply Chain ANSI X12 and UN/EDIFACT Protocols."""

from decimal import Decimal
import pytest

from gl_fuzzer.legacy_protocols.models import (
    LegacyProtocolType,
    ProtocolFuzzAnomaly,
)
from gl_fuzzer.legacy_protocols.edi_engine import (
    EDIEngine,
    EDIMutator,
    EDISerializer,
)


class TestEDISerializer:
    """Validates EDI serialization conformity for ANSI X12 and UN/EDIFACT standards."""

    def test_serialize_x12_810_invoice(self):
        edi = EDISerializer.serialize_x12_810_invoice(
            invoice_number="INV-2026-001",
            invoice_date="2026-04-14",
            vendor_id="VENDACME",
            customer_id="CUSTCORP",
            total_amount=Decimal("45000.00"),
        )
        lines = edi.splitlines()

        # Envelopes
        assert lines[0].startswith("ISA*00*")
        assert lines[1].startswith("GS*IN*")
        assert lines[2] == "ST*810*0001~"

        # Mandatory 810 segments
        assert any(l.startswith("BIG*20260414*INV-2026-001") for l in lines)
        assert any(l.startswith("N1*RE*VENDACME") for l in lines)
        assert any(l.startswith("N1*ST*CUSTCORP") for l in lines)
        assert any(l.startswith("ITD*") for l in lines)
        assert any(l.startswith("IT1*1*") for l in lines)
        assert any(l.startswith("TDS*4500000") for l in lines)  # $45,000 in cents
        assert any(l.startswith("CTT*1~") for l in lines)

        # Trailer envelopes
        assert lines[-3].startswith("SE*")
        assert lines[-2] == "GE*1*1~"
        assert lines[-1].startswith("IEA*1*")

    def test_serialize_x12_850_po(self):
        edi = EDISerializer.serialize_x12_850_po(
            po_number="PO-2026-8899",
            po_date="2026-04-14",
            vendor_id="VEND_SUPPLY",
            buyer_id="CORP_BUYER",
            total_amount=Decimal("12500.00"),
        )
        lines = edi.splitlines()

        assert lines[0].startswith("ISA*00*")
        assert lines[1].startswith("GS*PO*")
        assert lines[2] == "ST*850*0001~"
        assert any(l.startswith("BEG*00*NE*PO-2026-8899") for l in lines)
        assert any(l.startswith("PO1*1*") for l in lines)
        assert lines[-1].startswith("IEA*1*")

    def test_serialize_x12_856_asn(self):
        edi = EDISerializer.serialize_x12_856_asn(
            shipment_id="SHIP-991122",
            ship_date="2026-04-14",
            vendor_id="VEND_LOGISTICS",
            receiver_id="PLANT_01",
        )
        lines = edi.splitlines()

        assert lines[0].startswith("ISA*00*")
        assert lines[1].startswith("GS*SH*")
        assert lines[2] == "ST*856*0001~"
        assert any(l.startswith("BSN*00*SHIP-991122") for l in lines)
        assert any(l.startswith("HL*1**S~") for l in lines)
        assert any(l.startswith("SN1*1*100*EA~") for l in lines)
        assert lines[-1].startswith("IEA*1*")

    def test_serialize_edifact_invoic(self):
        edi = EDISerializer.serialize_edifact_invoic(
            invoice_number="INV-EUR-900",
            invoice_date="2026-04-14",
            supplier_id="SUPPLIER_DE",
            buyer_id="BUYER_FR",
            total_amount=Decimal("62000.50"),
            currency="EUR",
        )
        lines = edi.splitlines()

        assert lines[0] == "UNA:+.? '"
        assert lines[1].startswith("UNB+UNOC:3+SUPPLIER_DE")
        assert lines[2] == "UNH+1+INVOIC:D:96A:UN'"
        assert any(l.startswith("BGM+380+INV-EUR-900") for l in lines)
        assert any(l.startswith("MOA+77:62000.50:EUR:4'") for l in lines)
        assert any(l.startswith("UNT+") for l in lines)
        assert lines[-1] == "UNZ+1+00000001'"

    def test_serialize_edifact_orders(self):
        edi = EDISerializer.serialize_edifact_orders(
            po_number="ORD-2026-33",
            po_date="2026-04-14",
            supplier_id="SUPP_NL",
            buyer_id="BUYER_DE",
            total_amount=Decimal("15000.00"),
            currency="EUR",
        )
        lines = edi.splitlines()

        assert lines[0] == "UNA:+.? '"
        assert lines[2] == "UNH+1+ORDERS:D:96A:UN'"
        assert any(l.startswith("BGM+220+ORD-2026-33") for l in lines)
        assert lines[-1] == "UNZ+1+00000002'"


class TestEDIMutator:
    """Validates security fuzzing mutations on EDI streams."""

    def test_delimiter_corruption(self):
        raw = EDISerializer.serialize_x12_810_invoice(
            invoice_number="INV-001",
            invoice_date="2026-04-14",
            vendor_id="VEND1",
            customer_id="CUST1",
            total_amount=Decimal("100.00"),
        )
        mutated = EDIMutator.apply_mutations(raw, [ProtocolFuzzAnomaly.DELIMITER_CORRUPTION])
        # Either ^ replaced ~ or : replaced *
        assert "^" in mutated or mutated != raw

    def test_envelope_truncation(self):
        raw = EDISerializer.serialize_x12_810_invoice(
            invoice_number="INV-001",
            invoice_date="2026-04-14",
            vendor_id="VEND1",
            customer_id="CUST1",
            total_amount=Decimal("100.00"),
        )
        mutated = EDIMutator.apply_mutations(raw, [ProtocolFuzzAnomaly.ENVELOPE_TRUNCATION])
        assert not any(l.startswith("IEA") for l in mutated.splitlines())
        assert not any(l.startswith("GE*") for l in mutated.splitlines())

    def test_segment_count_desync(self):
        raw = EDISerializer.serialize_x12_810_invoice(
            invoice_number="INV-001",
            invoice_date="2026-04-14",
            vendor_id="VEND1",
            customer_id="CUST1",
            total_amount=Decimal("100.00"),
        )
        mutated = EDIMutator.apply_mutations(raw, [ProtocolFuzzAnomaly.SEGMENT_COUNT_DESYNC])
        # SE segment should have altered count (> 90)
        se_line = [l for l in mutated.splitlines() if l.startswith("SE*")][0]
        count = int(se_line.split("*")[1])
        assert count > 90

    def test_null_byte_injection(self):
        raw = EDISerializer.serialize_edifact_invoic(
            invoice_number="INV-001",
            invoice_date="2026-04-14",
            supplier_id="S1",
            buyer_id="B1",
            total_amount=Decimal("100.00"),
        )
        mutated = EDIMutator.apply_mutations(raw, [ProtocolFuzzAnomaly.NULL_BYTE_INJECTION])
        assert "\x00" in mutated


class TestEDIEngine:
    """Validates the high-level EDIEngine generation workflow."""

    def test_generate_edi_payload_x12(self):
        res = EDIEngine.generate_edi_payload(
            protocol=LegacyProtocolType.ANSI_X12_810,
            document_id="INV-9001",
            date_str="2026-04-14",
            sender_id="VEND_A",
            receiver_id="BUYER_B",
            amount=Decimal("50000.00"),
            anomalies=[ProtocolFuzzAnomaly.BUFFER_OVERFLOW],
        )
        assert res.protocol_type == LegacyProtocolType.ANSI_X12_810
        assert res.is_binary is False
        assert res.byte_size > 4000  # includes 4KB overflow buffer
        assert ProtocolFuzzAnomaly.BUFFER_OVERFLOW in res.applied_anomalies
