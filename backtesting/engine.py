"""
Historical backtesting engine (Phase 4 of the enhancement plan).

Validates the dip-buying methodology against historical data:

1. Walks forward through history at a fixed rebalance interval.
2. At each rebalance date, scores every ticker using only data available
   up to that date (point-in-time technical dip score - no lookahead).
3. "Buys" the top-N scorers above a minimum score and measures the forward
   return over the holding period, against a benchmark (SPY by default).
4. Produces win rate, average/median return, excess return vs benchmark,
   Sharpe ratio and max drawdown, plus a per-trade table.

The technical dip score mirrors the live 4-layer methodology's price-based
layers (Dip Signal + Reversal Spark). Fundamentals (Quality Gate) cannot be
reconstructed historically from free data sources, so the backtest measures
the timing engine - the layer the methodology leans on hardest (45% weight).

Each trade records its raw component values so the weight optimizer
(optimization/weight_optimizer.py) can re-weight components without
re-downloading data.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Default component weights (sum to 100). These mirror the live methodology:
# drop severity + RSI + volume make up the Dip Signal, MACD/reversal the
# Reversal Spark, and SMA/trend positioning the risk context.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "drop": 30.0,      # % below trailing high, sweet spot 15-40%
    "rsi": 25.0,       # RSI(14) oversold
    "volume": 15.0,    # volume spike 1.5x-3x sweet spot
    "sma": 15.0,       # position vs SMA50/SMA200
    "macd": 15.0,      # MACD reversal / momentum shift
}


@dataclass
class BacktestConfig:
    top_n: int = 10                 # positions per rebalance
    hold_days: int = 21             # holding period in trading days (~1 month)
    rebalance_days: int = 21        # trading days between entries
    min_history_days: int = 200     # bars needed before a ticker is scoreable
    min_score: float = 40.0         # only "buy" candidates above this score
    lookback_days: int = 252        # trailing window used for scoring
    benchmark: str = "SPY"
    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


# ----------------------------------------------------------------------
# Point-in-time scoring
# ----------------------------------------------------------------------
def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    last_gain = gain.iloc[-1]
    last_loss = loss.iloc[-1]
    if np.isnan(last_gain) or np.isnan(last_loss):
        return 50.0
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return float(100 - (100 / (1 + rs)))


def score_components(window: pd.DataFrame) -> Dict[str, float]:
    """Compute raw dip-score components (each scaled 0..1) from an OHLCV window.

    The window must contain only data up to the evaluation date (the engine
    guarantees this), with Title-case columns: Close, Volume, High, Low.
    """
    close = window["Close"]
    volume = window["Volume"]
    price = float(close.iloc[-1])

    components: Dict[str, float] = {}

    # --- Drop severity: % below trailing high, 15-40% is the sweet spot ---
    trailing_high = float(close.max())
    drop_pct = (trailing_high - price) / trailing_high * 100 if trailing_high > 0 else 0.0
    if 15 <= drop_pct <= 40:
        components["drop"] = 1.0
    elif 10 <= drop_pct < 15:
        components["drop"] = 0.6
    elif 40 < drop_pct <= 55:
        components["drop"] = 0.5   # deep value - riskier
    elif 5 <= drop_pct < 10:
        components["drop"] = 0.3
    else:
        components["drop"] = 0.0

    # --- RSI(14) oversold ---
    rsi = _rsi(close)
    if rsi < 25:
        components["rsi"] = 1.0
    elif rsi < 30:
        components["rsi"] = 0.8
    elif rsi < 35:
        components["rsi"] = 0.55
    elif rsi < 45:
        components["rsi"] = 0.25
    else:
        components["rsi"] = 0.0

    # --- Volume spike: 1.5x-3x the 20-day average is the sweet spot ---
    vol_avg20 = float(volume.tail(21).iloc[:-1].mean()) if len(volume) > 21 else float(volume.mean())
    vol_ratio = float(volume.iloc[-1]) / vol_avg20 if vol_avg20 > 0 else 1.0
    if 1.5 <= vol_ratio <= 3.0:
        components["volume"] = 1.0
    elif 1.2 <= vol_ratio < 1.5:
        components["volume"] = 0.5
    elif vol_ratio > 3.0:
        components["volume"] = 0.4   # panic blowoff - partially useful
    else:
        components["volume"] = 0.0

    # --- SMA positioning: dip below SMA50 while long-term trend intact ---
    sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    sma_score = 0.0
    if sma50 and price < sma50:
        sma_score += 0.5
    if sma200:
        if price >= sma200 * 0.9:   # not in structural breakdown
            sma_score += 0.5
    else:
        sma_score += 0.25
    components["sma"] = min(sma_score, 1.0)

    # --- MACD reversal: histogram improving / bullish cross ---
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    macd_score = 0.0
    if len(hist) >= 2:
        bullish_cross = macd.iloc[-2] < signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]
        if bullish_cross:
            macd_score = 1.0
        elif hist.iloc[-1] > hist.iloc[-2]:   # histogram rising = momentum shift
            macd_score = 0.6
        elif hist.iloc[-1] > 0:
            macd_score = 0.3
    components["macd"] = macd_score

    components["_drop_pct"] = drop_pct
    components["_rsi_14"] = rsi
    components["_vol_ratio"] = vol_ratio
    return components


def technical_dip_score(window: pd.DataFrame,
                        weights: Optional[Dict[str, float]] = None
                        ) -> Tuple[float, Dict[str, float]]:
    """Score an OHLCV window 0-100 using the weighted dip components."""
    w = weights or DEFAULT_WEIGHTS
    comps = score_components(window)
    score = sum(w.get(k, 0.0) * comps.get(k, 0.0) for k in w)
    return float(score), comps


def combine_components(components: Dict[str, float],
                       weights: Dict[str, float]) -> float:
    """Re-score previously recorded components with different weights."""
    return float(sum(weights.get(k, 0.0) * components.get(k, 0.0) for k in weights))


# ----------------------------------------------------------------------
# Backtest loop
# ----------------------------------------------------------------------
def run_backtest(price_data: Dict[str, pd.DataFrame],
                 benchmark: Optional[pd.DataFrame],
                 config: Optional[BacktestConfig] = None) -> Dict:
    """Run the walk-forward backtest over pre-fetched price data.

    Args:
        price_data: {ticker: OHLCV DataFrame} with DatetimeIndex, Title-case cols.
        benchmark: OHLCV DataFrame for the benchmark (may be None).
        config: BacktestConfig.

    Returns a result dict with summary metrics and the per-trade table.
    """
    cfg = config or BacktestConfig()

    # Build the union calendar from the benchmark or the largest ticker frame
    if benchmark is not None and not benchmark.empty:
        calendar = benchmark.index
    else:
        calendar = max(price_data.values(), key=len).index

    trades: List[Dict] = []
    period_returns: List[float] = []       # equal-weighted basket return per rebalance
    period_bench_returns: List[float] = []

    start_idx = cfg.min_history_days
    last_entry_idx = len(calendar) - cfg.hold_days - 1
    entry_indices = range(start_idx, max(start_idx, last_entry_idx) + 1, cfg.rebalance_days)

    for idx in entry_indices:
        entry_date = calendar[idx]
        exit_date = calendar[min(idx + cfg.hold_days, len(calendar) - 1)]

        # Score all candidates using data up to (and including) entry_date
        scored: List[Tuple[str, float, Dict[str, float]]] = []
        for ticker, df in price_data.items():
            hist = df.loc[:entry_date]
            if len(hist) < cfg.min_history_days:
                continue
            future = df.loc[entry_date:]
            if len(future) < cfg.hold_days + 1:
                continue
            window = hist.tail(cfg.lookback_days)
            try:
                score, comps = technical_dip_score(window, cfg.weights)
            except Exception:
                continue
            if score >= cfg.min_score:
                scored.append((ticker, score, comps))

        if not scored:
            continue

        scored.sort(key=lambda x: x[1], reverse=True)
        picks = scored[: cfg.top_n]

        # Benchmark return over the same window
        bench_ret = None
        if benchmark is not None and not benchmark.empty:
            b = benchmark.loc[entry_date:exit_date]["Close"]
            if len(b) >= 2 and b.iloc[0] > 0:
                bench_ret = float(b.iloc[-1] / b.iloc[0] - 1)

        pick_returns = []
        for ticker, score, comps in picks:
            df = price_data[ticker]
            span = df.loc[entry_date:exit_date]["Close"]
            if len(span) < 2 or span.iloc[0] <= 0:
                continue
            fwd_ret = float(span.iloc[-1] / span.iloc[0] - 1)
            pick_returns.append(fwd_ret)
            trades.append({
                "ticker": ticker,
                "entry_date": str(pd.Timestamp(entry_date).date()),
                "exit_date": str(pd.Timestamp(exit_date).date()),
                "score": round(score, 2),
                "entry_price": round(float(span.iloc[0]), 4),
                "exit_price": round(float(span.iloc[-1]), 4),
                "return_pct": round(fwd_ret * 100, 3),
                "benchmark_return_pct": round(bench_ret * 100, 3) if bench_ret is not None else None,
                "excess_return_pct": round((fwd_ret - bench_ret) * 100, 3) if bench_ret is not None else None,
                "components": {k: round(v, 4) for k, v in comps.items()},
            })

        if pick_returns:
            period_returns.append(float(np.mean(pick_returns)))
            if bench_ret is not None:
                period_bench_returns.append(bench_ret)

    return _build_result(trades, period_returns, period_bench_returns, cfg)


def _max_drawdown(period_returns: List[float]) -> float:
    """Max drawdown of the compounded equity curve, as a fraction (0..1)."""
    if not period_returns:
        return 0.0
    equity = np.cumprod([1 + r for r in period_returns])
    peaks = np.maximum.accumulate(equity)
    drawdowns = 1 - equity / peaks
    return float(np.max(drawdowns))


def _build_result(trades: List[Dict], period_returns: List[float],
                  period_bench_returns: List[float], cfg: BacktestConfig) -> Dict:
    returns = [t["return_pct"] / 100 for t in trades]
    excess = [t["excess_return_pct"] / 100 for t in trades
              if t.get("excess_return_pct") is not None]

    summary: Dict = {
        "total_trades": len(trades),
        "rebalance_periods": len(period_returns),
        "config": {**asdict(cfg)},
    }

    if trades:
        wins = sum(1 for r in returns if r > 0)
        summary.update({
            "win_rate_pct": round(wins / len(returns) * 100, 2),
            "avg_return_pct": round(float(np.mean(returns)) * 100, 3),
            "median_return_pct": round(float(np.median(returns)) * 100, 3),
            "best_trade_pct": round(max(returns) * 100, 3),
            "worst_trade_pct": round(min(returns) * 100, 3),
        })
        if excess:
            beat = sum(1 for e in excess if e > 0)
            summary.update({
                "avg_excess_return_pct": round(float(np.mean(excess)) * 100, 3),
                "beat_benchmark_rate_pct": round(beat / len(excess) * 100, 2),
            })
        if period_returns:
            mean_r = float(np.mean(period_returns))
            std_r = float(np.std(period_returns, ddof=1)) if len(period_returns) > 1 else 0.0
            periods_per_year = max(1, round(252 / cfg.rebalance_days))
            sharpe = (mean_r / std_r) * np.sqrt(periods_per_year) if std_r > 0 else None
            total_growth = float(np.prod([1 + r for r in period_returns]))
            years = len(period_returns) / periods_per_year
            cagr = total_growth ** (1 / years) - 1 if years > 0 and total_growth > 0 else None
            summary.update({
                "strategy_cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
                "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
                "max_drawdown_pct": round(_max_drawdown(period_returns) * 100, 2),
            })
        if period_bench_returns:
            bench_growth = float(np.prod([1 + r for r in period_bench_returns]))
            summary["benchmark_total_return_pct"] = round((bench_growth - 1) * 100, 2)
            strat_growth = float(np.prod([1 + r for r in period_returns]))
            summary["strategy_total_return_pct"] = round((strat_growth - 1) * 100, 2)

    return {
        "summary": summary,
        "trades": trades,
        "generated": datetime.now().isoformat(),
    }


# ----------------------------------------------------------------------
# Data fetching + report output
# ----------------------------------------------------------------------
def fetch_and_run(tickers: List[str], period: str = "2y",
                  config: Optional[BacktestConfig] = None,
                  batch_size: int = 50) -> Dict:
    """Download history for the given tickers and run the backtest."""
    from market_data import download_history, get_history
    import time as _time

    cfg = config or BacktestConfig()
    price_data: Dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"📥 Downloading history {i + 1}-{i + len(batch)} of {len(tickers)}…")
        price_data.update(download_history(batch, period=period))
        _time.sleep(1)   # stay well inside rate limits

    benchmark = get_history(cfg.benchmark, period=period)
    print(f"✅ Got history for {len(price_data)}/{len(tickers)} tickers"
          f" (benchmark {'OK' if benchmark is not None else 'MISSING'})")
    if not price_data:
        return {"summary": {"total_trades": 0, "error": "no price data downloaded"},
                "trades": [], "generated": datetime.now().isoformat()}
    return run_backtest(price_data, benchmark, cfg)


def save_report(result: Dict, out_dir: str = "output/backtests") -> str:
    """Persist the backtest result as JSON + a trades CSV. Returns JSON path."""
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(out_dir, f"backtest_{ts}.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    if result.get("trades"):
        csv_path = os.path.join(out_dir, f"backtest_trades_{ts}.csv")
        flat = []
        for t in result["trades"]:
            row = {k: v for k, v in t.items() if k != "components"}
            row.update({f"comp_{k}": v for k, v in t["components"].items()})
            flat.append(row)
        pd.DataFrame(flat).to_csv(csv_path, index=False)
    return json_path
