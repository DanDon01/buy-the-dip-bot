import streamlit as st
st.set_page_config(page_title="Buy-the-Dip Dashboard", layout="wide", page_icon="💹")

import pandas as pd
import glob
import os
import json
import ast
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

"""Streamlit dashboard for Buy-the-Dip Bot outputs.

Place this file in the project root and launch with:

    streamlit run dashboard.py

The app auto-detects the most recent `output/scan_*.csv` file, then
builds an interactive dashboard with filters, charts and a detailed
score-breakdown table.
"""

OUTPUT_DIR = "output"
CSV_PATTERN = "scan_*.csv"

# --------------------------- data loader -----------------------------------

def load_latest_csv():
    """Return (df, path) for the newest scan CSV in *OUTPUT_DIR* or (None, None)."""
    csv_files = glob.glob(os.path.join(OUTPUT_DIR, CSV_PATTERN))
    if not csv_files:
        return None, None
    latest_path = max(csv_files, key=os.path.getmtime)
    try:
        df = pd.read_csv(latest_path)
        return df, latest_path
    except Exception as e:
        st.error(f"Failed to read CSV `{latest_path}`: {e}")
        return None, latest_path

# --------------------------- helpers ---------------------------------------

def unpack_score_details(df: pd.DataFrame) -> pd.DataFrame:
    """Expand the *score_details* JSON column into flat numeric columns."""
    if "score_details" not in df.columns:
        return df

    def _try_parse(x):
        if pd.isna(x):
            return {}
        if isinstance(x, dict):
            return x
        try:
            return json.loads(x)
        except Exception:
            try:
                return ast.literal_eval(x)
            except Exception:
                return {}

    details_series = df["score_details"].apply(_try_parse)
    metrics = {}
    for item in details_series:
        for k, v in item.items():
            pts = v.get("points", 0)
            metrics.setdefault(k, []).append(pts)
    for k, vals in metrics.items():
        if len(vals) < len(df):
            # pad if some rows missing
            vals += [0] * (len(df) - len(vals))
        df[k + "_pts"] = vals
    return df

# ----------------------------- main ----------------------------------------

df, csv_path = load_latest_csv()
if df is None:
    st.warning("No scan CSV found in the `output/` directory. Run the bot with `--score` first.")
    st.stop()

# Basic clean-up
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# Add 52-week % drop column if missing
if "%_below_high" not in df.columns and {"price", "year_high"}.issubset(df.columns):
    df["%_below_high"] = ((df["year_high"] - df["price"]) / df["year_high"]) * 100

# Unpack score_details for table view
_df = unpack_score_details(df.copy())

# --------------------------- HEADER / METRICS ------------------------------

last_update = _df["timestamp"].max() if "timestamp" in _df.columns else None
avg_score = _df["score"].mean()
max_idx = _df["score"].idxmax()
min_idx = _df["score"].idxmin()

top_ticker, top_score = _df.loc[max_idx, ["ticker", "score"]]
bottom_ticker, bottom_score = _df.loc[min_idx, ["ticker", "score"]]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Last Update", last_update.strftime("%Y-%m-%d %H:%M") if last_update is not None else "—")
col2.metric("Average Score", f"{avg_score:.1f}")
col3.metric("Highest", f"{top_ticker} : {top_score}")
col4.metric("Lowest", f"{bottom_ticker} : {bottom_score}")

st.markdown("---")

# ------------------------------ SIDEBAR ------------------------------------

st.sidebar.header("Filters")

# Ticker search
search_ticker = st.sidebar.text_input("Ticker search (partial ok)")

# Score range slider
min_score, max_score = int(_df["score"].min()), int(_df["score"].max())
score_range = st.sidebar.slider("Score range", min_score, max_score, (min_score, max_score))

# TODO: Sector filter when sector column available

# Apply filters
filtered = _df.copy()
if search_ticker:
    filtered = filtered[filtered["ticker"].str.contains(search_ticker.upper(), na=False)]

filtered = filtered[(filtered["score"] >= score_range[0]) & (filtered["score"] <= score_range[1])]

st.caption(f"Showing {len(filtered)}/{len(_df)} tickers after filters")

# ------------------------------ MAIN TABS ----------------------------------

tab1, tab2, tab3 = st.tabs(["Score Performance", "Market Cap vs Score", "Breakdown Table"])

# --- Tab 1
with tab1:
    st.subheader("Score Distribution")
    st.bar_chart(filtered.set_index("ticker")["score"])

# --- Tab 2
with tab2:
    if {"market_cap", "score"}.issubset(filtered.columns):
        st.subheader("Market Cap vs Score")
        st.scatter_chart(filtered, x="score", y="market_cap", size="market_cap", color="score")
    else:
        st.info("Market-cap data not available in this CSV.")

# --- Tab 3
with tab3:
    st.subheader("Score Breakdown")
    st.dataframe(filtered.sort_values("score", ascending=False))

# ------------------------------ FOOTER -------------------------------------

st.markdown("---")
st.caption("Data source: Buy-the-Dip Bot | File: " + os.path.basename(csv_path)) 