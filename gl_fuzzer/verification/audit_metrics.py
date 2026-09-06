"""Audit and forensic detection metrics corresponding to the Calibrated Micro-Anomaly Library."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import math
from typing import Any, Dict, List, Tuple
import numpy as np
from scipy import stats

from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry
from gl_fuzzer.generators.distributions import BenfordDistribution


class ForensicAuditEvaluator:
    """Executes SOX 404 and forensic audit screening tests over a general ledger dataset."""

    @classmethod
    def evaluate_benford_compliance(cls, entries: List[JournalEntry]) -> Dict[str, Any]:
        """Performs first-digit Benford's Law Chi-Square test."""
        digit_counts = defaultdict(int)
        total_digits = 0

        for entry in entries:
            for line in entry.lines:
                amt_str = f"{line.amount:.2f}".lstrip("0").lstrip(".")
                if amt_str:
                    first_char = amt_str[0]
                    if first_char in "123456789":
                        digit = int(first_char)
                        digit_counts[digit] += 1
                        total_digits += 1

        if total_digits < 10:
            return {
                "total_observations": total_digits,
                "status": "INSUFFICIENT_DATA",
                "p_value": 1.0,
                "chi2_stat": 0.0,
                "digit_distribution": {},
            }

        observed_counts = np.array([digit_counts[d] for d in range(1, 10)], dtype=np.float64)
        theoretical_probs = BenfordDistribution.get_theoretical_array()
        expected_counts = theoretical_probs * total_digits

        # Chi-Square test
        chi2_res = stats.chisquare(f_obs=observed_counts, f_exp=expected_counts)

        empirical_pcts = {
            f"digit_{d}": round(float(digit_counts[d] / total_digits) * 100, 2)
            for d in range(1, 10)
        }
        theoretical_pcts = {
            f"digit_{d}": round(float(theoretical_probs[d - 1]) * 100, 2)
            for d in range(1, 10)
        }

        # Benford anomaly flagged if p-value < 0.05
        is_anomalous = bool(chi2_res.pvalue < 0.05)

        return {
            "total_observations": total_digits,
            "chi2_statistic": round(float(chi2_res.statistic), 4),
            "p_value": float(chi2_res.pvalue),
            "is_anomalous": is_anomalous,
            "empirical_percentages": empirical_pcts,
            "theoretical_percentages": theoretical_pcts,
            "forensic_conclusion": "REJECT_BENFORD_NULL (High probability of data fabrication/anomaly)" if is_anomalous else "ACCEPT_BENFORD_NULL (Natural logarithmic digit distribution)",
        }

    @classmethod
    def detect_doa_split_clusters(
        cls,
        entries: List[JournalEntry],
        threshold: Decimal = Decimal("10000.00"),
        lower_bound: Decimal = Decimal("9500.00"),
        window_hours: int = 48,
    ) -> Dict[str, Any]:
        """Detects clusters of payments/invoices to the same vendor just below approval thresholds."""
        # Group candidate items by vendor
        vendor_items = defaultdict(list)

        for entry in entries:
            for line in entry.lines:
                if line.vendor_id and (lower_bound <= line.amount < threshold):
                    try:
                        dt = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
                    except Exception:
                        dt = datetime.strptime(f"{entry.posting_date} {entry.entry_time}", "%Y-%m-%d %H:%M:%S")
                    vendor_items[line.vendor_id].append({
                        "entry_id": entry.entry_id,
                        "line_id": line.line_id,
                        "amount": str(line.amount),
                        "timestamp": dt,
                        "user": entry.created_by,
                    })

        flagged_clusters = []
        for vendor, items in vendor_items.items():
            if len(items) < 2:
                continue
            # Sort chronologically
            items.sort(key=lambda x: x["timestamp"])

            current_cluster = [items[0]]
            for next_item in items[1:]:
                diff_hours = (next_item["timestamp"] - current_cluster[0]["timestamp"]).total_seconds() / 3600.0
                if diff_hours <= window_hours:
                    current_cluster.append(next_item)
                else:
                    unique_entries = set(x["entry_id"] for x in current_cluster)
                    if len(unique_entries) >= 2:
                        tot_amt = sum((Decimal(x["amount"]) for x in current_cluster), Decimal("0.00"))
                        flagged_clusters.append({
                            "vendor": vendor,
                            "cluster_size": len(current_cluster),
                            "total_amount": str(tot_amt),
                            "entry_ids": list(unique_entries),
                            "users": list(set(x["user"] for x in current_cluster)),
                        })
                    current_cluster = [next_item]

            unique_entries = set(x["entry_id"] for x in current_cluster)
            if len(unique_entries) >= 2:
                tot_amt = sum((Decimal(x["amount"]) for x in current_cluster), Decimal("0.00"))
                flagged_clusters.append({
                    "vendor": vendor,
                    "cluster_size": len(current_cluster),
                    "total_amount": str(tot_amt),
                    "entry_ids": list(unique_entries),
                    "users": list(set(x["user"] for x in current_cluster)),
                })

        return {
            "threshold_checked": str(threshold),
            "window_hours": window_hours,
            "detected_clusters_count": len(flagged_clusters),
            "clusters": flagged_clusters,
            "has_doa_violations": len(flagged_clusters) > 0,
        }

    @classmethod
    def detect_off_hours_and_ghost_entries(cls, entries: List[JournalEntry]) -> Dict[str, Any]:
        """Detects manual journal entries (MJE) posted outside business calendars or during deep night."""
        flagged_entries = []

        for entry in entries:
            try:
                t_parts = [int(p) for p in entry.entry_time.split(":")]
                hour = t_parts[0]
            except Exception:
                hour = 12

            try:
                d = datetime.fromisoformat(entry.posting_date).date()
                is_weekend = d.weekday() >= 5
            except Exception:
                is_weekend = False

            is_deep_night = (2 <= hour <= 4)
            is_manual = entry.document_type in (DocumentType.MJE, DocumentType.SA)

            if (is_deep_night or is_weekend) and is_manual:
                flagged_entries.append({
                    "entry_id": entry.entry_id,
                    "document_number": entry.document_number,
                    "created_by": entry.created_by,
                    "posting_date": entry.posting_date,
                    "entry_time": entry.entry_time,
                    "is_weekend": is_weekend,
                    "is_deep_night": is_deep_night,
                    "amount": str(entry.total_debits),
                    "header_text": entry.header_text,
                })

        ghost_count = sum(1 for e in flagged_entries if e["is_deep_night"] or "DORMANT" in e.get("created_by", "") or "OVERRIDE" in e.get("header_text", "") or "GHOST" in e.get("header_text", ""))
        off_hours_count = sum(1 for e in flagged_entries if e["is_deep_night"])
        weekend_count = sum(1 for e in flagged_entries if e["is_weekend"])

        return {
            "total_entries_checked": len(entries),
            "off_hours_flagged_count": len(flagged_entries),
            "ghost_entries_count": ghost_count,
            "off_hours_entries_count": off_hours_count,
            "weekend_entries_count": weekend_count,
            "flagged_entries": flagged_entries,
            "has_off_hours_anomalies": len(flagged_entries) > 0,
            "has_unauthorized_mj_entries": len(flagged_entries) > 0,
        }

    @classmethod
    def detect_anomalous_pairings(cls, entries: List[JournalEntry]) -> Dict[str, Any]:
        """Detects prohibited account pairings (Cash <-> Expense, Suspense 99999, Expense <-> PPE)."""
        flagged_pairings = []

        for entry in entries:
            accounts_debited = {l.account_code for l in entry.lines if l.debit_credit == DebitCredit.DEBIT}
            accounts_credited = {l.account_code for l in entry.lines if l.debit_credit == DebitCredit.CREDIT}

            # 1. Cash debited, Expense credited
            cash_debited = bool("10100" in accounts_debited)
            expense_credited = any(acc.startswith(("5", "6")) for acc in accounts_credited)
            if cash_debited and expense_credited:
                flagged_pairings.append({
                    "entry_id": entry.entry_id,
                    "type": "CASH_DIRECT_EXPENSE_BYPASS",
                    "debit_accounts": list(accounts_debited),
                    "credit_accounts": list(accounts_credited),
                    "amount": str(entry.total_debits),
                })

            # 2. Suspense account parking (99999)
            if "99999" in accounts_debited or "99999" in accounts_credited:
                flagged_pairings.append({
                    "entry_id": entry.entry_id,
                    "type": "SUSPENSE_ACCOUNT_PARKING",
                    "debit_accounts": list(accounts_debited),
                    "credit_accounts": list(accounts_credited),
                    "amount": str(entry.total_debits),
                })

            # 3. Direct Expense debit with Fixed Asset credit
            if any(acc.startswith(("6")) for acc in accounts_debited) and "17000" in accounts_credited:
                flagged_pairings.append({
                    "entry_id": entry.entry_id,
                    "type": "EXPENSE_FIXED_ASSET_IMPAIRMENT_BYPASS",
                    "debit_accounts": list(accounts_debited),
                    "credit_accounts": list(accounts_credited),
                    "amount": str(entry.total_debits),
                })

        return {
            "total_entries_checked": len(entries),
            "flagged_pairings_count": len(flagged_pairings),
            "violations_count": len(flagged_pairings),
            "pairings": flagged_pairings,
            "has_anomalous_pairings": len(flagged_pairings) > 0,
            "has_topological_violations": len(flagged_pairings) > 0,
        }

    @classmethod
    def detect_intercompany_cycles(cls, entries: List[JournalEntry]) -> Dict[str, Any]:
        """Detects circular intercompany trading loops (A -> B -> C -> A) using graph cycle analysis."""
        # Build adjacency edges: sender -> receiver with transfer amount and dates
        graph = defaultdict(set)
        transfer_details = []

        for entry in entries:
            sender = entry.company_code
            for line in entry.lines:
                receiver = line.trading_partner
                if receiver and sender != receiver:
                    # Directional capital outflow: track Intercompany Receivables debit
                    if line.account_code == "12000" and line.debit_credit == DebitCredit.DEBIT:
                        graph[sender].add(receiver)
                        transfer_details.append({
                            "entry_id": entry.entry_id,
                            "sender": sender,
                            "receiver": receiver,
                            "amount": str(line.amount),
                            "date": entry.posting_date,
                        })

        # DFS Cycle Detection
        cycles: List[List[str]] = []
        visited: Dict[str, int] = {}  # 0=unvisited, 1=visiting, 2=visited
        path: List[str] = []

        all_nodes = sorted(list(set(list(graph.keys()) + [v for neighbors in graph.values() for v in neighbors])))

        def dfs(node: str):
            visited[node] = 1
            path.append(node)

            for neighbor in sorted(graph.get(node, [])):
                if visited.get(neighbor, 0) == 1:
                    # Cycle found: extract cycle slice
                    cycle_start_idx = path.index(neighbor)
                    raw_cycle = path[cycle_start_idx:]
                    if len(raw_cycle) >= 3:  # True multi-hop intercompany round-trip
                        min_elem = min(raw_cycle)
                        min_idx = raw_cycle.index(min_elem)
                        canonical = raw_cycle[min_idx:] + raw_cycle[:min_idx] + [min_elem]
                        if canonical not in cycles:
                            cycles.append(canonical)
                elif visited.get(neighbor, 0) == 0:
                    dfs(neighbor)

            path.pop()
            visited[node] = 2

        for node in all_nodes:
            if visited.get(node, 0) == 0:
                dfs(node)

        return {
            "entities_participating": all_nodes,
            "intercompany_transfers_count": len(transfer_details),
            "detected_cycles_count": len(cycles),
            "cycles": cycles,
            "has_cycles": len(cycles) > 0,
            "has_circular_round_tripping": len(cycles) > 0,
        }
