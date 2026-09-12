"""Test suite for Fixed Assets subledger, depreciation models, impairments, and fraud mutators."""

from decimal import Decimal
import pytest

from gl_fuzzer.subledgers.fixed_assets import (
    AssetClass,
    AssetComponent,
    AssetStatus,
    CapitalizationThresholdEvasionMutator,
    DepreciationMethod,
    FixedAssetMaster,
    FixedAssetSubledger,
    ImpairmentOmissionMutator,
    ZombieAssetMutator,
)
from gl_fuzzer.verification.invariants import InvariantVerifier


def test_fixed_asset_capitalization_threshold():
    subledger = FixedAssetSubledger(capitalization_threshold=Decimal("2500.00"))

    # Case 1: Below threshold -> Expensed directly
    asset_low, entry_low = subledger.register_asset(
        description="Office Mouse and Keyboard",
        cost=Decimal("150.00"),
        useful_life_months=12,
        capitalization_date="2026-09-01",
    )
    assert asset_low is None
    assert entry_low.is_balanced
    assert entry_low.lines[0].account_code == "69000"

    # Case 2: Above threshold -> Capitalized
    asset_high, entry_high = subledger.register_asset(
        description="Heavy Duty CNC Milling Machine",
        cost=Decimal("45000.00"),
        useful_life_months=60,
        capitalization_date="2026-09-01",
        asset_class=AssetClass.MACHINERY,
        salvage_value=Decimal("5000.00"),
    )
    assert asset_high is not None
    assert asset_high.original_cost == Decimal("45000.00")
    assert entry_high.is_balanced
    assert entry_high.lines[0].account_code == "17000"


def test_straight_line_depreciation():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Delivery Van",
        cost=Decimal("36000.00"),
        useful_life_months=36,
        capitalization_date="2026-01-01",
        asset_class=AssetClass.VEHICLES,
        salvage_value=Decimal("0.00"),
        depreciation_method=DepreciationMethod.STRAIGHT_LINE,
    )
    assert asset is not None

    # Month 1
    dep_entry = subledger.calculate_monthly_depreciation(asset.asset_id, "2026-01-31")
    assert dep_entry is not None
    assert dep_entry.is_balanced
    assert dep_entry.total_debits == Decimal("1000.00")
    assert asset.carrying_value == Decimal("35000.00")


def test_double_declining_depreciation():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Server Farm Rack",
        cost=Decimal("24000.00"),
        useful_life_months=24,
        capitalization_date="2026-01-01",
        asset_class=AssetClass.IT_EQUIPMENT,
        salvage_value=Decimal("2000.00"),
        depreciation_method=DepreciationMethod.DOUBLE_DECLINING,
    )
    assert asset is not None

    dep_entry = subledger.calculate_monthly_depreciation(asset.asset_id, "2026-01-31")
    assert dep_entry is not None
    assert dep_entry.is_balanced
    # 24000 * (2/24) = 2000.00
    assert dep_entry.total_debits == Decimal("2000.00")
    assert asset.carrying_value == Decimal("22000.00")


def test_units_of_production_depreciation():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Industrial Injection Molding Machine",
        cost=Decimal("100000.00"),
        useful_life_months=60,
        capitalization_date="2026-01-01",
        salvage_value=Decimal("10000.00"),
        depreciation_method=DepreciationMethod.UNITS_OF_PRODUCTION,
        total_estimated_units=Decimal("100000"),
    )
    assert asset is not None

    # 5,000 units produced: 5000 / 100000 * 90000 = 4500.00
    dep_entry = subledger.calculate_monthly_depreciation(
        asset.asset_id, "2026-01-31", units_produced=Decimal("5000")
    )
    assert dep_entry is not None
    assert dep_entry.is_balanced
    assert dep_entry.total_debits == Decimal("4500.00")
    assert asset.carrying_value == Decimal("95500.00")


def test_component_depreciation():
    subledger = FixedAssetSubledger()
    comp_engine = AssetComponent(
        component_id="COMP-ENG",
        description="Aircraft Engine",
        cost=Decimal("60000.00"),
        useful_life_months=60,
    )
    comp_body = AssetComponent(
        component_id="COMP-BODY",
        description="Airframe",
        cost=Decimal("120000.00"),
        useful_life_months=120,
    )
    asset, _ = subledger.register_asset(
        description="Corporate Transport Jet",
        cost=Decimal("180000.00"),
        useful_life_months=120,
        capitalization_date="2026-01-01",
        depreciation_method=DepreciationMethod.COMPONENT,
        components=[comp_engine, comp_body],
    )
    assert asset is not None

    # Engine: 60000 / 60 = 1000; Body: 120000 / 120 = 1000 -> Total = 2000
    dep_entry = subledger.calculate_monthly_depreciation(asset.asset_id, "2026-01-31")
    assert dep_entry is not None
    assert dep_entry.is_balanced
    assert dep_entry.total_debits == Decimal("2000.00")


