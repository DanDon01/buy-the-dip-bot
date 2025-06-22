"""
Layered scoring engine for advanced buy-the-dip analysis.

This package implements the 4-layer scoring methodology from ScoresandMetrics.txt:
- Quality Gate (30-40% weight): Business fundamentals and financial health
- Dip Signal (40-50% weight): Technical dip detection and oversold conditions  
- Reversal Spark (10-20% weight): Momentum shifts and reversal signals
- Risk Modifiers (±10% adjustment): Market context and risk factors

All scoring layers build on the Phase 1 collectors and preserve the existing
efficient data collection pipeline (6000+ → filtered thousands → enhanced scoring).
"""

from .quality_gate import QualityGate
from .dip_signal import DipSignal
from .reversal_spark import ReversalSpark
from .risk_modifiers import RiskModifiers
from .composite_scorer import CompositeScorer

__all__ = [
    'QualityGate', 
    'DipSignal', 
    'ReversalSpark', 
    'RiskModifiers', 
    'CompositeScorer'
] 