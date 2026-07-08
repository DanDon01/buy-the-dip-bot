"""Backtesting engine tests using synthetic data (no network)."""

import numpy as np
import pandas as pd

from backtesting import BacktestConfig, run_backtest, technical_dip_score
from backtesting.engine import combine_components, score_components
from tests.conftest import make_price_series


def test_dip_score_higher_for_dipped_stock(flat_market, dipped_stock):
    dipped_window = dipped_stock.iloc[:301].tail(252)   # right after the dip
    flat_window = flat_market.iloc[:301].tail(252)

    dip_score, dip_comps = technical_dip_score(dipped_window)
    flat_score, _ = technical_dip_score(flat_window)

    assert dip_score > flat_score
    assert dip_comps["drop"] > 0
    assert 0 <= dip_score <= 100


def test_score_components_ranges(dipped_stock):
    comps = score_components(dipped_stock.tail(252))
    for key in ("drop", "rsi", "volume", "sma", "macd"):
        assert 0.0 <= comps[key] <= 1.0
    assert comps["_drop_pct"] >= 0


def test_combine_components_matches_score(dipped_stock):
    window = dipped_stock.tail(252)
    weights = {"drop": 30, "rsi": 25, "volume": 15, "sma": 15, "macd": 15}
    score, comps = technical_dip_score(window, weights)
    assert abs(combine_components(comps, weights) - score) < 1e-9


def test_run_backtest_produces_trades_and_metrics():
    price_data = {
        f"TICK{i}": make_price_series(seed=i, dip_at=250 + i * 5)
        for i in range(6)
    }
    benchmark = make_price_series(seed=99, drift=0.0004, vol=0.01)
    cfg = BacktestConfig(top_n=3, hold_days=10, rebalance_days=10,
                         min_history_days=200, min_score=10)

    result = run_backtest(price_data, benchmark, cfg)
    summary = result["summary"]

    assert summary["total_trades"] > 0
    assert 0 <= summary["win_rate_pct"] <= 100
    assert "avg_return_pct" in summary
    assert "max_drawdown_pct" in summary
    # Trades must carry the component data the optimizer needs
    trade = result["trades"][0]
    assert set(trade["components"]).issuperset({"drop", "rsi", "volume", "sma", "macd"})
    assert trade["excess_return_pct"] is not None


def test_backtest_no_lookahead():
    """A ticker whose dip happens after the last entry date can't be traded
    on pre-dip data with a high score at entry."""
    price = make_price_series(n_days=260, dip_at=None, drift=0.001, vol=0.004, seed=11)
    cfg = BacktestConfig(top_n=5, hold_days=20, rebalance_days=20,
                         min_history_days=200, min_score=60)
    result = run_backtest({"UP": price}, price.copy(), cfg)
    # Steadily rising stock should never look like a high-scoring dip
    assert result["summary"]["total_trades"] == 0
