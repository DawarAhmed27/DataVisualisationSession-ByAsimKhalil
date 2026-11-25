"""Online Retail dashboard - DAV pre-seminar activity.
Run:  streamlit run app.py
Expects Online_Retail.xlsx in the same folder (cached to a .pkl after first load).
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

HERE = Path(__file__).parent
XLSX = HERE / "Online_Retail.xlsx"
CACHE = HERE / "Online_Retail.pkl"

# Stock codes that are fees/postage/manual adjustments, not real products
NON_PRODUCT = ["POST", "DOT", "M", "C2", "D", "S", "B", "BANK CHARGES",
               "AMAZONFEE", "CRUK", "PADS"]

BLUE, GREY = "#2563eb", "#cbd5e1"

st.set_page_config(page_title="Online Retail Dashboard", page_icon="🛒", layout="wide")


@st.cache_data(show_spinner="Loading data (first run reads the Excel file, ~1 min)...")
def load() -> pd.DataFrame:
    if CACHE.exists():
        df = pd.read_pickle(CACHE)
    else:
        df = pd.read_excel(XLSX)
        df.to_pickle(CACHE)
    df["Sales"] = df["Quantity"] * df["UnitPrice"]
    df["StockCode"] = df["StockCode"].astype(str)
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["Month"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    return df


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
countries = sorted(raw["Country"].unique())
sel = st.sidebar.multiselect("Countries", countries, default=[])
d0, d1 = raw["InvoiceDate"].min().date(), raw["InvoiceDate"].max().date()
rng = st.sidebar.date_input("Date range", (d0, d1), min_value=d0, max_value=d1)

df = raw
if clean:
    df = df[~df["InvoiceNo"].str.startswith("C") & (df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
if sel:
    df = df[df["Country"].isin(sel)]
if isinstance(rng, tuple) and len(rng) == 2:
    df = df[(df["InvoiceDate"].dt.date >= rng[0]) & (df["InvoiceDate"].dt.date <= rng[1])]

# ---------------- Header + KPIs ----------------
st.title("🛒 Online Retail - Sales Dashboard")
st.caption("UK online gift retailer, 1 Dec 2010 - 9 Dec 2011. Sales = Quantity x UnitPrice.")

monthly = df.groupby("Month", as_index=False)["Sales"].sum()
by_country = df.groupby("Country", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total sales", f"£{df['Sales'].sum():,.0f}")
c2.metric("Unique orders", f"{df['InvoiceNo'].nunique():,}")
if len(monthly):
    best = monthly.loc[monthly["Sales"].idxmax()]
    c3.metric("Best month", best["Month"], f"£{best['Sales']:,.0f}", delta_color="off")
    c4.metric("Top country", by_country.iloc[0]["Country"], f"£{by_country.iloc[0]['Sales']:,.0f}", delta_color="off")

st.divider()

# ---------------- Monthly sales ----------------
st.subheader("Sales by month")
if len(monthly):
    monthly["colour"] = monthly["Sales"].eq(monthly["Sales"].max()).map({True: BLUE, False: GREY})
    fig = px.bar(monthly, x="Month", y="Sales", color="colour",
                 color_discrete_map="identity", labels={"Sales": "Sales (£)"})
    fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                      margin=dict(t=10, b=10))
    fig.update_yaxes(tickprefix="£", gridcolor="#e5e7eb")
    st.plotly_chart(fig, width="stretch")
    st.caption("Dec 2011 is incomplete: the data ends on 9 December.")

left, right = st.columns(2)

# ---------------- Top 5 products ----------------
with left:
    st.subheader("Top 5 products by sales")
    p = df[~df["StockCode"].isin(NON_PRODUCT)] if only_products else df
    prod = (p.groupby("StockCode")
              .agg(Product=("Description", lambda s: s.mode().iat[0] if s.notna().any() else ""),
                   Sales=("Sales", "sum"))
              .nlargest(5, "Sales").reset_index())
    fig = px.bar(prod.iloc[::-1], x="Sales", y="Product", orientation="h",
                 color_discrete_sequence=[BLUE], labels={"Sales": "Sales (£)"})
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=10, b=10), yaxis_title=None)
    fig.update_xaxes(tickprefix="£", gridcolor="#e5e7eb")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(prod.assign(Sales=prod["Sales"].round(0)), hide_index=True, width="stretch")

# ---------------- Countries ----------------
with right:
    st.subheader("Top countries by sales")
    skip_uk = st.checkbox("Hide United Kingdom (so others are visible)", value=False)
    cc = by_country[by_country["Country"] != "United Kingdom"] if skip_uk else by_country
    top = cc.head(10)
    fig = px.bar(top.iloc[::-1], x="Sales", y="Country", orientation="h",
                 color_discrete_sequence=[BLUE], labels={"Sales": "Sales (£)"})
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=10, b=10), yaxis_title=None)
    fig.update_xaxes(tickprefix="£", gridcolor="#e5e7eb")
    st.plotly_chart(fig, width="stretch")
    if len(by_country) and by_country["Sales"].sum() > 0:
        share = by_country.iloc[0]["Sales"] / by_country["Sales"].sum()
        st.caption(f"{by_country.iloc[0]['Country']} accounts for {share:.0%} of sales in the current view.")

with st.expander("Data notes"):
    st.markdown(
        "- **Clean data** (default) drops cancellations, returns and zero-price rows. "
        "Untick it to see the raw dataset where returns reduce total sales.\n"
        "- Some stock codes are postage/fees, not products (e.g. DOTCOM POSTAGE). "
        "They are excluded from the product ranking by default.\n"
        "- ~25% of rows have no CustomerID; they are still counted in sales and orders.")
