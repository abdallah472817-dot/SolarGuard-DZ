"""Unit tests for physics generation, signed waterfall conservation, billing reconciliation, and sizing."""

from __future__ import annotations

import numpy as np

from solarguard.analytics import (
    TOU_ORDER,
    compute_executive_kpis,
    compute_load_diagnostics,
    compute_monthly_billing_table,
    compute_pv_loss_waterfall,
    recommend_optimal_sizing,
    simulate_custom_sizing,
)
from solarguard.config import TARIFF_PROFILES
from solarguard.data_generator import generate_facility_telemetry


def test_energy_conservation_and_solar_physics():
    df = generate_facility_telemetry("oran_industrial", "Oran", year=2026)
    assert len(df) == 8760

    night_pv = df.loc[df["irradiance_wm2"] == 0.0, "pv_ac_kw"]
    assert np.allclose(night_pv, 0.0)

    supplied = df["direct_pv_kw"] + df["battery_to_load_kw"] + df["grid_import_kw"]
    assert np.allclose(df["load_kw"], supplied, atol=0.02)

    pv_used = df["direct_pv_kw"] + df["pv_to_battery_kw"] + df["grid_export_kw"]
    assert np.allclose(df["pv_ac_kw"], pv_used, atol=0.02)

    assert df["battery_soc_pct"].min() >= 0.0
    assert df["battery_soc_pct"].max() <= 100.0


def test_cold_climate_signed_waterfall_exact_identity():
    # January in Setif (1,096m elevation) has cold sunny mornings where cell_temp < 25°C
    df_jan = generate_facility_telemetry("constantine_hospital", "Setif", year=2026).iloc[:744]
    wf = compute_pv_loss_waterfall(df_jan)
    assert len(wf) == 6

    stc_kwh = float(wf.loc[wf["stage"] == "Theoretical STC Yield", "kwh"].iloc[0])
    rel_sum = float(wf.loc[wf["measure"] == "relative", "kwh"].sum())
    net_ac = float(wf.loc[wf["stage"] == "Net AC Energy Delivered", "kwh"].iloc[0])
    assert abs((stc_kwh + rel_sum) - net_ac) < 1e-6


def test_billing_reconciliation_between_kpis_and_monthly_table():
    df = generate_facility_telemetry("oran_industrial", "Oran", year=2026)
    tariff = TARIFF_PROFILES["sonelgaz_mt_tou"]

    # Full year reconciliation
    kpis_full = compute_executive_kpis(df, 250.0, 300.0, tariff)
    m_full = compute_monthly_billing_table(df, tariff)
    assert np.isclose(kpis_full["baseline_bill"], m_full["baseline_bill"].sum(), atol=1e-4)
    assert np.isclose(kpis_full["actual_net_bill"], m_full["solarguard_bill"].sum(), atol=1e-4)
    assert np.isclose(kpis_full["net_savings"], m_full["net_savings"].sum(), atol=1e-4)

    # Partial 10-day window reconciliation
    df_10d = df.iloc[4000:4240]
    kpis_10d = compute_executive_kpis(df_10d, 250.0, 300.0, tariff)
    m_10d = compute_monthly_billing_table(df_10d, tariff)
    assert np.isclose(kpis_10d["net_savings"], m_10d["net_savings"].sum(), atol=1e-4)


def test_saharan_vs_coastal_insolation():
    df_algiers = generate_facility_telemetry("algiers_campus", "Algiers", year=2026)
    df_adrar = generate_facility_telemetry("algiers_campus", "Adrar", year=2026)

    poa_algiers = df_algiers["irradiance_wm2"].sum() / 1000.0
    poa_adrar = df_adrar["irradiance_wm2"].sum() / 1000.0
    assert poa_adrar > poa_algiers * 1.25


def test_kpis_tou_order_and_load_diagnostics():
    df = generate_facility_telemetry("ghardaia_microgrid", "Ghardaia", year=2026)
    tariff = TARIFF_PROFILES["sonelgaz_mt_tou"]
    kpis = compute_executive_kpis(df, pv_capacity_kwp=150.0, battery_capacity_kwh=400.0, tariff=tariff)

    assert 65.0 <= kpis["performance_ratio_pct"] <= 95.0
    assert 0.0 < kpis["self_sufficiency_pct"] <= 100.0
    assert kpis["co2_avoided_tons"] > 50.0
    assert kpis["net_savings"] > 0.0

    diag = compute_load_diagnostics(df)
    assert diag["tou_df"]["tou_band"].tolist() == TOU_ORDER
    ldc = diag["ldc_df"]["facility_load_kw"].to_numpy()
    assert np.all(np.diff(ldc) <= 1e-9)


def test_prescriptive_sizing_and_battery_autarky():
    df = generate_facility_telemetry("algiers_campus", "Algiers", year=2026).iloc[:720]
    tariff = TARIFF_PROFILES["sonelgaz_bt_comm"]

    for strat in ("balanced", "peak_shaving", "zero_export"):
        rec = recommend_optimal_sizing(df, strategy=strat)
        assert rec["pv_kwp"] >= 5.0
        assert rec["ess_kwh"] >= 0.0
        assert rec["ess_kw"] >= 10.0

    sim_no_batt = simulate_custom_sizing(df, 85.0, 120.0, 0.0, 0.0)
    sim_with_batt = simulate_custom_sizing(df, 85.0, 120.0, 300.0, 100.0)

    k0 = compute_executive_kpis(sim_no_batt, 120.0, 0.0, tariff)
    k1 = compute_executive_kpis(sim_with_batt, 120.0, 300.0, tariff)
    assert k1["self_sufficiency_pct"] > k0["self_sufficiency_pct"]
    assert k1["grid_import_kwh"] < k0["grid_import_kwh"]
