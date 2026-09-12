"""IBM Mainframe, COBOL Copybook, EBCDIC, NACHA ACH, BAI2, and SWIFT MT940 Engine."""

from __future__ import annotations

from decimal import Decimal
import math
import random
from typing import Any, Dict, List, Optional, Tuple, Union

from gl_fuzzer.legacy_protocols.models import (
    LegacyProtocolType,
    LegacySerializationResult,
    ProtocolFuzzAnomaly,
)


def pack_comp3(val: int, num_bytes: int, signed: bool = True) -> bytes:
    """Packs an integer into COBOL COMP-3 (packed decimal) format.

    Each byte stores 2 BCD digits; the lowest nibble stores the sign (0xC = positive, 0xD = negative, 0xF = unsigned).
    """
    is_neg = val < 0
    abs_val = abs(val)
    sign_nibble = 0xD if is_neg else (0xC if signed else 0xF)

    # Convert number to digits
    s_digits = str(abs_val)
    # Total available digit slots = (num_bytes * 2) - 1
    max_digits = (num_bytes * 2) - 1
    s_digits = s_digits.zfill(max_digits)
    if len(s_digits) > max_digits:
        raise OverflowError(
            f"pack_comp3: value {val} requires {len(str(abs_val))} digits "
            f"but num_bytes={num_bytes} only holds {max_digits}. "
            "Increase num_bytes to avoid financial data corruption."
        )

    # Append sign nibble
    nibbles = [int(d) for d in s_digits] + [sign_nibble]
    out = bytearray(num_bytes)
    for i in range(num_bytes):
        high = nibbles[i * 2]
        low = nibbles[i * 2 + 1]
        out[i] = (high << 4) | low
    return bytes(out)


def unpack_comp3(data: bytes, signed: bool = True) -> int:
    """Unpacks COBOL COMP-3 bytes into an integer."""
    nibbles: List[int] = []
    for b in data:
        nibbles.append((b >> 4) & 0x0F)
        nibbles.append(b & 0x0F)

    sign_nibble = nibbles[-1]
    is_neg = (sign_nibble == 0xD) if signed else False
    digit_str = "".join(str(n) for n in nibbles[:-1])
    val = int(digit_str or "0")
    return -val if is_neg else val


