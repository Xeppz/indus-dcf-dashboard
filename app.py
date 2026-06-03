"""
Discounted Cash Flow Dashboard — Indus Towers Ltd

An interactive equity valuation model. The DCF engine runs in Python; the interface
is built with Streamlit. Base-case intrinsic value ties to the underlying Excel model
at Rs.812.09 per share.

Built by Puttamreddy Gauthamsimha Reddy.
Run:  streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# live price helper — Alpha Vantage API (key stored securely in Streamlit secrets)
import urllib.request, json

@st.cache_data(ttl=300)   # cache 5 min so we don't burn the daily API quota
def fetch_live_price():
    """Fetch Indus Towers live price from Alpha Vantage.
    Free tier supports NSE via the BSE/NSE suffix. Returns (price, error_detail)."""
    api_key = st.secrets.get("ALPHA_VANTAGE_KEY", "")
    if not api_key:
        return None, "no_key"
    # Alpha Vantage uses GLOBAL_QUOTE with an exchange suffix for Indian stocks
    symbols = ["INDUSTOWER.BSE", "INDUSTOWER.NSE", "INDUSTOWER.BO"]
    last_msg = "unknown_error"
    for sym in symbols:
        try:
            url = (f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
                   f"&symbol={sym}&apikey={api_key}")
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            # successful quote
            quote = data.get("Global Quote") or data.get("Global Quote ", {})
            if quote and quote.get("05. price"):
                px = float(quote["05. price"])
                if px > 0:
                    return px, None
            # API limit / info messages
            if "Note" in data:
                last_msg = "Daily API limit reached — try again later"
            elif "Information" in data:
                last_msg = data["Information"][:120]
            elif "Error Message" in data:
                last_msg = f"symbol {sym} not found"
            else:
                last_msg = f"no price for {sym}"
        except Exception as e:
            last_msg = str(e)
    return None, last_msg

st.set_page_config(page_title="DCF Dashboard · Indus Towers Ltd", page_icon="◆", layout="wide",
                   initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════════════════════════════
#  EXCEL DEFAULTS  — these reproduce Rs.812.09 exactly. DO NOT EDIT.
# ════════════════════════════════════════════════════════════════════════════
BASE_REV   = 304686.0                    # FY25 Total Income
EXACT_WACC = 10.437451986537956          # %
TGR_DEF    = 3.5                          # %
TAX_DEF    = 25.0                          # % (sidebar single value; see note below)
SHARES     = 2638.163                     # mm
CASH_DEF   = 18561.0
DEBT_DEF   = 211558.0

# Year-by-year base curves (FY26E..FY30E)
G_BASE     = [6.0, 7.0, 8.0, 8.0, 7.0]            # revenue growth %
EBITM_BASE = [44.0, 44.0, 49.0, 49.0, 51.0]       # EBIT margin %
TAXE_BASE  = [23.25220145658716, 23.605157282339106,
              24.027129967421246, 24.173842615153493,
              24.326189080613167]                  # tax % of EBIT (Excel)
DA_BASE    = [21.0, 21.0, 21.0, 21.0, 21.0]        # D&A % of revenue
CAPEX_BASE = [18.0, 16.0, 15.0, 14.0, 13.0]        # CapEx % of revenue
NWC_BASE   = [4.383927136256940, 1.219065858309802,
              2.331276860079425, 1.450759356274240,
              1.661661684708464]                    # change in NWC % of revenue

FCAST = ["FY26E","FY27E","FY28E","FY29E","FY30E"]
HIST_YEARS = ["FY21","FY22","FY23","FY24","FY25"]
ALL_YEARS  = HIST_YEARS + FCAST

# Historical actuals (from statements)
H_REV   = [139543,277172,283818,286006,301228]
H_EBITDA= [74568,152954,101283,150550,211905]
H_EBIT  = [46084,99702,48044,89951,147884]
H_PAT   = [37790,63731,20400,60362,99317]
H_DA    = [28484,53252,53239,60599,64021]
H_CAPEX = [19518,28697,31681,84465,62571]
H_FCF   = [53627,58361,42822,26292,128610]

# ════════════════════════════════════════════════════════════════════════════
#  DCF ENGINE  (parallel-shift logic for growth & margin)
# ════════════════════════════════════════════════════════════════════════════
def shift(curve, slider_first_val, base_first_val):
    """Parallel shift: move whole curve by (slider - base_first)."""
    delta = slider_first_val - base_first_val
    return [c + delta for c in curve]

def run_dcf(g_first, ebitm_first, wacc, tgr, tax_rate,
            base_rev=BASE_REV, shares=SHARES, cash=CASH_DEF, debt=DEBT_DEF,
            use_tax_ebit_curve=True):
    # build shifted curves
    g_curve     = shift(G_BASE, g_first, G_BASE[0])
    ebitm_curve = shift(EBITM_BASE, ebitm_first, EBITM_BASE[0])

    w = wacc/100.0
    t = tgr/100.0
    g_  = [x/100.0 for x in g_curve]
    em_ = [x/100.0 for x in ebitm_curve]
    da_ = [x/100.0 for x in DA_BASE]
    cx_ = [x/100.0 for x in CAPEX_BASE]
    nw_ = [x/100.0 for x in NWC_BASE]

    # tax: if user keeps default we use the exact Excel per-year curve so the
    # base case ties to the dot; if user changes the single tax slider we apply
    # that flat rate to every year (per your instruction "tax stays the same").
    if use_tax_ebit_curve:
        tax_ = [x/100.0 for x in TAXE_BASE]
    else:
        tax_ = [tax_rate/100.0]*5

    rev=[]; prev=base_rev
    for gr in g_:
        prev = prev*(1+gr); rev.append(prev)

    ebit  = [rev[i]*em_[i]            for i in range(5)]
    ebiat = [ebit[i]*(1-tax_[i])      for i in range(5)]
    da    = [rev[i]*da_[i]            for i in range(5)]
    capex = [rev[i]*cx_[i]            for i in range(5)]
    nwc   = [rev[i]*nw_[i]            for i in range(5)]
    ufcf  = [ebiat[i]+da[i]-capex[i]-nwc[i] for i in range(5)]

    pv    = [ufcf[i]/(1+w)**(i+0.5)   for i in range(5)]   # mid-year convention
    sum_pv= sum(pv)
    tv    = ufcf[4]*(1+t)/(w-t) if w>t else float('inf')
    pv_tv = tv/(1+w)**5
    ev    = sum_pv+pv_tv
    net_debt = debt-cash
    eq    = ev-net_debt
    sp    = eq/shares

    return dict(rev=rev, ebit=ebit, ebiat=ebiat, da=da, capex=capex, nwc=nwc,
                ufcf=ufcf, pv=pv, sum_pv=sum_pv, tv=tv, pv_tv=pv_tv,
                ev=ev, eq=eq, sp=sp, net_debt=net_debt,
                g_curve=g_curve, ebitm_curve=ebitm_curve)

# ════════════════════════════════════════════════════════════════════════════
#  THEME  — institutional dark, blue/green accents, hover effects
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* deep black-grey base, no colourful background */
.stApp{background:#0a0a0c;}
*{font-family:'Inter',sans-serif;}

/* Sidebar — slightly lighter charcoal */
section[data-testid="stSidebar"]{background:#0f0f12;border-right:1px solid #1f1f24;}
section[data-testid="stSidebar"] *{color:#c7ccd4 !important;}
section[data-testid="stSidebar"] h3{color:#f3f4f6 !important;font-size:15px !important;font-weight:700 !important;}

h1,h2,h3,h4{color:#f3f4f6 !important;letter-spacing:-.01em;}
.block-container{padding-top:1.4rem;padding-bottom:2rem;max-width:1400px;}

/* ── KPI metric cards ── */
[data-testid="stMetric"]{
    background:#141417;
    border:1px solid #232328;border-radius:14px;padding:16px 18px;
    border-top:2px solid #ff7a45;
    transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}
[data-testid="stMetric"]:hover{
    transform:translateY(-3px);
    box-shadow:0 8px 30px rgba(255,122,69,.16);
    border-color:#ff7a45;
}
[data-testid="stMetricValue"]{color:#ff7a45 !important;font-weight:800 !important;font-size:26px !important;}
[data-testid="stMetricLabel"]{color:#7c7f88 !important;font-size:10.5px !important;
    text-transform:uppercase;letter-spacing:.09em;font-weight:600 !important;}
[data-testid="stMetricDelta"]{font-size:12px !important;}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{
    background:#0f0f12;border:1px solid #232328;border-radius:14px;
    padding:6px;gap:4px;
}
.stTabs [data-baseweb="tab"]{
    color:#7c7f88;font-size:13px;font-weight:600;border-radius:9px;
    padding:10px 22px;letter-spacing:.02em;transition:all .15s ease;background:transparent;
}
.stTabs [data-baseweb="tab"]:hover{color:#f3f4f6;background:#1a1a1f;}
.stTabs [aria-selected="true"]{
    background:linear-gradient(135deg,#ff7a45 0%,#ff5e3a 100%) !important;
    color:#fff !important;box-shadow:0 4px 16px rgba(255,94,58,.35);
}
.stTabs [data-baseweb="tab-highlight"]{background:transparent;}
.stTabs [data-baseweb="tab-border"]{background:transparent;}

/* ── Section title ── */
.sec{font-size:12px;font-weight:700;color:#ff7a45;letter-spacing:.1em;
    text-transform:uppercase;margin:8px 0 14px;padding-bottom:8px;
    border-bottom:1px solid #232328;}

/* ── Waterfall lines ── */
.wf-line{display:flex;justify-content:space-between;padding:10px 6px;
    border-bottom:1px solid #1f1f24;font-size:14px;transition:background .12s;}
.wf-line:hover{background:#16161a;}
.wf-line.total{font-weight:700;color:#ff7a45;border-bottom:2px solid #ff5e3a;}
.wf-line .lbl{color:#9296a0;}
.wf-line .val{color:#e8eaed;font-weight:600;}
.wf-line .val.green{color:#3ddc97;}.wf-line .val.red{color:#ff6b5b;}

/* ── Buttons ── */
.stButton button{background:#1a1a1f;
    border:1px solid #2e2e35;color:#c7ccd4;border-radius:9px;
    font-size:12px;font-weight:600;width:100%;transition:all .15s;}
.stButton button:hover{border-color:#ff7a45;color:#fff;
    box-shadow:0 4px 16px rgba(255,122,69,.2);}

/* ── Hero header ── */
.hero{background:#141417;
    border:1px solid #232328;border-left:3px solid #ff7a45;border-radius:14px;
    padding:20px 26px;margin-bottom:20px;}
.hero h1{font-size:26px;font-weight:800;margin:0;color:#f3f4f6 !important;}
.hero .sub{color:#7c7f88;font-size:13px;margin-top:4px;letter-spacing:.02em;}
.hero .tags{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;}
.hero .tag{background:#1a1a1f;border:1px solid #2e2e35;border-radius:6px;
    padding:4px 12px;font-size:11px;color:#9296a0;letter-spacing:.03em;}
.hero .tag.live{border-color:#2bb583;color:#3ddc97;}

/* ── Expander ── */
[data-testid="stExpander"]{background:#0f0f12;border:1px solid #232328;border-radius:10px;}

/* ── Dataframe ── */
[data-testid="stDataFrame"]{border:1px solid #232328;border-radius:10px;}

/* ── Footer credit ── */
.credit{margin-top:32px;padding:18px 0;border-top:1px solid #232328;
    text-align:center;color:#6b6e76;font-size:12px;letter-spacing:.03em;}
.credit b{color:#c7ccd4;font-weight:600;}
.credit .role{color:#54565d;font-size:11px;margin-top:3px;}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("### Discounted Cash Flow")
st.sidebar.markdown("##### Indus Towers Ltd · Assumptions")

def do_reset():
    for k in ["g_first","ebitm_first","wacc","tgr","tax"]:
        st.session_state.pop(k, None)
    st.session_state.update(g_first=6.0, ebitm_first=44.0,
                            wacc=EXACT_WACC, tgr=3.5, tax=25.0)

st.sidebar.button("Reset to base-case assumptions", on_click=do_reset)

st.sidebar.markdown("#### Key Value Drivers")
g_first = st.sidebar.slider("Revenue Growth — Year 1 (shifts whole curve)",
    0.0, 20.0, st.session_state.get("g_first",6.0), 0.5, key="g_first")
ebitm_first = st.sidebar.slider("EBIT Margin — Year 1 (shifts whole curve)",
    20.0, 65.0, st.session_state.get("ebitm_first",44.0), 0.5, key="ebitm_first")
wacc = st.sidebar.slider("WACC (%)",
    6.0, 15.0, st.session_state.get("wacc",EXACT_WACC), 0.05, key="wacc")
tgr = st.sidebar.slider("Terminal Growth Rate (%)",
    1.0, 5.0, st.session_state.get("tgr",3.5), 0.1, key="tgr")
tax = st.sidebar.slider("Tax Rate (% — applied to all years)",
    15.0, 35.0, st.session_state.get("tax",25.0), 0.5, key="tax")

at_base_tax = abs(tax-25.0) < 0.001
use_curve = at_base_tax

gc = shift(G_BASE, g_first, G_BASE[0])
ec = shift(EBITM_BASE, ebitm_first, EBITM_BASE[0])
st.sidebar.markdown("###### Resulting forecast curves")
st.sidebar.caption(f"Revenue growth: {', '.join(f'{x:.1f}%' for x in gc)}")
st.sidebar.caption(f"EBIT margin: {', '.join(f'{x:.1f}%' for x in ec)}")

R = run_dcf(g_first, ebitm_first, wacc, tgr, tax, use_tax_ebit_curve=use_curve)

# ── Market price ──
st.sidebar.markdown("#### Market Price")
if "mkt_price" not in st.session_state:
    st.session_state.mkt_price = 435.65
if st.sidebar.button("Fetch live price (NSE · Alpha Vantage)"):
    px, err = fetch_live_price()
    if px:
        st.session_state.mkt_price = round(px, 2)
        st.sidebar.success(f"Live price: ₹{px:.2f}")
    elif err == "no_key":
        st.sidebar.info("Live price needs an API key. Add ALPHA_VANTAGE_KEY in "
                        "app Settings → Secrets. Using manual value for now.")
    else:
        st.sidebar.warning("Live price unavailable — using manual value below.")
        with st.sidebar.expander("Why? (details)"):
            st.caption(f"API response: {err}")
MKT = st.sidebar.number_input("Market Price (₹)", value=float(st.session_state.mkt_price), step=1.0)
st.session_state.mkt_price = MKT
upside = (R["sp"]-MKT)/MKT*100

# ════════════════════════════════════════════════════════════════════════════
#  HERO HEADER
# ════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="hero">
  <h1>Discounted Cash Flow Dashboard — Indus Towers Ltd</h1>
  <div class="sub">Intrinsic equity valuation · Five-year explicit forecast (FY26E–FY30E) with Gordon-growth terminal value</div>
  <div class="tags">
    <span class="tag">NSE: INDUSTOWER</span>
    <span class="tag">Telecom Infrastructure</span>
    <span class="tag">Consolidated · ₹ million</span>
    <span class="tag live">● Live recalculation</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Company description
with st.expander("About Indus Towers & this model"):
    st.markdown("""
    **Indus Towers Limited** is one of the world's largest telecom tower infrastructure
    providers, operating a portfolio of over 240,000 towers across India. It leases passive
    infrastructure (towers, power, and related assets) to mobile network operators on long-term
    contracts, earning stable, annuity-like rental revenue. Its largest customers include Bharti
    Airtel and Vodafone Idea.

    **This model** values the company using an unlevered discounted cash flow (DCF) approach:

    - **Unlevered Free Cash Flow** = EBIT × (1 − tax) + D&A − CapEx − change in net working capital
    - Cash flows are discounted at the **WACC** using the mid-year convention
    - A **Gordon-growth terminal value** captures cash flows beyond the explicit forecast
    - **Enterprise Value** is bridged to **Equity Value** by adding cash and subtracting debt,
      then divided by shares outstanding to give the **intrinsic value per share**

    Move the sidebar drivers to test how the valuation responds. The base case reproduces the
    underlying Excel model precisely.
    """)

# ════════════════════════════════════════════════════════════════════════════
#  KPI CARDS
# ════════════════════════════════════════════════════════════════════════════
k1,k2,k3,k4 = st.columns(4)
k1.metric("Intrinsic Value / Share", f"₹{R['sp']:.2f}", f"{upside:+.1f}% vs market")
k2.metric("Current Market Price", f"₹{MKT:.2f}")
k3.metric("Enterprise Value", f"₹{R['ev']/1000:,.0f}B")
k4.metric("Equity Value", f"₹{R['eq']/1000:,.0f}B")

k5,k6,k7,k8 = st.columns(4)
k5.metric("WACC", f"{wacc:.2f}%")
k6.metric("Terminal Growth Rate", f"{tgr:.1f}%")
k7.metric("Explicit PV Share", f"{R['sum_pv']/R['ev']*100:.1f}%")
k8.metric("Terminal Value Share", f"{R['pv_tv']/R['ev']*100:.1f}%")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
#  CHART STYLING
# ════════════════════════════════════════════════════════════════════════════
# Black-grey theme palette — orange-coral primary
ORANGE="#ff7a45"; ORANGE_L="#ff9a6b"; CORAL="#ff5e3a"
BLUE="#5b8def"; BLUE_L="#7aa5f5"; GREEN="#3ddc97"; GREEN_D="#2bb583"
AMBER="#f5a623"; RED="#ff6b5b"; YELLOW="#e8b84b"; PURPLE="#a78bfa"; SLATE="#3a4a63"

def sty(fig, h=320, legend=True):
    """MetricFlow look: minimal horizontal gridlines, no vertical lines,
    soft rounded tooltip, clean axis, no plot border."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8a98ad", family="Inter", size=11),
        margin=dict(l=14,r=14,t=30,b=14), height=h,
        legend=dict(orientation="h", y=1.18, x=0, font=dict(size=10, color="#8a98ad"),
                    bgcolor="rgba(0,0,0,0)") if legend else dict(),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1a1a1f", bordercolor="#2e2e35",
                        font=dict(color="#e2e8f0", family="Inter", size=12)),
        bargap=0.35, bargroupgap=0.12,
    )
    # x-axis: no gridlines, thin baseline only
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False,
                     tickfont=dict(size=10, color="#6b7a90"))
    # y-axis: faint horizontal gridlines only
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,.045)",
                     zeroline=False, showline=False,
                     tickfont=dict(size=10, color="#6b7a90"))
    return fig

