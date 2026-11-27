"""Executive Dark-Mode SaaS & CleanTech theme, CSS architecture, and UI components."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING
import streamlit as st

from solarguard.config import WILAYAS_CATALOG

if TYPE_CHECKING:
    from solarguard.ui import AppContext


EXECUTIVE_DARK_CSS = """
<style>
/* ==========================================================================
   1. DESIGN TOKENS — CleanTech Executive Dark Palette
   ========================================================================== */
:root {
    --sg-bg-base: #0B1120;
    --sg-bg-surface: #111827;
    --sg-bg-elevated: #1E293B;
    --sg-border-subtle: rgba(148, 163, 184, 0.15);
    --sg-border-strong: rgba(148, 163, 184, 0.26);
    --sg-text-primary: #F8FAFC;
    --sg-text-secondary: #CBD5E1;
    --sg-text-muted: #94A3B8;
    --sg-amber: #F59E0B;
    --sg-amber-soft: rgba(245, 158, 11, 0.16);
    --sg-emerald: #10B981;
    --sg-emerald-soft: rgba(16, 185, 129, 0.15);
    --sg-cyan: #06B6D4;
    --sg-cyan-soft: rgba(6, 182, 212, 0.15);
    --sg-coral: #F43F5E;
}

/* ==========================================================================
   2. GLOBAL VIEWPORT, TYPOGRAPHY & CHROME CLEANUP
   ========================================================================== */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--sg-bg-base) !important;
    color: var(--sg-text-primary);
    font-feature-settings: "cv02", "cv03", "cv04", "cv11";
}

/* Hide Streamlit top rainbow decoration, deploy clutter & default footer
   while keeping the sidebar toggle accessible on laptop viewports */
[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
#MainMenu,
footer {
    display: none !important;
    visibility: hidden !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.25rem !important;
    min-height: 2.25rem !important;
}

.block-container {
    padding-top: 0.9rem !important;
    padding-bottom: 1.85rem !important;
    padding-left: 1.75rem !important;
    padding-right: 1.75rem !important;
    max-width: 1480px !important;
}

@media (max-width: 1280px) {
    .block-container {
        padding-left: 1.15rem !important;
        padding-right: 1.15rem !important;
    }
}

/* ==========================================================================
   3. EXECUTIVE HERO BANNER & STATUS PILLS
   ========================================================================== */
.sg-banner {
    background:
        radial-gradient(circle at 92% 18%, rgba(245, 158, 11, 0.13) 0%, transparent 46%),
        radial-gradient(circle at 72% 88%, rgba(6, 182, 212, 0.09) 0%, transparent 45%),
        linear-gradient(135deg, #0F172A 0%, #111827 65%, #162033 100%);
    color: var(--sg-text-primary);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-left: 4px solid var(--sg-amber);
    border-radius: 14px;
    padding: 16px 22px;
    margin-bottom: 14px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
    box-shadow: 0 10px 28px -8px rgba(2, 6, 23, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.sg-banner-title {
    font-size: 1.28rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--sg-text-primary);
    margin: 0;
    line-height: 1.25;
}

.sg-banner-sub {
    font-size: 0.84rem;
    color: var(--sg-text-muted);
    margin-top: 4px;
    line-height: 1.4;
}

.sg-pill-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
}

.sg-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(30, 41, 59, 0.72);
    border: 1px solid rgba(148, 163, 184, 0.22);
    color: #E2E8F0;
    border-radius: 999px;
    padding: 4px 11px;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    backdrop-filter: blur(8px);
    white-space: nowrap;
}

.sg-pill-amber {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.42);
    color: #FCD34D;
}

.sg-pill-cyan {
    background: rgba(6, 182, 212, 0.13);
    border: 1px solid rgba(6, 182, 212, 0.36);
    color: #67E8F9;
}

.sg-pill-emerald {
    background: rgba(16, 185, 129, 0.13);
    border: 1px solid rgba(16, 185, 129, 0.36);
    color: #6EE7B7;
}

.sg-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #F59E0B;
    box-shadow: 0 0 8px rgba(245, 158, 11, 0.85);
    display: inline-block;
}

/* ==========================================================================
   4. KPI METRIC CARDS (stMetric) — Glassmorphic Elevation & Zero Truncation
   ========================================================================== */
[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.68) 0%, rgba(17, 24, 39, 0.94) 100%);
    border: 1px solid var(--sg-border-subtle);
    border-radius: 12px;
    padding: 13px 15px !important;
    box-shadow: 0 4px 18px -4px rgba(2, 6, 23, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(10px);
    transition: border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
    height: 100%;
    overflow: visible !important;
}

