"""ANSI X12 and UN/EDIFACT Electronic Data Interchange (EDI) Protocol Serialization & Fuzzing Engine."""

from __future__ import annotations

from decimal import Decimal
import random
from typing import Any, Dict, List, Optional

from gl_fuzzer.legacy_protocols.models import (
    LegacyProtocolType,
    LegacySerializationResult,
    ProtocolFuzzAnomaly,
)


class EDISerializer:
    """Serializes financial transactions and supply chain orders into ANSI X12 and UN/EDIFACT formats."""

    @staticmethod
    def serialize_x12_810_invoice(
        invoice_number: str,
        invoice_date: str,
        vendor_id: str,
        customer_id: str,
        total_amount: Decimal,
        currency: str = "USD",
        line_items: Optional[List[Dict[str, Any]]] = None,
        control_number: str = "000000001",
    ) -> str:
        """Serializes an invoice to ANSI X12 810 format."""
        date_str = invoice_date.replace("-", "")[:6] or "260414"
        date_full = invoice_date.replace("-", "")[:8] or "20260414"
        amount_cents = int(total_amount * 100)

        lines = [
            f"ISA*00*          *00*          *ZZ*{vendor_id.ljust(15)[:15]}*ZZ*{customer_id.ljust(15)[:15]}*{date_str}*1200*U*00401*{control_number}*0*P*:~",
            f"GS*IN*{vendor_id[:10]}*{customer_id[:10]}*{date_full}*1200*1*X*004010~",
            f"ST*810*0001~",
            f"BIG*{date_full}*{invoice_number}***DI~",
            f"N1*RE*{vendor_id[:35]}~",
            f"N1*ST*{customer_id[:35]}~",
            f"ITD*01*3*2**30~",
        ]

        items = line_items or [
            {"line": 1, "qty": 10, "unit_price": total_amount / Decimal("10") if total_amount else Decimal("100.00"), "uom": "EA", "desc": "RAW MATERIAL COMPONENTS"}
        ]

        for item in items:
            idx = item.get("line", 1)
            qty = int(item.get("qty", 1))
            price = f"{Decimal(str(item.get('unit_price', 10.00))):.2f}"
            uom = item.get("uom", "EA")
            desc = item.get("desc", "COMMERCIAL GOODS")
            lines.append(f"IT1*{idx}*{qty}*{uom}*{price}**VP*{desc[:20]}~")

        lines.append(f"TDS*{amount_cents}~")
        lines.append(f"CTT*{len(items)}~")
        # Total segments between ST and SE inclusive
        seg_count = len(lines) - 2 + 1  # current lines minus ISA/GS + SE itself
        lines.append(f"SE*{seg_count}*0001~")
        lines.append(f"GE*1*1~")
        lines.append(f"IEA*1*{control_number}~")

        return "\n".join(lines)

    @staticmethod
    def serialize_x12_850_po(
        po_number: str,
        po_date: str,
        vendor_id: str,
        buyer_id: str,
        total_amount: Decimal,
        line_items: Optional[List[Dict[str, Any]]] = None,
        control_number: str = "000000002",
    ) -> str:
        """Serializes a purchase order to ANSI X12 850 format."""
        date_str = po_date.replace("-", "")[:6] or "260414"
        date_full = po_date.replace("-", "")[:8] or "20260414"

        lines = [
            f"ISA*00*          *00*          *ZZ*{buyer_id.ljust(15)[:15]}*ZZ*{vendor_id.ljust(15)[:15]}*{date_str}*0930*U*00401*{control_number}*0*P*:~",
            f"GS*PO*{buyer_id[:10]}*{vendor_id[:10]}*{date_full}*0930*1*X*004010~",
            f"ST*850*0001~",
            f"BEG*00*NE*{po_number}**{date_full}~",
            f"N1*BY*{buyer_id[:35]}~",
            f"N1*SE*{vendor_id[:35]}~",
        ]

        items = line_items or [
            {"line": 1, "qty": 50, "unit_price": Decimal("250.00"), "uom": "EA", "desc": "INDUSTRIAL BEARINGS"}
        ]

        for item in items:
            idx = item.get("line", 1)
            qty = int(item.get("qty", 1))
            price = f"{Decimal(str(item.get('unit_price', 10.00))):.2f}"
            uom = item.get("uom", "EA")
            desc = item.get("desc", "INDUSTRIAL PARTS")
            lines.append(f"PO1*{idx}*{qty}*{uom}*{price}**BP*{desc[:20]}~")

        lines.append(f"CTT*{len(items)}~")
        seg_count = len(lines) - 2 + 1
        lines.append(f"SE*{seg_count}*0001~")
        lines.append(f"GE*1*1~")
        lines.append(f"IEA*1*{control_number}~")

        return "\n".join(lines)

    @staticmethod
    def serialize_x12_856_asn(
        shipment_id: str,
        ship_date: str,
        vendor_id: str,
        receiver_id: str,
        po_number: str = "PO-2026-001",
        control_number: str = "000000003",
    ) -> str:
        """Serializes an advance shipping notice (ASN) to ANSI X12 856 format."""
        date_str = ship_date.replace("-", "")[:6] or "260414"
        date_full = ship_date.replace("-", "")[:8] or "20260414"

        lines = [
            f"ISA*00*          *00*          *ZZ*{vendor_id.ljust(15)[:15]}*ZZ*{receiver_id.ljust(15)[:15]}*{date_str}*1400*U*00401*{control_number}*0*P*:~",
            f"GS*SH*{vendor_id[:10]}*{receiver_id[:10]}*{date_full}*1400*1*X*004010~",
            f"ST*856*0001~",
            f"BSN*00*{shipment_id}*{date_full}*1400~",
            f"HL*1**S~",
            f"N1*SF*{vendor_id[:35]}~",
            f"N1*ST*{receiver_id[:35]}~",
            f"HL*2*1*O~",
            f"PRF*{po_number}~",
            f"HL*3*2*I~",
            f"LIN*1*VP*PART-7890~",
            f"SN1*1*100*EA~",
            f"CTT*3~",
        ]
        seg_count = len(lines) - 2 + 1
        lines.append(f"SE*{seg_count}*0001~")
        lines.append(f"GE*1*1~")
        lines.append(f"IEA*1*{control_number}~")

        return "\n".join(lines)

    @staticmethod
    def serialize_edifact_invoic(
        invoice_number: str,
        invoice_date: str,
        supplier_id: str,
        buyer_id: str,
        total_amount: Decimal,
        currency: str = "EUR",
        line_items: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Serializes a commercial invoice to UN/EDIFACT D.96A INVOIC format."""
        date_full = invoice_date.replace("-", "")[:8] or "20260414"
        amount_str = f"{total_amount:.2f}"

        segments = [
            "UNA:+.? '",
            f"UNB+UNOC:3+{supplier_id}:ZZ+{buyer_id}:ZZ+{date_full[:6]}:1200+00000001++INVOIC'",
            "UNH+1+INVOIC:D:96A:UN'",
            f"BGM+380+{invoice_number}+9'",
            f"DTM+137:{date_full}:102'",
            f"NAD+SU+{supplier_id}::92'",
            f"NAD+BY+{buyer_id}::92'",
        ]

        items = line_items or [
            {"line": 1, "qty": 10, "unit_price": total_amount / Decimal("10") if total_amount else Decimal("100.00"), "desc": "RAW MATERIALS"}
        ]

        for item in items:
            idx = item.get("line", 1)
            qty = item.get("qty", 1)
            price = f"{Decimal(str(item.get('unit_price', 10.00))):.2f}"
            segments.append(f"LIN+{idx}++{item.get('desc', 'MATERIAL')}:VP'")
            segments.append(f"QTY+47:{qty}'")
            segments.append(f"PRI+AAA:{price}'")

        segments.append(f"UNS+S'")
        segments.append(f"MOA+77:{amount_str}:{currency}:4'")
        segments.append(f"CNT+2:{len(items)}'")

        # UNT count includes UNH through UNT inclusive
        unt_count = len(segments) - 2 + 1  # exclude UNA and UNB, include UNT
        segments.append(f"UNT+{unt_count}+1'")
        segments.append("UNZ+1+00000001'")

        return "\n".join(segments)

    @staticmethod
    def serialize_edifact_orders(
        po_number: str,
        po_date: str,
        supplier_id: str,
        buyer_id: str,
        total_amount: Decimal,
        currency: str = "EUR",
    ) -> str:
        """Serializes a purchase order to UN/EDIFACT D.96A ORDERS format."""
        date_full = po_date.replace("-", "")[:8] or "20260414"
        segments = [
            "UNA:+.? '",
            f"UNB+UNOC:3+{buyer_id}:ZZ+{supplier_id}:ZZ+{date_full[:6]}:1000+00000002++ORDERS'",
            "UNH+1+ORDERS:D:96A:UN'",
            f"BGM+220+{po_number}+9'",
            f"DTM+137:{date_full}:102'",
            f"NAD+BY+{buyer_id}::92'",
            f"NAD+SU+{supplier_id}::92'",
            "LIN+1++TURBINE-VALVE:VP'",
            "QTY+21:25:EA'",
            "UNS+S'",
            f"MOA+86:{total_amount:.2f}:{currency}:4'",
            "CNT+2:1'",
        ]
        unt_count = len(segments) - 2 + 1
        segments.append(f"UNT+{unt_count}+1'")
        segments.append("UNZ+1+00000002'")
        return "\n".join(segments)


class EDIMutator:
    """Injects protocol fuzzing anomalies into ANSI X12 and UN/EDIFACT streams."""

    @classmethod
    def apply_mutations(
        cls,
        raw_edi: str,
        anomalies: List[ProtocolFuzzAnomaly],
    ) -> str:
        mutated = raw_edi
        for anomaly in anomalies:
            if anomaly == ProtocolFuzzAnomaly.DELIMITER_CORRUPTION:
                # Corrupt segment terminator or element separator
                lines = mutated.splitlines()
                if len(lines) > 3:
                    target_idx = random.randint(2, len(lines) - 2)
                    lines[target_idx] = lines[target_idx].replace("~", "^").replace("*", ":")
                    mutated = "\n".join(lines)

            elif anomaly == ProtocolFuzzAnomaly.ENVELOPE_TRUNCATION:
                # Strip closing control trailers (IEA, UNZ, GE, UNT)
                lines = [
                    l for l in mutated.splitlines()
                    if not (l.startswith("IEA") or l.startswith("UNZ") or l.startswith("GE*") or l.startswith("UNT"))
                ]
                mutated = "\n".join(lines)

            elif anomaly == ProtocolFuzzAnomaly.SEGMENT_COUNT_DESYNC:
                # Alter segment counts in SE or UNT
                lines = []
                for line in mutated.splitlines():
                    if line.startswith("SE*"):
                        parts = line.split("*")
                        if len(parts) >= 3:
                            bogus_count = int(parts[1]) + 99
                            lines.append(f"SE*{bogus_count}*{parts[2]}")
                            continue
                    elif line.startswith("UNT+"):
                        parts = line.split("+")
                        if len(parts) >= 3:
                            bogus_count = int(parts[1]) + 99
                            lines.append(f"UNT+{bogus_count}+{parts[2]}")
                            continue
                    lines.append(line)
                mutated = "\n".join(lines)

            elif anomaly == ProtocolFuzzAnomaly.BUFFER_OVERFLOW:
                # Inject 4KB overflow string into a data element
                lines = mutated.splitlines()
                if len(lines) > 2:
                    overflow_str = "A" * 4096
                    lines[2] = lines[2] + f"*OVERFLOW*{overflow_str}~"
                    mutated = "\n".join(lines)

            elif anomaly == ProtocolFuzzAnomaly.NULL_BYTE_INJECTION:
                # Inject null bytes into the payload
                pos = len(mutated) // 2
                mutated = mutated[:pos] + "\x00\x00\x00" + mutated[pos:]

        return mutated


class EDIEngine:
    """High-level engine for generating valid or fuzzed EDI payloads."""

    @classmethod
    def generate_edi_payload(
        cls,
        protocol: LegacyProtocolType,
        document_id: str,
        date_str: str,
        sender_id: str,
        receiver_id: str,
        amount: Decimal,
        anomalies: Optional[List[ProtocolFuzzAnomaly]] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
    ) -> LegacySerializationResult:
        if protocol == LegacyProtocolType.ANSI_X12_810:
            raw = EDISerializer.serialize_x12_810_invoice(
                invoice_number=document_id,
                invoice_date=date_str,
                vendor_id=sender_id,
                customer_id=receiver_id,
                total_amount=amount,
                line_items=line_items,
            )
        elif protocol == LegacyProtocolType.ANSI_X12_850:
            raw = EDISerializer.serialize_x12_850_po(
                po_number=document_id,
                po_date=date_str,
                vendor_id=receiver_id,
                buyer_id=sender_id,
                total_amount=amount,
                line_items=line_items,
            )
        elif protocol == LegacyProtocolType.ANSI_X12_856:
            raw = EDISerializer.serialize_x12_856_asn(
                shipment_id=document_id,
                ship_date=date_str,
                vendor_id=sender_id,
                receiver_id=receiver_id,
            )
        elif protocol == LegacyProtocolType.EDIFACT_INVOIC:
            raw = EDISerializer.serialize_edifact_invoic(
                invoice_number=document_id,
                invoice_date=date_str,
                supplier_id=sender_id,
                buyer_id=receiver_id,
                total_amount=amount,
                line_items=line_items,
            )
        elif protocol == LegacyProtocolType.EDIFACT_ORDERS:
            raw = EDISerializer.serialize_edifact_orders(
                po_number=document_id,
                po_date=date_str,
                supplier_id=receiver_id,
                buyer_id=sender_id,
                total_amount=amount,
            )
        else:
            raise ValueError(f"Unsupported EDI protocol type: {protocol}")

        applied = anomalies or []
        if applied:
            raw = EDIMutator.apply_mutations(raw, applied)

        return LegacySerializationResult(
            protocol_type=protocol,
            raw_payload=raw,
            is_binary=False,
            record_count=len(raw.splitlines()),
            byte_size=len(raw.encode("utf-8")),
            applied_anomalies=applied,
            metadata={"document_id": document_id, "amount": str(amount)},
        )
