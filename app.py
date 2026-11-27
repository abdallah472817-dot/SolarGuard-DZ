"""SolarGuard-DZ: Full-Stack Energy Analytics, Solar PV Diagnostics & Microgrid Optimization."""

from __future__ import annotations

import streamlit as st

from solarguard.config import tr
from solarguard.ui import build_sidebar_and_context, inject_custom_css
from solarguard.views.data_studio import render_data_studio_page
from solarguard.views.economics_view import render_economics_page
from solarguard.views.forecast_sim import render_forecast_sim_page
from solarguard.views.load_grid import render_load_grid_page
from solarguard.views.overview import render_overview_page
from solarguard.views.pv_guard import render_pv_guard_page

st.set_page_config(
    page_title="SolarGuard-DZ | Energy & Solar Intelligence",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

lang_curr = st.session_state.get("sg_lang") or "en"
inject_custom_css(lang=lang_curr)


def page_overview() -> None:
    render_overview_page(st.session_state["_sg_active_ctx"])


def page_pv_guard() -> None:
    render_pv_guard_page(st.session_state["_sg_active_ctx"])


def page_load_grid() -> None:
    render_load_grid_page(st.session_state["_sg_active_ctx"])


def page_forecast_sim() -> None:
    render_forecast_sim_page(st.session_state["_sg_active_ctx"])


def page_economics() -> None:
    render_economics_page(st.session_state["_sg_active_ctx"])


def page_data_studio() -> None:
    render_data_studio_page(st.session_state["_sg_active_ctx"])


nav = st.navigation(
    [
        st.Page(
            page_overview,
            title=tr(lang_curr, "nav_overview"),
            icon=":material/dashboard:",
            url_path="overview",
            default=True,
        ),
        st.Page(
            page_pv_guard,
            title=tr(lang_curr, "nav_pv"),
            icon=":material/wb_sunny:",
            url_path="pv-guard",
        ),
        st.Page(
            page_load_grid,
            title=tr(lang_curr, "nav_load"),
            icon=":material/bolt:",
            url_path="load-grid",
        ),
        st.Page(
            page_forecast_sim,
            title=tr(lang_curr, "nav_forecast"),
            icon=":material/trending_up:",
            url_path="forecast-sim",
        ),
        st.Page(
            page_economics,
            title=tr(lang_curr, "nav_econ"),
            icon=":material/payments:",
            url_path="economics",
        ),
        st.Page(
            page_data_studio,
            title=tr(lang_curr, "nav_data"),
            icon=":material/table_view:",
            url_path="data-studio",
        ),
    ],
    position="sidebar",
)

st.session_state["_sg_active_ctx"] = build_sidebar_and_context()
nav.run()
