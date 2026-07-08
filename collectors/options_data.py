"""
Options chain collector.

Pulls the option chain for a ticker (via yfinance) and derives dip-relevant
signals:

* Put/Call volume and open-interest ratios (elevated puts near a bottom is a
  classic capitulation/contrarian signal).
* ATM implied volatility for calls and puts.
* IV skew (OTM put IV vs OTM call IV) - fear gauge.
* Max pain strike for the nearest expiration.

Results are cached in cache/options_data.json (TTL 6h).

CLI:  python cli.py --options --ticker AAPL
API:  GET /api/stock/<ticker>/options
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

CACHE_FILE = os.path.join("cache", "options_data.json")
CACHE_TTL_HOURS = 6


def analyze_chain(calls: pd.DataFrame, puts: pd.DataFrame,
                  spot_price: float, expiration: str = "") -> Dict:
    """Pure analysis over a fetched option chain (offline-testable).

    Expects yfinance-style columns: strike, volume, openInterest,
    impliedVolatility.
    """
    result: Dict = {
        "expiration": expiration,
        "spot_price": round(spot_price, 2) if spot_price else None,
    }

    call_vol = float(calls["volume"].fillna(0).sum()) if len(calls) else 0.0
    put_vol = float(puts["volume"].fillna(0).sum()) if len(puts) else 0.0
    call_oi = float(calls["openInterest"].fillna(0).sum()) if len(calls) else 0.0
    put_oi = float(puts["openInterest"].fillna(0).sum()) if len(puts) else 0.0

    result["call_volume"] = int(call_vol)
    result["put_volume"] = int(put_vol)
    result["put_call_volume_ratio"] = round(put_vol / call_vol, 3) if call_vol > 0 else None
    result["put_call_oi_ratio"] = round(put_oi / call_oi, 3) if call_oi > 0 else None

    # --- ATM implied volatility ---
    def _atm_iv(df: pd.DataFrame) -> Optional[float]:
        if df.empty or not spot_price:
            return None
        idx = (df["strike"] - spot_price).abs().idxmin()
        iv = df.loc[idx, "impliedVolatility"]
        return round(float(iv), 4) if pd.notna(iv) else None

    result["atm_call_iv"] = _atm_iv(calls)
    result["atm_put_iv"] = _atm_iv(puts)

    # --- IV skew: ~10% OTM put IV minus ~10% OTM call IV ---
    skew = None
    if spot_price and len(calls) and len(puts):
        otm_puts = puts[puts["strike"] <= spot_price * 0.92]
        otm_calls = calls[calls["strike"] >= spot_price * 1.08]
        if len(otm_puts) and len(otm_calls):
            put_iv = otm_puts.iloc[(otm_puts["strike"] - spot_price * 0.9).abs().argsort().iloc[0]]["impliedVolatility"]
            call_iv = otm_calls.iloc[(otm_calls["strike"] - spot_price * 1.1).abs().argsort().iloc[0]]["impliedVolatility"]
            if pd.notna(put_iv) and pd.notna(call_iv):
                skew = round(float(put_iv) - float(call_iv), 4)
    result["iv_skew"] = skew

    # --- Max pain: strike minimizing total intrinsic value paid out ---
    result["max_pain_strike"] = _max_pain(calls, puts)

    # --- Interpretation for the dashboard ---
    result["signals"] = _interpret(result)
    return result


def _max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> Optional[float]:
    if calls.empty and puts.empty:
        return None
    strikes = sorted(set(calls["strike"].tolist()) | set(puts["strike"].tolist()))
    if not strikes:
        return None
    best_strike, best_pain = None, None
    call_oi = calls.set_index("strike")["openInterest"].fillna(0) if len(calls) else pd.Series(dtype=float)
    put_oi = puts.set_index("strike")["openInterest"].fillna(0) if len(puts) else pd.Series(dtype=float)
    for s in strikes:
        call_pain = sum(oi * max(0.0, s - k) for k, oi in call_oi.items())
        put_pain = sum(oi * max(0.0, k - s) for k, oi in put_oi.items())
        pain = call_pain + put_pain
        if best_pain is None or pain < best_pain:
            best_pain, best_strike = pain, s
    return float(best_strike) if best_strike is not None else None


def _interpret(result: Dict) -> Dict:
    """Translate raw metrics into human-readable dip signals."""
    signals = {}
    pcr = result.get("put_call_volume_ratio")
    if pcr is not None:
        if pcr >= 1.5:
            signals["put_call"] = "extreme_fear (contrarian bullish)"
        elif pcr >= 1.0:
            signals["put_call"] = "elevated_puts (fear building)"
        elif pcr <= 0.5:
            signals["put_call"] = "call_heavy (complacent/bullish)"
        else:
            signals["put_call"] = "balanced"

    skew = result.get("iv_skew")
    if skew is not None:
        if skew >= 0.10:
            signals["skew"] = "steep_put_skew (downside hedging demand)"
        elif skew <= -0.02:
            signals["skew"] = "call_skew (upside speculation)"
        else:
            signals["skew"] = "normal"

    spot = result.get("spot_price")
    max_pain = result.get("max_pain_strike")
    if spot and max_pain:
        diff_pct = (max_pain - spot) / spot * 100
        if diff_pct >= 5:
            signals["max_pain"] = f"max pain {diff_pct:+.1f}% above spot (pull-up bias)"
        elif diff_pct <= -5:
            signals["max_pain"] = f"max pain {diff_pct:+.1f}% below spot (pull-down bias)"
        else:
            signals["max_pain"] = "max pain near spot"
    return signals


class OptionsDataCollector:
    """Fetches and analyzes option chains with caching."""

    def get_options_summary(self, ticker: str, use_cache: bool = True) -> Dict:
        ticker = ticker.upper()
        cache = _load_cache()
        if use_cache and ticker in cache:
            entry = cache[ticker]
            try:
                if datetime.now() - datetime.fromisoformat(entry["fetched"]) \
                        <= timedelta(hours=CACHE_TTL_HOURS):
                    return entry["data"]
            except (KeyError, ValueError):
                pass

        summary = self._fetch_and_analyze(ticker)
        if summary is None:
            if ticker in cache:
                return cache[ticker]["data"]
            return {"ticker": ticker, "available": False,
                    "error": "options data unavailable"}

        cache[ticker] = {"fetched": datetime.now().isoformat(), "data": summary}
        _save_cache(cache)
        return summary

    def _fetch_and_analyze(self, ticker: str) -> Optional[Dict]:
        from market_data import get_option_expirations, get_option_chain, get_history
        expirations = get_option_expirations(ticker)
        if not expirations:
            return None
        # Nearest expiration at least a week out gives cleaner signals
        target = expirations[0]
        for exp in expirations:
            try:
                if (datetime.strptime(exp, "%Y-%m-%d").date()
                        - datetime.now().date()).days >= 7:
                    target = exp
                    break
            except ValueError:
                continue

        calls, puts = get_option_chain(ticker, target)
        if calls is None or puts is None:
            return None

        spot = None
        hist = get_history(ticker, period="5d")
        if hist is not None and len(hist):
            spot = float(hist["Close"].iloc[-1])

        summary = analyze_chain(calls, puts, spot or 0.0, target)
        summary["ticker"] = ticker
        summary["available"] = True
        summary["all_expirations"] = expirations[:8]
        return summary


def _load_cache() -> Dict:
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: Dict):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
