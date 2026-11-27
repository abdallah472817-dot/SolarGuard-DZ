"""Strictly causal Machine Learning Energy Forecaster (PV Generation & Electrical Demand)."""

from __future__ import annotations

from typing import Any, Dict
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error


FEATURE_NAMES = [
    "hour_sin",
    "hour_cos",
    "semi_sin",
    "semi_cos",
    "doy_sin",
    "doy_cos",
    "day_of_week",
    "is_dz_weekend",
    "clear_sky_index",
    "clim_irr_anchor",
    "clim_temp_anchor",
    "causal_hour_dow_anchor",
]


def _clear_sky_bell(timestamps: pd.Series) -> np.ndarray:
    """Deterministic astronomical solar elevation proxy (zero future sensor leakage)."""
    hour = timestamps.dt.hour.to_numpy(dtype=np.float64) + 0.5
    doy = timestamps.dt.day_of_year.to_numpy(dtype=np.float64)
    decl = np.deg2rad(23.45 * np.sin(2.0 * np.pi * (284.0 + doy) / 365.0))
    lat_ref = np.deg2rad(33.0)
    omega = np.deg2rad(15.0 * (hour - 12.5))
    sin_el = np.sin(lat_ref) * np.sin(decl) + np.cos(lat_ref) * np.cos(decl) * np.cos(omega)
    return np.clip(sin_el, 0.0, 1.0)


def _build_feature_frame(
    timestamps: pd.Series,
    clim_irr: np.ndarray,
    clim_temp: np.ndarray,
    causal_anchor: np.ndarray,
) -> pd.DataFrame:
    hour = timestamps.dt.hour.to_numpy(dtype=np.float64)
    doy = timestamps.dt.day_of_year.to_numpy(dtype=np.float64)
    dow = timestamps.dt.day_of_week.to_numpy(dtype=np.float64)
    is_wknd = ((dow == 4) | (dow == 5)).astype(np.float64)

    return pd.DataFrame(
        {
            "hour_sin": np.sin(2.0 * np.pi * hour / 24.0),
            "hour_cos": np.cos(2.0 * np.pi * hour / 24.0),
            "semi_sin": np.sin(4.0 * np.pi * hour / 24.0),
            "semi_cos": np.cos(4.0 * np.pi * hour / 24.0),
            "doy_sin": np.sin(2.0 * np.pi * doy / 365.0),
            "doy_cos": np.cos(2.0 * np.pi * doy / 365.0),
            "day_of_week": dow,
            "is_dz_weekend": is_wknd,
            "clear_sky_index": _clear_sky_bell(timestamps),
            "clim_irr_anchor": clim_irr,
            "clim_temp_anchor": clim_temp,
            "causal_hour_dow_anchor": causal_anchor,
        }
    )


