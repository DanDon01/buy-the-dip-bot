# -*- coding: utf-8 -*-
"""
Advanced Streamlit dashboard for Buy-The-Dip Bot
------------------------------------------------
Run: streamlit run advanced_dashboard.py
Requires: streamlit, streamlit-aggrid
"""

import streamlit as st
st.set_page_config(
    page_title="Buy-The-Dip Screener", page_icon="📉", layout="wide", initial_sidebar_state="expanded"
)

import pandas as pd
import glob
import os
import json
import ast
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

# --------------------------- Constants & Theme ---------------------------

OUTPUT_DIR, PATTERN = "output", "scan_*.csv"

TOOLTIPS = {
    "score": "Overall dip score. Higher is generally better.",
    "price_drop": "Points for % drop from 5-day high. More drop = more points.",
    "rsi5": "Points for a low RSI(5) value. Below 30 is typically considered oversold.",
    "volume_spike": "Points for a significant volume increase vs the 20-day average, indicating potential capitulation.",
    "below_sma200": "Points if price is below the 200-day Simple Moving Average (long-term downtrend).",
    "below_sma50": "Points if price is below the 50-day Simple Moving Average (medium-term downtrend).",
    "macd_bull_cross": "Points for a recent bullish MACD crossover signal.",
    "pe": "Points for a low Price-to-Earnings ratio (value indicator).",
    "div_yield": "Bonus points for a high dividend yield.",
    "beta": "Penalty for high volatility (Beta > 2).",
    "short_float": "Penalty for very high short interest as a % of float.",
    "%_below_high": "Percentage the current price is below the 52-week high."
}

