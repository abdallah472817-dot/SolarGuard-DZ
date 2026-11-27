"""Core energy engineering analytics: IEC 61724 PV metrics, load diagnostics, FFT, and sizing."""

from __future__ import annotations

from typing import Any, Dict
import numpy as np
import pandas as pd
from scipy.fft import rfft, rfftfreq

from solarguard.config import GRID_CO2_KG_PER_KWH, TariffScheme
from solarguard.data_generator import dispatch_microgrid_arrays

TOU_ORDER = [
    "Off-Peak (23h-06h)",
    "Shoulder (06h-17h, 21h-23h)",
    "Evening Peak (17h-21h)",
]


def hourly_tou_rates(timestamps: pd.Series, tariff: TariffScheme) -> np.ndarray:
    """Return hourly import tariff rate array based on Algerian/C&I Time-of-Use bands."""
    h = timestamps.dt.hour.to_numpy()
    return np.where(
        (h >= 17) & (h < 21),
        tariff.peak_rate,
        np.where((h >= 23) | (h < 6), tariff.off_peak_rate, tariff.shoulder_rate),
    )


def tou_band_labels(timestamps: pd.Series) -> np.ndarray:
    """Classify each hour into Off-Peak, Shoulder, or Evening Peak tariff periods."""
    h = timestamps.dt.hour.to_numpy()
    return np.where(
        (h >= 17) & (h < 21),
        "Evening Peak (17h-21h)",
        np.where((h >= 23) | (h < 6), "Off-Peak (23h-06h)", "Shoulder (06h-17h, 21h-23h)"),
    )


