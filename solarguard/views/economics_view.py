"""Page 5: Financial ROI, Sonelgaz/C&I Tariff Billing Audit, LCOE, and 25-Year Cash Flow."""

from __future__ import annotations

import streamlit as st

from solarguard.charts import chart_cashflow_projection, chart_monthly_bills
from solarguard.config import bi
from solarguard.economics import compute_lifecycle_economics
from solarguard.ui import AppContext, render_page_banner, render_section_header


def render_economics_page(ctx: AppContext) -> None:
    lg = ctx.lang
    render_page_banner(
        ctx,
        page_title=bi(
            lg,
            "Financial ROI, Tariff Billing Audit & 25-Year Lifecycle Cash Flow",
            "Rentabilité Financière, Audit Tarifaire & Bilan Carbone 25 Ans",
            "العائد على الاستثمار، التدقيق التعريفي والتدفقات النقدية لـ 25 سنة",
        ),
        subtitle=bi(
            lg,
            "Complete CAPEX/OPEX modeling, Net Present Value (NPV), IRR, PV & Hybrid LCOE, payback horizon, and monthly bill audit.",
            "Modélisation CAPEX/OPEX complète, VAN (NPV), TRI (IRR), LCOE PV & Hybride, temps de retour et facturation mensuelle.",
            "نمذجة متكاملة للتكاليف الرأسمالية والتشغيلية، صافي القيمة الحالية (NPV)، معدل العائد الداخلي (IRR)، التكلفة المستوية للطاقة (LCOE) والفواتير الشهرية.",
        ),
    )

    t = ctx.tariff
    sym = t.symbol

    with st.container(border=True):
        render_section_header(
            bi(
                lg,
                f"Economic & Capital Cost Assumptions ({t.currency})",
                f"Hypothèses Économiques & CAPEX ({t.currency})",
                f"الافتراضات الاقتصادية والتكاليف الاستثمارية ({t.currency})",
            )
        )
        p1, p2, p3, p4, p5, p6 = st.columns(6)
        step_capex = 2000.0 if t.currency == "DZD" else 25.0
        with p1:
            pv_capex = st.number_input(
                bi(lg, f"PV CAPEX ({sym}/kWp)", f"CAPEX PV ({sym}/kWc)", f"تكلفة الألواح ({sym}/kWp)"),
                min_value=0.0,
                value=float(t.default_pv_capex_per_kwp),
                step=step_capex,
                key=f"ec_pv_{t.key}",
            )
        with p2:
            ess_capex = st.number_input(
                bi(lg, f"ESS CAPEX ({sym}/kWh)", f"CAPEX BESS ({sym}/kWh)", f"تكلفة البطاريات ({sym}/kWh)"),
                min_value=0.0,
                value=float(t.default_ess_capex_per_kwh),
                step=step_capex * 0.5,
                key=f"ec_ess_{t.key}",
            )
        with p3:
            subsidy_pct = st.slider(
                bi(lg, "Grant / Incentive (%)", "Subvention / Prime (%)", "نسبة الدعم / المنحة (%)"),
                min_value=0,
                max_value=50,
                value=10 if t.currency == "DZD" else 0,
                step=5,
            )
        with p4:
            disc_rate = st.slider(
                bi(lg, "Discount Rate (%)", "Taux d'Actualisation (%)", "معدل الخصم (%)"),
                min_value=2.0,
                max_value=15.0,
                value=7.0,
                step=0.5,
            )
        with p5:
            esc_rate = st.slider(
                bi(lg, "Tariff Escalation (%/yr)", "Inflation Tarif (%/an)", "تضخم التعريفة (%/سنة)"),
                min_value=0.0,
                max_value=12.0,
                value=4.5,
                step=0.5,
            )
        with p6:
            co2_price = st.number_input(
                bi(lg, f"Carbon Credit ({sym}/tCO₂)", f"Crédit Carbone ({sym}/tCO₂)", f"سعر الكربون ({sym}/طن)"),
                min_value=0.0,
                value=0.0,
                step=500.0 if t.currency == "DZD" else 10.0,
                key=f"ec_co2_{t.key}",
            )

    econ = compute_lifecycle_economics(
        df=ctx.df,
        tariff=t,
        pv_capacity_kwp=ctx.pv_capacity_kwp,
        battery_capacity_kwh=ctx.battery_capacity_kwh,
        pv_capex_per_kwp=pv_capex,
        ess_capex_per_kwh=ess_capex,
        subsidy_pct=float(subsidy_pct),
        discount_rate_pct=float(disc_rate),
        tariff_escalation_pct=float(esc_rate),
        carbon_price_per_ton=float(co2_price),
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(
        bi(lg, "Net Initial CAPEX", "CAPEX Initial Net", "صافي الاستثمار الأولي"),
        f"{econ['net_capex']:,.0f} {sym}",
        delta=f"Yr-1 Sav: {econ['yr1_savings']:,.0f}",
    )
    k2.metric(
        bi(lg, "25-Yr Net Present Value", "VAN (NPV 25 Ans)", "صافي القيمة الحالية (NPV)"),
        f"{econ['npv']:,.0f} {sym}",
        delta=bi(
            lg,
            "Value accretive" if econ["npv"] >= 0 else "Below hurdle rate",
            "Créateur de valeur" if econ["npv"] >= 0 else "Sous le taux cible",
            "استثمار مجدٍ اقتصادياً" if econ["npv"] >= 0 else "أقل من عائد الخصم",
        ),
        delta_color="normal" if econ["npv"] >= 0 else "inverse",
    )
    k3.metric(
        bi(lg, "Internal Rate of Return", "TRI (IRR)", "معدل العائد الداخلي (IRR)"),
        f"{econ['irr_pct']:.1f}%" if econ["irr_pct"] is not None else "N/A",
        delta=f"vs {disc_rate:.1f}% WACC",
    )
    k4.metric(
        bi(lg, "Simple Payback", "Temps de Retour", "فترة الاسترداد البسيطة"),
        f"{econ['simple_payback_yr']:.1f} yrs" if econ["simple_payback_yr"] is not None else "> 25 yrs",
        delta=(
            f"Disc: {econ['discounted_payback_yr']:.1f} yrs"
            if econ["discounted_payback_yr"] is not None
            else "Disc: >25 yrs"
        ),
        delta_color="off",
    )
    k5.metric(
        bi(lg, "PV Generation LCOE", "LCOE Solaire PV", "التكلفة المستوية للطاقة (LCOE)"),
        f"{econ['lcoe']:.2f} {sym}/kWh",
        delta=f"PV+ESS: {econ['hybrid_lcoe']:.2f} {sym}",
        delta_color="off",
        help=bi(
            lg,
            "Pure PV generation LCOE vs. combined PV+ESS hybrid LCOE.",
            "Coût actualisé du kWh solaire seul vs système hybride complet PV+BESS.",
            "التكلفة المستوية لإنتاج الكيلوواط ساعة الشمسي مقابل النظام الهجين الشامل للبطاريات.",
        ),
    )
    k6.metric(
        bi(lg, "25-Yr CO₂ Offset", "CO₂ Évité (25 Ans)", "خفض الكربون خلال 25 سنة"),
        f"{econ['total_co2_tons_25yr']:,.0f} t",
        delta=bi(lg, "Lifecycle clean yield", "Bilan cycle de vie", "حصيلة دورة الحياة النظيفة"),
    )

    col_cf, col_mb = st.columns([0.54, 0.46])
    with col_cf:
        with st.container(border=True):
            render_section_header(
                bi(
                    lg,
                    "25-Year Cumulative & Discounted Cash Flow",
                    "Projection des Flux de Trésorerie sur 25 Ans",
                    "التدفقات النقدية التراكمية والمخصومة على مدى 25 سنة",
                )
            )
            st.caption(
                bi(
                    lg,
                    "Includes annual PV linear degradation (0.5%/yr), O&M escalation, and Year-12 inverter/ESS refurbishment.",
                    "Inclut la dégradation linéaire PV (0,5%/an), la maintenance O&M et le renouvellement onduleur/batterie à l'année 12.",
                    "يتضمن التدهور السنوي للألواح (0.5%/سنة)، تكاليف الصيانة وتجديد العواكس والبطاريات في السنة 12.",
                )
            )
            st.plotly_chart(chart_cashflow_projection(econ["cashflow_df"], sym), width="stretch")

    with col_mb:
        with st.container(border=True):
            render_section_header(
                bi(
                    lg,
                    "Monthly Bill Audit: Grid Baseline vs. SolarGuard",
                    "Comparaison Mensuelle des Factures Électriques",
                    "مقارنة الفواتير الشهرية: الشبكة المرجعية مقابل نظام SolarGuard",
                )
            )
            st.caption(
                bi(
                    lg,
                    f"ToU Rates — Off-Peak: {t.off_peak_rate} {sym} • Shoulder: {t.shoulder_rate} {sym} • Evening Peak: {t.peak_rate} {sym}/kWh.",
                    f"Tarifs ToU — Creuses : {t.off_peak_rate} {sym} • Pleines : {t.shoulder_rate} {sym} • Pointe : {t.peak_rate} {sym}/kWh.",
                    f"التعريفة الساعية — خارج الذروة: {t.off_peak_rate} {sym} • العادية: {t.shoulder_rate} {sym} • الذروة: {t.peak_rate} {sym}/kWh.",
                )
            )
            st.plotly_chart(chart_monthly_bills(econ["monthly_df"], sym), width="stretch")

    with st.expander(
        bi(
            lg,
            "View Full 25-Year Financial Cash-Flow Schedule",
            "Voir l'Échéancier Financier Complet sur 25 Ans",
            "عرض الجدول المالي التفصيلي للتدفقات النقدية على مدى 25 سنة",
        )
    ):
        st.dataframe(econ["cashflow_df"], width="stretch", hide_index=True)
