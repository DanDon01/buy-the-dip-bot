"""
Configuration Manager for Scoring Parameters

Manages loading and applying scoring parameters from the configuration file
created by the frontend scoring tuning dashboard.
"""

import json
import os
from typing import Dict, Optional
from datetime import datetime


class ScoringConfigManager:
    """Manages scoring configuration parameters."""
    
    def __init__(self, config_file: str = 'config/scoring_parameters.json'):
        self.config_file = config_file
        self._cached_config = None
        self._last_loaded = None
    
    def load_parameters(self) -> Dict:
        """Load scoring parameters from configuration file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                self._cached_config = config.get('parameters', {})
                self._last_loaded = datetime.now()
                
                print(f"✅ Loaded scoring parameters from {self.config_file}")
                return self._cached_config
            else:
                print(f"⚠️ No config file found at {self.config_file}, using defaults")
                return self._get_default_parameters()
                
        except Exception as e:
            print(f"❌ Error loading scoring parameters: {e}")
            return self._get_default_parameters()
    
    def get_parameters(self, force_reload: bool = False) -> Dict:
        """Get current parameters, optionally force reload from file."""
        if force_reload or self._cached_config is None:
            return self.load_parameters()
        return self._cached_config
    
    def _get_default_parameters(self) -> Dict:
        """Get default scoring parameters."""
        return {
            # Layer Weights (base layers sum to 100; risk is ± on top)
            'quality_gate_weight': 30,
            'dip_signal_weight': 40,
            'reversal_spark_weight': 15,
            'stabilization_weight': 15,
            'risk_adjustment_weight': 10,
            
            # Quality Gate Thresholds
            'quality_fcf_threshold': 0,
            'quality_pe_multiplier': 1.2,
            'quality_debt_ebitda_max': 3.0,
            'quality_roe_min': 0.10,
            'quality_margin_min': 0.05,
            
            # Dip Signal Thresholds
            'dip_sweet_spot_min': 15,
            'dip_sweet_spot_max': 40,
            'dip_rsi_oversold_min': 25,
            'dip_rsi_oversold_max': 35,
            'dip_volume_spike_min': 1.5,
            'dip_volume_spike_max': 3.0,
            
            # Reversal Spark Thresholds
            'reversal_rsi_min': 30,
            'reversal_volume_threshold': 1.2,
            'reversal_price_action_weight': 0.5,
            
            # Recommendation Thresholds
            'strong_buy_threshold': 80,
            'buy_threshold': 70,
            'watch_threshold': 50,
            'avoid_threshold': 40
        }
    
    def get_recommendation_thresholds(self) -> Dict:
        """Get recommendation thresholds for use in recommendation logic."""
        params = self.get_parameters()
        return {
            'strong_buy_threshold': params.get('strong_buy_threshold', 80),
            'buy_threshold': params.get('buy_threshold', 70),
            'watch_threshold': params.get('watch_threshold', 50),
            'avoid_threshold': params.get('avoid_threshold', 40)
        }


# Global instance for easy access
config_manager = ScoringConfigManager()


def load_scoring_parameters() -> Dict:
    """Convenience function to load scoring parameters."""
    return config_manager.get_parameters(force_reload=True)