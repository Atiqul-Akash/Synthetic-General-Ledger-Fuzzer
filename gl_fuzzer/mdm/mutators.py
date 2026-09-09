"""Master Data Management mutators for sybil attacks, bank tampering, and employee collusion."""

from __future__ import annotations

import random
import uuid
from typing import Any, Dict, List, Optional, Tuple

from gl_fuzzer.mdm.models import (
    CustomerMaster,
    EmployeeMaster,
    MDMAnomalyRecord,
    MDMAnomalyType,
    VendorMaster,
)


class VendorSybilMutator:
    """Creates near-duplicate vendor records with slightly shifted corporate forms or tax IDs."""

    SUFFIXES = [" LLC", " Corp", " Inc", " Logistics", " Services", " Holdings", " Group"]

    @classmethod
    def mutate(cls, base_vendor: VendorMaster, rng: Optional[random.Random] = None) -> Tuple[VendorMaster, MDMAnomalyRecord]:
        r = rng or random.Random(42)
        base_name = base_vendor.name
        for s in cls.SUFFIXES:
            if base_name.endswith(s):
                base_name = base_name[:-len(s)]
                break

        chosen_suffix = r.choice(cls.SUFFIXES)
        sybil_name = f"{base_name.strip()}{chosen_suffix}"
        sybil_id = f"VEND_SYBIL_{r.randint(1000, 9999)}"

        # Shift tax ID slightly
        tid = list(base_vendor.tax_id)
        if len(tid) > 2 and tid[-1].isdigit():
            tid[-1] = str((int(tid[-1]) + 1) % 10)
        sybil_tax_id = "".join(tid)

        # Alter bank account
        sybil_routing = f"021{r.randint(100000, 999999)}"
        sybil_account = f"{r.randint(100000000, 999999999)}"

        sybil_vendor = VendorMaster(
            vendor_id=sybil_id,
            name=sybil_name,
            tax_id=sybil_tax_id,
            country=base_vendor.country,
            bank_country=base_vendor.bank_country,
            bank_routing_number=sybil_routing,
            bank_account_number=sybil_account,
            payment_terms=base_vendor.payment_terms,
            is_approved=False,
            created_date="2026-03-01",
            last_modified_date="2026-03-01",
        )

        record = MDMAnomalyRecord(
            anomaly_id=f"MDM_SYBIL_{uuid.uuid4().hex[:8].upper()}",
            anomaly_type=MDMAnomalyType.DUPLICATE_SYBIL_VENDOR,
            target_id=sybil_id,
            entity_type="VENDOR",
            description=f"Sybil clone created mimicking '{base_vendor.name}' as '{sybil_name}' with altered bank routing",
            audit_evidence={
                "original_vendor_id": base_vendor.vendor_id,
                "original_vendor_name": base_vendor.name,
                "sybil_vendor_name": sybil_name,
                "sybil_tax_id": sybil_tax_id,
                "sybil_routing": sybil_routing,
            },
            detection_rule="Fuzzy string match >= 85% Levenshtein similarity with distinct bank destination",
        )
        return sybil_vendor, record


class BankRoutingTamperingMutator:
    """Modifies vendor bank details right before scheduled disbursements."""

    @classmethod
    def mutate(
        cls,
        vendor: VendorMaster,
        tamper_date: str = "2026-04-14",
        rng: Optional[random.Random] = None,
    ) -> Tuple[VendorMaster, MDMAnomalyRecord]:
        r = rng or random.Random(42)
        old_routing = vendor.bank_routing_number
        old_account = vendor.bank_account_number

        new_routing = f"091{r.randint(100000, 999999)}"
        new_account = f"{r.randint(500000000, 999999999)}"

        tampered = vendor.model_copy(
            update={
                "bank_routing_number": new_routing,
                "bank_account_number": new_account,
                "last_modified_date": tamper_date,
            }
        )

        record = MDMAnomalyRecord(
            anomaly_id=f"MDM_TAMPER_{uuid.uuid4().hex[:8].upper()}",
            anomaly_type=MDMAnomalyType.BANK_ROUTING_TAMPERING_24H,
            target_id=vendor.vendor_id,
            entity_type="VENDOR",
            description=f"Unauthorized vendor bank account mutation 24h prior to scheduled disbursement run",
            audit_evidence={
                "vendor_id": vendor.vendor_id,
                "vendor_name": vendor.name,
                "old_routing": old_routing,
                "old_account": old_account,
                "new_routing": new_routing,
                "new_account": new_account,
                "tamper_date": tamper_date,
            },
            detection_rule="Audit log timestamp correlation between bank master change and disbursement execution",
        )
        return tampered, record


class EmployeeVendorCollusionMutator:
    """Generates an illicit vendor profile sharing banking coordinates with an internal employee."""

    @classmethod
    def mutate(
        cls,
        employee: EmployeeMaster,
        rng: Optional[random.Random] = None,
    ) -> Tuple[VendorMaster, MDMAnomalyRecord]:
        r = rng or random.Random(42)
        vendor_id = f"VEND_COLLUDE_{employee.employee_id}"
        vendor_name = f"{employee.name.split()[-1]} Advisory Group LLC"

        vendor = VendorMaster(
            vendor_id=vendor_id,
            name=vendor_name,
            tax_id=employee.tax_id,
            bank_country="US",
            bank_routing_number=employee.bank_routing_number,
            bank_account_number=employee.bank_account_number,
            is_approved=True,
            created_date="2026-02-10",
            last_modified_date="2026-02-10",
        )

        record = MDMAnomalyRecord(
            anomaly_id=f"MDM_COLLUDE_{uuid.uuid4().hex[:8].upper()}",
            anomaly_type=MDMAnomalyType.EMPLOYEE_VENDOR_COLLUSION,
            target_id=vendor_id,
            entity_type="VENDOR",
            description=f"Illicit collusion: AP Vendor '{vendor_name}' shares identical bank routing and SSN with Employee {employee.employee_id} ({employee.name})",
            audit_evidence={
                "employee_id": employee.employee_id,
                "employee_name": employee.name,
                "shared_tax_id": employee.tax_id,
                "shared_bank_account": employee.bank_account_number,
                "shared_routing": employee.bank_routing_number,
            },
            detection_rule="Exact match cross-join between HR payroll bank details and AP vendor master",
        )
        return vendor, record
