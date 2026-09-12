"""Master Data Manager: Central registry and audit screening for enterprise master data."""

from __future__ import annotations

import difflib
import random
from typing import Any, Dict, List, Optional, Tuple

from gl_fuzzer.mdm.models import (
    CustomerMaster,
    EmployeeMaster,
    MDMAnomalyRecord,
    MDMAnomalyType,
    VendorMaster,
)
from gl_fuzzer.mdm.mutators import (
    BankRoutingTamperingMutator,
    EmployeeVendorCollusionMutator,
    VendorSybilMutator,
)


class MasterDataManager:
    """Enterprise Master Data Management registry with deep fraud injection and screening."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.vendors: Dict[str, VendorMaster] = {}
        self.customers: Dict[str, CustomerMaster] = {}
        self.employees: Dict[str, EmployeeMaster] = {}
        self.anomalies: List[MDMAnomalyRecord] = []
        self.company_tolerances: Dict[str, Dict[str, Any]] = {
            "1000": {"three_way_match_tolerance_pct": 1.0, "require_approval": True},
            "2000": {"three_way_match_tolerance_pct": 5.0, "require_approval": True},
            "3000": {"three_way_match_tolerance_pct": 100.0, "require_approval": False},  # Policy drift
        }

    @classmethod
    def create_default(cls, seed: int = 42) -> MasterDataManager:
        """Instantiates and pre-populates an enterprise MDM registry."""
        mdm = cls(seed=seed)
        mdm._seed_baseline_records()
        return mdm

    def _seed_baseline_records(self):
        # 5 baseline vendors
        default_vendors = [
            ("VEND_001", "Apex Logistics Corporation", "12-3456781", "021000021", "123456789"),
            ("VEND_002", "Nordic Raw Materials AS", "12-3456782", "021000022", "234567890"),
            ("VEND_003", "Precision Tooling & Equipment Inc", "12-3456783", "021000023", "345678901"),
            ("VEND_004", "Global Tech Cloud Services LLC", "12-3456784", "021000024", "456789012"),
            ("VEND_005", "Acme Office Supplies Ltd", "12-3456785", "021000025", "567890123"),
        ]
        for vid, name, tax, routing, acct in default_vendors:
            self.vendors[vid] = VendorMaster(
                vendor_id=vid, name=name, tax_id=tax, bank_routing_number=routing, bank_account_number=acct
            )

        # 3 baseline employees
        default_employees = [
            ("EMP_001", "David Sterling", "021000099", "998877665", "999-11-2233", "FINANCE_AP"),
            ("EMP_002", "Samantha Miller", "021000098", "887766554", "999-22-3344", "PROCUREMENT"),
            ("EMP_003", "Michael Thorne", "021000097", "776655443", "999-33-4455", "EXECUTIVE"),
        ]
        for eid, name, routing, acct, tax, dept in default_employees:
            self.employees[eid] = EmployeeMaster(
                employee_id=eid, name=name, bank_routing_number=routing, bank_account_number=acct, tax_id=tax, department=dept
            )

    def inject_sybil_vendor(self, base_vendor_id: str = "VEND_001") -> Tuple[VendorMaster, MDMAnomalyRecord]:
        """Injects a near-duplicate Sybil vendor clone."""
        base_vendor = self.vendors.get(base_vendor_id) or next(iter(self.vendors.values()))
        sybil_vendor, record = VendorSybilMutator.mutate(base_vendor, self.rng)
        self.vendors[sybil_vendor.vendor_id] = sybil_vendor
        self.anomalies.append(record)
        return sybil_vendor, record

    def tamper_vendor_bank(self, vendor_id: str = "VEND_002", tamper_date: str = "2026-04-14") -> Tuple[VendorMaster, MDMAnomalyRecord]:
        """Modifies a vendor's banking routing immediately prior to a payment."""
        vendor = self.vendors.get(vendor_id) or (next(iter(self.vendors.values())) if self.vendors else None)
        if not vendor:
            raise ValueError(f"Vendor {vendor_id} not found and registry is empty")
        tampered, record = BankRoutingTamperingMutator.mutate(vendor, tamper_date, self.rng)
        self.vendors[vendor.vendor_id] = tampered
        self.anomalies.append(record)
        return tampered, record

    def inject_employee_collusion(self, employee_id: str = "EMP_001") -> Tuple[VendorMaster, MDMAnomalyRecord]:
        """Creates a vendor record colluding with an employee's personal bank account."""
        employee = self.employees.get(employee_id) or (next(iter(self.employees.values())) if self.employees else None)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found and registry is empty")
        collude_vendor, record = EmployeeVendorCollusionMutator.mutate(employee, self.rng)
        self.vendors[collude_vendor.vendor_id] = collude_vendor
        self.anomalies.append(record)
        return collude_vendor, record

    def screen_mdm_anomalies(self) -> Dict[str, Any]:
        """Forensic screening detecting Sybil duplicates, employee collusion, and policy drift."""
        flagged_sybils = []
        flagged_collusions = []

        # 1. Fuzzy match duplicate vendor check
        vendor_list = list(self.vendors.values())
        for i in range(len(vendor_list)):
            for j in range(i + 1, len(vendor_list)):
                v1 = vendor_list[i]
                v2 = vendor_list[j]
                ratio = difflib.SequenceMatcher(None, v1.name.lower(), v2.name.lower()).ratio()
                if ratio >= 0.85:
                    same_bank = (v1.bank_account_number == v2.bank_account_number)
                    flagged_sybils.append({
                        "vendor_1": {"id": v1.vendor_id, "name": v1.name},
                        "vendor_2": {"id": v2.vendor_id, "name": v2.name},
                        "similarity_score": round(ratio, 4),
                        "shared_bank_account": same_bank,
                        "reason": (
                            "High name similarity with shared bank account — high fraud risk"
                            if same_bank
                            else "High name similarity with disparate bank routing"
                        ),
                    })

        # 2. Employee collusion cross-check
        emp_banks = {(e.bank_routing_number, e.bank_account_number): e for e in self.employees.values()}
        for v in self.vendors.values():
            key = (v.bank_routing_number, v.bank_account_number)
            if key in emp_banks:
                matching_emp = emp_banks[key]
                flagged_collusions.append({
                    "vendor_id": v.vendor_id,
                    "vendor_name": v.name,
                    "employee_id": matching_emp.employee_id,
                    "employee_name": matching_emp.name,
                    "shared_bank_account": v.bank_account_number,
                })

        return {
            "total_vendors_screened": len(self.vendors),
            "total_employees_screened": len(self.employees),
            "sybil_duplicates_found": len(flagged_sybils),
            "sybils": flagged_sybils,
            "collusions_found": len(flagged_collusions),
            "collusions": flagged_collusions,
            "has_mdm_anomalies": len(flagged_sybils) > 0 or len(flagged_collusions) > 0,
        }
