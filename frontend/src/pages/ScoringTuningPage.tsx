import React, { useState, useEffect } from 'react';

interface ScoringParameters {
  // Layer Weights (total should = 100)
  quality_gate_weight: number;
  dip_signal_weight: number;
  reversal_spark_weight: number;
  risk_adjustment_weight: number;
  
  // Quality Gate Thresholds  
  quality_fcf_threshold: number;
  quality_pe_multiplier: number;
  quality_debt_ebitda_max: number;
  quality_roe_min: number;
  quality_margin_min: number;
  
  // Dip Signal Thresholds
  dip_sweet_spot_min: number;  // % below 52w high
  dip_sweet_spot_max: number;
  dip_rsi_oversold_min: number;
  dip_rsi_oversold_max: number;
  dip_volume_spike_min: number; // volume multiplier
  dip_volume_spike_max: number;
  
  // Reversal Spark Thresholds
  reversal_rsi_min: number;
  reversal_volume_threshold: number;
  reversal_price_action_weight: number;
  
  // Recommendation Thresholds
  strong_buy_threshold: number;
  buy_threshold: number;
  watch_threshold: number;
  avoid_threshold: number;
}

interface TestResult {
  ticker: string;
  old_score: number;
  new_score: number;
  score_change: number;
  old_recommendation: string;
  new_recommendation: string;
  recommendation_changed: boolean;
  layer_scores: {
    quality_gate: number;
    dip_signal: number;
    reversal_spark: number;
    risk_adjustment: number;
  };
  issues: string[];
  data_issues: boolean;
  has_enhanced_data: boolean;
  calculation_details?: {
    method: string;
    pe_check?: string;
    market_cap_check?: string;
    dividend_check?: string;
    dip_check?: string;
    volatility_check?: string;
    beta_check?: string;
    oversold_check?: string;
  };
  fundamental_data?: {
    pe_ratio: number | null;
    market_cap: number | null;
    dividend_yield: number | null;
    beta: number | null;
    year_high: number | null;
    year_low: number | null;
    current_price: number | null;
  };
  data_quality: {
    missing_fundamentals: boolean;
    missing_technical: boolean;
    missing_volume: boolean;
    error_count: number;
  };
}

