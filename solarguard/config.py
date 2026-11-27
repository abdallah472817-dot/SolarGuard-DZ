"""Domain configuration: Algerian climatic atlas, facility presets, tariffs, and EN/FR/AR i18n."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class WilayaProfile:
    code: str
    name: str
    zone: str
    lat: float
    lon: float
    elevation_m: int
    annual_ghi_kwh_m2: float
    optimal_tilt_deg: int
    avg_temp_summer_c: float
    avg_temp_winter_c: float
    soiling_risk: str  # Low, Moderate, High, Extreme
    base_soiling_rate_pct_day: float
    name_ar: str = ""
    zone_ar: str = ""


WILAYAS_CATALOG: Dict[str, WilayaProfile] = {
    "Oran": WilayaProfile(
        code="31",
        name="Oran",
        name_ar="وهران",
        zone="Mediterranean Coast",
        zone_ar="الساحل المتوسطي الغربي",
        lat=35.697,
        lon=-0.630,
        elevation_m=101,
        annual_ghi_kwh_m2=1865.0,
        optimal_tilt_deg=31,
        avg_temp_summer_c=27.8,
        avg_temp_winter_c=12.4,
        soiling_risk="Moderate",
        base_soiling_rate_pct_day=0.14,
    ),
    "Algiers": WilayaProfile(
        code="16",
        name="Algiers (Alger)",
        name_ar="الجزائر العاصمة",
        zone="Mediterranean Coast",
        zone_ar="الساحل المتوسطي الأوسط",
        lat=36.753,
        lon=3.058,
        elevation_m=59,
        annual_ghi_kwh_m2=1785.0,
        optimal_tilt_deg=32,
        avg_temp_summer_c=27.1,
        avg_temp_winter_c=11.9,
        soiling_risk="Low",
        base_soiling_rate_pct_day=0.11,
    ),
    "Constantine": WilayaProfile(
        code="25",
        name="Constantine",
        name_ar="قسنطينة",
        zone="Tell Atlas Inland",
        zone_ar="الأطلس التلي الداخلي",
        lat=36.365,
        lon=6.614,
        elevation_m=694,
        annual_ghi_kwh_m2=1830.0,
        optimal_tilt_deg=32,
        avg_temp_summer_c=28.4,
        avg_temp_winter_c=7.8,
        soiling_risk="Low",
        base_soiling_rate_pct_day=0.12,
    ),
    "Annaba": WilayaProfile(
        code="23",
        name="Annaba",
        name_ar="عنابة",
        zone="Eastern Coast",
        zone_ar="الساحل الشرقي",
        lat=36.900,
        lon=7.767,
        elevation_m=18,
        annual_ghi_kwh_m2=1760.0,
        optimal_tilt_deg=31,
        avg_temp_summer_c=26.9,
        avg_temp_winter_c=12.1,
        soiling_risk="Low",
        base_soiling_rate_pct_day=0.10,
    ),
    "Setif": WilayaProfile(
        code="19",
        name="Sétif",
        name_ar="سطيف",
        zone="High Plateaus",
        zone_ar="الهضاب العليا الشرقية",
        lat=36.190,
        lon=5.410,
        elevation_m=1096,
        annual_ghi_kwh_m2=1945.0,
        optimal_tilt_deg=32,
        avg_temp_summer_c=27.5,
        avg_temp_winter_c=5.9,
        soiling_risk="Moderate",
        base_soiling_rate_pct_day=0.15,
    ),
    "Djelfa": WilayaProfile(
        code="17",
        name="Djelfa",
        name_ar="الجلفة",
        zone="Steppe / High Plateaus",
        zone_ar="السهوب والهضاب العليا",
        lat=34.670,
        lon=3.250,
        elevation_m=1144,
        annual_ghi_kwh_m2=2065.0,
        optimal_tilt_deg=30,
        avg_temp_summer_c=29.2,
        avg_temp_winter_c=6.2,
        soiling_risk="High",
        base_soiling_rate_pct_day=0.21,
    ),
    "Biskra": WilayaProfile(
        code="07",
        name="Biskra",
        name_ar="بسكرة",
        zone="Saharan Atlas Gateway",
        zone_ar="بوابة الأطلس الصحراوي",
        lat=34.850,
        lon=5.728,
        elevation_m=124,
        annual_ghi_kwh_m2=2155.0,
        optimal_tilt_deg=30,
        avg_temp_summer_c=35.8,
        avg_temp_winter_c=12.5,
        soiling_risk="High",
        base_soiling_rate_pct_day=0.25,
    ),
    "Bechar": WilayaProfile(
        code="08",
        name="Béchar",
        name_ar="بشار",
        zone="Western Sahara",
        zone_ar="الجنوب الغربي الصحراوي",
        lat=31.617,
        lon=-2.217,
        elevation_m=773,
        annual_ghi_kwh_m2=2270.0,
        optimal_tilt_deg=28,
        avg_temp_summer_c=35.1,
        avg_temp_winter_c=10.8,
        soiling_risk="High",
        base_soiling_rate_pct_day=0.27,
    ),
    "Ghardaia": WilayaProfile(
        code="47",
        name="Ghardaïa",
        name_ar="غرداية",
        zone="Northern Sahara (M'Zab)",
        zone_ar="شمال الصحراء (وادي مزاب)",
        lat=32.491,
        lon=3.674,
        elevation_m=469,
        annual_ghi_kwh_m2=2290.0,
        optimal_tilt_deg=29,
        avg_temp_summer_c=36.3,
        avg_temp_winter_c=11.7,
        soiling_risk="High",
        base_soiling_rate_pct_day=0.28,
    ),
    "Ouargla": WilayaProfile(
        code="30",
        name="Ouargla / Hassi Messaoud",
        name_ar="ورقلة / حاسي مسعود",
        zone="Eastern Sahara Energy Basin",
        zone_ar="الحوض الطاقوي الصحراوي الشرقي",
        lat=31.950,
        lon=5.325,
        elevation_m=141,
        annual_ghi_kwh_m2=2315.0,
        optimal_tilt_deg=28,
        avg_temp_summer_c=37.6,
        avg_temp_winter_c=12.2,
        soiling_risk="Extreme",
        base_soiling_rate_pct_day=0.33,
    ),
    "Adrar": WilayaProfile(
        code="01",
        name="Adrar",
        name_ar="أدرار",
        zone="Grand Sud Sahara",
        zone_ar="الجنوب الكبير الصحراوي",
        lat=27.874,
        lon=-0.293,
        elevation_m=263,
        annual_ghi_kwh_m2=2465.0,
        optimal_tilt_deg=25,
        avg_temp_summer_c=39.4,
        avg_temp_winter_c=13.6,
        soiling_risk="Extreme",
        base_soiling_rate_pct_day=0.36,
    ),
    "Tamanrasset": WilayaProfile(
        code="11",
        name="Tamanrasset",
        name_ar="تمنراست",
        zone="Hoggar Highlands",
        zone_ar="مرتفعات الهقار",
        lat=22.785,
        lon=5.523,
        elevation_m=1378,
        annual_ghi_kwh_m2=2515.0,
        optimal_tilt_deg=22,
        avg_temp_summer_c=30.6,
        avg_temp_winter_c=13.9,
        soiling_risk="High",
        base_soiling_rate_pct_day=0.26,
    ),
}


@dataclass(frozen=True)
class FacilityPreset:
    key: str
    label_en: str
    label_fr: str
    wilaya: str
    sector: str
    pv_capacity_kwp: float
    inverter_ac_kw: float
    battery_capacity_kwh: float
    battery_max_kw: float
    base_load_kw: float
    peak_load_kw: float
    load_profile_type: str  # industrial, commercial, hospital, microgrid, utility
    label_ar: str = ""


FACILITY_PRESETS: Dict[str, FacilityPreset] = {
    "oran_industrial": FacilityPreset(
        key="oran_industrial",
        label_en="Oran Industrial Plant (250 kWp + 300 kWh ESS)",
        label_fr="Usine Industrielle d'Oran (250 kWc + 300 kWh BESS)",
        label_ar="المصنع الصناعي بوهران (250 kWp + 300 kWh بطاريات)",
        wilaya="Oran",
        sector="Industrial Manufacturing",
        pv_capacity_kwp=250.0,
        inverter_ac_kw=225.0,
        battery_capacity_kwh=300.0,
        battery_max_kw=120.0,
        base_load_kw=68.0,
        peak_load_kw=235.0,
        load_profile_type="industrial",
    ),
    "ghardaia_microgrid": FacilityPreset(
        key="ghardaia_microgrid",
        label_en="Ghardaïa Hybrid Solar Microgrid (150 kWp + 400 kWh ESS)",
        label_fr="Micro-réseau Hybride Ghardaïa (150 kWc + 400 kWh BESS)",
        label_ar="الشبكة المصغرة الهجينة بغرداية (150 kWp + 400 kWh بطاريات)",
        wilaya="Ghardaia",
        sector="Remote Microgrid / Agro-Pumping",
        pv_capacity_kwp=150.0,
        inverter_ac_kw=135.0,
        battery_capacity_kwh=400.0,
        battery_max_kw=100.0,
        base_load_kw=28.0,
        peak_load_kw=115.0,
        load_profile_type="microgrid",
    ),
    "adrar_utility": FacilityPreset(
        key="adrar_utility",
        label_en="Adrar Saharan Solar Feeder (1,200 kWp + 800 kWh ESS)",
        label_fr="Centrale Solaire d'Adrar (1 200 kWc + 800 kWh BESS)",
        label_ar="محطة أدرار الشمسية الصحراوية (1,200 kWp + 800 kWh بطاريات)",
        wilaya="Adrar",
        sector="Utility / Oil & Gas Camp Feeder",
        pv_capacity_kwp=1200.0,
        inverter_ac_kw=1080.0,
        battery_capacity_kwh=800.0,
        battery_max_kw=350.0,
        base_load_kw=260.0,
        peak_load_kw=890.0,
        load_profile_type="utility",
    ),
    "algiers_campus": FacilityPreset(
        key="algiers_campus",
        label_en="Algiers Tech & Office Campus (85 kWp + 120 kWh ESS)",
        label_fr="Campus Tertiaire d'Alger (85 kWc + 120 kWh BESS)",
        label_ar="المجمع التكنولوجي والإداري بالجزائر (85 kWp + 120 kWh بطاريات)",
        wilaya="Algiers",
        sector="Commercial / Tertiary",
        pv_capacity_kwp=85.0,
        inverter_ac_kw=78.0,
        battery_capacity_kwh=120.0,
        battery_max_kw=50.0,
        base_load_kw=19.0,
        peak_load_kw=92.0,
        load_profile_type="commercial",
    ),
    "constantine_hospital": FacilityPreset(
        key="constantine_hospital",
        label_en="Constantine Healthcare Complex (320 kWp + 500 kWh ESS)",
        label_fr="Complexe Hospitalier Constantine (320 kWc + 500 kWh BESS)",
        label_ar="المركب الاستشفائي بقسنطينة (320 kWp + 500 kWh بطاريات)",
        wilaya="Constantine",
        sector="Critical Healthcare 24/7",
        pv_capacity_kwp=320.0,
        inverter_ac_kw=290.0,
        battery_capacity_kwh=500.0,
        battery_max_kw=180.0,
        base_load_kw=115.0,
        peak_load_kw=275.0,
        load_profile_type="hospital",
    ),
}


@dataclass(frozen=True)
class TariffScheme:
    key: str
    name_en: str
    name_fr: str
    currency: str
    symbol: str
    off_peak_rate: float      # 22:30 - 06:00 (approx 23:00-06:00)
    shoulder_rate: float      # 06:00 - 17:00 & 21:00 - 23:00
    peak_rate: float          # 17:00 - 21:00
    export_feed_in: float     # credit per kWh exported
    demand_charge_per_kw_month: float
    default_pv_capex_per_kwp: float
    default_ess_capex_per_kwh: float
    name_ar: str = ""


TARIFF_PROFILES: Dict[str, TariffScheme] = {
    "sonelgaz_mt_tou": TariffScheme(
        key="sonelgaz_mt_tou",
        name_en="Sonelgaz Medium-Voltage ToU (DZD)",
        name_fr="Sonelgaz Moyenne Tension HPH/HPL (DZD)",
        name_ar="سونلغاز التوتر المتوسط حسب الفترات (DZD)",
        currency="DZD",
        symbol="DA",
        off_peak_rate=2.45,
        shoulder_rate=4.68,
        peak_rate=8.92,
        export_feed_in=3.20,
        demand_charge_per_kw_month=215.0,
        default_pv_capex_per_kwp=118000.0,
        default_ess_capex_per_kwh=46000.0,
    ),
    "sonelgaz_bt_comm": TariffScheme(
        key="sonelgaz_bt_comm",
        name_en="Sonelgaz Low-Voltage Commercial/Pro (DZD)",
        name_fr="Sonelgaz Basse Tension Pro/Tertiaire (DZD)",
        name_ar="سونلغاز التوتر المنخفض تجاري / مهني (DZD)",
        currency="DZD",
        symbol="DA",
        off_peak_rate=4.18,
        shoulder_rate=5.48,
        peak_rate=6.95,
        export_feed_in=2.85,
        demand_charge_per_kw_month=95.0,
        default_pv_capex_per_kwp=125000.0,
        default_ess_capex_per_kwh=48000.0,
    ),
    "intl_usd_tou": TariffScheme(
        key="intl_usd_tou",
        name_en="International C&I Time-of-Use (USD)",
        name_fr="Tarif C&I International (USD)",
        name_ar="التعريفة الصناعية والتجارية الدولية (USD)",
        currency="USD",
        symbol="$",
        off_peak_rate=0.085,
        shoulder_rate=0.135,
        peak_rate=0.215,
        export_feed_in=0.065,
        demand_charge_per_kw_month=8.50,
        default_pv_capex_per_kwp=850.0,
        default_ess_capex_per_kwh=310.0,
    ),
    "med_eur_tou": TariffScheme(
        key="med_eur_tou",
        name_en="Euro-Med Industrial Benchmark (EUR)",
        name_fr="Référence Industrielle Euro-Med (EUR)",
        name_ar="المرجع الصناعي الأورومتوسطي (EUR)",
        currency="EUR",
        symbol="€",
        off_peak_rate=0.105,
        shoulder_rate=0.165,
        peak_rate=0.255,
        export_feed_in=0.075,
        demand_charge_per_kw_month=9.20,
        default_pv_capex_per_kwp=790.0,
        default_ess_capex_per_kwh=290.0,
    ),
}

# Algeria grid carbon intensity (kg CO2e per kWh) - natural gas combined/open cycle mix
GRID_CO2_KG_PER_KWH: float = 0.548

# Semantic color system for Executive Dark-Mode CleanTech UI
PALETTE = {
    "pv": "#F59E0B",          # Solar Amber / Gold (Primary Accent)
    "pv_light": "#FBBF24",    # Warm Solar Highlight
    "load": "#06B6D4",        # CleanTech Cyan (Load / Telemetry)
    "grid_import": "#F43F5E", # Coral / Rose Red (Grid Import)
    "grid_export": "#10B981", # Clean Energy Emerald (Export / Savings)
    "battery": "#10B981",     # ESS Storage Emerald
    "cyan": "#22D3EE",        # Luminous Cyan Accent (SoC / Atlas)
    "anomaly": "#EF4444",     # Fault Crimson
    "warning": "#FB923C",     # Thermal / Dust Amber-Orange
    "slate": "#F8FAFC",       # Primary Off-White Ink
    "muted": "#94A3B8",       # Secondary Muted Slate Label
    "gridline": "rgba(148, 163, 184, 0.14)",  # Crisp Dark-Mode Gridline
}


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "app_subtitle": "Energy Analytics, Solar PV Diagnostics & Microgrid Optimization",
        "nav_overview": "Executive Overview",
        "nav_pv": "PV Performance & Guard",
        "nav_load": "Load & Grid Analysis",
        "nav_forecast": "ML Forecast & ESS Sim",
        "nav_econ": "Financial ROI & Carbon",
        "nav_data": "Data Studio & Export",
        "sidebar_data_source": "Data Source & Facility",
        "mode_preset": "Simulated DZ Facility",
        "mode_upload": "Upload Custom CSV/XLSX",
        "date_window": "Analysis Window",
        "tariff_profile": "Tariff & Currency",
        "active_site": "Active Site",
    },
    "fr": {
        "app_subtitle": "Analytique Énergétique, Diagnostic Solaire PV & Optimisation Micro-réseau",
        "nav_overview": "Vue Exécutive & Carte",
        "nav_pv": "Performance PV & Guard",
        "nav_load": "Analyse Charge & Réseau",
        "nav_forecast": "Prévision IA & Sim BESS",
        "nav_econ": "Rentabilité ROI & Carbone",
        "nav_data": "Studio Données & Export",
        "sidebar_data_source": "Source de Données & Site",
        "mode_preset": "Site Algérien Simulé",
        "mode_upload": "Importer CSV / Excel",
        "date_window": "Période d'Analyse",
        "tariff_profile": "Tarification & Devise",
        "active_site": "Site Actif",
    },
    "ar": {
        "app_subtitle": "تحليلات الطاقة، تشخيص الأنظمة الكهروضوئية وتحسين الشبكات المصغرة",
        "nav_overview": "النظرة التنفيذية والأطلس",
        "nav_pv": "أداء الطاقة الشمسية والتشخيص",
        "nav_load": "تحليل الحمل الكهربائي والشبكة",
        "nav_forecast": "التنبؤ الذكي ومحاكاة البطاريات",
        "nav_econ": "العائد المالي والبصمة الكربونية",
        "nav_data": "استوديو البيانات والتصدير",
        "sidebar_data_source": "مصدر البيانات والمنشأة",
        "mode_preset": "منشأة جزائرية محاكاة",
        "mode_upload": "رفع ملف CSV / Excel",
        "date_window": "فترة التحليل الزمنية",
        "tariff_profile": "التعريفة والعملة",
        "active_site": "الموقع النشط",
    },
}


def tr(lang: str, key: str) -> str:
    """Translate UI string for active language ('en', 'fr', or 'ar')."""
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))


def bi(lang: str, en_text: str, fr_text: str, ar_text: Optional[str] = None) -> str:
    """Inline trilingual selector ('ar' -> Arabic, 'fr' -> French, otherwise English)."""
    if lang == "ar":
        return ar_text if ar_text is not None else en_text
    if lang == "fr":
        return fr_text
    return en_text


def wilaya_display_name(w: WilayaProfile, lang: str) -> str:
    """Return localized Wilaya display name."""
    if lang == "ar" and w.name_ar:
        return w.name_ar
    return w.name


def wilaya_zone_name(w: WilayaProfile, lang: str) -> str:
    """Return localized Wilaya climatic zone description."""
    if lang == "ar" and w.zone_ar:
        return w.zone_ar
    return w.zone


def preset_display_label(p: FacilityPreset, lang: str) -> str:
    """Return localized facility preset label."""
    if lang == "ar" and p.label_ar:
        return p.label_ar
    if lang == "fr":
        return p.label_fr
    return p.label_en


def tariff_display_name(t: TariffScheme, lang: str) -> str:
    """Return localized tariff scheme name."""
    if lang == "ar" and t.name_ar:
        return t.name_ar
    if lang == "fr":
        return t.name_fr
    return t.name_en
