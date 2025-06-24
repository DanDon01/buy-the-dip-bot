"""
Risk Modifiers - Fourth layer of the 4-layer methodology.

Weight: ±10% of final score (additive/subtractive)
Purpose: "What's the market context? Are there external risks?"

Uses Phase 1 data to evaluate:
- Sector momentum (is the sector hot or cold?)
- Volatility regime (VIX levels and beta)
- Liquidity and short squeeze risk
- Macro event timing (Fed meetings, earnings)

This layer provides a final adjustment based on the broader market environment.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path to import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use yahooquery like the rest of the system
from yahooquery import Ticker

# Add parent directory to path to import Phase 1 collectors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.fundamental_data import FundamentalDataCollector
from collectors.technical_indicators import TechnicalIndicators


class RiskModifiers:
    """
    Risk Modifiers scoring layer - adjusts score based on market context.
    
    Score Range: -10 to +10 points (additive/subtractive)
    """
    
    def __init__(self, max_adjustment: int = 10):
        self.max_adjustment = max_adjustment
        self.fundamental_collector = FundamentalDataCollector()
        self.tech_indicators = TechnicalIndicators()
        
        # Risk modifier weights (can go positive or negative)
        self.weights = {
            'sector_momentum': 4,
            'volatility_regime': 3,
            'liquidity_risk': 2,
            'macro_timing': 1
        }

    def score_risk_modifiers(self, ticker: str, enhanced_data: Dict = None) -> Tuple[float, Dict]:
        """
        Score risk modifiers for a ticker.
        """
        try:
            # THE FIX: This layer uses data from both the main record and enhanced_tech
            stock_data = enhanced_data.get('ticker_data', {})
            tech_data = enhanced_data.get('enhanced_tech', {})
            
            # Pass the correct data objects to the sub-methods
            sector_adj = self._assess_sector_momentum(stock_data)
            volatility_adj = self._assess_volatility_regime(stock_data)
            liquidity_adj = self._assess_liquidity_risk(stock_data)
            macro_adj = self._assess_macro_timing()
            
            total_adjustment = sector_adj + volatility_adj + liquidity_adj + macro_adj
            total_adjustment = max(-self.max_adjustment, min(self.max_adjustment, total_adjustment))
            
            risk_details = {
                'sector_momentum': sector_adj,
                'volatility_regime': volatility_adj,
                'liquidity_risk': liquidity_adj,
                'macro_timing': macro_adj,
                'total_risk_adjustment': total_adjustment,
                'risk_level': self._assess_risk_level(total_adjustment),
                'market_regime': self._detect_market_regime(),
                'adjustment_factors': self._explain_adjustments(sector_adj, volatility_adj, liquidity_adj, macro_adj)
            }
            
            return total_adjustment, risk_details
            
        except Exception as e:
            print(f"Error scoring risk modifiers for {ticker}: {e}")
            return 0, self._empty_risk_details()

    def _assess_sector_momentum(self, stock_data: Dict) -> float:
        """Assess sector momentum. For now, this is a placeholder."""
        return 0.0

    def _assess_volatility_regime(self, stock_data: Dict) -> float:
        """Assess volatility regime based on beta."""
        adjustment = 0.0
        max_adj = self.weights['volatility_regime']
        beta = stock_data.get('beta')
        
        # In a real scenario, we'd check VIX. For now, just use beta.
        if beta:
            if beta > 1.5: adjustment -= max_adj * 0.8
            elif beta < 0.8: adjustment += max_adj * 0.4
                
        return adjustment

    def _assess_liquidity_risk(self, stock_data: Dict) -> float:
        """Assess liquidity and short squeeze risks."""
        adjustment = 0.0
        max_adj = self.weights['liquidity_risk']
        short_float = stock_data.get('short_percent_of_float')
        
        if short_float:
            if short_float > 0.20: adjustment -= max_adj
            elif short_float > 0.15: adjustment -= max_adj * 0.6
            elif short_float < 0.05: adjustment += max_adj * 0.4
                
        return adjustment

    def _assess_macro_timing(self) -> float:
        """Assess macro event timing risks."""
        return 0.0

    def _assess_risk_level(self, adjustment: float) -> str:
        """Assess overall risk level based on adjustment."""
        if adjustment <= -5: return 'high_risk'
        elif adjustment <= -2: return 'elevated_risk'
        elif adjustment >= 5: return 'favorable'
        elif adjustment >= 2: return 'slightly_favorable'
        else: return 'neutral'

    def _detect_market_regime(self) -> str:
        """Detect current market regime (e.g., bull, bear, neutral). Placeholder."""
        return 'neutral'

    def _explain_adjustments(self, sector_adj: float, volatility_adj: float, liquidity_adj: float, macro_adj: float) -> Dict:
        """Explain the reasoning behind adjustments."""
        explanations = {}
        if abs(sector_adj) > 0.5: explanations['sector'] = 'strong' if sector_adj > 0 else 'weak'
        if abs(volatility_adj) > 0.5: explanations['volatility'] = 'favorable' if volatility_adj > 0 else 'unfavorable'
        if abs(liquidity_adj) > 0.5: explanations['liquidity'] = 'clean' if liquidity_adj > 0 else 'risky'
        if abs(macro_adj) > 0.2: explanations['macro'] = 'supportive' if macro_adj > 0 else 'cautionary'
        return explanations

    def _empty_risk_details(self) -> Dict:
        """Return empty risk details when calculation fails."""
        return {
            'sector_momentum': 0, 'volatility_regime': 0, 'liquidity_risk': 0, 'macro_timing': 0,
            'total_risk_adjustment': 0, 'risk_level': 'unknown', 'market_regime': 'unknown',
            'adjustment_factors': {}
        } 