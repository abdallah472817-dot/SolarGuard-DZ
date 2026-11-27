"""Page 6: Data Quality Studio, Correlation Matrix, Telemetry Explorer & Audit Exports."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from solarguard.charts import _apply_solar_layout
from solarguard.config import WILAYAS_CATALOG, bi
from solarguard.economics import compute_lifecycle_economics
from solarguard.exporter import (
    build_excel_audit_workbook,
    build_html_audit_report,
    build_sample_csv_template,
)
from solarguard.ui import AppContext, cached_detect_anomalies, render_page_banner, render_section_header


def render_data_studio_page(ctx: AppContext) -> None:
    lg = ctx.lang
    render_page_banner(
        ctx,
        page_title=bi(
            lg,
            "Data Studio, Statistical Audit & Report Exports",
            "Studio de Données, Statistiques & Rapports d'Audit",
        ),
        subtitle=bi(
            lg,
            "Hourly telemetry inspector, multivariate correlation matrix, descriptive statistics, and 1-click audit exports.",
            "Exploration des séries horaires, matrice de corrélation, contrôle qualité et exports Excel / CSV / HTML.",
        ),
    )

    t = ctx.tariff
    sym = t.symbol
    avg_rate = 0.5 * (t.shoulder_rate + t.peak_rate)

    anom_res = cached_detect_anomalies(ctx.df, ctx.pv_capacity_kwp, 0.025, avg_rate)
    annotated_df = anom_res["annotated_df"]
    incidents_df = anom_res["incidents_df"]

    econ = compute_lifecycle_economics(
        df=ctx.df,
        tariff=t,
        pv_capacity_kwp=ctx.pv_capacity_kwp,
        battery_capacity_kwh=ctx.battery_capacity_kwh,
        pv_capex_per_kwp=t.default_pv_capex_per_kwp,
        ess_capex_per_kwh=t.default_ess_capex_per_kwh,
    )

    with st.container(border=True):
        render_section_header(
            bi(
                lg,
                "Executive Audit & Telemetry Export Center",
                "Centre d'Exportation des Rapports d'Audit",
            )
        )
        st.caption(
            bi(
                lg,
                "Download formatted multi-sheet Excel workbooks, anomaly-annotated CSV logs, printable HTML reports, or an upload template.",
                "Téléchargez le classeur d'audit Excel multi-feuilles, les données annotées CSV, le rapport exécutif HTML ou un modèle CSV.",
            )
        )

        xlsx_bytes = build_excel_audit_workbook(
            site_label=ctx.site_label,
            kpis=ctx.kpis,
            monthly_df=econ["monthly_df"],
            incidents_df=incidents_df,
            cashflow_df=econ["cashflow_df"],
            annotated_df=annotated_df,
            currency_symbol=sym,
        )
        csv_bytes = annotated_df.to_csv(index=False).encode("utf-8")
        w_name = WILAYAS_CATALOG.get(ctx.wilaya_key, WILAYAS_CATALOG["Oran"]).name
        html_str = build_html_audit_report(
            site_label=ctx.site_label,
            wilaya_name=w_name,
            kpis=ctx.kpis,
            econ=econ,
            anom_summary=anom_res["summary"],
            incidents_df=incidents_df,
            currency_symbol=sym,
        )
        tpl_bytes = build_sample_csv_template()

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.download_button(
                label=bi(lg, "📊 Excel Audit (.xlsx)", "📊 Audit Excel (.xlsx)"),
                data=xlsx_bytes,
                file_name="SolarGuard_DZ_Energy_Audit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                width="stretch",
            )
        with b2:
            st.download_button(
                label=bi(lg, "📄 Enriched Telemetry (.csv)", "📄 Télémesures Annotées (.csv)"),
                data=csv_bytes,
                file_name="SolarGuard_DZ_Telemetry_Annotated.csv",
                mime="text/csv",
                width="stretch",
            )
        with b3:
            st.download_button(
                label=bi(lg, "🖨️ Executive Report (.html)", "🖨️ Rapport Exécutif (.html)"),
                data=html_str.encode("utf-8"),
                file_name="SolarGuard_DZ_Executive_Report.html",
                mime="text/html",
                width="stretch",
            )
        with b4:
            st.download_button(
                label=bi(lg, "📥 Sample Upload Template", "📥 Modèle CSV d'Import"),
                data=tpl_bytes,
                file_name="SolarGuard_Upload_Template.csv",
                mime="text/csv",
                width="stretch",
            )

    stat_cols = [
        "irradiance_wm2",
        "ambient_temp_c",
        "cell_temp_c",
        "pv_ac_kw",
        "load_kw",
        "power_factor",
        "battery_soc_pct",
        "grid_import_kw",
        "grid_export_kw",
    ]
    avail_cols = [c for c in stat_cols if c in ctx.df.columns]

    col_stat, col_corr = st.columns([0.55, 0.45])
    with col_stat:
        with st.container(border=True):
            st.markdown(
                f'<div class="sg-section-hdr">{bi(lg, "Descriptive Engineering Statistics", "Statistiques Descriptives des Capteurs")}</div>',
                unsafe_allow_html=True,
            )
            desc = (
                ctx.df[avail_cols]
                .agg(
                    [
                        "mean",
                        "std",
                        "min",
                        lambda s: np.percentile(s, 10),
                        "median",
                        lambda s: np.percentile(s, 90),
                        "max",
                    ]
                )
                .T
            )
            desc.columns = ["Mean", "Std Dev", "Min", "P10", "Median", "P90", "Max"]
            desc = desc.round(2).reset_index().rename(columns={"index": "Telemetry Channel"})
            st.dataframe(desc, width="stretch", hide_index=True, height=345)

    with col_corr:
        with st.container(border=True):
            st.markdown(
                f'<div class="sg-section-hdr">{bi(lg, "Multivariate Pearson Correlation Matrix", "Matrice de Corrélation de Pearson")}</div>',
                unsafe_allow_html=True,
            )
            corr = ctx.df[avail_cols].corr().fillna(0.0).round(2)
            short_labels = [
                c.replace("_wm2", "").replace("_kw", "").replace("_pct", "%").replace("_c", "°C")
                for c in avail_cols
            ]
            fig_corr = go.Figure(
                data=go.Heatmap(
                    z=corr.values,
                    x=short_labels,
                    y=short_labels,
                    zmin=-1,
                    zmax=1,
                    colorscale="RdBu_r",
                    text=corr.values,
                    texttemplate="%{text:.2f}",
                    textfont=dict(size=10),
                )
            )
            _apply_solar_layout(fig_corr, height=345, hovermode="closest")
            st.plotly_chart(fig_corr, width="stretch")

    with st.container(border=True):
        hdr_l, hdr_r = st.columns([0.65, 0.35], vertical_alignment="center")
        with hdr_l:
            st.markdown(
                f'<div class="sg-section-hdr">{bi(lg, "Hourly SCADA / Smart-Meter Telemetry Explorer", "Explorateur des Séries Horaires SCADA")}</div>',
                unsafe_allow_html=True,
            )
        with hdr_r:
            only_anom = st.toggle(
                bi(lg, "Show Flagged Anomalies Only", "Afficher Uniquement les Anomalies"),
                value=False,
            )

        view_df = annotated_df.loc[annotated_df["is_anomaly"]] if only_anom else annotated_df.head(500)
        display_cols = [
            "timestamp",
            "irradiance_wm2",
            "ambient_temp_c",
            "cell_temp_c",
            "pv_ac_kw",
            "expected_pv_kw",
            "load_kw",
            "battery_soc_pct",
            "grid_import_kw",
            "grid_export_kw",
            "anomaly_type",
            "energy_impact_kwh",
        ]
        display_cols = [c for c in display_cols if c in view_df.columns]
        st.caption(
            bi(
                lg,
                f"Displaying {len(view_df):,} rows"
                + ("" if only_anom else " (first 500 rows shown; use CSV download above for full export)."),
                f"Affichage de {len(view_df):,} lignes"
                + ("" if only_anom else " (500 premières lignes affichées ; utilisez l'export CSV complet ci-dessus)."),
            )
        )
        st.dataframe(view_df[display_cols], width="stretch", hide_index=True, height=340)
