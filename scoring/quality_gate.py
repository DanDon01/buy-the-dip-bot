"""
Quality Gate scorer - First layer of the 4-layer methodology.

Weight: 30-40% of final score
Purpose: "Is this a business I'd want to own at any price?"

Uses Phase 1 FundamentalDataCollector to evaluate:
- Free cash flow trends and cash management
- P/E ratios and valuation metrics  
- Debt management and financial strength
- Profitability and business quality

Filters out garbage before considering momentum factors.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import sys
import os

# Add parent directory to path to import Phase 1 collectors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.fundamental_data import FundamentalDataCollector


class QualityGate:
    """
    Quality Gate scoring layer - filters out poor businesses.
    
    Implements the "Quality Gate" from ScoresandMetrics.txt methodology:
    "Weed out garbage before you even think about momentum"
    
    Score Range: 0-35 points (35% of 100-point scale)
    Fail Threshold: Stocks failing 2+ quality checks are filtered out
    """
    
    def __init__(self, max_points: int = 35):
        self.max_points = max_points
        self.fundamental_collector = FundamentalDataCollector()
        
        # Quality check weights (total = max_points)
        self.weights = {
            'cash_flow_health': 8,      # FCF positive, growing
            'profitability': 8,         # Operating margins, ROE
            'debt_management': 7,       # Debt/equity, current ratio
            'valuation_sanity': 7,      # P/E reasonable vs sector
            'business_quality': 5       # Revenue growth, consistency
        }
    
    def score_quality_gate(self, ticker: str, enhanced_data: Dict = None) -> Tuple[float, Dict]:
        """
        Score the quality gate for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            enhanced_data: Optional pre-fetched enhanced data from Phase 1
            
        Returns:
            Tuple of (quality_score, quality_details)
        """
        try:
            # THE FIX: Get the nested stock_data record, which contains the fundamentals
            stock_data = enhanced_data.get('ticker_data', {})
            if not stock_data:
                return 0, self._empty_quality_details()
            
            # All sub-methods will now use the correct stock_data object
            cash_flow_score = self._score_cash_flow_health(stock_data)
            profitability_score = self._score_profitability(stock_data)
            debt_score = self._score_debt_management(stock_data)
            valuation_score = self._score_valuation_sanity(stock_data)
            business_score = self._score_business_quality(stock_data)
            
            total_score = (
                cash_flow_score + profitability_score + debt_score + 
                valuation_score + business_score
            )
            
            quality_checks = self._perform_quality_checks(stock_data)
            failed_checks = sum(1 for check in quality_checks.values() if not check)
            
            passes_quality_gate = failed_checks < 3
            
            quality_details = {
                'cash_flow_health': cash_flow_score,
                'profitability': profitability_score,
                'debt_management': debt_score,
                'valuation_sanity': valuation_score,
                'business_quality': business_score,
                'total_quality_score': total_score,
                'check_details': quality_checks,
                'failed_checks': failed_checks,
                'passes_quality_gate': passes_quality_gate,
                'quality_grade': self._get_quality_grade(total_score)
            }
            
            return total_score, quality_details
            
        except Exception as e:
            print(f"Error scoring quality gate for {ticker}: {e}")
            return 0, self._empty_quality_details()
    
    def _score_cash_flow_health(self, fundamentals: Dict) -> float:
        """Score cash flow health and cash management."""
        score = 0
        max_score = self.weights['cash_flow_health']
        
        fcf = fundamentals.get('free_cash_flow')
        op_cash_flow = fundamentals.get('operating_cash_flow')

        if fcf is not None and fcf > 0:
            score += 4
        elif fcf is not None and op_cash_flow is not None and fcf > -op_cash_flow * 0.1:
            score += 2
        
        total_cash = fundamentals.get('total_cash', 0)
        total_debt = fundamentals.get('total_debt', 0)
        
        if total_debt == 0:
            score += 4
        elif total_cash > total_debt:
            score += 3
        elif total_cash > total_debt * 0.5:
            score += 2
        elif total_cash > total_debt * 0.25:
            score += 1
        
        return min(score, max_score)
    
    def _score_profitability(self, fundamentals: Dict) -> float:
        """Score profitability metrics and efficiency."""
        score = 0
        max_score = self.weights['profitability']
        
        op_margins = fundamentals.get('operating_margins')
        if op_margins:
            if op_margins > 0.15: score += 4
            elif op_margins > 0.10: score += 3
            elif op_margins > 0.05: score += 2
            elif op_margins > 0: score += 1
        
        roe = fundamentals.get('return_on_equity')
        if roe:
            if roe > 0.20: score += 4
            elif roe > 0.15: score += 3
            elif roe > 0.10: score += 2
            elif roe > 0: score += 1
        
        return min(score, max_score)
    
    def _score_debt_management(self, fundamentals: Dict) -> float:
        """Score debt management and financial stability."""
        score = 0
        max_score = self.weights['debt_management']
        
        debt_equity = fundamentals.get('debt_to_equity')
        if debt_equity is not None:
            if debt_equity < 0.3: score += 4
            elif debt_equity < 0.5: score += 3
            elif debt_equity < 1.0: score += 2
            elif debt_equity < 2.0: score += 1
        else:
            score += 2
        
        current_ratio = fundamentals.get('current_ratio')
        if current_ratio:
            if current_ratio > 2.0: score += 3
            elif current_ratio > 1.5: score += 2
            elif current_ratio > 1.0: score += 1
        
        return min(score, max_score)
    
    def _score_valuation_sanity(self, fundamentals: Dict) -> float:
        """Score valuation reasonableness (not cheap, just not insane)."""
        score = 0
        max_score = self.weights['valuation_sanity']
        
        pe = fundamentals.get('pe')
        if pe:
            if pe < 10: score += 4
            elif pe < 20: score += 3
            elif pe < 30: score += 2
            elif pe < 50: score += 1
        else:
            score += 2
        
        pb = fundamentals.get('price_to_book')
        if pb:
            if pb < 2.0: score += 3
            elif pb < 5.0: score += 2
            elif pb < 10.0: score += 1
        else:
            score += 1
        
        return min(score, max_score)
    
    def _score_business_quality(self, fundamentals: Dict) -> float:
        """Score overall business quality and growth."""
        score = 0
        max_score = self.weights['business_quality']
        
        rev_growth = fundamentals.get('revenue_growth')
        if rev_growth:
            if rev_growth > 0.15: score += 3
            elif rev_growth > 0.05: score += 2
            elif rev_growth > 0: score += 1
        
        payout_ratio = fundamentals.get('payout_ratio')
        dividend_yield = fundamentals.get('dividend_yield')
        
        if dividend_yield and dividend_yield > 0:
            if payout_ratio and payout_ratio < 0.6: score += 2
            elif payout_ratio and payout_ratio < 0.8: score += 1
        else:
            score += 1
        
        return min(score, max_score)
    
    def _perform_quality_checks(self, fundamentals: Dict) -> Dict[str, bool]:
        """Perform binary quality checks for filtering."""
        checks = {}
        
        fcf = fundamentals.get('free_cash_flow', 0)
        op_cf = fundamentals.get('operating_cash_flow', 0)
        checks['positive_cash_flow'] = fcf > 0 or (op_cf and fcf > -op_cf * 0.2)

        debt_equity = fundamentals.get('debt_to_equity')
        checks['manageable_debt'] = debt_equity is None or debt_equity < 3.0
        
        profit_margins = fundamentals.get('profit_margins', 0)
        checks['profitable'] = profit_margins is None or profit_margins > 0
        
        current_ratio = fundamentals.get('current_ratio', 1.5)
        checks['adequate_liquidity'] = current_ratio is None or current_ratio > 0.8
        
        pe = fundamentals.get('pe')
        checks['sane_valuation'] = pe is None or pe < 100
        
        return checks
    
    def _get_quality_grade(self, score: float) -> str:
        """Convert quality score to letter grade."""
        if score >= self.max_points * 0.85: return 'A'
        elif score >= self.max_points * 0.70: return 'B'
        elif score >= self.max_points * 0.55: return 'C'
        elif score >= self.max_points * 0.40: return 'D'
        else: return 'F'
    
    def _empty_quality_details(self) -> Dict:
        """Return empty quality details when calculation fails."""
        return {
            'cash_flow_health': 0, 'profitability': 0, 'debt_management': 0,
            'valuation_sanity': 0, 'business_quality': 0,
            'total_quality_score': 0,
            'check_details': {
                'positive_cash_flow': False, 'manageable_debt': False,
                'profitable': False, 'adequate_liquidity': False, 'sane_valuation': False
            },
            'failed_checks': 5, 'passes_quality_gate': False, 'quality_grade': 'F'
        } 