"""Unit tests for SolarGuard anomaly detection (including Load-Only guard) and causal ML forecasting."""

from __future__ import annotations

import numpy as np
import pandas as pd

from solarguard.anomaly import PV_FAULT_CATEGORIES, detect_energy_anomalies
from solarguard.data_generator import generate_facility_telemetry
from solarguard.data_loader import auto_detect_mapping, normalize_custom_dataset
from solarguard.forecasting import run_energy_forecast


def test_anomaly_detection_identifies_injected_faults():
    df = generate_facility_telemetry("oran_industrial", "Oran", year=2026)
    res = detect_energy_anomalies(df, pv_capacity_kwp=250.0, contamination=0.025, avg_tariff_rate=6.5)

    summary = res["summary"]
    incidents = res["incidents_df"]
    assert summary["flagged_hours"] > 20
    assert summary["incident_count"] >= 3
    assert summary["recoverable_pv_kwh"] > 100.0
    assert not incidents.empty
    assert "PV String / Inverter Dropout" in set(incidents["Category"])


def test_load_only_dataset_triggers_zero_false_pv_faults():
    ts = pd.date_range("2026-05-01", periods=240, freq="1h")
    raw = pd.DataFrame({"timestamp": ts, "load_kw": 80.0 + 20.0 * np.sin(np.pi * ts.hour / 12.0)})
    norm_df, meta = normalize_custom_dataset(raw, auto_detect_mapping(list(raw.columns)))
    assert meta["inferred_pv_kwp"] == 0.0

    anom = detect_energy_anomalies(norm_df, pv_capacity_kwp=meta["inferred_pv_kwp"], contamination=0.025)
    assert anom["summary"]["recoverable_pv_kwh"] == 0.0
    flagged_cats = set(anom["annotated_df"]["anomaly_type"])
    assert flagged_cats.isdisjoint(set(PV_FAULT_CATEGORIES))


def test_ml_forecaster_strictly_causal_no_future_leakage():
    df = generate_facility_telemetry("oran_industrial", "Oran", year=2026).iloc[:1000].copy()

    res_clean = run_energy_forecast(df, target_col="pv_ac_kw", horizon_hours=48)
    assert res_clean["metrics"]["r2"] > 0.65

    # Corrupt future pyranometer & temperature inside holdout window and prove backtest predictions are unchanged!
    df_corrupted = df.copy()
    holdout_n = res_clean["metrics"]["holdout_hours"]
    df_corrupted.iloc[-holdout_n:, df_corrupted.columns.get_loc("irradiance_wm2")] = 9999.0
    df_corrupted.iloc[-holdout_n:, df_corrupted.columns.get_loc("ambient_temp_c")] = 99.0

    res_corrupt = run_energy_forecast(df_corrupted, target_col="pv_ac_kw", horizon_hours=48)
    assert np.allclose(
        res_clean["backtest_df"]["predicted_p50"],
        res_corrupt["backtest_df"]["predicted_p50"],
    )


def test_ml_forecaster_quantiles_and_zero_pv_fastpath():
    df = generate_facility_telemetry("oran_industrial", "Oran", year=2026).iloc[:1200]

    fc_load = run_energy_forecast(df, target_col="load_kw", horizon_hours=48)
    assert fc_load["metrics"]["r2"] > 0.60
    f_df = fc_load["forecast_df"]
    assert len(f_df) == 48
    assert np.all(f_df["forecast_p10"] <= f_df["forecast_p50"] + 1e-6)
    assert np.all(f_df["forecast_p50"] <= f_df["forecast_p90"] + 1e-6)

    # Constant-zero PV fast path on Load-Only frame
    zero_pv_df = df.copy()
    zero_pv_df["pv_ac_kw"] = 0.0
    fc_zero = run_energy_forecast(zero_pv_df, target_col="pv_ac_kw", horizon_hours=24)
    assert np.allclose(fc_zero["forecast_df"]["forecast_p50"], 0.0)
