"""
market_data.py - Unified Yahoo Finance access layer built on yfinance.

Why this exists
---------------
The project originally used ``yahooquery``, which stopped working after Yahoo
introduced cookie/crumb authentication and the package went unmaintained.
``yfinance`` is actively maintained (1.x line, curl_cffi-based sessions that
handle Yahoo's cookie/crumb flow automatically), so all Yahoo access now goes
through this module.

The :class:`Ticker` class below is a drop-in replacement for
``yahooquery.Ticker`` covering the subset of its API this project uses:

* ``Ticker("AAPL").price`` / ``.summary_detail`` / ``.key_stats`` /
  ``.financial_data`` / ``.asset_profile``  -> ``{symbol: {field: value}}``
* ``Ticker("AAPL MSFT").price``             -> dict keyed by each symbol
* ``Ticker("AAPL").history(period="1mo", interval="1d")`` -> DataFrame

yfinance exposes all quote-summary modules merged into a single ``info``
dict using the same camelCase field names Yahoo returns (``marketCap``,
``trailingPE``, ``freeCashflow`` ...), so every module property returns that
merged dict - callers already merge the module dicts themselves, so this is
fully compatible.

Rate limiting: a module-wide minimum delay between Yahoo requests is enforced
(``YF_RATE_LIMIT_SECONDS`` env var, default 0.5s) to respect the project's
rule #1: never risk API bans.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

_RATE_LIMIT_SECONDS = float(os.getenv("YF_RATE_LIMIT_SECONDS", "0.5"))
_rate_lock = threading.Lock()
_last_request_time = 0.0


def _rate_limit():
    """Block until at least _RATE_LIMIT_SECONDS since the last Yahoo request."""
    global _last_request_time
    with _rate_lock:
        now = time.time()
        wait = _RATE_LIMIT_SECONDS - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.time()


class Ticker:
    """yahooquery-compatible wrapper around yfinance.

    Accepts one or more space-separated symbols. Extra keyword arguments
    (``asynchronous``, ``progress``, ``timeout`` ...) are accepted for
    backward compatibility and ignored where yfinance has no equivalent.
    """

    def __init__(self, symbols: str, **kwargs):
        self.symbols: List[str] = [s for s in str(symbols).split() if s]
        self._info_cache: Dict[str, dict] = {}
        self._timeout = kwargs.get("timeout", 10)

    # ------------------------------------------------------------------
    # info / quote-summary modules
    # ------------------------------------------------------------------
    def _get_info(self, symbol: str) -> dict:
        if symbol not in self._info_cache:
            try:
                _rate_limit()
                info = yf.Ticker(symbol).info or {}
                if not isinstance(info, dict):
                    info = {}
            except Exception:
                info = {}
            # Normalise a couple of fields yahooquery used to expose
            if "exchangeName" not in info and info.get("fullExchangeName"):
                info["exchangeName"] = info["fullExchangeName"]
            self._info_cache[symbol] = info
        return self._info_cache[symbol]

    def _module(self) -> Dict[str, dict]:
        """Return {symbol: merged info dict} - shared by all module props."""
        return {sym: self._get_info(sym) for sym in self.symbols}

    @property
    def price(self) -> Dict[str, dict]:
        return self._module()

    @property
    def summary_detail(self) -> Dict[str, dict]:
        return self._module()

    @property
    def key_stats(self) -> Dict[str, dict]:
        return self._module()

    @property
    def financial_data(self) -> Dict[str, dict]:
        return self._module()

    @property
    def asset_profile(self) -> Dict[str, dict]:
        return self._module()

    @property
    def summary_profile(self) -> Dict[str, dict]:
        return self._module()

    # ------------------------------------------------------------------
    # history
    # ------------------------------------------------------------------
    def history(self, period: str = "1mo", interval: str = "1d",
                **kwargs) -> Optional[pd.DataFrame]:
        """Daily/intraday OHLCV history.

        Single symbol: DataFrame with a plain DatetimeIndex and Title-case
        columns (Open/High/Low/Close/Volume) - same shape both yahooquery
        consumers and yfinance callers already handle.

        Multiple symbols: DataFrame with a (symbol, date) MultiIndex, matching
        yahooquery's layout so existing ``.xs(symbol, level=0)`` calls work.
        """
        try:
            _rate_limit()
            if len(self.symbols) == 1:
                df = yf.Ticker(self.symbols[0]).history(
                    period=period, interval=interval, auto_adjust=False)
                if df is None or df.empty:
                    return df
                return df

            frames = {}
            data = yf.download(self.symbols, period=period, interval=interval,
                               group_by="ticker", auto_adjust=False,
                               progress=False, threads=False)
            if data is None or data.empty:
                return data
            for sym in self.symbols:
                try:
                    sub = data[sym].dropna(how="all")
                    if not sub.empty:
                        frames[sym] = sub
                except (KeyError, TypeError):
                    continue
            if not frames:
                return pd.DataFrame()
            return pd.concat(frames, names=["symbol", "date"])
        except Exception:
            return None


# ----------------------------------------------------------------------
# Convenience helpers used by the newer modules (backtesting, sectors ...)
# ----------------------------------------------------------------------
def get_history(symbol: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch OHLCV history for one symbol. Returns None on failure."""
    try:
        _rate_limit()
        df = yf.Ticker(symbol).history(period=period, interval=interval,
                                       auto_adjust=False)
        if df is None or df.empty:
            return None
        df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
        return df
    except Exception:
        return None


def download_history(symbols: List[str], period: str = "1y",
                     interval: str = "1d") -> Dict[str, pd.DataFrame]:
    """Batch-download OHLCV history. Returns {symbol: DataFrame}."""
    result: Dict[str, pd.DataFrame] = {}
    if not symbols:
        return result
    try:
        _rate_limit()
        data = yf.download(list(symbols), period=period, interval=interval,
                           group_by="ticker", auto_adjust=False,
                           progress=False, threads=False)
        if data is None or data.empty:
            return result
        if len(symbols) == 1:
            sym = symbols[0]
            df = data.dropna(how="all")
            if isinstance(df.columns, pd.MultiIndex):
                df = df[sym] if sym in df.columns.get_level_values(0) else df
            if not df.empty:
                df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)
                result[sym] = df
            return result
        for sym in symbols:
            try:
                sub = data[sym].dropna(how="all")
                if not sub.empty:
                    sub.index = pd.to_datetime(sub.index, utc=True).tz_convert(None)
                    result[sym] = sub
            except (KeyError, TypeError):
                continue
    except Exception:
        pass
    return result


def get_info(symbol: str) -> dict:
    """Fetch the merged quote-summary info dict for a symbol."""
    return Ticker(symbol)._get_info(symbol)


def get_option_expirations(symbol: str) -> List[str]:
    """List available option expiration dates for a symbol."""
    try:
        _rate_limit()
        return list(yf.Ticker(symbol).options or [])
    except Exception:
        return []


def get_option_chain(symbol: str, expiration: Optional[str] = None):
    """Return (calls_df, puts_df) for the given / nearest expiration."""
    try:
        _rate_limit()
        chain = yf.Ticker(symbol).option_chain(expiration)
        return chain.calls, chain.puts
    except Exception:
        return None, None
