# Discounted Cash Flow Dashboard — Indus Towers Ltd

A dark-themed, institutional-style discounted cash flow (DCF) valuation dashboard for
**Indus Towers Limited** (NSE: INDUSTOWER). The DCF math runs entirely in Python; the
interface is built with Streamlit. The base case reproduces the underlying Excel model
**exactly — ₹812.09 per share**.

![status](https://img.shields.io/badge/base--case-%E2%82%B9812.09-brightgreen)

## Features

- **Five live sidebar variables** — Revenue Growth, EBIT Margin, WACC, Terminal Growth
  Rate, and Tax Rate. Move any one and every output recalculates instantly.
- **Parallel-shift logic** — changing the Year-1 revenue growth shifts the whole forecast
  curve by the same amount (e.g. base `6,7,8,8,7` → set Year 1 to 4 → `4,5,6,6,5`). EBIT
  margin behaves the same way.
- **Reset button** — restores every input to the Excel base-case values.
- **Four sections** — DCF Model (waterfall + forecast table), Charts & Graphs (dynamic),
  Sensitivity Analysis (WACC×TGR and Margin×Growth heatmaps), and Scenarios (Bull/Base/Bear).
- **Dynamic charts** — revenue over years, EBIT as % of revenue, CapEx vs depreciation,
  free cash flows, and UFCF vs present value. All update with the sliders.

## DCF Methodology

```
Revenue_t   = Revenue_(t-1) × (1 + growth_t)
EBIT_t      = Revenue_t × EBIT_margin_t
EBIAT_t     = EBIT_t × (1 − tax_t)
UFCF_t      = EBIAT_t + D&A_t − CapEx_t − ΔNWC_t
PV(UFCF_t)  = UFCF_t / (1 + WACC)^(t − 0.5)        # mid-year convention
Terminal V  = UFCF_5 × (1 + g) / (WACC − g)        # Gordon growth
EV          = Σ PV(UFCF) + PV(Terminal Value)
Equity      = EV + Cash − Debt
Price/Share = Equity Value / Shares Outstanding
```

## Base-Case Assumptions (from Excel)

| Driver | FY26E | FY27E | FY28E | FY29E | FY30E |
|--------|-------|-------|-------|-------|-------|
| Revenue growth % | 6 | 7 | 8 | 8 | 7 |
| EBIT margin % | 44 | 44 | 49 | 49 | 51 |
| CapEx % revenue | 18 | 16 | 15 | 14 | 13 |
| D&A % revenue | 21 | 21 | 21 | 21 | 21 |

WACC 10.44% · Terminal growth 3.5% · Shares 2,638.163mm · Net debt ₹192,997mm

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Deploy Free (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. **New app** → select repo → main file `app.py` → **Deploy**.
4. Live at `https://<your-app>.streamlit.app`.

## Author

**Puttamreddy Gauthamsimha Reddy**  
Discounted Cash Flow valuation model · Indus Towers Ltd · Equity research project.

## Disclaimer

Educational and analytical use only. Not investment advice.
