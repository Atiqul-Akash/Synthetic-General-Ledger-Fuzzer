"""Zero-OOM streaming synthesis engine with multi-currency triangulation and macro seasonality."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Generator, List, Optional, Tuple
import numpy as np

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import Batch, DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.models.manifest import AnomalyRecord
from gl_fuzzer.models.currency import Currency, ExchangeRateProvider
from gl_fuzzer.generators.macro_calendar import MacroCalendarModulator
from gl_fuzzer.generators.base_engine import BaseSynthesisEngine
from gl_fuzzer.anomalies.pipeline import AnomalyPipeline


class ChunkedSynthesisEngine:
    """Enterprise chunked synthesis engine yielding streaming batches with bounded RAM footprint."""

    def __init__(
        self,
        coa: Optional[ChartOfAccounts] = None,
        seed: Optional[int] = 42,
        multi_currency: bool = False,
        macro_seasonality: bool = False,
        base_currency: str = "USD",
        reporting_currency: str = "USD",
    ):
        self.coa = coa if coa is not None else ChartOfAccounts.create_default()
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.multi_currency = multi_currency
        self.macro_seasonality = macro_seasonality
        self.base_currency = base_currency
        self.reporting_currency = reporting_currency

        self.fx_provider = ExchangeRateProvider(seed=seed) if multi_currency else None
        self.macro_calendar = MacroCalendarModulator(rng=self.rng) if macro_seasonality else None
        self.base_engine = BaseSynthesisEngine(coa=self.coa, seed=seed)
        self.anomaly_pipeline = AnomalyPipeline(coa=self.coa, seed=seed)

    def _apply_multi_currency_and_seasonality(self, entries: List[JournalEntry]) -> List[JournalEntry]:
        """Enriches entries with multi-currency valuations and seasonal date shifts."""
        if not self.multi_currency and not self.macro_seasonality:
            return entries

        foreign_currencies = ["EUR", "GBP", "JPY", "CHF", "CAD"]

        for entry in entries:
            # 1. Apply Macro Seasonality Date Shift
            if self.macro_seasonality and self.macro_calendar:
                try:
                    entry_dt = datetime.fromisoformat(entry.posting_date)
                    is_weekend = entry_dt.weekday() >= 5 or "GHOST" in entry.entry_id or "WEEKEND" in entry.entry_id
                except Exception:
                    is_weekend = "GHOST" in entry.entry_id or "WEEKEND" in entry.entry_id

                if is_weekend:
                    sampled_date = self.macro_calendar.sample_weekend_date()
                else:
                    sampled_date = self.macro_calendar.sample_business_date()
                entry.posting_date = sampled_date.isoformat()
                entry.document_date = sampled_date.isoformat()
                entry.fiscal_year = sampled_date.year
                entry.fiscal_period = sampled_date.month
                time_str = getattr(entry, "entry_time", "09:30:00") or "09:30:00"
                entry.created_at = f"{sampled_date.isoformat()}T{time_str}Z"

            # 2. Apply Multi-Currency Triad (ASC 830)
            if self.multi_currency and self.fx_provider:
                # 35% of transactions are foreign currency
                is_foreign = bool(self.rng.random() < 0.35)
                doc_currency = str(self.rng.choice(foreign_currencies)) if is_foreign else "USD"
                doc_date_str = entry.posting_date

                # Triangulate local and group conversion rates
                rate_to_local = self.fx_provider.get_exchange_rate(doc_currency, self.base_currency, doc_date_str)
                rate_to_group = self.fx_provider.get_exchange_rate(self.base_currency, self.reporting_currency, doc_date_str)

                for line in entry.lines:
                    line.currency = doc_currency
                    line.currency_local = self.base_currency
                    line.currency_group = self.reporting_currency
                    line.exchange_rate_local = rate_to_local
                    line.exchange_rate_group = rate_to_group

                    # Convert to local and group amounts
                    amt_local = (line.amount * rate_to_local).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    amt_group = (amt_local * rate_to_group).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                    line.amount_local = amt_local
                    line.amount_group = amt_group

                # Invariant Safeguard: Ensure local and group sums balance to exact cent
                delta_local = entry.total_debits_local - entry.total_credits_local
                if delta_local != Decimal("0.00") and len(entry.lines) >= 2:
                    # Adjust the largest credit line to safely absorb rounding fractional cent without going <= 0
                    credit_lines = [l for l in entry.lines if l.debit_credit == DebitCredit.CREDIT and l.amount_local is not None]
                    if credit_lines:
                        target_line = max(credit_lines, key=lambda l: l.amount_local or Decimal("0.00"))
                        target_line.amount_local = (target_line.amount_local + delta_local).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                delta_group = entry.total_debits_group - entry.total_credits_group
                if delta_group != Decimal("0.00") and len(entry.lines) >= 2:
                    credit_lines_g = [l for l in entry.lines if l.debit_credit == DebitCredit.CREDIT and l.amount_group is not None]
                    if credit_lines_g:
                        target_line_g = max(credit_lines_g, key=lambda l: l.amount_group or Decimal("0.00"))
                        target_line_g.amount_group = (target_line_g.amount_group + delta_group).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return entries

    def stream_chunks(
        self,
        total_entries: int,
        chunk_size: int = 10_000,
        anomaly_rate: float = 0.05,
        stream_publisher: Optional[Any] = None,
        stream_topic: str = "gl.transactions.v1",
    ) -> Generator[Tuple[List[JournalEntry], List[AnomalyRecord]], None, None]:
        """Yields streaming chunks of balanced and fuzzed journal entries.
        
        Yields: (entries_chunk, anomaly_records_chunk)
        """
        remaining = total_entries
        batch_idx = 1

        while remaining > 0:
            current_chunk_size = min(remaining, chunk_size)
            batch_id = f"STREAM_B{batch_idx:04d}"

            # 1. Generate base clean entries for this chunk
            batch = self.base_engine.generate_batch(batch_id=batch_id, target_entry_count=current_chunk_size)

            # 2. Inject calibrated micro-anomalies first so amounts and entries are finalized
            anom_records: List[AnomalyRecord] = []
            if anomaly_rate > 0.0:
                anom_records = self.anomaly_pipeline.inject_anomalies(batch=batch, overall_anomaly_rate=anomaly_rate)

            # 3. Enrich all entries with multi-currency and seasonality
            batch.entries = self._apply_multi_currency_and_seasonality(batch.entries)

            # 4. Stream publish in real time if publisher provided
            if stream_publisher is not None:
                for entry in batch.entries:
                    stream_publisher.publish_entry(entry, topic=stream_topic)
                for anom in anom_records:
                    stream_publisher.publish_anomaly(anom)
                stream_publisher.flush()

            yield batch.entries, anom_records

            remaining -= current_chunk_size
            batch_idx += 1
