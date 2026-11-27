"""Page 1: Executive Energy Overview, Sankey Energy Flow, and Algeria Solar Atlas."""

from __future__ import annotations

import streamlit as st

from solarguard.analytics import resample_energy_frame
from solarguard.charts import (
    chart_algeria_solar_map,
    chart_energy_balance_timeline,
    chart_energy_sankey,
)
from solarguard.config import WILAYAS_CATALOG, bi
from solarguard.ui import AppContext, render_page_banner


def render_overview_page(ctx: AppContext) -> None:
    lg = ctx.lang
    render_page_banner(
        ctx,
        page_title=bi(lg, "Executive Energy Overview & Solar Atlas", "Vue Exécutive & Bilan Énergétique"),
        subtitle=bi(
            lg,
            "Real-time synthesis of solar PV yield, facility load, battery ESS dispatch, tariff savings, and carbon offset.",
            "Synthèse de la production PV, consommation électrique, stockage BESS, économies tarifaires et impact carbone.",
        ),
    )

    k = ctx.kpis
    sym = ctx.tariff.symbol

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric(
            label=bi(lg, "PV AC Yield", "Production PV AC"),
            value=f"{k['total_pv_kwh'] / 1000.0:,.1f} MWh"
            if k["total_pv_kwh"] >= 10000
            else f"{k['total_pv_kwh']:,.0f} kWh",
            delta=f"{k['annualized_specific_yield']:,.0f} kWh/kWp/yr",
            chart_data=k["spark_pv"],
            chart_type="area",
            help=bi(
                lg,
                "Total AC solar energy delivered by inverters over the selected window.",
                "Énergie solaire AC totale délivrée par les onduleurs sur la période.",
            ),
        )
    with c2:
        st.metric(
            label=bi(lg, "Facility Demand", "Demande du Site"),
            value=f"{k['total_load_kwh'] / 1000.0:,.1f} MWh"
            if k["total_load_kwh"] >= 10000
            else f"{k['total_load_kwh']:,.0f} kWh",
            delta=f"Peak {k['peak_load_kw']:,.1f} kW",
            delta_color="off",
            chart_data=k["spark_load"],
            chart_type="line",
            help=bi(
                lg,
                "Total active electrical consumption of the facility.",
                "Consommation électrique active totale de l'installation.",
            ),
        )
    with c3:
        st.metric(
            label=bi(lg, "Self-Sufficiency", "Autonomie Site"),
            value=f"{k['self_sufficiency_pct']:.1f}%",
            delta=bi(
                lg,
                f"{k['self_consumption_pct']:.1f}% PV self-used",
                f"{k['self_consumption_pct']:.1f}% autoconsommé",
            ),
            chart_data=k["spark_autarky"],
            chart_type="area",
            help=bi(
                lg,
                "Share of facility electricity demand covered by on-site PV + Battery ESS.",
                "Part de la demande électrique couverte par le système PV + Batterie.",
            ),
        )
    with c4:
        st.metric(
            label="Performance Ratio",
            value=f"{k['performance_ratio_pct']:.1f}%",
            delta=f"CF {k['capacity_factor_pct']:.1f}%",
            chart_data=k["spark_pr"],
            chart_type="line",
            help=bi(
                lg,
                "IEC 61724 Performance Ratio comparing actual specific yield to plane-of-array insolation.",
                "Ratio de performance IEC 61724 comparant le productible réel à l'irradiation POA.",
            ),
        )
    with c5:
        st.metric(
            label=bi(lg, "Net Bill Savings", "Économie Facture"),
            value=f"{k['net_savings']:,.0f} {sym}",
            delta=bi(lg, f"{k['savings_pct']:+.1f}% vs Grid", f"{k['savings_pct']:+.1f}% vs Réseau"),
            help=bi(
                lg,
                "Monthly-reconciled electricity & peak demand charge savings over the active period.",
                "Économies nettes sur l'énergie et la prime de puissance mensuelle.",
            ),
        )
    with c6:
        st.metric(
            label=bi(lg, "CO₂ Avoided", "CO₂ Évité"),
            value=f"{k['co2_avoided_tons']:,.1f} t",
            delta=bi(lg, f"≈ {k['equiv_trees']:,.0f} trees", f"≈ {k['equiv_trees']:,.0f} arbres"),
            help=bi(
                lg,
                "Avoided grid emissions (0.548 kg CO₂/kWh Algerian gas-turbine mix).",
                "Émissions évitées sur le réseau (facteur 0,548 kg CO₂/kWh mix gaz algérien).",
            ),
        )

    with st.container(border=True):
        hdr_col, ctrl_col = st.columns([0.64, 0.36], vertical_alignment="center")
        with hdr_col:
            st.markdown(
                f'<div class="sg-section-hdr">{bi(lg, "Energy Balance Dispatch & Battery State-of-Charge Timeline", "Chronologie du Bilan Énergétique & État de Charge Batterie (SoC)")}</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                bi(
                    lg,
                    f"Direct PV-to-Load: **{k['direct_pv_kwh']:,.0f} kWh** • Battery Discharged: **{k['batt_to_load_kwh']:,.0f} kWh** • "
                    f"Grid Import: **{k['grid_import_kwh']:,.0f} kWh** • Grid Export: **{k['grid_export_kwh']:,.0f} kWh**",
                    f"PV Direct: **{k['direct_pv_kwh']:,.0f} kWh** • Décharge Batterie: **{k['batt_to_load_kwh']:,.0f} kWh** • "
                    f"Import Réseau: **{k['grid_import_kwh']:,.0f} kWh** • Export Réseau: **{k['grid_export_kwh']:,.0f} kWh**",
                )
            )
        with ctrl_col:
            freq_labels = {
                "1h": bi(lg, "Hourly", "Horaire"),
                "1D": bi(lg, "Daily", "Jour"),
                "1W": bi(lg, "Weekly", "Semaine"),
                "ME": bi(lg, "Monthly", "Mois"),
            }
            freq_keys = list(freq_labels.keys())
            default_idx = 1 if len(ctx.df) > 360 else 0
            sel_freq = st.radio(
                "Aggregation",
                options=freq_keys,
                index=default_idx,
                format_func=lambda x: freq_labels[x],
                horizontal=True,
                key="ov_freq_radio",
                label_visibility="collapsed",
            )

        agg_df = resample_energy_frame(ctx.df, sel_freq)
        st.plotly_chart(chart_energy_balance_timeline(agg_df, sel_freq), width="stretch")

    left_col, right_col = st.columns([0.52, 0.48])

    with left_col:
        with st.container(border=True):
            st.markdown(
                f'<div class="sg-section-hdr">{bi(lg, "Source-to-Sink Energy Flow Diagram", "Flux Énergétiques Source-à-Charge (Sankey)")}</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                bi(
                    lg,
                    "Conservation breakdown from Solar PV & Utility Grid to Facility Load, Battery Cycling, and Export.",
                    "Répartition conservative des flux depuis le champ PV et le réseau vers la charge, la batterie et l'export.",
                )
            )
            st.plotly_chart(chart_energy_sankey(k), width="stretch")

    with right_col:
        with st.container(border=True):
            w_prof = WILAYAS_CATALOG.get(ctx.wilaya_key, WILAYAS_CATALOG["Oran"])
            st.markdown(
                f'<div class="sg-section-hdr">{bi(lg, "Algeria Solar Resource Atlas (12 Wilayas)", "Atlas Solaire Algérien (12 Wilayas)")}</div>',
                unsafe_allow_html=True,
            )
            st.caption(
                bi(
                    lg,
                    f"Active Zone: **{w_prof.name}** ({w_prof.zone}) • Optimal Tilt: **{w_prof.optimal_tilt_deg}° S** • Dust Risk: **{w_prof.soiling_risk}**",
                    f"Zone Active: **{w_prof.name}** ({w_prof.zone}) • Inclinaison Optimale: **{w_prof.optimal_tilt_deg}° S** • Risque Poussière: **{w_prof.soiling_risk}**",
                )
            )
            st.plotly_chart(chart_algeria_solar_map(ctx.wilaya_key), width="stretch")
