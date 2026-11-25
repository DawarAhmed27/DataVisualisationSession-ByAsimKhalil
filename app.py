"""Online Retail dashboard - DAV pre-seminar activity.
Run:  streamlit run app.py
Expects Online_Retail.xlsx in the same folder (cached to a .pkl after first load).
"""
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

STUDENT = "Dawar Ahmed"
ROLL_NO = "24I2533"

HERE = Path(__file__).parent
XLSX = HERE / "Online_Retail.xlsx"
CACHE = HERE / "Online_Retail.pkl"
LOG_FILE = HERE / "dashboard.log"

# Stock codes that are fees/postage/manual adjustments, not real products
NON_PRODUCT = ["POST", "DOT", "M", "C2", "D", "S", "B", "BANK CHARGES",
               "AMAZONFEE", "CRUK", "PADS"]

# ---- Palette (validated light-mode set: blue = primary, orange = secondary) ----
BLUE, BLUE_LIGHT, ORANGE = "#257de0", "#b6d5f8", "#f47230"
INK, INK_SOFT, GRID, BG = "#111827", "#6b7280", "#e5e7eb", "#f4f7fb"
BLUE_RAMP = ["#eef5fe", "#cce3fd", "#9dc8f7", "#6aabf1", "#338ced", "#1b64be", "#0e3d7e"]

st.set_page_config(page_title="Online Retail Dashboard", page_icon="🛒", layout="wide")

st.markdown(f"""
<style>
.stApp {{ background: {BG}; }}
[data-testid="stSidebar"] {{ background: #ffffff; border-right: 1px solid {GRID}; }}
[data-testid="stMetric"] {{ background: #fff; border: 1px solid {GRID}; border-top: 4px solid {BLUE};
    border-radius: 10px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(16,24,40,.04); }}
[data-testid="stMetricLabel"] {{ color: {INK_SOFT}; }}
[data-testid="stMetricValue"] {{ color: {INK}; font-weight: 700; }}
.hero {{ background: linear-gradient(135deg, #0e3d7e 0%, #257de0 100%); color: #fff;
    padding: 22px 28px; border-radius: 14px; margin-bottom: 18px; }}
.hero h1 {{ margin: 0; font-size: 1.9rem; color: #fff; }}
.hero p {{ margin: 4px 0 0; opacity: .9; }}
.chip {{ display: inline-block; background: rgba(255,255,255,.18); border-radius: 999px;
    padding: 3px 12px; margin: 10px 8px 0 0; font-size: .85rem; }}
h3 {{ color: {INK}; }}
</style>
""", unsafe_allow_html=True)


# ---------------- Logging ----------------
def get_logger() -> logging.Logger:
    log = logging.getLogger("retail_dashboard")
    if not log.handlers:
        log.setLevel(logging.INFO)
        h = RotatingFileHandler(LOG_FILE, maxBytes=500_000, backupCount=2, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
        log.addHandler(h)
    return log


log = get_logger()


@st.cache_data(show_spinner="Loading data (first run reads the Excel file, ~1 min)...")
def load() -> pd.DataFrame:
    log.info("Loading data (cache exists: %s)", CACHE.exists())
    if CACHE.exists():
        df = pd.read_pickle(CACHE)
    else:
        df = pd.read_excel(XLSX)
        df.to_pickle(CACHE)
        log.info("Read %s and wrote cache %s", XLSX.name, CACHE.name)
    df["Sales"] = df["Quantity"] * df["UnitPrice"]
    df["StockCode"] = df["StockCode"].astype(str)
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    log.info("Loaded %s rows, %s columns", f"{len(df):,}", df.shape[1])
    return df


def style(fig, height=380, ytick=""):
    fig.update_layout(
        height=height, plot_bgcolor="white", paper_bgcolor="white", font=dict(color=INK, size=13),
        margin=dict(t=10, b=10, l=10, r=10), showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=13, bordercolor=GRID))
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickprefix=ytick, ticks="")
    return fig


def money(v):
    return f"£{v:,.0f}"


raw = load()

# ---------------- Sidebar ----------------
st.sidebar.header("Filters")
clean = st.sidebar.checkbox(
    "Clean data", value=True,
    help="Removes cancelled invoices (start with 'C'), rows with Quantity <= 0 "
         "and rows with UnitPrice <= 0. Untick for the raw dataset as given.")
