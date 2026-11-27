"""Page 3: Electrical Load Profile, Load Duration Curve, ToU Breakdown, and FFT Harmonics."""

from __future__ import annotations

import streamlit as st

from solarguard.analytics import compute_load_diagnostics
from solarguard.charts import (
    chart_diurnal_profiles,
    chart_fft_spectrum,
    chart_load_duration_curve,
    chart_load_heatmap,
    chart_tou_breakdown,
)
from solarguard.config import bi
from solarguard.ui import AppContext, render_page_banner, render_section_header


def render_load_grid_page(ctx: AppContext) -> None:
    lg = ctx.lang
    render_page_banner(
        ctx,
        page_title=bi(
            lg,
            "Electrical Load Profile & Grid Demand Audit",
            "Analyse de la Charge Électrique & Réseau",
        ),
        subtitle=bi(
            lg,
            "Load duration curve (LDC), 24h×12 seasonal heatmap, Algerian workweek/weekend diurnal bands, ToU energy mix & FFT cycles.",
            "Monotone de charge (LDC), matrice horo-saisonnière 24h×12, postes horaires Sonelgaz/ToU et spectre FFT.",
        ),
    )

    k = ctx.kpis
    diag = compute_load_diagnostics(ctx.df)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric(
            bi(lg, "Peak Facility Demand", "Pointe Appelée Site"),
            f"{k['peak_load_kw']:,.1f} kW",
            delta=f"{k['peak_apparent_kva']:,.0f} kVA apparent",
            delta_color="off",
        )
    with c2:
        st.metric(
            bi(lg, "Net Grid Peak", "Pointe Nette Réseau"),
            f"{k['net_grid_peak_kw']:,.1f} kW",
            delta=bi(lg, f"-{k['peak_shaving_kw']:,.1f} kW shaved", f"-{k['peak_shaving_kw']:,.1f} kW écrêtés"),
        )
    with c3:
        st.metric(
            bi(lg, "Baseload (P10)", "Talon de Charge (P10)"),
            f"{k['baseload_p10_kw']:,.1f} kW",
            delta=f"Avg {k['avg_load_kw']:,.1f} kW",
            delta_color="off",
        )
    with c4:
        st.metric(
            bi(lg, "Load Factor", "Facteur de Charge"),
            f"{k['load_factor_pct']:.1f}%",
            delta=bi(lg, "Avg / Peak ratio", "Ratio Moy. / Pointe"),
            delta_color="off",
        )
    with c5:
        pf_val = k["avg_power_factor"]
        st.metric(
            bi(lg, "Mean Power Factor", "Facteur de Puissance"),
            f"{pf_val:.3f} cos φ",
            delta=bi(
                lg,
                "Healthy ≥ 0.90" if pf_val >= 0.90 else "Reactive penalty risk (<0.90)",
                "Conforme ≥ 0.90" if pf_val >= 0.90 else "Risque pénalité réactive (<0.90)",
            ),
            delta_color="normal" if pf_val >= 0.90 else "inverse",
        )

    r1_left, r1_right = st.columns(2)
    with r1_left:
        with st.container(border=True):
            render_section_header(
                bi(lg, "24-Hour × Monthly Demand Intensity Heatmap", "Matrice Thermique Horaire × Mensuelle (kW)")
            )
            st.caption(
                bi(
                    lg,
                    "Reveals summer HVAC cooling peaks and industrial shift schedules across the year.",
                    "Met en évidence les pointes de climatisation estivales et les horaires de postes industriels.",
                )
            )
            st.plotly_chart(chart_load_heatmap(diag["heatmap_pivot"]), width="stretch")

    with r1_right:
        with st.container(border=True):
            render_section_header(
                bi(lg, "Load Duration Curve (Gross Load vs. Net Grid)", "Monotone de Puissance (Charge Brute vs Réseau)")
            )
            st.caption(
                bi(
                    lg,
                    "Area between curves represents total clean on-site energy autonomy & peak demand reduction.",
                    "L'aire entre les deux courbes représente l'autonomie énergétique locale et l'écrêtement de pointe.",
                )
            )
            st.plotly_chart(chart_load_duration_curve(diag["ldc_df"]), width="stretch")

    r2_left, r2_right = st.columns(2)
    with r2_left:
        with st.container(border=True):
            render_section_header(
                bi(
                    lg,
                    "Diurnal Profiles: Workweek (Sun–Thu) vs. Weekend (Fri–Sat)",
                    "Profils Journaliers Ouvrés (Dim–Jeu) vs Week-end (Ven–Sam)",
                )
            )
            st.caption(
                bi(
                    lg,
                    "Calibrated to Algerian workweek calendar with P10–P90 demand envelope and PV coincidence curve.",
                    "Calibré sur la semaine algérienne avec enveloppe P10–P90 et courbe moyenne de production PV.",
                )
            )
            st.plotly_chart(chart_diurnal_profiles(diag["diurnal_df"]), width="stretch")

    with r2_right:
        with st.container(border=True):
            render_section_header(
                bi(
                    lg,
                    "Time-of-Use (ToU) Tariff Window Breakdown",
                    "Répartition par Poste Tarifaire (Creuse / Pleine / Pointe)",
                )
            )
            st.caption(
                bi(
                    lg,
                    "Ordered chronologically from Off-Peak to Evening Peak to highlight storage peak-shaving dispatch.",
                    "Classé par poste tarifaire (Creuses → Pleines → Pointe soir) illustrant le délestage par batterie.",
                )
            )
            st.plotly_chart(chart_tou_breakdown(diag["tou_df"]), width="stretch")

    with st.container(border=True):
        render_section_header(
            bi(
                lg,
                "Fast Fourier Transform (FFT) Load Periodicity Spectrum",
                "Analyse Spectrale FFT des Cycles de Consommation",
            )
        )
        st.caption(
            bi(
                lg,
                "Identifies dominant periodic operational cycles (12h semi-diurnal, 24h diurnal, 168h weekly).",
                "Identifie les cycles périodiques dominants (harmonique 12h, cycle journalier 24h, cycle hebdomadaire 168h).",
            )
        )
        st.plotly_chart(chart_fft_spectrum(diag["fft_df"]), width="stretch")