def bar_grad(color):
    return dict(color=color, line=dict(width=0))

def smooth_line(fig, x, y, name, color, fill=True, dash=None):
    """Curved spline line with soft gradient fill + glow markers, MetricFlow style."""
    # convert hex to rgba for fill
    h=color.lstrip('#'); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    fig.add_scatter(
        x=x, y=y, name=name, mode="lines",
        line=dict(color=color, width=3, shape="spline", smoothing=1.3,
                  dash=dash),
        fill="tozeroy" if fill else None,
        fillcolor=f"rgba({r},{g},{b},0.10)" if fill else None,
        hovertemplate="%{y:,.0f}<extra></extra>",
    )
    return fig

# ════════════════════════════════════════════════════════════════════════════
#  TABS
# ════════════════════════════════════════════════════════════════════════════
t1,t2,t3,t4 = st.tabs(["DCF Model", "Charts & Analysis", "Sensitivity", "Scenarios"])

# ── TAB 1: DCF MODEL ─────────────────────────────────────────────────────────
with t1:
    cL,cR = st.columns([3,2], gap="medium")
    with cL:
        st.markdown('<div class="sec">Enterprise Value → Equity Value Bridge</div>', unsafe_allow_html=True)
        rows = [
            ("PV of Explicit Free Cash Flows (FY26E–FY30E)", f"₹{R['sum_pv']:,.0f}", "", False),
            ("PV of Terminal Value", f"₹{R['pv_tv']:,.0f}", "", False),
            ("Enterprise Value", f"₹{R['ev']:,.0f}", "", True),
            ("Add: Cash &amp; Bank Balances", f"+₹{CASH_DEF:,.0f}", "green", False),
            ("Less: Total Debt", f"−₹{DEBT_DEF:,.0f}", "red", False),
            ("Equity Value", f"₹{R['eq']:,.0f}", "", True),
            ("Shares Outstanding", f"{SHARES:,.1f} mm", "", False),
        ]
        html = "".join(
            f'<div class="wf-line {"total" if tot else ""}"><span class="lbl">{l}</span>'
            f'<span class="val {cls}">{v}</span></div>'
            for l,v,cls,tot in rows)
        html += (f'<div class="wf-line total" style="font-size:18px;margin-top:6px">'
                 f'<span class="lbl" style="color:#f1f5f9">Intrinsic Value per Share</span>'
                 f'<span class="val green" style="font-size:24px">₹{R["sp"]:.2f}</span></div>')
        st.markdown(html, unsafe_allow_html=True)
    with cR:
        st.markdown('<div class="sec">Value Composition</div>', unsafe_allow_html=True)
        fig=go.Figure(go.Pie(labels=["Explicit FCFs","Terminal Value"],
            values=[R["sum_pv"],R["pv_tv"]], hole=.68,
            marker=dict(colors=[ORANGE,"#3a3a42"], line=dict(color="#0a0a0c",width=3)),
            textfont=dict(color="#e2e8f0",size=12)))
        fig.update_layout(annotations=[dict(text=f"EV<br>₹{R['ev']/1000:,.0f}B",
            x=.5,y=.5,font=dict(size=15,color="#f3f4f6"),showarrow=False)])
        st.plotly_chart(sty(fig,300,legend=True), use_container_width=True)

    st.markdown('<div class="sec">Forecast Cash Flow Detail (₹ million)</div>', unsafe_allow_html=True)
    df=pd.DataFrame({
        "Year":FCAST,
        "Revenue":[round(x) for x in R["rev"]],
        "EBIT":[round(x) for x in R["ebit"]],
        "EBIAT":[round(x) for x in R["ebiat"]],
        "D&A":[round(x) for x in R["da"]],
        "CapEx":[round(x) for x in R["capex"]],
        "Δ NWC":[round(x) for x in R["nwc"]],
        "Unlevered FCF":[round(x) for x in R["ufcf"]],
        "PV of FCF":[round(x) for x in R["pv"]],
    }).set_index("Year")
    st.dataframe(df, use_container_width=True)

