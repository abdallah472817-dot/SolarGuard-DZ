"""Smart CSV/Excel ingestion, auto-column detection, normalization, and validation."""

from __future__ import annotations

import io
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd

from solarguard.data_generator import dispatch_microgrid_arrays

COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "timestamp": ("timestamp", "datetime", "date_time", "date", "time", "horodatage", "heure", "period"),
    "load_kw": (
        "load_kw",
        "load",
        "consumption",
        "demand",
        "conso",
        "consommation",
        "active_power",
        "grid_load",
        "power_kw",
        "energy_kwh",
        "kwh",
    ),
    "pv_ac_kw": (
        "pv_ac_kw",
        "pv_kw",
        "pv_power",
        "solar_kw",
        "solar",
        "solaire",
        "pv_generation",
        "generation",
        "production",
        "ac_power",
        "inverter_power",
    ),
    "irradiance_wm2": (
        "irradiance_wm2",
        "irradiance",
        "poa",
        "ghi",
        "radiation",
        "solar_radiation",
        "ensoleillement",
        "wm2",
    ),
    "ambient_temp_c": (
        "ambient_temp_c",
        "ambient_temp",
        "temp_ambient",
        "temperature",
        "temp_c",
        "air_temp",
    ),
    "cell_temp_c": ("cell_temp_c", "module_temp", "panel_temp", "pv_temp", "t_cell"),
    "battery_soc_pct": ("battery_soc_pct", "soc", "soc_pct", "battery_soc", "etat_charge"),
}


