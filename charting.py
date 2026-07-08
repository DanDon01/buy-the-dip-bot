"""
Advanced charting data builder.

Produces chart-ready series (price + technical overlays) for the frontend's
AdvancedChart component:

* OHLC / close price and volume
* SMA 20 / 50 / 200
* Bollinger Bands (20, 2σ)
* RSI(14) sub-panel
* MACD (12/26/9) sub-panel

Data source: fresh Yahoo history when reachable (up to 1y), falling back to
the cached ``historical_data`` stored in cache/stock_data.json.

API: GET /api/stock/<ticker>/chart?period=6mo
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y"}


def build_chart_payload(df: pd.DataFrame, ticker: str) -> Dict:
    """Compute all indicator series from an OHLCV DataFrame (offline-testable)."""
    close = df["Close"]
    high = df.get("High", close)
    low = df.get("Low", close)
    volume = df.get("Volume", pd.Series(0, index=df.index))

    out: Dict[str, List] = {}
    dates = [d.strftime("%Y-%m-%d") for d in pd.to_datetime(df.index)]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal

    def _clean(series) -> List[Optional[float]]:
        return [round(float(v), 4) if pd.notna(v) and np.isfinite(v) else None
                for v in series]

    points = []
    close_l, high_l, low_l = _clean(close), _clean(high), _clean(low)
    vol_l = [int(v) if pd.notna(v) else None for v in volume]
    sma20_l, sma50_l, sma200_l = _clean(sma20), _clean(sma50), _clean(sma200)
    bbu_l, bbl_l = _clean(bb_upper), _clean(bb_lower)
    rsi_l = _clean(rsi)
    macd_l, sig_l, hist_l = _clean(macd), _clean(macd_signal), _clean(macd_hist)

    for i, date in enumerate(dates):
        points.append({
            "date": date,
            "close": close_l[i],
            "high": high_l[i],
            "low": low_l[i],
            "volume": vol_l[i],
            "sma20": sma20_l[i],
            "sma50": sma50_l[i],
            "sma200": sma200_l[i],
            "bbUpper": bbu_l[i],
            "bbLower": bbl_l[i],
            "rsi": rsi_l[i],
            "macd": macd_l[i],
            "macdSignal": sig_l[i],
            "macdHist": hist_l[i],
        })

    last_close = close_l[-1] if close_l else None
    year_high = max((v for v in high_l if v is not None), default=None)
    return {
        "ticker": ticker.upper(),
        "points": points,
        "meta": {
            "bars": len(points),
            "last_close": last_close,
            "period_high": year_high,
            "drop_from_period_high_pct": round((1 - last_close / year_high) * 100, 2)
            if last_close and year_high else None,
        },
    }


def get_chart_data(ticker: str, period: str = "6mo") -> Optional[Dict]:
    """Fetch history (live, falling back to cache) and build the payload."""
    ticker = ticker.upper()
    if period not in VALID_PERIODS:
        period = "6mo"

    df = None
    try:
        from market_data import get_history
        df = get_history(ticker, period=period)
    except Exception:
        df = None

    if df is None or df.empty:
        df = _history_from_cache(ticker)

    if df is None or df.empty:
        return None
    return build_chart_payload(df, ticker)


def _history_from_cache(ticker: str) -> Optional[pd.DataFrame]:
    try:
        with open(os.path.join("cache", "stock_data.json")) as f:
            rec = json.load(f).get(ticker) or {}
        hist = rec.get("historical_data")
        if not hist or not hist.get("close"):
            return None
        return pd.DataFrame(
            {
                "Close": hist["close"],
                "High": hist.get("high", hist["close"]),
                "Low": hist.get("low", hist["close"]),
                "Volume": hist.get("volume", [0] * len(hist["close"])),
            },
            index=pd.to_datetime(hist["dates"]),
        )
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        return None
