"""Multi-sheet formatted Excel (.xlsx), enriched CSV, template CSV, and HTML Audit Report exporters."""

from __future__ import annotations

import html
import io
from datetime import datetime, timezone
from typing import Any, Dict
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _style_worksheet(ws: Any) -> None:
    """Apply clean header styling, frozen top row, and auto-fitted column widths."""
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=10.5)
    ws.freeze_panes = "A2"

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="left", vertical="center")

    for col_idx, col_cells in enumerate(ws.columns, start=1):
        max_len = 0
        for cell in col_cells[:200]:
            val_str = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(val_str))
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 13), 48)


def build_excel_audit_workbook(
    site_label: str,
    kpis: Dict[str, Any],
    monthly_df: pd.DataFrame,
    incidents_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    annotated_df: pd.DataFrame,
    currency_symbol: str,
) -> bytes:
    """Create a styled multi-sheet Excel energy audit workbook in memory."""
    buf = io.BytesIO()
    kpi_rows = [
        ("Facility / Dataset", site_label, ""),
        ("Analyzed Duration", kpis["hours"], "hours"),
        ("Installed PV Capacity", round(kpis["pv_capacity_kwp"], 2), "kWp"),
        ("Battery ESS Capacity", round(kpis["battery_capacity_kwh"], 2), "kWh"),
        ("Total PV AC Yield", round(kpis["total_pv_kwh"], 1), "kWh"),
        ("Total Facility Consumption", round(kpis["total_load_kwh"], 1), "kWh"),
        ("Self-Sufficiency (Autarky)", round(kpis["self_sufficiency_pct"], 2), "%"),
        ("PV Self-Consumption", round(kpis["self_consumption_pct"], 2), "%"),
        ("IEC 61724 Performance Ratio", round(kpis["performance_ratio_pct"], 2), "%"),
        ("Annualized Specific Yield", round(kpis["annualized_specific_yield"], 1), "kWh/kWp/yr"),
        ("Peak Facility Demand", round(kpis["peak_load_kw"], 2), "kW"),
        ("Net Grid Peak Demand", round(kpis["net_grid_peak_kw"], 2), "kW"),
        ("Load Factor", round(kpis["load_factor_pct"], 2), "%"),
        ("Average Power Factor", round(kpis["avg_power_factor"], 3), "cos phi"),
        ("Window Baseline Bill", round(kpis["baseline_bill"], 1), currency_symbol),
        ("Window SolarGuard Net Bill", round(kpis["actual_net_bill"], 1), currency_symbol),
        ("Window Net Bill Savings", round(kpis["net_savings"], 1), currency_symbol),
        ("CO2 Emissions Avoided", round(kpis["co2_avoided_tons"], 2), "tCO2e"),
    ]
    kpi_table = pd.DataFrame(kpi_rows, columns=["Metric", "Value", "Unit"])

    daily_summary = (
        annotated_df.set_index("timestamp")
        .resample("1D")
        .agg(
            pv_kwh=("pv_ac_kw", "sum"),
            load_kwh=("load_kw", "sum"),
            grid_import_kwh=("grid_import_kw", "sum"),
            grid_export_kwh=("grid_export_kw", "sum"),
            poa_kwh_m2=("irradiance_wm2", lambda s: round(s.sum() / 1000.0, 2)),
            avg_cell_temp_c=("cell_temp_c", "mean"),
            flagged_anomaly_hours=("is_anomaly", "sum"),
        )
        .round(2)
        .reset_index()
    )

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        kpi_table.to_excel(writer, sheet_name="Executive_KPIs", index=False)
        monthly_df.drop(columns=["timestamp"], errors="ignore").round(2).to_excel(
            writer, sheet_name="Monthly_Billing", index=False
        )
        if not incidents_df.empty:
            inc_export = incidents_df.copy()
            for dt_col in ("Start", "End"):
                if dt_col in inc_export.columns:
                    inc_export[dt_col] = inc_export[dt_col].astype(str)
            inc_export.to_excel(writer, sheet_name="SolarGuard_Faults", index=False)
        else:
            pd.DataFrame({"Status": ["No critical anomalies detected in window."]}).to_excel(
                writer, sheet_name="SolarGuard_Faults", index=False
            )
        cashflow_df.to_excel(writer, sheet_name="CashFlow_25Yr", index=False)
        daily_summary.to_excel(writer, sheet_name="Daily_Summary", index=False)

        for ws in writer.book.worksheets:
            _style_worksheet(ws)

    return buf.getvalue()


