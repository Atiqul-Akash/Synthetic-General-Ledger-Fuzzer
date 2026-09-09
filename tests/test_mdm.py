"""Tests for Master Data Management (MDM) fuzzing and integrity screening."""

import pytest

from gl_fuzzer.mdm.models import MDMAnomalyType
from gl_fuzzer.mdm.engine import MasterDataManager


def test_master_data_initialization():
    mdm = MasterDataManager.create_default(seed=42)
    assert len(mdm.vendors) >= 5
    assert len(mdm.employees) >= 3
    assert "VEND_001" in mdm.vendors
    assert "EMP_001" in mdm.employees


def test_sybil_vendor_injection_and_detection():
    mdm = MasterDataManager.create_default(seed=42)
    sybil_vendor, record = mdm.inject_sybil_vendor("VEND_001")

    assert record.anomaly_type == MDMAnomalyType.DUPLICATE_SYBIL_VENDOR
    assert sybil_vendor.vendor_id in mdm.vendors
    assert sybil_vendor.name != mdm.vendors["VEND_001"].name

    # Screen for sybils
    screening = mdm.screen_mdm_anomalies()
    assert screening["has_mdm_anomalies"] is True
    assert screening["sybil_duplicates_found"] >= 1
    assert any(s["vendor_2"]["id"] == sybil_vendor.vendor_id for s in screening["sybils"])


def test_bank_routing_tampering():
    mdm = MasterDataManager.create_default(seed=42)
    old_account = mdm.vendors["VEND_002"].bank_account_number
    tampered, record = mdm.tamper_vendor_bank("VEND_002", tamper_date="2026-05-01")

    assert record.anomaly_type == MDMAnomalyType.BANK_ROUTING_TAMPERING_24H
    assert tampered.bank_account_number != old_account
    assert tampered.last_modified_date == "2026-05-01"


def test_employee_vendor_collusion_and_detection():
    mdm = MasterDataManager.create_default(seed=42)
    collude_vendor, record = mdm.inject_employee_collusion("EMP_001")

    assert record.anomaly_type == MDMAnomalyType.EMPLOYEE_VENDOR_COLLUSION
    assert collude_vendor.bank_account_number == mdm.employees["EMP_001"].bank_account_number

    # Screen for collusion
    screening = mdm.screen_mdm_anomalies()
    assert screening["has_mdm_anomalies"] is True
    assert screening["collusions_found"] >= 1
    collusion_match = screening["collusions"][0]
    assert collusion_match["employee_id"] == "EMP_001"
    assert collusion_match["vendor_id"] == collude_vendor.vendor_id