def test_ias_36_impairment_test():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Specialized Tooling",
        cost=Decimal("50000.00"),
        useful_life_months=50,
        capitalization_date="2026-01-01",
    )
    assert asset is not None

    # Recoverable amount dropped to 35,000 (impairment of 15,000)
    imp_entry = subledger.test_impairment(asset.asset_id, Decimal("35000.00"), "2026-06-30")
    assert imp_entry is not None
    assert imp_entry.is_balanced
    assert imp_entry.total_debits == Decimal("15000.00")
    assert imp_entry.lines[0].account_code == "65100"
    assert asset.status == AssetStatus.IMPAIRED
    assert asset.carrying_value == Decimal("35000.00")


def test_asset_retirement_with_gain():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Corporate Executive Car",
        cost=Decimal("30000.00"),
        useful_life_months=30,
        capitalization_date="2026-01-01",
    )
    assert asset is not None
    subledger.calculate_monthly_depreciation(asset.asset_id, "2026-01-31")  # dep = 1000, NBV = 29000

    # Sell for 32,000 -> Gain = 3000
    ret_entry = subledger.retire_asset(asset.asset_id, Decimal("32000.00"), "2026-02-15")
    assert ret_entry is not None
    assert ret_entry.is_balanced
    assert asset.status == AssetStatus.RETIRED
    assert any(line.account_code == "48000" and line.amount == Decimal("3000.00") for line in ret_entry.lines)


def test_asset_retirement_with_loss():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Office Photocopier",
        cost=Decimal("10000.00"),
        useful_life_months=20,
        capitalization_date="2026-01-01",
    )
    assert asset is not None
    # Scrap for 2,000 without prior dep -> Loss = 8000
    ret_entry = subledger.retire_asset(asset.asset_id, Decimal("2000.00"), "2026-01-15")
    assert ret_entry is not None
    assert ret_entry.is_balanced
    assert any(line.account_code == "65200" and line.amount == Decimal("8000.00") for line in ret_entry.lines)


def test_ias_16_revaluation_model():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Headquarters Real Estate",
        cost=Decimal("500000.00"),
        useful_life_months=360,
        capitalization_date="2026-01-01",
        asset_class=AssetClass.BUILDING,
    )
    assert asset is not None

    rev_entry = subledger.revalue_asset(asset.asset_id, Decimal("650000.00"), "2026-12-31")
    assert rev_entry is not None
    assert rev_entry.is_balanced
    assert rev_entry.total_debits == Decimal("150000.00")
    assert asset.carrying_value == Decimal("650000.00")


def test_zombie_asset_mutator():
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Scrapped Generator",
        cost=Decimal("12000.00"),
        useful_life_months=12,
        capitalization_date="2026-01-01",
    )
    assert asset is not None
    subledger.retire_asset(asset.asset_id, Decimal("0.00"), "2026-01-15")
    assert asset.status == AssetStatus.RETIRED

    zombie_entry = ZombieAssetMutator.mutate(subledger, asset.asset_id, "2026-02-28", Decimal("1000.00"))
    assert zombie_entry is not None
    assert zombie_entry.is_balanced
    assert zombie_entry.is_anomaly
    assert "ANOM_ZOMBIE_ASSET_DEPRECIATION" in zombie_entry.anomaly_ids


def test_capitalization_threshold_evasion_mutator():
    subledger = FixedAssetSubledger(capitalization_threshold=Decimal("2500.00"))
    entries = CapitalizationThresholdEvasionMutator.mutate(
        subledger=subledger,
        total_expenditure=Decimal("6000.00"),
        splits=3,
        period_date="2026-09-01",
    )
    assert len(entries) == 3
    for entry in entries:
        assert entry.is_balanced
        assert entry.is_anomaly
        assert "ANOM_CAPITALIZATION_THRESHOLD_EVASION" in entry.anomaly_ids
        assert entry.total_debits == Decimal("2000.00")  # Each below 2500 threshold


def test_asset_retirement_with_revaluation_surplus():
    """Verify retirement of an asset with revaluation surplus maintains strict double-entry balance."""
    subledger = FixedAssetSubledger()
    asset, _ = subledger.register_asset(
        description="Headquarters Building",
        cost=Decimal("100000.00"),
        useful_life_months=240,
        capitalization_date="2026-01-01",
    )
    assert asset is not None

    # Revalue asset upward by 25,000 to fair value 125,000
    rev_entry = subledger.revalue_asset(asset.asset_id, Decimal("125000.00"), "2026-06-30")
    assert rev_entry is not None
    assert rev_entry.is_balanced
    assert asset.revaluation_surplus == Decimal("25000.00")

    # Retire asset for proceeds of 130,000 (gain of 5,000 over 125,000 carrying value)
    ret_entry = subledger.retire_asset(asset.asset_id, Decimal("130000.00"), "2026-12-31")
    assert ret_entry is not None
    assert ret_entry.is_balanced
    assert ret_entry.fiscal_year == 2026
    assert ret_entry.fiscal_period == 12

