"""APTNarrativeOrchestrator: Coordinates multi-quarter, multi-phase financial fraud campaigns."""

from __future__ import annotations

from decimal import Decimal
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple

from gl_fuzzer.models.coa import ChartOfAccounts
from gl_fuzzer.models.journal import DebitCredit, DocumentType, JournalEntry, LineItem
from gl_fuzzer.campaigns.models import (
    APTActor,
    APTCampaignPhase,
    APTCampaignRecord,
    APTCampaignType,
    APTPhaseMilestone,
)


class APTNarrativeOrchestrator:
    """Coordinates complex, multi-period financial fraud narratives linking vouchers across time."""

    def __init__(self, coa: Optional[ChartOfAccounts] = None, seed: int = 42):
        self.coa = coa or ChartOfAccounts.create_default()
        self.rng = random.Random(seed)

    def orchestrate_campaign(
        self,
        campaign_type: APTCampaignType = APTCampaignType.INVENTORY_MAP_CREEP_AND_OBSOLESCENCE,
        fiscal_year: int = 2026,
    ) -> Tuple[APTCampaignRecord, List[JournalEntry]]:
        """Generates a complete multi-quarter adversarial narrative with linked journal vouchers."""
        if campaign_type == APTCampaignType.INVENTORY_MAP_CREEP_AND_OBSOLESCENCE:
            return self._orchestrate_inventory_creep(fiscal_year)
        elif campaign_type == APTCampaignType.ENRON_SPV_ROUND_TRIPPING:
            return self._orchestrate_enron_spv(fiscal_year)
        else:
            return self._orchestrate_doa_kickback(fiscal_year)

    def _orchestrate_inventory_creep(self, fiscal_year: int) -> Tuple[APTCampaignRecord, List[JournalEntry]]:
        adversary = APTActor(
            actor_id="CTRL_MARCUS_V",
            name="Marcus Vance",
            role="Senior Plant Controller",
            company_code="1000",
            access_level="CONTROLLING_SUPERVISOR",
        )
        campaign_id = f"APT_INV_{uuid.uuid4().hex[:8].upper()}"
        entries: List[JournalEntry] = []
        milestones: List[APTPhaseMilestone] = []
        total_illicit = Decimal("0.00")

        # Phase 1: Q1 - Seed Manipulation (Inflated Goods Receipts)
        p1_entries, p1_vol = self._create_inflated_gr_entries(campaign_id, adversary, fiscal_year, period=2, count=3)
        entries.extend(p1_entries)
        total_illicit += p1_vol
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_1_RECONNAISSANCE_AND_SEED,
            fiscal_period=2,
            quarter="Q1",
            description="Gradual micro-inflation of purchase order prices to elevate moving average price (MAP)",
            target_accounts=["14000", "21100"],
            entry_ids=[e.entry_id for e in p1_entries],
            micro_anomalies_injected=["PRICE_VARIANCE_CREEP"],
            illicit_volume=p1_vol,
        ))

        # Phase 2: Q2 - Staging & Margin Depletion
        p2_entries, p2_vol = self._create_depleted_margin_entries(campaign_id, adversary, fiscal_year, period=5, count=3)
        entries.extend(p2_entries)
        total_illicit += p2_vol
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_2_STAGING_AND_MANIPULATION,
            fiscal_period=5,
            quarter="Q2",
            description="Goods issue at inflated MAP transferring value to COGS while suppressing divisional margins",
            target_accounts=["50000", "14100"],
            entry_ids=[e.entry_id for e in p2_entries],
            micro_anomalies_injected=["INFLATED_COGS_DISPATCH"],
            illicit_volume=p2_vol,
        ))

        # Phase 3: Q3 - Laundering & Balancing
        p3_entries, p3_vol = self._create_intercompany_wash(campaign_id, adversary, fiscal_year, period=8)
        entries.extend(p3_entries)
        total_illicit += p3_vol
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_3_LAUNDERING_AND_TRANSFER,
            fiscal_period=8,
            quarter="Q3",
            description="Intercompany transfer to subsidiary Entity 2000 to absorb working capital variance",
            target_accounts=["13000", "21150"],
            entry_ids=[e.entry_id for e in p3_entries],
            micro_anomalies_injected=["INTERCOMPANY_TRANSFER_WASH"],
            illicit_volume=p3_vol,
        ))

        # Phase 4: Q4 - Year-End Concealment (Off-Hours Inventory Write-Down to Suspense)
        p4_entries, p4_vol = self._create_concealment_write_down(campaign_id, adversary, fiscal_year, period=12)
        entries.extend(p4_entries)
        total_illicit += p4_vol
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_4_YEAR_END_CONCEALMENT,
            fiscal_period=12,
            quarter="Q4",
            description="Late-night unauthorized physical inventory write-off to suspense account 99999 concealing discrepancy",
            target_accounts=["99999", "14000"],
            entry_ids=[e.entry_id for e in p4_entries],
            micro_anomalies_injected=["INVENTORY_SHRINKAGE_CONCEALMENT", "GHOST_OFF_HOURS_POSTING"],
            illicit_volume=p4_vol,
        ))

        record = APTCampaignRecord(
            campaign_id=campaign_id,
            title="Multi-Quarter Inventory Valuation Creep & Year-End Obsolescence Concealment",
            campaign_type=APTCampaignType.INVENTORY_MAP_CREEP_AND_OBSOLESCENCE,
            fiscal_year=fiscal_year,
            primary_adversary=adversary,
            target_entities=["1000", "2000"],
            narrative_summary=(
                "A sophisticated 4-quarter conspiracy led by the Plant Controller. In Q1, raw material receipt costs "
                "were subtly inflated across multiple POs to artificially raise the Moving Average Price (MAP). In Q2, "
                "finished goods were relieved at inflated valuation. In Q3, working capital variance was washed across "
                "intercompany trading balances. Finally on Dec 30 in Q4, an unauthorized manual entry credited inventory "
                "into suspense account 99999, concealing the cumulative $25,000+ divergence."
            ),
            milestones=milestones,
            total_entries_generated=len(entries),
            total_illicit_volume=total_illicit,
            is_concealed_at_close=True,
        )
        return record, entries

    def _orchestrate_enron_spv(self, fiscal_year: int) -> Tuple[APTCampaignRecord, List[JournalEntry]]:
        adversary = APTActor(
            actor_id="VP_TREASURY_JH",
            name="Julian Hayes",
            role="VP of Global Treasury",
            company_code="1000",
            access_level="EXECUTIVE_ADMIN",
        )
        campaign_id = f"APT_SPV_{uuid.uuid4().hex[:8].upper()}"
        entries: List[JournalEntry] = []
        milestones: List[APTPhaseMilestone] = []
        total_illicit = Decimal("0.00")

        # Q1: Seed consulting contracts
        e1, v1 = self._create_split_consulting_invoice(campaign_id, adversary, fiscal_year, period=2)
        entries.extend(e1)
        total_illicit += v1
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_1_RECONNAISSANCE_AND_SEED,
            fiscal_period=2,
            quarter="Q1",
            description="Establishment of offshore shell advisory billings",
            target_accounts=["63000", "20000"],
            entry_ids=[e.entry_id for e in e1],
            illicit_volume=v1,
        ))

        # Q2 & Q3: Circular transfers (1000 -> 2000 -> 3000 -> 1000)
        e2, v2 = self._create_circular_loop(campaign_id, adversary, fiscal_year, period=6)
        entries.extend(e2)
        total_illicit += v2
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_2_STAGING_AND_MANIPULATION,
            fiscal_period=6,
            quarter="Q2",
            description="Circular transfer loop across 3 subsidiaries inflating synthetic cash turnover",
            target_accounts=["13000", "21150"],
            entry_ids=[e.entry_id for e in e2],
            micro_anomalies_injected=["CIRCULAR_ROUND_TRIP"],
            illicit_volume=v2,
        ))

        # Q4: Year-end concealment
        e3, v3 = self._create_debt_reclassification(campaign_id, adversary, fiscal_year, period=12)
        entries.extend(e3)
        total_illicit += v3
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_4_YEAR_END_CONCEALMENT,
            fiscal_period=12,
            quarter="Q4",
            description="Executive override reclassifying intercompany debt to operating revenue on Dec 31",
            target_accounts=["21150", "40000"],
            entry_ids=[e.entry_id for e in e3],
            micro_anomalies_injected=["ANOMALOUS_PAIRING_REVENUE", "OFF_HOURS_OVERRIDE"],
            illicit_volume=v3,
        ))

        record = APTCampaignRecord(
            campaign_id=campaign_id,
            title="Offshore SPV Round-Tripping & Year-End Revenue Recognition Conspiracy",
            campaign_type=APTCampaignType.ENRON_SPV_ROUND_TRIPPING,
            fiscal_year=fiscal_year,
            primary_adversary=adversary,
            target_entities=["1000", "2000", "3000"],
            narrative_summary="Multi-quarter round-tripping scheme routing funds through special purpose entities to fabricate operating revenue.",
            milestones=milestones,
            total_entries_generated=len(entries),
            total_illicit_volume=total_illicit,
        )
        return record, entries

    def _orchestrate_doa_kickback(self, fiscal_year: int) -> Tuple[APTCampaignRecord, List[JournalEntry]]:
        adversary = APTActor(
            actor_id="AP_DIR_ELENA",
            name="Elena Rostova",
            role="Director of Accounts Payable",
            company_code="1000",
        )
        campaign_id = f"APT_DOA_{uuid.uuid4().hex[:8].upper()}"
        entries: List[JournalEntry] = []
        milestones: List[APTPhaseMilestone] = []
        total_illicit = Decimal("0.00")

        # Invoices under $10k limit
        e1, v1 = self._create_smurfed_invoices(campaign_id, adversary, fiscal_year, period=4)
        entries.extend(e1)
        total_illicit += v1
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_1_RECONNAISSANCE_AND_SEED,
            fiscal_period=4,
            quarter="Q2",
            description="Sequential invoice splitting clustered at $9,800 to avoid dual-CFO sign-off",
            target_accounts=["62000", "20000"],
            entry_ids=[e.entry_id for e in e1],
            micro_anomalies_injected=["SMURFING_DOA_BYPASS"],
            illicit_volume=v1,
        ))

        # Payment with zero WHT
        e2, v2 = self._create_zero_wht_payment(campaign_id, adversary, fiscal_year, period=7)
        entries.extend(e2)
        total_illicit += v2
        milestones.append(APTPhaseMilestone(
            phase=APTCampaignPhase.PHASE_3_LAUNDERING_AND_TRANSFER,
            fiscal_period=7,
            quarter="Q3",
            description="Immediate vendor disbursement bypassing statutory 10% withholding tax",
            target_accounts=["20000", "10100"],
            entry_ids=[e.entry_id for e in e2],
            micro_anomalies_injected=["TAX_EVASION_ZERO_WHT"],
            illicit_volume=v2,
        ))

        record = APTCampaignRecord(
            campaign_id=campaign_id,
            title="AP Director DOA Smurfing & Statutory Tax Evasion Kickback",
            campaign_type=APTCampaignType.EXECUTIVE_DOA_SMURFING_WITH_KICKBACK,
            fiscal_year=fiscal_year,
            primary_adversary=adversary,
            target_entities=["1000"],
            narrative_summary="Systematic AP bypass splitting invoices below the $10,000 threshold followed by zero-WHT disbursements.",
            milestones=milestones,
            total_entries_generated=len(entries),
            total_illicit_volume=total_illicit,
        )
        return record, entries

    # --- Voucher Builder Helpers ---
    def _create_inflated_gr_entries(self, camp_id, actor, year, period, count):
        entries = []
        vol = Decimal("0.00")
        for i in range(count):
            amt = Decimal(f"{self.rng.randint(4000, 7000)}.00")
            vol += amt
            eid = f"{camp_id}-GR-{period}-{i+1}"
            doc_num = f"50000{self.rng.randint(1000, 9999)}"
            lines = [
                LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="14000", debit_credit=DebitCredit.DEBIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
                LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="21100", debit_credit=DebitCredit.CREDIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
            ]
            entries.append(JournalEntry(
                entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
                document_type=DocumentType.WE, document_number=doc_num, posting_date=f"{year}-02-{10+i:02d}",
                document_date=f"{year}-02-{10+i:02d}", created_at=f"{year}-02-{10+i:02d}T10:00:00", created_by=actor.actor_id,
                reference=f"PO-APT-{i+1}", header_text="Goods Receipt at Adjusted Price", lines=lines,
                is_anomaly=True, anomaly_ids=["APT_INVENTORY_CREEP"],
            ))
        return entries, vol

    def _create_depleted_margin_entries(self, camp_id, actor, year, period, count):
        entries = []
        vol = Decimal("0.00")
        for i in range(count):
            amt = Decimal(f"{self.rng.randint(3500, 6000)}.00")
            vol += amt
            eid = f"{camp_id}-GI-{period}-{i+1}"
            doc_num = f"49000{self.rng.randint(1000, 9999)}"
            lines = [
                LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="50000", debit_credit=DebitCredit.DEBIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
                LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="14100", debit_credit=DebitCredit.CREDIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
            ]
            entries.append(JournalEntry(
                entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
                document_type=DocumentType.WA, document_number=doc_num, posting_date=f"{year}-05-{12+i:02d}",
                document_date=f"{year}-05-{12+i:02d}", created_at=f"{year}-05-{12+i:02d}T11:30:00", created_by=actor.actor_id,
                reference=f"DELV-APT-{i+1}", header_text="Goods Issue with Elevated MAP", lines=lines,
                is_anomaly=True, anomaly_ids=["APT_MARGIN_DEPRESSION"],
            ))
        return entries, vol

    def _create_intercompany_wash(self, camp_id, actor, year, period):
        amt = Decimal("18500.00")
        eid = f"{camp_id}-IC-{period}"
        lines = [
            LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="13000", debit_credit=DebitCredit.DEBIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD", trading_partner="2000"),
            LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="21150", debit_credit=DebitCredit.CREDIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD", trading_partner="2000"),
        ]
        entry = JournalEntry(
            entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
            document_type=DocumentType.IC, document_number="1800000001", posting_date=f"{year}-08-20",
            document_date=f"{year}-08-20", created_at=f"{year}-08-20T14:15:00", created_by=actor.actor_id,
            reference="IC-RECON-Q3", header_text="Intercompany working capital wash", lines=lines,
            is_anomaly=True, anomaly_ids=["APT_INTERCOMPANY_WASH"],
        )
        return [entry], amt

    def _create_concealment_write_down(self, camp_id, actor, year, period):
        amt = Decimal("24750.00")
        eid = f"{camp_id}-MJE-CONCEAL"
        lines = [
            LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="99999", debit_credit=DebitCredit.DEBIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
            LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="14000", debit_credit=DebitCredit.CREDIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
        ]
        entry = JournalEntry(
            entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
            document_type=DocumentType.MJE, document_number="1000099999", posting_date=f"{year}-12-30",
            document_date=f"{year}-12-30", created_at=f"{year}-12-30T03:45:00", created_by=actor.actor_id,
            reference="ADJ-YE-INV", header_text="Year-End Inventory Shrinkage Balancing", lines=lines,
            is_anomaly=True, anomaly_ids=["INVENTORY_SHRINKAGE_CONCEALMENT", "GHOST_OFF_HOURS_POSTING"],
        )
        return [entry], amt

    def _create_split_consulting_invoice(self, camp_id, actor, year, period):
        amt = Decimal("9800.00")
        eid = f"{camp_id}-KR-SPLIT"
        lines = [
            LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="63000", debit_credit=DebitCredit.DEBIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
            LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="20000", debit_credit=DebitCredit.CREDIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD", vendor_id="VEND_SHELL_99"),
        ]
        entry = JournalEntry(
            entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
            document_type=DocumentType.KR, document_number="1900000010", posting_date=f"{year}-02-15",
            document_date=f"{year}-02-15", created_at=f"{year}-02-15T11:00:00", created_by=actor.actor_id,
            reference="INV-ADVISORY-01", header_text="Management Advisory Retainer", lines=lines,
            is_anomaly=True, anomaly_ids=["SMURFING_DOA_BYPASS"],
        )
        return [entry], amt

    def _create_circular_loop(self, camp_id, actor, year, period):
        amt = Decimal("50000.00")
        entries = []
        legs = [("1000", "2000"), ("2000", "3000"), ("3000", "1000")]
        for i, (src, dst) in enumerate(legs):
            eid = f"{camp_id}-CIRC-{i+1}"
            lines = [
                LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="13000", debit_credit=DebitCredit.DEBIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD", trading_partner=dst),
                LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="21150", debit_credit=DebitCredit.CREDIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD", trading_partner=dst),
            ]
            entries.append(JournalEntry(
                entry_id=eid, batch_id=camp_id, company_code=src, fiscal_year=year, fiscal_period=period,
                document_type=DocumentType.IC, document_number=f"18000000{i+2}", posting_date=f"{year}-06-25",
                document_date=f"{year}-06-25", created_at=f"{year}-06-25T16:00:00", created_by=actor.actor_id,
                reference=f"IC-LOOP-{src}-{dst}", header_text="Intercompany treasury settlement", lines=lines,
                is_anomaly=True, anomaly_ids=["CIRCULAR_ROUND_TRIP"],
            ))
        return entries, amt * 3

    def _create_debt_reclassification(self, camp_id, actor, year, period):
        amt = Decimal("150000.00")
        eid = f"{camp_id}-DEBT-RECLASS"
        lines = [
            LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="21150", debit_credit=DebitCredit.DEBIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
            LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="40000", debit_credit=DebitCredit.CREDIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
        ]
        entry = JournalEntry(
            entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
            document_type=DocumentType.MJE, document_number="1000099998", posting_date=f"{year}-12-31",
            document_date=f"{year}-12-31", created_at=f"{year}-12-31T03:15:00", created_by=actor.actor_id,
            reference="YE-RECLASS-SPV", header_text="SPV Liability Reclassification to Revenue", lines=lines,
            is_anomaly=True, anomaly_ids=["ANOMALOUS_PAIRING_REVENUE", "OFF_HOURS_OVERRIDE"],
        )
        return [entry], amt

    def _create_smurfed_invoices(self, camp_id, actor, year, period):
        entries = []
        vol = Decimal("0.00")
        amounts = [Decimal("9850.00"), Decimal("9900.00"), Decimal("9950.00")]
        for i, amt in enumerate(amounts):
            vol += amt
            eid = f"{camp_id}-SMURF-{i+1}"
            lines = [
                LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="62000", debit_credit=DebitCredit.DEBIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
                LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="20000", debit_credit=DebitCredit.CREDIT,
                         amount=amt, amount_local=amt, amount_group=amt, currency="USD", vendor_id="VEND_EXP_77"),
            ]
            entries.append(JournalEntry(
                entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
                document_type=DocumentType.KR, document_number=f"19000000{20+i}", posting_date=f"{year}-04-10",
                document_date=f"{year}-04-10", created_at=f"{year}-04-10T09:30:00", created_by=actor.actor_id,
                reference=f"INV-OFFICE-SMURF-{i+1}", header_text="Facility Operations Split Invoice", lines=lines,
                is_anomaly=True, anomaly_ids=["SMURFING_DOA_BYPASS"],
            ))
        return entries, vol

    def _create_zero_wht_payment(self, camp_id, actor, year, period):
        amt = Decimal("29700.00")
        eid = f"{camp_id}-KZ-ZERO-WHT"
        lines = [
            LineItem(line_id=f"{eid}-1", entry_id=eid, line_number=1, account_code="20000", debit_credit=DebitCredit.DEBIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD", vendor_id="VEND_EXP_77"),
            LineItem(line_id=f"{eid}-2", entry_id=eid, line_number=2, account_code="10100", debit_credit=DebitCredit.CREDIT,
                     amount=amt, amount_local=amt, amount_group=amt, currency="USD"),
        ]
        entry = JournalEntry(
            entry_id=eid, batch_id=camp_id, company_code=actor.company_code, fiscal_year=year, fiscal_period=period,
            document_type=DocumentType.KZ, document_number="1500000099", posting_date=f"{year}-07-15",
            document_date=f"{year}-07-15", created_at=f"{year}-07-15T14:30:00", created_by=actor.actor_id,
            reference="PMT-EXP-BATCH", header_text="Full disbursement without withholding tax", lines=lines,
            is_anomaly=True, anomaly_ids=["TAX_EVASION_ZERO_WHT"],
        )
        return [entry], amt
