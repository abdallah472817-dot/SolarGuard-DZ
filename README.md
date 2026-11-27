# SolarGuard-DZ — Full-Stack Energy & Solar PV Analytics Platform

**SolarGuard-DZ** is a complete Streamlit energy engineering, solar photovoltaic (PV) diagnostics, electrical load auditing, machine-learning forecasting, battery ESS sizing, and financial ROI platform calibrated for Algerian climatic zones (12 Wilayas from Oran & Algiers to Ghardaïa, Adrar & Tamanrasset) as well as any custom uploaded SCADA / smart-meter dataset.

---

## Core Modules & Capabilities

1. **Executive Overview & Algeria Solar Atlas (`Overview`)**
   - Executive KPI strip with live sparklines: PV AC Yield, Facility Demand, Self-Sufficiency (Autarky %), IEC 61724 Performance Ratio (PR %), Net Bill Savings, and Avoided $\text{CO}_2$ (`0.548 kg CO2/kWh` gas-turbine grid factor).
   - Multi-resolution (`Hourly`, `Daily`, `Weekly`, `Monthly`) Energy Balance & Battery State-of-Charge (SoC) interactive timeline.
   - Conservation-accurate **Source-to-Sink Sankey Energy Flow** diagram.
   - Vector **Algeria Solar Irradiation Atlas** across 12 Wilayas with GHI ($\text{kWh/m}^2/\text{yr}$), optimal tilt angle, ambient thermal profile, and dust/soiling risk.

2. **Solar PV Physics & SolarGuard AI Diagnostics (`PV Performance & Guard`)**
   - **PV Conversion & Loss Waterfall**: Reconciles Theoretical STC Yield $\rightarrow$ Module Thermal Derating ($-0.40\%/^\circ\text{C}$) $\rightarrow$ Saharan Sand/Dust Soiling $\rightarrow$ Wiring & Inverter Efficiency $\rightarrow$ Clipping & Faults $\rightarrow$ Net AC Yield.
   - **Irradiance vs. AC Power Curve** colored by module cell temperature ($^\circ\text{C}$) with healthy physics envelope.
   - **SolarGuard Hybrid AI Anomaly Engine**: Combines `IsolationForest` multivariate detection with physical PV & load residual models to classify root-cause incidents (*PV String Dropout*, *Sand/Dust Soiling Surge*, *Inverter Thermal Derating*, *Off-Hours Baseload Surge*, *Peak Demand / Reactive Spike*) and quantify recoverable kWh & financial impact.

3. **Load Profile & Grid Demand Analysis (`Load & Grid Analysis`)**
   - Peak Demand ($\text{kW}$ & apparent $\text{kVA}$), Net Grid Peak shaving, Baseload P10, Load Factor (%), and Power Factor ($\cos \phi$).
   - **24-Hour $\times$ Monthly Consumption Heatmap** & **Load Duration Curve (LDC)** comparing gross facility load against net grid import.
   - **Algerian Workweek (`Sun–Thu`) vs. Weekend (`Fri–Sat`)** diurnal P10–P90 demand profiles.
   - **Time-of-Use (ToU)** tariff window breakdown (`Off-Peak`, `Shoulder`, `Evening Peak`) and **FFT Spectral Periodicity** analysis (`12h`, `24h`, `168h` harmonics).

4. **ML Forecasting & Battery ESS Sizing Lab (`ML Forecast & ESS Sim`)**
   - **Strictly Causal Probabilistic Forecaster**: Trains `HistGradientBoostingRegressor` quantile models (`P10`, `P50`, `P90`) with strictly pre-origin rolling/climatological features and astronomical clear-sky geometry (zero future holdout leakage) for 24h–168h ahead **Solar PV**, **Electrical Demand**, and **Joint Net Grid Import** forecasting (`R²`, `MAE`, `RMSE`, permutation importance).
   - **Prescriptive PV + Battery ESS Sizing & Dispatch Simulator**: Includes automatic engineering presets (*Balanced Self-Sufficiency*, *Peak Demand Shaving*, *Max Autarky / Near-Zero Export*) alongside manual controls for PV capacity ($\text{kWp}$), Battery storage ($\text{kWh}$), PCS power ($\text{kW}$), round-trip efficiency, and minimum SoC reserve.

5. **Financial ROI, Tariff Audit & 25-Year Cash Flow (`Financial ROI & Carbon`)**
   - Supports **Sonelgaz Medium-Voltage & Low-Voltage Time-of-Use tariffs (`DZD`)**, **USD (`$`)**, and **EUR (`€`)** with exact calendar-month proration reconciled across Executive KPIs and monthly bills.
   - Computes **Net CAPEX**, **25-Year NPV**, **IRR (%)**, **Simple & Discounted Payback**, **Pure Solar PV LCOE** vs. **Hybrid PV+ESS LCOE**, Year-12 inverter/ESS refurbishment, and monthly billing comparison.

6. **Data Studio & 1-Click Audit Exports (`Data Studio & Export`)**
   - Upload any custom **CSV** (`,` or `;` delimited, `.` or `,` decimals, sub-hourly, hourly, or **daily** logs with diurnal disaggregation, including **Load-Only `0 kWp`** facility meters) or **Excel (`.xlsx`)** dataset with automatic column mapping & unit scaling (`W`, `kW`, `MW`).
   - Descriptive percentile statistics, Pearson correlation heatmap, SCADA row inspector, and 1-click exports:
     - **Styled Multi-sheet Excel Audit Workbook (`.xlsx`)**
     - **Anomaly-Annotated Hourly CSV (`.csv`)**
     - **XSS-Safe Printable Executive HTML Report (`.html`)**
     - **Ready-to-Fill Sample CSV Upload Template (`.csv`)**

---

## Project Structure

```text
SolarGuard-DZ/
├── .streamlit/config.toml         # Server, CORS/iframe & executive CleanTech dark theme
├── app.py                         # Streamlit multi-page navigation entrypoint
├── requirements.txt               # Reproducible Python dependencies
├── pyproject.toml                 # Package metadata & pytest configuration
├── data/
│   └── sample_solarguard_oran_2026.csv
├── solarguard/
│   ├── config.py                  # 12-Wilaya solar atlas, facility presets, tariffs & EN/FR i18n
│   ├── data_generator.py          # Physics-based 8,760h solar, load, ESS & fault generator
│   ├── data_loader.py             # Smart CSV/Excel ingestion, auto-mapper & unit normalizer
│   ├── analytics.py               # IEC 61724 KPIs, waterfall, LDC, ToU, FFT & ESS sizing
│   ├── anomaly.py                 # Hybrid physics + IsolationForest fault classifier
│   ├── forecasting.py             # Quantile HistGradientBoosting forecaster (P10/P50/P90)
│   ├── economics.py               # 25-yr CAPEX/OPEX cash flow, NPV, IRR, LCOE & monthly bills
│   ├── charts.py                  # Unified dark-mode CleanTech Plotly chart suite
│   ├── exporter.py                # Excel (.xlsx), CSV & Executive HTML report builders
│   ├── ui/                        # Modular UI context (__init__.py) & executive CSS (theme.py)
│   └── views/                     # Modular Streamlit page views (6 analytical modules)
└── tests/                         # Unit tests + Streamlit AppTest headless UI suite
```

---

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## Running Tests

```bash
.venv/bin/pytest -v
```
