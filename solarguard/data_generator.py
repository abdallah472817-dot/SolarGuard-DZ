"""Physics-informed hourly solar PV, load, battery ESS, and grid telemetry generator."""

from __future__ import annotations

from typing import Tuple
import numpy as np
import pandas as pd

from solarguard.config import (
    FACILITY_PRESETS,
    WILAYAS_CATALOG,
    FacilityPreset,
    WilayaProfile,
)


def dispatch_microgrid_arrays(
    pv_ac_kw: np.ndarray,
    load_kw: np.ndarray,
    battery_capacity_kwh: float,
    battery_max_kw: float,
    roundtrip_eff: float = 0.92,
    min_soc_pct: float = 15.0,
    max_soc_pct: float = 98.0,
    initial_soc_pct: float = 55.0,
    dt_hours: float = 1.0,
) -> dict[str, np.ndarray]:
    """Run fast, energy-conserving hourly microgrid & battery ESS dispatch."""
    n = len(pv_ac_kw)
    pv_clean = np.maximum(np.asarray(pv_ac_kw, dtype=np.float64), 0.0)
    ld_clean = np.maximum(np.asarray(load_kw, dtype=np.float64), 0.0)
    direct_pv = np.minimum(pv_clean, ld_clean)
    surplus_pv = np.maximum(pv_clean - direct_pv, 0.0)
    residual_load = np.maximum(ld_clean - direct_pv, 0.0)

    pv_to_batt = np.zeros(n, dtype=np.float64)
    batt_to_load = np.zeros(n, dtype=np.float64)
    grid_import = np.zeros(n, dtype=np.float64)
    grid_export = np.zeros(n, dtype=np.float64)
    soc_pct = np.zeros(n, dtype=np.float64)

    if battery_capacity_kwh <= 0.0 or battery_max_kw <= 0.0:
        grid_export[:] = surplus_pv
        grid_import[:] = residual_load
        return {
            "direct_pv_kw": direct_pv,
            "pv_to_battery_kw": pv_to_batt,
            "battery_to_load_kw": batt_to_load,
            "grid_import_kw": grid_import,
            "grid_export_kw": grid_export,
            "battery_soc_pct": soc_pct,
        }

    eta_c = np.sqrt(np.clip(roundtrip_eff, 0.5, 1.0))
    eta_d = eta_c
    safe_min_soc = float(np.clip(min_soc_pct, 0.0, 90.0))
    safe_max_soc = float(np.clip(max_soc_pct, safe_min_soc + 5.0, 100.0))
    e_min = battery_capacity_kwh * (safe_min_soc / 100.0)
    e_max = battery_capacity_kwh * (safe_max_soc / 100.0)
    e_curr = np.clip(battery_capacity_kwh * (initial_soc_pct / 100.0), e_min, e_max)

    for i in range(n):
        s_pv = surplus_pv[i]
        r_ld = residual_load[i]
        if s_pv > 0.0:
            headroom_kwh = max(0.0, e_max - e_curr)
            max_charge_kw = min(battery_max_kw, headroom_kwh / (eta_c * dt_hours))
            charge_kw = min(s_pv, max_charge_kw)
            e_curr += charge_kw * eta_c * dt_hours
            pv_to_batt[i] = charge_kw
            grid_export[i] = s_pv - charge_kw
        elif r_ld > 0.0:
            avail_kwh = max(0.0, e_curr - e_min)
            max_discharge_kw = min(battery_max_kw, (avail_kwh * eta_d) / dt_hours)
            discharge_kw = min(r_ld, max_discharge_kw)
            e_curr -= (discharge_kw / eta_d) * dt_hours
            batt_to_load[i] = discharge_kw
            grid_import[i] = r_ld - discharge_kw

        soc_pct[i] = (e_curr / battery_capacity_kwh) * 100.0

    return {
        "direct_pv_kw": direct_pv,
        "pv_to_battery_kw": pv_to_batt,
        "battery_to_load_kw": batt_to_load,
        "grid_import_kw": grid_import,
        "grid_export_kw": grid_export,
        "battery_soc_pct": soc_pct,
    }