def compute_monthly_billing_table(df: pd.DataFrame, tariff: TariffScheme) -> pd.DataFrame:
    """Compute monthly electricity bills With vs Without SolarGuard PV+ESS (exact monthly peak billing)."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "load_kwh",
                "pv_kwh",
                "grid_import_kwh",
                "grid_export_kwh",
                "peak_load_kw",
                "net_peak_kw",
                "baseline_bill",
                "solarguard_bill",
                "net_savings",
            ]
        )

    work = df.copy()
    work["rate"] = hourly_tou_rates(work["timestamp"], tariff)
    work["base_energy_cost"] = work["load_kw"] * work["rate"]
    work["actual_import_cost"] = work["grid_import_kw"] * work["rate"]
    work["export_credit"] = work["grid_export_kw"] * tariff.export_feed_in

    monthly = (
        work.set_index("timestamp")
        .resample("ME")
        .agg(
            hours_present=("load_kw", "count"),
            load_kwh=("load_kw", "sum"),
            pv_kwh=("pv_ac_kw", "sum"),
            grid_import_kwh=("grid_import_kw", "sum"),
            grid_export_kwh=("grid_export_kw", "sum"),
            peak_load_kw=("load_kw", "max"),
            net_peak_kw=("grid_import_kw", "max"),
            base_energy_cost=("base_energy_cost", "sum"),
            actual_import_cost=("actual_import_cost", "sum"),
            export_credit=("export_credit", "sum"),
        )
        .reset_index()
    )
    # Filter empty resampled months (if dataset has multi-month gaps)
    monthly = monthly.loc[monthly["hours_present"] > 0].reset_index(drop=True)

    full_month_hours = monthly["timestamp"].dt.days_in_month * 24.0
    proration = (monthly["hours_present"] / full_month_hours).clip(lower=0.05, upper=1.0)

    monthly["month"] = monthly["timestamp"].dt.strftime("%Y-%m")
    monthly["baseline_bill"] = (
        monthly["base_energy_cost"]
        + monthly["peak_load_kw"] * tariff.demand_charge_per_kw_month * proration
    )
    monthly["solarguard_bill"] = (
        monthly["actual_import_cost"]
        + monthly["net_peak_kw"] * tariff.demand_charge_per_kw_month * proration
        - monthly["export_credit"]
    )
    monthly["net_savings"] = monthly["baseline_bill"] - monthly["solarguard_bill"]
    return monthly


def compute_executive_kpis(
    df: pd.DataFrame,
    pv_capacity_kwp: float,
    battery_capacity_kwh: float,
    tariff: TariffScheme,
) -> Dict[str, Any]:
    """Compute comprehensive IEC 61724 PV, electrical demand, carbon, and reconciled tariff KPIs."""
    n_hours = max(len(df), 1)
    scale_annual = 8760.0 / n_hours

    total_pv_kwh = float(df["pv_ac_kw"].sum())
    total_load_kwh = float(df["load_kw"].sum())
    grid_import_kwh = float(df["grid_import_kw"].sum())
    grid_export_kwh = float(df["grid_export_kw"].sum())
    direct_pv_kwh = float(df["direct_pv_kw"].sum())
    batt_to_load_kwh = float(df["battery_to_load_kw"].sum())
    pv_to_batt_kwh = float(df["pv_to_battery_kw"].sum())

    self_sufficiency_pct = (
        100.0 * max(0.0, total_load_kwh - grid_import_kwh) / total_load_kwh
        if total_load_kwh > 0
        else 0.0
    )
    self_consumption_pct = (
        100.0 * min(total_pv_kwh, direct_pv_kwh + pv_to_batt_kwh) / total_pv_kwh
        if total_pv_kwh > 0
        else 0.0
    )

    poa_kwh_m2 = float(df["irradiance_wm2"].sum()) / 1000.0
    has_pv = pv_capacity_kwp > 0 and total_pv_kwh > 0
    eff_kwp = max(float(pv_capacity_kwp), 0.001)
    specific_yield = total_pv_kwh / eff_kwp if has_pv else 0.0
    annualized_specific_yield = specific_yield * scale_annual

    if has_pv and poa_kwh_m2 > 0.5:
        performance_ratio_pct = float(np.clip(100.0 * specific_yield / poa_kwh_m2, 0.0, 100.0))
    else:
        performance_ratio_pct = 0.0

    capacity_factor_pct = (
        100.0 * total_pv_kwh / (eff_kwp * n_hours) if has_pv else 0.0
    )

    peak_load_kw = float(df["load_kw"].max()) if len(df) else 0.0
    avg_load_kw = float(df["load_kw"].mean()) if len(df) else 0.0
    baseload_p10_kw = float(df["load_kw"].quantile(0.10)) if len(df) else 0.0
    load_factor_pct = 100.0 * avg_load_kw / peak_load_kw if peak_load_kw > 0 else 0.0
    avg_pf = float(df["power_factor"].mean()) if "power_factor" in df.columns else 0.90
    peak_apparent_kva = peak_load_kw / max(avg_pf, 0.5)
    net_grid_peak_kw = float(df["grid_import_kw"].max()) if len(df) else 0.0

    # Exact monthly-reconciled billing & savings
    monthly_bills = compute_monthly_billing_table(df, tariff)
    baseline_bill = float(monthly_bills["baseline_bill"].sum())
    actual_net_bill = float(monthly_bills["solarguard_bill"].sum())
    export_revenue = float(monthly_bills["export_credit"].sum()) if "export_credit" in monthly_bills.columns else 0.0
    net_savings = baseline_bill - actual_net_bill
    savings_pct = 100.0 * net_savings / baseline_bill if baseline_bill > 0 else 0.0

    # Carbon avoidance
    clean_displaced_kwh = direct_pv_kwh + batt_to_load_kwh + grid_export_kwh
    co2_avoided_tons = (clean_displaced_kwh * GRID_CO2_KG_PER_KWH) / 1000.0
    equiv_trees = co2_avoided_tons * 45.5

    # Compact sparklines for st.metric cards
    daily = (
        df.set_index("timestamp")
        .resample("1D")
        .agg(
            pv_kwh=("pv_ac_kw", "sum"),
            load_kwh=("load_kw", "sum"),
            imp_kwh=("grid_import_kw", "sum"),
            poa=("irradiance_wm2", lambda s: s.sum() / 1000.0),
        )
    )
    spark_df = daily.iloc[:: max(len(daily) // 36, 1)] if len(daily) > 45 else daily

    spark_autarky = (
        100.0
        * (spark_df["load_kwh"] - spark_df["imp_kwh"]).clip(lower=0.0)
        / spark_df["load_kwh"].replace(0, np.nan)
    ).fillna(0.0)
    spark_pr = (
        (100.0 * (spark_df["pv_kwh"] / eff_kwp) / spark_df["poa"].replace(0, np.nan))
        .clip(0.0, 100.0)
        .fillna(0.0)
        if has_pv
        else pd.Series(0.0, index=spark_df.index)
    )

    return {
        "hours": n_hours,
        "pv_capacity_kwp": pv_capacity_kwp,
        "battery_capacity_kwh": battery_capacity_kwh,
        "total_pv_kwh": total_pv_kwh,
        "total_load_kwh": total_load_kwh,
        "grid_import_kwh": grid_import_kwh,
        "grid_export_kwh": grid_export_kwh,
        "direct_pv_kwh": direct_pv_kwh,
        "batt_to_load_kwh": batt_to_load_kwh,
        "pv_to_batt_kwh": pv_to_batt_kwh,
        "self_sufficiency_pct": self_sufficiency_pct,
        "self_consumption_pct": self_consumption_pct,
        "poa_kwh_m2": poa_kwh_m2,
        "specific_yield_kwh_kwp": specific_yield,
        "annualized_specific_yield": annualized_specific_yield,
        "performance_ratio_pct": performance_ratio_pct,
        "capacity_factor_pct": capacity_factor_pct,
        "peak_load_kw": peak_load_kw,
        "net_grid_peak_kw": net_grid_peak_kw,
        "peak_shaving_kw": max(0.0, peak_load_kw - net_grid_peak_kw),
        "avg_load_kw": avg_load_kw,
        "baseload_p10_kw": baseload_p10_kw,
        "load_factor_pct": load_factor_pct,
        "avg_power_factor": avg_pf,
        "peak_apparent_kva": peak_apparent_kva,
        "avg_cell_temp_day_c": float(df.loc[df["irradiance_wm2"] > 100, "cell_temp_c"].mean())
        if (df["irradiance_wm2"] > 100).any()
        else float(df["cell_temp_c"].mean()),
        "avg_soiling_pct": float(df["soiling_loss_pct"].mean()),
        "baseline_bill": baseline_bill,
        "actual_net_bill": actual_net_bill,
        "export_revenue": export_revenue,
        "net_savings": net_savings,
        "savings_pct": savings_pct,
        "co2_avoided_tons": co2_avoided_tons,
        "equiv_trees": equiv_trees,
        "spark_pv": spark_df["pv_kwh"].round(1).tolist(),
        "spark_load": spark_df["load_kwh"].round(1).tolist(),
        "spark_autarky": spark_autarky.round(1).tolist(),
        "spark_pr": spark_pr.round(1).tolist(),
    }


def compute_pv_loss_waterfall(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize exact signed PV conversion & loss stages in kWh and % of STC theoretical."""
    stc_kwh = float(df["pv_stc_kw"].sum())
    net_ac_kwh = float(df["pv_ac_kw"].sum())
    if stc_kwh <= 0.0:
        return pd.DataFrame(
            [
                ("Theoretical STC Yield", 0.0, 0.0, "absolute"),
                ("Thermal Effect", 0.0, 0.0, "relative"),
                ("Dust & Soiling Loss", 0.0, 0.0, "relative"),
                ("Wiring & Inverter Loss", 0.0, 0.0, "relative"),
                ("Clipping & Fault Loss", 0.0, 0.0, "relative"),
                ("Net AC Energy Delivered", 0.0, 0.0, "total"),
            ],
            columns=["stage", "kwh", "share_pct", "measure"],
        )

    temp_delta = -float(df["loss_temp_kw"].sum())  # negative = heat loss, positive = cold gain
    soil_delta = -float(df["loss_soiling_kw"].sum())
    sys_delta = -float(df["loss_system_kw"].sum())
    clip_fault_delta = net_ac_kwh - (stc_kwh + temp_delta + soil_delta + sys_delta)

    rows = [
        ("Theoretical STC Yield", stc_kwh, 100.0, "absolute"),
        ("Thermal Effect", temp_delta, 100.0 * temp_delta / stc_kwh, "relative"),
        ("Dust & Soiling Loss", soil_delta, 100.0 * soil_delta / stc_kwh, "relative"),
        ("Wiring & Inverter Loss", sys_delta, 100.0 * sys_delta / stc_kwh, "relative"),
        ("Clipping & Fault Loss", clip_fault_delta, 100.0 * clip_fault_delta / stc_kwh, "relative"),
        ("Net AC Energy Delivered", net_ac_kwh, 100.0 * net_ac_kwh / stc_kwh, "total"),
    ]
    return pd.DataFrame(rows, columns=["stage", "kwh", "share_pct", "measure"])


