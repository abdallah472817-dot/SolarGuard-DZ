"""Unit tests for custom CSV/Excel ingestion, daily disaggregation, Plotly serialization, and exports."""

from __future__ import annotations

import io
import numpy as np
import openpyxl
import pandas as pd

from solarguard.analytics import (
    compute_executive_kpis,
    compute_load_diagnostics,
    compute_pv_loss_waterfall,
    resample_energy_frame,
    simulate_custom_sizing,
)
from solarguard.anomaly import detect_energy_anomalies
from solarguard.charts import (
    chart_algeria_solar_map,
    chart_anomaly_timeline,
    chart_battery_dispatch_comparison,
    chart_cashflow_projection,
    chart_diurnal_profiles,
    chart_energy_balance_timeline,
    chart_energy_sankey,
    chart_feature_importance,
    chart_fft_spectrum,
    chart_forecast_horizon,
    chart_irradiance_power_curve,
    chart_load_duration_curve,
    chart_load_heatmap,
    chart_monthly_bills,
    chart_pv_waterfall,
    chart_tou_breakdown,
)
from solarguard.config import TARIFF_PROFILES
from solarguard.data_generator import generate_facility_telemetry
from solarguard.data_loader import (
    auto_detect_mapping,
    normalize_custom_dataset,
    read_uploaded_table,
)
from solarguard.economics import compute_lifecycle_economics
from solarguard.exporter import (
    build_excel_audit_workbook,
    build_html_audit_report,
    build_sample_csv_template,
)
from solarguard.forecasting import run_energy_forecast


def test_french_semicolon_csv_and_unmapped_fallback():
    ts = pd.date_range("2026-06-01", periods=72, freq="1h")
    lines = ["Horodatage;Consommation_kW;Production_Solaire"]
    for i, t in enumerate(ts):
        ld = f"{45.5 + (i % 12) * 2.1:.2f}".replace(".", ",")
        pv = f"{max(0.0, 30.0 - abs((i % 24) - 12) * 5.0):.2f}".replace(".", ",")
        lines.append(f"{t.strftime('%Y-%m-%d %H:%M')};{ld};{pv}")
    csv_bytes = "\n".join(lines).encode("utf-8")

    raw = read_uploaded_table(csv_bytes, "releve_sonelgaz.csv")
    mapping = auto_detect_mapping(list(raw.columns))
    norm_df, meta = normalize_custom_dataset(raw, mapping)
    assert len(norm_df) == 72
    assert meta["completeness_pct"] == 100.0
    assert norm_df["load_kw"].mean() > 40.0

    # Unmapped comma-decimal string column fallback
    obscure = pd.DataFrame({"Date_Ref": ts, "Canal_Mesure_A": ["112,5"] * 72})
    norm_obs, _ = normalize_custom_dataset(obscure, {"timestamp": "Date_Ref"})
    assert np.allclose(norm_obs["load_kw"], 112.5)


def test_daily_csv_disaggregates_cleanly_without_night_pv():
    days = pd.date_range("2026-07-01", periods=10, freq="1D")
    daily_df = pd.DataFrame(
        {
            "Date": days,
            "Daily_Load_kWh": 2400.0,
            "Daily_PV_kWh": 1200.0,
        }
    )
    mapping = auto_detect_mapping(list(daily_df.columns))
    norm_df, meta = normalize_custom_dataset(daily_df, mapping)

    assert meta["is_daily_disaggregated"] is True
    assert len(norm_df) == 240
    # Total 10-day energy conserved (10 * 2400 = 24,000 kWh; 10 * 1200 = 12,000 kWh)
    assert np.isclose(norm_df["load_kw"].sum(), 24000.0, rtol=0.01)
    assert np.isclose(norm_df["pv_ac_kw"].sum(), 12000.0, rtol=0.01)
    # Nighttime hours (00:00..05:00) must have strictly 0 PV!
    night_pv = norm_df.loc[norm_df["timestamp"].dt.hour < 6, "pv_ac_kw"]
    assert np.allclose(night_pv, 0.0)


