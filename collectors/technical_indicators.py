"""
Technical indicators collector for enhanced dip analysis.

Builds on existing RSI calculation in utils.py and adds new indicators
following the methodology from ScoresandMetrics.txt.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import sys
import os

# Add parent directory to path to import existing utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import calculate_rsi


class TechnicalIndicators:
    """
    Enhanced technical indicators calculator that builds on existing infrastructure.
    
    Focuses on dip-hunting indicators:
    - RSI levels (using existing function)
    - MACD crossover detection (enhanced)
    - SMA position analysis
    - Volume-based indicators
    """
    
    def __init__(self):
        self.cache = {}
    
    def calculate_all_indicators(self, stock_data: pd.DataFrame, ticker: str = "") -> Dict:
        """
        Calculate all technical indicators for a stock.
        
        Args:
            stock_data: DataFrame with OHLCV data
            ticker: Stock ticker for caching
            
        Returns:
            Dictionary with all technical indicators
        """
        if stock_data is None or len(stock_data) < 20:
            return self._empty_indicators()
        
        try:
            indicators = {}
            
            # Use existing RSI calculation from utils.py
            indicators.update(self._calculate_rsi_indicators(stock_data))
            
            # Enhanced MACD analysis
            indicators.update(self._calculate_macd_indicators(stock_data))
            
            # SMA position analysis (key for dip detection)
            indicators.update(self._calculate_sma_indicators(stock_data))
            
            # Price position analysis
            indicators.update(self._calculate_price_position(stock_data))
            
            # Momentum indicators
            indicators.update(self._calculate_momentum_indicators(stock_data))
            
            return indicators
            
        except Exception as e:
            print(f"Error calculating technical indicators for {ticker}: {e}")
            return self._empty_indicators()
    
    def _calculate_rsi_indicators(self, stock_data: pd.DataFrame) -> Dict:
        """Calculate RSI-based indicators using existing function."""
        try:
            # Use existing RSI function from utils.py
            rsi_14 = calculate_rsi(stock_data["Close"], period=14)
            rsi_5 = calculate_rsi(stock_data["Close"], period=5)
            
            current_rsi_14 = rsi_14.iloc[-1] if not rsi_14.empty else 50
            current_rsi_5 = rsi_5.iloc[-1] if not rsi_5.empty else 50
            
            return {
                'rsi_14': current_rsi_14,
                'rsi_5': current_rsi_5,
                'rsi_oversold': current_rsi_14 < 30,  # Classic oversold
                'rsi_extremely_oversold': current_rsi_14 < 25,  # Extreme oversold
                'rsi_divergence': self._check_rsi_divergence(stock_data, rsi_14)
            }
        except Exception:
            return {
                'rsi_14': 50, 'rsi_5': 50, 'rsi_oversold': False,
                'rsi_extremely_oversold': False, 'rsi_divergence': False
            }
    
    def _calculate_macd_indicators(self, stock_data: pd.DataFrame) -> Dict:
        """Enhanced MACD analysis for dip detection."""
        try:
            # Calculate MACD components
            ema_12 = stock_data["Close"].ewm(span=12, adjust=False).mean()
            ema_26 = stock_data["Close"].ewm(span=26, adjust=False).mean()
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            histogram = macd_line - signal_line
            
            # Current values
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_histogram = histogram.iloc[-1]
            
            # Bullish crossover detection (last 5 days)
            bullish_cross_recent = False
            for i in range(1, min(6, len(macd_line))):
                if (macd_line.iloc[-i-1] <= signal_line.iloc[-i-1] and 
                    macd_line.iloc[-i] > signal_line.iloc[-i]):
                    bullish_cross_recent = True
                    break
            
            return {
                'macd_line': current_macd,
                'macd_signal': current_signal,
                'macd_histogram': current_histogram,
                'macd_bullish_cross': bullish_cross_recent,
                'macd_above_signal': current_macd > current_signal,
                'macd_histogram_positive': current_histogram > 0
            }
        except Exception:
            return {
                'macd_line': 0, 'macd_signal': 0, 'macd_histogram': 0,
                'macd_bullish_cross': False, 'macd_above_signal': False,
                'macd_histogram_positive': False
            }
    
    def _calculate_sma_indicators(self, stock_data: pd.DataFrame) -> Dict:
        """SMA position analysis - key for dip identification."""
        try:
            current_price = stock_data["Close"].iloc[-1]
            
            # Calculate SMAs
            sma_20 = stock_data["Close"].rolling(window=20).mean().iloc[-1] if len(stock_data) >= 20 else None
            sma_50 = stock_data["Close"].rolling(window=50).mean().iloc[-1] if len(stock_data) >= 50 else None
            sma_200 = stock_data["Close"].rolling(window=200).mean().iloc[-1] if len(stock_data) >= 200 else None
            
            # Position relative to SMAs
            below_sma_20 = sma_20 and current_price < sma_20
            below_sma_50 = sma_50 and current_price < sma_50
            below_sma_200 = sma_200 and current_price < sma_200
            
            # Distance from SMAs (percentage)
            sma_20_distance = ((current_price - sma_20) / sma_20 * 100) if sma_20 else 0
            sma_50_distance = ((current_price - sma_50) / sma_50 * 100) if sma_50 else 0
            sma_200_distance = ((current_price - sma_200) / sma_200 * 100) if sma_200 else 0
            
            return {
                'sma_20': sma_20,
                'sma_50': sma_50,
                'sma_200': sma_200,
                'below_sma_20': below_sma_20,
                'below_sma_50': below_sma_50,
                'below_sma_200': below_sma_200,
                'sma_20_distance_pct': sma_20_distance,
                'sma_50_distance_pct': sma_50_distance,
                'sma_200_distance_pct': sma_200_distance
            }
        except Exception:
            return {
                'sma_20': None, 'sma_50': None, 'sma_200': None,
                'below_sma_20': False, 'below_sma_50': False, 'below_sma_200': False,
                'sma_20_distance_pct': 0, 'sma_50_distance_pct': 0, 'sma_200_distance_pct': 0
            }
    
    def _calculate_price_position(self, stock_data: pd.DataFrame) -> Dict:
        """Analyze price position relative to recent highs/lows."""
        try:
            current_price = stock_data["Close"].iloc[-1]
            
            # 52-week high/low (or available data)
            high_52w = stock_data["High"].max()
            low_52w = stock_data["Low"].min()
            
            # Recent highs (different timeframes)
            high_5d = stock_data["High"].tail(5).max()
            high_20d = stock_data["High"].tail(20).max()
            
            # Calculate drops from highs
            drop_from_52w_high = ((high_52w - current_price) / high_52w) * 100
            drop_from_5d_high = ((high_5d - current_price) / high_5d) * 100
            drop_from_20d_high = ((high_20d - current_price) / high_20d) * 100
            
            # Position in 52-week range
            range_position = ((current_price - low_52w) / (high_52w - low_52w)) * 100
            
            return {
                'high_52w': high_52w,
                'low_52w': low_52w,
                'drop_from_52w_high_pct': drop_from_52w_high,
                'drop_from_5d_high_pct': drop_from_5d_high,
                'drop_from_20d_high_pct': drop_from_20d_high,
                'range_position_pct': range_position,
                'in_dip_zone': 15 <= drop_from_52w_high <= 40  # Sweet spot per methodology
            }
        except Exception:
            return {
                'high_52w': 0, 'low_52w': 0, 'drop_from_52w_high_pct': 0,
                'drop_from_5d_high_pct': 0, 'drop_from_20d_high_pct': 0,
                'range_position_pct': 50, 'in_dip_zone': False
            }
    
    def _calculate_momentum_indicators(self, stock_data: pd.DataFrame) -> Dict:
        """Additional momentum indicators for dip analysis."""
        try:
            # Rate of change
            roc_5 = ((stock_data["Close"].iloc[-1] / stock_data["Close"].iloc[-6]) - 1) * 100 if len(stock_data) > 5 else 0
            roc_10 = ((stock_data["Close"].iloc[-1] / stock_data["Close"].iloc[-11]) - 1) * 100 if len(stock_data) > 10 else 0
            
            # Momentum slowing (smaller red candles)
            recent_ranges = []
            for i in range(1, min(6, len(stock_data))):
                day_range = abs(stock_data["Close"].iloc[-i] - stock_data["Open"].iloc[-i])
                recent_ranges.append(day_range)
            
            momentum_slowing = len(recent_ranges) > 2 and all(
                recent_ranges[i] <= recent_ranges[i-1] for i in range(1, len(recent_ranges))
            )
            
            return {
                'roc_5d': roc_5,
                'roc_10d': roc_10,
                'momentum_slowing': momentum_slowing
            }
        except Exception:
            return {
                'roc_5d': 0,
                'roc_10d': 0,
                'momentum_slowing': False
            }
    
    def _check_rsi_divergence(self, stock_data: pd.DataFrame, rsi_series: pd.Series) -> bool:
        """Check for RSI divergence - price making lower lows while RSI makes higher lows."""
        try:
            if len(stock_data) < 10 or len(rsi_series) < 10:
                return False
            
            # Look at last 10 periods for divergence
            recent_prices = stock_data["Close"].tail(10)
            recent_rsi = rsi_series.tail(10)
            
            # Find recent low points
            price_lows = recent_prices.rolling(window=3, center=True).min()
            rsi_lows = recent_rsi.rolling(window=3, center=True).min()
            
            # Simple divergence check: if we have 2+ lows
            price_low_indices = price_lows[price_lows == recent_prices].index
            if len(price_low_indices) >= 2:
                first_low_idx = price_low_indices[0]
                last_low_idx = price_low_indices[-1]
                
                # Bullish divergence: price lower low, RSI higher low
                price_lower = recent_prices[last_low_idx] < recent_prices[first_low_idx]
                rsi_higher = recent_rsi[last_low_idx] > recent_rsi[first_low_idx]
                
                return price_lower and rsi_higher
            
            return False
        except Exception:
            return False
    
    def _empty_indicators(self) -> Dict:
        """Return empty indicators structure when calculation fails."""
        return {
            'rsi_14': 50, 'rsi_5': 50, 'rsi_oversold': False,
            'rsi_extremely_oversold': False, 'rsi_divergence': False,
            'macd_line': 0, 'macd_signal': 0, 'macd_histogram': 0,
            'macd_bullish_cross': False, 'macd_above_signal': False,
            'macd_histogram_positive': False,
            'sma_20': None, 'sma_50': None, 'sma_200': None,
            'below_sma_20': False, 'below_sma_50': False, 'below_sma_200': False,
            'sma_20_distance_pct': 0, 'sma_50_distance_pct': 0, 'sma_200_distance_pct': 0,
            'high_52w': 0, 'low_52w': 0, 'drop_from_52w_high_pct': 0,
            'drop_from_5d_high_pct': 0, 'drop_from_20d_high_pct': 0,
            'range_position_pct': 50, 'in_dip_zone': False,
            'roc_5d': 0, 'roc_10d': 0, 'momentum_slowing': False
        } 