def _compute_solar_irradiance_and_weather(
    timestamps: pd.DatetimeIndex,
    wilaya: WilayaProfile,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute realistic POA irradiance (W/m²), ambient temp (°C), wind (m/s), and cloud transmittance."""
    doy = timestamps.day_of_year.to_numpy(dtype=np.float64)
    hour = timestamps.hour.to_numpy(dtype=np.float64) + 0.5  # mid-hour solar evaluation

    lat_rad = np.deg2rad(wilaya.lat)
    tilt_rad = np.deg2rad(wilaya.optimal_tilt_deg)

    # Solar declination (Cooper equation) + Equation of Time (Spencer)
    decl_rad = np.deg2rad(23.45 * np.sin(2.0 * np.pi * (284.0 + doy) / 365.0))
    b_ang = 2.0 * np.pi * (doy - 81.0) / 364.0
    eot_hours = (9.87 * np.sin(2.0 * b_ang) - 7.53 * np.cos(b_ang) - 1.5 * np.sin(b_ang)) / 60.0
    # Solar hour angle (Algeria UTC+1 standard meridian = 15°E)
    solar_time = hour + (wilaya.lon - 15.0) / 15.0 + eot_hours
    omega_rad = np.deg2rad(15.0 * (solar_time - 12.0))

    sin_elev = (
        np.sin(lat_rad) * np.sin(decl_rad)
        + np.cos(lat_rad) * np.cos(decl_rad) * np.cos(omega_rad)
    )
    sin_elev_pos = np.clip(sin_elev, 0.0, 1.0)
    daylight_mask = sin_elev > 0.02

    # Incidence angle on south-facing tilted plane (azimuth = 0 south in northern hemisphere)
    lat_minus_tilt = lat_rad - tilt_rad
    cos_theta_poa = (
        np.sin(lat_minus_tilt) * np.sin(decl_rad)
        + np.cos(lat_minus_tilt) * np.cos(decl_rad) * np.cos(omega_rad)
    )
    cos_theta_poa = np.where(daylight_mask, np.clip(cos_theta_poa, 0.0, 1.0), 0.0)

    # Extraterrestrial normal irradiance + Hottel/Air-Mass clear-sky atmospheric transmittance
    e_ext = 1361.0 * (1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.0))
    air_mass = np.where(daylight_mask, 1.0 / (sin_elev_pos + 0.15 * ((np.rad2deg( np.arcsin(sin_elev_pos) ) + 3.885) ** -1.253)), 38.0)
    tau_beam = np.where(daylight_mask, 0.76 ** (air_mass ** 0.678), 0.0)

    dni_clear = e_ext * tau_beam
    dhi_clear = np.where(daylight_mask, 0.115 * e_ext * sin_elev_pos, 0.0)
    ghi_clear = dni_clear * sin_elev_pos + dhi_clear

    # POA = Beam tilted + Isotropic sky diffuse + Ground-reflected albedo (0.22)
    poa_clear = (
        dni_clear * cos_theta_poa
        + dhi_clear * (1.0 + np.cos(tilt_rad)) * 0.5
        + ghi_clear * 0.22 * (1.0 - np.cos(tilt_rad)) * 0.5
    )

    # Markov-like daily cloudiness modulated by coastal vs Saharan climate
    n_days = int(np.ceil(len(timestamps) / 24)) + 2
    is_saharan = wilaya.annual_ghi_kwh_m2 >= 2150.0
    seasonal_cloud_prob = 0.08 if is_saharan else 0.24
    day_idx = np.arange(len(timestamps)) // 24

    daily_u = rng.uniform(0.0, 1.0, size=n_days)
    # Winter months have higher cloud cover than summer
    day_doy = np.clip((np.arange(n_days) % 365) + 1, 1, 365)
    winter_factor = 0.55 + 0.45 * np.cos(2.0 * np.pi * (day_doy - 15.0) / 365.0)
    cloud_thresh = seasonal_cloud_prob * (0.45 + 0.95 * winter_factor)

    daily_transmittance = np.where(
        daily_u < cloud_thresh,
        rng.uniform(0.32, 0.78, size=n_days),
        rng.uniform(0.93, 1.02, size=n_days),
    )
    hourly_cloud_jit = np.clip(daily_transmittance[day_idx] + rng.normal(0.0, 0.04, size=len(timestamps)), 0.18, 1.04)
    raw_poa = np.where(daylight_mask, poa_clear * hourly_cloud_jit, 0.0)

    # Scale so annualized POA matches wilaya GHI * tilt gain (~1.085)
    hours_span = max(len(timestamps), 1)
    target_poa_kwh_m2 = wilaya.annual_ghi_kwh_m2 * 1.085 * (hours_span / 8760.0)
    actual_poa_kwh_m2 = max(raw_poa.sum() / 1000.0, 1.0)
    poa_wm2 = np.clip(raw_poa * (target_poa_kwh_m2 / actual_poa_kwh_m2), 0.0, 1220.0)

    # Ambient temperature (°C): annual seasonal wave peaking late July (doy ~205) + diurnal swing peaking 15:00
    t_mean = 0.5 * (wilaya.avg_temp_summer_c + wilaya.avg_temp_winter_c)
    t_amp = 0.5 * (wilaya.avg_temp_summer_c - wilaya.avg_temp_winter_c)
    diurnal_swing = 6.2 if is_saharan else 4.1
    temp_ambient_c = (
        t_mean
        - t_amp * np.cos(2.0 * np.pi * (doy - 22.0) / 365.0)
        - diurnal_swing * np.cos(2.0 * np.pi * (hour - 3.5) / 24.0)
        + rng.normal(0.0, 1.15, size=len(timestamps))
    )

    wind_speed_ms = np.clip(
        rng.weibull(2.1, size=len(timestamps)) * (4.2 if is_saharan else 3.5)
        + 0.8 * np.sin(np.pi * np.clip((hour - 8.0) / 10.0, 0.0, 1.0)),
        0.4,
        16.0,
    )

    return poa_wm2, temp_ambient_c, wind_speed_ms, hourly_cloud_jit


def _simulate_load_profile(
    timestamps: pd.DatetimeIndex,
    preset: FacilityPreset,
    temp_ambient_c: np.ndarray,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate realistic Algerian facility electrical load (kW) and power factor."""
    hour = timestamps.hour.to_numpy()
    dow = timestamps.day_of_week.to_numpy()  # Monday=0 ... Friday=4, Saturday=5, Sunday=6
    is_dz_weekend = (dow == 4) | (dow == 5)  # Friday & Saturday in Algeria

    span = preset.peak_load_kw - preset.base_load_kw
    ptype = preset.load_profile_type

    if ptype == "industrial":
        # Two-shift manufacturing 07:00 - 21:00, lighter night shift
        diurnal = np.where((hour >= 7) & (hour <= 19), 0.78, np.where((hour >= 20) & (hour <= 22), 0.45, 0.14))
        diurnal = diurnal + 0.12 * np.exp(-0.5 * ((hour - 11.0) / 2.2) ** 2)
        weekend_mult = np.where(dow == 4, 0.46, np.where(dow == 5, 0.68, 1.0))
        base_pf = 0.885
    elif ptype == "commercial":
        # Tertiary campus 08:00 - 18:00, minimal night load, sharp AC sensitivity
        diurnal = np.exp(-0.5 * ((hour - 13.0) / 3.4) ** 2) * 0.88
        diurnal = np.where((hour < 7) | (hour > 20), 0.08, diurnal)
        weekend_mult = np.where(is_dz_weekend, 0.28, 1.0)
        base_pf = 0.93
    elif ptype == "hospital":
        # 24/7 critical facility with moderate daytime diagnostic/HVAC bump
        diurnal = 0.35 + 0.52 * np.exp(-0.5 * ((hour - 13.5) / 4.8) ** 2)
        weekend_mult = np.where(is_dz_weekend, 0.86, 1.0)
        base_pf = 0.915
    elif ptype == "microgrid":
        # Agro-pumping morning/afternoon + community evening lighting peak (19:00-22:00)
        diurnal = (
            0.55 * np.exp(-0.5 * ((hour - 10.5) / 2.6) ** 2)
            + 0.72 * np.exp(-0.5 * ((hour - 20.0) / 2.1) ** 2)
            + 0.10
        )
        weekend_mult = np.where(dow == 4, 0.82, 1.0)
        base_pf = 0.895
    else:  # utility feeder
        diurnal = (
            0.48 * np.exp(-0.5 * ((hour - 13.5) / 3.8) ** 2)
            + 0.62 * np.exp(-0.5 * ((hour - 20.0) / 2.5) ** 2)
            + 0.18
        )
        weekend_mult = np.where(is_dz_weekend, 0.88, 1.0)
        base_pf = 0.905

    # Cooling degree effect above 24°C and slight heating below 10°C
    cooling_boost = np.clip((temp_ambient_c - 24.0) / 18.0, 0.0, 0.38)
    heating_boost = np.clip((10.0 - temp_ambient_c) / 20.0, 0.0, 0.14)

    raw_load = preset.base_load_kw + span * diurnal * weekend_mult + span * (cooling_boost + heating_boost)
    noise = rng.normal(1.0, 0.045, size=len(timestamps))
    load_kw = np.clip(raw_load * noise, preset.base_load_kw * 0.65, preset.peak_load_kw * 1.12)

    # Power factor dips slightly during heavy inductive motor/HVAC load
    load_ratio = load_kw / max(preset.peak_load_kw, 1.0)
    power_factor = np.clip(base_pf - 0.035 * load_ratio + rng.normal(0.0, 0.012, size=len(timestamps)), 0.79, 0.985)
    return load_kw, power_factor


def generate_facility_telemetry(
    preset_key: str = "oran_industrial",
    wilaya_override: str | None = None,
    year: int = 2026,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a complete 8,760-hour physics-accurate energy dataset with realistic fault injections."""
    preset = FACILITY_PRESETS.get(preset_key, FACILITY_PRESETS["oran_industrial"])
    wilaya_name = wilaya_override if wilaya_override in WILAYAS_CATALOG else preset.wilaya
    wilaya = WILAYAS_CATALOG[wilaya_name]

    rng = np.random.default_rng(seed + sum(ord(c) for c in (preset_key + wilaya_name)))
    timestamps = pd.date_range(start=f"{year}-01-01 00:00:00", end=f"{year}-12-31 23:00:00", freq="1h")
    n = len(timestamps)

    poa_wm2, temp_ambient_c, wind_speed_ms, _ = _compute_solar_irradiance_and_weather(timestamps, wilaya, rng)

    # Module cell temperature (NOCT = 45°C with wind convective cooling)
    temp_cell_c = temp_ambient_c + ((45.0 - 20.0) / 800.0) * poa_wm2 * np.clip(1.08 - 0.04 * wind_speed_ms, 0.72, 1.05)

    # Theoretical STC power (kW)
    pv_stc_kw = preset.pv_capacity_kwp * (poa_wm2 / 1000.0)

    # Thermal derating (-0.40% / °C above 25°C; slight gain below 25°C capped at +3%)
    # Signed loss: positive = heat derating loss, negative = cold-weather efficiency gain
    gamma_temp = -0.0040
    temp_factor = np.clip(1.0 + gamma_temp * (temp_cell_c - 25.0), 0.76, 1.03)
    pv_after_temp_kw = pv_stc_kw * temp_factor
    loss_temp_kw = pv_stc_kw - pv_after_temp_kw

    # Soiling loss simulation (sawtooth dust build-up + scheduled washings/rain + 2 Chergui dust storms)
    soiling_pct = np.zeros(n, dtype=np.float64)
    curr_soil = 1.2
    for d in range(0, n, 24):
        curr_soil += wilaya.base_soiling_rate_pct_day * rng.uniform(0.7, 1.35)
        # Periodic cleaning or rainfall wash every ~28-40 days
        if curr_soil > 6.8 or (d > 0 and (d // 24) % 34 == 0 and rng.uniform() < 0.75):
            curr_soil = rng.uniform(0.4, 1.1)
        soiling_pct[d : min(d + 24, n)] = curr_soil

    # Inject Chergui / Sirocco sandstorm event in May (hours ~3240..3360)
    storm_start, storm_end = min(3240, n - 1), min(3384, n)
    if storm_end > storm_start:
        soiling_pct[storm_start:storm_end] = np.clip(soiling_pct[storm_start:storm_end] + 11.5, 0.0, 24.0)

    pv_after_soil_kw = pv_after_temp_kw * (1.0 - soiling_pct / 100.0)
    loss_soiling_kw = np.maximum(pv_after_temp_kw - pv_after_soil_kw, 0.0)

    # DC wiring + Inverter conversion efficiency (~96.2%)
    sys_eff = 0.962
    pv_pre_clip_kw = pv_after_soil_kw * sys_eff
    loss_system_kw = np.maximum(pv_after_soil_kw - pv_pre_clip_kw, 0.0)

    # Inverter AC clipping + Injected String/Inverter Faults ("SolarGuard" ground-truth events)
    fault_label = np.array(["Normal"] * n, dtype=object)
    fault_factor = np.ones(n, dtype=np.float64)

    if storm_end > storm_start:
        daytime_storm = (poa_wm2[storm_start:storm_end] > 180.0)
        idx_slice = np.arange(storm_start, storm_end)[daytime_storm]
        fault_label[idx_slice] = "Sand/Dust Soiling Surge"

    # Fault 1: String combiner fuse open (~26% PV drop) for 48h in March
    f1_s, f1_e = min(1800, n - 1), min(1848, n)
    fault_factor[f1_s:f1_e] = 0.74
    fault_label[f1_s:f1_e] = np.where(poa_wm2[f1_s:f1_e] > 150.0, "PV String Dropout", fault_label[f1_s:f1_e])

    # Fault 2: Inverter thermal trip / severe derating during July heat peak
    f2_s, f2_e = min(4680, n - 1), min(4720, n)
    hot_midday = (np.arange(n) >= f2_s) & (np.arange(n) < f2_e) & (poa_wm2 > 550.0)
    fault_factor[hot_midday] = 0.58
    fault_label[hot_midday] = "Inverter Thermal Derating"

    # Fault 3: Partial inverter outage in September
    f3_s, f3_e = min(6120, n - 1), min(6156, n)
    fault_factor[f3_s:f3_e] = 0.64
    fault_label[f3_s:f3_e] = np.where(poa_wm2[f3_s:f3_e] > 150.0, "Inverter Partial Trip", fault_label[f3_s:f3_e])

    pv_faulted_kw = pv_pre_clip_kw * fault_factor
    pv_ac_kw = np.minimum(pv_faulted_kw, preset.inverter_ac_kw)
    loss_clip_and_fault_kw = np.maximum(pv_pre_clip_kw - pv_ac_kw, 0.0)

    # Load simulation + 2 Load anomalies (night baseload leak + compressor surge)
    load_kw, power_factor = _simulate_load_profile(timestamps, preset, temp_ambient_c, rng)

    l1_s, l1_e = min(2520, n - 1), min(2568, n)
    night_mask = (np.arange(n) >= l1_s) & (np.arange(n) < l1_e) & ((timestamps.hour < 6) | (timestamps.hour > 21))
    load_kw[night_mask] *= 1.85
    fault_label[night_mask] = "Night Baseload Surge"

    l2_s, l2_e = min(5410, n - 1), min(5426, n)
    peak_mask = (np.arange(n) >= l2_s) & (np.arange(n) < l2_e) & (timestamps.hour >= 12) & (timestamps.hour <= 17)
    load_kw[peak_mask] = preset.peak_load_kw * 1.28
    power_factor[peak_mask] = 0.77
    fault_label[peak_mask] = "Demand & Reactive Spike"

    # Microgrid dispatch
    dispatch = dispatch_microgrid_arrays(
        pv_ac_kw=pv_ac_kw,
        load_kw=load_kw,
        battery_capacity_kwh=preset.battery_capacity_kwh,
        battery_max_kw=preset.battery_max_kw,
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "irradiance_wm2": np.round(poa_wm2, 2),
            "ambient_temp_c": np.round(temp_ambient_c, 2),
            "cell_temp_c": np.round(temp_cell_c, 2),
            "wind_speed_ms": np.round(wind_speed_ms, 2),
            "soiling_loss_pct": np.round(soiling_pct, 2),
            "pv_stc_kw": np.round(pv_stc_kw, 3),
            "pv_ac_kw": np.round(pv_ac_kw, 3),
            "loss_temp_kw": np.round(loss_temp_kw, 3),
            "loss_soiling_kw": np.round(loss_soiling_kw, 3),
            "loss_system_kw": np.round(loss_system_kw, 3),
            "loss_clip_fault_kw": np.round(loss_clip_and_fault_kw, 3),
            "load_kw": np.round(load_kw, 3),
            "power_factor": np.round(power_factor, 3),
            "direct_pv_kw": np.round(dispatch["direct_pv_kw"], 3),
            "pv_to_battery_kw": np.round(dispatch["pv_to_battery_kw"], 3),
            "battery_to_load_kw": np.round(dispatch["battery_to_load_kw"], 3),
            "battery_soc_pct": np.round(dispatch["battery_soc_pct"], 2),
            "grid_import_kw": np.round(dispatch["grid_import_kw"], 3),
            "grid_export_kw": np.round(dispatch["grid_export_kw"], 3),
            "event_tag": fault_label,
        }
    )
    return df
