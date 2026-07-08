"""Portfolio and position sizing tests."""

import pytest

from portfolio import Portfolio, suggest_position_size


@pytest.fixture
def portfolio(tmp_path):
    return Portfolio(path=str(tmp_path / "portfolio.json"))


def test_add_and_average_position(portfolio):
    portfolio.add_position("aapl", 10, 100)
    pos = portfolio.add_position("AAPL", 10, 200)
    assert pos["shares"] == 20
    assert pos["avg_cost"] == 150


def test_sell_realizes_pnl(portfolio):
    portfolio.add_position("MSFT", 10, 100)
    trade = portfolio.sell_position("MSFT", 4, 150)
    assert trade["realized_pnl"] == 200
    assert portfolio.data["positions"]["MSFT"]["shares"] == 6

    trade = portfolio.sell_position("MSFT", None, 90)   # close the rest
    assert trade["shares"] == 6
    assert "MSFT" not in portfolio.data["positions"]


def test_sell_unknown_raises(portfolio):
    with pytest.raises(KeyError):
        portfolio.sell_position("NOPE", 1, 10)


def test_summary_math(portfolio):
    portfolio.add_position("AAPL", 10, 100)
    summary = portfolio.summary(price_lookup={"AAPL": 120})
    assert summary["total_cost"] == 1000
    assert summary["total_market_value"] == 1200
    assert summary["total_unrealized_pnl"] == 200
    assert summary["positions"][0]["unrealized_pnl_pct"] == 20.0


def test_position_sizing_risk_math():
    s = suggest_position_size(price=100, atr=2.0, score=75,
                              total_capital=10000, risk_per_trade_pct=1.0,
                              atr_stop_multiple=2.0, max_position_pct=100.0)
    # risk budget = 100 (1% x conviction 1.0), stop distance = 4 -> 25 shares
    assert s["risk_budget"] == 100
    assert s["stop_distance"] == 4.0
    assert s["shares"] == 25
    assert s["stop_price"] == 96.0
    # With the default 15% position cap the same trade gets truncated
    capped = suggest_position_size(price=100, atr=2.0, score=75,
                                   total_capital=10000, risk_per_trade_pct=1.0,
                                   atr_stop_multiple=2.0)
    assert capped["capped_by_max_position"] and capped["shares"] == 15


def test_position_sizing_caps_at_max_position():
    s = suggest_position_size(price=10, atr=0.05, score=100,
                              total_capital=10000, risk_per_trade_pct=1.0,
                              max_position_pct=15.0)
    assert s["capped_by_max_position"]
    assert s["position_value"] <= 1500 + 10   # one share of tolerance


def test_position_sizing_score_scales_conviction():
    low = suggest_position_size(price=100, atr=2.0, score=50, total_capital=10000)
    high = suggest_position_size(price=100, atr=2.0, score=100, total_capital=10000)
    assert high["risk_budget"] > low["risk_budget"]


def test_position_sizing_invalid_inputs():
    with pytest.raises(ValueError):
        suggest_position_size(price=0)
