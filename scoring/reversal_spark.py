"""
Reversal Spark scorer - Third layer of the 4-layer methodology.

Weight: 10-15% of final score
Purpose: "Is there a spark of life that signals a turnaround?"

Uses Phase 1 TechnicalIndicators to evaluate:
- MACD crossovers and divergence
- Reversal candlestick patterns (Hammers, Dojis)
- Momentum divergence (RSI vs price)
- Volume signatures indicating capitulation or exhaustion

This layer looks for the initial signs that a downtrend is losing steam.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import sys
import os

# Add parent directory to path to import Phase 1 collectors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.technical_indicators import TechnicalIndicators
from collectors.volume_analysis import VolumeAnalyzer


class ReversalSpark:
    """
    Reversal Spark scoring layer - detects early signs of turnaround.
    
    Score Range: 0-15 points (15% of 100-point scale)
    """
    
    def __init__(self, max_points: int = 15):
        self.max_points = max_points
        self.tech_indicators = TechnicalIndicators()
        self.volume_analyzer = VolumeAnalyzer()
        
        # Reversal signal weights (total = max_points)
        self.weights = {
            'macd_signals': 5,
            'candle_patterns': 4,
            'momentum_divergence': 3,
            'volume_reversal': 3
        }
    
    def score_reversal_spark(self, df: pd.DataFrame, ticker: str, enhanced_data: Dict = None) -> Tuple[float, Dict]:
        """
        Score reversal spark signals for a ticker.
        """
        try:
            # THE FIX: Get the nested stock_data record
            stock_data = enhanced_data.get('ticker_data', {})
            if not stock_data:
                return 0, self._empty_reversal_details()

            tech_data = enhanced_data.get('enhanced_tech', {})
            if not tech_data:
                tech_data = self.tech_indicators.calculate_all_indicators(df, ticker)
            
            volume_data = stock_data.get('volume_analysis', {})
            if not volume_data:
                volume_data = self.volume_analyzer.analyze_volume_patterns(df, ticker)

            # Calculate each reversal component
            macd_score = self._score_macd_signals(tech_data)
            candle_score = self._score_candle_patterns(df)
            divergence_score = self._score_momentum_divergence(tech_data)
            volume_reversal_score = self._score_volume_reversal(volume_data)
            
            total_score = macd_score + candle_score + divergence_score + volume_reversal_score
            
            reversal_signals = self._identify_reversal_signals(tech_data, volume_data, df)
            
            reversal_details = {
                'macd_signals': macd_score,
                'candle_patterns': candle_score,
                'momentum_divergence': divergence_score,
                'volume_reversal': volume_reversal_score,
                'total_reversal_score': total_score,
                'reversal_signals': reversal_signals,
                'reversal_strength': self._assess_reversal_strength(total_score)
            }
            
            return total_score, reversal_details
            
        except Exception as e:
            print(f"Error scoring reversal spark for {ticker}: {e}")
            return 0, self._empty_reversal_details()

    def _score_macd_signals(self, tech_data: Dict) -> float:
        """Score MACD crossover and momentum signals."""
        score = 0
        max_score = self.weights['macd_signals']
        
        if tech_data.get('macd_bullish_crossover_recent', False):
            score += 3
        
        if tech_data.get('macd_histogram_increasing', False):
            score += 2
        
        return min(score, max_score)

    def _score_candle_patterns(self, df: pd.DataFrame) -> float:
        """Score reversal candlestick patterns in recent sessions."""
        score = 0
        max_score = self.weights['candle_patterns']
        
        if len(df) < 3: return 0
        
        recent_candles = df.tail(3)
        for i, candle in recent_candles.iterrows():
            pattern_score = self._analyze_candle_pattern(candle)
            if i == recent_candles.index[-1]: score += pattern_score * 1.0
            elif i == recent_candles.index[-2]: score += pattern_score * 0.7
            else: score += pattern_score * 0.5
        
        return min(score, max_score)

    def _analyze_candle_pattern(self, candle: pd.Series) -> float:
        """Analyze individual candle for reversal patterns."""
        open_price = candle.get('Open', candle['Close'])
        high = candle['High']
        low = candle['Low']
        close = candle['Close']
        
        body_size = abs(close - open_price)
        total_range = high - low
        if total_range == 0: return 0
        
        lower_wick = min(open_price, close) - low
        upper_wick = high - max(open_price, close)
        
        is_hammer = (lower_wick > body_size * 2 and upper_wick < body_size * 0.5 and (body_size / total_range) < 0.3)
        is_doji = (body_size / total_range) < 0.1
        
        if is_hammer: return 2.0
        if is_doji: return 1.0
        if lower_wick > body_size: return 0.5
        
        return 0

    def _score_momentum_divergence(self, tech_data: Dict) -> float:
        """Score momentum divergence signals."""
        score = 0
        max_score = self.weights['momentum_divergence']
        
        if tech_data.get('rsi_bullish_divergence', False): score += 2
        if tech_data.get('macd_bullish_divergence', False): score += 2
        if tech_data.get('momentum_slowing', False): score += 1
        
        return min(score, max_score)

    def _score_volume_reversal(self, volume_data: Dict) -> float:
        """Score volume signatures that indicate reversal."""
        score = 0
        max_score = self.weights['volume_reversal']
        
        if volume_data.get('volume_exhaustion_detected', False): score += 2
        if volume_data.get('volume_accumulation_detected', False): score += 2
        
        return min(score, max_score)

    def _identify_reversal_signals(self, tech_data: Dict, volume_data: Dict, df: pd.DataFrame) -> Dict:
        """Identify key binary reversal signals."""
        return {
            'macd_bullish_cross': tech_data.get('macd_bullish_crossover_recent', False),
            'rsi_divergence': tech_data.get('rsi_bullish_divergence', False),
            'hammer_pattern': self._detect_recent_hammer(df),
            'volume_exhaustion': volume_data.get('volume_exhaustion_detected', False),
            'momentum_slowing': tech_data.get('momentum_slowing', False),
        }

    def _detect_recent_hammer(self, df: pd.DataFrame) -> bool:
        """Detect hammer pattern in last 3 sessions."""
        if len(df) < 1: return False
        
        for _, candle in df.tail(3).iterrows():
            if self._analyze_candle_pattern(candle) >= 1.5: return True
        return False
    
    def _assess_reversal_strength(self, score: float) -> str:
        """Assess the overall strength of reversal signals."""
        if score >= self.max_points * 0.7: return 'strong'
        elif score >= self.max_points * 0.5: return 'moderate'
        elif score > 0: return 'weak'
        else: return 'none'

    def _empty_reversal_details(self) -> Dict:
        """Return empty reversal details when calculation fails."""
        return {
            'macd_signals': 0, 'candle_patterns': 0, 'momentum_divergence': 0,
            'volume_reversal': 0, 'total_reversal_score': 0,
            'reversal_signals': {
                'macd_bullish_cross': False, 'rsi_divergence': False,
                'hammer_pattern': False, 'volume_exhaustion': False,
                'momentum_slowing': False,
            },
            'reversal_strength': 'none'
        } 