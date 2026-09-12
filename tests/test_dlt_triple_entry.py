"""Test suite for Cryptographic Triple-Entry, Merkle Ledger, Fabric, and EVM drivers."""

from decimal import Decimal
import pytest

from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.dlt import (
    EndorsementPolicyMismatch,
    EVMSmartContractSimulator,
    FabricLedgerSimulator,
    GasLimitExceededError,
    MerkleIntegrityError,
    MerkleLedger,
    RWSetVersionConflict,
    ReentrancyExploitError,
)


@pytest.fixture
def sample_entries():
    engine = BaseSynthesisEngine(seed=42)
    return engine.generate_batch(target_entry_count=6).entries


def test_merkle_tree_construction_and_verification(sample_entries):
    ledger = MerkleLedger(sample_entries)
    assert len(ledger.root_hash) == 64  # SHA-256 hex string
    assert ledger.verify_entire_ledger()


def test_merkle_inclusion_proof_and_receipt(sample_entries):
    ledger = MerkleLedger(sample_entries)
    receipt = ledger.generate_triple_entry_receipt(0)

    assert receipt.entry_id == sample_entries[0].entry_id
    assert receipt.root_hash == ledger.root_hash
    assert len(receipt.proof_steps) > 0

    # Verify proof independently
    is_valid = MerkleLedger.verify_proof(
        receipt.entry_leaf_hash, receipt.proof_steps, receipt.root_hash
    )
    assert is_valid


def test_merkle_tamper_detection(sample_entries):
    ledger = MerkleLedger(sample_entries)
    # Tamper with an entry amount
    sample_entries[0].lines[0].amount = Decimal("999999.99")

    # verify_entire_ledger should raise MerkleIntegrityError
    with pytest.raises(MerkleIntegrityError):
        ledger.verify_entire_ledger()


def test_fabric_simulation_happy_path():
    fab = FabricLedgerSimulator()
    rwset = fab.simulate_create_voucher("TX-HAPPY", "10100", "20000", Decimal("1500.00"))
    assert fab.commit_transaction(rwset)
    val, _ = fab.get_state("acc_10100")
    assert val == Decimal("501500.00")


def test_fabric_mvcc_conflict():
    fab = FabricLedgerSimulator()
    tx1, tx2 = fab.inject_mvcc_conflict_anomaly("10100", Decimal("100.00"), Decimal("200.00"))

    # First transaction commits cleanly
    assert fab.commit_transaction(tx1)

    # Second transaction attempts commit with outdated read version -> MVCC conflict
    with pytest.raises(RWSetVersionConflict):
        fab.commit_transaction(tx2)


def test_fabric_endorsement_mismatch():
    fab = FabricLedgerSimulator()
    rwset = fab.simulate_create_voucher(
        "TX-BAD-ENDORSER", "10100", "20000", Decimal("500.00"), endorsers=["Org1MSP.peer0"]
    )
    with pytest.raises(EndorsementPolicyMismatch):
        fab.commit_transaction(rwset)


def test_evm_transfer_and_balance():
    evm = EVMSmartContractSimulator()
    treasury_bal = evm.balance_of("0xTREASURY_ESCROW")
    assert treasury_bal > 0

    evm.transfer("0xTREASURY_ESCROW", "0xCORP_OPERATIONS", 10_000)
    assert evm.balance_of("0xCORP_OPERATIONS") == 10_000


def test_evm_fuzz_underflow():
    evm = EVMSmartContractSimulator()
    wrapped = evm.fuzz_integer_underflow("0xCORP_OPERATIONS", 500)
    assert wrapped > 0  # Wraps to 2^256 - 500


def test_evm_fuzz_reentrancy():
    evm = EVMSmartContractSimulator()
    evm.balances["0xVICTIM_VAULT"] = 100_000
    evm.balances["0xATTACKER"] = 0

    with pytest.raises(ReentrancyExploitError):
        evm.fuzz_reentrancy_attack("0xVICTIM_VAULT", "0xATTACKER", withdraw_amount=20_000, max_depth=4)


def test_evm_fuzz_gas_exhaustion():
    evm = EVMSmartContractSimulator(gas_limit=100_000)
    with pytest.raises(GasLimitExceededError):
        evm.fuzz_gas_limit_exhaustion(recipient_count=10, gas_per_transfer=21_000)
