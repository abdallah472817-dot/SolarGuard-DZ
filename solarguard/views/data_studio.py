"""Page 6: Data Quality Studio, Correlation Matrix, Telemetry Explorer & Audit Exports."""

from __future__ import annotations

import numpy as np
import streamlit as st

from solarguard.charts import chart_correlation_heatmap
from solarguard.config import WILAYAS_CATALOG, bi, wilaya_display_name
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
            "استوديو البيانات، التدقيق الإحصائي وتصدير التقارير",
        ),
        subtitle=bi(
            lg,
            "Hourly telemetry inspector, multivariate correlation matrix, descriptive statistics, and 1-click audit exports.",
            "Exploration des séries horaires, matrice de corrélation, contrôle qualité et exports Excel / CSV / HTML.",
            "مستكشف القياسات الساعية، مصفوفة ارتباط بيرسون، الإحصاءات الوصفية وتصدير تقارير التدقيق بضغطة واحدة.",
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
                "مركز تصدير تقارير التدقيق التنفيذية والبيانات الهندسية",
            )
        )
        st.caption(
            bi(
                lg,
                "Download formatted multi-sheet Excel workbooks, anomaly-annotated CSV logs, printable HTML reports, or an upload template.",
                "Téléchargez le classeur d'audit Excel multi-feuilles, les données annotées CSV, le rapport exécutif HTML ou un modèle CSV.",
                "حمّل مصنف التدقيق متعدد الأوراق بصيغة Excel، أو السجلات المصنفة بصيغة CSV، أو التقرير التنفيذي للطباعة بصيغة HTML، أو نموذج الرفع.",
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
        w_obj = WILAYAS_CATALOG.get(ctx.wilaya_key, WILAYAS_CATALOG["Oran"])
        w_name = wilaya_display_name(w_obj, lg)
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
                label=bi(lg, "📊 Excel Audit (.xlsx)", "📊 Audit Excel (.xlsx)", "📊 مصنف تدقيق Excel (.xlsx)"),
                data=xlsx_bytes,
                file_name="SolarGuard_DZ_Energy_Audit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                width="stretch",
            )
        with b2:
            st.download_button(
                label=bi(lg, "📄 Enriched Telemetry (.csv)", "📄 Télémesures Annotées (.csv)", "📄 القياسات المصنفة (.csv)"),
                data=csv_bytes,
                file_name="SolarGuard_DZ_Telemetry_Annotated.csv",
                mime="text/csv",
                width="stretch",
            )
        with b3:
            st.download_button(
                label=bi(lg, "🖨️ Executive Report (.html)", "🖨️ Rapport Exécutif (.html)", "🖨️ التقرير التنفيذي (.html)"),
                data=html_str.encode("utf-8"),
                file_name="SolarGuard_DZ_Executive_Report.html",
                mime="text/html",
                width="stretch",
            )
        with b4:
            st.download_button(
                label=bi(lg, "📥 Sample Upload Template", "📥 Modèle CSV d'Import", "📥 نموذج CSV جاهز للرفع"),
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
            render_section_header(
                bi(
                    lg,
                    "Descriptive Engineering Statistics",
                    "Statistiques Descriptives des Capteurs",
                    "الإحصاءات الهندسية الوصفية لقنوات القياس",
                )
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
            render_section_header(
                bi(
                    lg,
                    "Multivariate Pearson Correlation Matrix",
                    "Matrice de Corrélation de Pearson",
                    "مصفوفة الارتباط متعدد المتغيرات (بيرسون)",
                )
            )
            corr = ctx.df[avail_cols].corr().fillna(0.0).round(2)
            short_labels = [
                c.replace("_wm2", "").replace("_kw", "").replace("_pct", "%").replace("_c", "°C")
                for c in avail_cols
            ]
            st.plotly_chart(chart_correlation_heatmap(corr, short_labels), width="stretch")

    with st.container(border=True):
        hdr_l, hdr_r = st.columns([0.65, 0.35], vertical_alignment="center")
        with hdr_l:
            render_section_header(
                bi(
                    lg,
                    "Hourly SCADA / Smart-Meter Telemetry Explorer",
                    "Explorateur des Séries Horaires SCADA",
                    "مستكشف السجلات الساعية لنظام SCADA والعدادات الذكية",
                )
            )
        with hdr_r:
            only_anom = st.toggle(
                bi(
                    lg,
                    "Show Flagged Anomalies Only",
                    "Afficher Uniquement les Anomalies",
                    "عرض الساعات الشاذة فقط",
                ),
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
                f"يتم عرض {len(view_df):,} سطر"
                + ("" if only_anom else " (أول 500 سطر للعرض السريع؛ استخدم زر تصدير CSV أعلاه لتحميل السجل الكامل)."),
            )
        )
        st.dataframe(view_df[display_cols], width="stretch", hide_index=True, height=340)
