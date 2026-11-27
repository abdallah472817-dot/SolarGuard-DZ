"""SolarGuard Hybrid Physics + IsolationForest Anomaly & Fault Detection Engine."""

from __future__ import annotations

from typing import Any, Dict
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


RECOMMENDED_ACTIONS: Dict[str, str] = {
    "PV String / Inverter Dropout": "Inspect DC combiner string fuses, MPPT voltage balance & inverter alarm logs.",
    "Heavy Dust / Sandstorm Soiling": "Trigger array panel cleaning cycle; verify soiling sensor transmittance.",
    "Inverter Thermal Derating": "Clean inverter heat-sink filters, check cabinet fans & ventilation clearance.",
    "Off-Hours Baseload Surge": "Audit night-shift HVAC schedules, compressed-air leaks & contactor timers.",
    "Peak Demand / Reactive Spike": "Check automatic power-factor capacitor bank stages & stagger motor starts.",
}

PV_FAULT_CATEGORIES = (
    "PV String / Inverter Dropout",
    "Heavy Dust / Sandstorm Soiling",
    "Inverter Thermal Derating",
)


def detect_energy_anomalies(
    df: pd.DataFrame,
    pv_capacity_kwp: float,
    contamination: float = 0.025,
    avg_tariff_rate: float = 5.5,
) -> Dict[str, Any]:
    """Run hybrid physics-residual + IsolationForest anomaly detection on telemetry."""
    work = df.copy().reset_index(drop=True)
    n = len(work)
    if n < 24:
        work["expected_pv_kw"] = work["pv_ac_kw"]
        work["pv_deficit_kw"] = 0.0
        work["is_anomaly"] = False
        work["anomaly_type"] = "Normal"
        work["anomaly_score"] = 0.0
        work["energy_impact_kwh"] = 0.0
        return {
            "annotated_df": work,
            "incidents_df": pd.DataFrame(),
            "summary": {
                "flagged_hours": 0,
                "incident_count": 0,
                "recoverable_pv_kwh": 0.0,
                "excess_load_kwh": 0.0,
                "financial_impact": 0.0,
            },
        }

    irr = work["irradiance_wm2"].to_numpy(dtype=np.float64)
    tcell = work["cell_temp_c"].to_numpy(dtype=np.float64)
    pv_actual = work["pv_ac_kw"].to_numpy(dtype=np.float64)
    load_actual = work["load_kw"].to_numpy(dtype=np.float64)
    pf = (
        work["power_factor"].to_numpy(dtype=np.float64)
        if "power_factor" in work.columns
        else np.full(n, 0.91)
    )
    soiling = (
        work["soiling_loss_pct"].to_numpy(dtype=np.float64)
        if "soiling_loss_pct" in work.columns
        else np.zeros(n)
    )

    has_pv_telemetry = (pv_capacity_kwp > 0.0) and (float(np.max(pv_actual)) > 0.01)

    # 1. Physics-expected clean PV output (strictly disabled on Load-Only datasets!)
    if has_pv_telemetry:
        temp_f = np.clip(1.0 - 0.0040 * (tcell - 25.0), 0.76, 1.03)
        raw_phys_pv = pv_capacity_kwp * (irr / 1000.0) * temp_f * 0.945

        sunny = (irr > 280.0) & (raw_phys_pv > 1.0)
        if sunny.sum() >= 10:
            healthy_scale = float(np.percentile(pv_actual[sunny] / raw_phys_pv[sunny], 82))
            healthy_scale = float(np.clip(healthy_scale, 0.70, 1.05))
        else:
            healthy_scale = 0.96

        expected_pv_kw = np.where(irr > 25.0, raw_phys_pv * healthy_scale, 0.0)
        inv_ceil = max(float(np.percentile(pv_actual[pv_actual > 0], 99.5)) * 1.02, float(pv_actual.max()))
        expected_pv_kw = np.minimum(expected_pv_kw, inv_ceil)

        pv_deficit_kw = np.where(irr > 160.0, np.maximum(expected_pv_kw - pv_actual, 0.0), 0.0)
        pv_deficit_ratio = np.where(
            expected_pv_kw > 2.0, pv_deficit_kw / np.maximum(expected_pv_kw, 1.0), 0.0
        )
    else:
        expected_pv_kw = np.zeros(n, dtype=np.float64)
        pv_deficit_kw = np.zeros(n, dtype=np.float64)
        pv_deficit_ratio = np.zeros(n, dtype=np.float64)

    # 2. Robust hour x day-type load baseline (median + MAD)
    dow = work["timestamp"].dt.day_of_week.to_numpy()
    is_wknd = ((dow == 4) | (dow == 5)).astype(int)
    hour = work["timestamp"].dt.hour.to_numpy()

    tmp_grp = pd.DataFrame({"load": load_actual, "h": hour, "w": is_wknd})
    stats = (
        tmp_grp.groupby(["w", "h"])["load"]
        .agg(
            med="median",
            mad=lambda s: max(
                float(np.median(np.abs(s - np.median(s)))) * 1.4826,
                float(np.std(s)) * 0.5,
                max(float(np.median(s)) * 0.04, 0.5),
            ),
        )
        .reset_index()
    )
    merged_stats = tmp_grp.merge(stats, on=["w", "h"], how="left")
    load_med = merged_stats["med"].to_numpy()
    load_scale = merged_stats["mad"].to_numpy()
    load_z = (load_actual - load_med) / np.maximum(load_scale, 0.5)
    load_excess_kw = np.maximum(load_actual - load_med, 0.0)

    # 3. Multivariate IsolationForest
    feat_matrix = np.column_stack(
        [
            pv_deficit_ratio * 4.0,
            np.clip(load_z, -2.0, 12.0),
            np.where(has_pv_telemetry & (irr > 400.0), np.maximum(tcell - 55.0, 0.0) / 10.0, 0.0),
            np.maximum(0.86 - pf, 0.0) * 15.0,
            np.where(has_pv_telemetry & (irr > 180.0), np.maximum(soiling - 8.0, 0.0) / 5.0, 0.0),
        ]
    )

    eff_contam = float(np.clip(contamination, 0.005, 0.12))
    iso = IsolationForest(n_estimators=120, contamination=eff_contam, random_state=42)
    preds = iso.fit_predict(feat_matrix)
    raw_scores = -iso.score_samples(feat_matrix)

    phys_pv_fault = has_pv_telemetry & (irr > 180.0) & (pv_deficit_ratio > 0.16)
    phys_load_fault = load_z > 3.3
    phys_pf_fault = (pf < 0.80) & (load_actual > np.percentile(load_actual, 75))

    ml_gate = (pv_deficit_ratio > 0.11) | (load_z > 2.6) | phys_pf_fault
    is_anom = ((preds == -1) & ml_gate) | phys_pv_fault | phys_load_fault

    # Vectorized root-cause classification
    is_pv_issue = is_anom & has_pv_telemetry & (pv_deficit_ratio >= 0.12) & (irr > 160.0)
    is_dust = is_pv_issue & (soiling >= 9.0) & (pv_deficit_ratio < 0.28)
    is_thermal = is_pv_issue & (~is_dust) & (tcell >= 58.0) & (irr > 500.0)
    is_dropout = is_pv_issue & (~is_dust) & (~is_thermal)

    is_load_issue = is_anom & (~is_pv_issue)
    is_peak_pf = is_load_issue & ((pf < 0.81) | ((hour >= 11) & (hour <= 19) & (load_z > 2.5)))
    is_baseload = is_load_issue & (~is_peak_pf)

    anom_type = np.select(
        [is_dust, is_thermal, is_dropout, is_peak_pf, is_baseload],
        [
            "Heavy Dust / Sandstorm Soiling",
            "Inverter Thermal Derating",
            "PV String / Inverter Dropout",
            "Peak Demand / Reactive Spike",
            "Off-Hours Baseload Surge",
        ],
        default="Normal",
    )
    impact_kwh = np.where(is_pv_issue, pv_deficit_kw, np.where(is_load_issue, load_excess_kw, 0.0))

    work["expected_pv_kw"] = np.round(expected_pv_kw, 3)
    work["pv_deficit_kw"] = np.round(pv_deficit_kw, 3)
    work["is_anomaly"] = is_anom
    work["anomaly_type"] = anom_type
    work["anomaly_score"] = np.round(raw_scores, 3)
    work["energy_impact_kwh"] = np.round(impact_kwh, 2)

    anom_rows = work.loc[work["is_anomaly"]].copy()
    incidents = []
    if not anom_rows.empty:
        anom_rows = anom_rows.sort_values(["anomaly_type", "timestamp"])
        anom_rows["gap_h"] = (
            anom_rows.groupby("anomaly_type")["timestamp"]
            .diff()
            .dt.total_seconds()
            .div(3600.0)
            .fillna(999.0)
        )
        anom_rows["grp_id"] = (anom_rows["gap_h"] > 18.0).cumsum()

        mean_ld = float(work["load_kw"].mean())
        for (atype, _), grp in anom_rows.groupby(["anomaly_type", "grp_id"]):
            tot_impact = float(grp["energy_impact_kwh"].sum())
            dur_h = int(len(grp))
            max_score = float(grp["anomaly_score"].max())
            severity = "Critical" if (tot_impact > mean_ld * 1.5 or dur_h >= 8) else "Warning"
            incidents.append(
                {
                    "Start": grp["timestamp"].min(),
                    "End": grp["timestamp"].max(),
                    "Category": atype,
                    "Severity": severity,
                    "Flagged Hours": dur_h,
                    "Impact (kWh)": round(tot_impact, 1),
                    "Est. Cost Impact": round(tot_impact * avg_tariff_rate, 1),
                    "Peak Score": round(max_score, 3),
                    "Recommended Action": RECOMMENDED_ACTIONS.get(
                        atype, "Inspect metering & SCADA telemetry."
                    ),
                }
            )

    incidents_df = pd.DataFrame(incidents)
    if not incidents_df.empty:
        incidents_df = incidents_df.sort_values("Impact (kWh)", ascending=False).reset_index(drop=True)

    pv_mask = work["anomaly_type"].isin(PV_FAULT_CATEGORIES)
    load_mask = work["is_anomaly"] & (~pv_mask)
    recov_pv_kwh = float(work.loc[pv_mask, "energy_impact_kwh"].sum())
    excess_ld_kwh = float(work.loc[load_mask, "energy_impact_kwh"].sum())

    return {
        "annotated_df": work,
        "incidents_df": incidents_df,
        "summary": {
            "flagged_hours": int(is_anom.sum()),
            "incident_count": int(len(incidents_df)),
            "recoverable_pv_kwh": recov_pv_kwh,
            "excess_load_kwh": excess_ld_kwh,
            "financial_impact": (recov_pv_kwh + excess_ld_kwh) * avg_tariff_rate,
        },
    }
