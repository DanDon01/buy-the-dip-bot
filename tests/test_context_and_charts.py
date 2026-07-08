"""Sector rotation, options analysis, charting, and alert formatting tests."""

import pandas as pd

from alerts import format_alert_message, AlertManager
from analysis.sector_rotation import SECTOR_ETFS, compute_sector_rotation
from charting import build_chart_payload
from collectors.options_data import analyze_chain
from tests.conftest import make_price_series


# ----------------------------------------------------------------------
# Sector rotation
# ----------------------------------------------------------------------
def test_sector_rotation_phases_and_ranks():
    price_data = {etf: make_price_series(seed=i, drift=0.001 if i % 2 else -0.001)
                  for i, etf in enumerate(SECTOR_ETFS)}
    benchmark = make_price_series(seed=50, drift=0.0002)

    result = compute_sector_rotation(price_data, benchmark)
    sectors = result["sectors"]
    assert len(sectors) == len(SECTOR_ETFS)
    ranks = [s["momentum_rank"] for s in sectors]
    assert ranks == sorted(ranks)
    assert all(s["phase"] in {"leading", "improving", "weakening", "lagging", "unknown"}
               for s in sectors)
    # Uptrending sectors should rank above downtrending ones
    top, bottom = sectors[0], sectors[-1]
    assert (top["rel_strength_1m_pct"] or 0) >= (bottom["rel_strength_1m_pct"] or 0)


# ----------------------------------------------------------------------
# Options analysis
# ----------------------------------------------------------------------
def _fake_chain():
    calls = pd.DataFrame({
        "strike": [90, 100, 110],
        "volume": [100, 200, 150],
        "openInterest": [1000, 2000, 500],
        "impliedVolatility": [0.35, 0.30, 0.28],
    })
    puts = pd.DataFrame({
        "strike": [90, 100, 110],
        "volume": [400, 300, 100],
        "openInterest": [3000, 1500, 200],
        "impliedVolatility": [0.45, 0.33, 0.30],
    })
    return calls, puts


def test_options_analysis_metrics():
    calls, puts = _fake_chain()
    result = analyze_chain(calls, puts, spot_price=100.0, expiration="2026-08-21")
    assert result["put_call_volume_ratio"] == round(800 / 450, 3)
    assert result["atm_call_iv"] == 0.30
    assert result["atm_put_iv"] == 0.33
    assert result["max_pain_strike"] in {90.0, 100.0, 110.0}
    assert "put_call" in result["signals"]


def test_options_analysis_empty_chain():
    empty = pd.DataFrame(columns=["strike", "volume", "openInterest", "impliedVolatility"])
    result = analyze_chain(empty, empty, spot_price=100.0)
    assert result["put_call_volume_ratio"] is None
    assert result["max_pain_strike"] is None


# ----------------------------------------------------------------------
# Charting
# ----------------------------------------------------------------------
def test_chart_payload_series(dipped_stock):
    payload = build_chart_payload(dipped_stock, "test")
    assert payload["ticker"] == "TEST"
    assert payload["meta"]["bars"] == len(dipped_stock)
    point = payload["points"][-1]
    for key in ("close", "sma20", "sma50", "sma200", "bbUpper", "bbLower",
                "rsi", "macd", "macdSignal", "macdHist", "volume"):
        assert key in point
    # With 400 bars, all indicators should be populated at the end
    assert point["sma200"] is not None
    assert point["rsi"] is not None and 0 <= point["rsi"] <= 100
    # Early bars must have None (not NaN) for long-window indicators
    assert payload["points"][0]["sma200"] is None


# ----------------------------------------------------------------------
# Alerts
# ----------------------------------------------------------------------
def test_alert_message_formatting():
    candidates = [
        {"ticker": "AAPL", "score": 85.0, "price": 150.0, "action": "STRONG_BUY",
         "grade": "A", "reason": "ideal dip conditions"},
        {"ticker": "MSFT", "score": 78.5, "price": 300.0, "action": "BUY",
         "grade": "B+", "reason": ""},
    ]
    subject, body = format_alert_message(candidates, 75)
    assert "AAPL" in subject and "85.0" in subject
    assert "MSFT" in body and "STRONG_BUY" in body


def test_alert_candidate_detection_and_dedupe(tmp_path, monkeypatch):
    import alerts
    monkeypatch.setattr(alerts, "STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setattr(alerts, "LOG_FILE", str(tmp_path / "log.csv"))

    scores = {"scores": {
        "AAPL": {"score": 82, "price": 150,
                 "score_details": {"investment_recommendation":
                                   {"action": "STRONG_BUY", "reason": "test"},
                                   "overall_grade": "A"}},
        "XYZ": {"score": 30, "price": 10, "score_details": {}},
    }}
    manager = alerts.AlertManager(threshold=75)
    candidates = manager.find_candidates(scores)
    assert [c["ticker"] for c in candidates] == ["AAPL"]

    # After recording, the same candidate is deduped within the cooldown
    manager._record(candidates)
    assert manager.filter_new(candidates) == []
    # ...unless the score improves by 5+
    improved = [dict(candidates[0], score=90.0)]
    assert manager.filter_new(improved) == improved