[data-testid="stMetric"]:hover {
    border-color: rgba(245, 158, 11, 0.42);
    box-shadow: 0 8px 24px -6px rgba(2, 6, 23, 0.72), 0 0 0 1px rgba(245, 158, 11, 0.12);
    transform: translateY(-1px);
}

[data-testid="stMetricLabel"] {
    overflow: visible !important;
    white-space: normal !important;
}

[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] div {
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--sg-text-muted) !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    line-height: 1.28 !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] > div {
    font-size: clamp(1.06rem, 1.28vw, 1.42rem) !important;
    font-weight: 700 !important;
    color: var(--sg-text-primary) !important;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-break: keep-all;
    line-height: 1.22 !important;
    margin-top: 2px;
}

[data-testid="stMetricDelta"],
[data-testid="stMetricDelta"] > div {
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    line-height: 1.25 !important;
    margin-top: 3px;
}

/* ==========================================================================
   5. ELEVATED CHART CARDS, CONTAINERS & SECTION HEADERS
   ========================================================================== */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(17, 24, 39, 0.92) 0%, rgba(15, 23, 42, 0.95) 100%) !important;
    border: 1px solid var(--sg-border-subtle) !important;
    border-radius: 14px !important;
    box-shadow: 0 6px 22px -6px rgba(2, 6, 23, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
}

.sg-section-hdr {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.98rem;
    font-weight: 650;
    color: var(--sg-text-primary);
    margin: 0.15rem 0 0.25rem 0;
    letter-spacing: -0.01em;
    line-height: 1.3;
}

.sg-section-hdr::before {
    content: "";
    display: inline-block;
    width: 3px;
    height: 15px;
    border-radius: 3px;
    background: linear-gradient(180deg, #F59E0B 0%, #06B6D4 100%);
    flex-shrink: 0;
}

/* Captions & helper text */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    color: var(--sg-text-muted) !important;
    font-size: 0.8rem !important;
}

/* ==========================================================================
   6. SIDEBAR NAVIGATION, BRAND HEADER & CONTROL SURFACES
   ========================================================================== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1426 0%, #111827 100%) !important;
    border-right: 1px solid rgba(148, 163, 184, 0.14) !important;
}

section[data-testid="stSidebar"] hr {
    border-color: rgba(148, 163, 184, 0.14) !important;
    margin: 0.75rem 0 !important;
}

/* Sidebar Navigation Links */
[data-testid="stSidebarNav"] {
    padding-top: 0.65rem !important;
    padding-bottom: 0.35rem !important;
    border-bottom: 1px solid rgba(148, 163, 184, 0.13);
}

[data-testid="stSidebarNav"] ul {
    gap: 3px;
}

[data-testid="stSidebarNav"] a {
    border-radius: 10px !important;
    padding: 0.46rem 0.75rem !important;
    margin: 1px 6px !important;
    color: #CBD5E1 !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    border-left: 3px solid transparent;
}

[data-testid="stSidebarNav"] a:hover {
    background-color: rgba(30, 41, 59, 0.75) !important;
    color: #F8FAFC !important;
}

[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.18) 0%, rgba(245, 158, 11, 0.04) 100%) !important;
    border-left: 3px solid #F59E0B !important;
    color: #F8FAFC !important;
    font-weight: 650 !important;
}

[data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: #FDE68A !important;
    font-weight: 650 !important;
}

/* Brand Card inside Sidebar */
.sg-brand-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.92) 100%);
    border: 1px solid rgba(245, 158, 11, 0.28);
    border-radius: 12px;
    padding: 11px 13px;
    margin-bottom: 10px;
}

.sg-brand-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.sg-brand-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.01em;
}

.sg-brand-badge {
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #10B981;
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.34);
    padding: 2px 7px;
    border-radius: 999px;
}

.sg-brand-sub {
    font-size: 0.75rem;
    color: #94A3B8;
    margin-top: 4px;
    line-height: 1.35;
}

.sg-sb-section {
    font-size: 0.71rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #94A3B8;
    margin: 0.35rem 0 0.35rem 0;
}

.sg-sb-status {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 9px;
    padding: 8px 10px;
    margin-top: 8px;
    font-size: 0.75rem;
    color: #CBD5E1;
    line-height: 1.4;
}

/* ==========================================================================
   7. FORM CONTROLS: DROPDOWNS, RADIOS, TABS, INPUTS, EXPANDERS & BUTTONS
   ========================================================================== */
