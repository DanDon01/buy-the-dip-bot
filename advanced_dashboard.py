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

# --------------------------- Constants & Tooltips ---------------------------

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

# --------------------------- Main Page Layout ---------------------------

st.title("📉 Buy-The-Dip Stock Screener v1.2")

# --- Summary Metrics ---
scan_date = df.timestamp.max().strftime("%b %d, %Y %H:%M") if "timestamp" in df.columns else "N/A"
top_3_str = ", ".join(df.sort_values("score", ascending=False).head(3).ticker)

c1, c2, c3 = st.columns(3)
with c1: st.metric("📅 Last Scan", scan_date)
with c2: st.metric("📊 Average Score", f"{df.score.mean():.1f}")
with c3: st.metric("🏆 Top 3 Tickers", top_3_str)
st.markdown("---")

# --- AgGrid Table & Detail Panel ---
main_col, detail_col = st.columns([2, 1])

with main_col:
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    gb.configure_default_column(resizable=True, filter=True, sortable=True, minWidth=80)
    
    # Add tooltips and styling
    for col, tip in TOOLTIPS.items():
        if col in filtered_df.columns:
            gb.configure_column(col, headerTooltip=tip)
            
    gb.configure_column("score", cellStyle=JsCode("params => params.value >= 70 ? {color: '#4CAF50', fontWeight: 'bold'} : params.value <= 40 ? {color: '#F44336'} : {color: 'white'}"))
    gb.configure_column("%_below_high", cellStyle=JsCode("params => params.value >= 15 ? {backgroundColor: 'rgba(76, 175, 80, 0.2)'} : null"))
    
    # Hide raw data and score component columns to keep the grid clean
    score_component_cols = [
        "price_drop", "rsi5", "volume_spike", "below_sma200", "below_sma50",
        "macd_bull_cross", "pe", "div_yield", "beta", "short_float"
    ]
    cols_to_hide = [c for c in score_component_cols if c in filtered_df.columns]
    cols_to_hide.extend(['timestamp', 'year_high', 'year_low'])
    gb.configure_columns(cols_to_hide, hide=True)
    
    # Updated selection configuration to address deprecation warnings
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    grid_options = gb.build()

    # Remove excess empty space by auto-adjusting grid height
    grid_options["domLayout"] = "autoHeight"

    # Define custom CSS for a robust dark theme
    custom_css = {
        ".ag-theme-alpine-dark": {
            "--ag-background-color": "#16191f",
            "--ag-header-background-color": "#262730",
            "--ag-odd-row-background-color": "#1f2229",
            "--ag-row-hover-color": "#4a5464",
            "--ag-font-family": "sans-serif",
            "--ag-font-size": "16px",
            "--ag-foreground-color": "#e0e0e0",
            "--ag-header-foreground-color": "#fafafa",
            "--ag-border-color": "#303338",
            "--ag-selected-row-background-color": "#4a5464 !important"
        },
        ".ag-theme-alpine-dark .ag-center-cols-viewport": {
            "background-color": "#16191f !important"
        },
        ".ag-theme-alpine-dark .ag-body-viewport": {
            "background-color": "#16191f !important"
        },
        ".ag-theme-alpine-dark .ag-body": {
            "background-color": "#16191f !important"
        }
    }

    grid_response = AgGrid(
        filtered_df,
        gridOptions=grid_options,
        height=600,
        width='100%',
        theme="alpine-dark",
        custom_css=custom_css, # Apply the robust custom theme
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True, # Fit columns to screen
    )
    selected_rows = grid_response['selected_rows']

with detail_col:
    st.subheader("🔍 Ticker Detail")
    if selected_rows is not None and not selected_rows.empty:
        row = selected_rows.iloc[0]
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
            if points != 0: # Only display score components that have a value
                target_col = col1 if i % 2 == 0 else col2
                target_col.metric(metric, f"{points:g}")
                i += 1
            
        st.markdown("---")
        st.markdown("##### Raw Data")
        st.json(row.dropna().to_dict(), expanded=False)

    else:
        st.info("Click a row in the table to see detailed info here.")

# --- Footer ---
st.caption(f"Data from `{csv_filename}` | Dashboard updated: {datetime.now():%Y-%m-%d %H:%M}")

# --- Custom Styling ---
st.markdown("""
<style>
    /* General font size increase for better readability */
    html, body, [class*="st-"], .ag-theme-alpine-dark {
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
    .st-ag-grid {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True) 