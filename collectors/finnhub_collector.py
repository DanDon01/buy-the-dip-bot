"""finnhub_collector.py
Light-weight wrapper around the official ``finnhub-python`` client that we use
for *bulk* fundamental/price data download. It enforces the global
rate-limit rules requested by the user (≥0.5 s between calls, ≤120 calls/min)
while providing the minimal interface required by ``DataCollector``.

Secrets
-------

The Finnhub API key is **never** hard-coded.  Set it via the environment
variable ``FINNHUB_API_KEY`` or pass it explicitly to the constructor.  See
``.env.example`` for a template.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List

import pandas as pd

try:
    import finnhub  # type: ignore
except ImportError as exc:  # pragma: no cover – handled at runtime
    raise ImportError(
        "Missing dependency: 'finnhub-python'. Add it to requirements.txt and pip install."
    ) from exc

# ---------------------------------------------------------------------------
# Global rate-limit settings (per user requirements)
# ---------------------------------------------------------------------------
# Free-tier Finnhub limits: 60 req/min.  Give ourselves some headroom.
MIN_DELAY_SECONDS = 1.1   # ≥1 s between calls keeps well below 60/min
MAX_CALLS_PER_MIN = 55    # rolling-window upper-bound


# Custom exception used to signal a hard rate-limit (HTTP 429)
class RateLimitError(RuntimeError):
    pass


class FinnhubCollector:
    """Tiny façade over the finnhub SDK providing throttled helper methods."""

    def __init__(self, api_key: str | None = None, min_delay: float = MIN_DELAY_SECONDS):
        self.api_key: str | None = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Finnhub API key not found. Set FINNHUB_API_KEY env var or inject via constructor."
            )

        self._client = finnhub.Client(api_key=self.api_key)
        self._min_delay = max(min_delay, MIN_DELAY_SECONDS)
        self._last_call_ts = 0.0
        self._rolling_window: List[float] = []  # stores epoch seconds of recent calls (≤60 s)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _throttle(self) -> None:
        """Apply both fixed delay and rolling-window throttling."""
        now = time.time()

        # 1) Fixed delay between consecutive calls
        elapsed = now - self._last_call_ts
        if elapsed < self._min_delay:
            time.sleep(self._min_delay - elapsed)

        # 2) Rolling 60-second window (max 120 calls)
        self._rolling_window = [t for t in self._rolling_window if now - t < 60]
        if len(self._rolling_window) >= MAX_CALLS_PER_MIN:
            wait_time = 60 - (now - self._rolling_window[0]) + 0.01
            time.sleep(max(wait_time, self._min_delay))
            now = time.time()
            self._rolling_window = [t for t in self._rolling_window if now - t < 60]

        # Record call timestamp
        self._rolling_window.append(now)
        self._last_call_ts = now

    # ------------------------------------------------------------------
    # Public API – kept minimal for current integration needs
    # ------------------------------------------------------------------
    def get_stock_snapshot(self, symbol: str) -> Dict[str, Any] | None:
        """Return live quote + basic company info.

        *None* is returned if any mandatory field is missing so the caller can
        treat the ticker as unsupported – mirroring current yahoo flow.
        """
        self._throttle()
        try:
            # --- 1) Quote (price, volume) ---
            quote = self._client.quote(symbol)
            profile = self._client.company_profile2(symbol=symbol)

            # --- 2) 52-week high/low via /stock/metric (price group) ---
            hi_52w = lo_52w = None
            try:
                if hasattr(self._client, "stock_metric"):
                    self._throttle()
                    m_price = self._client.stock_metric(symbol, metric="price")
                    m_dict = m_price.get("metric", {}) if isinstance(m_price, dict) else {}
                    hi_52w = m_dict.get("52WeekHigh")
                    lo_52w = m_dict.get("52WeekLow")
            except Exception as m_err:
                if "429" in str(m_err):
                    raise RateLimitError(str(m_err)) from m_err
                pass  # fall through to basic financials

            # --- 3) Expanded fundamentals via company_basic_financials ---
            fundamentals_metric = {}
            try:
                if hasattr(self._client, "company_basic_financials"):
                    self._throttle()
                    fin_data = self._client.company_basic_financials(symbol, "all")
                    fundamentals_metric = fin_data.get("metric", {}) if isinstance(fin_data, dict) else {}
                    # If 52w not obtained yet, attempt from this payload
                    hi_52w = hi_52w or fundamentals_metric.get("52WeekHigh")
                    lo_52w = lo_52w or fundamentals_metric.get("52WeekLow")
            except Exception as f_err:
                if "429" in str(f_err):
                    raise RateLimitError(str(f_err)) from f_err
                pass
        except Exception as err:  # pragma: no cover – network / API error
            # Bubble up hard rate-limit so callers can disable Finnhub gracefully
            if "429" in str(err):
                raise RateLimitError(str(err)) from err
            print(f"! Finnhub error for {symbol}: {err}")
            return None

        current_price = quote.get("c")  # Current price
        market_cap_mln = profile.get("marketCapitalization")  # in *millions*

        if not current_price or not market_cap_mln:
            return None

        # Finnhub sometimes sends volume None pre-market; coerce to 0 for downstream maths
        volume_val = quote.get("v") or 0
        # Try to replace with 10-day average trading volume from fundamentals if available
        avg_vol = fundamentals_metric.get("10DayAverageTradingVolume") if 'fundamentals_metric' in locals() else None
        if avg_vol is not None:
            # Finnhub returns in millions of shares; convert if value is < 1000
            if avg_vol < 1000:
                volume_val = int(avg_vol * 1_000_000)
            else:
                volume_val = int(avg_vol)

        # hi_52w / lo_52w may still be None if not provided by the API
        

        snapshot = {
            "current_price": current_price,
            "prev_close": quote.get("pc"),
            "volume": volume_val,
            "market_cap": market_cap_mln * 1_000_000,  # convert to absolute dollars
            "exchange": profile.get("exchange"),
            "52w_high": hi_52w,
            "52w_low": lo_52w,
            "fundamentals": fundamentals_metric,
        }

        return snapshot

    def get_month_history(self, symbol: str):
        """Return last-month daily OHLCV as ``pd.DataFrame`` (UTC, tz-naive)."""
        end = int(time.time())
        start = end - 30 * 24 * 60 * 60  # 30 days ago

        self._throttle()
        try:
            candles = self._client.stock_candles(symbol, "D", start, end)
        except Exception as err:  # pragma: no cover
            if "429" in str(err):
                raise RateLimitError(str(err)) from err
            print(f"! Finnhub history error for {symbol}: {err}")
            return None

        if candles.get("s") != "ok":  # Finnhub returns s == 'no_data' on failure
            return None

        df = pd.DataFrame(
            {
                "Close": candles["c"],
                "High": candles["h"],
                "Low": candles["l"],
                "Open": candles["o"],
                "Volume": candles["v"],
            }
        )
        df.index = pd.to_datetime(candles["t"], unit="s", utc=True).tz_convert(None)
        return df

    # Convenience helper -------------------------------------------------------
    def get_stock_data(self, symbol: str) -> Dict[str, Any] | None:
        """Return combined snapshot + 1-month history in the JSON structure used
        throughout the project. The layout matches the output of
        ``DataCollector._assemble_record`` so downstream code remains unchanged.
        """
        snapshot = self.get_stock_snapshot(symbol)
        if snapshot is None:
            return None

        hist_df = self.get_month_history(symbol)
        if hist_df is None or hist_df.empty:
            return None

        avg_volume = hist_df["Volume"].mean() or snapshot.get("volume", 0)

        return {
            "ticker": symbol,
            "current_price": snapshot["current_price"],
            "avg_volume": avg_volume,
            "market_cap": snapshot["market_cap"],
            "exchange": snapshot.get("exchange", ""),
            "year_high": snapshot.get("52w_high"),
            "year_low": snapshot.get("52w_low"),
            "historical_data": {
                "close": hist_df["Close"].tolist(),
                "volume": hist_df["Volume"].tolist(),
                "high": hist_df["High"].tolist(),
                "low": hist_df["Low"].tolist(),
                "dates": hist_df.index.strftime("%Y-%m-%d").tolist(),
            },
        } 