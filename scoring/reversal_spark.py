"""
Reversal Spark scorer - Third layer of the 4-layer methodology.

Weight: 10-20% of final score
Purpose: "Is the selling pressure exhausting and buying pressure emerging?"

Detects early momentum shifts and reversal signals:
- MACD bullish crossovers (recent)
- Hammer/pin-bar candlestick patterns
- Positive earnings surprises during dips
- Volume pattern reversals
- Early momentum exhaustion signals

This layer catches the first hints of a turn-up before the crowd notices.
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
    Reversal Spark scoring layer - early momentum shift detection.
    
    Implements the "Reversal Spark" from ScoresandMetrics.txt methodology:
    "Detect the first hints of a turn-up"
    
    Score Range: 0-15 points (15% of 100-point scale)
    Focus: Early reversal signals and momentum exhaustion
    """
    
    def __init__(self, max_points: int = 15):
        self.max_points = max_points
        self.tech_indicators = TechnicalIndicators()
        self.volume_analyzer = VolumeAnalyzer()
        
        # Reversal signal weights (total = max_points)
        self.weights = {
            'macd_signals': 5,          # MACD bullish cross
            'candle_patterns': 4,       # Hammer/pin-bar patterns
            'momentum_divergence': 3,   # Price vs momentum divergence
            'volume_reversal': 3        # Volume pattern shifts
        }
    
    def score_reversal_spark(self, df: pd.DataFrame, ticker: str, enhanced_data: Dict = None) -> Tuple[float, Dict]:
        """
        Score reversal spark signals for a ticker.
        
        Args:
            df: Historical price/volume DataFrame
            ticker: Stock ticker symbol
            enhanced_data: Optional pre-fetched enhanced data from Phase 1
            
        Returns:
            Tuple of (reversal_score, reversal_details)
        """
        try:
            # Get technical and volume data (from Phase 1 or fresh)
            if enhanced_data and 'enhanced_tech' in enhanced_data:
                tech_data = enhanced_data['enhanced_tech']
                volume_data = enhanced_data.get('enhanced_volume', {})
            else:
                tech_data = self.tech_indicators.calculate_all_indicators(df, ticker)
                volume_data = self.volume_analyzer.analyze_volume_patterns(df, ticker)
            
            # Calculate each reversal component
            macd_score = self._score_macd_signals(tech_data)
            candle_score = self._score_candle_patterns(df)
            divergence_score = self._score_momentum_divergence(tech_data)
            volume_reversal_score = self._score_volume_reversal(volume_data)
            
            # Total reversal score
            total_score = macd_score + candle_score + divergence_score + volume_reversal_score
            
            # Identify key reversal signals
            reversal_signals = self._identify_reversal_signals(tech_data, volume_data, df)
            
            reversal_details = {
                'macd_signals': macd_score,
                'candle_patterns': candle_score,
                'momentum_divergence': divergence_score,
                'volume_reversal': volume_reversal_score,
                'total_reversal_score': total_score,
                'reversal_signals': reversal_signals,
                'reversal_strength': self._assess_reversal_strength(total_score),
                'spark_grade': self._get_spark_grade(total_score)
            }
            
            return total_score, reversal_details
            
        except Exception as e:
            print(f"Error scoring reversal spark for {ticker}: {e}")
            return 0, self._empty_reversal_details()
    
    def _score_macd_signals(self, tech_data: Dict) -> float:
        """Score MACD crossover and momentum signals."""
        score = 0
        max_score = self.weights['macd_signals']
        
        # Recent MACD bullish crossover (last 5 days)
        if tech_data.get('macd_bullish_crossover_recent', False):
            score += 3  # Fresh bullish signal
        
        # MACD histogram improving
        if tech_data.get('macd_histogram_improving', False):
            score += 2  # Building momentum
        
        # MACD line above signal line (current state)
        if tech_data.get('macd_bullish', False):
            score += 1  # Favorable momentum
        
        return min(score, max_score)
    
    def _score_candle_patterns(self, df: pd.DataFrame) -> float:
        """Score reversal candlestick patterns in recent sessions."""
        score = 0
        max_score = self.weights['candle_patterns']
        
        if len(df) < 3:
            return 0
        
        # Look at last 3 sessions for reversal patterns
        recent_candles = df.tail(3)
        
        for i in range(len(recent_candles)):
            candle = recent_candles.iloc[i]
            pattern_score = self._analyze_candle_pattern(candle)
            
            # Weight recent patterns higher
            if i == len(recent_candles) - 1:  # Most recent
                score += pattern_score * 1.0
            elif i == len(recent_candles) - 2:  # Second most recent
                score += pattern_score * 0.7
            else:  # Third most recent
                score += pattern_score * 0.5
        
        return min(score, max_score)
    
    def _analyze_candle_pattern(self, candle: pd.Series) -> float:
        """Analyze individual candle for reversal patterns."""
        open_price = candle['Open'] if 'Open' in candle.index else candle['Close']
        high = candle['High']
        low = candle['Low']
        close = candle['Close']
        
        body_size = abs(close - open_price)
        total_range = high - low
        
        if total_range == 0:
            return 0
        
        # Hammer pattern (long lower wick, small body)
        lower_wick = min(open_price, close) - low
        upper_wick = high - max(open_price, close)
        
        if (lower_wick > body_size * 2 and 
            upper_wick < body_size * 0.5 and
            body_size / total_range < 0.3):
            return 2.0  # Strong hammer pattern
        
        # Doji pattern (very small body)
        if body_size / total_range < 0.1:
            return 1.0  # Indecision/potential reversal
        
        # Long lower wick (partial hammer)
        if lower_wick > body_size:
            return 0.5  # Weak reversal signal
        
        return 0
    
    def _score_momentum_divergence(self, tech_data: Dict) -> float:
        """Score momentum divergence signals."""
        score = 0
        max_score = self.weights['momentum_divergence']
        
        # RSI bullish divergence
        if tech_data.get('rsi_bullish_divergence', False):
            score += 2  # Price making lower lows, RSI making higher lows
        
        # MACD bullish divergence
        if tech_data.get('macd_bullish_divergence', False):
            score += 2  # Hidden strength
        
        # Momentum slowing (exhaustion)
        if tech_data.get('momentum_slowing', False):
            score += 1  # Selling pressure diminishing
        
        return min(score, max_score)
    
    def _score_volume_reversal(self, volume_data: Dict) -> float:
        """Score volume pattern reversals and accumulation."""
        score = 0
        max_score = self.weights['volume_reversal']
        
        # Volume exhaustion pattern
        if volume_data.get('volume_exhaustion_detected', False):
            score += 2  # High volume decline followed by low volume
        
        # Accumulation pattern
        if volume_data.get('volume_classification') == 'accumulation':
            score += 2  # Smart money buying
        
        # Volume trend reversal
        volume_trend = volume_data.get('volume_trend', 'neutral')
        if volume_trend == 'increasing_on_bounce':
            score += 1  # Volume supporting price recovery
        
        return min(score, max_score)
    
    def _identify_reversal_signals(self, tech_data: Dict, volume_data: Dict, df: pd.DataFrame) -> Dict:
        """Identify and catalog specific reversal signals."""
        signals = {
            'macd_bullish_cross': tech_data.get('macd_bullish_crossover_recent', False),
            'rsi_divergence': tech_data.get('rsi_bullish_divergence', False),
            'hammer_pattern': self._detect_recent_hammer(df),
            'volume_exhaustion': volume_data.get('volume_exhaustion_detected', False),
            'momentum_slowing': tech_data.get('momentum_slowing', False),
            'capitulation_signal': volume_data.get('volume_classification') == 'capitulation'
        }
        
        # Count active signals
        signals['total_signals'] = sum(1 for signal in signals.values() if isinstance(signal, bool) and signal)
        
        return signals
    
    def _detect_recent_hammer(self, df: pd.DataFrame) -> bool:
        """Detect hammer pattern in last 3 sessions."""
        if len(df) < 1:
            return False
        
        recent_candles = df.tail(3)
        
        for i in range(len(recent_candles)):
            candle = recent_candles.iloc[i]
            pattern_score = self._analyze_candle_pattern(candle)
            if pattern_score >= 1.5:  # Strong reversal pattern
                return True
        
        return False
    
    def _assess_reversal_strength(self, score: float) -> str:
        """Assess the overall strength of reversal signals."""
        score_pct = score / self.max_points
        
        if score_pct >= 0.8:
            return 'strong'
        elif score_pct >= 0.6:
            return 'moderate'
        elif score_pct >= 0.4:
            return 'weak'
        else:
            return 'minimal'
    
    def _get_spark_grade(self, score: float) -> str:
        """Convert reversal score to letter grade."""
        if score >= self.max_points * 0.85:
            return 'A'
        elif score >= self.max_points * 0.70:
            return 'B'
        elif score >= self.max_points * 0.55:
            return 'C'
        elif score >= self.max_points * 0.40:
            return 'D'
        else:
            return 'F'
    
    def _empty_reversal_details(self) -> Dict:
        """Return empty reversal details when calculation fails."""
        return {
            'macd_signals': 0,
            'candle_patterns': 0,
            'momentum_divergence': 0,
            'volume_reversal': 0,
            'total_reversal_score': 0,
            'reversal_signals': {
                'macd_bullish_cross': False,
                'rsi_divergence': False,
                'hammer_pattern': False,
                'volume_exhaustion': False,
                'momentum_slowing': False,
                'capitulation_signal': False,
                'total_signals': 0
            },
            'reversal_strength': 'minimal',
            'spark_grade': 'F'
        } 