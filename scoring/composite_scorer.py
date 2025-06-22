"""
Composite Scorer - Orchestrates the complete 4-layer methodology.

Combines all scoring layers with proper weighting:
1. Quality Gate (35 points) - Business quality filter
2. Dip Signal (45 points) - Core dip detection  
3. Reversal Spark (15 points) - Momentum shift signals
4. Risk Modifiers (±10 points) - Market context adjustments

Total Score: 0-100+ points (with risk adjustments)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import sys
import os

# Import all scoring layers
from .quality_gate import QualityGate
from .dip_signal import DipSignal  
from .reversal_spark import ReversalSpark
from .risk_modifiers import RiskModifiers

# Add parent directory to path to import Phase 1 collectors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.technical_indicators import TechnicalIndicators
from collectors.volume_analysis import VolumeAnalyzer
from collectors.fundamental_data import FundamentalDataCollector


class CompositeScorer:
    """
    Composite scoring engine that implements the complete 4-layer methodology.
    
    Orchestrates Quality Gate → Dip Signal → Reversal Spark → Risk Modifiers
    with proper weighting and quality gate filtering.
    
    Total Score Range: 0-100+ points (risk adjustments can exceed 100)
    Quality Gate Filter: Stocks failing 2+ quality checks are filtered out
    """
    
    def __init__(self):
        # Initialize all scoring layers
        self.quality_gate = QualityGate(max_points=35)
        self.dip_signal = DipSignal(max_points=45)  
        self.reversal_spark = ReversalSpark(max_points=15)
        self.risk_modifiers = RiskModifiers(max_adjustment=10)
        
        # Initialize Phase 1 collectors for data efficiency
        self.tech_indicators = TechnicalIndicators()
        self.volume_analyzer = VolumeAnalyzer()
        self.fundamental_collector = FundamentalDataCollector()
        
        # Methodology weights (should add up to 95, with ±10 risk adjustment)
        self.layer_weights = {
            'quality_gate': 35,     # 35% - Business quality
            'dip_signal': 45,       # 45% - Core dip detection  
            'reversal_spark': 15,   # 15% - Momentum shifts
            'risk_adjustment': 10   # ±10% - Market context
        }
    
    def calculate_composite_score(self, df: pd.DataFrame, ticker: str, 
                                pre_computed_data: Dict = None) -> Tuple[float, Dict]:
        """
        Calculate the complete composite score using the 4-layer methodology.
        
        Args:
            df: Historical price/volume DataFrame
            ticker: Stock ticker symbol
            pre_computed_data: Optional pre-computed data from Phase 1 collectors
            
        Returns:
            Tuple of (composite_score, detailed_breakdown)
        """
        try:
            # Gather enhanced data if not provided (using Phase 1 collectors)
            enhanced_data = pre_computed_data or self._gather_enhanced_data(df, ticker)
            
            # Layer 1: Quality Gate (with filtering)
            quality_score, quality_details = self.quality_gate.score_quality_gate(
                ticker, enhanced_data
            )
            
            # Apply quality gate filter
            if not quality_details.get('passes_quality_gate', False):
                return self._create_filtered_result(quality_details, ticker)
            
            # Layer 2: Dip Signal (core methodology)
            dip_score, dip_details = self.dip_signal.score_dip_signal(
                df, ticker, enhanced_data
            )
            
            # Layer 3: Reversal Spark (momentum detection)
            reversal_score, reversal_details = self.reversal_spark.score_reversal_spark(
                df, ticker, enhanced_data
            )
            
            # Layer 4: Risk Modifiers (context adjustment)
            risk_adjustment, risk_details = self.risk_modifiers.score_risk_modifiers(
                ticker, enhanced_data
            )
            
            # Calculate composite score
            base_score = quality_score + dip_score + reversal_score
            final_score = base_score + risk_adjustment
            
            # Create comprehensive scoring breakdown
            scoring_breakdown = {
                'final_composite_score': final_score,
                'base_score': base_score,
                'layer_scores': {
                    'quality_gate': quality_score,
                    'dip_signal': dip_score,
                    'reversal_spark': reversal_score,
                    'risk_adjustment': risk_adjustment
                },
                'layer_details': {
                    'quality_gate': quality_details,
                    'dip_signal': dip_details,
                    'reversal_spark': reversal_details,
                    'risk_modifiers': risk_details
                },
                'methodology_compliance': self._assess_methodology_compliance(
                    quality_details, dip_details, reversal_details
                ),
                'overall_grade': self._calculate_overall_grade(final_score),
                'investment_recommendation': self._generate_recommendation(
                    final_score, quality_details, dip_details, reversal_details, risk_details
                ),
                'ticker': ticker,
                'scoring_timestamp': pd.Timestamp.now().isoformat()
            }
            
            return final_score, scoring_breakdown
            
        except Exception as e:
            print(f"Error calculating composite score for {ticker}: {e}")
            return 0, self._empty_composite_result(ticker)
    
    def _gather_enhanced_data(self, df: pd.DataFrame, ticker: str) -> Dict:
        """Gather enhanced data using Phase 1 collectors."""
        enhanced_data = {}
        
        try:
            # Technical indicators
            enhanced_data['enhanced_tech'] = self.tech_indicators.calculate_all_indicators(df, ticker)
            
            # Volume analysis  
            enhanced_data['enhanced_volume'] = self.volume_analyzer.analyze_volume_patterns(df, ticker)
            
            # Fundamental data (with rate limiting)
            enhanced_data['fundamentals'] = self.fundamental_collector.get_fundamental_metrics(ticker)
            
        except Exception as e:
            print(f"Error gathering enhanced data for {ticker}: {e}")
        
        return enhanced_data
    
    def _create_filtered_result(self, quality_details: Dict, ticker: str) -> Tuple[float, Dict]:
        """Create result for stocks filtered out by quality gate."""
        return 0, {
            'final_composite_score': 0,
            'base_score': 0,
            'layer_scores': {
                'quality_gate': quality_details.get('total_quality_score', 0),
                'dip_signal': 0,
                'reversal_spark': 0,
                'risk_adjustment': 0
            },
            'layer_details': {
                'quality_gate': quality_details,
                'dip_signal': {},
                'reversal_spark': {},
                'risk_modifiers': {}
            },
            'methodology_compliance': {
                'passes_quality_gate': False,
                'reason': 'Failed quality gate filter',
                'failed_checks': quality_details.get('failed_checks', 0)
            },
            'overall_grade': 'F',
            'investment_recommendation': {
                'action': 'AVOID',
                'confidence': 'high',
                'reason': 'Poor business quality - failed quality gate'
            },
            'ticker': ticker,
            'scoring_timestamp': pd.Timestamp.now().isoformat()
        }
    
    def _assess_methodology_compliance(self, quality_details: Dict, 
                                     dip_details: Dict, reversal_details: Dict) -> Dict:
        """Assess compliance with ScoresandMetrics.txt methodology."""
        compliance = {
            'passes_quality_gate': quality_details.get('passes_quality_gate', False),
            'in_dip_sweet_spot': dip_details.get('in_sweet_spot', False),
            'has_reversal_signals': reversal_details.get('reversal_signals', {}).get('total_signals', 0) > 0,
            'dip_classification': dip_details.get('dip_classification', 'no_dip'),
            'quality_grade': quality_details.get('quality_grade', 'F'),
            'dip_grade': dip_details.get('dip_grade', 'F'),
            'reversal_strength': reversal_details.get('reversal_strength', 'minimal')
        }
        
        # Overall methodology score
        methodology_score = 0
        if compliance['passes_quality_gate']:
            methodology_score += 30
        if compliance['in_dip_sweet_spot']:
            methodology_score += 40
        if compliance['has_reversal_signals']:
            methodology_score += 20
        
        compliance['methodology_score'] = methodology_score
        compliance['methodology_grade'] = 'A' if methodology_score >= 80 else 'B' if methodology_score >= 60 else 'C' if methodology_score >= 40 else 'D' if methodology_score >= 20 else 'F'
        
        return compliance
    
    def _calculate_overall_grade(self, final_score: float) -> str:
        """Calculate overall letter grade for the composite score."""
        if final_score >= 85:
            return 'A+'
        elif final_score >= 80:
            return 'A'
        elif final_score >= 75:
            return 'A-'
        elif final_score >= 70:
            return 'B+'
        elif final_score >= 65:
            return 'B'
        elif final_score >= 60:
            return 'B-'
        elif final_score >= 55:
            return 'C+'
        elif final_score >= 50:
            return 'C'
        elif final_score >= 45:
            return 'C-'
        elif final_score >= 40:
            return 'D+'
        elif final_score >= 35:
            return 'D'
        elif final_score >= 30:
            return 'D-'
        else:
            return 'F'
    
    def _generate_recommendation(self, final_score: float, quality_details: Dict,
                               dip_details: Dict, reversal_details: Dict, 
                               risk_details: Dict) -> Dict:
        """Generate investment recommendation based on layered analysis."""
        
        # Base recommendation on score
        if final_score >= 80:
            action = 'STRONG_BUY'
            confidence = 'high'
        elif final_score >= 70:
            action = 'BUY'
            confidence = 'high'
        elif final_score >= 60:
            action = 'BUY'
            confidence = 'medium'
        elif final_score >= 50:
            action = 'WATCH'
            confidence = 'medium'
        elif final_score >= 40:
            action = 'WATCH'
            confidence = 'low'
        else:
            action = 'AVOID'
            confidence = 'high'
        
        # Adjust based on specific factors
        risk_level = risk_details.get('risk_level', 'neutral')
        dip_classification = dip_details.get('dip_classification', 'no_dip')
        
        if risk_level == 'high_risk' and action in ['STRONG_BUY', 'BUY']:
            action = 'WATCH'
            confidence = 'low'
        
        if dip_classification == 'premium_dip' and final_score >= 60:
            if action == 'BUY':
                action = 'STRONG_BUY'
        
        # Generate reasoning
        reasons = []
        if quality_details.get('quality_grade', 'F') in ['A', 'B']:
            reasons.append('solid business quality')
        
        if dip_details.get('in_sweet_spot', False):
            reasons.append('ideal dip conditions')
        
        if reversal_details.get('reversal_strength', 'minimal') in ['strong', 'moderate']:
            reasons.append('reversal signals present')
        
        if risk_level in ['high_risk', 'elevated_risk']:
            reasons.append('elevated market risk')
        
        return {
            'action': action,
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'comprehensive analysis',
            'key_strengths': self._identify_key_strengths(quality_details, dip_details, reversal_details),
            'key_risks': self._identify_key_risks(quality_details, dip_details, risk_details)
        }
    
    def _identify_key_strengths(self, quality_details: Dict, dip_details: Dict, 
                              reversal_details: Dict) -> list:
        """Identify key strengths from the analysis."""
        strengths = []
        
        if quality_details.get('quality_grade', 'F') == 'A':
            strengths.append('Excellent business quality')
        
        if dip_details.get('dip_classification') == 'premium_dip':
            strengths.append('Premium dip opportunity')
        
        if dip_details.get('in_sweet_spot', False):
            strengths.append('Perfect dip zone (15-40% drop)')
        
        if reversal_details.get('reversal_signals', {}).get('total_signals', 0) >= 3:
            strengths.append('Multiple reversal signals')
        
        return strengths
    
    def _identify_key_risks(self, quality_details: Dict, dip_details: Dict, 
                          risk_details: Dict) -> list:
        """Identify key risks from the analysis."""
        risks = []
        
        if quality_details.get('failed_checks', 0) > 0:
            risks.append(f"Failed {quality_details['failed_checks']} quality checks")
        
        if dip_details.get('dip_classification') == 'deep_value':
            risks.append('Deep decline (potential structural issues)')
        
        if risk_details.get('risk_level') == 'high_risk':
            risks.append('High market risk environment')
        
        adjustment_factors = risk_details.get('adjustment_factors', {})
        if 'volatility' in adjustment_factors and adjustment_factors['volatility'] == 'unfavorable':
            risks.append('Unfavorable volatility regime')
        
        return risks
    
    def _empty_composite_result(self, ticker: str) -> Dict:
        """Return empty composite result when calculation fails."""
        return {
            'final_composite_score': 0,
            'base_score': 0,
            'layer_scores': {
                'quality_gate': 0,
                'dip_signal': 0,
                'reversal_spark': 0,
                'risk_adjustment': 0
            },
            'layer_details': {
                'quality_gate': {},
                'dip_signal': {},
                'reversal_spark': {},
                'risk_modifiers': {}
            },
            'methodology_compliance': {
                'passes_quality_gate': False,
                'methodology_score': 0,
                'methodology_grade': 'F'
            },
            'overall_grade': 'F',
            'investment_recommendation': {
                'action': 'AVOID',
                'confidence': 'high',
                'reason': 'calculation_error'
            },
            'ticker': ticker,
            'scoring_timestamp': pd.Timestamp.now().isoformat()
        } 