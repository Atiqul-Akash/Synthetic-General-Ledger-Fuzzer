"""Hyperledger Fabric Consensus & Chaincode ReadWriteSet (RWSet) Fuzzer."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class FabricConsensusError(Exception):
    """Base exception for Fabric consensus and execution failures."""
    pass


class RWSetVersionConflict(FabricConsensusError):
    """MVCC conflict when read key version differs from world state at commit time."""
    pass


class EndorsementPolicyMismatch(FabricConsensusError):
    """Transaction submitted without satisfying required endorsement policy (e.g. 2-of-2)."""
    pass


class OutdatedStateCommitment(FabricConsensusError):
    """Replay or stale block commitment failure."""
    pass


class VersionedValue(BaseModel):
    value: Decimal
    block_num: int
    tx_num: int

    @property
    def version_tuple(self) -> Tuple[int, int]:
        return (self.block_num, self.tx_num)


class ReadWriteSet(BaseModel):
    tx_id: str
    read_set: Dict[str, Tuple[int, int]] = Field(default_factory=dict)
    write_set: Dict[str, Decimal] = Field(default_factory=dict)
    endorsers: List[str] = Field(default_factory=list)
    timestamp: str = ""


class FabricLedgerSimulator:
    """Simulates Hyperledger Fabric channel ledger, MVCC validation, and chaincode transactions."""

    def __init__(self, channel_id: str = "financial-channel"):
        self.channel_id = channel_id
        self.world_state: Dict[str, VersionedValue] = {}
        self.current_block: int = 1
        self.current_tx_seq: int = 1
        self.required_endorsers: List[str] = ["Org1MSP.peer0", "Org2MSP.peer0"]

        # Initialize default account balances in world state
        self._init_world_state()

    def _init_world_state(self) -> None:
        init_accounts = {
            "acc_10100": Decimal("500000.00"),
            "acc_11000": Decimal("250000.00"),
            "acc_20000": Decimal("150000.00"),
            "acc_50000": Decimal("0.00"),
            "acc_61000": Decimal("0.00"),
        }
        for k, v in init_accounts.items():
            self.world_state[k] = VersionedValue(value=v, block_num=0, tx_num=0)

    def get_state(self, key: str) -> Tuple[Decimal, Tuple[int, int]]:
        """Reads key value and version from world state."""
        vv = self.world_state.get(key)
        if vv is None:
            return Decimal("0.00"), (0, 0)
        return vv.value, vv.version_tuple

    def simulate_create_voucher(
        self,
        tx_id: str,
        dr_account: str,
        cr_account: str,
        amount: Decimal,
        endorsers: Optional[List[str]] = None,
    ) -> ReadWriteSet:
        """Simulates chaincode execution on peers and creates a ReadWriteSet."""
        dr_key = f"acc_{dr_account}"
        cr_key = f"acc_{cr_account}"
        amt = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        dr_val, dr_ver = self.get_state(dr_key)
        cr_val, cr_ver = self.get_state(cr_key)

        rwset = ReadWriteSet(
            tx_id=tx_id,
            read_set={dr_key: dr_ver, cr_key: cr_ver},
            write_set={dr_key: dr_val + amt, cr_key: cr_val - amt},
            endorsers=endorsers or list(self.required_endorsers),
        )
        return rwset

    def commit_transaction(self, rwset: ReadWriteSet, enforce_endorsement: bool = True) -> bool:
        """Orders and commits transaction through Fabric MVCC validation phase."""
        # 1. Validate Endorsement Policy
        if enforce_endorsement:
            for req in self.required_endorsers:
                if req not in rwset.endorsers:
                    raise EndorsementPolicyMismatch(
                        f"Endorsement policy breached: missing {req} in {rwset.endorsers}"
                    )

        # 2. MVCC Validation Phase: Check if read keys have changed since simulation
        for key, read_ver in rwset.read_set.items():
            curr_val, curr_ver = self.get_state(key)
            if curr_ver != read_ver:
                raise RWSetVersionConflict(
                    f"MVCC conflict on key '{key}': simulated with version {read_ver} but state is at {curr_ver}"
                )

        # 3. Commit WriteSet to World State
        self.current_tx_seq += 1
        for key, new_val in rwset.write_set.items():
            self.world_state[key] = VersionedValue(
                value=new_val,
                block_num=self.current_block,
                tx_num=self.current_tx_seq,
            )

        # Increment block every 10 transactions
        if self.current_tx_seq % 10 == 0:
            self.current_block += 1

        return True

    def inject_mvcc_conflict_anomaly(
        self,
        target_account: str,
        amount1: Decimal,
        amount2: Decimal,
    ) -> Tuple[ReadWriteSet, ReadWriteSet]:
        """Synthesizes two concurrent transactions reading the same key at the same version."""
        acc_key = f"acc_{target_account}"
        _, ver = self.get_state(acc_key)

        tx1 = self.simulate_create_voucher("TX_CONCURRENT_1", target_account, "10100", amount1)
        tx2 = self.simulate_create_voucher("TX_CONCURRENT_2", target_account, "20000", amount2)

        # Both have identical read versions
        return tx1, tx2
