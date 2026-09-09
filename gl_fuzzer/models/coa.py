"""Chart of Accounts (COA) and account hierarchy definitions."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"
    CLEARING = "CLEARING"


class NormalBalance(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class Account(BaseModel):
    """Represents an individual general ledger account."""
    code: str = Field(..., description="Account number (e.g. '10100')")
    name: str = Field(..., description="Account description (e.g. 'Operating Cash')")
    account_type: AccountType
    normal_balance: NormalBalance
    parent_code: Optional[str] = None
    is_reconciliation: bool = False
    is_intercompany: bool = False
    is_contra: bool = False
    description: str = ""

    def validate_normal_balance(self) -> bool:
        """Validate whether account adheres to standard accounting normal balance conventions."""
        if self.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            expected = NormalBalance.CREDIT if self.is_contra else NormalBalance.DEBIT
            return self.normal_balance == expected
        elif self.account_type in (AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE):
            expected = NormalBalance.DEBIT if self.is_contra else NormalBalance.CREDIT
            return self.normal_balance == expected
        # CLEARING accounts can be either debit or credit depending on clearing state
        return True


class ChartOfAccounts(BaseModel):
    """Enterprise Chart of Accounts hierarchy."""
    name: str = "Enterprise Standard COA"
    accounts: Dict[str, Account] = Field(default_factory=dict)

    def add_account(self, account: Account) -> None:
        self.accounts[account.code] = account

    def get_account(self, code: str) -> Optional[Account]:
        return self.accounts.get(code)

    def get_accounts_by_type(self, account_type: AccountType) -> List[Account]:
        return [acc for acc in self.accounts.values() if acc.account_type == account_type]

    def get_intercompany_accounts(self) -> List[Account]:
        return [acc for acc in self.accounts.values() if acc.is_intercompany]

    @classmethod
    def create_default(cls) -> ChartOfAccounts:
        """Creates a comprehensive standard enterprise 5-digit Chart of Accounts."""
        coa = cls(name="US GAAP / SAP Enterprise Standard COA")

        account_definitions = [
            # 1xxxx: Assets (Debit Normal)
            Account(code="10100", name="Operating Cash & Bank", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="10200", name="Payroll Cash Account", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="11000", name="Accounts Receivable - Trade", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT, is_reconciliation=True),
            Account(code="11500", name="Allowance for Doubtful Accounts", account_type=AccountType.ASSET, normal_balance=NormalBalance.CREDIT, is_contra=True), # Contra asset
            Account(code="12000", name="Intercompany Receivables", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT, is_intercompany=True),
            Account(code="13000", name="Input Tax / VAT Receivable", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="13100", name="Use Tax Receivable", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="14000", name="Raw Materials Inventory", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="14100", name="Finished Goods Inventory", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="15000", name="Prepaid Expenses", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="17000", name="Property, Plant & Equipment", account_type=AccountType.ASSET, normal_balance=NormalBalance.DEBIT),
            Account(code="17900", name="Accumulated Depreciation - PPE", account_type=AccountType.ASSET, normal_balance=NormalBalance.CREDIT, is_contra=True), # Contra asset

            # 2xxxx: Liabilities & Clearing (Credit Normal)
            Account(code="20000", name="Accounts Payable - Trade", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT, is_reconciliation=True),
            Account(code="21000", name="Accrued Operating Expenses", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),
            Account(code="21100", name="GR/IR Clearing Account", account_type=AccountType.CLEARING, normal_balance=NormalBalance.CREDIT, is_reconciliation=True),
            Account(code="21150", name="GR/IR Subledger Bridge Clearing", account_type=AccountType.CLEARING, normal_balance=NormalBalance.CREDIT, is_reconciliation=True),
            Account(code="21200", name="Salaries and Wages Payable", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),
            Account(code="21250", name="Payroll Accrual Clearing", account_type=AccountType.CLEARING, normal_balance=NormalBalance.CREDIT),
            Account(code="21300", name="Payroll Tax Withholdings Payable", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),
            Account(code="22000", name="Sales Tax Payable", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),
            Account(code="22100", name="Output Tax / VAT Payable", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),
            Account(code="22200", name="Withholding Tax Payable", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),
            Account(code="22300", name="Use Tax Payable", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),
            Account(code="23000", name="Intercompany Payables", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT, is_intercompany=True),
            Account(code="25000", name="Current Portion of Long Term Debt", account_type=AccountType.LIABILITY, normal_balance=NormalBalance.CREDIT),

            # 3xxxx: Equity (Credit Normal)
            Account(code="30000", name="Common Stock", account_type=AccountType.EQUITY, normal_balance=NormalBalance.CREDIT),
            Account(code="31000", name="Additional Paid-in Capital", account_type=AccountType.EQUITY, normal_balance=NormalBalance.CREDIT),
            Account(code="33000", name="Retained Earnings", account_type=AccountType.EQUITY, normal_balance=NormalBalance.CREDIT),

            # 4xxxx: Revenue (Credit Normal)
            Account(code="40000", name="Gross Product Sales Revenue", account_type=AccountType.REVENUE, normal_balance=NormalBalance.CREDIT),
            Account(code="41000", name="Service & Consulting Revenue", account_type=AccountType.REVENUE, normal_balance=NormalBalance.CREDIT),
            Account(code="42000", name="Intercompany Revenue - Management Fees", account_type=AccountType.REVENUE, normal_balance=NormalBalance.CREDIT, is_intercompany=True),
            Account(code="43000", name="Sales Discounts Allowed", account_type=AccountType.REVENUE, normal_balance=NormalBalance.DEBIT, is_contra=True), # Contra revenue
            Account(code="47000", name="Realized Foreign Exchange Gain", account_type=AccountType.REVENUE, normal_balance=NormalBalance.CREDIT),

            # 5xxxx: Cost of Goods Sold & Variances (Debit Normal)
            Account(code="50000", name="Cost of Goods Sold - Materials", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="50100", name="Cost of Goods Sold - Inventory", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="51000", name="Cost of Goods Sold - Labor", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="52000", name="Freight-in / Shipping Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="52100", name="Purchase Price Variance - Materials", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),

            # 6xxxx: Operating Expenses (Debit Normal)
            Account(code="61000", name="Salaries & Wages Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="61100", name="Employer Payroll Taxes Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="61200", name="Employee Benefits Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="62000", name="Rent & Facilities Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="62100", name="Utilities Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="63000", name="Advertising & Marketing Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="64000", name="Legal & Professional Fees", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="65000", name="Depreciation Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="66000", name="Travel & Entertainment Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="67000", name="Realized Foreign Exchange Loss", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),
            Account(code="69000", name="Miscellaneous Operating Expense", account_type=AccountType.EXPENSE, normal_balance=NormalBalance.DEBIT),

            # 9xxxx: Suspense & Intercompany Clearing
            Account(code="90000", name="Intercompany Settlement Clearing", account_type=AccountType.CLEARING, normal_balance=NormalBalance.DEBIT, is_intercompany=True),
            Account(code="99100", name="Intercompany Reconciliation Suspense", account_type=AccountType.CLEARING, normal_balance=NormalBalance.DEBIT, is_intercompany=True),
            Account(code="99999", name="Suspense / Unassigned Account", account_type=AccountType.CLEARING, normal_balance=NormalBalance.DEBIT),
        ]

        for acc in account_definitions:
            coa.add_account(acc)

        return coa
