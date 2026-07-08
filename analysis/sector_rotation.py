"""
Sector rotation analysis.

Ranks the 11 GICS sector ETFs by relative strength vs SPY over multiple
horizons (1m / 3m / 6m) and classifies each sector's rotation phase:

* leading        - outperforming on both 3m and 1m horizons
* improving      - underperformed over 3m but outperforming over 1m
* weakening      - outperformed over 3m but lagging over 1m
* lagging        - underperforming on both horizons

Results are cached in cache/sector_rotation.json (TTL 24h by default) so the
scoring loop can consume sector context without any extra API calls.

CLI:  python cli.py --sectors
API:  GET /api/sectors
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

SECTOR_ETFS: Dict[str, str] = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLC": "Communication Services",
}

# Map Yahoo `sector` strings (as stored in stock records) to the ETF proxies
SECTOR_NAME_TO_ETF: Dict[str, str] = {
    "technology": "XLK",
    "financial services": "XLF",
    "financial": "XLF",
    "healthcare": "XLV",
    "health care": "XLV",
    "consumer cyclical": "XLY",
    "consumer discretionary": "XLY",
    "consumer defensive": "XLP",
    "consumer staples": "XLP",
    "energy": "XLE",
    "industrials": "XLI",
    "basic materials": "XLB",
    "materials": "XLB",
    "real estate": "XLRE",
    "utilities": "XLU",
    "communication services": "XLC",
}

CACHE_FILE = os.path.join("cache", "sector_rotation.json")
CACHE_TTL_HOURS = 24


def _pct_return(close: pd.Series, days: int) -> Optional[float]:
    if len(close) <= days:
        return None
    start = close.iloc[-(days + 1)]
    if not start or start <= 0:
        return None
    return float(close.iloc[-1] / start - 1)


def compute_sector_rotation(price_data: Dict[str, pd.DataFrame],
                            benchmark: pd.DataFrame) -> Dict:
    """Pure computation over pre-fetched ETF price frames (testable offline).

    Args:
        price_data: {etf_symbol: OHLCV frame}
        benchmark:  SPY OHLCV frame
    """
    bench_close = benchmark["Close"]
    bench = {h: _pct_return(bench_close, d)
             for h, d in (("1m", 21), ("3m", 63), ("6m", 126))}

    sectors: List[Dict] = []
    for etf, name in SECTOR_ETFS.items():
        df = price_data.get(etf)
        if df is None or df.empty:
            continue
        close = df["Close"]
        rets = {h: _pct_return(close, d)
                for h, d in (("1m", 21), ("3m", 63), ("6m", 126))}
        rs = {h: (rets[h] - bench[h]) if rets[h] is not None and bench[h] is not None else None
              for h in rets}

        rs1, rs3 = rs.get("1m"), rs.get("3m")
        if rs1 is None or rs3 is None:
            phase = "unknown"
        elif rs1 >= 0 and rs3 >= 0:
            phase = "leading"
        elif rs1 >= 0 > rs3:
            phase = "improving"
        elif rs1 < 0 <= rs3:
            phase = "weakening"
        else:
            phase = "lagging"

        sectors.append({
            "etf": etf,
            "sector": name,
            "return_1m_pct": round(rets["1m"] * 100, 2) if rets["1m"] is not None else None,
            "return_3m_pct": round(rets["3m"] * 100, 2) if rets["3m"] is not None else None,
            "return_6m_pct": round(rets["6m"] * 100, 2) if rets["6m"] is not None else None,
            "rel_strength_1m_pct": round(rs1 * 100, 2) if rs1 is not None else None,
            "rel_strength_3m_pct": round(rs3 * 100, 2) if rs3 is not None else None,
            "phase": phase,
        })

    # Momentum rank: blend of 1m and 3m relative strength
    def _rank_key(s):
        a = s["rel_strength_1m_pct"] or 0
        b = s["rel_strength_3m_pct"] or 0
        return 0.6 * a + 0.4 * b

    sectors.sort(key=_rank_key, reverse=True)
    for i, s in enumerate(sectors, 1):
        s["momentum_rank"] = i

    return {
        "generated": datetime.now().isoformat(),
        "benchmark": {
            "symbol": "SPY",
            "return_1m_pct": round(bench["1m"] * 100, 2) if bench["1m"] is not None else None,
            "return_3m_pct": round(bench["3m"] * 100, 2) if bench["3m"] is not None else None,
            "return_6m_pct": round(bench["6m"] * 100, 2) if bench["6m"] is not None else None,
        },
        "sectors": sectors,
    }


def refresh_sector_rotation(period: str = "1y") -> Optional[Dict]:
    """Fetch ETF data and rebuild the sector rotation cache."""
    from market_data import download_history, get_history

    symbols = list(SECTOR_ETFS.keys())
    price_data = download_history(symbols, period=period)
    benchmark = get_history("SPY", period=period)
    if not price_data or benchmark is None:
        print("⚠️  Could not fetch sector ETF data.")
        return None

    result = compute_sector_rotation(price_data, benchmark)
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(result, f, indent=2)
    return result


def load_sector_rotation(max_age_hours: float = CACHE_TTL_HOURS,
                         refresh_if_stale: bool = False) -> Optional[Dict]:
    """Load cached sector rotation data; optionally refresh when stale."""
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        generated = datetime.fromisoformat(data["generated"])
        if datetime.now() - generated <= timedelta(hours=max_age_hours):
            return data
        if refresh_if_stale:
            return refresh_sector_rotation() or data
        return data   # stale but better than nothing
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        return refresh_sector_rotation() if refresh_if_stale else None


def sector_adjustment_for(sector_name: str, max_points: float = 4.0) -> float:
    """Risk-modifier adjustment (± max_points) for a stock's sector.

    Reads only the local cache - never triggers API calls from the scoring
    loop. Returns 0 when no data is available.
    """
    if not sector_name:
        return 0.0
    etf = SECTOR_NAME_TO_ETF.get(sector_name.strip().lower())
    if not etf:
        return 0.0
    data = load_sector_rotation(max_age_hours=72)   # tolerate a few days old
    if not data:
        return 0.0
    for s in data.get("sectors", []):
        if s["etf"] == etf:
            phase = s.get("phase")
            if phase == "leading":
                return max_points
            if phase == "improving":
                return max_points * 0.5
            if phase == "weakening":
                return -max_points * 0.5
            if phase == "lagging":
                return -max_points
            return 0.0
    return 0.0