class MainframeSerializer:
    """Serializes financial ledgers and transactions into legacy IBM mainframe and banking formats."""

    @staticmethod
    def serialize_cobol_80col(
        records: List[Dict[str, Any]],
    ) -> str:
        """Serializes records to IBM 80-column fixed-width punched-card layout.

        Layout:
        Col 01-06: Sequence Number (PIC 9(6))
        Col 07-07: Indicator / Continuation (' ')
        Col 08-17: Voucher / Doc ID (PIC X(10))
        Col 18-25: Date YYYYMMDD (PIC 9(8))
        Col 26-35: Account Number (PIC 9(10))
        Col 36-37: Debit / Credit Code ('DR' or 'CR')
        Col 38-49: Amount in Cents (PIC 9(10)V99)
        Col 50-70: Description / Cost Center (PIC X(21))
        Col 71-80: Identification Tag (PIC X(10))
        Total = 80 characters per card.
        """
        lines = []
        for i, rec in enumerate(records, start=1):
            seq = f"{i:06d}"
            indicator = " "
            doc_id = str(rec.get("doc_id", "DOC001")).ljust(10)[:10]
            date_str = str(rec.get("date", "20260414")).replace("-", "").ljust(8)[:8]
            acct = str(rec.get("account", "1010000000")).ljust(10)[:10]
            dr_cr = str(rec.get("dr_cr", "DR")).upper().ljust(2)[:2]
            amount_cents = int(abs(Decimal(str(rec.get("amount", "0.00")))) * 100)
            amount_str = f"{amount_cents:012d}"
            desc = str(rec.get("description", "GENERAL LEDGER ENTRY")).ljust(21)[:21]
            tag = str(rec.get("tag", "GL-SYS370")).ljust(10)[:10]

            line = f"{seq}{indicator}{doc_id}{date_str}{acct}{dr_cr}{amount_str}{desc}{tag}"
            if len(line) != 80:
                line = line.ljust(80)[:80]
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def serialize_cobol_132col(
        records: List[Dict[str, Any]],
    ) -> str:
        """Serializes records to IBM 132-column line printer ledger report format."""
        lines = []
        header = (
            f"SEQ   VOUCHER-ID DATE     ACCOUNT-NO DESCRIPTION                    "
            f"DC AMOUNT(CENTS)   CURR ENTITY  SUB-LEDGER      AUDIT-HASH  "
        ).ljust(132)[:132]
        lines.append(header)
        lines.append("-" * 132)

        for i, rec in enumerate(records, start=1):
            seq = f"{i:05d} "
            vch = str(rec.get("doc_id", "DOC001")).ljust(11)[:11]
            dt = str(rec.get("date", "20260414")).replace("-", "").ljust(9)[:9]
            acct = str(rec.get("account", "10100000")).ljust(11)[:11]
            desc = str(rec.get("description", "GENERAL JOURNAL ENTRY")).ljust(31)[:31]
            dr_cr = str(rec.get("dr_cr", "DR")).upper().ljust(3)[:3]
            amt = f"{int(abs(Decimal(str(rec.get('amount', '0.00')))) * 100):015d} "
            curr = str(rec.get("currency", "USD")).ljust(5)[:5]
            entity = str(rec.get("entity", "CORP01")).ljust(8)[:8]
            sub = str(rec.get("subledger", "AP-SUB01")).ljust(16)[:16]
            hsh = str(rec.get("hash", "A89F123C")).ljust(12)[:12]

            line = f"{seq}{vch}{dt}{acct}{desc}{dr_cr}{amt}{curr}{entity}{sub}{hsh}".ljust(132)[:132]
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def serialize_ebcdic_binary(
        records: List[Dict[str, Any]],
        code_page: str = "cp037",
    ) -> bytes:
        """Serializes records into binary IBM Mainframe EBCDIC CP037 format with COMP-3 fields.

        Binary record layout (32 bytes per record):
        - Byte 00-03: Record Sequence (4 bytes, binary uint32)
        - Byte 04-11: Voucher ID in EBCDIC (8 bytes)
        - Byte 12-19: Account Number in EBCDIC (8 bytes)
        - Byte 20-21: DR/CR Flag in EBCDIC (2 bytes)
        - Byte 22-27: Amount in COMP-3 packed decimal (6 bytes = 11 digits + sign)
        - Byte 28-31: Record CRC/Hash in EBCDIC (4 bytes)
        Total = 32 bytes binary record.
        """
        raw_bytes = bytearray()
        for i, rec in enumerate(records, start=1):
            # 4 bytes uint32 big-endian
            raw_bytes.extend(i.to_bytes(4, byteorder="big"))
            # 8 bytes EBCDIC voucher
            vch_ebcdic = str(rec.get("doc_id", "DOC01")).ljust(8)[:8].encode(code_page)
            raw_bytes.extend(vch_ebcdic)
            # 8 bytes EBCDIC account
            acct_ebcdic = str(rec.get("account", "10100000")).ljust(8)[:8].encode(code_page)
            raw_bytes.extend(acct_ebcdic)
            # 2 bytes DR/CR
            drcr_ebcdic = str(rec.get("dr_cr", "DR")).upper().ljust(2)[:2].encode(code_page)
            raw_bytes.extend(drcr_ebcdic)
            # 6 bytes COMP-3 amount in cents
            amt_cents = int(abs(Decimal(str(rec.get("amount", "0.00")))) * 100)
            comp3_bytes = pack_comp3(amt_cents, num_bytes=6, signed=True)
            raw_bytes.extend(comp3_bytes)
            # 4 bytes tag
            tag_ebcdic = str(rec.get("tag", "EBCD")).ljust(4)[:4].encode(code_page)
            raw_bytes.extend(tag_ebcdic)

        return bytes(raw_bytes)

    @staticmethod
    def serialize_nacha_ach(
        entries: List[Dict[str, Any]],
        company_name: str = "ENTERPRISE CORP",
        company_id: str = "1234567890",
        originating_dfi: str = "02100002",
    ) -> str:
        """Serializes entries to strict NACHA ACH 94-character fixed-width file format."""
        file_lines: List[str] = []

        # Record 1: File Header Record (94 chars)
        rec1 = (
            "1"
            "01"
            f" {originating_dfi[:9].ljust(9)}"  # 10 chars immediate dest
            f" {company_id[:9].ljust(9)}"        # 10 chars immediate origin
            "260414"                              # 6 chars date
            "1430"                                # 4 chars time
            "A"                                   # 1 char modifier
            "094"                                 # 3 chars record size
            "10"                                  # 2 chars blocking factor
            "1"                                   # 1 char format code
            f"{'GLOBAL COMMERCE BANK'.ljust(23)[:23]}"
            f"{company_name.ljust(23)[:23]}"
            "00000001"                            # 8 chars reference
        )
        file_lines.append(rec1[:94].ljust(94))

        # Record 5: Batch Header Record (94 chars)
        rec5 = (
            "5"
            "200"                                 # Service class code (mixed DR/CR)
            f"{company_name.ljust(16)[:16]}"
            f"{'PAYROLL VENDOR PMT'.ljust(20)[:20]}"
            f"{company_id.ljust(10)[:10]}"
            "CCD"                                 # Standard entry class
            f"{'VENDOR PMT'.ljust(10)[:10]}"
            "260414"                              # Descriptive date
            "260415"                              # Effective date
            "   "                                 # Settlement date blank
            "1"                                   # Originator status
            f"{originating_dfi[:8].ljust(8)}"
            "0000001"                             # Batch number
        )
        file_lines.append(rec5[:94].ljust(94))

        total_debits_cents = 0
        total_credits_cents = 0
        entry_hash_sum = 0

        # Record 6: Entry Detail Records (94 chars each)
        for i, entry in enumerate(entries, start=1):
            routing = str(entry.get("routing", "021000021")).zfill(9)[:9]
            dfi_8 = routing[:8]
            check_digit = routing[8]
            entry_hash_sum += int(dfi_8)

            amt = Decimal(str(entry.get("amount", "0.00")))
            amt_cents = int(abs(amt) * 100)
            is_credit = entry.get("dr_cr", "CR").upper() == "CR"
            if is_credit:
                tx_code = "22"  # Credit
                total_credits_cents += amt_cents
            else:
                tx_code = "27"  # Debit
                total_debits_cents += amt_cents

            acct_num = str(entry.get("account", "123456789")).ljust(17)[:17]
            amt_str = f"{amt_cents:010d}"
            vend_id = str(entry.get("vendor_id", f"VEND{i:04d}")).ljust(15)[:15]
            vend_name = str(entry.get("name", "RECIPIENT NAME")).ljust(22)[:22]
            trace_num = f"{dfi_8}{i:07d}"

            rec6 = (
                "6"
                f"{tx_code}"
                f"{dfi_8}"
                f"{check_digit}"
                f"{acct_num}"
                f"{amt_str}"
                f"{vend_id}"
                f"{vend_name}"
                "  "                              # Discretionary
                "0"                               # Addenda flag
                f"{trace_num}"
            )
            file_lines.append(rec6[:94].ljust(94))

        # Record 8: Batch Control Record (94 chars)
        entry_hash_10 = f"{(entry_hash_sum % (10**10)):010d}"
        rec8 = (
            "8"
            "200"
            f"{len(entries):06d}"
            f"{entry_hash_10}"
            f"{total_debits_cents:012d}"
            f"{total_credits_cents:012d}"
            f"{company_id.ljust(10)[:10]}"
            f"{' ' * 19}"
            f"{' ' * 6}"
            f"{originating_dfi[:8].ljust(8)}"
            "0000001"
        )
        file_lines.append(rec8[:94].ljust(94))

        # Record 9: File Control Record (94 chars)
        total_records = len(file_lines) + 1  # will include record 9
        block_count = math.ceil(total_records / 10)
        rec9 = (
            "9"
            "000001"                             # Batch count
            f"{block_count:06d}"                 # Block count
            f"{len(entries):08d}"                # Entry count
            f"{entry_hash_10}"
            f"{total_debits_cents:012d}"
            f"{total_credits_cents:012d}"
            f"{' ' * 39}"
        )
        file_lines.append(rec9[:94].ljust(94))

        # Block-10 padding with all '9' lines
        while len(file_lines) % 10 != 0:
            file_lines.append("9" * 94)

        return "\n".join(file_lines)

    @staticmethod
    def serialize_bai2(
        entries: List[Dict[str, Any]],
        account_number: str = "987654321",
        currency: str = "USD",
    ) -> str:
        """Serializes entries to BAI2 Cash Management Statement format."""
        lines: List[str] = [
            f"01,ENTERPRISE_BANK,ENTERPRISE_CORP,260414,1200,1,80,2/",
            f"02,CORP_TREASURY,260414,1,1200,{currency}/",
            f"03,{account_number},{currency},010,50000000,,,/",
        ]

        total_amount_cents = 0
        for i, entry in enumerate(entries, start=1):
            amt = Decimal(str(entry.get("amount", "100.00")))
            amt_cents = int(abs(amt) * 100)
            total_amount_cents += amt_cents
            is_credit = entry.get("dr_cr", "CR").upper() == "CR"
            type_code = "195" if is_credit else "495"  # 195 Incoming Wire, 495 Outgoing Wire
            doc_id = str(entry.get("doc_id", f"REF{i:04d}"))
            lines.append(f"16,{type_code},{amt_cents},Z,{doc_id},{doc_id},SETTLEMENT ENTRY/")

        lines.append(f"49,{total_amount_cents},{len(entries)}/")
        lines.append(f"98,{total_amount_cents},1,{len(entries) + 2}/")
        lines.append(f"99,{total_amount_cents},1,{len(lines) + 1}/")

        return "\n".join(lines)

    @staticmethod
    def serialize_swift_mt940(
        entries: List[Dict[str, Any]],
        account_number: str = "US89021000022998877665",
        currency: str = "USD",
        opening_balance: Decimal = Decimal("100000.00"),
    ) -> str:
        """Serializes transactions into standard SWIFT MT940 statement message."""
        lines: List[str] = [
            ":20:STMT20260414001",
            f":25:{account_number}",
            ":28C:00001/001",
            f":60F:C260414{currency}{str(opening_balance).replace('.', ',')}",
        ]

        running_balance = opening_balance
        for i, entry in enumerate(entries, start=1):
            amt = Decimal(str(entry.get("amount", "100.00")))
            is_credit = entry.get("dr_cr", "CR").upper() == "CR"
            dr_cr_mark = "CR" if is_credit else "DR"
            if is_credit:
                running_balance += amt
            else:
                running_balance -= amt

            amt_comma = f"{amt:.2f}".replace(".", ",")
            doc_id = str(entry.get("doc_id", f"TX{i:04d}"))
            desc = str(entry.get("description", "COMMERCIAL SETTLEMENT"))

            lines.append(f":61:2604140414{dr_cr_mark}{amt_comma}NTRFNONREF//{doc_id}")
            lines.append(f":86:/BENM/{desc}/REMARK/EXPEDITED SETTLEMENT")

        close_mark = "C" if running_balance >= 0 else "D"
        lines.append(f":62F:{close_mark}260414{currency}{str(abs(running_balance)).replace('.', ',')}")
        lines.append("-")

        return "\n".join(lines)


