"""
Fundamental data collector for enhanced dip analysis.

Conservative implementation that builds on existing yahooquery integration
and avoids API rate limits by using cached data where possible.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
import time
import sys
import os

# Add parent directory to path to import existing utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use the same API that works throughout the system
from yahooquery import Ticker


class FundamentalDataCollector:
    """
    Conservative fundamental data collector that focuses on key metrics
    from the methodology without overwhelming API calls.
    
    Key metrics per ScoresandMetrics.txt:
    - Free Cash Flow trends
    - P/E ratios (reasonable valuation)
    - Debt/EBITDA ratios
    - Quality gate fundamentals
    """
    
    def __init__(self):
        self.cache = {}
        self.rate_limit_delay = 1.0  # 1 second between API calls
        self.last_api_call = 0
    
    def get_fundamental_metrics(self, ticker: str, use_cache: bool = True) -> Dict:
        """
        Get fundamental metrics for a ticker using yahooquery (same as the working system).
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary with fundamental metrics
        """
        if use_cache and ticker in self.cache:
            return self.cache[ticker]
        
        try:
            # Rate limiting
            current_time = time.time()
            if current_time - self.last_api_call < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - (current_time - self.last_api_call))
            
            # Use yahooquery like the rest of the system (this works!)
            stock = Ticker(ticker)
            
            # Get fundamental data from multiple endpoints
            summary_detail = stock.summary_detail.get(ticker, {})
            financial_data = stock.financial_data.get(ticker, {})
            key_stats = stock.key_stats.get(ticker, {})
            company_info = stock.asset_profile.get(ticker, {})
            
            self.last_api_call = time.time()
            
            # Combine all data sources
            combined_info = {**summary_detail, **financial_data, **key_stats, **company_info}
            
            if not combined_info:
                return self._empty_fundamentals()
            
            # Extract key fundamental metrics
            fundamentals = self._extract_key_metrics(combined_info, ticker)
            
            # Cache the results
            self.cache[ticker] = fundamentals
            
            return fundamentals
            
        except Exception as e:
            print(f"Error fetching fundamentals for {ticker}: {e}")
            return self._empty_fundamentals()
    
    def _extract_key_metrics(self, info: Dict, ticker: str) -> Dict:
        """Extract key fundamental metrics from yahooquery data."""
        try:
            # Quality Gate metrics (30-40% of methodology)
            fundamentals = {
                # Cash flow metrics (from financial_data)
                'free_cash_flow': self._safe_get(info, 'freeCashflow'),
                'operating_cash_flow': self._safe_get(info, 'operatingCashflow'),
                'total_cash': self._safe_get(info, 'totalCash'),
                
                # Valuation metrics (from summary_detail)
                'pe_ratio': self._safe_get(info, 'trailingPE'),
                'forward_pe': self._safe_get(info, 'forwardPE'),
                'peg_ratio': self._safe_get(info, 'pegRatio'),
                'price_to_book': self._safe_get(info, 'priceToBook'),
                
                # Debt and financial strength (from financial_data)
                'total_debt': self._safe_get(info, 'totalDebt'),
                'debt_to_equity': self._safe_get(info, 'debtToEquity'),
                'current_ratio': self._safe_get(info, 'currentRatio'),
                'quick_ratio': self._safe_get(info, 'quickRatio'),
                
                # Profitability (from financial_data)
                'gross_margins': self._safe_get(info, 'grossMargins'),
                'operating_margins': self._safe_get(info, 'operatingMargins'),
                'profit_margins': self._safe_get(info, 'profitMargins'),
                'return_on_equity': self._safe_get(info, 'returnOnEquity'),
                'return_on_assets': self._safe_get(info, 'returnOnAssets'),
                
                # Growth metrics (from financial_data)
                'revenue_growth': self._safe_get(info, 'revenueGrowth'),
                'earnings_growth': self._safe_get(info, 'earningsGrowth'),
                
                # Dividend metrics (from summary_detail)
                'dividend_yield': self._safe_get(info, 'dividendYield'),
                'payout_ratio': self._safe_get(info, 'payoutRatio'),
                
                # Market metrics (from summary_detail)
                'beta': self._safe_get(info, 'beta'),
                'market_cap': self._safe_get(info, 'marketCap'),
                
                # Sector information (from asset_profile)
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                
                # Additional metrics (from key_stats)
                'shares_outstanding': self._safe_get(info, 'sharesOutstanding'),
                'float_shares': self._safe_get(info, 'floatShares'),
                'short_ratio': self._safe_get(info, 'shortRatio'),
                'short_percent_float': self._safe_get(info, 'shortPercentOfFloat'),
                
                # Alternative field names that yahooquery might use
                'enterprise_value': self._safe_get(info, 'enterpriseValue'),
                'ebitda': self._safe_get(info, 'ebitda'),
                'total_revenue': self._safe_get(info, 'totalRevenue'),
                
                # Metadata
                'ticker': ticker,
                'last_updated': pd.Timestamp.now().isoformat()
            }
            
            # Calculate derived metrics
            fundamentals.update(self._calculate_derived_metrics(fundamentals))
            
            return fundamentals
            
        except Exception as e:
            print(f"Error extracting metrics for {ticker}: {e}")
            return self._empty_fundamentals()
    
    def _calculate_derived_metrics(self, fundamentals: Dict) -> Dict:
        """Calculate derived fundamental metrics."""
        derived = {}
        
        try:
            # Debt/EBITDA approximation (if EBITDA not available, use operating cash flow)
            total_debt = fundamentals.get('total_debt')
            operating_cf = fundamentals.get('operating_cash_flow')
            
            if total_debt and operating_cf and operating_cf > 0:
                derived['debt_to_operating_cf'] = total_debt / operating_cf
            else:
                derived['debt_to_operating_cf'] = None
            
            # Free Cash Flow yield
            free_cash_flow = fundamentals.get('free_cash_flow')
            market_cap = fundamentals.get('market_cap')
            
            if free_cash_flow and market_cap and market_cap > 0:
                derived['fcf_yield'] = free_cash_flow / market_cap
            else:
                derived['fcf_yield'] = None
            
            # Quality Score (0-100) based on methodology
            derived['quality_score'] = self._calculate_quality_score(fundamentals)
            
            # Financial Strength Score (0-100)
            derived['financial_strength'] = self._calculate_financial_strength(fundamentals)
            
            # Valuation Score (0-100, higher = more attractive)
            derived['valuation_score'] = self._calculate_valuation_score(fundamentals)
            
        except Exception as e:
            print(f"Error calculating derived metrics: {e}")
        
        return derived
    
    def _calculate_quality_score(self, fundamentals: Dict) -> float:
        """Calculate quality score based on methodology (0-100)."""
        score = 0
        max_score = 100
        
        try:
            # Free cash flow positive (20 points)
            fcf = fundamentals.get('free_cash_flow')
            if fcf and fcf > 0:
                score += 20
            
            # Operating margins > 10% (20 points)
            op_margins = fundamentals.get('operating_margins')
            if op_margins and op_margins > 0.10:
                score += 20
            elif op_margins and op_margins > 0.05:
                score += 10
            
            # Return on equity > 15% (20 points)
            roe = fundamentals.get('return_on_equity')
            if roe and roe > 0.15:
                score += 20
            elif roe and roe > 0.10:
                score += 10
            
            # Current ratio > 1.5 (15 points)
            current_ratio = fundamentals.get('current_ratio')
            if current_ratio and current_ratio > 1.5:
                score += 15
            elif current_ratio and current_ratio > 1.0:
                score += 8
            
            # Debt to equity < 0.5 (15 points)
            debt_equity = fundamentals.get('debt_to_equity')
            if debt_equity is not None:
                if debt_equity < 0.3:
                    score += 15
                elif debt_equity < 0.5:
                    score += 10
                elif debt_equity < 1.0:
                    score += 5
            
            # Revenue growth positive (10 points)
            rev_growth = fundamentals.get('revenue_growth')
            if rev_growth and rev_growth > 0:
                score += 10
            
        except Exception:
            pass
        
        return min(score, max_score)
    
    def _calculate_financial_strength(self, fundamentals: Dict) -> float:
        """Calculate financial strength score (0-100)."""
        score = 0
        
        try:
            # Cash vs debt ratio
            total_cash = fundamentals.get('total_cash', 0)
            total_debt = fundamentals.get('total_debt', 0)
            
            if total_debt == 0:
                score += 30  # No debt is excellent
            elif total_cash > total_debt:
                score += 25  # More cash than debt
            elif total_cash > total_debt * 0.5:
                score += 15  # Decent cash coverage
            
            # Profitability consistency
            profit_margins = fundamentals.get('profit_margins')
            if profit_margins and profit_margins > 0.10:
                score += 25
            elif profit_margins and profit_margins > 0.05:
                score += 15
            elif profit_margins and profit_margins > 0:
                score += 5
            
            # Operating efficiency
            op_margins = fundamentals.get('operating_margins')
            gross_margins = fundamentals.get('gross_margins')
            
            if op_margins and gross_margins:
                efficiency = op_margins / gross_margins if gross_margins > 0 else 0
                if efficiency > 0.3:
                    score += 20
                elif efficiency > 0.2:
                    score += 15
                elif efficiency > 0.1:
                    score += 10
            
            # Growth sustainability
            rev_growth = fundamentals.get('revenue_growth', 0)
            earnings_growth = fundamentals.get('earnings_growth', 0)
            
            if rev_growth > 0 and earnings_growth > 0:
                score += 15
            elif rev_growth > 0 or earnings_growth > 0:
                score += 8
            
            # Dividend sustainability
            payout_ratio = fundamentals.get('payout_ratio')
            if payout_ratio is not None and payout_ratio < 0.6:
                score += 10
            
        except Exception:
            pass
        
        return min(score, 100)
    
    def _calculate_valuation_score(self, fundamentals: Dict) -> float:
        """Calculate valuation attractiveness score (0-100)."""
        score = 0
        
        try:
            # P/E ratio scoring
            pe = fundamentals.get('pe_ratio')
            if pe:
                if pe < 10:
                    score += 30
                elif pe < 15:
                    score += 25
                elif pe < 20:
                    score += 20
                elif pe < 25:
                    score += 10
            
            # PEG ratio scoring
            peg = fundamentals.get('peg_ratio')
            if peg:
                if peg < 1.0:
                    score += 20
                elif peg < 1.5:
                    score += 15
                elif peg < 2.0:
                    score += 10
            
            # Price to book
            pb = fundamentals.get('price_to_book')
            if pb:
                if pb < 1.0:
                    score += 15
                elif pb < 2.0:
                    score += 10
                elif pb < 3.0:
                    score += 5
            
            # FCF yield
            fcf_yield = fundamentals.get('fcf_yield')
            if fcf_yield:
                if fcf_yield > 0.08:  # 8%+ FCF yield
                    score += 20
                elif fcf_yield > 0.05:  # 5%+ FCF yield
                    score += 15
                elif fcf_yield > 0.03:  # 3%+ FCF yield
                    score += 10
            
            # Dividend yield bonus
            div_yield = fundamentals.get('dividend_yield')
            if div_yield and div_yield > 0.03:  # 3%+ dividend
                score += 15
            
        except Exception:
            pass
        
        return min(score, 100)
    
    def _safe_get(self, data: Dict, key: str) -> Any:
        """Safely get a value from dict, handling various edge cases."""
        try:
            value = data.get(key)
            if value is None:
                return None
            if isinstance(value, str) and value.lower() in ['n/a', 'none', '']:
                return None
            if isinstance(value, (int, float)) and pd.isna(value):
                return None
            return value
        except Exception:
            return None
    
    def _empty_fundamentals(self) -> Dict:
        """Return empty fundamentals structure when data unavailable."""
        return {
            'free_cash_flow': None, 'operating_cash_flow': None, 'total_cash': None,
            'pe_ratio': None, 'forward_pe': None, 'peg_ratio': None, 'price_to_book': None,
            'total_debt': None, 'debt_to_equity': None, 'current_ratio': None, 'quick_ratio': None,
            'gross_margins': None, 'operating_margins': None, 'profit_margins': None,
            'return_on_equity': None, 'return_on_assets': None, 'revenue_growth': None,
            'earnings_growth': None, 'dividend_yield': None, 'payout_ratio': None,
            'beta': None, 'market_cap': None, 'sector': '', 'industry': '',
            'shares_outstanding': None, 'float_shares': None, 'short_ratio': None,
            'short_percent_float': None, 'ticker': '', 'last_updated': '',
            'debt_to_operating_cf': None, 'fcf_yield': None, 'quality_score': 0,
            'financial_strength': 0, 'valuation_score': 0
        } 