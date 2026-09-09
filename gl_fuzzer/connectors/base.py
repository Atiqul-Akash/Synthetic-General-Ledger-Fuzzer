"""Base abstractions and data transfer objects for bidirectional ERP connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, DebitCredit, JournalEntry


class ERPConnectionConfig(BaseModel):
    """Configuration connection settings for ERP integration."""
    host: str = Field(default="localhost", description="ERP host or endpoint URL")
    port: int = Field(default=443, description="Port number")
    client: str = Field(default="100", description="SAP client / Mandant")
    system_id: str = Field(default="S4H", description="ERP system identifier (e.g. S4H, EBS)")
    company_code: str = Field(default="1000", description="Default company code (BUKRS)")
    auth_type: str = Field(default="basic", description="Auth type: basic, token, oauth2, rfc_snc")
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    verify_ssl: bool = True
    timeout_seconds: int = 30


class ERPPostingResult(BaseModel):
    """Execution response returned when posting a transaction to ERP."""
    success: bool
    document_number: Optional[str] = None
    fiscal_year: int = 2026
    status_code: int = 200
    error_code: Optional[str] = None  # e.g. "SAP_F5_022", "SAP_F5_201"
    error_message: Optional[str] = None
    latency_ms: int = 0
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class OpenItem(BaseModel):
    """Represents an open AP/AR item awaiting clearing in ERP."""
    company_code: str
    account_number: str
    partner_id: str
    partner_name: str
    document_number: str
    posting_date: str
    amount: Decimal
    currency: str = "USD"
    debit_credit: DebitCredit
    is_cleared: bool = False
    clearing_doc: Optional[str] = None


class ERPAccountBalance(BaseModel):
    """Aggregated general ledger account balance snapshot."""
    account_number: str
    company_code: str
    fiscal_year: int
    fiscal_period: int
    debit_balance: Decimal = Decimal("0.00")
    credit_balance: Decimal = Decimal("0.00")
    net_balance: Decimal = Decimal("0.00")
    currency: str = "USD"


class ERPPeriodStatus(BaseModel):
    """Posting period open/close status."""
    fiscal_year: int
    period: int
    is_open: bool = True
    posting_allowed: bool = True


class ERPConnector(ABC):
    """Abstract interface for bidirectional ERP connectors."""

    def __init__(self, config: Optional[ERPConnectionConfig] = None):
        self.config = config or ERPConnectionConfig()
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the ERP system."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes connection to the ERP system."""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Runs health check and diagnostic connectivity test."""
        pass

    @abstractmethod
    def fetch_chart_of_accounts(self, company_code: str) -> ChartOfAccounts:
        """Fetches active Chart of Accounts and account definitions from ERP."""
        pass

    @abstractmethod
    def fetch_open_items(self, company_code: str, account_type: str = "ALL") -> List[OpenItem]:
        """Fetches open AR/AP line items from ERP."""
        pass

    @abstractmethod
    def fetch_account_balances(self, company_code: str, fiscal_year: int) -> Dict[str, ERPAccountBalance]:
        """Fetches current cumulative account balances from ERP."""
        pass

    @abstractmethod
    def fetch_posting_periods(self, company_code: str, fiscal_year: int) -> Dict[int, ERPPeriodStatus]:
        """Fetches status of all fiscal posting periods (open vs locked)."""
        pass

    @abstractmethod
    def post_journal_entry(self, entry: JournalEntry) -> ERPPostingResult:
        """Posts a single journal entry document to ERP."""
        pass

    def post_batch(self, batch: Batch) -> List[ERPPostingResult]:
        """Posts an entire batch of documents to ERP."""
        return [self.post_journal_entry(entry) for entry in batch.entries]
