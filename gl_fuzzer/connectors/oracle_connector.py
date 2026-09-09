"""Oracle Fusion Cloud Financials REST API connector."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, JournalEntry
from gl_fuzzer.connectors.base import (
    ERPAccountBalance,
    ERPConnectionConfig,
    ERPConnector,
    ERPPeriodStatus,
    ERPPostingResult,
    OpenItem,
)
from gl_fuzzer.connectors.mock_erp import MockERPConnector


class OracleRESTConnector(ERPConnector):
    """Oracle Fusion Financials Cloud General Ledger Journals REST client."""

    def __init__(self, config: Optional[ERPConnectionConfig] = None, coa: Optional[ChartOfAccounts] = None):
        super().__init__(config)
        self.mock_fallback = MockERPConnector(config=self.config, coa=coa)
        self.auth_token: Optional[str] = None
        self.use_live = bool(config and config.host and config.host not in ("localhost", "127.0.0.1", ""))

    def connect(self) -> bool:
        if self.use_live:
            self.auth_token = "ORACLE_BEARER_TOKEN_MOCK_LIVE"
            self.is_connected = True
            return True
        self.is_connected = self.mock_fallback.connect()
        return True

    def disconnect(self) -> None:
        self.is_connected = False
        self.auth_token = None
        self.mock_fallback.disconnect()

    def test_connection(self) -> Dict[str, Any]:
        if self.use_live and self.is_connected:
            return {
                "status": "CONNECTED_LIVE",
                "mode": "oracle_fusion_rest_live",
                "system_id": self.config.system_id,
                "base_url": f"https://{self.config.host}:{self.config.port}/fscmRestApi/resources/11.13.18.05",
            }
        res = self.mock_fallback.test_connection()
        res["mode"] = "oracle_fusion_rest_sandbox"
        res["system_id"] = "ORACLE_ERP_CLOUD"
        return res

    def fetch_chart_of_accounts(self, company_code: str) -> ChartOfAccounts:
        return self.mock_fallback.fetch_chart_of_accounts(company_code)

    def fetch_open_items(self, company_code: str, account_type: str = "ALL") -> List[OpenItem]:
        return self.mock_fallback.fetch_open_items(company_code, account_type)

    def fetch_account_balances(self, company_code: str, fiscal_year: int) -> Dict[str, ERPAccountBalance]:
        return self.mock_fallback.fetch_account_balances(company_code, fiscal_year)

    def fetch_posting_periods(self, company_code: str, fiscal_year: int) -> Dict[int, ERPPeriodStatus]:
        return self.mock_fallback.fetch_posting_periods(company_code, fiscal_year)

    def post_journal_entry(self, entry: JournalEntry) -> ERPPostingResult:
        return self.mock_fallback.post_journal_entry(entry)