# ── TAB 2: CHARTS ────────────────────────────────────────────────────────────
with t2:
    fr=[round(x) for x in R["rev"]]
    RADIUS=6
    c1,c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown('<div class="sec">Revenue Trajectory — Historical & Forecast</div>', unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_bar(x=HIST_YEARS, y=H_REV, name="Historical", marker=dict(color="#5a4a42"),
                    hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
        fig.add_bar(x=FCAST, y=fr, name="Forecast", marker=dict(color=ORANGE),
                    hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
        fig.update_layout(barmode="group", barcornerradius=RADIUS)
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(sty(fig), use_container_width=True)
    with c2:
        st.markdown('<div class="sec">Profitability Margins (% of Revenue)</div>', unsafe_allow_html=True)
        em_h=[H_EBITDA[i]/H_REV[i]*100 for i in range(5)]
        ebitda_e=[ec[i]*1.12 for i in range(5)]
        ebit_all=[H_EBIT[i]/H_REV[i]*100 for i in range(5)]+[R["ebit"][i]/R["rev"][i]*100 for i in range(5)]
        fig=go.Figure()
        smooth_line(fig, ALL_YEARS, em_h+ebitda_e, "EBITDA margin", ORANGE, fill=True)
        smooth_line(fig, ALL_YEARS, ebit_all, "EBIT margin", BLUE_L, fill=False, dash="dot")
        # highlight markers on final point
        fig.add_scatter(x=[ALL_YEARS[-1]], y=[ (em_h+ebitda_e)[-1] ], mode="markers",
            marker=dict(size=9,color=ORANGE,line=dict(color="#0a0a0c",width=2)),
            showlegend=False, hoverinfo="skip")
        fig.update_yaxes(ticksuffix="%")
        st.plotly_chart(sty(fig), use_container_width=True)
    c3,c4 = st.columns(2, gap="medium")
    with c3:
        st.markdown('<div class="sec">Capital Expenditure vs Depreciation</div>', unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_bar(x=ALL_YEARS, y=H_CAPEX+[round(x) for x in R["capex"]], name="CapEx",
                    marker=dict(color=ORANGE), hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
        fig.add_bar(x=ALL_YEARS, y=H_DA+[round(x) for x in R["da"]], name="Depreciation & Amortisation",
                    marker=dict(color="#6b7280"), hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
        fig.update_layout(barmode="group", barcornerradius=RADIUS)
        st.plotly_chart(sty(fig), use_container_width=True)
    with c4:
        st.markdown('<div class="sec">Free Cash Flow Generation</div>', unsafe_allow_html=True)
        allf=H_FCF+[round(x) for x in R["ufcf"]]
        fig=go.Figure()
        fig.add_bar(x=ALL_YEARS, y=allf, marker=dict(color=[GREEN if v>=0 else RED for v in allf]),
                    hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
        fig.update_layout(barcornerradius=RADIUS)
        st.plotly_chart(sty(fig,legend=False), use_container_width=True)
    st.markdown('<div class="sec">Unlevered FCF vs Present Value — Discounting Effect</div>', unsafe_allow_html=True)
    fig=go.Figure()
    fig.add_bar(x=FCAST, y=[round(x) for x in R["ufcf"]], name="Unlevered FCF",
                marker=dict(color=ORANGE), hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
    fig.add_bar(x=FCAST, y=[round(x) for x in R["pv"]], name="Present Value",
                marker=dict(color="#6b7280"), hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>")
    fig.update_layout(barmode="group", barcornerradius=RADIUS)
    st.plotly_chart(sty(fig,300), use_container_width=True)

# ── TAB 3: SENSITIVITY ───────────────────────────────────────────────────────
with t3:
    st.markdown('<div class="sec">Implied Share Price (₹) — WACC vs Terminal Growth Rate</div>', unsafe_allow_html=True)
    waccs=[wacc-1,wacc-0.5,wacc,wacc+0.5,wacc+1]
    tgrs=[tgr-1,tgr-0.5,tgr,tgr+0.5,tgr+1]
    data=[]
    for tt in tgrs:
        row=[]
        for w in waccs:
            row.append(None if w<=tt else round(run_dcf(g_first,ebitm_first,w,tt,tax,use_tax_ebit_curve=use_curve)["sp"]))
        data.append(row)
    sdf=pd.DataFrame(data, index=[f"{x:.1f}%" for x in tgrs], columns=[f"{x:.2f}%" for x in waccs])
    def csp(v):
        if v is None: return "background-color:#0f0f12;color:#54565d"
        u=(v-MKT)/MKT
        if u>0.5: return "background-color:#0d3d28;color:#5ee9a8;font-weight:600"
        if u>0.2: return "background-color:#10402a;color:#9af0c4"
        if u>0: return "background-color:#13241c;color:#9af0c4"
        if u>-0.2: return "background-color:#3a2410;color:#ffb27a"
        return "background-color:#4a1f18;color:#ff9080"
    st.dataframe(sdf.style.map(csp).format(lambda v:f"₹{v}" if v is not None else "—"), use_container_width=True)
    st.caption("Rows: terminal growth rate · Columns: WACC · Centre cell reflects current sidebar selection")

    st.markdown('<div class="sec">Implied Share Price (₹) — EBIT Margin vs Revenue Growth</div>', unsafe_allow_html=True)
    ms=[ebitm_first-4,ebitm_first-2,ebitm_first,ebitm_first+2,ebitm_first+4]
    gs=[g_first-2,g_first-1,g_first,g_first+1,g_first+2]
    d2=[[round(run_dcf(gg,m,wacc,tgr,tax,use_tax_ebit_curve=use_curve)["sp"]) for gg in gs] for m in ms]
    s2=pd.DataFrame(d2, index=[f"{m:.0f}%" for m in ms], columns=[f"{gg:.0f}%" for gg in gs])
    st.dataframe(s2.style.map(csp).format(lambda v:f"₹{v}"), use_container_width=True)
    st.caption("Rows: EBIT margin (Year 1, shifts curve) · Columns: revenue growth (Year 1, shifts curve)")

# ── TAB 4: SCENARIOS ─────────────────────────────────────────────────────────
with t4:
    st.markdown('<div class="sec">Scenario Analysis — Share Price across Bull / Base / Bear</div>', unsafe_allow_html=True)
    st.caption("Scenarios flex only WACC (risk perception) and terminal growth rate (long-run growth view). "
               "Operating assumptions — revenue growth, EBIT margin, CapEx — are held constant across all three.")
    scens=[
        ("Bull", EXACT_WACC, 3.5, "Current model — successful deleveraging, EBITDA margin recovery, Vodafone Idea receivables normalising"),
        ("Base", 11.5, 3.0, "Slightly higher WACC (+100 bps for equity risk), conservative 3% terminal growth"),
        ("Bear", 12.5, 2.0, "Higher WACC (+200 bps for Vodafone Idea default / single-customer concentration risk), 2% terminal growth"),
    ]
    cols=st.columns(3, gap="medium")
    sps=[]
    cmap={"Bull":GREEN,"Base":BLUE_L,"Bear":RED}
    for i,(nm,w,t,rat) in enumerate(scens):
        rr=run_dcf(6.0,44.0,w,t,tax,use_tax_ebit_curve=True)
        sps.append(rr["sp"]); up=(rr["sp"]-MKT)/MKT*100
        cols[i].metric(f"{nm} Case", f"₹{rr['sp']:.2f}", f"{up:+.1f}% vs market")
        cols[i].caption(f"WACC {w:.2f}% · TGR {t:.1f}%")
        cols[i].caption(rat)
    fig=go.Figure()
    fig.add_bar(x=["Bull","Base","Bear"], y=[round(x,2) for x in sps],
                marker=dict(color=[GREEN,ORANGE,RED]),
                text=[f"₹{x:.0f}" for x in sps], textposition="outside",
                textfont=dict(color="#e2e8f0",size=14),
                hovertemplate="%{x}: ₹%{y:,.2f}<extra></extra>", width=0.55)
    fig.add_hline(y=MKT, line_dash="dot", line_color=YELLOW, line_width=1.5,
                  annotation_text=f"Market ₹{MKT:.2f}", annotation_font_color="#e8b84b")
    fig.update_layout(barcornerradius=8)
    st.plotly_chart(sty(fig,320,legend=False), use_container_width=True)
    st.markdown("""
    ##### Methodology Notes
    - Operating assumptions (revenue, EBITDA, CapEx) are held constant across scenarios
    - Scenarios flex only WACC, capturing risk perception, and terminal growth, capturing the long-run growth view
    - For a full bull / base / bear with differing operating cases, flex revenue growth, EBIT margin and CapEx independently using the sidebar
    """)

# ════════════════════════════════════════════════════════════════════════════
#  FOOTER CREDIT
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="credit">
  Built by <b>Puttamreddy Gauthamsimha Reddy</b>
  <div class="role">Discounted Cash Flow Valuation · Indus Towers Ltd · Equity Research Model</div>
</div>
""", unsafe_allow_html=True)
