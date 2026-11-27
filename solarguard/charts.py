"""Unified Plotly 7 visualization suite for SolarGuard-DZ (Executive Dark CleanTech Theme)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from solarguard.config import PALETTE, WILAYAS_CATALOG, wilaya_display_name, wilaya_zone_name

FONT_STACK = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

HOVER_STYLE = dict(
    bgcolor="#0F172A",
    bordercolor="#334155",
    font=dict(family=FONT_STACK, size=12, color="#F8FAFC"),
)


def _apply_solar_layout(
    fig: go.Figure,
    title: str = "",
    xaxis_title: str = "",
    yaxis_title: str = "",
    height: int = 390,
    hovermode: str = "x unified",
) -> go.Figure:
    """Apply executive CleanTech dark-mode styling with transparent surfaces & crisp gridlines."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family=FONT_STACK, size=15, color=PALETTE["slate"]),
            x=0.0,
            xanchor="left",
        ),
        font=dict(family=FONT_STACK, size=12, color="#CBD5E1"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        hovermode=hovermode,
        hoverlabel=HOVER_STYLE,
        margin=dict(l=14, r=14, t=54 if title else 34, b=16),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(15, 23, 42, 0.45)",
            bordercolor="rgba(148, 163, 184, 0.14)",
            borderwidth=1,
            font=dict(size=11.5, color="#E2E8F0"),
        ),
    )
    fig.update_xaxes(
        title=dict(text=xaxis_title, font=dict(size=12, color="#94A3B8")),
        showgrid=False,
        linecolor="rgba(148, 163, 184, 0.24)",
        tickfont=dict(size=11, color="#94A3B8"),
    )
    fig.update_yaxes(
        title=dict(text=yaxis_title, font=dict(size=12, color="#94A3B8")),
        showgrid=True,
        gridcolor=PALETTE["gridline"],
        zeroline=True,
        zerolinecolor="rgba(148, 163, 184, 0.26)",
        tickfont=dict(size=11, color="#94A3B8"),
    )
    return fig


def chart_energy_balance_timeline(df: pd.DataFrame, freq_key: str = "1D") -> go.Figure:
    """Multi-series energy balance & Battery SoC chart."""
    unit = "kW" if freq_key == "1h" else "kWh"
    plot_df = df.iloc[:: max(len(df) // 1200, 1)] if freq_key == "1h" and len(df) > 1400 else df

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.72, 0.28],
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["timestamp"],
            y=plot_df["pv_ac_kw"],
            name=f"Solar PV ({unit})",
            mode="lines",
            line=dict(color=PALETTE["pv"], width=2.2),
            fill="tozeroy",
            fillcolor="rgba(245, 158, 11, 0.18)",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["timestamp"],
            y=plot_df["load_kw"],
            name=f"Facility Load ({unit})",
            mode="lines",
            line=dict(color=PALETTE["load"], width=2.1),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["timestamp"],
            y=plot_df["grid_import_kw"],
            name=f"Grid Import ({unit})",
            mode="lines",
            line=dict(color=PALETTE["grid_import"], width=1.6, dash="dot"),
        ),
        row=1,
        col=1,
    )
    if "grid_export_kw" in plot_df.columns and float(plot_df["grid_export_kw"].max()) > 0.0:
        fig.add_trace(
            go.Scatter(
                x=plot_df["timestamp"],
                y=plot_df["grid_export_kw"],
                name=f"Grid Export ({unit})",
                mode="lines",
                line=dict(color=PALETTE["grid_export"], width=1.6, dash="dashdot"),
            ),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=plot_df["timestamp"],
            y=plot_df["battery_soc_pct"],
            name="Battery SoC (%)",
            mode="lines",
            line=dict(color="#22D3EE", width=2.0),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.16)",
        ),
        row=2,
        col=1,
    )

    _apply_solar_layout(fig, title="", height=440)
    fig.update_yaxes(title=dict(text=f"Power / Energy ({unit})"), row=1, col=1)
    fig.update_yaxes(title=dict(text="ESS SoC (%)"), range=[0, 105], row=2, col=1)
    return fig