/* Labels */
[data-testid="stWidgetLabel"] p {
    color: #CBD5E1 !important;
    font-size: 0.81rem !important;
    font-weight: 500 !important;
}

/* Selectbox & Inputs */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {
    background-color: #0F172A !important;
    border-color: rgba(148, 163, 184, 0.24) !important;
    border-radius: 9px !important;
    color: #F8FAFC !important;
}

div[data-baseweb="select"] > div:hover,
div[data-baseweb="input"] > div:hover {
    border-color: rgba(245, 158, 11, 0.55) !important;
}

/* Horizontal Radio Groups */
[data-testid="stRadio"] div[role="radiogroup"] {
    gap: 8px;
}

[data-testid="stRadio"] label p {
    color: #E2E8F0 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}

/* Tabs */
div[data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(15, 23, 42, 0.65);
    padding: 5px 6px;
    border-radius: 11px;
    border: 1px solid var(--sg-border-subtle);
    margin-bottom: 0.65rem;
}

button[data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 7px 16px !important;
    color: #94A3B8 !important;
    font-weight: 600 !important;
    border: none !important;
    background: transparent !important;
}

button[data-baseweb="tab"]:hover {
    color: #F8FAFC !important;
    background: rgba(30, 41, 59, 0.55) !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.20) 0%, rgba(245, 158, 11, 0.08) 100%) !important;
    color: #FDE68A !important;
    box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.42);
}

div[data-baseweb="tab-highlight"] {
    display: none !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background-color: rgba(17, 24, 39, 0.85) !important;
    border: 1px solid var(--sg-border-subtle) !important;
    border-radius: 12px !important;
}

/* Buttons & Download Buttons */
[data-testid="stDownloadButton"] button,
[data-testid="stButton"] button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.83rem !important;
    transition: all 0.16s ease !important;
}

[data-testid="stDownloadButton"] button[kind="primary"],
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
    color: #0B1120 !important;
    border: 1px solid #FBBF24 !important;
    font-weight: 700 !important;
}

[data-testid="stDownloadButton"] button[kind="secondary"],
[data-testid="stButton"] button[kind="secondary"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
}

[data-testid="stDownloadButton"] button[kind="secondary"]:hover,
[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: #F59E0B !important;
    color: #FDE68A !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--sg-border-subtle);
}
</style>
"""


def inject_custom_css() -> None:
    """Inject executive SaaS & CleanTech dark-mode CSS styling."""
    st.markdown(EXECUTIVE_DARK_CSS, unsafe_allow_html=True)


def render_page_banner(ctx: "AppContext", page_title: str, subtitle: str) -> None:
    """Render top executive hero banner with semantic CleanTech status pills and HTML escaping."""
    w = WILAYAS_CATALOG.get(ctx.wilaya_key, WILAYAS_CATALOG["Oran"])
    safe_title = html.escape(str(page_title))
    safe_sub = html.escape(str(subtitle))
    safe_site = html.escape(str(ctx.site_label))
    safe_wname = html.escape(str(w.name))
    safe_curr = html.escape(str(ctx.tariff.currency))
    safe_sym = html.escape(str(ctx.tariff.symbol))
    st.markdown(
        f"""
        <div class="sg-banner">
            <div>
                <div class="sg-banner-title">{safe_title}</div>
                <div class="sg-banner-sub">{safe_sub}</div>
            </div>
            <div class="sg-pill-row">
                <span class="sg-pill sg-pill-amber"><span class="sg-dot"></span>{safe_site}</span>
                <span class="sg-pill sg-pill-cyan">☀️ {safe_wname} • {w.annual_ghi_kwh_m2:.0f} kWh/m²/yr</span>
                <span class="sg-pill sg-pill-emerald">⚡ {ctx.pv_capacity_kwp:,.0f} kWp PV • {ctx.battery_capacity_kwh:,.0f} kWh ESS</span>
                <span class="sg-pill">{safe_curr} ({safe_sym})</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str) -> None:
    """Render an HTML-escaped CleanTech section header with solar-cyan accent rule."""
    st.markdown(f'<div class="sg-section-hdr">{html.escape(str(title))}</div>', unsafe_allow_html=True)


def render_sidebar_brand(subtitle: str) -> None:
    """Render sleek CleanTech SaaS brand card at the top of the sidebar."""
    safe_sub = html.escape(str(subtitle))
    st.markdown(
        f"""
        <div class="sg-brand-card">
            <div class="sg-brand-row">
                <span class="sg-brand-title">☀️ SolarGuard-DZ</span>
                <span class="sg-brand-badge">LIVE EMS</span>
            </div>
            <div class="sg-brand-sub">{safe_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