def _compute_origin_anchors(
    history_df: pd.DataFrame,
    query_timestamps: pd.Series,
    target_col: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute strictly pre-origin climatological anchors for query timestamps (zero lookahead)."""
    recent = history_df.iloc[-min(504, len(history_df)) :].copy()
    recent["_h"] = recent["timestamp"].dt.hour
    recent["_wknd"] = recent["timestamp"].dt.day_of_week.isin([4, 5]).astype(int)

    by_h_wknd = recent.groupby(["_wknd", "_h"])[target_col].mean()
    by_h_only = recent.groupby("_h").agg(
        irr_med=("irradiance_wm2", "median"),
        temp_med=("ambient_temp_c", "median"),
        y_mean=(target_col, "mean"),
    )

    q_h = query_timestamps.dt.hour.to_numpy()
    q_wknd = query_timestamps.dt.day_of_week.isin([4, 5]).astype(int).to_numpy()

    irr_out = by_h_only.reindex(q_h)["irr_med"].fillna(0.0).to_numpy(dtype=np.float64)
    temp_out = by_h_only.reindex(q_h)["temp_med"].fillna(20.0).to_numpy(dtype=np.float64)

    global_mean = float(recent[target_col].mean())
    anchor_out = np.empty(len(query_timestamps), dtype=np.float64)
    for i, (w, h) in enumerate(zip(q_wknd, q_h)):
        if (w, h) in by_h_wknd.index:
            anchor_out[i] = float(by_h_wknd.loc[(w, h)])
        elif h in by_h_only.index:
            anchor_out[i] = float(by_h_only.loc[h, "y_mean"])
        else:
            anchor_out[i] = global_mean

    return irr_out, temp_out, anchor_out


def run_energy_forecast(
    df: pd.DataFrame,
    target_col: str = "load_kw",
    horizon_hours: int = 72,
) -> Dict[str, Any]:
    """Train strictly causal quantile HistGradientBoosting models (P10, P50, P90), backtest & forecast."""
    work = df.sort_values("timestamp").reset_index(drop=True).copy()
    if len(work) > 2880:
        work = work.iloc[-2880:].reset_index(drop=True)

    n = len(work)
    if n < 48:
        raise ValueError("At least 48 hourly observations are required for ML forecasting.")

    y_all = work[target_col].to_numpy(dtype=np.float64)

    # Constant-zero series fast path (e.g. PV forecast on a Load-Only 0 kWp facility)
    if float(np.max(y_all)) <= 1e-6:
        holdout_n = min(max(int(n * 0.15), 24), 168)
        split_idx = n - holdout_n
        last_ts = work["timestamp"].iloc[-1]
        future_ts = pd.date_range(start=last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="1h")
        return {
            "metrics": {"mae": 0.0, "rmse": 0.0, "r2": 1.0, "nmae_pct": 0.0, "holdout_hours": holdout_n},
            "backtest_df": pd.DataFrame(
                {
                    "timestamp": work["timestamp"].iloc[split_idx:].to_numpy(),
                    "actual": np.zeros(holdout_n),
                    "predicted_p50": np.zeros(holdout_n),
                    "predicted_p10": np.zeros(holdout_n),
                    "predicted_p90": np.zeros(holdout_n),
                }
            ),
            "forecast_df": pd.DataFrame(
                {
                    "timestamp": future_ts,
                    "forecast_p50": np.zeros(horizon_hours),
                    "forecast_p10": np.zeros(horizon_hours),
                    "forecast_p90": np.zeros(horizon_hours),
                    "irradiance_proxy": np.zeros(horizon_hours),
                }
            ),
            "importance_df": pd.DataFrame(
                {"feature": FEATURE_NAMES, "importance_pct": np.round(100.0 / len(FEATURE_NAMES), 2)}
            ),
        }

    holdout_n = min(max(int(n * 0.15), 24), 168)
    split_idx = n - holdout_n

    # Build causal rolling anchors inside training window (shifted by 7 days / same-hour+wknd history)
    train_df = work.iloc[:split_idx].copy()
    train_df["_h"] = train_df["timestamp"].dt.hour
    train_df["_wknd"] = train_df["timestamp"].dt.day_of_week.isin([4, 5]).astype(int)

    tr_anchor = (
        train_df.groupby(["_wknd", "_h"])[target_col]
        .transform(lambda s: s.shift(1).rolling(14, min_periods=1).mean())
        .bfill()
        .fillna(float(train_df[target_col].mean()))
        .to_numpy(dtype=np.float64)
    )
    tr_irr_clim = (
        train_df.groupby("_h")["irradiance_wm2"]
        .transform(lambda s: s.shift(1).rolling(14, min_periods=1).median())
        .bfill()
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
    )
    tr_temp_clim = (
        train_df.groupby("_h")["ambient_temp_c"]
        .transform(lambda s: s.shift(1).rolling(14, min_periods=1).median())
        .bfill()
        .fillna(20.0)
        .to_numpy(dtype=np.float64)
    )

    X_train = _build_feature_frame(train_df["timestamp"], tr_irr_clim, tr_temp_clim, tr_anchor)
    y_train = y_all[:split_idx]

    # Strictly causal holdout test features: derived ONLY from train_df (< split_idx)!
    test_ts = work["timestamp"].iloc[split_idx:].reset_index(drop=True)
    te_irr, te_temp, te_anchor = _compute_origin_anchors(train_df, test_ts, target_col)
    X_test = _build_feature_frame(test_ts, te_irr, te_temp, te_anchor)
    y_test = y_all[split_idx:]

    common_params = dict(
        max_iter=115,
        max_depth=5,
        learning_rate=0.07,
        min_samples_leaf=12,
        random_state=42,
    )

    model_p50 = HistGradientBoostingRegressor(loss="squared_error", **common_params)
    model_p10 = HistGradientBoostingRegressor(loss="quantile", quantile=0.10, **common_params)
    model_p90 = HistGradientBoostingRegressor(loss="quantile", quantile=0.90, **common_params)

    model_p50.fit(X_train, y_train)
    model_p10.fit(X_train, y_train)
    model_p90.fit(X_train, y_train)

    pred_test_p50 = np.maximum(model_p50.predict(X_test), 0.0)
    pred_test_p10 = np.maximum(np.minimum(model_p10.predict(X_test), pred_test_p50), 0.0)
    pred_test_p90 = np.maximum(model_p90.predict(X_test), pred_test_p50)

    if target_col == "pv_ac_kw":
        night_test = (te_irr < 8.0) & (_clear_sky_bell(test_ts) <= 0.01)
        pred_test_p50[night_test] = 0.0
        pred_test_p10[night_test] = 0.0
        pred_test_p90[night_test] = 0.0

    mae = float(mean_absolute_error(y_test, pred_test_p50))
    rmse = float(root_mean_squared_error(y_test, pred_test_p50))
    r2 = float(r2_score(y_test, pred_test_p50)) if np.std(y_test) > 1e-6 else 1.0
    nmae_pct = 100.0 * mae / max(float(np.mean(y_test)), 1.0)

    perm = permutation_importance(model_p50, X_test, y_test, n_repeats=4, random_state=42)
    imp_vals = np.maximum(perm.importances_mean, 0.0)
    imp_sum = imp_vals.sum()
    imp_norm = (
        100.0 * imp_vals / imp_sum
        if imp_sum > 0
        else np.full(len(FEATURE_NAMES), 100.0 / len(FEATURE_NAMES))
    )
    importance_df = (
        pd.DataFrame({"feature": FEATURE_NAMES, "importance_pct": np.round(imp_norm, 2)})
        .sort_values("importance_pct", ascending=True)
        .reset_index(drop=True)
    )

    # Refit on full history (0..n) using identical causal rolling feature construction
    full_w = work.copy()
    full_w["_h"] = full_w["timestamp"].dt.hour
    full_w["_wknd"] = full_w["timestamp"].dt.day_of_week.isin([4, 5]).astype(int)
    all_anchor = (
        full_w.groupby(["_wknd", "_h"])[target_col]
        .transform(lambda s: s.shift(1).rolling(14, min_periods=1).mean())
        .bfill()
        .fillna(float(full_w[target_col].mean()))
        .to_numpy(dtype=np.float64)
    )
    all_irr = (
        full_w.groupby("_h")["irradiance_wm2"]
        .transform(lambda s: s.shift(1).rolling(14, min_periods=1).median())
        .bfill()
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
    )
    all_temp = (
        full_w.groupby("_h")["ambient_temp_c"]
        .transform(lambda s: s.shift(1).rolling(14, min_periods=1).median())
        .bfill()
        .fillna(20.0)
        .to_numpy(dtype=np.float64)
    )
    X_all = _build_feature_frame(full_w["timestamp"], all_irr, all_temp, all_anchor)

    model_p50.fit(X_all, y_all)
    model_p10.fit(X_all, y_all)
    model_p90.fit(X_all, y_all)

    last_ts = work["timestamp"].iloc[-1]
    future_ts = pd.Series(pd.date_range(start=last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="1h"))
    fut_irr, fut_temp, fut_anchor = _compute_origin_anchors(work, future_ts, target_col)
    X_fut = _build_feature_frame(future_ts, fut_irr, fut_temp, fut_anchor)

    fut_p50 = np.maximum(model_p50.predict(X_fut), 0.0)
    fut_p10 = np.maximum(np.minimum(model_p10.predict(X_fut), fut_p50), 0.0)
    fut_p90 = np.maximum(model_p90.predict(X_fut), fut_p50)

    if target_col == "pv_ac_kw":
        night_fut = (fut_irr < 8.0) & (_clear_sky_bell(future_ts) <= 0.01)
        fut_p50[night_fut] = 0.0
        fut_p10[night_fut] = 0.0
        fut_p90[night_fut] = 0.0

    backtest_df = pd.DataFrame(
        {
            "timestamp": work["timestamp"].iloc[split_idx:].to_numpy(),
            "actual": np.round(y_test, 2),
            "predicted_p50": np.round(pred_test_p50, 2),
            "predicted_p10": np.round(pred_test_p10, 2),
            "predicted_p90": np.round(pred_test_p90, 2),
        }
    )

    forecast_df = pd.DataFrame(
        {
            "timestamp": future_ts,
            "forecast_p50": np.round(fut_p50, 2),
            "forecast_p10": np.round(fut_p10, 2),
            "forecast_p90": np.round(fut_p90, 2),
            "irradiance_proxy": np.round(fut_irr, 1),
        }
    )

    return {
        "metrics": {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 4),
            "nmae_pct": round(nmae_pct, 2),
            "holdout_hours": holdout_n,
        },
        "backtest_df": backtest_df,
        "forecast_df": forecast_df,
        "importance_df": importance_df,
    }