def chart_energy_sankey(kpis: dict) -> go.Figure:
    """Sankey diagram tracing PV & Grid sources to Direct Load, Battery ESS, and Export."""
    direct_pv = max(kpis["direct_pv_kwh"], 0.0)
    pv_to_batt = max(kpis["pv_to_batt_kwh"], 0.0)
    grid_exp = max(kpis["grid_export_kwh"], 0.0)
    batt_to_ld = max(kpis["batt_to_load_kwh"], 0.0)
    grid_imp = max(kpis["grid_import_kwh"], 0.0)
    ess_loss = max(pv_to_batt - batt_to_ld, 0.0)

    labels = [
        "Solar PV Array",          # 0
        "Sonelgaz / Grid Supply",  # 1
        "Battery ESS",             # 2
        "Facility Load Consumed",  # 3
        "Grid Feed-In Export",     # 4
        "Storage Cycling Loss",    # 5
    ]
    node_colors = [
        "#F59E0B",  # Amber PV
        "#F43F5E",  # Coral Grid Import
        "#22D3EE",  # Cyan ESS
        "#06B6D4",  # CleanTech Cyan Load
        "#10B981",  # Emerald Export
        "#64748B",  # Muted Loss
    ]

    sources = [0, 0, 0, 2, 2, 1]
    targets = [3, 2, 4, 3, 5, 3]
    values = [direct_pv, pv_to_batt, grid_exp, batt_to_ld, ess_loss, grid_imp]
    link_colors = [
        "rgba(245, 158, 11, 0.42)",
        "rgba(34, 211, 238, 0.38)",
        "rgba(16, 185, 129, 0.42)",
        "rgba(6, 182, 212, 0.42)",
        "rgba(100, 116, 139, 0.34)",
        "rgba(244, 63, 94, 0.36)",
    ]

    triples = [(s, t, v, c) for s, t, v, c in zip(sources, targets, values, link_colors) if v > 0.5]
    if not triples:
        triples = [(1, 3, max(kpis["total_load_kwh"], 1.0), "rgba(244, 63, 94, 0.38)")]

    fig = go.Figure(
        data=[
            go.Sankey(
                valueformat=",.0f",
                valuesuffix=" kWh",
                textfont=dict(family=FONT_STACK, size=12, color="#F8FAFC"),
                node=dict(
                    pad=18,
                    thickness=18,
                    line=dict(color="rgba(15, 23, 42, 0.85)", width=1.2),
                    label=labels,
                    color=node_colors,
                ),
                link=dict(
                    source=[x[0] for x in triples],
                    target=[x[1] for x in triples],
                    value=[round(x[2], 1) for x in triples],
                    color=[x[3] for x in triples],
                ),
            )
        ]
    )
    fig.update_layout(
        font=dict(family=FONT_STACK, size=12, color="#F8FAFC"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=HOVER_STYLE,
        height=360,
        margin=dict(l=10, r=10, t=20, b=16),
    )
    return fig


def chart_algeria_solar_map(active_wilaya_key: str, lang: str = "en") -> go.Figure:
    """Offline-safe dark geospatial Scattergeo Solar Irradiation Atlas across 12 Algerian Wilayas."""
    rows = []
    for k, w in WILAYAS_CATALOG.items():
        rows.append(
            {
                "key": k,
                "name": f"{w.code} - {wilaya_display_name(w, lang)}",
                "lat": w.lat,
                "lon": w.lon,
                "ghi": w.annual_ghi_kwh_m2,
                "tilt": w.optimal_tilt_deg,
                "zone": wilaya_zone_name(w, lang),
                "soiling": w.soiling_risk,
                "summer_c": w.avg_temp_summer_c,
                "is_active": k == active_wilaya_key,
            }
        )
    mdf = pd.DataFrame(rows)

    fig = go.Figure()

    fig.add_trace(
        go.Scattergeo(
            lat=mdf["lat"],
            lon=mdf["lon"],
            text=mdf["name"],
            customdata=np.stack(
                [mdf["ghi"], mdf["tilt"], mdf["zone"], mdf["soiling"], mdf["summer_c"]], axis=-1
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Zone: %{customdata[2]}<br>"
                "Annual GHI: <b>%{customdata[0]:.0f} kWh/m²/yr</b><br>"
                "Optimal PV Tilt: %{customdata[1]}° South<br>"
                "Summer Avg Temp: %{customdata[4]}°C | Soiling: %{customdata[3]}"
                "<extra></extra>"
            ),
            mode="markers+text",
            textposition="top center",
            textfont=dict(size=10, color="#E2E8F0"),
            marker=dict(
                size=13,
                color=mdf["ghi"],
                colorscale=[
                    [0.0, "#38BDF8"],
                    [0.35, "#FBBF24"],
                    [0.72, "#F59E0B"],
                    [1.0, "#F43F5E"],
                ],
                cmin=1700,
                cmax=2550,
                line=dict(width=1.4, color="#0B1120"),
                colorbar=dict(
                    title=dict(text="GHI<br>(kWh/m²)", font=dict(size=10.5, color="#CBD5E1")),
                    tickfont=dict(size=10, color="#94A3B8"),
                    thickness=12,
                    len=0.72,
                    outlinewidth=0,
                ),
            ),
            name="DZ Solar Atlas",
            showlegend=False,
        )
    )

    act = mdf.loc[mdf["is_active"]]
    if not act.empty:
        fig.add_trace(
            go.Scattergeo(
                lat=act["lat"],
                lon=act["lon"],
                mode="markers",
                marker=dict(
                    size=24,
                    color="rgba(6, 182, 212, 0.22)",
                    line=dict(width=2.8, color="#22D3EE"),
                ),
                hoverinfo="skip",
                name="Active Site",
                showlegend=False,
            )
        )

    fig.update_geos(
        resolution=50,
        bgcolor="rgba(0,0,0,0)",
        showframe=True,
        framecolor="rgba(148, 163, 184, 0.16)",
        showcountries=True,
        countrycolor="#334155",
        showcoastlines=True,
        coastlinecolor="#475569",
        showland=True,
        landcolor="#162033",
        showocean=True,
        oceancolor="#0B1120",
        lataxis_range=[18.5, 38.2],
        lonaxis_range=[-9.2, 12.6],
        projection_type="mercator",
    )
    fig.update_layout(
        font=dict(family=FONT_STACK, size=11.5, color="#F8FAFC"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=HOVER_STYLE,
        height=360,
        margin=dict(l=0, r=0, t=12, b=8),
    )
    return fig


def chart_pv_waterfall(wf_df: pd.DataFrame) -> go.Figure:
    """PV conversion & loss waterfall from Theoretical STC to Net AC Energy."""
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=wf_df["measure"].tolist(),
            x=wf_df["stage"].tolist(),
            y=wf_df["kwh"].round(1).tolist(),
            text=[
                f"{v:+,.0f} kWh<br>({p:+.1f}%)" if m == "relative" else f"{v:,.0f} kWh"
                for v, p, m in zip(wf_df["kwh"], wf_df["share_pct"], wf_df["measure"])
            ],
            textposition="outside",
            textfont=dict(size=11, color="#F8FAFC"),
            cliponaxis=False,
            connector=dict(line=dict(color="rgba(148, 163, 184, 0.42)", width=1.2, dash="dot")),
            decreasing=dict(marker=dict(color=PALETTE["grid_import"])),
            increasing=dict(marker=dict(color=PALETTE["grid_export"])),
            totals=dict(marker=dict(color=PALETTE["pv"])),
        )
    )
    stc_val = float(wf_df["kwh"].iloc[0]) if not wf_df.empty else 1.0
    rel_pos = float(wf_df.loc[wf_df["measure"] == "relative", "kwh"].clip(lower=0.0).sum())
    max_y = max(stc_val + rel_pos, float(wf_df["kwh"].max()), 1.0) * 1.26
    _apply_solar_layout(fig, yaxis_title="Energy (kWh)", height=400, hovermode="closest")
    fig.update_yaxes(range=[0, max_y])
    return fig


