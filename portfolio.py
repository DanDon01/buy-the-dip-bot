"""
Portfolio tracking and position sizing.

Positions are stored in cache/portfolio.json. The module provides:

* Recording buys/sells and computing open P&L against the latest known price
  (from cache/stock_data.json, falling back to a live quote).
* Risk-based position sizing: risk a fixed % of portfolio equity per trade,
  with the stop distance derived from the stock's ATR (volatility), scaled by
  the conviction implied by its dip score.

CLI:
    python cli.py --portfolio                          # view holdings + P&L
    python cli.py --portfolio-add AAPL --shares 10 --price 150
    python cli.py --portfolio-sell AAPL --shares 5 --price 170
    python cli.py --position-size AAPL                 # sizing suggestion

API (Flask):
    GET    /api/portfolio
    POST   /api/portfolio/position        {ticker, shares, price}
    POST   /api/portfolio/sell            {ticker, shares, price}
    GET    /api/portfolio/position-size/<ticker>
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

PORTFOLIO_FILE = os.path.join("cache", "portfolio.json")

DEFAULT_SETTINGS = {
    "total_capital": 10000.0,       # account size used for sizing
    "risk_per_trade_pct": 1.0,      # % of capital risked per position
    "max_position_pct": 15.0,       # cap on any single position
    "atr_stop_multiple": 2.0,       # stop distance = N x ATR(14)
}


class Portfolio:
    """JSON-persisted portfolio with cost-basis accounting."""

    def __init__(self, path: str = PORTFOLIO_FILE):
        self.path = path
        self.data = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> Dict:
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data.setdefault("positions", {})
        data.setdefault("closed_trades", [])
        data.setdefault("settings", dict(DEFAULT_SETTINGS))
        # Merge in any settings keys added after the file was created
        for key, val in DEFAULT_SETTINGS.items():
            data["settings"].setdefault(key, val)
        return data

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------
    def add_position(self, ticker: str, shares: float, price: float,
                     note: str = "") -> Dict:
        """Buy `shares` at `price` (averages into an existing position)."""
        if shares <= 0 or price <= 0:
            raise ValueError("shares and price must be positive")
        ticker = ticker.upper()
        pos = self.data["positions"].get(ticker)
        if pos:
            total_cost = pos["shares"] * pos["avg_cost"] + shares * price
            pos["shares"] += shares
            pos["avg_cost"] = total_cost / pos["shares"]
            pos["last_buy"] = datetime.now().isoformat()
        else:
            pos = {
                "ticker": ticker,
                "shares": shares,
                "avg_cost": price,
                "opened": datetime.now().isoformat(),
                "last_buy": datetime.now().isoformat(),
                "note": note,
            }
            self.data["positions"][ticker] = pos
        self.save()
        return pos

    def sell_position(self, ticker: str, shares: Optional[float],
                      price: float) -> Dict:
        """Sell `shares` (None = all) at `price`. Realized P&L is logged."""
        ticker = ticker.upper()
        pos = self.data["positions"].get(ticker)
        if not pos:
            raise KeyError(f"No open position in {ticker}")
        if price <= 0:
            raise ValueError("price must be positive")
        sell_shares = pos["shares"] if shares is None else min(shares, pos["shares"])
        if sell_shares <= 0:
            raise ValueError("shares must be positive")

        realized = (price - pos["avg_cost"]) * sell_shares
        trade = {
            "ticker": ticker,
            "shares": sell_shares,
            "buy_price": round(pos["avg_cost"], 4),
            "sell_price": price,
            "realized_pnl": round(realized, 2),
            "realized_pnl_pct": round((price / pos["avg_cost"] - 1) * 100, 2),
            "closed": datetime.now().isoformat(),
        }
        self.data["closed_trades"].append(trade)

        pos["shares"] -= sell_shares
        if pos["shares"] <= 1e-9:
            del self.data["positions"][ticker]
        self.save()
        return trade

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------
    def summary(self, price_lookup: Optional[Dict[str, float]] = None) -> Dict:
        """Portfolio snapshot with per-position and total P&L.

        price_lookup: {ticker: current_price}. Missing tickers are looked up
        in cache/stock_data.json; positions with no known price are valued
        at cost.
        """
        prices = dict(price_lookup or {})
        unknown = [t for t in self.data["positions"] if t not in prices]
        if unknown:
            prices.update(_cached_prices(unknown))

        positions = []
        total_cost = total_value = 0.0
        for ticker, pos in sorted(self.data["positions"].items()):
            cost = pos["shares"] * pos["avg_cost"]
            price = prices.get(ticker)
            value = pos["shares"] * price if price else cost
            positions.append({
                "ticker": ticker,
                "shares": pos["shares"],
                "avg_cost": round(pos["avg_cost"], 4),
                "current_price": price,
                "market_value": round(value, 2),
                "unrealized_pnl": round(value - cost, 2) if price else None,
                "unrealized_pnl_pct": round((value / cost - 1) * 100, 2) if price and cost else None,
                "opened": pos.get("opened"),
                "note": pos.get("note", ""),
            })
            total_cost += cost
            total_value += value

        realized = sum(t["realized_pnl"] for t in self.data["closed_trades"])
        return {
            "positions": positions,
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_value, 2),
            "total_unrealized_pnl": round(total_value - total_cost, 2),
            "total_realized_pnl": round(realized, 2),
            "closed_trades": self.data["closed_trades"][-20:],
            "settings": self.data["settings"],
        }


def _cached_prices(tickers: List[str]) -> Dict[str, float]:
    """Best-effort current prices from the local stock_data cache."""
    prices: Dict[str, float] = {}
    try:
        with open(os.path.join("cache", "stock_data.json")) as f:
            stock_data = json.load(f)
        for t in tickers:
            rec = stock_data.get(t)
            if rec and rec.get("current_price"):
                prices[t] = float(rec["current_price"])
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return prices


# ----------------------------------------------------------------------
# Position sizing
# ----------------------------------------------------------------------
def suggest_position_size(price: float,
                          atr: Optional[float] = None,
                          score: Optional[float] = None,
                          total_capital: float = DEFAULT_SETTINGS["total_capital"],
                          risk_per_trade_pct: float = DEFAULT_SETTINGS["risk_per_trade_pct"],
                          max_position_pct: float = DEFAULT_SETTINGS["max_position_pct"],
                          atr_stop_multiple: float = DEFAULT_SETTINGS["atr_stop_multiple"],
                          ) -> Dict:
    """Risk-based position sizing.

    * Risk budget = capital x risk_per_trade_pct (scaled 0.5x-1.5x by score
      conviction: 50 -> 0.5x, 100 -> 1.5x).
    * Stop distance = atr_stop_multiple x ATR (default 8% of price if no ATR).
    * Shares = risk budget / stop distance, capped at max_position_pct of
      capital.
    """
    if price <= 0 or total_capital <= 0:
        raise ValueError("price and total_capital must be positive")

    conviction = 1.0
    if score is not None:
        # 50 -> 0.5x, 75 -> 1.0x, 100 -> 1.5x (clamped)
        conviction = max(0.5, min(1.5, 0.5 + (score - 50) / 50))

    risk_budget = total_capital * (risk_per_trade_pct / 100) * conviction
    stop_distance = atr_stop_multiple * atr if atr and atr > 0 else price * 0.08
    stop_price = max(price - stop_distance, 0.01)

    shares = risk_budget / stop_distance
    max_value = total_capital * (max_position_pct / 100)
    capped = False
    if shares * price > max_value:
        shares = max_value / price
        capped = True

    shares = int(shares) if shares >= 1 else round(shares, 4)
    position_value = shares * price
    return {
        "shares": shares,
        "position_value": round(position_value, 2),
        "position_pct_of_capital": round(position_value / total_capital * 100, 2),
        "risk_budget": round(risk_budget, 2),
        "stop_price": round(stop_price, 2),
        "stop_distance": round(stop_distance, 4),
        "conviction_multiplier": round(conviction, 2),
        "capped_by_max_position": capped,
        "inputs": {
            "price": price, "atr": atr, "score": score,
            "total_capital": total_capital,
            "risk_per_trade_pct": risk_per_trade_pct,
            "max_position_pct": max_position_pct,
            "atr_stop_multiple": atr_stop_multiple,
        },
    }


def compute_atr_from_history(historical_data: Dict, period: int = 14) -> Optional[float]:
    """ATR(14) from the cached historical_data structure (close/high/low lists)."""
    try:
        import pandas as pd
        df = pd.DataFrame({
            "Close": historical_data["close"],
            "High": historical_data["high"],
            "Low": historical_data["low"],
        })
        prev_close = df["Close"].shift(1)
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        if atr and atr == atr:   # not NaN
            return float(atr)
    except Exception:
        pass
    return None


def position_size_for_ticker(ticker: str, portfolio: Optional[Portfolio] = None) -> Dict:
    """Sizing suggestion for a ticker using cached price/ATR/score data."""
    ticker = ticker.upper()
    pf = portfolio or Portfolio()
    settings = pf.data["settings"]

    price = atr = score = None
    try:
        with open(os.path.join("cache", "stock_data.json")) as f:
            rec = json.load(f).get(ticker) or {}
        price = rec.get("current_price")
        if rec.get("historical_data"):
            atr = compute_atr_from_history(rec["historical_data"])
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    try:
        with open(os.path.join("cache", "daily_scores.json")) as f:
            sc = json.load(f).get("scores", {}).get(ticker) or {}
        score = sc.get("score")
        price = price or sc.get("price")
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if not price:
        raise KeyError(f"No cached price for {ticker} - run data collection first")

    result = suggest_position_size(
        price=float(price), atr=atr, score=score,
        total_capital=settings["total_capital"],
        risk_per_trade_pct=settings["risk_per_trade_pct"],
        max_position_pct=settings["max_position_pct"],
        atr_stop_multiple=settings["atr_stop_multiple"],
    )
    result["ticker"] = ticker
    return result
