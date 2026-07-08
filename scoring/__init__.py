"""
Layered scoring engine for advanced buy-the-dip analysis.

This package implements the 5-layer scoring methodology (ScoresandMetrics.txt
plus the July 2026 Stabilization extension):

- Quality Gate (default 30): Business fundamentals and financial health
- Dip Signal (default 40): Technical dip detection and oversold conditions
- Reversal Spark (default 15): Momentum shifts and reversal signals
- Stabilization (default 15): Falling-knife filter - has the price based?
- Risk Modifiers (±10 adjustment): Market context and risk factors

Layer weights are configurable via config/scoring_parameters.json (dashboard
Scoring Tuner / ML weight optimizer); CompositeScorer rescales each layer's
native score to the configured weight.

All scoring layers build on the Phase 1 collectors and preserve the existing
efficient data collection pipeline (6000+ → filtered thousands → enhanced scoring).
"""

from .quality_gate import QualityGate
from .dip_signal import DipSignal
from .reversal_spark import ReversalSpark
from .stabilization import Stabilization
from .risk_modifiers import RiskModifiers
from .composite_scorer import CompositeScorer
from .config_manager import ScoringConfigManager

__all__ = [
    'QualityGate',
    'DipSignal',
    'ReversalSpark',
    'Stabilization',
    'RiskModifiers',
    'CompositeScorer',
    'ScoringConfigManager',
]
