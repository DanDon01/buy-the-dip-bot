"""
Volume analysis collector for enhanced dip detection.

Builds on existing volume logic in data_collector.py and utils.py
to provide sophisticated volume spike analysis and pattern detection.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class VolumeAnalyzer:
    """
    Enhanced volume analyzer for dip-hunting strategies.
    
    Focuses on:
    - Volume spike detection (builds on existing logic)
    - Unusual activity patterns  
    - Volume trend analysis
    - Capitulation and accumulation signals
    """
    
    def __init__(self):
        self.cache = {}
    
    def analyze_volume_patterns(self, stock_data: pd.DataFrame, ticker: str = "") -> Dict:
        """
        Comprehensive volume analysis for a stock.
        
        Args:
            stock_data: DataFrame with OHLCV data
            ticker: Stock ticker for caching
            
        Returns:
            Dictionary with volume analysis results
        """
        if stock_data is None or len(stock_data) < 10:
            return self._empty_volume_analysis()
        
        try:
            analysis = {}
            
            # Basic volume metrics
            analysis.update(self._calculate_basic_volume_metrics(stock_data))
            
            # Volume spike detection (enhanced from existing logic)
            analysis.update(self._detect_volume_spikes(stock_data))
            
            # Volume trend analysis
            analysis.update(self._analyze_volume_trends(stock_data))
            
            # Capitulation/accumulation signals
            analysis.update(self._detect_volume_signals(stock_data))
            
            # Volume vs price relationship
            analysis.update(self._analyze_volume_price_relationship(stock_data))
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing volume patterns for {ticker}: {e}")
            return self._empty_volume_analysis()
    
    def _calculate_basic_volume_metrics(self, stock_data: pd.DataFrame) -> Dict:
        """Calculate basic volume statistics."""
        try:
            current_volume = stock_data["Volume"].iloc[-1]
            
            # Various volume averages
            vol_avg_5 = stock_data["Volume"].tail(5).mean()
            vol_avg_10 = stock_data["Volume"].tail(10).mean()
            vol_avg_20 = stock_data["Volume"].tail(20).mean()
            vol_avg_50 = stock_data["Volume"].tail(50).mean() if len(stock_data) >= 50 else vol_avg_20
            
            # Volume ratios
            vol_ratio_5 = current_volume / vol_avg_5 if vol_avg_5 > 0 else 1
            vol_ratio_10 = current_volume / vol_avg_10 if vol_avg_10 > 0 else 1
            vol_ratio_20 = current_volume / vol_avg_20 if vol_avg_20 > 0 else 1
            vol_ratio_50 = current_volume / vol_avg_50 if vol_avg_50 > 0 else 1
            
            return {
                'current_volume': current_volume,
                'volume_avg_5d': vol_avg_5,
                'volume_avg_10d': vol_avg_10,
                'volume_avg_20d': vol_avg_20,
                'volume_avg_50d': vol_avg_50,
                'volume_ratio_5d': vol_ratio_5,
                'volume_ratio_10d': vol_ratio_10,
                'volume_ratio_20d': vol_ratio_20,
                'volume_ratio_50d': vol_ratio_50
            }
        except Exception:
            return {
                'current_volume': 0, 'volume_avg_5d': 0, 'volume_avg_10d': 0,
                'volume_avg_20d': 0, 'volume_avg_50d': 0, 'volume_ratio_5d': 1,
                'volume_ratio_10d': 1, 'volume_ratio_20d': 1, 'volume_ratio_50d': 1
            }
    
    def _detect_volume_spikes(self, stock_data: pd.DataFrame) -> Dict:
        """Enhanced volume spike detection based on methodology."""
        try:
            current_volume = stock_data["Volume"].iloc[-1]
            vol_avg_20 = stock_data["Volume"].tail(20).mean()
            vol_ratio = current_volume / vol_avg_20 if vol_avg_20 > 0 else 1
            
            # Classification based on methodology (1.5x-3x is sweet spot)
            spike_classification = "normal"
            if vol_ratio >= 3.0:
                spike_classification = "extreme_spike"
            elif vol_ratio >= 2.0:
                spike_classification = "strong_spike"
            elif vol_ratio >= 1.5:
                spike_classification = "moderate_spike"
            elif vol_ratio >= 1.2:
                spike_classification = "mild_increase"
            
            # Recent spike history (last 5 days)
            recent_spikes = 0
            for i in range(1, min(6, len(stock_data))):
                past_vol = stock_data["Volume"].iloc[-i]
                past_avg = stock_data["Volume"].iloc[-i-20:-i].mean() if i <= len(stock_data) - 20 else vol_avg_20
                if past_avg > 0 and (past_vol / past_avg) >= 1.5:
                    recent_spikes += 1
            
            # Volume spike score (0-100)
            spike_score = min(100, int((vol_ratio - 1) * 50))
            
            # In sweet spot for dip hunting
            in_spike_sweet_spot = 1.5 <= vol_ratio <= 3.0
            
            return {
                'volume_spike_ratio': vol_ratio,
                'volume_spike_classification': spike_classification,
                'volume_spike_score': spike_score,
                'recent_spike_count': recent_spikes,
                'in_spike_sweet_spot': in_spike_sweet_spot,
                'extreme_volume': vol_ratio >= 3.0,
                'low_volume': vol_ratio < 0.5
            }
        except Exception:
            return {
                'volume_spike_ratio': 1.0, 'volume_spike_classification': 'normal',
                'volume_spike_score': 0, 'recent_spike_count': 0,
                'in_spike_sweet_spot': False, 'extreme_volume': False, 'low_volume': False
            }
    
    def _analyze_volume_trends(self, stock_data: pd.DataFrame) -> Dict:
        """Analyze volume trends over different timeframes."""
        try:
            # Volume trend over last 5, 10, 20 days
            vol_5d = stock_data["Volume"].tail(5)
            vol_10d = stock_data["Volume"].tail(10)
            vol_20d = stock_data["Volume"].tail(20)
            
            # Calculate trends (using linear regression slope)
            def calculate_trend(values):
                if len(values) < 3:
                    return 0
                x = np.arange(len(values))
                y = values.values
                slope = np.polyfit(x, y, 1)[0]
                return slope / values.mean() if values.mean() > 0 else 0
            
            volume_trend_5d = calculate_trend(vol_5d)
            volume_trend_10d = calculate_trend(vol_10d)
            volume_trend_20d = calculate_trend(vol_20d)
            
            # Volume consistency (lower standard deviation = more consistent)
            volume_consistency_20d = 1 / (1 + vol_20d.std() / vol_20d.mean()) if vol_20d.mean() > 0 else 0
            
            # Volume momentum (acceleration)
            recent_avg = vol_5d.mean()
            older_avg = vol_20d.tail(15).head(5).mean() if len(vol_20d) >= 15 else vol_20d.mean()
            volume_momentum = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            
            return {
                'volume_trend_5d': volume_trend_5d,
                'volume_trend_10d': volume_trend_10d,
                'volume_trend_20d': volume_trend_20d,
                'volume_consistency_20d': volume_consistency_20d,
                'volume_momentum': volume_momentum,
                'volume_increasing': volume_trend_10d > 0.02,  # 2% daily increase
                'volume_decreasing': volume_trend_10d < -0.02   # 2% daily decrease
            }
        except Exception:
            return {
                'volume_trend_5d': 0, 'volume_trend_10d': 0, 'volume_trend_20d': 0,
                'volume_consistency_20d': 0, 'volume_momentum': 0,
                'volume_increasing': False, 'volume_decreasing': False
            }
    
    def _detect_volume_signals(self, stock_data: pd.DataFrame) -> Dict:
        """Detect capitulation and accumulation volume signals."""
        try:
            # Capitulation signal: high volume + price drop
            current_price = stock_data["Close"].iloc[-1]
            prev_price = stock_data["Close"].iloc[-2] if len(stock_data) > 1 else current_price
            price_change_pct = ((current_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0
            
            vol_ratio = stock_data["Volume"].iloc[-1] / stock_data["Volume"].tail(20).mean()
            
            # Capitulation: high volume + significant price drop
            capitulation_signal = vol_ratio >= 2.0 and price_change_pct <= -3.0
            
            # Accumulation: above average volume + price stability/slight increase
            accumulation_signal = vol_ratio >= 1.3 and -1.0 <= price_change_pct <= 2.0
            
            # Distribution: high volume + price drop over multiple days
            recent_price_changes = []
            recent_volumes = []
            for i in range(1, min(4, len(stock_data))):
                price_today = stock_data["Close"].iloc[-i]
                price_yesterday = stock_data["Close"].iloc[-i-1] if len(stock_data) > i else price_today
                change = ((price_today - price_yesterday) / price_yesterday) * 100 if price_yesterday > 0 else 0
                recent_price_changes.append(change)
                recent_volumes.append(stock_data["Volume"].iloc[-i])
            
            avg_recent_volume = np.mean(recent_volumes) if recent_volumes else 0
            avg_baseline_volume = stock_data["Volume"].tail(20).mean()
            distribution_signal = (
                len(recent_price_changes) >= 2 and
                sum(1 for x in recent_price_changes if x < -1) >= 2 and
                avg_recent_volume > avg_baseline_volume * 1.5
            )
            
            # Volume exhaustion: very high volume followed by normal volume
            volume_exhaustion = False
            if len(stock_data) >= 3:
                yesterday_vol = stock_data["Volume"].iloc[-2]
                today_vol = stock_data["Volume"].iloc[-1]
                avg_vol = stock_data["Volume"].tail(20).mean()
                volume_exhaustion = (yesterday_vol > avg_vol * 2.5 and 
                                   today_vol < avg_vol * 1.2)
            
            return {
                'capitulation_signal': capitulation_signal,
                'accumulation_signal': accumulation_signal,
                'distribution_signal': distribution_signal,
                'volume_exhaustion': volume_exhaustion,
                'forced_selling_likely': vol_ratio >= 2.5 and price_change_pct <= -5.0
            }
        except Exception:
            return {
                'capitulation_signal': False, 'accumulation_signal': False,
                'distribution_signal': False, 'volume_exhaustion': False,
                'forced_selling_likely': False
            }
    
    def _analyze_volume_price_relationship(self, stock_data: pd.DataFrame) -> Dict:
        """Analyze the relationship between volume and price movements."""
        try:
            # Volume-price correlation over last 20 days
            if len(stock_data) < 20:
                return {'volume_price_correlation': 0, 'volume_confirms_trend': False}
            
            recent_data = stock_data.tail(20)
            price_changes = recent_data["Close"].pct_change().dropna()
            volume_changes = recent_data["Volume"].pct_change().dropna()
            
            # Correlation between volume and absolute price changes
            abs_price_changes = abs(price_changes)
            correlation = abs_price_changes.corr(volume_changes) if len(abs_price_changes) > 5 else 0
            
            # Volume confirmation of trend
            recent_trend = (recent_data["Close"].iloc[-1] - recent_data["Close"].iloc[0]) / recent_data["Close"].iloc[0]
            recent_volume_trend = (recent_data["Volume"].tail(5).mean() - recent_data["Volume"].head(5).mean()) / recent_data["Volume"].head(5).mean()
            
            # Volume confirms trend if both are in same direction
            volume_confirms_trend = (
                (recent_trend > 0 and recent_volume_trend > 0) or  # Up trend with volume
                (recent_trend < 0 and recent_volume_trend > 0)     # Down trend with volume (selling)
            )
            
            # On-balance volume approximation
            obv_changes = []
            for i in range(1, len(recent_data)):
                price_change = recent_data["Close"].iloc[i] - recent_data["Close"].iloc[i-1]
                volume = recent_data["Volume"].iloc[i]
                if price_change > 0:
                    obv_changes.append(volume)
                elif price_change < 0:
                    obv_changes.append(-volume)
                else:
                    obv_changes.append(0)
            
            obv_trend = sum(obv_changes[-5:]) if len(obv_changes) >= 5 else 0
            
            return {
                'volume_price_correlation': correlation,
                'volume_confirms_trend': volume_confirms_trend,
                'obv_trend_recent': obv_trend,
                'volume_leads_price': correlation > 0.3
            }
        except Exception:
            return {
                'volume_price_correlation': 0,
                'volume_confirms_trend': False,
                'obv_trend_recent': 0,
                'volume_leads_price': False
            }
    
    def _empty_volume_analysis(self) -> Dict:
        """Return empty volume analysis when calculation fails."""
        return {
            'current_volume': 0, 'volume_avg_5d': 0, 'volume_avg_10d': 0,
            'volume_avg_20d': 0, 'volume_avg_50d': 0, 'volume_ratio_5d': 1,
            'volume_ratio_10d': 1, 'volume_ratio_20d': 1, 'volume_ratio_50d': 1,
            'volume_spike_ratio': 1.0, 'volume_spike_classification': 'normal',
            'volume_spike_score': 0, 'recent_spike_count': 0,
            'in_spike_sweet_spot': False, 'extreme_volume': False, 'low_volume': False,
            'volume_trend_5d': 0, 'volume_trend_10d': 0, 'volume_trend_20d': 0,
            'volume_consistency_20d': 0, 'volume_momentum': 0,
            'volume_increasing': False, 'volume_decreasing': False,
            'capitulation_signal': False, 'accumulation_signal': False,
            'distribution_signal': False, 'volume_exhaustion': False,
            'forced_selling_likely': False, 'volume_price_correlation': 0,
            'volume_confirms_trend': False, 'obv_trend_recent': 0,
            'volume_leads_price': False
        } 