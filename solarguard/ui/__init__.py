"""Shared Streamlit UI context, caching wrappers, and trilingual (EN/FR/AR) sidebar orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import html
from typing import Any, Dict
import pandas as pd
import streamlit as st

from solarguard.analytics import compute_executive_kpis
from solarguard.anomaly import detect_energy_anomalies
from solarguard.config import (
    FACILITY_PRESETS,
    TARIFF_PROFILES,
    WILAYAS_CATALOG,
    TariffScheme,
    bi,
    preset_display_label,
    tariff_display_name,
    tr,
    wilaya_display_name,
)
from solarguard.data_generator import generate_facility_telemetry
from solarguard.data_loader import (
    auto_detect_mapping,
    normalize_custom_dataset,
    read_uploaded_table,
)
from solarguard.forecasting import run_energy_forecast
from solarguard.ui.theme import (
    inject_custom_css,
    inject_rtl_css,
    render_page_banner,
    render_section_header,
    render_sidebar_brand,
)

__all__ = [
    "AppContext",
    "inject_custom_css",
    "inject_rtl_css",
    "render_page_banner",
    "render_section_header",
    "render_sidebar_brand",
    "cached_generate_telemetry",
    "cached_detect_anomalies",
    "cached_run_forecast",
    "build_sidebar_and_context",
]

WINDOW_PRESET_LABELS = {
    "Full Dataset": ("Full Dataset", "Jeu Complet", "كامل البيانات"),
    "Q1 (Jan–Mar)": ("Q1 (Jan–Mar)", "T1 (Jan–Mar)", "الربع 1 (يناير–مارس)"),
    "Q2 (Apr–Jun)": ("Q2 (Apr–Jun)", "T2 (Avr–Juin)", "الربع 2 (أبريل–يونيو)"),
    "Q3 Peak Summer (Jul–Sep)": ("Q3 Peak Summer (Jul–Sep)", "T3 Été (Juil–Sep)", "الربع 3 ذروة الصيف (يوليو–سبتمبر)"),
    "Q4 (Oct–Dec)": ("Q4 (Oct–Dec)", "T4 (Oct–Déc)", "الربع 4 (أكتوبر–ديسمبر)"),
    "Custom Date Range": ("Custom Date Range", "Plage Personnalisée", "نطاق زمني مخصص"),
}


@dataclass
class AppContext:
    lang: str
    site_label: str
    sector_label: str
    wilaya_key: str
    pv_capacity_kwp: float
    battery_capacity_kwh: float
    battery_max_kw: float
    tariff: TariffScheme
    df: pd.DataFrame
    full_df: pd.DataFrame
    kpis: Dict[str, Any]
    is_custom_upload: bool


@st.cache_data(show_spinner=False)
def cached_generate_telemetry(preset_key: str, wilaya_key: str) -> pd.DataFrame:
    return generate_facility_telemetry(preset_key=preset_key, wilaya_override=wilaya_key, year=2026)


@st.cache_data(show_spinner=False)
def cached_detect_anomalies(
    df: pd.DataFrame,
    pv_kwp: float,
    contamination: float,
    avg_rate: float,
) -> Dict[str, Any]:
    return detect_energy_anomalies(
        df=df,
        pv_capacity_kwp=pv_kwp,
        contamination=contamination,
        avg_tariff_rate=avg_rate,
    )


@st.cache_data(show_spinner=False)
def cached_run_forecast(
    df: pd.DataFrame,
    target_col: str,
    horizon_hours: int,
) -> Dict[str, Any]:
    return run_energy_forecast(df=df, target_col=target_col, horizon_hours=horizon_hours)


def build_sidebar_and_context() -> AppContext:
    """Render shared sidebar controls and return active dataset + computed KPIs."""
    with st.sidebar:
        active_lang_hint = st.session_state.get("sg_lang") or "en"
        render_sidebar_brand(tr(active_lang_hint, "app_subtitle"), lang=active_lang_hint)

        lang = st.radio(
            "Language / Langue / اللغة",
            options=["en", "fr", "ar"],
            format_func=lambda k: {"en": "English", "fr": "Français", "ar": "العربية"}.get(k, k),
            horizontal=True,
            key="sg_lang",
            label_visibility="collapsed",
        )
        if lang == "ar":
            inject_rtl_css()

        st.divider()

        st.markdown(
            f'<div class="sg-sb-section">{html.escape(tr(lang, "sidebar_data_source"))}</div>',
            unsafe_allow_html=True,
        )
        source_mode = st.radio(
            "Source Mode",
            options=["preset", "upload"],
            format_func=lambda m: tr(lang, "mode_preset") if m == "preset" else tr(lang, "mode_upload"),
            key="sg_source_mode",
            label_visibility="collapsed",
        )

        is_custom = False
        if source_mode == "preset":
            preset_keys = list(FACILITY_PRESETS.keys())
            sel_preset_key = st.selectbox(
                bi(lang, "Facility Profile", "Profil du Site", "ملف المنشأة"),
                options=preset_keys,
                format_func=lambda k: preset_display_label(FACILITY_PRESETS[k], lang),
                key="sg_preset_key",
            )
            preset = FACILITY_PRESETS[sel_preset_key]

            wilaya_keys = list(WILAYAS_CATALOG.keys())
            default_w_idx = wilaya_keys.index(preset.wilaya) if preset.wilaya in wilaya_keys else 0
            sel_wilaya = st.selectbox(
                bi(
                    lang,
                    "Climatic Wilaya (Solar Atlas)",
                    "Wilaya Climatique (Atlas Solaire)",
                    "الولاية المناخية (الأطلس الشمسي)",
                ),
                options=wilaya_keys,
                index=default_w_idx,
                format_func=lambda k: f"{WILAYAS_CATALOG[k].code} - {wilaya_display_name(WILAYAS_CATALOG[k], lang)}",
                key=f"sg_wilaya_{sel_preset_key}",
            )

            full_df = cached_generate_telemetry(sel_preset_key, sel_wilaya)
            site_label = preset_display_label(preset, lang).split("(")[0].strip()
            sector_label = preset.sector
            pv_kwp = preset.pv_capacity_kwp
            batt_kwh = preset.battery_capacity_kwh
            batt_kw = preset.battery_max_kw
        else:
            uploaded = st.file_uploader(
                bi(lang, "CSV / Excel (.xlsx)", "CSV / Excel (.xlsx)", "ملف CSV / Excel (.xlsx)"),
                type=["csv", "xlsx", "xls"],
                key="sg_uploader",
            )
            sel_wilaya = st.selectbox(
                bi(lang, "Reference Wilaya Climate", "Wilaya de Référence", "الولاية المرجعية للمناخ"),
                options=list(WILAYAS_CATALOG.keys()),
                format_func=lambda k: f"{WILAYAS_CATALOG[k].code} - {wilaya_display_name(WILAYAS_CATALOG[k], lang)}",
                key="sg_upload_wilaya",
            )
            if uploaded is not None:
                try:
                    raw_df = read_uploaded_table(uploaded.getvalue(), uploaded.name)
                    auto_map = auto_detect_mapping(list(raw_df.columns))
                    cols_with_none = [None] + list(raw_df.columns)

                    with st.expander(
                        bi(lang, "Column Mapping & Units", "Correspondance des Colonnes", "ربط الأعمدة والوحدات"),
                        expanded=False,
                    ):
                        ts_col = st.selectbox(
                            bi(lang, "Timestamp Column", "Colonne Horodatage", "عمود التاريخ والوقت"),
                            options=list(raw_df.columns),
                            index=list(raw_df.columns).index(auto_map["timestamp"])
                            if auto_map["timestamp"] in raw_df.columns
                            else 0,
                        )
                        ld_col = st.selectbox(
                            bi(lang, "Load / Consumption Column", "Colonne Consommation", "عمود الاستهلاك الكهربائي"),
                            options=cols_with_none,
                            index=cols_with_none.index(auto_map["load_kw"])
                            if auto_map["load_kw"] in cols_with_none
                            else 0,
                        )
                        pv_col = st.selectbox(
                            bi(lang, "Solar PV Power Column", "Colonne Production PV", "عمود إنتاج الطاقة الشمسية"),
                            options=cols_with_none,
                            index=cols_with_none.index(auto_map["pv_ac_kw"])
                            if auto_map["pv_ac_kw"] in cols_with_none
                            else 0,
                        )
                        irr_col = st.selectbox(
                            bi(lang, "Irradiance (W/m²) Column", "Colonne Irradiance (W/m²)", "عمود الإشعاع الشمسي (W/m²)"),
                            options=cols_with_none,
                            index=cols_with_none.index(auto_map["irradiance_wm2"])
                            if auto_map["irradiance_wm2"] in cols_with_none
                            else 0,
                        )
                        unit_label = st.selectbox(
                            bi(lang, "Power Unit", "Unité de Puissance", "وحدة القدرة"),
                            ["kW / kWh", "W / Wh (÷1000)", "MW / MWh (×1000)"],
                        )
                        unit_mult = 0.001 if "W /" in unit_label else (1000.0 if "MW" in unit_label else 1.0)
                        user_kwp = st.number_input(
                            bi(lang, "Installed PV (kWp, 0 = auto)", "PV Installé (kWc, 0 = auto)", "قدرة الألواح (kWp، 0 = تلقائي)"),
                            min_value=0.0,
                            value=0.0,
                            step=10.0,
                        )
                        user_ess = st.number_input(
                            bi(lang, "Battery ESS (kWh)", "Batterie BESS (kWh)", "سعة البطارية (kWh)"),
                            min_value=0.0,
                            value=0.0,
                            step=25.0,
                        )

                    user_map = {
                        "timestamp": ts_col,
                        "load_kw": ld_col,
                        "pv_ac_kw": pv_col,
                        "irradiance_wm2": irr_col,
                        "ambient_temp_c": auto_map.get("ambient_temp_c"),
                        "cell_temp_c": auto_map.get("cell_temp_c"),
                        "battery_soc_pct": auto_map.get("battery_soc_pct"),
                    }
                    full_df, meta = normalize_custom_dataset(
                        raw_df=raw_df,
                        mapping=user_map,
                        unit_multiplier=unit_mult,
                        assumed_pv_kwp=user_kwp if user_kwp > 0 else None,
                        assumed_battery_kwh=user_ess,
                        assumed_battery_kw=user_ess * 0.5,
                    )
                    site_label = uploaded.name
                    sector_label = "Custom Uploaded Telemetry"
                    pv_kwp = user_kwp if user_kwp > 0 else meta["inferred_pv_kwp"]
                    batt_kwh = user_ess
                    batt_kw = user_ess * 0.5
                    is_custom = True
                    st.success(
                        bi(
                            lang,
                            f"Loaded {meta['hourly_rows']:,} hourly rows ({meta['completeness_pct']}% valid).",
                            f"{meta['hourly_rows']:,} lignes horaires chargées ({meta['completeness_pct']}% valides).",
                            f"تم تحميل {meta['hourly_rows']:,} سجل ساعي ({meta['completeness_pct']}% مكتمل).",
                        )
                    )
                except Exception as exc:
                    st.error(
                        bi(
                            lang,
                            f"Upload parse error: {exc}. Showing Oran reference dataset.",
                            f"Erreur de lecture : {exc}. Affichage du site d'Oran.",
                            f"خطأ في قراءة الملف: {exc}. يتم عرض بيانات وهران المرجعية.",
                        )
                    )
                    full_df = cached_generate_telemetry("oran_industrial", sel_wilaya)
                    site_label = bi(lang, "Oran Industrial Plant", "Usine Industrielle d'Oran", "المصنع الصناعي بوهران")
                    sector_label = "Industrial Manufacturing"
                    pv_kwp = 250.0
                    batt_kwh = 300.0
                    batt_kw = 120.0
            else:
                st.info(
                    bi(
                        lang,
                        "Upload any CSV/XLSX above, or explore with the active Oran dataset.",
                        "Importez un fichier CSV/XLSX ci-dessus, ou explorez le jeu de données d'Oran.",
                        "ارفع ملف CSV أو Excel أعلاه، أو استكشف المنصة عبر بيانات وهران المرجعية.",
                    )
                )
                full_df = cached_generate_telemetry("oran_industrial", sel_wilaya)
                site_label = bi(lang, "Oran Industrial Plant", "Usine Industrielle d'Oran", "المصنع الصناعي بوهران")
                sector_label = "Industrial Manufacturing"
                pv_kwp = 250.0
                batt_kwh = 300.0
                batt_kw = 120.0

        st.divider()
        st.markdown(
            f'<div class="sg-sb-section">{html.escape(tr(lang, "date_window"))}</div>',
            unsafe_allow_html=True,
        )
        min_date = full_df["timestamp"].min().date()
        max_date = full_df["timestamp"].max().date()

        window_preset = st.selectbox(
            "Period Preset",
            options=list(WINDOW_PRESET_LABELS.keys()),
            format_func=lambda opt: bi(lang, *WINDOW_PRESET_LABELS[opt]),
            key="sg_window_preset",
            label_visibility="collapsed",
        )

        if window_preset == "Custom Date Range":
            date_sel = st.date_input(
                bi(lang, "Select Range", "Sélectionner la Période", "اختر النطاق الزمني"),
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="sg_custom_dates",
            )
            if isinstance(date_sel, (tuple, list)) and len(date_sel) == 2:
                d_start, d_end = date_sel[0], date_sel[1]
            else:
                d_start, d_end = min_date, max_date
            filtered_df = full_df.loc[
                (full_df["timestamp"].dt.date >= d_start) & (full_df["timestamp"].dt.date <= d_end)
            ].reset_index(drop=True)
        elif window_preset.startswith("Q1"):
            filtered_df = full_df.loc[full_df["timestamp"].dt.month.isin([1, 2, 3])].reset_index(drop=True)
        elif window_preset.startswith("Q2"):
            filtered_df = full_df.loc[full_df["timestamp"].dt.month.isin([4, 5, 6])].reset_index(drop=True)
        elif window_preset.startswith("Q3"):
            filtered_df = full_df.loc[full_df["timestamp"].dt.month.isin([7, 8, 9])].reset_index(drop=True)
        elif window_preset.startswith("Q4"):
            filtered_df = full_df.loc[full_df["timestamp"].dt.month.isin([10, 11, 12])].reset_index(drop=True)
        else:
            filtered_df = full_df

        if len(filtered_df) < 24:
            if window_preset != "Full Dataset":
                st.caption(
                    bi(
                        lang,
                        "⚠️ Selected window has <24h in dataset; showing full dataset.",
                        "⚠️ La période choisie contient <24h ; affichage complet.",
                        "⚠️ الفترة المختارة أقل من 24 ساعة؛ يتم عرض كامل البيانات.",
                    )
                )
            filtered_df = full_df

        st.markdown(
            f'<div class="sg-sb-section" style="margin-top:0.55rem;">{html.escape(tr(lang, "tariff_profile"))}</div>',
            unsafe_allow_html=True,
        )
        tariff_keys = list(TARIFF_PROFILES.keys())
        sel_tariff_key = st.selectbox(
            "Tariff",
            options=tariff_keys,
            format_func=lambda k: tariff_display_name(TARIFF_PROFILES[k], lang),
            key="sg_tariff_key",
            label_visibility="collapsed",
        )
        tariff = TARIFF_PROFILES[sel_tariff_key]

        t_start = filtered_df["timestamp"].min().strftime("%Y-%m-%d")
        t_end = filtered_df["timestamp"].max().strftime("%Y-%m-%d")
        active_lbl = bi(lang, "telemetry active", "mesures actives", "ساعة قياس نشطة")
        st.markdown(
            f"""
            <div class="sg-sb-status">
                <strong style="color:#F8FAFC;"><span class="sg-ltr">{len(filtered_df):,} h</span></strong> {active_lbl}<br/>
                <span style="color:#94A3B8;" class="sg-ltr">{t_start} → {t_end}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    kpis = compute_executive_kpis(
        df=filtered_df,
        pv_capacity_kwp=pv_kwp,
        battery_capacity_kwh=batt_kwh,
        tariff=tariff,
    )

    return AppContext(
        lang=lang,
        site_label=site_label,
        sector_label=sector_label,
        wilaya_key=sel_wilaya,
        pv_capacity_kwp=pv_kwp,
        battery_capacity_kwh=batt_kwh,
        battery_max_kw=batt_kw,
        tariff=tariff,
        df=filtered_df,
        full_df=full_df,
        kpis=kpis,
        is_custom_upload=is_custom,
    )