def inject_dark_aggrid_styles():
    """Force dark theme on AG-Grid components."""
    st.markdown("""
        <style>
        .ag-theme-alpine-dark .ag-header,
        .ag-theme-alpine-dark .ag-header-cell,
        .ag-theme-alpine-dark .ag-cell,
        .ag-theme-alpine-dark .ag-row,
        .ag-theme-alpine-dark .ag-row-even,
        .ag-theme-alpine-dark .ag-row-odd {
            background-color: #1e1e1e !important;
            color: #f5f5f5 !important;
        }
        .ag-theme-alpine-dark .ag-root-wrapper {
            border: 1px solid #444;
        }
        /* Selected row highlight */
        .ag-theme-alpine-dark .ag-row-selected {
            background-color: #2d3748 !important;
        }
        /* Hover state */
        .ag-theme-alpine-dark .ag-row:hover {
            background-color: #2d3748 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --------------------------- Data Loading & Processing ---------------------------

@st.cache_data(show_spinner="Loading latest scan data...")
def load_and_process_scan():
    """Finds the latest scan CSV, loads it, and processes it into a clean DataFrame."""
    csv_files = glob.glob(os.path.join(OUTPUT_DIR, PATTERN))
    if not csv_files:
        return None, None
    
    latest_csv_path = max(csv_files, key=os.path.getmtime)
    df = pd.read_csv(latest_csv_path)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    def _parse_details(x):
        if pd.isna(x) or isinstance(x, (int, float)): return {}
        try: return json.loads(x)
        except (json.JSONDecodeError, TypeError):
            try: return ast.literal_eval(x)
            except (ValueError, SyntaxError): return {}

    if "score_details" in df.columns:
        details_series = df.pop("score_details").apply(_parse_details)
        extra_cols = pd.json_normalize(details_series)
        df = pd.concat([df, extra_cols], axis=1)

    if "%_below_high" not in df.columns and {"price", "year_high"}.issubset(df.columns):
        df["%_below_high"] = ((df["year_high"] - df["price"]) / df["year_high"] * 100)

    for col in df.select_dtypes("number").columns:
        df[col] = df[col].round(2)

    return df, os.path.basename(latest_csv_path)

df, csv_filename = load_and_process_scan()

if df is None:
    st.error(f"No scan CSVs found in `{OUTPUT_DIR}/`. Please run the bot's `--score` command first.")
    st.stop()

# --------------------------- Main Layout ---------------------------

# Force dark theme on all grids
inject_dark_aggrid_styles()

st.title("📉 Buy-The-Dip Stock Screener v1.3")

# --- Summary Metrics ---
scan_date = df.timestamp.max().strftime("%b %d, %Y %H:%M") if "timestamp" in df.columns else "N/A"
top_3_str = ", ".join(df.sort_values("score", ascending=False).head(3).ticker)

c1, c2, c3 = st.columns(3)
with c1: st.metric("📅 Last Scan", scan_date)
with c2: st.metric("📊 Average Score", f"{df.score.mean():.1f}")
with c3: st.metric("🏆 Top 3 Tickers", top_3_str)
st.markdown("---")

# --------------------------- Sidebar Filters ---------------------------

st.sidebar.header("Screener Filters")
min_s, max_s = int(df.score.min()), int(df.score.max())
if min_s < max_s:
    score_range = st.sidebar.slider("Score range", min_s, max_s, (min_s, max_s))
else:
    st.sidebar.info(f"All tickers have the same score: {min_s}")
    score_range = (min_s, max_s)

query = st.sidebar.text_input("Ticker search")
rows_choice = st.sidebar.radio("Show top", [50, 100, "All"], index=1, horizontal=True)

# Apply filters
filtered_df = df[df.score.between(*score_range)]
if query:
    filtered_df = filtered_df[filtered_df.ticker.str.contains(query.upper(), na=False)]
if rows_choice != "All":
    filtered_df = filtered_df.head(int(rows_choice))

# --------------------------- Main Grid & Detail Panel ---------------------------
main_col, detail_col = st.columns([2, 1])

with main_col:
    # Explicit dark styling per column
    dark_cell_style = {'backgroundColor': '#1e1e1e', 'color': '#f5f5f5'}

    grid_options = {
        "defaultColDef": {
            "resizable": True,
            "sortable": True,
            "filter": True,
        },
        "columnDefs": [
            {
                "headerName": "Ticker",
                "field": "ticker",
                "cellStyle": dark_cell_style
            },
            {
                "headerName": "Price",
                "field": "price",
                "type": "numericColumn",
                "cellStyle": dark_cell_style
            },
            {
                "headerName": "Score",
                "field": "score",
                "type": "numericColumn",
                "cellStyle": dark_cell_style
            },
            {
                "headerName": "% Below High",
                "field": "%_below_high",
                "type": "numericColumn",
                "cellStyle": dark_cell_style
            },
        ],
        "rowStyle": dark_cell_style,
        "rowSelection": "single"
    }

    grid_response = AgGrid(
        filtered_df,
        gridOptions=grid_options,
        theme="alpine-dark",  # still required for outer wrappers
        height=600,
        use_container_width=True,  # replaces fit_columns
        enable_enterprise_modules=False,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
    )
    selected_rows = grid_response['selected_rows']


with detail_col:
    st.subheader("🔍 Ticker Detail")
    if selected_rows:
        row = pd.Series(selected_rows[0])
        st.metric(f"**{row['ticker']}**", f"${row['price']:.2f}", f"{row.get('%_below_high', 0):.1f}% below 52W high")
        
        st.markdown("---")
        st.markdown("##### Score Breakdown")

        score_data = {}
        score_component_cols = [
            "price_drop", "rsi5", "volume_spike", "below_sma200", "below_sma50",
            "macd_bull_cross", "pe", "div_yield", "beta", "short_float"
        ]
        for col in score_component_cols:
            if col in row and pd.notna(row[col]):
                score_data[col.replace('_', ' ').title()] = row[col]

        # Use columns for a cleaner breakdown layout
        col1, col2 = st.columns(2)
        i = 0
        for metric, points in score_data.items():
            if points != 0:  # Only display non-zero scores
                target_col = col1 if i % 2 == 0 else col2
                target_col.metric(metric, f"{points:g}")
                i += 1
            
        st.markdown("---")
        st.markdown("##### Raw Data")
        
        # Display raw data in a grid
        raw_df = pd.DataFrame(row.dropna()).reset_index()
        raw_df.columns = ["Field", "Value"]
        
        raw_gb = GridOptionsBuilder.from_dataframe(raw_df)
        raw_gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)
        raw_grid_opts = raw_gb.build()
        
        AgGrid(
            raw_df,
            gridOptions=raw_grid_opts,
            theme="alpine-dark",
            height=300,
            fit_columns_on_grid_load=True,
            enable_enterprise_modules=False,
        )
    else:
        st.info("Click a row in the table to see detailed info here.")

# --- Footer ---
st.caption(f"Data from `{csv_filename}` | Dashboard updated: {datetime.now():%Y-%m-%d %H:%M}")

# --- Custom Styling ---
st.markdown("""
<style>
    /* General font size increase for better readability */
    html, body, [class*="st-"] {
        font-size: 16px;
    }
    /* Tighter, cleaner metric cards */
    [data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #303338;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True) 