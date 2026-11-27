"""Financial ROI, Tariff Billing Audit, LCOE, NPV, IRR, and 25-Year Lifecycle Cash Flow."""

from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

from solarguard.analytics import compute_monthly_billing_table
from solarguard.config import GRID_CO2_KG_PER_KWH, TariffScheme


def _solve_irr_pct(cash_flows: np.ndarray) -> Optional[float]:
    """Compute Internal Rate of Return (%) via robust bisection + Newton polish on [-0.45, 3.00]."""
    if len(cash_flows) < 2 or cash_flows[0] >= 0 or np.sum(cash_flows) <= 0:
        return None

    t = np.arange(len(cash_flows), dtype=np.float64)

    def npv_at(rate: float) -> float:
        return float(np.sum(cash_flows / ((1.0 + rate) ** t)))

    low, high = -0.45, 3.00
    f_low, f_high = npv_at(low), npv_at(high)
    if f_low * f_high > 0:
        return None

    for _ in range(80):
        mid = 0.5 * (low + high)
        f_mid = npv_at(mid)
        if abs(f_mid) < 1e-6:
            return round(mid * 100.0, 2)
        if f_low * f_mid <= 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return round(0.5 * (low + high) * 100.0, 2)


def _interpolated_payback(cum_cf: np.ndarray) -> Optional[float]:
    """Find fractional year where cumulative cash flow crosses zero."""
    pos_idx = np.where(cum_cf >= 0.0)[0]
    if len(pos_idx) == 0:
        return None
    k = int(pos_idx[0])
    if k == 0:
        return 0.0
    prev_val = cum_cf[k - 1]
    curr_val = cum_cf[k]
    denom = curr_val - prev_val
    frac = abs(prev_val) / denom if denom > 0 else 0.0
    return round((k - 1) + frac, 2)


