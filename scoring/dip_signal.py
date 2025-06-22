"""
Dip Signal scorer - Second layer of the 4-layer methodology.

Weight: 40-50% of final score (the meat of the scoring)
Purpose: "Is this a temporary bruise or a structural break?"

Uses Phase 1 TechnicalIndicators and VolumeAnalyzer to evaluate:
- Distance from 52-week high (sweet spot: 15-40% drop)
- RSI oversold conditions (< 30, ideally < 25)
- Volume spike patterns (1.5x-3x average volume)
- Moving average positioning (SMA50, SMA200)

This is the core dip detection layer that identifies genuine buying opportunities.
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


class DipSignal:
    """
    Dip Signal scoring layer - the core dip detection engine.
    
    Implements the "Dip Signal" from ScoresandMetrics.txt methodology:
    "Measure how far and how fast it's fallen"
    
    Score Range: 0-45 points (45% of 100-point scale)
    Sweet Spots: 15-40% drop, RSI 25-35, volume 1.5x-3x
    """
    
    def __init__(self, max_points: int = 45):
        self.max_points = max_points
        self.tech_indicators = TechnicalIndicators()
        self.volume_analyzer = VolumeAnalyzer()
        
        # Dip signal weights (total = max_points)
        self.weights = {
            'drop_severity': 15,        # % below 52-week high
            'oversold_rsi': 12,         # RSI levels and positioning
            'volume_signature': 10,     # Volume spike patterns
            'sma_positioning': 8        # Moving average breaks
        }
    
    def score_dip_signal(self, df: pd.DataFrame, ticker: str, enhanced_data: Dict = None) -> Tuple[float, Dict]:
        """
        Score the dip signal for a ticker.
        
        Args:
            df: Historical price/volume DataFrame
            ticker: Stock ticker symbol
            enhanced_data: Optional pre-fetched enhanced data from Phase 1
            
        Returns:
            Tuple of (dip_score, dip_details)
        """
        try:
            # Get technical and volume data (from Phase 1 or fresh)
            if enhanced_data and 'enhanced_tech' in enhanced_data:
                tech_data = enhanced_data['enhanced_tech']
                volume_data = enhanced_data.get('enhanced_volume', {})
            else:
                tech_data = self.tech_indicators.calculate_all_indicators(df, ticker)
                volume_data = self.volume_analyzer.analyze_volume_patterns(df, ticker)
            
            # Calculate each dip component
            drop_score = self._score_drop_severity(tech_data)
            rsi_score = self._score_oversold_rsi(tech_data)
            volume_score = self._score_volume_signature(volume_data)
            sma_score = self._score_sma_positioning(tech_data)
            
            # Total dip score
            total_score = drop_score + rsi_score + volume_score + sma_score
            
            # Determine dip quality classification
            dip_classification = self._classify_dip_quality(tech_data, volume_data)
            
            dip_details = {
                'drop_severity': drop_score,
                'oversold_rsi': rsi_score,
                'volume_signature': volume_score,
                'sma_positioning': sma_score,
                'total_dip_score': total_score,
                'dip_classification': dip_classification,
                'in_sweet_spot': self._is_in_sweet_spot(tech_data, volume_data),
                'dip_grade': self._get_dip_grade(total_score),
                'key_levels': self._extract_key_levels(tech_data)
            }
            
            return total_score, dip_details
            
        except Exception as e:
            print(f"Error scoring dip signal for {ticker}: {e}")
            return 0, self._empty_dip_details()
    
    def _score_drop_severity(self, tech_data: Dict) -> float:
        """Score the severity and quality of the price drop."""
        score = 0
        max_score = self.weights['drop_severity']
        
        # Primary metric: % below 52-week high
        drop_52w = tech_data.get('percent_below_52w_high', 0)
        
        if drop_52w >= 15 and drop_52w <= 40:
            # Sweet spot: 15-40% drop gets maximum points
            if drop_52w >= 20 and drop_52w <= 30:
                score += max_score  # Perfect dip zone
            else:
                score += max_score * 0.85  # Good dip zone
        elif drop_52w > 40 and drop_52w <= 60:
            score += max_score * 0.6  # Deeper dip, more risk
        elif drop_52w > 60:
            score += max_score * 0.3  # Too deep, structural concerns
        elif drop_52w >= 10:
            score += max_score * 0.4  # Minor dip
        
        # Bonus for consistent drop pattern (not erratic)
        drop_consistency = self._calculate_drop_consistency(tech_data)
        if drop_consistency > 0.7:
            score += 2  # Bonus for smooth decline
        
        return min(score, max_score)
    
    def _score_oversold_rsi(self, tech_data: Dict) -> float:
        """Score RSI oversold conditions and exhaustion signals."""
        score = 0
        max_score = self.weights['oversold_rsi']
        
        # RSI(14) primary signal
        rsi_14 = tech_data.get('rsi_14', 50)
        
        if rsi_14 < 25:
            score += 6  # Extreme oversold (sweet spot)
        elif rsi_14 < 30:
            score += 5  # Classic oversold
        elif rsi_14 < 35:
            score += 3  # Approaching oversold
        elif rsi_14 < 40:
            score += 1  # Mild weakness
        
        # RSI(5) for short-term exhaustion
        rsi_5 = tech_data.get('rsi_5', 50)
        
        if rsi_5 < 20:
            score += 3  # Short-term capitulation
        elif rsi_5 < 30:
            score += 2  # Short-term oversold
        
        # RSI divergence bonus
        if tech_data.get('rsi_bullish_divergence', False):
            score += 3  # Hidden strength
        
        return min(score, max_score)
    
    def _score_volume_signature(self, volume_data: Dict) -> float:
        """Score volume patterns and spike signatures."""
        score = 0
        max_score = self.weights['volume_signature']
        
        # Volume ratio (current vs average)
        volume_ratio = volume_data.get('volume_ratio_current', 1.0)
        
        if volume_ratio >= 1.5 and volume_ratio <= 3.0:
            # Sweet spot: 1.5x-3x volume spike
            if volume_ratio >= 2.0 and volume_ratio <= 2.5:
                score += 6  # Perfect volume signature
            else:
                score += 5  # Good volume spike
        elif volume_ratio > 3.0:
            score += 3  # Too much volume, might be distribution
        elif volume_ratio >= 1.2:
            score += 2  # Moderate increase
        
        # Volume trend and pattern
        if volume_data.get('volume_classification') == 'capitulation':
            score += 4  # Selling climax signal
        elif volume_data.get('volume_classification') == 'accumulation':
            score += 2  # Smart money buying
        
        return min(score, max_score)
    
    def _score_sma_positioning(self, tech_data: Dict) -> float:
        """Score moving average positioning and breaks."""
        score = 0
        max_score = self.weights['sma_positioning']
        
        # Price vs SMA positioning
        price_vs_sma50 = tech_data.get('price_vs_sma50', 0)
        price_vs_sma200 = tech_data.get('price_vs_sma200', 0)
        
        # Ideal: below SMA50 but above SMA200 (temporary pullback)
        if price_vs_sma50 < 0 and price_vs_sma200 > 0:
            score += 4  # Perfect dip setup
        elif price_vs_sma50 < 0 and price_vs_sma200 > -0.1:
            score += 3  # Near-term support break
        elif price_vs_sma50 < 0:
            score += 2  # Below both SMAs
        
        # SMA slope analysis (trend context)
        sma50_slope = tech_data.get('sma50_slope', 0)
        sma200_slope = tech_data.get('sma200_slope', 0)
        
        if sma200_slope > 0:  # Long-term uptrend intact
            score += 2
        if sma50_slope < 0 and sma200_slope > 0:  # Short-term pullback in uptrend
            score += 2
        
        return min(score, max_score)
    
    def _classify_dip_quality(self, tech_data: Dict, volume_data: Dict) -> str:
        """Classify the overall dip quality."""
        drop_52w = tech_data.get('percent_below_52w_high', 0)
        rsi_14 = tech_data.get('rsi_14', 50)
        volume_ratio = volume_data.get('volume_ratio_current', 1.0)
        
        # Premium dip conditions
        if (15 <= drop_52w <= 40 and 
            rsi_14 < 30 and 
            1.5 <= volume_ratio <= 3.0):
            return 'premium_dip'
        
        # Quality dip
        elif (10 <= drop_52w <= 50 and 
              rsi_14 < 35 and 
              volume_ratio >= 1.2):
            return 'quality_dip'
        
        # Mild dip
        elif drop_52w >= 5 and rsi_14 < 40:
            return 'mild_dip'
        
        # Deep value (risky)
        elif drop_52w > 50:
            return 'deep_value'
        
        # No clear dip
        else:
            return 'no_dip'
    
    def _is_in_sweet_spot(self, tech_data: Dict, volume_data: Dict) -> bool:
        """Check if the dip meets all sweet spot criteria."""
        drop_52w = tech_data.get('percent_below_52w_high', 0)
        rsi_14 = tech_data.get('rsi_14', 50)
        volume_ratio = volume_data.get('volume_ratio_current', 1.0)
        
        return (15 <= drop_52w <= 40 and 
                25 <= rsi_14 <= 35 and 
                1.5 <= volume_ratio <= 3.0)
    
    def _calculate_drop_consistency(self, tech_data: Dict) -> float:
        """Calculate how consistent/smooth the decline has been."""
        # This would analyze the volatility during the decline
        # For now, return a placeholder based on available data
        drop_from_high = tech_data.get('percent_below_52w_high', 0)
        drop_from_20d = tech_data.get('percent_below_20d_high', 0)
        
        if abs(drop_from_high - drop_from_20d) < 5:
            return 0.8  # Consistent decline
        else:
            return 0.5  # More erratic
    
    def _extract_key_levels(self, tech_data: Dict) -> Dict:
        """Extract key technical levels from the data."""
        return {
            'current_price': tech_data.get('current_price'),
            'sma_50': tech_data.get('sma_50'),
            'sma_200': tech_data.get('sma_200'),
            '52_week_high': tech_data.get('price_52w_high'),
            '52_week_low': tech_data.get('price_52w_low'),
            'resistance_level': tech_data.get('sma_50'),  # SMA50 often acts as resistance
            'support_level': tech_data.get('price_52w_low')
        }
    
    def _get_dip_grade(self, score: float) -> str:
        """Convert dip score to letter grade."""
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
    
    def _empty_dip_details(self) -> Dict:
        """Return empty dip details when calculation fails."""
        return {
            'drop_severity': 0,
            'oversold_rsi': 0,
            'volume_signature': 0,
            'sma_positioning': 0,
            'total_dip_score': 0,
            'dip_classification': 'no_data',
            'in_sweet_spot': False,
            'dip_grade': 'F',
            'key_levels': {}
        } 