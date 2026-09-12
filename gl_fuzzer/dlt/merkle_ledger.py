"""Triple-Entry Cryptographic Accounting & SHA-256 Binary Merkle Tree Ledger."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from gl_fuzzer.models.journal import JournalEntry


class MerkleIntegrityError(Exception):
    """Raised when cryptographic Merkle root or receipt proof verification fails."""
    pass


class MerkleProofStep(BaseModel):
    sibling_hash: str
    is_left: bool  # True if sibling is on the left, False if on the right


class TripleEntryReceipt(BaseModel):
    """Cryptographic electronic receipt proving inclusion in the immutable ledger."""
    entry_id: str
    document_number: str
    entry_leaf_hash: str
    root_hash: str
    proof_steps: List[MerkleProofStep] = Field(default_factory=list)
    timestamp_utc: str
    signature: str = Field(default="")


class MerkleLedger:
    """Enterprise SHA-256 Binary Merkle Tree maintaining cryptographic integrity proofs."""

    def __init__(self, entries: Optional[List[JournalEntry]] = None):
        self.entries: List[JournalEntry] = entries or []
        self.leaves: List[bytes] = []
        self.tree_levels: List[List[bytes]] = []
        self.root_hash: str = ""

        if self.entries:
            self._build_tree()

    @staticmethod
    def hash_leaf(entry: JournalEntry) -> bytes:
        """Computes deterministic 32-byte SHA-256 leaf digest for a journal entry."""
        dr = f"{entry.total_debits:.2f}"
        cr = f"{entry.total_credits:.2f}"
        raw = f"{entry.entry_id}|{entry.document_number}|{entry.company_code}|{entry.posting_date}|{dr}|{cr}|{entry.fiscal_year}"
        return hashlib.sha256(raw.encode("utf-8")).digest()

    @staticmethod
    def hash_pair(left: bytes, right: bytes) -> bytes:
        """Computes internal parent node hash = SHA256(left || right)."""
        return hashlib.sha256(left + right).digest()

    def _build_tree(self) -> None:
        """Constructs binary Merkle tree with leaves padded to next power of 2."""
        if not self.entries:
            self.root_hash = hashlib.sha256(b"EMPTY_LEDGER").hexdigest()
            self.tree_levels = []
            return

        raw_leaves = [self.hash_leaf(e) for e in self.entries]

        # Pad to next power of 2
        n = len(raw_leaves)
        power_of_two = 1
        while power_of_two < n:
            power_of_two *= 2

        padded_leaves = list(raw_leaves)
        while len(padded_leaves) < power_of_two:
            # Duplicate the last leaf (Bitcoin / RFC 6962 convention)
            padded_leaves.append(padded_leaves[-1])

        self.leaves = padded_leaves
        self.tree_levels = [self.leaves]

        current_level = self.leaves
        while len(current_level) > 1:
            next_level: List[bytes] = []
            for i in range(0, len(current_level), 2):
                parent = self.hash_pair(current_level[i], current_level[i + 1])
                next_level.append(parent)
            self.tree_levels.append(next_level)
            current_level = next_level

        self.root_hash = self.tree_levels[-1][0].hex()

    def get_inclusion_proof(self, entry_index: int) -> List[MerkleProofStep]:
        """Generates O(log N) audit path proof steps for a given entry index."""
        if entry_index < 0 or entry_index >= len(self.entries):
            raise IndexError("Entry index out of range")

        proof: List[MerkleProofStep] = []
        idx = entry_index

        for level in self.tree_levels[:-1]:
            # Sibling index
            if idx % 2 == 0:
                sibling_idx = idx + 1
                is_left = False
            else:
                sibling_idx = idx - 1
                is_left = True

            sibling_hash = level[sibling_idx].hex()
            proof.append(MerkleProofStep(sibling_hash=sibling_hash, is_left=is_left))
            idx //= 2

        return proof

    @classmethod
    def verify_proof(cls, leaf_hash_hex: str, proof: List[MerkleProofStep], expected_root_hex: str) -> bool:
        """Verifies inclusion proof by recalculating path from leaf to root."""
        current = bytes.fromhex(leaf_hash_hex)
        for step in proof:
            sibling = bytes.fromhex(step.sibling_hash)
            if step.is_left:
                current = cls.hash_pair(sibling, current)
            else:
                current = cls.hash_pair(current, sibling)

        return current.hex().lower() == expected_root_hex.lower()

    def generate_triple_entry_receipt(self, entry_index: int) -> TripleEntryReceipt:
        """Generates a cryptographic Triple-Entry receipt for counterparty reconciliation."""
        entry = self.entries[entry_index]
        leaf_hex = self.hash_leaf(entry).hex()
        proof = self.get_inclusion_proof(entry_index)
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Digital signature surrogate over (leaf + root)
        sig_data = f"{leaf_hex}:{self.root_hash}:{now_utc}"
        sig_hash = hashlib.sha256(sig_data.encode("utf-8")).hexdigest()

        return TripleEntryReceipt(
            entry_id=entry.entry_id,
            document_number=entry.document_number,
            entry_leaf_hash=leaf_hex,
            root_hash=self.root_hash,
            proof_steps=proof,
            timestamp_utc=now_utc,
            signature=f"SIG_{sig_hash[:32]}",
        )

    def verify_entire_ledger(self) -> bool:
        """Validates all entries against current root hash; raises MerkleIntegrityError if tampered."""
        for i, entry in enumerate(self.entries):
            leaf_hex = self.hash_leaf(entry).hex()
            proof = self.get_inclusion_proof(i)
            if not self.verify_proof(leaf_hex, proof, self.root_hash):
                raise MerkleIntegrityError(f"Tamper detected in entry {entry.entry_id} at index {i}!")
        return True