class MainframeMutator:
    """Injects protocol-level fuzzing corruptions into IBM mainframe and banking payloads."""

    @classmethod
    def apply_string_mutations(
        cls,
        raw_text: str,
        anomalies: List[ProtocolFuzzAnomaly],
    ) -> str:
        mutated = raw_text
        for anomaly in anomalies:
            if anomaly == ProtocolFuzzAnomaly.FIXED_WIDTH_OVERFLOW:
                # Add 5 characters to some lines, breaking 94 or 80 fixed character limit
                lines = mutated.splitlines()
                if len(lines) > 2:
                    lines[1] = lines[1] + "CORRUPT_OVERFLOW"
                    mutated = "\n".join(lines)

            elif anomaly == ProtocolFuzzAnomaly.HASH_TOTAL_DESYNC:
                # Desynchronize entry hash in NACHA ACH Record 8 or 9
                lines = []
                for l in mutated.splitlines():
                    if l.startswith("8") and len(l) == 94:
                        # Tamper with entry hash at pos 11-20
                        lines.append(l[:10] + "9999999999" + l[20:])
                    elif l.startswith("9") and len(l) == 94:
                        lines.append(l[:21] + "9999999999" + l[31:])
                    else:
                        lines.append(l)
                mutated = "\n".join(lines)

            elif anomaly == ProtocolFuzzAnomaly.ENVELOPE_TRUNCATION:
                # Strip block-padding 9s and trailer record
                lines = [l for l in mutated.splitlines() if not l.startswith("9") and not l.startswith("99")]
                mutated = "\n".join(lines)

            elif anomaly == ProtocolFuzzAnomaly.NULL_BYTE_INJECTION:
                pos = len(mutated) // 2
                mutated = mutated[:pos] + "\x00\x00\x00" + mutated[pos:]

            elif anomaly == ProtocolFuzzAnomaly.BUFFER_OVERFLOW:
                lines = mutated.splitlines()
                if len(lines) > 1:
                    lines[1] = lines[1] + ("X" * 1024)
                    mutated = "\n".join(lines)

        return mutated

    @classmethod
    def apply_binary_mutations(
        cls,
        raw_bytes: bytes,
        anomalies: List[ProtocolFuzzAnomaly],
    ) -> bytes:
        data = bytearray(raw_bytes)
        for anomaly in anomalies:
            if anomaly == ProtocolFuzzAnomaly.EBCDIC_SIGN_CORRUPTION:
                # Corrupt COMP-3 sign nibble at byte 27 of record (offset 27)
                if len(data) >= 28:
                    # Invert sign nibble to 0x0 (invalid COMP-3 sign)
                    data[27] = data[27] & 0xF0
            elif anomaly == ProtocolFuzzAnomaly.NULL_BYTE_INJECTION:
                # Inject null bytes into the binary stream
                data.extend(b"\x00\x00\x00\x00\x00\x00")
            elif anomaly == ProtocolFuzzAnomaly.BUFFER_OVERFLOW:
                # Append 4096 arbitrary binary bytes
                data.extend(b"\xFF" * 4096)
        return bytes(data)