def compute_load_diagnostics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute Load Duration Curve, ordered ToU breakdown, 24x12 heatmap, diurnal bands, and FFT."""
    sorted_load = np.sort(df["load_kw"].to_numpy())[::-1]
    sorted_net_grid = np.sort(df["grid_import_kw"].to_numpy())[::-1]
    pct_exceeded = np.linspace(0.0, 100.0, len(sorted_load))
    step = max(len(sorted_load) // 450, 1)
    ldc_df = pd.DataFrame(
        {
            "pct_hours": pct_exceeded[::step],
            "facility_load_kw": sorted_load[::step],
            "net_grid_import_kw": sorted_net_grid[::step],
        }
    )

    bands = pd.Categorical(tou_band_labels(df["timestamp"]), categories=TOU_ORDER, ordered=True)
    tou_df = (
        df.assign(tou_band=bands)
        .groupby("tou_band", observed=False, as_index=False)
        .agg(
            hours=("load_kw", "count"),
            load_kwh=("load_kw", "sum"),
            pv_kwh=("pv_ac_kw", "sum"),
            grid_import_kwh=("grid_import_kw", "sum"),
            battery_discharge_kwh=("battery_to_load_kw", "sum"),
        )
        .sort_values("tou_band")
        .reset_index(drop=True)
    )
    tou_df["tou_band"] = tou_df["tou_band"].astype(str)
    tou_df["load_share_pct"] = 100.0 * tou_df["load_kwh"] / max(float(tou_df["load_kwh"].sum()), 1.0)

    hm_work = df.assign(
        hour=df["timestamp"].dt.hour,
        month_num=df["timestamp"].dt.month,
    )
    heatmap_pivot = hm_work.pivot_table(
        index="month_num", columns="hour", values="load_kw", aggfunc="mean"
    )
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    heatmap_pivot.index = [month_names.get(int(m), str(m)) for m in heatmap_pivot.index]

    dow = df["timestamp"].dt.day_of_week
    day_type = np.where((dow == 4) | (dow == 5), "Weekend (Fri-Sat)", "Workweek (Sun-Thu)")
    diurnal_df = (
        df.assign(hour=df["timestamp"].dt.hour, day_type=day_type)
        .groupby(["day_type", "hour"], as_index=False)
        .agg(
            mean_load_kw=("load_kw", "mean"),
            p10_load_kw=("load_kw", lambda s: float(np.percentile(s, 10))),
            p90_load_kw=("load_kw", lambda s: float(np.percentile(s, 90))),
            mean_pv_kw=("pv_ac_kw", "mean"),
        )
    )

    sig = df["load_kw"].to_numpy(dtype=np.float64)
    sig_centered = sig - np.mean(sig)
    if len(sig_centered) >= 48 and np.std(sig_centered) > 1e-6:
        yf = np.abs(rfft(sig_centered)) / len(sig_centered)
        xf = rfftfreq(len(sig_centered), d=1.0)
        valid = (xf > 1.0 / 240.0) & (xf <= 0.5)
        periods_hours = 1.0 / xf[valid]
        amps = yf[valid] * 2.0
        fft_df = (
            pd.DataFrame({"period_hours": periods_hours, "amplitude_kw": amps})
            .sort_values("amplitude_kw", ascending=False)
            .head(60)
            .sort_values("period_hours")
        )
    else:
        fft_df = pd.DataFrame({"period_hours": [12.0, 24.0, 168.0], "amplitude_kw": [0.0, 0.0, 0.0]})

    return {
        "ldc_df": ldc_df,
        "tou_df": tou_df,
        "heatmap_pivot": heatmap_pivot,
        "diurnal_df": diurnal_df,
        "fft_df": fft_df,
    }


def recommend_optimal_sizing(df: pd.DataFrame, strategy: str = "balanced") -> Dict[str, float]:
    """Compute prescriptive engineering PV + Battery ESS sizing from load & irradiance telemetry."""
    n_hours = max(len(df), 1)
    avg_daily_load_kwh = float(df["load_kw"].sum()) * (24.0 / n_hours)
    peak_load_kw = float(df["load_kw"].max()) if len(df) else 50.0
    avg_daily_psh = max(float(df["irradiance_wm2"].sum()) / 1000.0 * (24.0 / n_hours), 3.8)
    pr_est = 0.82

    h = df["timestamp"].dt.hour
    evening_night_kwh_day = float(df.loc[(h >= 17) | (h < 7), "load_kw"].mean()) * 14.0
    daytime_load_kw_p90 = float(df.loc[(h >= 8) & (h <= 16), "load_kw"].quantile(0.90)) if ((h >= 8) & (h <= 16)).any() else peak_load_kw

    if strategy == "peak_shaving":
        rec_pv = (0.70 * avg_daily_load_kwh) / (avg_daily_psh * pr_est)
        rec_ess_kwh = max(0.55 * evening_night_kwh_day, peak_load_kw * 1.5)
        rec_ess_kw = max(0.55 * peak_load_kw, rec_ess_kwh * 0.5)
    elif strategy == "zero_export":
        rec_pv = daytime_load_kw_p90 * 0.95
        rec_ess_kwh = rec_pv * 1.2
        rec_ess_kw = max(rec_ess_kwh * 0.45, 10.0)
    else:  # balanced high-autarky (~75-82% self-sufficiency)
        rec_pv = (0.95 * avg_daily_load_kwh) / (avg_daily_psh * pr_est)
        rec_ess_kwh = 0.72 * evening_night_kwh_day
        rec_ess_kw = max(rec_ess_kwh * 0.42, 0.45 * peak_load_kw)

    return {
        "pv_kwp": round(max(rec_pv, 5.0), 0),
        "ess_kwh": round(max(rec_ess_kwh, 0.0), 0),
        "ess_kw": round(max(rec_ess_kw, 10.0), 0),
    }


def simulate_custom_sizing(
    df: pd.DataFrame,
    baseline_pv_kwp: float,
    target_pv_kwp: float,
    target_batt_kwh: float,
    target_batt_kw: float,
    roundtrip_eff: float = 0.92,
    min_soc_pct: float = 15.0,
) -> pd.DataFrame:
    """Re-simulate hourly PV + Battery ESS dispatch for an arbitrary proposed system sizing."""
    sim = df.copy()
    if baseline_pv_kwp > 0 and df["pv_ac_kw"].max() > 0:
        scale = target_pv_kwp / baseline_pv_kwp
        new_pv_ac = df["pv_ac_kw"].to_numpy(dtype=np.float64) * scale
    else:
        irr = df["irradiance_wm2"].to_numpy(dtype=np.float64)
        tcell = df["cell_temp_c"].to_numpy(dtype=np.float64)
        temp_f = np.clip(1.0 - 0.0040 * (tcell - 25.0), 0.76, 1.03)
        new_pv_ac = target_pv_kwp * (irr / 1000.0) * temp_f * 0.94 * 0.975

    eff_batt_kw = target_batt_kw if target_batt_kwh > 0 else 0.0
    dispatch = dispatch_microgrid_arrays(
        pv_ac_kw=new_pv_ac,
        load_kw=df["load_kw"].to_numpy(dtype=np.float64),
        battery_capacity_kwh=target_batt_kwh,
        battery_max_kw=eff_batt_kw,
        roundtrip_eff=roundtrip_eff,
        min_soc_pct=min_soc_pct,
    )
    sim["pv_ac_kw"] = np.round(new_pv_ac, 3)
    sim["direct_pv_kw"] = np.round(dispatch["direct_pv_kw"], 3)
    sim["pv_to_battery_kw"] = np.round(dispatch["pv_to_battery_kw"], 3)
    sim["battery_to_load_kw"] = np.round(dispatch["battery_to_load_kw"], 3)
    sim["battery_soc_pct"] = np.round(dispatch["battery_soc_pct"], 2)
    sim["grid_import_kw"] = np.round(dispatch["grid_import_kw"], 3)
    sim["grid_export_kw"] = np.round(dispatch["grid_export_kw"], 3)
    return sim


def resample_energy_frame(df: pd.DataFrame, freq_key: str) -> pd.DataFrame:
    """Aggregate hourly energy frame into Hourly ('1h'), Daily ('1D'), Weekly ('1W'), or Monthly ('ME')."""
    if freq_key == "1h":
        return df.copy()

    indexed = df.set_index("timestamp")
    agg = indexed.resample(freq_key).agg(
        pv_ac_kw=("pv_ac_kw", "sum"),
        load_kw=("load_kw", "sum"),
        grid_import_kw=("grid_import_kw", "sum"),
        grid_export_kw=("grid_export_kw", "sum"),
        direct_pv_kw=("direct_pv_kw", "sum"),
        battery_to_load_kw=("battery_to_load_kw", "sum"),
        battery_soc_pct=("battery_soc_pct", "mean"),
        irradiance_wm2=("irradiance_wm2", "mean"),
        ambient_temp_c=("ambient_temp_c", "mean"),
        cell_temp_c=("cell_temp_c", "mean"),
    )
    # Drop empty gaps if any
    agg = agg.dropna(subset=["load_kw"], how="all")
    return agg.reset_index()