def compute_lifecycle_economics(
    df: pd.DataFrame,
    tariff: TariffScheme,
    pv_capacity_kwp: float,
    battery_capacity_kwh: float,
    pv_capex_per_kwp: float,
    ess_capex_per_kwh: float,
    subsidy_pct: float = 0.0,
    om_pct_yr: float = 1.25,
    discount_rate_pct: float = 7.5,
    tariff_escalation_pct: float = 4.0,
    degradation_pct_yr: float = 0.50,
    carbon_price_per_ton: float = 0.0,
    project_years: int = 25,
) -> Dict[str, Any]:
    """Evaluate 25-year CAPEX/OPEX cash flows, PV & Hybrid LCOE, NPV, IRR, Payback, and Carbon."""
    n_hours = max(len(df), 1)
    annual_scale = 8760.0 / n_hours

    monthly_df = compute_monthly_billing_table(df, tariff)
    window_savings = float(monthly_df["net_savings"].sum())
    yr1_bill_savings = window_savings * annual_scale

    yr1_pv_kwh = float(df["pv_ac_kw"].sum()) * annual_scale
    yr1_clean_kwh = (
        float((df["direct_pv_kw"] + df["battery_to_load_kw"] + df["grid_export_kw"]).sum())
        * annual_scale
    )
    yr1_co2_tons = (yr1_clean_kwh * GRID_CO2_KG_PER_KWH) / 1000.0

    sub_factor = 1.0 - float(np.clip(subsidy_pct, 0.0, 80.0)) / 100.0
    pv_gross_capex = pv_capacity_kwp * pv_capex_per_kwp
    ess_gross_capex = battery_capacity_kwh * ess_capex_per_kwh
    gross_capex = pv_gross_capex + ess_gross_capex
    net_capex = gross_capex * sub_factor

    base_om_total = gross_capex * (om_pct_yr / 100.0)
    base_om_pv_only = pv_gross_capex * (om_pct_yr / 100.0)

    r_disc = discount_rate_pct / 100.0
    r_esc = tariff_escalation_pct / 100.0
    r_deg = degradation_pct_yr / 100.0

    years = np.arange(0, project_years + 1)
    annual_cf = np.zeros(project_years + 1, dtype=np.float64)
    disc_cf = np.zeros(project_years + 1, dtype=np.float64)
    pv_gen_yr = np.zeros(project_years + 1, dtype=np.float64)
    lifecycle_costs_total = np.zeros(project_years + 1, dtype=np.float64)
    lifecycle_costs_pv = np.zeros(project_years + 1, dtype=np.float64)
    co2_tons_yr = np.zeros(project_years + 1, dtype=np.float64)

    annual_cf[0] = -net_capex
    disc_cf[0] = -net_capex
    lifecycle_costs_total[0] = net_capex
    lifecycle_costs_pv[0] = pv_gross_capex * sub_factor

    for y in range(1, project_years + 1):
        deg_mult = max(0.5, 1.0 - r_deg * (y - 1))
        esc_mult = (1.0 + r_esc) ** (y - 1)
        om_cost = base_om_total * (1.025 ** (y - 1))
        om_pv_cost = base_om_pv_only * (1.025 ** (y - 1))

        inv_rep = 0.10 * pv_gross_capex if y == 12 else 0.0
        ess_rep = 0.28 * ess_gross_capex if y == 12 else 0.0
        replacement_cost = inv_rep + ess_rep

        pv_gen_yr[y] = yr1_pv_kwh * deg_mult
        co2_tons_yr[y] = yr1_co2_tons * deg_mult
        gross_sav = yr1_bill_savings * deg_mult * esc_mult + co2_tons_yr[y] * carbon_price_per_ton
        net_yr = gross_sav - om_cost - replacement_cost

        disc_div = (1.0 + r_disc) ** y
        annual_cf[y] = net_yr
        disc_cf[y] = net_yr / disc_div
        lifecycle_costs_total[y] = (om_cost + replacement_cost) / disc_div
        lifecycle_costs_pv[y] = (om_pv_cost + inv_rep) / disc_div

    cum_cf = np.cumsum(annual_cf)
    cum_disc_cf = np.cumsum(disc_cf)

    npv = float(np.sum(disc_cf))
    irr_pct = _solve_irr_pct(annual_cf)
    simple_payback = _interpolated_payback(cum_cf)
    discounted_payback = _interpolated_payback(cum_disc_cf)

    disc_factors = np.array([1.0 / ((1.0 + r_disc) ** y) for y in years])
    pv_discounted_kwh = float(np.sum(pv_gen_yr * disc_factors))
    pv_lcoe = float(np.sum(lifecycle_costs_pv)) / pv_discounted_kwh if pv_discounted_kwh > 0 else 0.0
    hybrid_lcoe = float(np.sum(lifecycle_costs_total)) / pv_discounted_kwh if pv_discounted_kwh > 0 else 0.0

    cashflow_df = pd.DataFrame(
        {
            "Year": years,
            "Annual Cash Flow": np.round(annual_cf, 1),
            "Discounted Cash Flow": np.round(disc_cf, 1),
            "Cumulative Cash Flow": np.round(cum_cf, 1),
            "Cumulative Discounted CF": np.round(cum_disc_cf, 1),
            "PV Yield (kWh)": np.round(pv_gen_yr, 0),
            "CO2 Avoided (t)": np.round(co2_tons_yr, 2),
        }
    )

    return {
        "net_capex": net_capex,
        "gross_capex": gross_capex,
        "yr1_savings": yr1_bill_savings,
        "npv": npv,
        "irr_pct": irr_pct,
        "simple_payback_yr": simple_payback,
        "discounted_payback_yr": discounted_payback,
        "lcoe": pv_lcoe,
        "hybrid_lcoe": hybrid_lcoe,
        "net_profit_25yr": float(cum_cf[-1]),
        "total_co2_tons_25yr": float(co2_tons_yr.sum()),
        "cashflow_df": cashflow_df,
        "monthly_df": monthly_df,
    }
