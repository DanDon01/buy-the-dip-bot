"""
Stabilization scorer - Fifth layer of the methodology (added July 2026).

Weight: ~15% of final score
Purpose: "Has the knife hit the floor, or is it still falling?"

The original 4-layer system scored a stock still in free-fall the same as one
that had already stopped falling and started basing. This layer discriminates
between the two by measuring, from price action alone:

- Base formation: higher lows over the recent window
- Recovery traction: how far price has lifted off its recent low
- Volatility contraction: short-term ATR cooling vs its longer average
  (panic subsiding)
- Down-momentum decay: down days becoming rarer/shallower

A high Dip Signal with a low Stabilization score = "catching a falling
knife". A high Dip Signal WITH a high Stabilization score = the dip has
likely found its floor - the setup the methodology actually wants.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


class Stabilization:
    """
    Stabilization scoring layer - falling-knife filter.

    Score Range: 0-15 points (default; rescaled by CompositeScorer)
    """

    def __init__(self, max_points: int = 15):
        self.max_points = max_points

        # Component weights (total = max_points)
        self.weights = {
            'base_formation': 5,          # higher lows forming
            'recovery_traction': 4,       # bounce off the low holding
            'volatility_contraction': 3,  # panic subsiding (ATR cooling)
            'momentum_decay': 3,          # down days easing off
        }

    def score_stabilization(self, df: pd.DataFrame, ticker: str,
                            enhanced_data: Dict = None) -> Tuple[float, Dict]:
        """Score stabilization signals from the price/volume DataFrame.

        Needs ~30 bars to be meaningful; degrades gracefully below that.
        """
        try:
            if df is None or len(df) < 15:
                return 0, self._empty_details('insufficient_history')

            close = df['Close'].astype(float)
            low = df['Low'].astype(float) if 'Low' in df else close
            high = df['High'].astype(float) if 'High' in df else close

            base_score, base_info = self._score_base_formation(low)
            recovery_score, recovery_info = self._score_recovery_traction(close, low)
            vol_score, vol_info = self._score_volatility_contraction(high, low, close)
            momentum_score, momentum_info = self._score_momentum_decay(close)

            total = base_score + recovery_score + vol_score + momentum_score
            total = min(total, self.max_points)

            details = {
                'base_formation': base_score,
                'recovery_traction': recovery_score,
                'volatility_contraction': vol_score,
                'momentum_decay': momentum_score,
                'total_stabilization_score': total,
                'stabilization_state': self._classify_state(total),
                'falling_knife_risk': self._knife_risk(total),
                'stabilization_grade': self._grade(total),
                'signals': {**base_info, **recovery_info, **vol_info, **momentum_info},
            }
            return total, details

        except Exception as e:
            print(f"Error scoring stabilization for {ticker}: {e}")
            return 0, self._empty_details('calculation_error')

    # ------------------------------------------------------------------
    # Components
    # ------------------------------------------------------------------
    def _score_base_formation(self, low: pd.Series) -> Tuple[float, Dict]:
        """Higher lows over the last ~10 sessions indicate a base forming."""
        max_score = self.weights['base_formation']
        window = low.tail(10)
        if len(window) < 6:
            return 0, {'higher_lows': False}

        # Split the window into thirds and compare their minima
        thirds = np.array_split(window.values, 3)
        mins = [float(np.min(t)) for t in thirds]
        strictly_rising = mins[0] < mins[1] < mins[2]
        partially_rising = mins[2] > mins[0]

        # Also: how many of the last 5 sessions printed a new 10-day low?
        recent_new_lows = int((window.tail(5) <= window.min() * 1.001).sum())

        score = 0.0
        if strictly_rising:
            score = max_score
        elif partially_rising:
            score = max_score * 0.6
        if recent_new_lows >= 2:
            score = max(0.0, score - max_score * 0.4)   # still printing lows

        return score, {
            'higher_lows': bool(strictly_rising),
            'lows_trending_up': bool(partially_rising),
            'new_lows_last_5d': recent_new_lows,
        }

    def _score_recovery_traction(self, close: pd.Series,
                                 low: pd.Series) -> Tuple[float, Dict]:
        """Reward a modest, holding bounce off the recent low.

        Sweet spot: 3-15% above the 20-day low. Less = still on the floor
        (unproven); much more = the discount is already gone.
        """
        max_score = self.weights['recovery_traction']
        lookback = min(len(close), 20)
        # Compare close-to-close: measuring against the Low column would
        # count ordinary intraday range as a "bounce" even in a free-fall.
        recent_low = float(close.tail(lookback).min())
        price = float(close.iloc[-1])
        if recent_low <= 0:
            return 0, {'pct_above_20d_low': None}

        lift_pct = (price - recent_low) / recent_low * 100

        if 3 <= lift_pct <= 15:
            score = max_score
        elif 1.5 <= lift_pct < 3:
            score = max_score * 0.5
        elif 15 < lift_pct <= 25:
            score = max_score * 0.5   # bounce already extended
        elif lift_pct > 25:
            score = max_score * 0.2
        else:
            score = 0.0               # sitting on the low - unproven

        # Did the bounce hold? (close today >= close 3 sessions ago)
        held = len(close) >= 4 and price >= float(close.iloc[-4])
        if score > 0 and held:
            score = min(max_score, score + max_score * 0.25)

        return min(score, max_score), {
            'pct_above_20d_low': round(lift_pct, 2),
            'bounce_holding': bool(held),
        }

    def _score_volatility_contraction(self, high: pd.Series, low: pd.Series,
                                      close: pd.Series) -> Tuple[float, Dict]:
        """ATR(5) cooling below ATR(15) means the panic phase is ending."""
        max_score = self.weights['volatility_contraction']
        prev_close = close.shift(1)
        tr = pd.concat([high - low,
                        (high - prev_close).abs(),
                        (low - prev_close).abs()], axis=1).max(axis=1)
        # Normalise to % of price: in a steep decline the *absolute* range
        # shrinks with the price, which would fake a contraction signal.
        tr = tr / close

        atr5 = tr.rolling(5).mean().iloc[-1]
        atr15 = tr.rolling(min(len(tr), 15)).mean().iloc[-1]
        if not np.isfinite(atr5) or not np.isfinite(atr15) or atr15 <= 0:
            return 0, {'atr_ratio': None}

        ratio = float(atr5 / atr15)
        if ratio <= 0.75:
            score = max_score          # sharp contraction
        elif ratio <= 0.9:
            score = max_score * 0.7
        elif ratio <= 1.0:
            score = max_score * 0.4
        else:
            score = 0.0                # volatility still expanding

        return score, {'atr_ratio': round(ratio, 3),
                       'volatility_contracting': ratio < 1.0}

    def _score_momentum_decay(self, close: pd.Series) -> Tuple[float, Dict]:
        """Down days becoming rarer and shallower vs the prior stretch."""
        max_score = self.weights['momentum_decay']
        rets = close.pct_change().dropna()
        if len(rets) < 10:
            return 0, {'down_days_last_5': None}

        recent = rets.tail(5)
        prior = rets.tail(10).head(5)

        down_recent = int((recent < 0).sum())
        avg_down_recent = float(recent[recent < 0].mean()) if down_recent else 0.0
        avg_down_prior = float(prior[prior < 0].mean()) if (prior < 0).any() else 0.0

        # Still falling nearly every session: no deceleration credit at all
        if down_recent >= 4:
            return 0.0, {
                'down_days_last_5': down_recent,
                'avg_down_day_recent_pct': round(avg_down_recent * 100, 2),
                'avg_down_day_prior_pct': round(avg_down_prior * 100, 2),
            }

        score = 0.0
        if down_recent <= 1:
            score += max_score * 0.5
        elif down_recent == 2:
            score += max_score * 0.3

        # Shallower average down day than the prior week (both negative;
        # "greater" = closer to zero = decelerating)
        if avg_down_prior < 0 and avg_down_recent > avg_down_prior:
            score += max_score * 0.5

        return min(score, max_score), {
            'down_days_last_5': down_recent,
            'avg_down_day_recent_pct': round(avg_down_recent * 100, 2),
            'avg_down_day_prior_pct': round(avg_down_prior * 100, 2),
        }

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------
    def _classify_state(self, score: float) -> str:
        frac = score / self.max_points
        if frac >= 0.7:
            return 'stabilized'
        if frac >= 0.45:
            return 'basing'
        if frac >= 0.25:
            return 'early_signs'
        return 'still_falling'

    def _knife_risk(self, score: float) -> str:
        frac = score / self.max_points
        if frac >= 0.6:
            return 'low'
        if frac >= 0.35:
            return 'moderate'
        return 'high'

    def _grade(self, score: float) -> str:
        frac = score / self.max_points
        if frac >= 0.85: return 'A'
        if frac >= 0.70: return 'B'
        if frac >= 0.55: return 'C'
        if frac >= 0.40: return 'D'
        return 'F'

    def _empty_details(self, reason: str = 'no_data') -> Dict:
        return {
            'base_formation': 0, 'recovery_traction': 0,
            'volatility_contraction': 0, 'momentum_decay': 0,
            'total_stabilization_score': 0,
            'stabilization_state': reason,
            'falling_knife_risk': 'unknown',
            'stabilization_grade': 'F',
            'signals': {},
        }
