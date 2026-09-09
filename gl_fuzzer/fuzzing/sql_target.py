"""Relational SQL execution target with ACID transactions and strict SQL constraints."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from typing import Any, Dict, List, Optional

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import JournalEntry
from gl_fuzzer.fuzzing.target import ERPExecutionTarget, TargetExecutionResult, TargetStatus


class RelationalLedgerTarget(ERPExecutionTarget):
    """Executes postings against an ACID-compliant relational SQL schema with foreign keys."""

    def __init__(self, coa: Optional[ChartOfAccounts] = None):
        self.coa = coa or ChartOfAccounts.create_default()
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                account_code TEXT PRIMARY KEY,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                document_number TEXT PRIMARY KEY,
                company_code TEXT NOT NULL,
                fiscal_year INTEGER NOT NULL,
                fiscal_period INTEGER NOT NULL,
                posting_date TEXT NOT NULL,
                document_type TEXT NOT NULL,
                header_text TEXT,
                reference TEXT
            );

            CREATE TABLE IF NOT EXISTS line_items (
                line_id TEXT PRIMARY KEY,
                document_number TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                account_code TEXT NOT NULL,
                debit_credit TEXT NOT NULL CHECK(debit_credit IN ('DEBIT', 'CREDIT')),
                amount NUMERIC NOT NULL CHECK(amount > 0),
                currency TEXT NOT NULL,
                cost_center TEXT,
                FOREIGN KEY (document_number) REFERENCES journal_entries(document_number),
                FOREIGN KEY (account_code) REFERENCES chart_of_accounts(account_code)
            );
        """)
        # Seed Chart of Accounts
        for code, acc in self.coa.accounts.items():
            cur.execute(
                "INSERT OR REPLACE INTO chart_of_accounts VALUES (?, ?, ?);",
                (code, acc.name, acc.account_type.value),
            )
        self.conn.commit()

    def reset_target(self) -> None:
        self.conn.execute("DELETE FROM line_items;")
        self.conn.execute("DELETE FROM journal_entries;")
        self.conn.commit()

    def get_health(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        entries_cnt = cur.execute("SELECT COUNT(*) FROM journal_entries;").fetchone()[0]
        lines_cnt = cur.execute("SELECT COUNT(*) FROM line_items;").fetchone()[0]
        return {
            "status": "HEALTHY",
            "type": "RelationalLedgerTarget_SQLite",
            "total_documents": entries_cnt,
            "total_lines": lines_cnt,
        }

    def execute_entry(self, entry: JournalEntry) -> TargetExecutionResult:
        start = time.perf_counter()
        payload_hash = hashlib.sha256(entry.model_dump_json().encode("utf-8")).hexdigest()

        cur = self.conn.cursor()
        savepoint_name = f"sp_{entry.document_number.replace('-', '_')}"

        try:
            cur.execute(f"SAVEPOINT {savepoint_name};")

            # Check 1: Invariant balance check before SQL commit
            if not entry.is_balanced:
                cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))
                return TargetExecutionResult(
                    entry_id=entry.entry_id,
                    status=TargetStatus.REJECTED_VALIDATION,
                    status_code=400,
                    error_code="SQL_CHECK_IMBALANCE",
                    error_message=f"Double-entry debit!=credit imbalance (Delta: {entry.balance_delta})",
                    response_ms=elapsed_ms,
                    payload_hash=payload_hash,
                )

            # Insert Header
            cur.execute(
                """
                INSERT INTO journal_entries (document_number, company_code, fiscal_year, fiscal_period, posting_date, document_type, header_text, reference)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    entry.document_number,
                    entry.company_code,
                    entry.fiscal_year,
                    entry.fiscal_period,
                    entry.posting_date,
                    entry.document_type.value,
                    entry.header_text,
                    entry.reference,
                ),
            )

            # Insert Lines
            for line in entry.lines:
                cur.execute(
                    """
                    INSERT INTO line_items (line_id, document_number, line_number, account_code, debit_credit, amount, currency, cost_center)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        line.line_id,
                        entry.document_number,
                        line.line_number,
                        line.account_code,
                        line.debit_credit.value,
                        float(line.amount),
                        line.currency,
                        line.cost_center,
                    ),
                )

            cur.execute(f"RELEASE SAVEPOINT {savepoint_name};")
            self.conn.commit()

            elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))

            # Anomaly bypass check
            if entry.is_anomaly:
                return TargetExecutionResult(
                    entry_id=entry.entry_id,
                    status=TargetStatus.BYPASS_DETECTED,
                    status_code=200,
                    response_ms=elapsed_ms,
                    payload_hash=payload_hash,
                    bypass_vector=",".join(entry.anomaly_ids) if entry.anomaly_ids else "ANOMALY_ACCEPTED",
                )

            return TargetExecutionResult(
                entry_id=entry.entry_id,
                status=TargetStatus.ACCEPTED,
                status_code=200,
                response_ms=elapsed_ms,
                payload_hash=payload_hash,
            )

        except sqlite3.IntegrityError as ex:
            cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
            elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))
            return TargetExecutionResult(
                entry_id=entry.entry_id,
                status=TargetStatus.REJECTED_CONSTRAINT,
                status_code=400,
                error_code="SQL_INTEGRITY_VIOLATION",
                error_message=str(ex),
                response_ms=elapsed_ms,
                payload_hash=payload_hash,
            )
        except Exception as ex:
            cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
            elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))
            return TargetExecutionResult(
                entry_id=entry.entry_id,
                status=TargetStatus.CRASH_500,
                status_code=500,
                error_code="SQL_OPERATIONAL_CRASH",
                error_message=str(ex),
                response_ms=elapsed_ms,
                payload_hash=payload_hash,
            )
