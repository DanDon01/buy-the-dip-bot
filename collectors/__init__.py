"""
Data collectors package for enhanced buy-the-dip bot.

This package contains specialized collectors for different types of financial data:
- fundamental_data.py: Financial fundamentals (FCF, P/E, debt ratios)
- technical_indicators.py: Technical analysis indicators (RSI, MACD, SMA)
- volume_analysis.py: Volume pattern analysis and spike detection
- market_context.py: Sector trends and market context data

All collectors implement rate limiting to avoid API bans.
"""

from .technical_indicators import TechnicalIndicators
from .volume_analysis import VolumeAnalyzer
from .fundamental_data import FundamentalDataCollector

__all__ = ['TechnicalIndicators', 'VolumeAnalyzer', 'FundamentalDataCollector'] 