def test_excel_upload_and_template_roundtrip():
    tpl_bytes = build_sample_csv_template()
    raw_tpl = read_uploaded_table(tpl_bytes, "template.csv")
    norm_tpl, _ = normalize_custom_dataset(raw_tpl, auto_detect_mapping(list(raw_tpl.columns)))
    assert len(norm_tpl) == 48

    ts = pd.date_range("2026-03-01", periods=48, freq="1h")
    sample = pd.DataFrame({"Date": ts, "Demand_kW": 100.0})
    buf = io.BytesIO()
    sample.to_excel(buf, index=False)

    raw = read_uploaded_table(buf.getvalue(), "meter_log.xlsx")
    norm_df, meta = normalize_custom_dataset(raw, auto_detect_mapping(list(raw.columns)))
    assert len(norm_df) == 48
    assert meta["inferred_pv_kwp"] == 0.0
    assert (norm_df["pv_ac_kw"] == 0.0).all()


def test_lifecycle_economics_xss_escaping_and_styled_excel():
    df = generate_facility_telemetry("oran_industrial", "Oran", year=2026).iloc[:1440]
    tariff = TARIFF_PROFILES["intl_usd_tou"]
    kpis = compute_executive_kpis(df, 250.0, 300.0, tariff)
    econ = compute_lifecycle_economics(
        df=df,
        tariff=tariff,
        pv_capacity_kwp=250.0,
        battery_capacity_kwh=300.0,
        pv_capex_per_kwp=tariff.default_pv_capex_per_kwp,
        ess_capex_per_kwh=tariff.default_ess_capex_per_kwh,
    )

    assert econ["net_capex"] > 0
    assert 0 < econ["lcoe"] < econ["hybrid_lcoe"]
    assert econ["irr_pct"] is not None
    assert len(econ["cashflow_df"]) == 26

    anom = detect_energy_anomalies(df, 250.0, 0.025, 0.16)
    xlsx_bytes = build_excel_audit_workbook(
        site_label="Oran Industrial Plant",
        kpis=kpis,
        monthly_df=econ["monthly_df"],
        incidents_df=anom["incidents_df"],
        cashflow_df=econ["cashflow_df"],
        annotated_df=anom["annotated_df"],
        currency_symbol="$",
    )
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    assert set(wb.sheetnames) == {
        "Executive_KPIs",
        "Monthly_Billing",
        "SolarGuard_Faults",
        "CashFlow_25Yr",
        "Daily_Summary",
    }
    assert wb["Executive_KPIs"].freeze_panes == "A2"

    html_doc = build_html_audit_report(
        site_label="<script>alert('xss')</script>",
        wilaya_name="Oran",
        kpis=kpis,
        econ=econ,
        anom_summary=anom["summary"],
        incidents_df=anom["incidents_df"],
        currency_symbol="$",
    )
    assert "<script>alert" not in html_doc
    assert "&lt;script&gt;" in html_doc


def test_all_16_plotly_charts_serialize_to_json():
    df = generate_facility_telemetry("oran_industrial", "Oran", year=2026).iloc[:720]
    tariff = TARIFF_PROFILES["sonelgaz_mt_tou"]
    kpis = compute_executive_kpis(df, 250.0, 300.0, tariff)
    wf = compute_pv_loss_waterfall(df)
    anom = detect_energy_anomalies(df, 250.0, 0.025, 6.0)
    diag = compute_load_diagnostics(df)
    fc = run_energy_forecast(df, "load_kw", 48)
    sim = simulate_custom_sizing(df, 250.0, 350.0, 450.0, 180.0)
    econ = compute_lifecycle_economics(df, tariff, 250.0, 300.0, 118000.0, 46000.0)

    figs = [
        chart_energy_balance_timeline(resample_energy_frame(df, "1D"), "1D"),
        chart_energy_sankey(kpis),
        chart_algeria_solar_map("Oran"),
        chart_pv_waterfall(wf),
        chart_irradiance_power_curve(anom["annotated_df"]),
        chart_anomaly_timeline(anom["annotated_df"]),
        chart_load_heatmap(diag["heatmap_pivot"]),
        chart_load_duration_curve(diag["ldc_df"]),
        chart_diurnal_profiles(diag["diurnal_df"]),
        chart_tou_breakdown(diag["tou_df"]),
        chart_fft_spectrum(diag["fft_df"]),
        chart_forecast_horizon(fc["backtest_df"], fc["forecast_df"], "Load kW", "#0284C7"),
        chart_feature_importance(fc["importance_df"]),
        chart_battery_dispatch_comparison(df, sim),
        chart_cashflow_projection(econ["cashflow_df"], "DA"),
        chart_monthly_bills(econ["monthly_df"], "DA"),
    ]
    for fig in figs:
        payload = fig.to_json()
        assert len(payload) > 100