only_products = st.sidebar.checkbox(
    "Exclude postage/fees from product ranking", value=True,
    help="Removes codes like POST, DOT (Dotcom postage), M (manual), BANK CHARGES.")
sel = st.sidebar.multiselect("Countries", sorted(raw["Country"].unique()), default=[])
d0, d1 = raw["InvoiceDate"].min().date(), raw["InvoiceDate"].max().date()
rng = st.sidebar.date_input("Date range", (d0, d1), min_value=d0, max_value=d1)

df = raw
if clean:
    df = df[~df["InvoiceNo"].str.startswith("C") & (df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
if sel:
    df = df[df["Country"].isin(sel)]
if isinstance(rng, tuple) and len(rng) == 2:
    df = df[(df["InvoiceDate"].dt.date >= rng[0]) & (df["InvoiceDate"].dt.date <= rng[1])]

log.info("View: clean=%s products_only=%s countries=%s range=%s -> %s rows",
         clean, only_products, sel or "all", rng, f"{len(df):,}")

# ---------------- Header ----------------
today = datetime.now().strftime("%A, %d %B %Y")
st.markdown(f"""
<div class="hero">
  <h1>🛒 Online Retail - Sales Dashboard</h1>
  <p>UK online gift retailer, 1 Dec 2010 - 9 Dec 2011 &middot; Sales = Quantity x UnitPrice</p>
  <span class="chip">👤 {STUDENT}</span><span class="chip">🎓 Roll No: {ROLL_NO}</span>
  <span class="chip">📅 {today}</span><span class="chip">DAV Seminar Activity</span>
</div>
""", unsafe_allow_html=True)

if df.empty:
    log.warning("Filters returned no rows")
    st.warning("No data for the current filters. Adjust the sidebar.")
    st.stop()

# ---------------- KPIs ----------------
monthly = (df.groupby("Month").agg(Sales=("Sales", "sum"), Orders=("InvoiceNo", "nunique")).reset_index())
monthly["AOV"] = monthly["Sales"] / monthly["Orders"]
by_country = df.groupby("Country", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)

total_sales = df["Sales"].sum()
n_orders = df["InvoiceNo"].nunique()
aov = total_sales / n_orders
log.info("KPIs: sales=%.2f orders=%d aov=%.2f", total_sales, n_orders, aov)

st.subheader("Key performance indicators")
k1, k2, k3 = st.columns(3)
k1.metric("Total sales", money(total_sales))
k2.metric("Orders", f"{n_orders:,}")
k3.metric("Average order value (AOV)", f"£{aov:,.2f}", help="Total sales / number of unique orders")
k4, k5, k6, k7 = st.columns(4)
k4.metric("Customers", f"{df['CustomerID'].nunique():,}", help="Rows without a CustomerID are not counted")
k5.metric("Units sold", f"{df['Quantity'].sum():,}")
k6.metric("Items per order", f"{df['Quantity'].sum() / n_orders:,.1f}")
best = monthly.loc[monthly["Sales"].idxmax()]
k7.metric("Best month", best["Month"], money(best["Sales"]), delta_color="off")

# ---------------- Monthly trend ----------------
st.subheader("Monthly trend")
kpi = st.radio("KPI", ["Sales", "Orders", "AOV"], horizontal=True, label_visibility="collapsed")
pre = "£" if kpi != "Orders" else ""
imax = monthly[kpi].idxmax()
fmt = (lambda v: f"£{v:,.0f}") if kpi == "Sales" else (lambda v: f"{v:,.0f}") if kpi == "Orders" else (lambda v: f"£{v:,.2f}")
if kpi == "AOV":
    fig = go.Figure(go.Scatter(
        x=monthly["Month"], y=monthly[kpi], mode="lines+markers", line=dict(color=ORANGE, width=2.5),
        marker=dict(size=9, color=ORANGE, line=dict(color="white", width=2)),
        hovertemplate="%{x}<br>AOV £%{y:,.2f}<extra></extra>"))
else:
    fig = go.Figure(go.Bar(
        x=monthly["Month"], y=monthly[kpi], marker_color=[BLUE if i == imax else BLUE_LIGHT for i in monthly.index],
        hovertemplate="%{x}<br>" + kpi + " " + pre + "%{y:,.0f}<extra></extra>"))
fig.add_annotation(x=monthly.loc[imax, "Month"], y=monthly.loc[imax, kpi], text=f"<b>Peak: {fmt(monthly.loc[imax, kpi])}</b>",
                   showarrow=False, yshift=16, font=dict(color=INK, size=13))
style(fig, 360, pre)
fig.update_yaxes(range=[0, monthly[kpi].max() * 1.15])
st.plotly_chart(fig, width="stretch")
st.caption("Highlighted = peak month. Dec 2011 is incomplete: the data ends on 9 December.")

left, right = st.columns(2)

# ---------------- Top 5 products ----------------
with left:
    st.subheader("Top 5 products by sales")
    p = df[~df["StockCode"].isin(NON_PRODUCT)] if only_products else df
    prod = (p.groupby("StockCode")
              .agg(Product=("Description", lambda s: s.mode().iat[0] if s.notna().any() else ""), Sales=("Sales", "sum"))
              .nlargest(5, "Sales").reset_index())
    pr = prod.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=pr["Sales"], y=pr["Product"].str.title(), orientation="h", marker_color=BLUE,
        text=[money(v) for v in pr["Sales"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>£%{x:,.0f}<extra></extra>"))
    style(fig, 340)
    fig.update_xaxes(visible=False, range=[0, pr["Sales"].max() * 1.25])
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch")

# ---------------- Countries ----------------
with right:
    st.subheader("Top countries by sales")
    skip_uk = st.checkbox("Hide United Kingdom (to compare the rest)", value=False)
    top = (by_country[by_country["Country"] != "United Kingdom"] if skip_uk else by_country).head(8).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=top["Sales"], y=top["Country"], orientation="h",
        marker_color=[BLUE if c == "United Kingdom" else BLUE_LIGHT if skip_uk is False else BLUE for c in top["Country"]],
        text=[money(v) for v in top["Sales"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>£%{x:,.0f}<extra></extra>"))
    style(fig, 340)
    fig.update_xaxes(visible=False, range=[0, top["Sales"].max() * 1.25])
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, width="stretch")
    lead = by_country.iloc[0]
    st.caption(f"{lead['Country']} accounts for {lead['Sales'] / by_country['Sales'].sum():.0%} of sales in this view.")

# ---------------- When do customers buy? ----------------
st.subheader("When do customers buy? (sales by weekday and hour)")
h = df.assign(Day=df["InvoiceDate"].dt.day_name(), Hour=df["InvoiceDate"].dt.hour)
order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
pv = h.pivot_table(index="Day", columns="Hour", values="Sales", aggfunc="sum", fill_value=0).reindex(order).fillna(0)
fig = go.Figure(go.Heatmap(
    z=pv.values, x=[f"{c:02d}:00" for c in pv.columns], y=pv.index,
    colorscale=[[i / (len(BLUE_RAMP) - 1), c] for i, c in enumerate(BLUE_RAMP)],
    xgap=2, ygap=2, colorbar=dict(title="Sales (£)", thickness=12),
    hovertemplate="%{y} %{x}<br>£%{z:,.0f}<extra></extra>"))
style(fig, 330)
fig.update_yaxes(autorange="reversed", showgrid=False)
st.plotly_chart(fig, width="stretch")
st.caption("Darker = more sales. The shop records no Saturday sales.")

# ---------------- Table view + logs + notes ----------------
with st.expander("Table view - monthly KPIs"):
    t = monthly[["Month", "Sales", "Orders", "AOV"]].copy()
    t["Sales"], t["AOV"] = t["Sales"].round(0), t["AOV"].round(2)
    st.dataframe(t, hide_index=True, width="stretch")

with st.expander("Activity log"):
    if LOG_FILE.exists():
        st.code("\n".join(LOG_FILE.read_text(encoding="utf-8").splitlines()[-25:]), language="text")
        st.caption(f"Full log saved to {LOG_FILE.name} next to app.py.")

with st.expander("Data notes"):
    st.markdown(
        "- **Clean data** (default) drops cancellations, returns and zero-price rows. "
        "Untick it to see the raw dataset where returns reduce total sales.\n"
        "- Some stock codes are postage/fees, not products (e.g. DOTCOM POSTAGE). "
        "They are excluded from the product ranking by default.\n"
        "- About 25% of rows have no CustomerID; they still count in sales and orders.")
