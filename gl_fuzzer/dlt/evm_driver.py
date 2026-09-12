"""Enterprise EVM Smart Contract Settlement & Exploit Fuzzer."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class EVMError(Exception):
    """Base exception for EVM smart contract execution errors."""
    pass


class ReentrancyExploitError(EVMError):
    """Raised when recursive callback drains contract funds before balance state mutation."""
    pass


class GasLimitExceededError(EVMError):
    """Raised when computational steps exceed block gas limit."""
    pass


class IntegerUnderflowError(EVMError):
    """Raised when an unconstrained subtraction wraps around MAX_UINT256."""
    pass


class StorageCollisionError(EVMError):
    """Raised when delegatecall writes to mismatched proxy storage slot."""
    pass


UINT256_MAX = 2**256 - 1


class EVMSmartContractSimulator:
    """Simulates enterprise ERC-20 / ERC-1155 settlement contracts and fuzzer exploit vectors."""

    def __init__(
        self,
        token_name: str = "Enterprise Stablecoin Settlement Token",
        symbol: str = "ESTT",
        initial_supply: int = 100_000_000_000_000_000_000_000,  # 100,000 * 10^18
        gas_limit: int = 8_000_000,
    ):
        self.token_name = token_name
        self.symbol = symbol
        self.total_supply = initial_supply
        self.gas_limit = gas_limit
        self.balances: Dict[str, int] = {
            "0xTREASURY_ESCROW": initial_supply,
            "0xCORP_OPERATIONS": 0,
            "0xSETTLEMENT_POOL": 0,
        }
        self.allowances: Dict[Tuple[str, str], int] = {}
        self.proxy_slots: Dict[int, str] = {0: "0xIMPLEMENTATION_ADDR", 1: "0xOWNER_ADDR"}

    def balance_of(self, account: str) -> int:
        return self.balances.get(account, 0)

    def transfer(self, sender: str, recipient: str, amount: int) -> bool:
        """Standard ERC-20 transfer with SafeMath / Solidity >=0.8 check."""
        if amount < 0:
            raise EVMError("Negative amounts prohibited")
        sender_bal = self.balance_of(sender)
        if sender_bal < amount:
            raise EVMError(f"ERC20: transfer amount exceeds balance ({sender_bal} < {amount})")

        self.balances[sender] = sender_bal - amount
        self.balances[recipient] = self.balance_of(recipient) + amount
        return True

    def approve(self, owner: str, spender: str, amount: int) -> bool:
        self.allowances[(owner, spender)] = amount
        return True

    def transfer_from(self, spender: str, from_account: str, to_account: str, amount: int) -> bool:
        allowed = self.allowances.get((from_account, spender), 0)
        if allowed < amount:
            raise EVMError("ERC20: insufficient allowance")
        self.allowances[(from_account, spender)] = allowed - amount
        return self.transfer(from_account, to_account, amount)

    # -----------------------------------------------------------------------
    # Exploit & Vulnerability Fuzzing Vectors
    # -----------------------------------------------------------------------

    def fuzz_integer_underflow(self, sender: str, amount: int) -> int:
        """Fuzzes pre-Solidity 0.8 unchecked integer underflow wrapping."""
        sender_bal = self.balance_of(sender)
        if amount > sender_bal:
            # Underflow wraps modulo 2^256
            wrapped = (sender_bal - amount) % (UINT256_MAX + 1)
            self.balances[sender] = wrapped
            return wrapped
        self.balances[sender] = sender_bal - amount
        return self.balances[sender]

    def fuzz_reentrancy_attack(
        self,
        victim_contract: str,
        attacker_contract: str,
        withdraw_amount: int,
        max_depth: int = 5,
    ) -> int:
        """Simulates classic DAO reentrancy where external call is made before state update."""
        pool_balance = self.balance_of(victim_contract)
        attacker_initial_balance = self.balance_of(attacker_contract)

        depth = 0
        total_drained = 0

        # Vulnerable withdrawal logic: external call before balance reset
        def reentrant_hook():
            nonlocal depth, total_drained, pool_balance
            depth += 1
            if depth < max_depth and pool_balance >= withdraw_amount:
                total_drained += withdraw_amount
                pool_balance -= withdraw_amount
                reentrant_hook()

        reentrant_hook()
        # State finally updated after malicious calls finish
        self.balances[victim_contract] = pool_balance
        self.balances[attacker_contract] = attacker_initial_balance + total_drained

        if depth > 1:
            raise ReentrancyExploitError(
                f"Reentrancy exploited: drained {total_drained} tokens over {depth} recursion levels"
            )
        return total_drained

    def fuzz_gas_limit_exhaustion(self, recipient_count: int, gas_per_transfer: int = 21_000) -> int:
        """Simulates batch mass payment loop that runs out of block gas limit."""
        total_gas = recipient_count * gas_per_transfer
        if total_gas > self.gas_limit:
            raise GasLimitExceededError(
                f"Out of Gas: required {total_gas:,} gas exceeds block limit {self.gas_limit:,}"
            )
        return total_gas

    def fuzz_delegatecall_storage_collision(
        self,
        new_implementation_addr: str,
        target_slot: int = 0,
    ) -> bool:
        """Simulates unaligned proxy implementation overwrite of sensitive storage slot."""
        # Target slot 0 is implementation, slot 1 is owner
        self.proxy_slots[target_slot] = new_implementation_addr
        if target_slot == 1:
            raise StorageCollisionError("Storage collision: Proxy owner slot overwritten by delegatecall!")
        return True
