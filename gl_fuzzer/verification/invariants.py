"""Mathematical Invariant Verifiers ensuring zero-sum double-entry accounting integrity."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field

from gl_fuzzer.models.journal import Batch, DebitCredit, JournalEntry


class InvariantViolation(BaseModel):
    """Details of a broken accounting invariant."""
    entry_id: str
    violation_type: str
    expected: str
    actual: str
    message: str


class InvariantReport(BaseModel):
    """Report summarizing invariant verification results."""
    total_entries_checked: int = 0
    total_lines_checked: int = 0
    total_debits: Decimal = Decimal("0.00")
    total_credits: Decimal = Decimal("0.00")
    is_globally_balanced: bool = True
    unbalanced_entries_count: int = 0
    violations: List[InvariantViolation] = Field(default_factory=list)


class InvariantVerifier:
    """Verifies double-entry mathematical invariants across journal entries and batches."""

    @classmethod
    def verify_entry(cls, entry: JournalEntry) -> List[InvariantViolation]:
        """Verifies a single journal entry."""
        violations: List[InvariantViolation] = []

        # Check 1: Minimum leg count (must have at least one debit and at least one credit)
        debit_lines = [l for l in entry.lines if l.debit_credit == DebitCredit.DEBIT]
        credit_lines = [l for l in entry.lines if l.debit_credit == DebitCredit.CREDIT]

        if not debit_lines or not credit_lines:
            violations.append(
                InvariantViolation(
                    entry_id=entry.entry_id,
                    violation_type="MISSING_LEGS",
                    expected=">=1 Debit and >=1 Credit",
                    actual=f"{len(debit_lines)} Debits, {len(credit_lines)} Credits",
                    message="Journal entry lacks reciprocal double-entry legs",
                )
            )

        # Check 2: All amounts strictly positive
        for line in entry.lines:
            if line.amount <= Decimal("0.00"):
                violations.append(
                    InvariantViolation(
                        entry_id=entry.entry_id,
                        violation_type="NON_POSITIVE_AMOUNT",
                        expected="Amount > 0.00",
                        actual=str(line.amount),
                        message=f"Line item {line.line_id} has non-positive amount {line.amount}",
                    )
                )

        # Check 3: Strict mathematical balance: Σ(Debits) == Σ(Credits)
        if not entry.is_balanced:
            violations.append(
                InvariantViolation(
                    entry_id=entry.entry_id,
                    violation_type="UNBALANCED_ENTRY",
                    expected=f"Debits == Credits (Delta: 0.00)",
                    actual=f"Debits: {entry.total_debits}, Credits: {entry.total_credits} (Delta: {entry.balance_delta})",
                    message="Debit and credit legs do not sum to zero",
                )
            )

        return violations

    @classmethod
    def verify_batch(cls, batch: Batch) -> InvariantReport:
        """Verifies all entries in a batch as well as global batch-level balance."""
        report = InvariantReport(
            total_entries_checked=len(batch.entries),
            total_lines_checked=batch.total_line_count,
            total_debits=batch.total_debits,
            total_credits=batch.total_credits,
            is_globally_balanced=batch.is_balanced,
        )

        unbalanced_count = 0
        for entry in batch.entries:
            entry_violations = cls.verify_entry(entry)
            if entry_violations:
                report.violations.extend(entry_violations)
                unbalanced_count += 1

        report.unbalanced_entries_count = unbalanced_count
        if unbalanced_count > 0 or not batch.is_balanced:
            report.is_globally_balanced = False

        return report

    @classmethod
    def verify_entries(cls, entries: List[JournalEntry]) -> InvariantReport:
        """Verifies an arbitrary collection of journal entries."""
        tot_deb = sum((e.total_debits for e in entries), Decimal("0.00"))
        tot_crd = sum((e.total_credits for e in entries), Decimal("0.00"))
        tot_lines = sum(len(e.lines) for e in entries)

        report = InvariantReport(
            total_entries_checked=len(entries),
            total_lines_checked=tot_lines,
            total_debits=tot_deb,
            total_credits=tot_crd,
            is_globally_balanced=(tot_deb == tot_crd),
        )

        unbalanced_count = 0
        for entry in entries:
            entry_violations = cls.verify_entry(entry)
            if entry_violations:
                report.violations.extend(entry_violations)
                unbalanced_count += 1

        report.unbalanced_entries_count = unbalanced_count
        if unbalanced_count > 0 or (tot_deb != tot_crd):
            report.is_globally_balanced = False

        return report
