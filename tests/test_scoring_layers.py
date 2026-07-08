"""Tests for the Stabilization layer and composite weight configuration."""

import numpy as np
import pandas as pd
import pytest

from scoring.stabilization import Stabilization
from tests.conftest import make_price_series


def _falling_knife(n_days=60, seed=5):
    """A stock dropping ~1.5% every single day - no base, no bounce."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(-0.015, 0.004, n_days)
    close = 100 * np.cumprod(1 + rets)
    dates = pd.bdate_range("2025-01-02", periods=n_days)
    return pd.DataFrame({
        "Close": close,
        "High": close * 1.005,
        "Low": close * 0.985,   # keeps printing new lows
        "Volume": rng.integers(1e6, 2e6, n_days).astype(float),
    }, index=dates)


def _based_stock(n_days=60, seed=6):
    """Crashed earlier, then formed a rising base with shrinking ranges."""
    rng = np.random.default_rng(seed)
    crash = 100 * np.cumprod(1 + np.full(30, -0.02))
    floor = crash[-1]
    # Recovery: gentle uptrend, low volatility, higher lows
    base = floor * np.cumprod(1 + rng.normal(0.004, 0.003, n_days - 30))
    close = np.concatenate([crash, base])
    ranges = np.concatenate([np.full(30, 0.03), np.full(n_days - 30, 0.008)])
    dates = pd.bdate_range("2025-01-02", periods=n_days)
    return pd.DataFrame({
        "Close": close,
        "High": close * (1 + ranges / 2),
        "Low": close * (1 - ranges / 2),
        "Volume": rng.integers(1e6, 2e6, n_days).astype(float),
    }, index=dates)


class TestStabilization:
    def test_falling_knife_scores_low(self):
        score, details = Stabilization().score_stabilization(_falling_knife(), "KNIFE")
        assert score <= 5
        assert details["falling_knife_risk"] in ("high", "moderate")

    def test_based_stock_scores_high(self):
        score, details = Stabilization().score_stabilization(_based_stock(), "BASED")
        assert score >= 9
        assert details["stabilization_state"] in ("stabilized", "basing")
        assert details["falling_knife_risk"] == "low"

    def test_based_beats_knife(self):
        knife_score, _ = Stabilization().score_stabilization(_falling_knife(), "K")
        based_score, _ = Stabilization().score_stabilization(_based_stock(), "B")
        assert based_score > knife_score

    def test_insufficient_history(self):
        df = _based_stock().head(5)
        score, details = Stabilization().score_stabilization(df, "SHORT")
        assert score == 0
        assert details["stabilization_state"] == "insufficient_history"

    def test_score_bounded(self):
        stab = Stabilization(max_points=15)
        for maker in (_falling_knife, _based_stock,
                      lambda: make_price_series(n_days=100, seed=9)):
            score, _ = stab.score_stabilization(maker(), "X")
            assert 0 <= score <= 15


class TestCompositeWeights:
    def test_composite_uses_configured_weights(self, tmp_path):
        """CompositeScorer must rescale native layer scores to config weights."""
        import json
        from scoring.composite_scorer import CompositeScorer
        from scoring.config_manager import ScoringConfigManager

        config_file = tmp_path / "params.json"
        config_file.write_text(json.dumps({"parameters": {
            "quality_gate_weight": 20,
            "dip_signal_weight": 50,
            "reversal_spark_weight": 10,
            "stabilization_weight": 20,
            "risk_adjustment_weight": 10,
        }}))
        scorer = CompositeScorer(ScoringConfigManager(str(config_file)))
        assert scorer.layer_weights["dip_signal"] == 50

        # Native dip max is 45 -> a full native score should rescale to 50
        assert scorer._rescale("dip_signal", 45) == pytest.approx(50)
        assert scorer._rescale("quality_gate", 35) == pytest.approx(20)
        assert scorer._rescale("stabilization", 15) == pytest.approx(20)

    def test_default_weights_sum_to_100(self):
        from scoring.config_manager import ScoringConfigManager
        params = ScoringConfigManager("/nonexistent/params.json")._get_default_parameters()
        base = (params["quality_gate_weight"] + params["dip_signal_weight"]
                + params["reversal_spark_weight"] + params["stabilization_weight"])
        assert base == 100

    def test_layer_scores_include_stabilization(self):
        """End-to-end composite run over synthetic data includes the new layer."""
        from scoring.composite_scorer import CompositeScorer

        df = _based_stock(80)
        enhanced_data = {
            "ticker_data": {
                "ticker": "TEST", "current_price": float(df["Close"].iloc[-1]),
                "market_cap": 5e9, "pe": 18, "free_cash_flow": 1e8,
                "operating_margins": 0.2, "return_on_equity": 0.18,
                "debt_to_equity": 0.4, "current_ratio": 1.8,
                "profit_margins": 0.12, "revenue_growth": 0.08,
                "total_cash": 2e9, "total_debt": 1e9, "sector": "Technology",
            },
            "fundamentals": {},
        }
        score, breakdown = CompositeScorer().calculate_composite_score(df, "TEST", enhanced_data)
        assert "stabilization" in breakdown["layer_scores"]
        assert "stabilization" in breakdown["layer_details"]
        assert "layer_weights" in breakdown
        assert 0 <= breakdown["data_confidence"] <= 1
        # Well-based synthetic stock: stabilization should contribute
        assert breakdown["layer_scores"]["stabilization"] > 0
