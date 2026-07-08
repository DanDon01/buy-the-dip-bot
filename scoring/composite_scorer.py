"""
Composite Scorer - Orchestrates the complete 5-layer methodology.

Combines all scoring layers with configurable weighting (defaults):
1. Quality Gate (30 points) - Business quality filter
2. Dip Signal (40 points) - Core dip detection
3. Reversal Spark (15 points) - Momentum shift signals
4. Stabilization (15 points) - Falling-knife filter (added July 2026)
5. Risk Modifiers (±10 points) - Market context adjustments

Total Score: 0-100+ points (with risk adjustments)

Layer weights are read from config/scoring_parameters.json (managed by the
dashboard's Scoring Tuner and the ML weight optimizer); each layer's raw
score is rescaled from its native range to the configured weight.
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
from .stabilization import Stabilization
from .risk_modifiers import RiskModifiers
from .config_manager import ScoringConfigManager

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
    
    # Native score ranges the layer implementations produce internally.
    # Raw layer scores are rescaled from these to the configured weights.
    NATIVE_MAX = {
        'quality_gate': 35,
        'dip_signal': 45,
        'reversal_spark': 15,
        'stabilization': 15,
    }

    def __init__(self, config_manager: Optional[ScoringConfigManager] = None):
        # Initialize all scoring layers (native ranges)
        self.quality_gate = QualityGate(max_points=35)
        self.dip_signal = DipSignal(max_points=45)
        self.reversal_spark = ReversalSpark(max_points=15)
        self.stabilization = Stabilization(max_points=15)
        self.risk_modifiers = RiskModifiers(max_adjustment=10)

        # Initialize Phase 1 collectors for data efficiency
        self.tech_indicators = TechnicalIndicators()
        self.volume_analyzer = VolumeAnalyzer()
        self.fundamental_collector = FundamentalDataCollector()

        # Configurable layer weights (base layers should add up to 100,
        # with ±risk_adjustment_weight on top). Managed by the dashboard
        # Scoring Tuner / ML optimizer via config/scoring_parameters.json.
        self._config = config_manager or ScoringConfigManager()
        params = self._config.get_parameters()
        self.layer_weights = {
            'quality_gate': params.get('quality_gate_weight', 30),
            'dip_signal': params.get('dip_signal_weight', 40),
            'reversal_spark': params.get('reversal_spark_weight', 15),
            'stabilization': params.get('stabilization_weight', 15),
            'risk_adjustment': params.get('risk_adjustment_weight', 10),
        }

    def _rescale(self, layer: str, raw_score: float) -> float:
        """Rescale a layer's native-range score to its configured weight."""
        native = self.NATIVE_MAX.get(layer)
        if not native:
            return raw_score
        return raw_score / native * self.layer_weights.get(layer, native)
    
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
            
            # Perform volume analysis and store it for later use
            volume_analysis_results = self.volume_analyzer.analyze_volume_patterns(df, ticker)
            
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

            # Layer 4: Stabilization (falling-knife filter)
            stabilization_score, stabilization_details = self.stabilization.score_stabilization(
                df, ticker, enhanced_data
            )

            # Layer 5: Risk Modifiers (context adjustment)
            risk_adjustment, risk_details = self.risk_modifiers.score_risk_modifiers(
                ticker, enhanced_data
            )

            # Rescale native layer scores to the configured weights
            quality_weighted = self._rescale('quality_gate', quality_score)
            dip_weighted = self._rescale('dip_signal', dip_score)
            reversal_weighted = self._rescale('reversal_spark', reversal_score)
            stabilization_weighted = self._rescale('stabilization', stabilization_score)

            # Calculate composite score
            base_score = (quality_weighted + dip_weighted
                          + reversal_weighted + stabilization_weighted)
            final_score = base_score + risk_adjustment

            # Data-completeness confidence (0..1)
            confidence = self._assess_data_confidence(
                enhanced_data, quality_details, dip_details
            )

            # Create comprehensive scoring breakdown
            scoring_breakdown = {
                'final_composite_score': final_score,
                'base_score': base_score,
                'volume_analysis': volume_analysis_results,
                'layer_scores': {
                    'quality_gate': quality_weighted,
                    'dip_signal': dip_weighted,
                    'reversal_spark': reversal_weighted,
                    'stabilization': stabilization_weighted,
                    'risk_adjustment': risk_adjustment
                },
                'layer_weights': dict(self.layer_weights),
                'layer_details': {
                    'quality_gate': quality_details,
                    'dip_signal': dip_details,
                    'reversal_spark': reversal_details,
                    'stabilization': stabilization_details,
                    'risk_modifiers': risk_details
                },
                'data_confidence': confidence,
                'methodology_compliance': self._assess_methodology_compliance(
                    quality_details, dip_details, reversal_details, stabilization_details
                ),
                'overall_grade': self._calculate_overall_grade(final_score),
                'investment_recommendation': self._generate_recommendation(
                    final_score, quality_details, dip_details, reversal_details,
                    risk_details, stabilization_details, confidence
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
                'stabilization': 0,
                'risk_adjustment': 0
            },
            'layer_details': {
                'quality_gate': quality_details,
                'dip_signal': {},
                'reversal_spark': {},
                'stabilization': {},
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
    
    def _assess_data_confidence(self, enhanced_data: Dict,
                                quality_details: Dict, dip_details: Dict) -> float:
        """Score data completeness 0..1 so thin-data results can be flagged.

        Checks the fundamental fields the Quality Gate leans on and whether
        the technical layers produced real (non-empty) detail dicts.
        """
        try:
            stock_data = (enhanced_data or {}).get('ticker_data', {}) or {}
            fundamental_keys = ('free_cash_flow', 'operating_margins',
                                'return_on_equity', 'debt_to_equity', 'pe',
                                'revenue_growth', 'market_cap')
            present = sum(1 for k in fundamental_keys
                          if stock_data.get(k) is not None)
            fundamentals_frac = present / len(fundamental_keys)

            technical_ok = 1.0 if dip_details.get('dip_classification', 'no_data') \
                not in ('no_data',) else 0.0
            quality_ok = 1.0 if quality_details.get('total_quality_score', 0) > 0 else 0.5

            return round(0.6 * fundamentals_frac + 0.25 * technical_ok
                         + 0.15 * quality_ok, 3)
        except Exception:
            return 0.5

    def _assess_methodology_compliance(self, quality_details: Dict,
                                     dip_details: Dict, reversal_details: Dict,
                                     stabilization_details: Dict = None) -> Dict:
        """Assess compliance with ScoresandMetrics.txt methodology."""
        stabilization_details = stabilization_details or {}
        compliance = {
            'passes_quality_gate': quality_details.get('passes_quality_gate', False),
            'in_dip_sweet_spot': dip_details.get('in_sweet_spot', False),
            'has_reversal_signals': reversal_details.get('reversal_signals', {}).get('total_signals', 0) > 0,
            'has_stabilized': stabilization_details.get('stabilization_state') in ('stabilized', 'basing'),
            'falling_knife_risk': stabilization_details.get('falling_knife_risk', 'unknown'),
            'dip_classification': dip_details.get('dip_classification', 'no_dip'),
            'quality_grade': quality_details.get('quality_grade', 'F'),
            'dip_grade': dip_details.get('dip_grade', 'F'),
            'stabilization_grade': stabilization_details.get('stabilization_grade', 'F'),
            'reversal_strength': reversal_details.get('reversal_strength', 'minimal')
        }

        # Overall methodology score
        methodology_score = 0
        if compliance['passes_quality_gate']:
            methodology_score += 25
        if compliance['in_dip_sweet_spot']:
            methodology_score += 35
        if compliance['has_reversal_signals']:
            methodology_score += 20
        if compliance['has_stabilized']:
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
                               risk_details: Dict, stabilization_details: Dict = None,
                               data_confidence: float = 1.0) -> Dict:
        """Generate investment recommendation based on layered analysis."""
        stabilization_details = stabilization_details or {}

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
        knife_risk = stabilization_details.get('falling_knife_risk', 'unknown')

        if risk_level == 'high_risk' and action in ['STRONG_BUY', 'BUY']:
            action = 'WATCH'
            confidence = 'low'

        # Falling-knife guard: never STRONG_BUY into a stock still in
        # free-fall, however attractive the discount looks.
        if knife_risk == 'high' and action == 'STRONG_BUY':
            action = 'BUY'
            confidence = 'medium'

        if dip_classification == 'premium_dip' and final_score >= 60:
            if action == 'BUY' and knife_risk != 'high':
                action = 'STRONG_BUY'

        # Thin data caps confidence - a great score built on missing
        # fundamentals shouldn't read as a table-pounding buy.
        if data_confidence < 0.5 and confidence == 'high':
            confidence = 'medium'

        # Generate reasoning
        reasons = []
        if quality_details.get('quality_grade', 'F') in ['A', 'B']:
            reasons.append('solid business quality')

        if dip_details.get('in_sweet_spot', False):
            reasons.append('ideal dip conditions')

        stab_state = stabilization_details.get('stabilization_state')
        if stab_state == 'stabilized':
            reasons.append('price has stabilized')
        elif stab_state == 'still_falling':
            reasons.append('still falling - unproven base')

        if reversal_details.get('reversal_strength', 'minimal') in ['strong', 'moderate']:
            reasons.append('reversal signals present')

        if risk_level in ['high_risk', 'elevated_risk']:
            reasons.append('elevated market risk')

        if data_confidence < 0.5:
            reasons.append('limited fundamental data')

        return {
            'action': action,
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'comprehensive analysis',
            'key_strengths': self._identify_key_strengths(quality_details, dip_details,
                                                          reversal_details, stabilization_details),
            'key_risks': self._identify_key_risks(quality_details, dip_details,
                                                  risk_details, stabilization_details)
        }
    
    def _identify_key_strengths(self, quality_details: Dict, dip_details: Dict,
                              reversal_details: Dict,
                              stabilization_details: Dict = None) -> list:
        """Identify key strengths from the analysis."""
        stabilization_details = stabilization_details or {}
        strengths = []

        if quality_details.get('quality_grade', 'F') == 'A':
            strengths.append('Excellent business quality')

        if dip_details.get('dip_classification') == 'premium_dip':
            strengths.append('Premium dip opportunity')

        if dip_details.get('in_sweet_spot', False):
            strengths.append('Perfect dip zone (15-40% drop)')

        if reversal_details.get('reversal_signals', {}).get('total_signals', 0) >= 3:
            strengths.append('Multiple reversal signals')

        if stabilization_details.get('stabilization_state') == 'stabilized':
            strengths.append('Price stabilized (base forming)')

        return strengths

    def _identify_key_risks(self, quality_details: Dict, dip_details: Dict,
                          risk_details: Dict,
                          stabilization_details: Dict = None) -> list:
        """Identify key risks from the analysis."""
        stabilization_details = stabilization_details or {}
        risks = []

        if quality_details.get('failed_checks', 0) > 0:
            risks.append(f"Failed {quality_details['failed_checks']} quality checks")

        if dip_details.get('dip_classification') == 'deep_value':
            risks.append('Deep decline (potential structural issues)')

        if risk_details.get('risk_level') == 'high_risk':
            risks.append('High market risk environment')

        if stabilization_details.get('falling_knife_risk') == 'high':
            risks.append('Falling knife - price has not stabilized')

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
                'stabilization': 0,
                'risk_adjustment': 0
            },
            'layer_details': {
                'quality_gate': {},
                'dip_signal': {},
                'reversal_spark': {},
                'stabilization': {},
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