"""Synthetic Corporate Email Thread Generator for audit and forensic contextual analysis."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import email.message

from gl_fuzzer.documents.models import DocumentArtifactType, SyntheticDocumentResult


class EmailThreadGenerator:
    """Generates synthetic corporate email chains capturing internal approval and override contexts."""

    @classmethod
    def generate_cfo_override_thread(
        cls,
        output_file: Path,
        vendor_name: str = "Apex Logistics Corporation",
        amount: str = "$9,950.00",
        invoice_number: str = "INV-2026-9081",
    ) -> SyntheticDocumentResult:
        """Generates an urgent CFO payment bypass email chain."""
        msg = email.message.EmailMessage()
        msg["From"] = "Arthur Pendelton <cfo@enterprise-corp.com>"
        msg["To"] = "Elena Rostova <ap.director@enterprise-corp.com>"
        msg["Cc"] = "treasury-operations@enterprise-corp.com"
        msg["Subject"] = f"URGENT: Executive Exception Approval - Expedited Settlement for {vendor_name}"
        msg["Date"] = "Tue, 14 Apr 2026 18:22:15 -0400"
        msg["Message-ID"] = "<exec.override.9081@enterprise-corp.com>"

        body = (
            f"Elena,\n\n"
            f"Due to supply chain sensitivities and contractual deadlines, please bypass the standard "
            f"dual-signoff requirement for invoice {invoice_number} ({amount}).\n\n"
            f"I have personally reviewed the deliverables with the vendor's VP. Please ensure this is released "
            f"in today's afternoon payment run directly without waiting for the secondary Controller signature.\n\n"
            f"I will log the formal post-clearance ratification in next week's executive committee meeting.\n\n"
            f"Regards,\n"
            f"Arthur Pendelton\n"
            f"Chief Financial Officer\n"
            f"Enterprise Holdings Corp.\n"
        )
        msg.set_content(body)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        size = output_file.stat().st_size
        return SyntheticDocumentResult(
            document_type=DocumentArtifactType.EMAIL_APPROVAL_THREAD,
            file_path=output_file,
            file_size_bytes=size,
            email_subject=msg["Subject"],
            is_mismatched=True,
            mismatch_summary="Executive DOA override email pressuring AP clerk to bypass secondary approval controls.",
        )

    @classmethod
    def generate_bank_update_notice(
        cls,
        output_file: Path,
        vendor_name: str = "Nordic Raw Materials AS",
        new_iban: str = "US89021000022998877665",
    ) -> SyntheticDocumentResult:
        """Generates a suspicious vendor bank update notification email."""
        msg = email.message.EmailMessage()
        clean_domain = re.sub(r"[^a-z0-9]", "", vendor_name.lower()) or "vendor"
        msg["From"] = f"Billing Support <accounts@{clean_domain}.com>"
        msg["To"] = "Accounts Payable <ap@enterprise-corp.com>"
        msg["Subject"] = f"URGENT: Updated Remittance Banking Details for {vendor_name}"
        msg["Date"] = "Wed, 16 Apr 2026 08:45:00 -0400"

        body = (
            f"Dear Accounts Payable Team,\n\n"
            f"Please be advised that effective immediately, all upcoming wire disbursements for {vendor_name} "
            f"should be remitted to our newly consolidated treasury account:\n\n"
            f"  Bank: Global Commercial Banking NA\n"
            f"  Account / IBAN: {new_iban}\n"
            f"  Routing / ABA: 021000099\n\n"
            f"Please update your master records and confirm receipt prior to releasing this week's scheduled payment.\n\n"
            f"Sincerely,\n"
            f"Treasury Department\n"
            f"{vendor_name}\n"
        )
        msg.set_content(body)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        size = output_file.stat().st_size
        return SyntheticDocumentResult(
            document_type=DocumentArtifactType.EMAIL_APPROVAL_THREAD,
            file_path=output_file,
            file_size_bytes=size,
            email_subject=msg["Subject"],
            is_mismatched=True,
            mismatch_summary="Suspicious unauthenticated vendor email requesting banking routing change before payment run.",
        )

    @classmethod
    def generate_from_social_engineering_thread(
        cls,
        output_file: Path,
        thread: Any,
    ) -> SyntheticDocumentResult:
        """Generates an RFC-2822 .eml file containing an autonomous social engineering dialogue chain."""
        msg = email.message.EmailMessage()
        subject = getattr(thread, "subject", "Executive Inquiries & Approvals")
        turns = getattr(thread, "turns", [])
        thread_id = getattr(thread, "thread_id", "THREAD-001")

        if not turns:
            msg["Subject"] = subject
            msg["From"] = "System Notice <system@enterprise-corp.com>"
            msg["To"] = "AP Clerk <ap@enterprise-corp.com>"
            msg.set_content("No dialogue turns recorded in social engineering thread.")
        else:
            last_turn = turns[-1]
            first_turn = turns[0]

            msg["Subject"] = f"Re: {subject}" if len(turns) > 1 and not subject.startswith("Re:") else subject
            msg["From"] = f"{last_turn.speaker_name} <{cls._format_email(last_turn.speaker_name)}>"
            msg["To"] = f"{first_turn.speaker_name} <{cls._format_email(first_turn.speaker_name)}>"
            msg["Date"] = last_turn.timestamp
            msg["Message-ID"] = f"<{thread_id}.turn{len(turns)}@enterprise-corp.com>"

            if len(turns) > 1:
                prev_id = f"<{thread_id}.turn{len(turns) - 1}@enterprise-corp.com>"
                msg["In-Reply-To"] = prev_id
                all_refs = [f"<{thread_id}.turn{i}@enterprise-corp.com>" for i in range(1, len(turns))]
                msg["References"] = " ".join(all_refs)

            campaign_id = getattr(thread, "campaign_id", None)
            if campaign_id:
                msg["X-Campaign-ID"] = str(campaign_id)
            if last_turn.persuasion_tactic:
                msg["X-Persuasion-Tactic"] = str(last_turn.persuasion_tactic.value if hasattr(last_turn.persuasion_tactic, "value") else last_turn.persuasion_tactic)

            # Build full nested conversational thread body
            body_parts = [last_turn.message_body, "\n"]
            for t in reversed(turns[:-1]):
                body_parts.append(
                    f"\n-----Original Message-----\n"
                    f"From: {t.speaker_name}\n"
                    f"Sent: {t.timestamp}\n"
                    f"Role: {t.speaker_role}\n\n"
                    f"{t.message_body}\n"
                )
            msg.set_content("\n".join(body_parts))

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(msg.as_string())

        size = output_file.stat().st_size
        return SyntheticDocumentResult(
            document_type=DocumentArtifactType.EMAIL_APPROVAL_THREAD,
            file_path=output_file,
            file_size_bytes=size,
            email_subject=msg["Subject"],
            is_mismatched=True,
            mismatch_summary=getattr(thread, "audit_notes", "Autonomous generative LLM social engineering thread."),
        )

    @staticmethod
    def _format_email(speaker_name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", speaker_name).strip()
        first_token = clean.split()[0].lower() if clean else "user"
        return f"{first_token}@enterprise-corp.com"