def chart_irradiance_power_curve(annotated_df: pd.DataFrame) -> go.Figure:
    """POA Irradiance vs AC Power scatter colored by Cell Temp + Fault markers."""
    day_df = annotated_df.loc[annotated_df["irradiance_wm2"] > 20.0].copy()
    if len(day_df) > 2000:
        normal_sample = day_df.loc[~day_df["is_anomaly"]].sample(
            n=min(1600, int((~day_df["is_anomaly"]).sum())), random_state=42
        )
        anom_all = day_df.loc[day_df["is_anomaly"]]
        day_df = pd.concat([normal_sample, anom_all], ignore_index=True)

    norm = day_df.loc[~day_df["is_anomaly"]]
    pv_anom = day_df.loc[
        day_df["is_anomaly"]
        & day_df["anomaly_type"].isin(
            ["PV String / Inverter Dropout", "Heavy Dust / Sandstorm Soiling", "Inverter Thermal Derating"]
        )
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=norm["irradiance_wm2"],
            y=norm["pv_ac_kw"],
            mode="markers",
            name="Normal Operation",
            marker=dict(
                size=5.5,
                opacity=0.76,
                color=norm["cell_temp_c"],
                colorscale=[
                    [0.0, "#06B6D4"],
                    [0.45, "#10B981"],
                    [0.75, "#F59E0B"],
                    [1.0, "#F43F5E"],
                ],
                colorbar=dict(
                    title=dict(text="T_cell (°C)", font=dict(size=10.5, color="#CBD5E1")),
                    tickfont=dict(size=10, color="#94A3B8"),
                    thickness=12,
                    len=0.75,
                    outlinewidth=0,
                ),
            ),
            hovertemplate="POA: %{x:.0f} W/m²<br>AC Power: %{y:.1f} kW<br>Cell Temp: %{marker.color:.1f}°C<extra></extra>",
        )
    )

    if not pv_anom.empty:
        fig.add_trace(
            go.Scatter(
                x=pv_anom["irradiance_wm2"],
                y=pv_anom["pv_ac_kw"],
                mode="markers",
                name="Detected PV Fault / Derating",
                text=pv_anom["anomaly_type"],
                marker=dict(
                    symbol="diamond",
                    size=8.8,
                    color=PALETTE["anomaly"],
                    line=dict(width=1.1, color="#F8FAFC"),
                ),
                hovertemplate="<b>%{text}</b><br>POA: %{x:.0f} W/m²<br>AC Power: %{y:.1f} kW<extra></extra>",
            )
        )

    if not day_df.empty:
        env = (
            day_df.assign(bin_irr=(day_df["irradiance_wm2"] // 50) * 50)
            .groupby("bin_irr", as_index=False)["expected_pv_kw"]
            .median()
            .sort_values("bin_irr")
        )
        fig.add_trace(
            go.Scatter(
                x=env["bin_irr"],
                y=env["expected_pv_kw"],
                mode="lines",
                name="Expected Healthy Curve",
                line=dict(color="#F8FAFC", width=2.2, dash="dash"),
            )
        )

    _apply_solar_layout(
        fig,
        xaxis_title="Plane-of-Array Irradiance (W/m²)",
        yaxis_title="AC Inverter Output (kW)",
        height=390,
        hovermode="closest",
    )
    return fig


def chart_anomaly_timeline(annotated_df: pd.DataFrame) -> go.Figure:
    """Timeline highlighting SolarGuard detected PV and Load anomalies."""
    step = max(len(annotated_df) // 1200, 1)
    base = annotated_df.iloc[::step]
    anoms = annotated_df.loc[annotated_df["is_anomaly"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=base["timestamp"],
            y=base["pv_ac_kw"],
            mode="lines",
            name="PV AC Power (kW)",
            line=dict(color=PALETTE["pv"], width=1.7),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=base["timestamp"],
            y=base["load_kw"],
            mode="lines",
            name="Facility Load (kW)",
            line=dict(color=PALETTE["load"], width=1.6),
        )
    )

    if not anoms.empty:
        y_marker = np.where(
            anoms["anomaly_type"].isin(
                ["PV String / Inverter Dropout", "Heavy Dust / Sandstorm Soiling", "Inverter Thermal Derating"]
            ),
            anoms["pv_ac_kw"],
            anoms["load_kw"],
        )
        fig.add_trace(
            go.Scatter(
                x=anoms["timestamp"],
                y=y_marker,
                mode="markers",
                name="Flagged Anomaly",
                text=anoms["anomaly_type"],
                customdata=anoms["energy_impact_kwh"],
                marker=dict(size=8.5, color=PALETTE["anomaly"], symbol="circle-open-dot", line=dict(width=2.1)),
                hovertemplate="<b>%{text}</b><br>%{x}<br>Power: %{y:.1f} kW<br>Impact: %{customdata:.1f} kWh<extra></extra>",
            )
        )

    _apply_solar_layout(fig, yaxis_title="Power (kW)", height=360)
    return fig


def chart_load_heatmap(heatmap_pivot: pd.DataFrame) -> go.Figure:
    """24-Hour x Month electrical consumption heatmap harmonized for dark mode."""
    fig = go.Figure(
        data=go.Heatmap(
            z=np.round(heatmap_pivot.values, 1),
            x=[f"{int(c):02d}:00" for c in heatmap_pivot.columns],
            y=heatmap_pivot.index.tolist(),
            colorscale=[
                [0.0, "#0F172A"],
                [0.32, "#0E7490"],
                [0.62, "#06B6D4"],
                [0.84, "#F59E0B"],
                [1.0, "#F43F5E"],
            ],
            colorbar=dict(
                title=dict(text="Avg kW", font=dict(size=11, color="#CBD5E1")),
                tickfont=dict(size=10, color="#94A3B8"),
                thickness=13,
                outlinewidth=0,
            ),
            hovertemplate="Month: %{y}<br>Hour: %{x}<br>Mean Load: <b>%{z:.1f} kW</b><extra></extra>",
        )
    )
    _apply_solar_layout(
        fig,
        xaxis_title="Hour of Day (Local Time)",
        yaxis_title="Month",
        height=370,
        hovermode="closest",
    )
    return fig


def chart_load_duration_curve(ldc_df: pd.DataFrame) -> go.Figure:
    """Load Duration Curve comparing gross facility load vs net grid import after PV+ESS."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ldc_df["pct_hours"],
            y=ldc_df["facility_load_kw"],
            mode="lines",
            name="Gross Facility Demand (kW)",
            line=dict(color=PALETTE["load"], width=2.4),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.15)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ldc_df["pct_hours"],
            y=ldc_df["net_grid_import_kw"],
            mode="lines",
            name="Net Grid Import w/ SolarGuard (kW)",
            line=dict(color=PALETTE["grid_import"], width=2.2, dash="dash"),
            fill="tozeroy",
            fillcolor="rgba(244, 63, 94, 0.14)",
        )
    )
    _apply_solar_layout(
        fig,
        xaxis_title="Percentage of Time Load Exceeded (%)",
        yaxis_title="Demand (kW)",
        height=370,
    )
    return fig


def chart_diurnal_profiles(diurnal_df: pd.DataFrame) -> go.Figure:
    """Workweek (Sun-Thu) vs Weekend (Fri-Sat) diurnal load profile with P10-P90 envelope + PV."""
    fig = go.Figure()
    work_d = diurnal_df.loc[diurnal_df["day_type"] == "Workweek (Sun-Thu)"]
    wknd_d = diurnal_df.loc[diurnal_df["day_type"] == "Weekend (Fri-Sat)"]

    if not work_d.empty:
        fig.add_trace(
            go.Scatter(
                x=work_d["hour"],
                y=work_d["p90_load_kw"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=work_d["hour"],
                y=work_d["p10_load_kw"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(6, 182, 212, 0.18)",
                name="Workweek P10–P90 Band",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=work_d["hour"],
                y=work_d["mean_load_kw"],
                mode="lines+markers",
                name="Workweek Mean Load (Sun–Thu)",
                line=dict(color=PALETTE["load"], width=2.4),
                marker=dict(size=5),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=work_d["hour"],
                y=work_d["mean_pv_kw"],
                mode="lines",
                name="Mean Solar PV Output",
                line=dict(color=PALETTE["pv"], width=2.3, dash="dot"),
            )
        )

    if not wknd_d.empty:
        fig.add_trace(
            go.Scatter(
                x=wknd_d["hour"],
                y=wknd_d["mean_load_kw"],
                mode="lines+markers",
                name="Weekend Mean Load (Fri–Sat)",
                line=dict(color=PALETTE["battery"], width=2.1),
                marker=dict(size=5),
            )
        )

    _apply_solar_layout(fig, xaxis_title="Hour of Day (0–23h)", yaxis_title="Power (kW)", height=370)
    return fig


def chart_tou_breakdown(tou_df: pd.DataFrame) -> go.Figure:
    """Time-of-Use tariff band energy comparison."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=tou_df["tou_band"],
            y=tou_df["load_kwh"],
            name="Facility Load (kWh)",
            marker_color=PALETTE["load"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=tou_df["tou_band"],
            y=tou_df["pv_kwh"],
            name="PV Generated (kWh)",
            marker_color=PALETTE["pv"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=tou_df["tou_band"],
            y=tou_df["grid_import_kwh"],
            name="Net Grid Import (kWh)",
            marker_color=PALETTE["grid_import"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=tou_df["tou_band"],
            y=tou_df["battery_discharge_kwh"],
            name="Battery Discharged (kWh)",
            marker_color=PALETTE["battery"],
        )
    )
    fig.update_layout(barmode="group")
    _apply_solar_layout(fig, yaxis_title="Total Energy (kWh)", height=360)
    return fig


def chart_fft_spectrum(fft_df: pd.DataFrame) -> go.Figure:
    """FFT Periodicity spectrum revealing dominant load cycles (12h, 24h, 168h)."""
    fig = go.Figure(
        go.Bar(
            x=fft_df["period_hours"],
            y=fft_df["amplitude_kw"],
            marker=dict(color=PALETTE["load"], line=dict(color="#38BDF8", width=0.6)),
            width=1.4,
            name="Spectral Amplitude (kW)",
            hovertemplate="Cycle Period: <b>%{x:.1f} h</b><br>Harmonic Amplitude: %{y:.2f} kW<extra></extra>",
        )
    )
    _apply_solar_layout(
        fig,
        xaxis_title="Cycle Period (Hours — e.g. 12h Semi-Diurnal, 24h Diurnal, 168h Weekly)",
        yaxis_title="Harmonic Amplitude (kW)",
        height=340,
        hovermode="closest",
    )
    return fig


def chart_forecast_horizon(
    backtest_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    target_label: str,
    color_hex: str,
) -> go.Figure:
    """Combined Holdout Actual vs Model + Future Horizon Quantile Forecast (P10-P90)."""
    bt = backtest_df.iloc[-96:] if len(backtest_df) > 96 else backtest_df
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=bt["timestamp"],
            y=bt["actual"],
            mode="lines",
            name=f"Historical Actual ({target_label})",
            line=dict(color="#F8FAFC", width=2.0),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=bt["timestamp"],
            y=bt["predicted_p50"],
            mode="lines",
            name="ML Backtest Fit (P50)",
            line=dict(color="#94A3B8", width=1.7, dash="dot"),
        )
    )

    if not bt.empty and not forecast_df.empty:
        anchor_row = pd.DataFrame(
            {
                "timestamp": [bt["timestamp"].iloc[-1]],
                "forecast_p50": [float(bt["actual"].iloc[-1])],
                "forecast_p10": [float(bt["actual"].iloc[-1])],
                "forecast_p90": [float(bt["actual"].iloc[-1])],
            }
        )
        fc_plot = pd.concat(
            [anchor_row, forecast_df[["timestamp", "forecast_p50", "forecast_p10", "forecast_p90"]]],
            ignore_index=True,
        )
    else:
        fc_plot = forecast_df

    is_solar = color_hex.upper() in ("#F59E0B", "#D97706", "#FBBF24")
    band_rgba = "rgba(245, 158, 11, 0.22)" if is_solar else "rgba(6, 182, 212, 0.22)"

    fig.add_trace(
        go.Scatter(
            x=fc_plot["timestamp"],
            y=fc_plot["forecast_p90"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=fc_plot["timestamp"],
            y=fc_plot["forecast_p10"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor=band_rgba,
            name="Forecast P10–P90 Confidence",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=fc_plot["timestamp"],
            y=fc_plot["forecast_p50"],
            mode="lines",
            name="Ahead Forecast (P50)",
            line=dict(color=color_hex, width=2.6),
        )
    )

    if not bt.empty:
        split_iso = pd.Timestamp(bt["timestamp"].iloc[-1]).isoformat()
        fig.add_vline(x=split_iso, line_width=1.5, line_dash="dash", line_color="rgba(248, 250, 252, 0.35)")

    _apply_solar_layout(fig, yaxis_title="Power (kW)", height=400)
    return fig


def chart_feature_importance(importance_df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of ML model feature importance."""
    fig = go.Figure(
        go.Bar(
            x=importance_df["importance_pct"],
            y=importance_df["feature"],
            orientation="h",
            marker=dict(color=PALETTE["load"], line=dict(color="#38BDF8", width=0.6)),
            text=[f"{v:.1f}%" for v in importance_df["importance_pct"]],
            textposition="outside",
            textfont=dict(size=11, color="#E2E8F0"),
        )
    )
    max_x = max(float(importance_df["importance_pct"].max()), 10.0) * 1.24
    _apply_solar_layout(fig, xaxis_title="Relative Importance (%)", height=340, hovermode="closest")
    fig.update_xaxes(range=[0, max_x], showgrid=True, gridcolor=PALETTE["gridline"])
    fig.update_yaxes(showgrid=False)
    return fig


def chart_battery_dispatch_comparison(base_df: pd.DataFrame, sim_df: pd.DataFrame) -> go.Figure:
    """7-Day sample operational comparison of Baseline vs Proposed PV+ESS Sizing."""
    win = min(168, len(sim_df))
    b_win = base_df.iloc[-win:]
    s_win = sim_df.iloc[-win:]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        row_heights=[0.55, 0.45],
    )

    fig.add_trace(
        go.Scatter(
            x=b_win["timestamp"],
            y=b_win["grid_import_kw"],
            name="Baseline Grid Import (kW)",
            line=dict(color="#94A3B8", width=1.8, dash="dot"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=s_win["timestamp"],
            y=s_win["grid_import_kw"],
            name="Proposed Grid Import (kW)",
            line=dict(color=PALETTE["grid_import"], width=2.2),
            fill="tozeroy",
            fillcolor="rgba(244, 63, 94, 0.14)",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=s_win["timestamp"],
            y=s_win["pv_ac_kw"],
            name="Proposed PV Output (kW)",
            line=dict(color=PALETTE["pv"], width=1.9),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=s_win["timestamp"],
            y=s_win["battery_soc_pct"],
            name="Proposed Battery SoC (%)",
            line=dict(color="#22D3EE", width=2.1),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.16)",
        ),
        row=2,
        col=1,
    )

    _apply_solar_layout(fig, height=420)
    fig.update_yaxes(title=dict(text="Power (kW)"), row=1, col=1)
    fig.update_yaxes(title=dict(text="SoC (%)"), range=[0, 105], row=2, col=1)
    return fig


def chart_cashflow_projection(cashflow_df: pd.DataFrame, currency_symbol: str) -> go.Figure:
    """25-Year Annual Net Cash Flow bars + Cumulative Nominal & Discounted Cash Flow curves."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=cashflow_df["Year"],
            y=cashflow_df["Annual Cash Flow"],
            name=f"Annual Cash Flow ({currency_symbol})",
            marker_color=np.where(cashflow_df["Annual Cash Flow"] >= 0, PALETTE["grid_export"], PALETTE["anomaly"]),
            opacity=0.72,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cashflow_df["Year"],
            y=cashflow_df["Cumulative Cash Flow"],
            mode="lines+markers",
            name=f"Cumulative Nominal CF ({currency_symbol})",
            line=dict(color=PALETTE["pv"], width=2.6),
            marker=dict(size=5.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cashflow_df["Year"],
            y=cashflow_df["Cumulative Discounted CF"],
            mode="lines",
            name=f"Cumulative Discounted NPV ({currency_symbol})",
            line=dict(color=PALETTE["load"], width=2.2, dash="dash"),
        )
    )
    fig.add_hline(y=0, line_width=1.4, line_color="rgba(148, 163, 184, 0.42)")
    _apply_solar_layout(
        fig,
        xaxis_title="Project Year (0 = CAPEX Commissioning)",
        yaxis_title=f"Cash Flow ({currency_symbol})",
        height=390,
    )
    return fig


def chart_monthly_bills(monthly_df: pd.DataFrame, currency_symbol: str) -> go.Figure:
    """Monthly electricity bill comparison Before vs After SolarGuard PV+ESS."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly_df["month"],
            y=monthly_df["baseline_bill"],
            name=f"Baseline Grid Bill ({currency_symbol})",
            marker_color="#64748B",
        )
    )
    fig.add_trace(
        go.Bar(
            x=monthly_df["month"],
            y=monthly_df["solarguard_bill"],
            name=f"Net Bill w/ SolarGuard ({currency_symbol})",
            marker_color=PALETTE["load"],
        )
    )
    fig.add_trace(
        go.Scatter(
            x=monthly_df["month"],
            y=monthly_df["net_savings"],
            mode="lines+markers",
            name=f"Monthly Savings ({currency_symbol})",
            line=dict(color=PALETTE["grid_export"], width=2.5),
            marker=dict(size=6),
        )
    )
    fig.update_layout(barmode="group")
    _apply_solar_layout(
        fig,
        xaxis_title="Billing Month",
        yaxis_title=f"Amount ({currency_symbol})",
        height=370,
    )
    return fig


def chart_correlation_heatmap(corr_df: pd.DataFrame, labels: list[str]) -> go.Figure:
    """Dark-harmonized multivariate Pearson correlation matrix."""
    fig = go.Figure(
        data=go.Heatmap(
            z=corr_df.values,
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            colorscale=[
                [0.0, "#F43F5E"],
                [0.5, "#1E293B"],
                [1.0, "#06B6D4"],
            ],
            text=corr_df.values,
            texttemplate="%{text:.2f}",
            textfont=dict(size=10, color="#F8FAFC"),
            colorbar=dict(
                title=dict(text="r", font=dict(size=11, color="#CBD5E1")),
                tickfont=dict(size=10, color="#94A3B8"),
                thickness=11,
                outlinewidth=0,
            ),
            hovertemplate="%{x} × %{y}<br>Pearson r: <b>%{z:.2f}</b><extra></extra>",
        )
    )
    _apply_solar_layout(fig, height=345, hovermode="closest")
    return fig
