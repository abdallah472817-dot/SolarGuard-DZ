"""End-to-end headless Streamlit AppTest across entrypoint, all 6 views, EN/FR, and Load-Only mode."""

from __future__ import annotations

from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT_APP = Path(__file__).resolve().parent.parent / "app.py"


def test_app_entrypoint_language_and_sidebar_controls():
    at = AppTest.from_file(ROOT_APP, default_timeout=45)
    at.run()
    assert len(at.exception) == 0, f"Entrypoint exception: {at.exception}"
    assert len(at.metric) >= 6

    # Switch language to French and Arabic and verify clean reruns
    at.radio(key="sg_lang").set_value("fr").run()
    assert len(at.exception) == 0

    at.radio(key="sg_lang").set_value("ar").run()
    assert len(at.exception) == 0
    assert any("إنتاج الطاقة الشمسية" in m.label for m in at.metric)

    # Switch facility preset & tariff currency
    at.selectbox(key="sg_preset_key").select("ghardaia_microgrid").run()
    assert len(at.exception) == 0

    at.selectbox(key="sg_tariff_key").select("intl_usd_tou").run()
    assert len(at.exception) == 0

    # Switch date window preset
    at.selectbox(key="sg_window_preset").select("Q3 Peak Summer (Jul–Sep)").run()
    assert len(at.exception) == 0


def _run_view_script():
    import streamlit as st
    from solarguard.ui import build_sidebar_and_context
    from solarguard.views.data_studio import render_data_studio_page
    from solarguard.views.economics_view import render_economics_page
    from solarguard.views.forecast_sim import render_forecast_sim_page
    from solarguard.views.load_grid import render_load_grid_page
    from solarguard.views.overview import render_overview_page
    from solarguard.views.pv_guard import render_pv_guard_page

    ctx = build_sidebar_and_context()
    if st.session_state.get("_force_load_only"):
        ctx.pv_capacity_kwp = 0.0
        ctx.df = ctx.df.copy()
        ctx.df["pv_ac_kw"] = 0.0
        ctx.kpis["total_pv_kwh"] = 0.0

    view_name = st.session_state.get("_test_view", "overview")
    dispatch = {
        "overview": render_overview_page,
        "pv_guard": render_pv_guard_page,
        "load_grid": render_load_grid_page,
        "forecast_sim": render_forecast_sim_page,
        "economics": render_economics_page,
        "data_studio": render_data_studio_page,
    }
    dispatch[view_name](ctx)


def test_every_single_page_view_renders_cleanly_en_fr_and_ar():
    for lang in ("en", "fr", "ar"):
        for view_key in ("overview", "pv_guard", "load_grid", "forecast_sim", "economics", "data_studio"):
            at = AppTest.from_function(_run_view_script, default_timeout=45)
            at.session_state["sg_lang"] = lang
            at.session_state["_test_view"] = view_key
            at.run()
            assert len(at.exception) == 0, f"View '{view_key}' ({lang}) raised: {at.exception}"


def test_forecast_auto_sizing_and_load_only_views():
    # Test auto-sizing strategy selector on forecast_sim view
    at = AppTest.from_function(_run_view_script, default_timeout=45)
    at.session_state["_test_view"] = "forecast_sim"
    at.run()
    assert len(at.exception) == 0
    at.selectbox(key="sim_strategy_mode").select("balanced").run()
    assert len(at.exception) == 0
    at.selectbox(key="sim_strategy_mode").select("peak_shaving").run()
    assert len(at.exception) == 0

    # Test Load-Only (0 kWp PV) rendering on pv_guard and forecast_sim
    for vkey in ("pv_guard", "forecast_sim"):
        at_lo = AppTest.from_function(_run_view_script, default_timeout=45)
        at_lo.session_state["_test_view"] = vkey
        at_lo.session_state["_force_load_only"] = True
        at_lo.run()
        assert len(at_lo.exception) == 0
