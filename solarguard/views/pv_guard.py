"""Page 2: Solar PV Physics Loss Waterfall & SolarGuard AI Fault Diagnostics."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from solarguard.analytics import compute_pv_loss_waterfall
from solarguard.charts import (
    chart_anomaly_timeline,
    chart_irradiance_power_curve,
    chart_pv_waterfall,
)
from solarguard.config import bi
from solarguard.ui import AppContext, cached_detect_anomalies, render_page_banner, render_section_header


def render_pv_guard_page(ctx: AppContext) -> None:
    lg = ctx.lang
    render_page_banner(
        ctx,
        page_title=bi(
            lg,
            "Solar PV Physics & SolarGuard AI Fault Diagnostics",
            "Performance Solaire PV & Diagnostic IA SolarGuard",
        ),
        subtitle=bi(
            lg,
            "IEC 61724 energy loss waterfall, irradiance-power thermal envelope, and hybrid ML + physics anomaly detection.",
            "Cascade des pertes IEC 61724, courbe d'irradiance/température et détection d'anomalies par IsolationForest.",
        ),
    )

    avg_rate = (ctx.tariff.shoulder_rate + ctx.tariff.peak_rate) * 0.5
    sym = ctx.tariff.symbol

    ctrl_left, ctrl_right = st.columns([0.70, 0.30], vertical_alignment="center")
    with ctrl_right:
        sens_pct = st.slider(
            bi(lg, "SolarGuard AI Sensitivity (%)", "Sensibilité IA SolarGuard (%)"),
            min_value=1.0,
            max_value=6.0,
            value=2.5,
            step=0.5,
            help=bi(
                lg,
                "IsolationForest contamination rate combined with physical PV/Load residual thresholds.",
                "Taux de contamination IsolationForest combiné aux seuils physiques de résidus PV/Charge.",
            ),
        )

    anom_res = cached_detect_anomalies(
        df=ctx.df,
        pv_kwp=ctx.pv_capacity_kwp,
        contamination=sens_pct / 100.0,
        avg_rate=avg_rate,
    )
    annotated_df = anom_res["annotated_df"]
    incidents_df = anom_res["incidents_df"]
    asum = anom_res["summary"]
    k = ctx.kpis

    with ctrl_left:
        st.caption(
            bi(
                lg,
                f"SolarGuard Status: **{asum['incident_count']} discrete operational incidents** detected across "
                f"**{asum['flagged_hours']} flagged hours** • Estimated recoverable PV + excess load value: "
                f"**{asum['financial_impact']:,.0f} {sym}**.",
                f"Statut SolarGuard : **{asum['incident_count']} incidents opérationnels** détectés sur "
                f"**{asum['flagged_hours']} heures** • Impact financier estimé : **{asum['financial_impact']:,.0f} {sym}**.",
            )
        )

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(
            bi(lg, "POA Insolation", "Irradiation POA"),
            f"{k['poa_kwh_m2']:,.0f} kWh/m²",
            delta=f"{k['performance_ratio_pct']:.1f}% PR",
        )
    with m2:
        st.metric(
            bi(lg, "Specific Yield", "Productible Spécifique"),
            f"{k['specific_yield_kwh_kwp']:,.0f} kWh/kWp",
            delta=f"{k['annualized_specific_yield']:,.0f} /yr eq.",
        )
    with m3:
        st.metric(
            bi(lg, "Daytime Cell Temp", "Temp. Cellule Jour"),
            f"{k['avg_cell_temp_day_c']:.1f} °C",
            delta=f"{k['avg_cell_temp_day_c'] - 25.0:+.1f} °C vs STC",
            delta_color="inverse",
        )
    with m4:
        st.metric(
            bi(lg, "Mean Soiling Loss", "Perte Encrassement"),
            f"{k['avg_soiling_pct']:.2f}%",
            delta=bi(lg, "Sand / Dust index", "Indice Poussière"),
            delta_color="off",
        )
    with m5:
        st.metric(
            bi(lg, "Recoverable PV Faults", "Pertes PV Récupérables"),
            f"{asum['recoverable_pv_kwh']:,.0f} kWh",
            delta=bi(lg, f"{asum['incident_count']} incidents", f"{asum['incident_count']} incidents"),
            delta_color="inverse" if asum["incident_count"] > 0 else "normal",
        )

    has_active_pv = ctx.pv_capacity_kwp > 0 and k["total_pv_kwh"] > 0
    if has_active_pv:
        col_wf, col_sc = st.columns(2)
        with col_wf:
            with st.container(border=True):
                render_section_header(
                    bi(lg, "PV Energy Loss Waterfall (STC → Net AC)", "Cascade des Pertes PV (STC → AC Net)")
                )
                st.caption(
                    bi(
                        lg,
                        "Exact reconciliation of thermal effect, Saharan dust soiling, inverter/wiring & clipping/fault losses.",
                        "Réconciliation exacte de l'effet thermique, de l'encrassement sable/poussière, de l'onduleur et des défauts.",
                    )
                )
                wf_df = compute_pv_loss_waterfall(ctx.df)
                st.plotly_chart(chart_pv_waterfall(wf_df), width="stretch")

        with col_sc:
            with st.container(border=True):
                render_section_header(
                    bi(lg, "Irradiance vs. AC Power Curve & Thermal Envelope", "Courbe Irradiance POA vs Puissance AC")
                )
                st.caption(
                    bi(
                        lg,
                        "Colored by PV cell temperature (°C); red diamonds mark SolarGuard-detected underperformance.",
                        "Coloré par température cellule (°C) ; les losanges rouges indiquent les sous-performances détectées.",
                    )
                )
                st.plotly_chart(chart_irradiance_power_curve(annotated_df), width="stretch")
    else:
        st.info(
            bi(
                lg,
                "ℹ️ Active dataset is Load-Only (0 kWp installed solar PV). Load & Power-Factor anomalies are monitored below. "
                "Open **ML Forecast & ESS Sim** in the sidebar to size a new Solar PV + Battery system for this facility.",
                "ℹ️ Ce jeu de données contient uniquement la consommation (0 kWc PV installé). Les anomalies de charge sont analysées ci-dessous. "
                "Ouvrez **Prévision IA & Sim BESS** pour dimensionner un système PV + Batterie.",
            )
        )

    with st.container(border=True):
        render_section_header(
            bi(
                lg,
                "SolarGuard Anomaly Timeline & Root-Cause Incident Log",
                "Chronologie des Anomalies & Journal d'Incidents",
            )
        )
        st.plotly_chart(chart_anomaly_timeline(annotated_df), width="stretch")

        if not incidents_df.empty:
            disp = incidents_df.copy()
            disp["Start"] = pd.to_datetime(disp["Start"]).dt.strftime("%Y-%m-%d %H:%M")
            disp["End"] = pd.to_datetime(disp["End"]).dt.strftime("%Y-%m-%d %H:%M")
            disp = disp.rename(columns={"Est. Cost Impact": f"Est. Cost ({sym})"})
            st.dataframe(disp, width="stretch", hide_index=True)
        else:
            st.success(
                bi(
                    lg,
                    "All solar strings, inverters, and load circuits are operating within healthy physical bounds.",
                    "Toutes les chaînes PV, onduleurs et départs électriques fonctionnent dans les limites nominales.",
                )
            )
