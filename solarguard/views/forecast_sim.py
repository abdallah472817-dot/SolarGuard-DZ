"""Page 4: ML Quantile Energy Forecasting & Interactive PV + Battery ESS Sizing Simulator."""

from __future__ import annotations

import numpy as np
import streamlit as st

from solarguard.analytics import (
    compute_executive_kpis,
    recommend_optimal_sizing,
    simulate_custom_sizing,
)
from solarguard.charts import (
    chart_battery_dispatch_comparison,
    chart_feature_importance,
    chart_forecast_horizon,
)
from solarguard.config import PALETTE, bi
from solarguard.ui import AppContext, cached_run_forecast, render_page_banner, render_section_header


def render_forecast_sim_page(ctx: AppContext) -> None:
    lg = ctx.lang
    render_page_banner(
        ctx,
        page_title=bi(
            lg,
            "ML Energy Forecasting & Interactive PV + Battery ESS Simulator",
            "Prévision IA Quantile & Simulateur de Dimensionnement PV + BESS",
        ),
        subtitle=bi(
            lg,
            "Strictly causal quantile HistGradientBoosting forecasts (P10/P50/P90) and prescriptive microgrid sizing lab.",
            "Modèles Gradient Boosting Quantiles strictement causaux (P10/P50/P90) et laboratoire de dimensionnement.",
        ),
    )

    tab_fc, tab_sim = st.tabs(
        [
            bi(lg, "🤖 ML Short-Term Forecaster", "🤖 Prévision IA Court-Terme"),
            bi(lg, "🔋 PV + Battery ESS Sizing Lab", "🔋 Dimensionnement PV + Batterie"),
        ]
    )

    with tab_fc:
        c_tgt, c_hor = st.columns([0.55, 0.45])
        with c_tgt:
            target_col = st.radio(
                bi(lg, "Forecast Target", "Série Cible"),
                options=["load_kw", "pv_ac_kw"],
                format_func=lambda c: (
                    bi(lg, "Electrical Load (kW)", "Charge Électrique (kW)")
                    if c == "load_kw"
                    else bi(lg, "Solar PV Output (kW)", "Production Solaire PV (kW)")
                ),
                horizontal=True,
                key="fc_target_radio",
            )
        with c_hor:
            horizon_h = st.select_slider(
                bi(lg, "Ahead Forecast Horizon (Hours)", "Horizon de Prévision (Heures)"),
                options=[24, 48, 72, 120, 168],
                value=72,
                key="fc_horizon_slider",
            )

        if len(ctx.df) < 48:
            st.warning(
                bi(
                    lg,
                    "Select at least 48 hours of data in the sidebar to train the ML forecaster.",
                    "Sélectionnez au moins 48 heures de données pour entraîner le modèle de prévision.",
                )
            )
        else:
            fc_load = cached_run_forecast(ctx.df, target_col="load_kw", horizon_hours=int(horizon_h))
            fc_pv = cached_run_forecast(ctx.df, target_col="pv_ac_kw", horizon_hours=int(horizon_h))
            fc_res = fc_load if target_col == "load_kw" else fc_pv

            m = fc_res["metrics"]
            fut_df = fc_res["forecast_df"]
            total_fut_kwh = float(fut_df["forecast_p50"].sum())
            peak_fut_kw = float(fut_df["forecast_p50"].max())

            # Expected Net Grid Balance across forecast horizon
            net_grid_fut = np.maximum(
                fc_load["forecast_df"]["forecast_p50"].to_numpy()
                - fc_pv["forecast_df"]["forecast_p50"].to_numpy(),
                0.0,
            )
            expected_net_import_kwh = float(net_grid_fut.sum())

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric(
                bi(lg, "Causal Holdout R²", "R² Validation Causale"),
                f"{m['r2']:.3f}",
                delta=f"{m['holdout_hours']}h holdout",
            )
            k2.metric("Holdout MAE", f"{m['mae']:.2f} kW", delta=f"{m['nmae_pct']:.1f}% nMAE", delta_color="off")
            k3.metric("Holdout RMSE", f"{m['rmse']:.2f} kW")
            k4.metric(
                bi(lg, f"Next {horizon_h}h Target", f"Prévision {horizon_h}h"),
                f"{total_fut_kwh:,.0f} kWh",
                delta=f"Peak {peak_fut_kw:,.1f} kW",
                delta_color="off",
            )
            k5.metric(
                bi(lg, f"Expected Net Grid ({horizon_h}h)", f"Import Réseau Prévu ({horizon_h}h)"),
                f"{expected_net_import_kwh:,.0f} kWh",
                delta=bi(lg, "Load − PV balance", "Bilan Charge − PV"),
                delta_color="off",
            )

            col_main, col_imp = st.columns([0.68, 0.32])
            with col_main:
                with st.container(border=True):
                    render_section_header(
                        bi(
                            lg,
                            "Strictly Causal Holdout Backtest & Ahead Forecast (P10–P90)",
                            "Validation Historique Causale & Prévision P10–P90",
                        )
                    )
                    t_label = "Load kW" if target_col == "load_kw" else "Solar PV kW"
                    c_hex = PALETTE["load"] if target_col == "load_kw" else PALETTE["pv"]
                    st.plotly_chart(
                        chart_forecast_horizon(fc_res["backtest_df"], fut_df, t_label, c_hex),
                        width="stretch",
                    )

            with col_imp:
                with st.container(border=True):
                    render_section_header(
                        bi(lg, "Permutation Feature Importance", "Importance des Variables (Permutation)")
                    )
                    st.plotly_chart(chart_feature_importance(fc_res["importance_df"]), width="stretch")

    with tab_sim:
        peak_ld = max(ctx.kpis["peak_load_kw"], 25.0)
        ref_pv = max(ctx.pv_capacity_kwp, peak_ld * 1.1, 25.0)
        max_pv_bound = float(max(round(ref_pv * 3.0, -1), 100.0))
        max_ess_bound = float(max(round(ref_pv * 4.5, -1), round(ctx.battery_capacity_kwh * 3.0, -1), 250.0))
        max_pcs_bound = float(max(round(max_ess_bound * 0.8, -1), round(peak_ld * 2.0, -1), 100.0))

        with st.container(border=True):
            top_l, top_r = st.columns([0.55, 0.45], vertical_alignment="center")
            with top_l:
                render_section_header(
                    bi(lg, "Configure Proposed PV + Battery ESS Architecture", "Architecture PV + Batterie Proposée")
                )
            with top_r:
                strat = st.selectbox(
                    bi(lg, "Sizing Strategy Preset", "Stratégie de Dimensionnement"),
                    options=["custom", "balanced", "peak_shaving", "zero_export"],
                    format_func=lambda s: {
                        "custom": bi(lg, "Manual Custom Sliders", "Réglage Manuel Personnalisé"),
                        "balanced": bi(lg, "✨ Auto-Size: Balanced High Autarky (~80%)", "✨ Auto : Haute Autonomie (~80%)"),
                        "peak_shaving": bi(lg, "⚡ Auto-Size: Evening Peak Shaving", "⚡ Auto : Écrêtement Pointe Soir"),
                        "zero_export": bi(lg, "🛡️ Auto-Size: Zero-Export Self-Use", "🛡️ Auto : Autoconsommation Sans Export"),
                    }[s],
                    key="sim_strategy_mode",
                    label_visibility="collapsed",
                )

            if strat != "custom":
                rec = recommend_optimal_sizing(ctx.df, strategy=strat)
                def_pv = float(min(rec["pv_kwp"], max_pv_bound))
                def_ess = float(min(rec["ess_kwh"], max_ess_bound))
                def_pcs = float(min(rec["ess_kw"], max_pcs_bound))
            else:
                def_pv = float(min(round(ref_pv * 1.25, 0), max_pv_bound))
                def_ess = float(min(round(max(ctx.battery_capacity_kwh * 1.35, ref_pv * 1.2), 0), max_ess_bound))
                def_pcs = float(min(round(max(ctx.battery_max_kw * 1.25, def_ess * 0.45, 20.0), 0), max_pcs_bound))

            pv_step = max(float(round(max_pv_bound / 60.0, 0)), 5.0)
            ess_step = max(float(round(max_ess_bound / 60.0, 0)), 10.0)
            pcs_step = max(float(round(max_pcs_bound / 50.0, 0)), 5.0)

            s1, s2, s3, s4, s5 = st.columns(5)
            with s1:
                sim_pv_kwp = st.slider(
                    bi(lg, "Target PV (kWp)", "Puissance PV (kWc)"),
                    min_value=0.0,
                    max_value=max_pv_bound,
                    value=def_pv,
                    step=pv_step,
                    key=f"sl_pv_{strat}_{ctx.site_label}",
                )
            with s2:
                sim_ess_kwh = st.slider(
                    bi(lg, "Battery Storage (kWh)", "Capacité BESS (kWh)"),
                    min_value=0.0,
                    max_value=max_ess_bound,
                    value=def_ess,
                    step=ess_step,
                    key=f"sl_ess_{strat}_{ctx.site_label}",
                )
            with s3:
                sim_ess_kw = st.slider(
                    bi(lg, "Max PCS Power (kW)", "Puissance PCS (kW)"),
                    min_value=0.0,
                    max_value=max_pcs_bound,
                    value=def_pcs if sim_ess_kwh > 0 else 0.0,
                    step=pcs_step,
                    key=f"sl_pcs_{strat}_{ctx.site_label}",
                )
            with s4:
                sim_rte = st.slider(
                    bi(lg, "Round-Trip Eff. (%)", "Rendement A/R (%)"),
                    min_value=78,
                    max_value=97,
                    value=92,
                    step=1,
                )
            with s5:
                sim_min_soc = st.slider(
                    bi(lg, "Min SoC Reserve (%)", "Réserve SoC Min (%)"),
                    min_value=5,
                    max_value=40,
                    value=15,
                    step=5,
                )

        sim_df = simulate_custom_sizing(
            df=ctx.df,
            baseline_pv_kwp=ctx.pv_capacity_kwp,
            target_pv_kwp=sim_pv_kwp,
            target_batt_kwh=sim_ess_kwh,
            target_batt_kw=sim_ess_kw,
            roundtrip_eff=sim_rte / 100.0,
            min_soc_pct=float(sim_min_soc),
        )
        sim_kpis = compute_executive_kpis(
            df=sim_df,
            pv_capacity_kwp=sim_pv_kwp,
            battery_capacity_kwh=sim_ess_kwh,
            tariff=ctx.tariff,
        )
        bk = ctx.kpis
        sym = ctx.tariff.symbol

        d1, d2, d3, d4 = st.columns(4)
        d1.metric(
            bi(lg, "Proposed Self-Sufficiency", "Autonomie Proposée"),
            f"{sim_kpis['self_sufficiency_pct']:.1f}%",
            delta=f"{sim_kpis['self_sufficiency_pct'] - bk['self_sufficiency_pct']:+.1f}% vs Baseline",
        )
        imp_delta_pct = (
            100.0 * (sim_kpis["grid_import_kwh"] - bk["grid_import_kwh"]) / max(bk["grid_import_kwh"], 1.0)
        )
        d2.metric(
            bi(lg, "Proposed Grid Import", "Import Réseau Proposé"),
            f"{sim_kpis['grid_import_kwh']:,.0f} kWh",
            delta=f"{imp_delta_pct:+.1f}% vs Baseline",
            delta_color="inverse",
        )
        d3.metric(
            bi(lg, "Proposed Net Grid Peak", "Pointe Réseau Proposée"),
            f"{sim_kpis['net_grid_peak_kw']:,.1f} kW",
            delta=f"{sim_kpis['net_grid_peak_kw'] - bk['net_grid_peak_kw']:+.1f} kW vs Baseline",
            delta_color="inverse",
        )
        d4.metric(
            bi(lg, "Proposed Window Savings", "Économies Période"),
            f"{sim_kpis['net_savings']:,.0f} {sym}",
            delta=f"{sim_kpis['net_savings'] - bk['net_savings']:+,.0f} {sym}",
        )

        with st.container(border=True):
            render_section_header(
                bi(
                    lg,
                    "7-Day Operational Dispatch Comparison (Baseline vs. Proposed Sizing)",
                    "Comparaison Opérationnelle sur 7 Jours (Référence vs Proposé)",
                )
            )
            st.plotly_chart(chart_battery_dispatch_comparison(ctx.df, sim_df), width="stretch")