class MainframeEngine:
    """High-level engine for generating valid or fuzzed Mainframe and Banking payloads."""

    @classmethod
    def generate_payload(
        cls,
        protocol: LegacyProtocolType,
        records: List[Dict[str, Any]],
        anomalies: Optional[List[ProtocolFuzzAnomaly]] = None,
        **kwargs: Any,
    ) -> LegacySerializationResult:
        applied = anomalies or []

        if protocol == LegacyProtocolType.COBOL_COPYBOOK_80:
            text = MainframeSerializer.serialize_cobol_80col(records)
            if applied:
                text = MainframeMutator.apply_string_mutations(text, applied)
            return LegacySerializationResult(
                protocol_type=protocol,
                raw_payload=text,
                is_binary=False,
                record_count=len(text.splitlines()),
                byte_size=len(text.encode("utf-8")),
                applied_anomalies=applied,
                encoding="utf-8",
                metadata={"record_layout": "80_COLUMN_PUNCHED_CARD"},
            )

        elif protocol == LegacyProtocolType.COBOL_COPYBOOK_132:
            text = MainframeSerializer.serialize_cobol_132col(records)
            if applied:
                text = MainframeMutator.apply_string_mutations(text, applied)
            return LegacySerializationResult(
                protocol_type=protocol,
                raw_payload=text,
                is_binary=False,
                record_count=len(text.splitlines()),
                byte_size=len(text.encode("utf-8")),
                applied_anomalies=applied,
                encoding="utf-8",
                metadata={"record_layout": "132_COLUMN_LINE_REPORT"},
            )

        elif protocol == LegacyProtocolType.EBCDIC_BINARY:
            raw_bin = MainframeSerializer.serialize_ebcdic_binary(records, code_page=kwargs.get("code_page", "cp037"))
            if applied:
                raw_bin = MainframeMutator.apply_binary_mutations(raw_bin, applied)
            return LegacySerializationResult(
                protocol_type=protocol,
                raw_payload=raw_bin,
                is_binary=True,
                record_count=len(records),
                byte_size=len(raw_bin),
                applied_anomalies=applied,
                encoding="cp037",
                metadata={"record_layout": "32_BYTE_BINARY_COMP3"},
            )

        elif protocol == LegacyProtocolType.NACHA_ACH:
            text = MainframeSerializer.serialize_nacha_ach(
                records,
                company_name=kwargs.get("company_name", "ENTERPRISE CORP"),
                company_id=kwargs.get("company_id", "1234567890"),
                originating_dfi=kwargs.get("originating_dfi", "02100002"),
            )
            if applied:
                text = MainframeMutator.apply_string_mutations(text, applied)
            return LegacySerializationResult(
                protocol_type=protocol,
                raw_payload=text,
                is_binary=False,
                record_count=len(text.splitlines()),
                byte_size=len(text.encode("utf-8")),
                applied_anomalies=applied,
                encoding="ascii",
                metadata={"standard": "NACHA_ACH_94_COL"},
            )

        elif protocol == LegacyProtocolType.BAI2:
            text = MainframeSerializer.serialize_bai2(
                records,
                account_number=kwargs.get("account_number", "987654321"),
                currency=kwargs.get("currency", "USD"),
            )
            if applied:
                text = MainframeMutator.apply_string_mutations(text, applied)
            return LegacySerializationResult(
                protocol_type=protocol,
                raw_payload=text,
                is_binary=False,
                record_count=len(text.splitlines()),
                byte_size=len(text.encode("utf-8")),
                applied_anomalies=applied,
                encoding="ascii",
                metadata={"standard": "BAI2_CASH_MGMT"},
            )

        elif protocol == LegacyProtocolType.SWIFT_MT940:
            text = MainframeSerializer.serialize_swift_mt940(
                records,
                account_number=kwargs.get("account_number", "US89021000022998877665"),
                currency=kwargs.get("currency", "USD"),
            )
            if applied:
                text = MainframeMutator.apply_string_mutations(text, applied)
            return LegacySerializationResult(
                protocol_type=protocol,
                raw_payload=text,
                is_binary=False,
                record_count=len(text.splitlines()),
                byte_size=len(text.encode("utf-8")),
                applied_anomalies=applied,
                encoding="ascii",
                metadata={"standard": "SWIFT_MT940"},
            )

        else:
            raise ValueError(f"Unsupported mainframe protocol type: {protocol}")