def read_uploaded_table(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read CSV (comma, semicolon, or tab separated) or Excel file into a raw DataFrame."""
    if not file_bytes:
        raise ValueError("Uploaded file is empty (0 bytes).")

    lower_name = filename.lower()
    buf = io.BytesIO(file_bytes)
    if lower_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(buf)
    else:
        sample = file_bytes[:8192].decode("utf-8", errors="ignore")
        first_line = sample.splitlines()[0] if sample.splitlines() else sample
        if first_line.count(";") > first_line.count(","):
            sep = ";"
        elif first_line.count("\t") > first_line.count(","):
            sep = "\t"
        else:
            sep = ","
        buf.seek(0)
        try:
            df = pd.read_csv(buf, sep=sep)
        except UnicodeDecodeError:
            buf.seek(0)
            df = pd.read_csv(buf, sep=sep, encoding="latin-1")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def _coerce_numeric_series(s: pd.Series) -> pd.Series:
    """Robustly coerce numeric or localized comma-decimal string series to float."""
    if pd.api.types.is_string_dtype(s) or s.dtype == object:
        cleaned = (
            s.astype(str)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(s, errors="coerce")


def auto_detect_mapping(columns: list[str]) -> Dict[str, Optional[str]]:
    """Suggest best-match raw column names for canonical SolarGuard fields."""
    detected: Dict[str, Optional[str]] = {k: None for k in COLUMN_ALIASES}
    used: set[str] = set()
    norm_cols = {col: col.lower().replace(" ", "_").replace("-", "_") for col in columns}

    for target, aliases in COLUMN_ALIASES.items():
        for col, ncol in norm_cols.items():
            if col in used:
                continue
            if ncol in aliases:
                detected[target] = col
                used.add(col)
                break

    for target, aliases in COLUMN_ALIASES.items():
        if detected[target] is not None:
            continue
        for col, ncol in norm_cols.items():
            if col in used:
                continue
            if any(alias in ncol for alias in aliases):
                detected[target] = col
                used.add(col)
                break

    if detected["timestamp"] is None and columns:
        detected["timestamp"] = columns[0]

    return detected


def normalize_custom_dataset(
    raw_df: pd.DataFrame,
    mapping: Dict[str, Optional[str]],
    unit_multiplier: float = 1.0,
    assumed_pv_kwp: Optional[float] = None,
    assumed_battery_kwh: float = 0.0,
    assumed_battery_kw: float = 0.0,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Convert an arbitrary user DataFrame into canonical hourly SolarGuard telemetry."""
    if raw_df.empty:
        raise ValueError("Uploaded dataset is empty.")

    ts_col = mapping.get("timestamp")
    if not ts_col or ts_col not in raw_df.columns:
        raise ValueError("A valid timestamp/date column must be mapped.")

    work = raw_df.copy()
    parsed_ts = pd.to_datetime(work[ts_col], errors="coerce", dayfirst=False)
    if parsed_ts.isna().mean() > 0.5:
        parsed_ts = pd.to_datetime(work[ts_col], errors="coerce", dayfirst=True)

    valid_mask = parsed_ts.notna()
    work = work.loc[valid_mask].copy()
    work["timestamp"] = parsed_ts.loc[valid_mask]
    if len(work) < 4:
        raise ValueError("Dataset must contain at least 4 valid timestamped rows.")

    if getattr(work["timestamp"].dt, "tz", None) is not None:
        work["timestamp"] = work["timestamp"].dt.tz_localize(None)

    work = work.sort_values("timestamp").drop_duplicates(subset=["timestamp"])

    def _extract_numeric(key: str, scale: float = 1.0) -> Optional[pd.Series]:
        col = mapping.get(key)
        if col and col in work.columns:
            return _coerce_numeric_series(work[col]) * scale
        return None

    num_frame = pd.DataFrame({"timestamp": work["timestamp"]})
    load_s = _extract_numeric("load_kw", unit_multiplier)
    pv_s = _extract_numeric("pv_ac_kw", unit_multiplier)
    irr_s = _extract_numeric("irradiance_wm2", 1.0)
    tamb_s = _extract_numeric("ambient_temp_c", 1.0)
    tcell_s = _extract_numeric("cell_temp_c", 1.0)
    soc_s = _extract_numeric("battery_soc_pct", 1.0)

    if load_s is None and pv_s is None:
        # Fallback: inspect unmapped columns, including comma-decimal string columns
        for c in work.columns:
            if c == ts_col:
                continue
            coerced = _coerce_numeric_series(work[c])
            if coerced.notna().mean() >= 0.5:
                load_s = coerced * unit_multiplier
                break
        if load_s is None:
            raise ValueError("Please map at least one numeric energy column (Load or Solar PV).")

    if load_s is not None:
        num_frame["load_kw"] = load_s.clip(lower=0.0)
    if pv_s is not None:
        num_frame["pv_ac_kw"] = pv_s.clip(lower=0.0)
    if irr_s is not None:
        num_frame["irradiance_wm2"] = irr_s.clip(lower=0.0, upper=1350.0)
    if tamb_s is not None:
        num_frame["ambient_temp_c"] = tamb_s
    if tcell_s is not None:
        num_frame["cell_temp_c"] = tcell_s
    if soc_s is not None:
        num_frame["battery_soc_pct"] = soc_s.clip(lower=0.0, upper=100.0)

    for extra_col in ("power_factor", "wind_speed_ms", "soiling_loss_pct"):
        if extra_col in work.columns and extra_col not in num_frame.columns:
            num_frame[extra_col] = _coerce_numeric_series(work[extra_col])
    if "event_tag" in work.columns:
        num_frame["event_tag"] = work["event_tag"].astype(str)

    diffs = num_frame["timestamp"].diff().dropna()
    median_sec = float(diffs.dt.total_seconds().median()) if len(diffs) > 0 else 3600.0
    is_daily_input = median_sec >= 43200.0  # >= 12h spacing (e.g. daily utility bill / daily meter CSV)

    num_cols = [c for c in num_frame.columns if c not in ("timestamp", "event_tag")]
    indexed = num_frame.set_index("timestamp")

    if is_daily_input:
        # Expand daily records across full 24h days so end-of-last-day hours are included
        start_hr = indexed.index.min().floor("D")
        end_hr = indexed.index.max().floor("D") + pd.Timedelta(hours=23)
        full_idx = pd.date_range(start_hr, end_hr, freq="1h")
        step_h = max(median_sec / 3600.0, 24.0)

        # Convert daily kWh totals to hourly mean kW if column name implies energy (kwh/wh/energy/conso/prod)
        ld_col_name = (mapping.get("load_kw") or "").lower()
        pv_col_name = (mapping.get("pv_ac_kw") or "").lower()
        energy_tokens = ("kwh", "mwh", "wh", "energy", "energie", "conso", "prod")

        daily_reindexed = indexed[num_cols].reindex(full_idx).ffill().bfill()
        if "load_kw" in daily_reindexed.columns:
            ld_base = daily_reindexed["load_kw"].to_numpy(dtype=np.float64)
            if any(tok in ld_col_name for tok in energy_tokens):
                ld_base = ld_base / step_h
            hr_arr = full_idx.hour.to_numpy(dtype=np.float64)
            # Mild diurnal shape with unit mean = 1.0 so daily energy sum is conserved
            shape_ld = 0.72 + 0.56 * np.sin(np.pi * np.clip((hr_arr - 5.0) / 15.0, 0.0, 1.0)) ** 2
            shape_ld = shape_ld / np.mean(shape_ld)
            daily_reindexed["load_kw"] = ld_base * shape_ld

        if "pv_ac_kw" in daily_reindexed.columns:
            pv_base = daily_reindexed["pv_ac_kw"].to_numpy(dtype=np.float64)
            if any(tok in pv_col_name for tok in energy_tokens):
                pv_base = pv_base / step_h
            hr_arr = full_idx.hour.to_numpy(dtype=np.float64)
            # Solar bell curve strictly zero at night, unit 24h mean = 1.0
            raw_bell = np.clip(np.sin(np.pi * (hr_arr - 6.0) / 12.0), 0.0, 1.0) ** 1.35
            bell_norm = raw_bell / max(float(np.mean(raw_bell)), 1e-6)
            daily_reindexed["pv_ac_kw"] = pv_base * bell_norm

        resampled_num = daily_reindexed
        tag_s = pd.Series("Normal", index=full_idx)
    else:
        resampled_num = (
            indexed[num_cols]
            .resample("1h")
            .mean()
            .interpolate(method="time", limit=12)
            .bfill()
            .ffill()
        )
        if "event_tag" in indexed.columns:
            tag_s = indexed["event_tag"].resample("1h").first().fillna("Normal")
        else:
            tag_s = pd.Series("Normal", index=resampled_num.index)

    df = resampled_num.reset_index().rename(columns={"index": "timestamp"})
    n = len(df)
    hours = df["timestamp"].dt.hour.to_numpy()
    doy = df["timestamp"].dt.day_of_year.to_numpy()

    if "load_kw" not in df.columns:
        pv_peak = float(df["pv_ac_kw"].max()) if "pv_ac_kw" in df.columns else 50.0
        df["load_kw"] = np.round(
            0.22 * pv_peak + 0.35 * pv_peak * np.exp(-0.5 * ((hours - 13.0) / 4.0) ** 2), 3
        )

    if "pv_ac_kw" not in df.columns:
        df["pv_ac_kw"] = 0.0

    has_active_pv = float(df["pv_ac_kw"].max()) > 0.0
    if assumed_pv_kwp is not None and assumed_pv_kwp > 0:
        est_pv_kwp = float(assumed_pv_kwp)
    elif has_active_pv:
        est_pv_kwp = max(float(df["pv_ac_kw"].quantile(0.995)) * 1.15, 0.5)
    else:
        # Load-only dataset with zero solar generation -> 0.0 kWp installed!
        est_pv_kwp = 0.0

    if "irradiance_wm2" not in df.columns:
        if has_active_pv and est_pv_kwp > 0:
            df["irradiance_wm2"] = np.clip((df["pv_ac_kw"] / est_pv_kwp) * 1080.0, 0.0, 1150.0)
        else:
            daylight = np.clip(np.sin(np.pi * (hours - 6.0) / 12.0), 0.0, 1.0)
            season = 0.78 + 0.22 * np.sin(2.0 * np.pi * (doy - 80.0) / 365.0)
            df["irradiance_wm2"] = np.round(880.0 * daylight * season, 2)

    if "ambient_temp_c" not in df.columns:
        df["ambient_temp_c"] = np.round(
            20.0
            - 7.5 * np.cos(2.0 * np.pi * (doy - 20.0) / 365.0)
            - 4.0 * np.cos(2.0 * np.pi * (hours - 3.5) / 24.0),
            2,
        )

    if "cell_temp_c" not in df.columns:
        df["cell_temp_c"] = np.round(df["ambient_temp_c"] + (25.0 / 800.0) * df["irradiance_wm2"], 2)

    if "wind_speed_ms" not in df.columns:
        df["wind_speed_ms"] = 3.2

    if "soiling_loss_pct" not in df.columns:
        df["soiling_loss_pct"] = 2.4

    if "power_factor" not in df.columns:
        df["power_factor"] = 0.91

    # Exact signed PV conversion waterfall
    if has_active_pv and est_pv_kwp > 0:
        pv_stc = est_pv_kwp * (df["irradiance_wm2"].to_numpy() / 1000.0)
        temp_factor = np.clip(1.0 - 0.0040 * (df["cell_temp_c"].to_numpy() - 25.0), 0.76, 1.03)
        pv_after_temp = pv_stc * temp_factor
        pv_after_soil = pv_after_temp * (1.0 - df["soiling_loss_pct"].to_numpy() / 100.0)
        pv_pre_clip = pv_after_soil * 0.962
        pv_actual_arr = df["pv_ac_kw"].to_numpy()

        df["pv_stc_kw"] = np.round(pv_stc, 3)
        df["loss_temp_kw"] = np.round(pv_stc - pv_after_temp, 3)
        df["loss_soiling_kw"] = np.round(pv_after_temp - pv_after_soil, 3)
        df["loss_system_kw"] = np.round(pv_after_soil - pv_pre_clip, 3)
        df["loss_clip_fault_kw"] = np.round(pv_pre_clip - pv_actual_arr, 3)
    else:
        for col_z in ("pv_stc_kw", "loss_temp_kw", "loss_soiling_kw", "loss_system_kw", "loss_clip_fault_kw"):
            df[col_z] = 0.0

    dispatch = dispatch_microgrid_arrays(
        pv_ac_kw=df["pv_ac_kw"].to_numpy(dtype=np.float64),
        load_kw=df["load_kw"].to_numpy(dtype=np.float64),
        battery_capacity_kwh=float(assumed_battery_kwh),
        battery_max_kw=float(assumed_battery_kw),
    )
    df["direct_pv_kw"] = np.round(dispatch["direct_pv_kw"], 3)
    df["pv_to_battery_kw"] = np.round(dispatch["pv_to_battery_kw"], 3)
    df["battery_to_load_kw"] = np.round(dispatch["battery_to_load_kw"], 3)
    if "battery_soc_pct" not in df.columns or assumed_battery_kwh > 0:
        df["battery_soc_pct"] = np.round(dispatch["battery_soc_pct"], 2)
    df["grid_import_kw"] = np.round(dispatch["grid_import_kw"], 3)
    df["grid_export_kw"] = np.round(dispatch["grid_export_kw"], 3)
    df["event_tag"] = tag_s.to_numpy()

    metadata = {
        "raw_rows": len(raw_df),
        "hourly_rows": len(df),
        "native_step_minutes": round(median_sec / 60.0, 1),
        "is_daily_disaggregated": is_daily_input,
        "inferred_pv_kwp": round(est_pv_kwp, 2),
        "peak_load_kw": round(float(df["load_kw"].max()), 2),
        "completeness_pct": round(100.0 * float(valid_mask.mean()), 2),
    }
    return df, metadata
