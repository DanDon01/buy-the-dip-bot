"""
Risk Modifiers scorer - Fourth layer of the 4-layer methodology.

Weight: ±10% adjustment to final score
Purpose: "Should I nudge this up or down given the backdrop?"

Adjusts scores based on market context and risk factors:
- Sector momentum and rotation patterns
- Beta and volatility in high VIX environments
- Short float and squeeze potential
- Macro event timing (Fed decisions, earnings)
- Market regime detection

This layer prevents accidentally buying into macro traps or meme-stock chaos.
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


class RiskModifiers:
    """
    Risk Modifiers scoring layer - market context adjustments.
    
    Implements the "Risk/Context Mods" from ScoresandMetrics.txt methodology:
    "Adjust for sector, liquidity, macro noise"
    
    Score Range: -10 to +10 points (±10% adjustment)
    Focus: Market context, risk factors, and macro backdrop
    """
    
    def __init__(self, max_adjustment: int = 10):
        self.max_adjustment = max_adjustment
        
        # Risk modifier weights (can go positive or negative)
        self.weights = {
            'sector_momentum': 4,       # Sector rotation and strength
            'volatility_regime': 3,     # VIX levels and beta impact
            'liquidity_risk': 2,        # Short float and volume
            'macro_timing': 1           # Fed decisions, earnings proximity
        }
    
    def score_risk_modifiers(self, ticker: str, enhanced_data: Dict = None) -> Tuple[float, Dict]:
        """
        Score risk modifiers for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            enhanced_data: Optional pre-fetched enhanced data from Phase 1
            
        Returns:
            Tuple of (risk_adjustment, risk_details)
        """
        try:
            # Calculate each risk component
            sector_adj = self._assess_sector_momentum(ticker, enhanced_data)
            volatility_adj = self._assess_volatility_regime(ticker, enhanced_data)
            liquidity_adj = self._assess_liquidity_risk(ticker, enhanced_data)
            macro_adj = self._assess_macro_timing()
            
            # Total risk adjustment (can be negative)
            total_adjustment = sector_adj + volatility_adj + liquidity_adj + macro_adj
            
            # Cap the adjustment within bounds
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
    
    def _assess_sector_momentum(self, ticker: str, enhanced_data: Dict = None) -> float:
        """Assess sector momentum and rotation patterns."""
        adjustment = 0
        max_adj = self.weights['sector_momentum']
        
        try:
            # Get sector information
            sector = self._get_stock_sector(ticker, enhanced_data)
            
            if sector:
                # Get sector ETF performance (simplified mapping)
                sector_etf = self._map_sector_to_etf(sector)
                
                if sector_etf:
                    sector_performance = self._get_sector_performance(sector_etf)
                    
                    # Positive adjustment for strong sectors
                    if sector_performance > 0.05:  # 5%+ outperformance
                        adjustment += max_adj
                    elif sector_performance > 0.02:  # 2%+ outperformance
                        adjustment += max_adj * 0.6
                    elif sector_performance < -0.05:  # 5%+ underperformance
                        adjustment -= max_adj * 0.8
                    elif sector_performance < -0.02:  # 2%+ underperformance
                        adjustment -= max_adj * 0.4
            
        except Exception as e:
            print(f"Error assessing sector momentum for {ticker}: {e}")
        
        return adjustment
    
    def _assess_volatility_regime(self, ticker: str, enhanced_data: Dict = None) -> float:
        """Assess volatility regime and beta impact."""
        adjustment = 0
        max_adj = self.weights['volatility_regime']
        
        try:
            # Get VIX level
            vix_level = self._get_vix_level()
            
            # Get stock beta
            beta = self._get_stock_beta(ticker, enhanced_data)
            
            # High VIX environment penalties
            if vix_level > 30:  # High volatility
                if beta and beta > 1.5:
                    adjustment -= max_adj  # High beta stocks suffer in volatile markets
                elif beta and beta > 1.2:
                    adjustment -= max_adj * 0.6
                elif beta and beta < 0.8:
                    adjustment += max_adj * 0.4  # Low beta defensive play
            elif vix_level < 15:  # Low volatility
                if beta and beta > 1.2:
                    adjustment += max_adj * 0.4  # High beta benefits in calm markets
            
        except Exception as e:
            print(f"Error assessing volatility regime for {ticker}: {e}")
        
        return adjustment
    
    def _assess_liquidity_risk(self, ticker: str, enhanced_data: Dict = None) -> float:
        """Assess liquidity and short squeeze risks."""
        adjustment = 0
        max_adj = self.weights['liquidity_risk']
        
        try:
            # Get short float data
            short_float = self._get_short_float(ticker, enhanced_data)
            
            if short_float is not None:
                if short_float > 0.20:  # 20%+ short float
                    adjustment -= max_adj  # High squeeze risk/manipulation
                elif short_float > 0.15:  # 15%+ short float
                    adjustment -= max_adj * 0.6
                elif short_float < 0.05:  # <5% short float
                    adjustment += max_adj * 0.4  # Clean setup
            
        except Exception as e:
            print(f"Error assessing liquidity risk for {ticker}: {e}")
        
        return adjustment
    
    def _assess_macro_timing(self) -> float:
        """Assess macro event timing risks."""
        adjustment = 0
        max_adj = self.weights['macro_timing']
        
        try:
            current_date = datetime.now()
            
            # Check for Fed meeting proximity (simplified - would need real calendar)
            # For now, apply general macro caution during certain periods
            
            # End of quarter/year caution
            if current_date.month in [3, 6, 9, 12] and current_date.day > 25:
                adjustment -= max_adj * 0.5  # End of quarter volatility
            
            # Earnings season caution (simplified)
            if current_date.month in [1, 4, 7, 10] and current_date.day < 15:
                adjustment -= max_adj * 0.3  # Earnings season volatility
        
        except Exception as e:
            print(f"Error assessing macro timing: {e}")
        
        return adjustment
    
    def _get_stock_sector(self, ticker: str, enhanced_data: Dict = None) -> Optional[str]:
        """Get stock sector information."""
        try:
            if enhanced_data and 'fundamentals' in enhanced_data:
                return enhanced_data['fundamentals'].get('sector')
            
            # Fallback to yahooquery (same as working system)
            stock = Ticker(ticker)
            asset_profile = stock.asset_profile.get(ticker, {})
            return asset_profile.get('sector')
        except:
            return None
    
    def _map_sector_to_etf(self, sector: str) -> Optional[str]:
        """Map sector name to corresponding ETF ticker."""
        sector_mapping = {
            'Technology': 'XLK',
            'Healthcare': 'XLV',
            'Financial Services': 'XLF',
            'Consumer Cyclical': 'XLY',
            'Consumer Defensive': 'XLP',
            'Energy': 'XLE',
            'Industrials': 'XLI',
            'Materials': 'XLB',
            'Real Estate': 'XLRE',
            'Utilities': 'XLU',
            'Communication Services': 'XLC'
        }
        return sector_mapping.get(sector)
    
    def _get_sector_performance(self, sector_etf: str) -> float:
        """Get recent sector performance vs SPY."""
        try:
            # Get 1-month performance for sector ETF vs SPY using yahooquery
            sector_ticker = Ticker(sector_etf)
            spy_ticker = Ticker('SPY')
            
            sector_history = sector_ticker.history(period='1mo')
            spy_history = spy_ticker.history(period='1mo')
            
            # Handle potential MultiIndex from yahooquery
            if isinstance(sector_history.index, pd.MultiIndex):
                sector_history = sector_history.xs(sector_etf, level=0, drop_level=True)
            if isinstance(spy_history.index, pd.MultiIndex):
                spy_history = spy_history.xs('SPY', level=0, drop_level=True)
            
            if len(sector_history) > 0 and len(spy_history) > 0:
                sector_return = (sector_history['close'].iloc[-1] / sector_history['close'].iloc[0]) - 1
                spy_return = (spy_history['close'].iloc[-1] / spy_history['close'].iloc[0]) - 1
                return sector_return - spy_return
            
            return 0
        except:
            return 0
    
    def _get_vix_level(self) -> float:
        """Get current VIX level."""
        try:
            vix = Ticker('^VIX')
            vix_data = vix.history(period='5d')
            
            # Handle potential MultiIndex from yahooquery
            if isinstance(vix_data.index, pd.MultiIndex):
                vix_data = vix_data.xs('^VIX', level=0, drop_level=True)
            
            if len(vix_data) > 0:
                return float(vix_data['close'].iloc[-1])
            return 20  # Default neutral level
        except:
            return 20
    
    def _get_stock_beta(self, ticker: str, enhanced_data: Dict = None) -> Optional[float]:
        """Get stock beta."""
        try:
            if enhanced_data and 'fundamentals' in enhanced_data:
                return enhanced_data['fundamentals'].get('beta')
            
            stock = Ticker(ticker)
            summary_detail = stock.summary_detail.get(ticker, {})
            return summary_detail.get('beta')
        except:
            return None
    
    def _get_short_float(self, ticker: str, enhanced_data: Dict = None) -> Optional[float]:
        """Get short float percentage."""
        try:
            if enhanced_data and 'fundamentals' in enhanced_data:
                return enhanced_data['fundamentals'].get('short_percent_float')
            
            stock = Ticker(ticker)
            key_stats = stock.key_stats.get(ticker, {})
            short_float = key_stats.get('shortPercentOfFloat')
            return short_float / 100 if short_float else None
        except:
            return None
    
    def _detect_market_regime(self) -> str:
        """Detect current market regime."""
        try:
            vix_level = self._get_vix_level()
            
            if vix_level > 30:
                return 'high_volatility'
            elif vix_level > 20:
                return 'elevated_volatility'
            elif vix_level < 15:
                return 'low_volatility'
            else:
                return 'normal_volatility'
        except:
            return 'unknown'
    
    def _assess_risk_level(self, adjustment: float) -> str:
        """Assess overall risk level based on adjustment."""
        if adjustment <= -5:
            return 'high_risk'
        elif adjustment <= -2:
            return 'elevated_risk'
        elif adjustment >= 5:
            return 'favorable'
        elif adjustment >= 2:
            return 'slightly_favorable'
        else:
            return 'neutral'
    
    def _explain_adjustments(self, sector_adj: float, volatility_adj: float, 
                           liquidity_adj: float, macro_adj: float) -> Dict:
        """Explain the reasoning behind adjustments."""
        explanations = {}
        
        if abs(sector_adj) > 0.5:
            explanations['sector'] = 'strong' if sector_adj > 0 else 'weak'
        
        if abs(volatility_adj) > 0.5:
            explanations['volatility'] = 'favorable' if volatility_adj > 0 else 'unfavorable'
        
        if abs(liquidity_adj) > 0.5:
            explanations['liquidity'] = 'clean' if liquidity_adj > 0 else 'risky'
        
        if abs(macro_adj) > 0.2:
            explanations['macro'] = 'supportive' if macro_adj > 0 else 'cautionary'
        
        return explanations
    
    def _empty_risk_details(self) -> Dict:
        """Return empty risk details when calculation fails."""
        return {
            'sector_momentum': 0,
            'volatility_regime': 0,
            'liquidity_risk': 0,
            'macro_timing': 0,
            'total_risk_adjustment': 0,
            'risk_level': 'unknown',
            'market_regime': 'unknown',
            'adjustment_factors': {}
        } 