const ScoringTuningPage: React.FC = () => {
  const [parameters, setParameters] = useState<ScoringParameters>({
    // Current default weights
    quality_gate_weight: 35,
    dip_signal_weight: 45,
    reversal_spark_weight: 15,
    risk_adjustment_weight: 10,
    
    // Quality Gate defaults
    quality_fcf_threshold: 0,
    quality_pe_multiplier: 1.2,
    quality_debt_ebitda_max: 3.0,
    quality_roe_min: 0.10,
    quality_margin_min: 0.05,
    
    // Dip Signal defaults  
    dip_sweet_spot_min: 15,
    dip_sweet_spot_max: 40,
    dip_rsi_oversold_min: 25,
    dip_rsi_oversold_max: 35,
    dip_volume_spike_min: 1.5,
    dip_volume_spike_max: 3.0,
    
    // Reversal Spark defaults
    reversal_rsi_min: 30,
    reversal_volume_threshold: 1.2,
    reversal_price_action_weight: 0.5,
    
    // Recommendation defaults
    strong_buy_threshold: 80,
    buy_threshold: 70,
    watch_threshold: 50,
    avoid_threshold: 40,
  });

  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentStocks, setCurrentStocks] = useState<any[]>([]);
  const [selectedTestSize, setSelectedTestSize] = useState(50);
  const [showOnlyIssues, setShowOnlyIssues] = useState(false);

  // Load current stock data on component mount
  useEffect(() => {
    loadStockData();
    loadParameters();
  }, []);

  const loadStockData = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/stocks');
      const stocks = await response.json();
      setCurrentStocks(stocks || []);
    } catch (error) {
      console.error('Error loading stock data:', error);
    }
  };

  const loadParameters = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/scoring/load-parameters');
      if (response.ok) {
        const params = await response.json();
        setParameters(prev => ({ ...prev, ...params }));
      }
    } catch (error) {
      console.error('Error loading parameters:', error);
    }
  };

  const handleParameterChange = (key: keyof ScoringParameters, value: number) => {
    setParameters(prev => ({ ...prev, [key]: value }));
  };

  const testNewScoring = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5001/api/scoring/test-parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: parameters,
          sample_size: selectedTestSize
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const results: TestResult[] = data.results.map((r: any) => ({
          ticker: r.ticker,
          old_score: r.old_score,
          new_score: r.new_score,
          score_change: r.score_change,
          old_recommendation: r.old_recommendation,
          new_recommendation: r.new_recommendation,
          recommendation_changed: r.recommendation_changed,
          layer_scores: r.layer_scores,
          issues: r.issues,
          data_issues: r.data_issues,
          has_enhanced_data: r.has_enhanced_data,
          calculation_details: r.calculation_details,
          fundamental_data: r.fundamental_data,
          data_quality: {
            missing_fundamentals: r.issues.includes('missing_quality_gate'),
            missing_technical: r.issues.includes('missing_dip_signal'),
            missing_volume: r.issues.includes('missing_reversal_spark'),
            error_count: r.issues.length
          }
        }));
        setTestResults(results);
      } else {
        console.error('Failed to test parameters');
      }
    } catch (error) {
      console.error('Error testing scoring:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const simulateScoring = async (stock: any): Promise<TestResult> => {
    // Simulate new scoring based on parameters
    // This would call the backend with new parameters or calculate locally
    
    const issues: string[] = [];
    const dataQuality = {
      missing_fundamentals: false,
      missing_technical: false,
      missing_volume: false,
      error_count: 0
    };

    // Check for data quality issues
    if (!stock.score_details?.layer_details?.quality_gate) {
      issues.push('Missing quality gate data');
      dataQuality.missing_fundamentals = true;
      dataQuality.error_count++;
    }
    
    if (!stock.score_details?.layer_details?.dip_signal) {
      issues.push('Missing dip signal data');
      dataQuality.missing_technical = true;
      dataQuality.error_count++;
    }
    
    if (!stock.score_details?.layer_details?.reversal_spark) {
      issues.push('Missing reversal spark data');
      dataQuality.missing_volume = true;
      dataQuality.error_count++;
    }

    // Get current scores
    const currentLayerScores = stock.score_details?.layer_scores || {};
    const oldScore = stock.score || 0;
    
    // Simulate new scores based on new parameters
    const newLayerScores = {
      quality_gate: (currentLayerScores.quality_gate || 0) * (parameters.quality_gate_weight / 35),
      dip_signal: (currentLayerScores.dip_signal || 0) * (parameters.dip_signal_weight / 45),
      reversal_spark: (currentLayerScores.reversal_spark || 0) * (parameters.reversal_spark_weight / 15),
      risk_adjustment: currentLayerScores.risk_adjustment || 0
    };
    
    const newScore = newLayerScores.quality_gate + newLayerScores.dip_signal + 
                    newLayerScores.reversal_spark + newLayerScores.risk_adjustment;

    // Determine recommendations
    const oldRecommendation = getRecommendation(oldScore, 'old');
    const newRecommendation = getRecommendation(newScore, 'new');

    return {
      ticker: stock.ticker,
      old_score: oldScore,
      new_score: newScore,
      score_change: newScore - oldScore,
      old_recommendation: oldRecommendation,
      new_recommendation: newRecommendation,
      recommendation_changed: oldRecommendation !== newRecommendation,
      layer_scores: newLayerScores,
      issues: issues,
      data_issues: false,
      has_enhanced_data: false,
      calculation_details: undefined,
      fundamental_data: undefined,
      data_quality: dataQuality
    };
  };

  const getRecommendation = (score: number, type: 'old' | 'new'): string => {
    const thresholds = type === 'new' ? parameters : {
      strong_buy_threshold: 80,
      buy_threshold: 70,
      watch_threshold: 50,
      avoid_threshold: 40
    };

    if (score >= thresholds.strong_buy_threshold) return 'STRONG_BUY';
    if (score >= thresholds.buy_threshold) return 'BUY';
    if (score >= thresholds.watch_threshold) return 'WATCH';
    if (score >= thresholds.avoid_threshold) return 'WEAK';
    return 'AVOID';
  };

  const saveParameters = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/scoring/save-parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parameters)
      });
      
      if (response.ok) {
        alert('Scoring parameters saved successfully!');
      } else {
        alert('Error saving parameters');
      }
    } catch (error) {
      console.error('Error saving parameters:', error);
      alert('Error saving parameters');
    }
  };

  const resetToDefaults = () => {
    const defaultParams: ScoringParameters = {
      // Layer weights
      quality_gate_weight: 35,
      dip_signal_weight: 45,
      reversal_spark_weight: 15,
      risk_adjustment_weight: 5,
      
      // Quality Gate
      quality_fcf_threshold: 0,
      quality_pe_multiplier: 25,
      quality_debt_ebitda_max: 3.0,
      quality_roe_min: 10,
      quality_margin_min: 5,
      
      // Dip Signal
      dip_sweet_spot_min: 15,
      dip_sweet_spot_max: 40,
      dip_rsi_oversold_min: 25,
      dip_rsi_oversold_max: 35,
      dip_volume_spike_min: 1.5,
      dip_volume_spike_max: 3.0,
      
      // Reversal Spark
      reversal_rsi_min: 30,
      reversal_volume_threshold: 1.2,
      reversal_price_action_weight: 1.0,
      
      // Recommendation thresholds
      strong_buy_threshold: 80,
      buy_threshold: 70,
      watch_threshold: 50,
      avoid_threshold: 40
    };
    
    setParameters(defaultParams);
  };

  const loadPreset = (presetName: string) => {
    const presets: Record<string, ScoringParameters> = {
      'amd_growth_dips': {
        // AMD-Style Growth Stock Dips (31% drop sweet spot)
        quality_gate_weight: 25,
        dip_signal_weight: 55,
        reversal_spark_weight: 15,
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 150,  // Allow high P/E growth stocks
        quality_debt_ebitda_max: 5.0,
        quality_roe_min: -5,  // Allow temporary losses
        quality_margin_min: 10,  // Require decent margins
        
        dip_sweet_spot_min: 20,  // 20-45% drop zone
        dip_sweet_spot_max: 45,
        dip_rsi_oversold_min: 20,  // Catch extreme oversold
        dip_rsi_oversold_max: 40,
        dip_volume_spike_min: 1.5,
        dip_volume_spike_max: 4.0,  // Allow panic selling
        
        reversal_rsi_min: 25,
        reversal_volume_threshold: 1.8,
        reversal_price_action_weight: 2.0,
        
        strong_buy_threshold: 75,  // More aggressive
        buy_threshold: 60,
        watch_threshold: 45,
        avoid_threshold: 30
      },
      
      'value_dividend_dips': {
        // Conservative Value/Dividend Stock Dips
        quality_gate_weight: 50,  // Heavy quality focus
        dip_signal_weight: 35,
        reversal_spark_weight: 10,
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 25,  // Traditional value P/E
        quality_debt_ebitda_max: 2.5,  // Conservative debt
        quality_roe_min: 12,  // Require profitability
        quality_margin_min: 8,  // Good margins
        
        dip_sweet_spot_min: 10,  // Smaller dips for stable stocks
        dip_sweet_spot_max: 30,
        dip_rsi_oversold_min: 25,
        dip_rsi_oversold_max: 35,
        dip_volume_spike_min: 1.2,  // Less volume needed
        dip_volume_spike_max: 2.5,
        
        reversal_rsi_min: 35,  // Conservative reversal
        reversal_volume_threshold: 1.1,
        reversal_price_action_weight: 0.8,
        
        strong_buy_threshold: 85,  // Very selective
        buy_threshold: 75,
        watch_threshold: 60,
        avoid_threshold: 45
      },
      
      'turnaround_recovery': {
        // Distressed/Turnaround Recovery Plays
        quality_gate_weight: 15,  // Minimal quality filter
        dip_signal_weight: 60,  // Focus on dip timing
        reversal_spark_weight: 20,  // Strong reversal signals needed
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 500,  // Allow any P/E (even negative)
        quality_debt_ebitda_max: 15.0,  // High debt tolerance
        quality_roe_min: -50,  // Allow big losses
        quality_margin_min: -30,  // Allow negative margins
        
        dip_sweet_spot_min: 40,  // Deep value territory
        dip_sweet_spot_max: 75,
        dip_rsi_oversold_min: 15,  // Extreme oversold
        dip_rsi_oversold_max: 30,
        dip_volume_spike_min: 2.0,  // Need significant volume
        dip_volume_spike_max: 8.0,
        
        reversal_rsi_min: 20,
        reversal_volume_threshold: 2.5,  // Strong volume confirmation
        reversal_price_action_weight: 2.5,
        
        strong_buy_threshold: 70,
        buy_threshold: 55,
        watch_threshold: 40,
        avoid_threshold: 25
      },
      
      'momentum_pullback': {
        // Momentum Stock Pullbacks (Buy the Dip in Uptrends)
        quality_gate_weight: 30,
        dip_signal_weight: 40,
        reversal_spark_weight: 25,  // High reversal weight
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 80,  // Moderate P/E tolerance
        quality_debt_ebitda_max: 4.0,
        quality_roe_min: 5,  // Require some profitability
        quality_margin_min: 3,
        
        dip_sweet_spot_min: 8,  // Shallow pullbacks
        dip_sweet_spot_max: 25,
        dip_rsi_oversold_min: 30,  // Not deeply oversold
        dip_rsi_oversold_max: 45,
        dip_volume_spike_min: 1.2,
        dip_volume_spike_max: 2.5,
        
        reversal_rsi_min: 35,  // Quick reversal signals
        reversal_volume_threshold: 1.5,
        reversal_price_action_weight: 2.8,  // Very sensitive to price action
        
        strong_buy_threshold: 78,
        buy_threshold: 65,
        watch_threshold: 50,
        avoid_threshold: 35
      },
      
      'earnings_reaction_dips': {
        // Post-Earnings Overreaction Dips
        quality_gate_weight: 35,
        dip_signal_weight: 45,
        reversal_spark_weight: 15,
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 60,
        quality_debt_ebitda_max: 3.5,
        quality_roe_min: 8,
        quality_margin_min: 5,
        
        dip_sweet_spot_min: 15,  // Earnings reactions
        dip_sweet_spot_max: 35,
        dip_rsi_oversold_min: 20,
        dip_rsi_oversold_max: 35,
        dip_volume_spike_min: 2.0,  // High volume from news
        dip_volume_spike_max: 6.0,
        
        reversal_rsi_min: 28,
        reversal_volume_threshold: 1.8,
        reversal_price_action_weight: 1.5,
        
        strong_buy_threshold: 80,
        buy_threshold: 68,
        watch_threshold: 52,
        avoid_threshold: 38
      },
      
      'market_crash_hunter': {
        // Market-Wide Crash/Correction Opportunities
        quality_gate_weight: 40,  // Quality matters in crashes
        dip_signal_weight: 50,
        reversal_spark_weight: 8,   // Less focus on immediate reversal
        risk_adjustment_weight: 2,   // Ignore market risk in crashes
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 35,  // Reasonable valuations
        quality_debt_ebitda_max: 2.0,  // Strong balance sheets
        quality_roe_min: 15,  // Profitable companies
        quality_margin_min: 10,
        
        dip_sweet_spot_min: 25,  // Deep market corrections
        dip_sweet_spot_max: 60,
        dip_rsi_oversold_min: 15,  // Extreme oversold
        dip_rsi_oversold_max: 30,
        dip_volume_spike_min: 2.0,
        dip_volume_spike_max: 10.0,  // Massive volume spikes
        
        reversal_rsi_min: 25,
        reversal_volume_threshold: 1.5,
        reversal_price_action_weight: 1.2,
        
        strong_buy_threshold: 82,
        buy_threshold: 70,
        watch_threshold: 55,
        avoid_threshold: 40
      },
      
      'quality_tech_dips': {
        // Quality Tech Stock Dips (Adobe-style 30-40% drops)
        quality_gate_weight: 40,  // Quality focus for tech
        dip_signal_weight: 45,
        reversal_spark_weight: 12,
        risk_adjustment_weight: 3,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 50,  // Reasonable for quality tech
        quality_debt_ebitda_max: 1.5,  // Low debt tech companies
        quality_roe_min: 20,  // High profitability required
        quality_margin_min: 15,  // Strong margins
        
        dip_sweet_spot_min: 25,  // Adobe-style 30-40% drops
        dip_sweet_spot_max: 50,
        dip_rsi_oversold_min: 20,
        dip_rsi_oversold_max: 35,
        dip_volume_spike_min: 1.5,
        dip_volume_spike_max: 4.0,
        
        reversal_rsi_min: 28,
        reversal_volume_threshold: 1.3,
        reversal_price_action_weight: 1.8,
        
        strong_buy_threshold: 80,
        buy_threshold: 68,
        watch_threshold: 55,
        avoid_threshold: 40
      },
      
      'blue_chip_pullbacks': {
        // Blue Chip Momentum Pullbacks (Mastercard-style 5-15% dips)
        quality_gate_weight: 45,  // Quality is key
        dip_signal_weight: 35,
        reversal_spark_weight: 15,
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 45,  // Premium valuations OK
        quality_debt_ebitda_max: 2.0,  // Strong balance sheets
        quality_roe_min: 25,  // Exceptional profitability
        quality_margin_min: 12,  // Strong margins
        
        dip_sweet_spot_min: 5,   // Shallow pullbacks
        dip_sweet_spot_max: 20,
        dip_rsi_oversold_min: 30,  // Not deeply oversold
        dip_rsi_oversold_max: 45,
        dip_volume_spike_min: 1.1,  // Minimal volume needed
        dip_volume_spike_max: 2.0,
        
        reversal_rsi_min: 35,
        reversal_volume_threshold: 1.2,
        reversal_price_action_weight: 2.2,
        
        strong_buy_threshold: 85,  // Very selective
        buy_threshold: 75,
        watch_threshold: 60,
        avoid_threshold: 45
      },
      
      'international_deep_value': {
        // International Deep Value Recovery (RR-style)
        quality_gate_weight: 20,  // Flexible quality for recovery
        dip_signal_weight: 55,  // Focus on dip timing
        reversal_spark_weight: 20,  // Strong reversal needed
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 200,  // Very flexible P/E
        quality_debt_ebitda_max: 8.0,  // Allow higher debt
        quality_roe_min: -20,  // Allow losses during recovery
        quality_margin_min: -10,  // Flexible margins
        
        dip_sweet_spot_min: 30,  // Deep value territory
        dip_sweet_spot_max: 70,
        dip_rsi_oversold_min: 15,
        dip_rsi_oversold_max: 35,
        dip_volume_spike_min: 1.8,
        dip_volume_spike_max: 6.0,
        
        reversal_rsi_min: 25,
        reversal_volume_threshold: 2.0,
        reversal_price_action_weight: 2.3,
        
        strong_buy_threshold: 72,
        buy_threshold: 58,
        watch_threshold: 42,
        avoid_threshold: 28
      },
      
      'defensive_dividend_dips': {
        // Defensive Dividend Stock Dips (McDonald's-style)
        quality_gate_weight: 55,  // Heavy quality focus
        dip_signal_weight: 30,
        reversal_spark_weight: 10,
        risk_adjustment_weight: 5,
        
        quality_fcf_threshold: 0,
        quality_pe_multiplier: 30,  // Conservative valuations
        quality_debt_ebitda_max: 3.0,
        quality_roe_min: 15,  // Consistent profitability
        quality_margin_min: 8,   // Decent margins
        
        dip_sweet_spot_min: 8,   // Smaller dips for defensive
        dip_sweet_spot_max: 25,
        dip_rsi_oversold_min: 25,
        dip_rsi_oversold_max: 40,
        dip_volume_spike_min: 1.1,
        dip_volume_spike_max: 2.2,
        
        reversal_rsi_min: 32,
        reversal_volume_threshold: 1.1,
        reversal_price_action_weight: 1.0,
        
        strong_buy_threshold: 83,
        buy_threshold: 72,
        watch_threshold: 58,
        avoid_threshold: 42
      }
    };
    
    if (presets[presetName]) {
      setParameters(presets[presetName]);
    }
  };

  const presetDescriptions = {
    'amd_growth_dips': {
      name: '🚀 Growth Stock Dips (AMD-Style)',
      description: 'Targets 20-45% drops in quality growth stocks with high P/E ratios. Perfect for AMD, NVIDIA, Tesla.',
      examples: 'AMD (31% drop), TSLA earnings reactions, NVDA pullbacks',
      strengths: 'Catches high-quality growth at discount prices',
      risks: 'May catch falling knives in growth corrections'
    },
    'value_dividend_dips': {
      name: '💰 Value & Dividend Dips',
      description: 'Conservative approach targeting 10-30% dips in profitable, low-debt companies with reasonable P/E ratios. Focus on quality over timing.',
      examples: 'JNJ, PG, KO, dividend aristocrats during market stress',
      strengths: 'Lower risk, steady compounders, dividend protection',
      risks: 'May miss explosive growth opportunities'
    },
    'turnaround_recovery': {
      name: '🔄 Turnaround Recovery Plays',
      description: 'Aggressive strategy for 40-75% drops in distressed companies showing reversal signals. High risk, high reward deep value plays.',
      examples: 'Bankruptcy recoveries, restructuring plays, cyclical bottoms',
      strengths: 'Massive upside potential, contrarian opportunities',
      risks: 'High failure rate, value traps, permanent capital loss'
    },
    'momentum_pullback': {
      name: '📈 Momentum Pullbacks',
      description: 'Shallow 8-25% dips in strong uptrending stocks. Buys temporary weakness in momentum leaders with quick reversal signals.',
      examples: 'AAPL pullbacks, QQQ dips, strong stocks in bull markets',
      strengths: 'Quick recoveries, trend continuation, lower drawdowns',
      risks: 'May miss deeper value opportunities, trend reversals'
    },
    'earnings_reaction_dips': {
      name: '📊 Earnings Overreaction Dips',
      description: 'Targets 15-35% drops following earnings announcements in quality companies. Catches market overreactions to temporary disappointments.',
      examples: 'Post-earnings selloffs, guidance cuts, temporary headwinds',
      strengths: 'Clear catalysts, often quick recoveries, predictable patterns',
      risks: 'Fundamental deterioration, guidance accuracy, sector rotation'
    },
    'market_crash_hunter': {
      name: '💥 Market Crash Hunter',
      description: 'Designed for major market corrections (25-60% drops). Focuses on quality companies with strong balance sheets during systemic selloffs.',
      examples: 'COVID crash, 2008 crisis, dot-com survivors, recession plays',
      strengths: 'Generational opportunities, quality at extreme discounts',
      risks: 'Timing challenges, extended bear markets, economic uncertainty'
    },
    'quality_tech_dips': {
      name: '💻 Quality Tech Dips (Adobe-style)',
      description: 'Targets 25-50% drops in quality tech stocks with high P/E ratios. Perfect for catching companies like Adobe, Microsoft, or Google during temporary selloffs.',
      examples: 'Adobe (31% drop), MSFT earnings reactions, GOOGL pullbacks',
      strengths: 'Catches high-quality tech at discount prices',
      risks: 'May catch falling knives in growth corrections'
    },
    'blue_chip_pullbacks': {
      name: '💳 Blue Chip Pullbacks (Mastercard-style)',
      description: 'Targets 5-20% dips in blue chip stocks with high P/E ratios. Perfect for catching companies like Mastercard, Visa, or JNJ during temporary selloffs.',
      examples: 'Mastercard (10% drop), V earnings reactions, JNJ pullbacks',
      strengths: 'Catches high-quality blue chips at discount prices',
      risks: 'May catch falling knives in growth corrections'
    },
    'international_deep_value': {
      name: '🌍 International Deep Value Recovery (RR-style)',
      description: 'Targets 30-70% drops in international stocks with high P/E ratios. Perfect for catching companies like NIO, BYD, or Tencent during temporary selloffs.',
      examples: 'NIO (31% drop), BYD earnings reactions, TCEHY pullbacks',
      strengths: 'Catches high-quality international stocks at discount prices',
      risks: 'May catch falling knives in growth corrections'
    },
    'defensive_dividend_dips': {
      name: '🍔 Defensive Dividend Dips (McDonald\'s-style)',
      description: 'Targets 8-25% dips in profitable, low-debt dividend stocks. Perfect for catching companies like PG, KO, or MCD during market stress.',
      examples: 'PG (10% drop), KO earnings reactions, MCD pullbacks',
      strengths: 'Lower risk, steady compounders, dividend protection',
      risks: 'May miss explosive growth opportunities'
    }
  };

  const filteredResults = showOnlyIssues 
    ? testResults.filter(r => r.issues.length > 0 || r.data_quality.error_count > 0)
    : testResults;

  const recommendationStats = testResults.reduce((acc, result) => {
    acc[result.new_recommendation] = (acc[result.new_recommendation] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-4">
          <span className="text-4xl">🎯</span>
          <div>
            <h1 className="text-3xl font-bold text-white">Scoring Algorithm Tuner</h1>
            <p className="text-slate-400 mt-1">
              Optimize buy-the-dip scoring parameters in real-time. Current stocks: {currentStocks.length}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        <div className="xl:col-span-2 space-y-6">
          {/* Layer Weights */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">⚖️ Layer Weights</h2>
            <p className="text-sm text-slate-400 mb-4">
              Controls how much each scoring layer contributes to the final score. Higher weights = more influence.
              Total should equal 100%.
            </p>
            <div className="space-y-4">
              {[
                { key: 'quality_gate_weight', label: 'Quality Gate', description: 'Filters out fundamentally weak companies' },
                { key: 'dip_signal_weight', label: 'Dip Signal', description: 'Identifies stocks at good discount levels' },
                { key: 'reversal_spark_weight', label: 'Reversal Spark', description: 'Detects potential upward momentum' },
                { key: 'risk_adjustment_weight', label: 'Risk Adjustment', description: 'Reduces scores for high-risk stocks' },
              ].map(({ key, label, description }) => (
                <div key={key}>
                  <label className="block text-sm text-slate-400 mb-1">{label}</label>
                  <div className="flex items-center space-x-3">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={parameters[key as keyof ScoringParameters]}
                      onChange={(e) => handleParameterChange(key as keyof ScoringParameters, Number(e.target.value))}
                      className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                      aria-label={`${label} weight`}
                    />
                    <span className="text-white font-mono w-8 text-right">
                      {parameters[key as keyof ScoringParameters]}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{description}</p>
                </div>
              ))}
            </div>
            <div className="mt-3 text-sm text-slate-400">
              Total: {Object.keys(parameters)
                .filter(k => k.endsWith('_weight'))
                .reduce((sum, k) => sum + parameters[k as keyof ScoringParameters], 0)}%
            </div>
          </div>

          {/* Quality Gate */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">✅ Quality Gate</h2>
            <p className="text-sm text-slate-400 mb-4">
              Fundamental analysis thresholds to ensure we only consider financially healthy companies.
              Stricter values = fewer but higher quality stocks pass.
            </p>
            <div className="space-y-4">
              {[
                { 
                  key: 'quality_pe_multiplier', 
                  label: 'Max P/E Ratio', 
                  min: -50, 
                  max: 500, 
                  step: 5,
                  description: 'Maximum P/E ratio allowed (negative P/E = losses, 25 = value stocks, 200+ = growth stocks)'
                },
                { 
                  key: 'quality_debt_ebitda_max', 
                  label: 'Max Debt/EBITDA', 
                  min: 0, 
                  max: 20, 
                  step: 0.5,
                  description: 'Maximum debt-to-EBITDA ratio (e.g., 3.0 = reject if debt > 3x EBITDA, higher for distressed)'
                },
                { 
                  key: 'quality_roe_min', 
                  label: 'Min ROE %', 
                  min: -100, 
                  max: 50, 
                  step: 1,
                  description: 'Minimum Return on Equity percentage (negative = losses, 10+ = profitable, -50+ = turnaround plays)'
                },
                { 
                  key: 'quality_margin_min', 
                  label: 'Min Profit Margin %', 
                  min: -100, 
                  max: 50, 
                  step: 1,
                  description: 'Minimum profit margin percentage (negative = losses, 5+ = profitable, -30+ = recovery plays)'
                },
              ].map(({ key, label, min, max, step, description }) => (
                <div key={key}>
                  <label className="block text-sm text-slate-400 mb-1">{label}</label>
                  <div className="flex items-center space-x-3">
                    <input
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={parameters[key as keyof ScoringParameters]}
                      onChange={(e) => handleParameterChange(key as keyof ScoringParameters, Number(e.target.value))}
                      className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                      aria-label={`${label} threshold`}
                    />
                    <span className="text-white font-mono w-16 text-right">
                      {key.includes('pe_multiplier') ? 
                        `${parameters[key as keyof ScoringParameters]}x` :
                        key.includes('debt_ebitda') ? 
                        `${Number(parameters[key as keyof ScoringParameters]).toFixed(1)}x` :
                        `${parameters[key as keyof ScoringParameters]}%`
                      }
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Dip Signal */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">📉 Dip Signal</h2>
            <p className="text-sm text-slate-400 mb-4">
              Identifies stocks at attractive discount levels. The "sweet spot" is the ideal price drop range
              where stocks are discounted but not in freefall.
            </p>
            <div className="space-y-4">
              {[
                { 
                  key: 'dip_sweet_spot_min', 
                  label: 'Sweet Spot Min %', 
                  min: 0, 
                  max: 50, 
                  step: 1,
                  description: 'Minimum % below 52-week high (e.g., 10 = must be down at least 10%)'
                },
                { 
                  key: 'dip_sweet_spot_max', 
                  label: 'Sweet Spot Max %', 
                  min: 20, 
                  max: 80, 
                  step: 1,
                  description: 'Maximum % below 52-week high (e.g., 50 = avoid if down more than 50%)'
                },
                { 
                  key: 'dip_rsi_oversold_min', 
                  label: 'RSI Oversold Min', 
                  min: 10, 
                  max: 40, 
                  step: 1,
                  description: 'Minimum RSI for oversold (e.g., 20 = RSI must be between 20-35 for signal)'
                },
                { 
                  key: 'dip_rsi_oversold_max', 
                  label: 'RSI Oversold Max', 
                  min: 25, 
                  max: 50, 
                  step: 1,
                  description: 'Maximum RSI for oversold (e.g., 35 = RSI must be ≤ 35 for oversold signal)'
                },
                { 
                  key: 'dip_volume_spike_min', 
                  label: 'Volume Spike Min', 
                  min: 1.0, 
                  max: 5.0, 
                  step: 0.1,
                  description: 'Minimum volume vs average (e.g., 1.5 = volume must be ≥ 1.5x normal)'
                },
                { 
                  key: 'dip_volume_spike_max', 
                  label: 'Volume Spike Max', 
                  min: 2.0, 
                  max: 10.0, 
                  step: 0.1,
                  description: 'Maximum volume vs average (e.g., 5.0 = avoid if volume > 5x normal = panic)'
                },
              ].map(({ key, label, min, max, step, description }) => (
                <div key={key}>
                  <label className="block text-sm text-slate-400 mb-1">{label}</label>
                  <div className="flex items-center space-x-3">
                    <input
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={parameters[key as keyof ScoringParameters]}
                      onChange={(e) => handleParameterChange(key as keyof ScoringParameters, Number(e.target.value))}
                      className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                      aria-label={`${label} threshold`}
                    />
                    <span className="text-white font-mono w-12 text-right">
                      {key.includes('volume') ? 
                        `${Number(parameters[key as keyof ScoringParameters]).toFixed(1)}x` : 
                        key.includes('rsi') ? 
                        `${parameters[key as keyof ScoringParameters]}` :
                        `${parameters[key as keyof ScoringParameters]}%`
                      }
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Reversal Spark */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">🚀 Reversal Spark</h2>
            <p className="text-sm text-slate-400 mb-4">
              Detects early signs of potential upward momentum after a dip. Higher values = more sensitive
              to momentum signals but potentially more false positives.
            </p>
            <div className="space-y-4">
              {[
                { 
                  key: 'reversal_rsi_min', 
                  label: 'Min RSI for Reversal', 
                  min: 15, 
                  max: 60, 
                  step: 1,
                  description: 'Minimum RSI to signal potential reversal (e.g., 30 = RSI must be ≥ 30)'
                },
                { 
                  key: 'reversal_volume_threshold', 
                  label: 'Volume Threshold', 
                  min: 1.0, 
                  max: 5.0, 
                  step: 0.1,
                  description: 'Volume multiplier needed for reversal (e.g., 2.0 = need 2x average volume)'
                },
                { 
                  key: 'reversal_price_action_weight', 
                  label: 'Price Action Weight', 
                  min: 0.1, 
                  max: 3.0, 
                  step: 0.1,
                  description: 'How much to weight recent price moves (higher = more sensitive to price)'
                },
              ].map(({ key, label, min, max, step, description }) => (
                <div key={key}>
                  <label className="block text-sm text-slate-400 mb-1">{label}</label>
                  <div className="flex items-center space-x-3">
                    <input
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={parameters[key as keyof ScoringParameters]}
                      onChange={(e) => handleParameterChange(key as keyof ScoringParameters, Number(e.target.value))}
                      className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                      aria-label={`${label} setting`}
                    />
                    <span className="text-white font-mono w-12 text-right">
                      {key.includes('volume') ? 
                        `${Number(parameters[key as keyof ScoringParameters]).toFixed(1)}x` :
                        key.includes('weight') ?
                        `${Number(parameters[key as keyof ScoringParameters]).toFixed(1)}` :
                        `${parameters[key as keyof ScoringParameters]}`
                      }
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Recommendation Thresholds */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">🎯 Recommendation Thresholds</h2>
            <p className="text-sm text-slate-400 mb-4">
              Score thresholds that determine buy/sell recommendations. Higher thresholds = more selective,
              lower thresholds = more recommendations but potentially lower quality.
            </p>
            <div className="space-y-4">
              {[
                { 
                  key: 'strong_buy_threshold', 
                  label: 'Strong Buy', 
                  min: 50, 
                  max: 95, 
                  step: 1,
                  description: 'Score needed for highest confidence recommendation (out of 100)'
                },
                { 
                  key: 'buy_threshold', 
                  label: 'Buy', 
                  min: 40, 
                  max: 85, 
                  step: 1,
                  description: 'Score needed for standard buy recommendation (out of 100)'
                },
                { 
                  key: 'watch_threshold', 
                  label: 'Watch', 
                  min: 20, 
                  max: 70, 
                  step: 1,
                  description: 'Score needed to add to watchlist (monitor but dont buy yet)'
                },
                { 
                  key: 'avoid_threshold', 
                  label: 'Avoid', 
                  min: 10, 
                  max: 60, 
                  step: 1,
                  description: 'Scores below this are marked as avoid (out of 100)'
                },
              ].map(({ key, label, min, max, step, description }) => (
                <div key={key}>
                  <label className="block text-sm text-slate-400 mb-1">{label}</label>
                  <div className="flex items-center space-x-3">
                    <input
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={parameters[key as keyof ScoringParameters]}
                      onChange={(e) => handleParameterChange(key as keyof ScoringParameters, Number(e.target.value))}
                      className="flex-1 h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer"
                      aria-label={`${label} recommendation threshold`}
                    />
                    <span className="text-white font-mono w-8 text-right">
                      {parameters[key as keyof ScoringParameters]}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Preset Configurations */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">🎯 Strategy Presets</h2>
            <p className="text-sm text-slate-400 mb-4">
              Pre-configured settings optimized for different types of dip opportunities. 
              Each preset targets specific market conditions and stock characteristics.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">🚀 Growth Stock Dips (AMD-Style)</h3>
                  <button
                    onClick={() => loadPreset('amd_growth_dips')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Targets 20-45% drops in quality growth stocks with high P/E ratios. Perfect for AMD, NVIDIA, Tesla.</p>
                <div className="text-xs text-green-400">✓ High-quality growth at discount prices</div>
                <div className="text-xs text-red-400">⚠ May catch falling knives in corrections</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">💰 Value & Dividend Dips</h3>
                  <button
                    onClick={() => loadPreset('value_dividend_dips')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Conservative 10-30% dips in profitable, low-debt dividend stocks. JNJ, PG, KO style.</p>
                <div className="text-xs text-green-400">✓ Lower risk, steady compounders, dividend protection</div>
                <div className="text-xs text-red-400">⚠ May miss explosive growth opportunities</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">🔄 Turnaround Recovery</h3>
                  <button
                    onClick={() => loadPreset('turnaround_recovery')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Aggressive 40-75% drops in distressed companies. High risk, high reward deep value.</p>
                <div className="text-xs text-green-400">✓ Massive upside potential, contrarian opportunities</div>
                <div className="text-xs text-red-400">⚠ High failure rate, value traps, permanent loss</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">📈 Momentum Pullbacks</h3>
                  <button
                    onClick={() => loadPreset('momentum_pullback')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Shallow 8-25% dips in uptrending stocks. AAPL pullbacks, QQQ dips, trend continuation.</p>
                <div className="text-xs text-green-400">✓ Quick recoveries, lower drawdowns</div>
                <div className="text-xs text-red-400">⚠ May miss deeper value, trend reversals</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">📊 Earnings Overreactions</h3>
                  <button
                    onClick={() => loadPreset('earnings_reaction_dips')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">15-35% post-earnings drops in quality companies. Clear catalysts, quick recoveries.</p>
                <div className="text-xs text-green-400">✓ Predictable patterns, clear catalysts</div>
                <div className="text-xs text-red-400">⚠ Fundamental deterioration, sector rotation</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">💥 Market Crash Hunter</h3>
                  <button
                    onClick={() => loadPreset('market_crash_hunter')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">25-60% drops during market corrections. Quality companies at extreme discounts.</p>
                <div className="text-xs text-green-400">✓ Generational opportunities, quality at discounts</div>
                <div className="text-xs text-red-400">⚠ Timing challenges, extended bear markets</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">💻 Quality Tech Dips (Adobe-style)</h3>
                  <button
                    onClick={() => loadPreset('quality_tech_dips')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Targets 25-50% drops in quality tech stocks with high P/E ratios. Perfect for Adobe, Microsoft, or Google.</p>
                <div className="text-xs text-green-400">✓ Catches high-quality tech at discount prices</div>
                <div className="text-xs text-red-400">⚠ May catch falling knives in growth corrections</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">💳 Blue Chip Pullbacks (Mastercard-style)</h3>
                  <button
                    onClick={() => loadPreset('blue_chip_pullbacks')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Targets 5-20% dips in blue chip stocks with high P/E ratios. Perfect for Mastercard, Visa, or JNJ.</p>
                <div className="text-xs text-green-400">✓ Catches high-quality blue chips at discount prices</div>
                <div className="text-xs text-red-400">⚠ May catch falling knives in growth corrections</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">🌍 International Deep Value Recovery</h3>
                  <button
                    onClick={() => loadPreset('international_deep_value')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Targets 30-70% drops in international stocks with high P/E ratios. Perfect for NIO, BYD, or Tencent.</p>
                <div className="text-xs text-green-400">✓ Catches high-quality international stocks at discount prices</div>
                <div className="text-xs text-red-400">⚠ May catch falling knives in growth corrections</div>
              </div>

              <div className="bg-slate-700 rounded-lg p-3 hover:bg-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-white text-sm">🍔 Defensive Dividend Dips (McDonald's-style)</h3>
                  <button
                    onClick={() => loadPreset('defensive_dividend_dips')}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition-colors"
                  >
                    Load
                  </button>
                </div>
                <p className="text-xs text-slate-300 mb-2">Targets 8-25% dips in profitable, low-debt dividend stocks. Perfect for PG, KO, or MCD.</p>
                <div className="text-xs text-green-400">✓ Lower risk, steady compounders, dividend protection</div>
                <div className="text-xs text-red-400">⚠ May miss explosive growth opportunities</div>
              </div>
            </div>
            
            <div className="text-xs text-slate-500 bg-slate-900 rounded p-3">
              <strong>💡 Usage Tips:</strong> Start with a preset matching your risk tolerance. 
              Test with different sample sizes to see performance. Fine-tune based on results.
            </div>
          </div>

          {/* Control Buttons */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">🎮 Controls</h2>
            <div className="space-y-3">
              <div>
                <label htmlFor="testSampleSize" className="block text-sm text-slate-400 mb-1">Test Sample Size</label>
                <select 
                  id="testSampleSize"
                  value={selectedTestSize}
                  onChange={(e) => setSelectedTestSize(Number(e.target.value))}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
                  aria-label="Select test sample size"
                >
                  <option value={25}>25 stocks</option>
                  <option value={50}>50 stocks</option>
                  <option value={100}>100 stocks</option>
                  <option value={250}>250 stocks</option>
                </select>
              </div>
              
              <button
                onClick={testNewScoring}
                disabled={isLoading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-bold py-3 px-4 rounded-lg transition-colors"
              >
                {isLoading ? '🔄 Testing...' : '🧪 Test New Scoring'}
              </button>
              
              <button
                onClick={saveParameters}
                className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg transition-colors"
              >
                💾 Save Parameters
              </button>
              
              <button
                onClick={resetToDefaults}
                className="w-full bg-slate-600 hover:bg-slate-700 text-white font-bold py-3 px-4 rounded-lg transition-colors"
              >
                🔄 Reset to Defaults
              </button>
            </div>
          </div>
        </div>

        {/* Results Panel */}
        <div className="xl:col-span-2 space-y-6">
          
          {/* Statistics */}
          {testResults.length > 0 && (
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4">📊 Test Results Summary</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(recommendationStats).map(([rec, count]) => (
                  <div key={rec} className="bg-slate-700 rounded-lg p-3 text-center">
                    <div className="text-sm text-slate-400">{rec.replace('_', ' ')}</div>
                    <div className="text-xl font-bold text-white">{count}</div>
                    <div className="text-xs text-slate-500">
                      {((count / testResults.length) * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-slate-700 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Enhanced Data</div>
                  <div className="text-xl font-bold text-green-400">
                    {testResults.filter(r => r.has_enhanced_data).length}
                  </div>
                  <div className="text-xs text-slate-500">
                    Full scoring available
                  </div>
                </div>
                <div className="bg-slate-700 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Basic Data</div>
                  <div className="text-xl font-bold text-blue-400">
                    {testResults.filter(r => !r.has_enhanced_data).length}
                  </div>
                  <div className="text-xs text-slate-500">
                    Fundamental calculation
                  </div>
                </div>
                <div className="bg-slate-700 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Avg Score Change</div>
                  <div className="text-xl font-bold text-white">
                    {testResults.length > 0 ? 
                      (testResults.reduce((sum, r) => sum + r.score_change, 0) / testResults.length).toFixed(1) : 
                      '0'
                    }
                  </div>
                  <div className="text-xs text-slate-500">
                    Parameter impact
                  </div>
                </div>
                <div className="bg-slate-700 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Data Issues</div>
                  <div className="text-xl font-bold text-red-400">
                    {testResults.filter(r => r.issues.length > 0).length}
                  </div>
                  <div className="text-xs text-slate-500">
                    Missing/problematic data
                  </div>
                </div>
                <div className="bg-slate-700 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Recommendation Changes</div>
                  <div className="text-xl font-bold text-yellow-400">
                    {testResults.filter(r => r.recommendation_changed).length}
                  </div>
                  <div className="text-xs text-slate-500">
                    Changed categories
                  </div>
                </div>
                <div className="bg-slate-700 rounded-lg p-3">
                  <div className="text-sm text-slate-400">Unique Tickers</div>
                  <div className="text-xl font-bold text-white">
                    {new Set(testResults.map(r => r.ticker)).size}
                  </div>
                  <div className="text-xs text-slate-500">
                    Different companies tested
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Results Table */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">📋 Detailed Results</h2>
              <div className="flex items-center space-x-2">
                <label className="flex items-center space-x-2 text-slate-300">
                  <input
                    type="checkbox"
                    checked={showOnlyIssues}
                    onChange={(e) => setShowOnlyIssues(e.target.checked)}
                    className="rounded"
                  />
                  <span>Show only issues</span>
                </label>
              </div>
            </div>

            {filteredResults.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-600">
                      <th className="text-left py-2 text-slate-300">Ticker</th>
                      <th className="text-right py-2 text-slate-300">Score Change</th>
                      <th className="text-right py-2 text-slate-300">New Score</th>
                      <th className="text-center py-2 text-slate-300">New Rec</th>
                      <th className="text-center py-2 text-slate-300">Data Source</th>
                      <th className="text-center py-2 text-slate-300">Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredResults.slice(0, 50).map((result) => (
                      <tr key={result.ticker} className="border-b border-slate-700 hover:bg-slate-700">
                        <td className="py-2 text-white font-mono">{result.ticker}</td>
                        <td className="py-2 text-right">
                          <span className={`font-bold ${
                            result.score_change > 0 ? 'text-green-400' : 
                            result.score_change < 0 ? 'text-red-400' : 'text-slate-300'
                          }`}>
                            {result.score_change > 0 ? '+' : ''}{result.score_change.toFixed(1)}
                          </span>
                        </td>
                        <td className="py-2 text-right text-white font-bold">{result.new_score.toFixed(1)}</td>
                        <td className="py-2 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            result.new_recommendation === 'STRONG_BUY' ? 'bg-green-900 text-green-300' :
                            result.new_recommendation === 'BUY' ? 'bg-blue-900 text-blue-300' :
                            result.new_recommendation === 'WATCH' ? 'bg-yellow-900 text-yellow-300' :
                            'bg-red-900 text-red-300'
                          }`}>
                            {result.new_recommendation}
                          </span>
                          {result.recommendation_changed && (
                            <span className="ml-1 text-yellow-400" title="Recommendation changed">🔄</span>
                          )}
                        </td>
                        <td className="py-2 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            result.has_enhanced_data ? 'bg-green-900 text-green-300' : 'bg-blue-900 text-blue-300'
                          }`}>
                            {result.has_enhanced_data ? 'Enhanced' : 'Basic'}
                          </span>
                        </td>
                        <td className="py-2 text-center">
                          {result.issues.length > 0 && (
                            <span className="text-red-400 cursor-help mr-1" title={result.issues.join(', ')}>
                              ⚠️ {result.issues.length}
                            </span>
                          )}
                          {result.calculation_details && (
                            <span 
                              className="text-blue-400 cursor-help" 
                              title={Object.entries(result.calculation_details)
                                .filter(([k]) => k !== 'method')
                                .map(([k, v]) => `${k}: ${v}`)
                                .join('\n')}
                            >
                              ℹ️
                            </span>
                          )}
                          {result.fundamental_data && (
                            <span 
                              className="text-green-400 cursor-help ml-1" 
                              title={`P/E: ${result.fundamental_data.pe_ratio || 'N/A'}, Market Cap: $${
                                result.fundamental_data.market_cap ? 
                                (result.fundamental_data.market_cap / 1e9).toFixed(1) + 'B' : 'N/A'
                              }, Beta: ${result.fundamental_data.beta || 'N/A'}`}
                            >
                              📊
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-slate-400">
                {testResults.length === 0 ? 'Run a test to see results' : 'No issues found'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScoringTuningPage; 