def build_sample_csv_template() -> bytes:
    """Generate a clean 48-hour CSV template for custom user uploads."""
    ts = pd.date_range("2026-06-01 00:00:00", periods=48, freq="1h")
    hr = ts.hour.to_numpy()
    irr = (850.0 * pd.Series(hr).map(lambda h: max(0.0, float(__import__("math").sin(3.14159 * (h - 6) / 12))) if 6 <= h <= 18 else 0.0)).round(1)
    pv = (irr * 0.18).round(2)
    ld = (55.0 + 65.0 * pd.Series(hr).map(lambda h: 1.0 if 8 <= h <= 19 else 0.25)).round(2)
    tamb = (24.0 + 5.5 * pd.Series(hr).map(lambda h: float(__import__("math").sin(3.14159 * (h - 8) / 12)))).round(1)
    tpl = pd.DataFrame(
        {
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "load_kw": ld,
            "pv_ac_kw": pv,
            "irradiance_wm2": irr,
            "ambient_temp_c": tamb,
        }
    )
    return tpl.to_csv(index=False).encode("utf-8")


def build_html_audit_report(
    site_label: str,
    wilaya_name: str,
    kpis: Dict[str, Any],
    econ: Dict[str, Any],
    anom_summary: Dict[str, Any],
    incidents_df: pd.DataFrame,
    currency_symbol: str,
) -> str:
    """Generate a clean, printable standalone HTML Executive Energy Audit Report."""
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    safe_site = html.escape(str(site_label))
    safe_wilaya = html.escape(str(wilaya_name))
    safe_sym = html.escape(str(currency_symbol))

    inc_rows_html = ""
    if not incidents_df.empty:
        for _, r in incidents_df.head(10).iterrows():
            inc_rows_html += (
                f"<tr>"
                f"<td>{html.escape(str(r['Start']))}</td>"
                f"<td>{html.escape(str(r['Category']))}</td>"
                f"<td><strong>{html.escape(str(r['Severity']))}</strong></td>"
                f"<td>{int(r['Flagged Hours'])} h</td>"
                f"<td>{float(r['Impact (kWh)']):,.1f} kWh</td>"
                f"<td>{html.escape(str(r['Recommended Action']))}</td>"
                f"</tr>"
            )
    else:
        inc_rows_html = (
            "<tr><td colspan='6'>No anomalous operational incidents flagged in analyzed period.</td></tr>"
        )

    irr_str = f"{econ['irr_pct']:.1f}%" if econ["irr_pct"] is not None else "N/A"
    pb_str = (
        f"{econ['simple_payback_yr']:.1f} yrs"
        if econ["simple_payback_yr"] is not None
        else "&gt;25 yrs"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SolarGuard-DZ Energy Audit Report — {safe_site}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #0F172A; background: #FFFFFF; max-width: 980px; margin: 32px auto; padding: 0 24px; line-height: 1.5; }}
  .header {{ border-bottom: 3px solid #D97706; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-end; }}
  h1 {{ margin: 0; font-size: 24px; color: #0F172A; }}
  .meta {{ color: #475569; font-size: 13px; }}
  h2 {{ font-size: 16px; text-transform: uppercase; letter-spacing: 0.05em; color: #334155; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; margin-top: 28px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px; }}
  .card {{ border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; background: #F8FAFC; }}
  .card .lbl {{ font-size: 11.5px; color: #64748B; text-transform: uppercase; }}
  .card .val {{ font-size: 20px; font-weight: 700; color: #0F172A; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
  th, td {{ border: 1px solid #E2E8F0; padding: 8px 10px; text-align: left; }}
  th {{ background: #F1F5F9; color: #334155; font-weight: 600; }}
  .footer {{ margin-top: 36px; font-size: 12px; color: #64748B; border-top: 1px solid #E2E8F0; padding-top: 12px; }}
  @media print {{ body {{ margin: 0; padding: 12px; }} }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <h1>SolarGuard-DZ — Executive Energy &amp; PV Audit Report</h1>
      <div class="meta">Facility: <strong>{safe_site}</strong> | Climatic Zone: <strong>{safe_wilaya}</strong></div>
    </div>
    <div class="meta">Generated: {gen_date}<br>Horizon: {kpis['hours']:,} hours</div>
  </div>

  <h2>1. Energy Balance &amp; IEC 61724 PV Performance</h2>
  <div class="grid">
    <div class="card"><div class="lbl">Solar PV Yield</div><div class="val">{kpis['total_pv_kwh']:,.0f} kWh</div></div>
    <div class="card"><div class="lbl">Facility Demand</div><div class="val">{kpis['total_load_kwh']:,.0f} kWh</div></div>
    <div class="card"><div class="lbl">Self-Sufficiency</div><div class="val">{kpis['self_sufficiency_pct']:.1f}%</div></div>
    <div class="card"><div class="lbl">Performance Ratio</div><div class="val">{kpis['performance_ratio_pct']:.1f}%</div></div>
    <div class="card"><div class="lbl">Specific Yield (Ann.)</div><div class="val">{kpis['annualized_specific_yield']:,.0f} kWh/kWp</div></div>
    <div class="card"><div class="lbl">Peak Demand / Grid</div><div class="val">{kpis['peak_load_kw']:.1f} / {kpis['net_grid_peak_kw']:.1f} kW</div></div>
    <div class="card"><div class="lbl">Load Factor / PF</div><div class="val">{kpis['load_factor_pct']:.1f}% / {kpis['avg_power_factor']:.2f}</div></div>
    <div class="card"><div class="lbl">CO2 Avoided</div><div class="val">{kpis['co2_avoided_tons']:.1f} tCO2e</div></div>
  </div>

  <h2>2. 25-Year Financial &amp; Tariff Assessment ({safe_sym})</h2>
  <div class="grid">
    <div class="card"><div class="lbl">Net CAPEX</div><div class="val">{econ['net_capex']:,.0f} {safe_sym}</div></div>
    <div class="card"><div class="lbl">Net Present Value</div><div class="val">{econ['npv']:,.0f} {safe_sym}</div></div>
    <div class="card"><div class="lbl">Internal Rate of Return</div><div class="val">{irr_str}</div></div>
    <div class="card"><div class="lbl">Simple Payback / PV LCOE</div><div class="val">{pb_str} | {econ['lcoe']:.2f} {safe_sym}/kWh</div></div>
  </div>

  <h2>3. SolarGuard AI Fault &amp; Anomaly Log ({anom_summary['incident_count']} Incidents | {anom_summary['recoverable_pv_kwh']:,.0f} kWh Recoverable PV)</h2>
  <table>
    <thead>
      <tr><th>Start Time</th><th>Category</th><th>Severity</th><th>Hours</th><th>Energy Impact</th><th>Engineering Action</th></tr>
    </thead>
    <tbody>
      {inc_rows_html}
    </tbody>
  </table>

  <div class="footer">
    SolarGuard-DZ Energy Intelligence Platform • IEC 61724 Compliant Analytics • Print this page (Ctrl+P) to save as PDF.
  </div>
</body>
</html>
"""
