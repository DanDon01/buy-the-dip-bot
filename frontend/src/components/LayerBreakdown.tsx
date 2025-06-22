import React, { useState } from 'react';

interface CalculationDetails {
  quality_gate?: {
    pe_ratio_check?: { value: number; passes: boolean; points: number };
    market_cap_tier?: { value: string; points: number };
    dividend_bonus?: { yield: number; points: number };
    financial_strength?: { debt_ratio: number; points: number };
    overall_pass?: boolean;
  };
  dip_signal?: {
    pct_drop_from_high?: { value: number; points: number };
    rsi_oversold?: { value: number; points: number };
    volume_surge?: { multiplier: number; points: number };
    ma_position?: { below_ma: boolean; points: number };
  };
  reversal_spark?: {
    momentum_indicators?: { macd: string; rsi: string; points: number };
    beta_analysis?: { beta: number; points: number };
    volatility_score?: { value: number; points: number };
  };
  risk_modifiers?: {
    market_cap_safety?: { tier: string; adjustment: number };
    dividend_protection?: { yield: number; adjustment: number };
    sector_momentum?: { score: number; adjustment: number };
  };
}

interface LayerData {
  layer_scores?: {
    quality_gate?: number;
    dip_signal?: number;
    reversal_spark?: number;
    risk_adjustment?: number;
  };
  calculation_details?: CalculationDetails;
  overall_grade?: string;
  score?: number;
}

interface LayerBreakdownProps {
  data: LayerData;
  ticker: string;
}

const LayerBreakdown: React.FC<LayerBreakdownProps> = ({ data, ticker }) => {
  const [expandedLayer, setExpandedLayer] = useState<string | null>(null);

  const toggleLayer = (layerName: string) => {
    setExpandedLayer(expandedLayer === layerName ? null : layerName);
  };

  const getGradeColor = (grade: string) => {
    const gradeColors: { [key: string]: string } = {
      'A+': 'text-green-400', 'A': 'text-green-400', 'A-': 'text-green-500',
      'B+': 'text-blue-400', 'B': 'text-blue-400', 'B-': 'text-blue-500',
      'C+': 'text-yellow-400', 'C': 'text-yellow-400', 'C-': 'text-yellow-500',
      'D+': 'text-orange-400', 'D': 'text-orange-400', 'D-': 'text-orange-500',
      'F': 'text-red-400'
    };
    return gradeColors[grade] || 'text-slate-400';
  };

  const getScoreGrade = (score: number, maxScore: number) => {
    const percentage = (score / maxScore) * 100;
    if (percentage >= 90) return 'A+';
    if (percentage >= 85) return 'A';
    if (percentage >= 80) return 'A-';
    if (percentage >= 75) return 'B+';
    if (percentage >= 70) return 'B';
    if (percentage >= 65) return 'B-';
    if (percentage >= 60) return 'C+';
    if (percentage >= 55) return 'C';
    if (percentage >= 50) return 'C-';
    if (percentage >= 45) return 'D+';
    if (percentage >= 40) return 'D';
    if (percentage >= 35) return 'D-';
    return 'F';
  };

  const formatValue = (value: any): string => {
    if (typeof value === 'number') {
      if (value % 1 === 0) return value.toString();
      return value.toFixed(2);
    }
    return value?.toString() || 'N/A';
  };

  const getPassFailColor = (passes: boolean) => passes ? 'text-green-400' : 'text-red-400';
  const getPointsColor = (points: number, maxPoints: number = 10) => {
    const ratio = points / maxPoints;
    if (ratio >= 0.8) return 'text-green-400';
    if (ratio >= 0.6) return 'text-yellow-400';
    if (ratio >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  return (
    <div className="space-y-4">
      <h3 className="text-xl font-bold text-white mb-4">Layer-by-Layer Analysis</h3>

      {/* Quality Gate Layer */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <button
          onClick={() => toggleLayer('quality')}
          className="w-full p-4 flex items-center justify-between hover:bg-slate-700 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-blue-500 rounded"></div>
            <span className="font-semibold text-white">Quality Gate (35% Weight)</span>
            <span className={`text-sm ${getGradeColor(getScoreGrade(data.layer_scores?.quality_gate || 0, 35))}`}>
              Grade {getScoreGrade(data.layer_scores?.quality_gate || 0, 35)}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-blue-400">{formatValue(data.layer_scores?.quality_gate)}/35</span>
            <span className="text-slate-400">
              {expandedLayer === 'quality' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'quality' && data.calculation_details?.quality_gate && (
          <div className="p-4 border-t border-slate-700 space-y-3">
            <div className="text-sm text-slate-300 mb-3">
              Business quality analysis including valuation, financial strength, and profitability metrics.
            </div>
            
            {data.calculation_details.quality_gate.pe_ratio_check && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">P/E Ratio Check</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{formatValue(data.calculation_details.quality_gate.pe_ratio_check.value)}</span>
                  <span className={getPassFailColor(data.calculation_details.quality_gate.pe_ratio_check.passes)}>
                    {data.calculation_details.quality_gate.pe_ratio_check.passes ? '✓' : '✗'}
                  </span>
                  <span className={getPointsColor(data.calculation_details.quality_gate.pe_ratio_check.points)}>
                    +{formatValue(data.calculation_details.quality_gate.pe_ratio_check.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.quality_gate.market_cap_tier && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Market Cap Tier</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{data.calculation_details.quality_gate.market_cap_tier.value}</span>
                  <span className={getPointsColor(data.calculation_details.quality_gate.market_cap_tier.points)}>
                    +{formatValue(data.calculation_details.quality_gate.market_cap_tier.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.quality_gate.dividend_bonus && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Dividend Bonus</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{formatValue(data.calculation_details.quality_gate.dividend_bonus.yield * 100)}%</span>
                  <span className={getPointsColor(data.calculation_details.quality_gate.dividend_bonus.points)}>
                    +{formatValue(data.calculation_details.quality_gate.dividend_bonus.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.quality_gate.financial_strength && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Financial Strength</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">Debt Ratio: {formatValue(data.calculation_details.quality_gate.financial_strength.debt_ratio)}</span>
                  <span className={getPointsColor(data.calculation_details.quality_gate.financial_strength.points)}>
                    +{formatValue(data.calculation_details.quality_gate.financial_strength.points)}
                  </span>
                </div>
              </div>
            )}

            <div className="border-t border-slate-600 pt-3 mt-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-300 font-medium">Overall Quality Gate:</span>
                <span className={getPassFailColor(data.calculation_details.quality_gate.overall_pass || false)}>
                  {data.calculation_details.quality_gate.overall_pass ? 'PASS' : 'FAIL'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Dip Signal Layer */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <button
          onClick={() => toggleLayer('dip')}
          className="w-full p-4 flex items-center justify-between hover:bg-slate-700 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-red-500 rounded"></div>
            <span className="font-semibold text-white">Dip Signal (45% Weight)</span>
            <span className={`text-sm ${getGradeColor(getScoreGrade(data.layer_scores?.dip_signal || 0, 45))}`}>
              Grade {getScoreGrade(data.layer_scores?.dip_signal || 0, 45)}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-red-400">{formatValue(data.layer_scores?.dip_signal)}/45</span>
            <span className="text-slate-400">
              {expandedLayer === 'dip' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'dip' && data.calculation_details?.dip_signal && (
          <div className="p-4 border-t border-slate-700 space-y-3">
            <div className="text-sm text-slate-300 mb-3">
              Core dip detection analyzing price drops, technical indicators, and volume patterns.
            </div>

            {data.calculation_details.dip_signal.pct_drop_from_high && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Drop from 52W High</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{formatValue(data.calculation_details.dip_signal.pct_drop_from_high.value)}%</span>
                  <span className={getPointsColor(data.calculation_details.dip_signal.pct_drop_from_high.points, 15)}>
                    +{formatValue(data.calculation_details.dip_signal.pct_drop_from_high.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.dip_signal.rsi_oversold && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">RSI Oversold Signal</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">RSI: {formatValue(data.calculation_details.dip_signal.rsi_oversold.value)}</span>
                  <span className={getPointsColor(data.calculation_details.dip_signal.rsi_oversold.points, 15)}>
                    +{formatValue(data.calculation_details.dip_signal.rsi_oversold.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.dip_signal.volume_surge && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Volume Surge</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{formatValue(data.calculation_details.dip_signal.volume_surge.multiplier)}x avg</span>
                  <span className={getPointsColor(data.calculation_details.dip_signal.volume_surge.points, 15)}>
                    +{formatValue(data.calculation_details.dip_signal.volume_surge.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.dip_signal.ma_position && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Moving Average Position</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{data.calculation_details.dip_signal.ma_position.below_ma ? 'Below MA' : 'Above MA'}</span>
                  <span className={getPointsColor(data.calculation_details.dip_signal.ma_position.points, 15)}>
                    +{formatValue(data.calculation_details.dip_signal.ma_position.points)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Reversal Spark Layer */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <button
          onClick={() => toggleLayer('reversal')}
          className="w-full p-4 flex items-center justify-between hover:bg-slate-700 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span className="font-semibold text-white">Reversal Spark (15% Weight)</span>
            <span className={`text-sm ${getGradeColor(getScoreGrade(data.layer_scores?.reversal_spark || 0, 15))}`}>
              Grade {getScoreGrade(data.layer_scores?.reversal_spark || 0, 15)}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-green-400">{formatValue(data.layer_scores?.reversal_spark)}/15</span>
            <span className="text-slate-400">
              {expandedLayer === 'reversal' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'reversal' && data.calculation_details?.reversal_spark && (
          <div className="p-4 border-t border-slate-700 space-y-3">
            <div className="text-sm text-slate-300 mb-3">
              Early momentum shift detection through technical indicators and volatility analysis.
            </div>

            {data.calculation_details.reversal_spark.momentum_indicators && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Momentum Indicators</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">
                    MACD: {data.calculation_details.reversal_spark.momentum_indicators.macd}, 
                    RSI: {data.calculation_details.reversal_spark.momentum_indicators.rsi}
                  </span>
                  <span className={getPointsColor(data.calculation_details.reversal_spark.momentum_indicators.points, 8)}>
                    +{formatValue(data.calculation_details.reversal_spark.momentum_indicators.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.reversal_spark.beta_analysis && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Beta Analysis</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">β: {formatValue(data.calculation_details.reversal_spark.beta_analysis.beta)}</span>
                  <span className={getPointsColor(data.calculation_details.reversal_spark.beta_analysis.points, 4)}>
                    +{formatValue(data.calculation_details.reversal_spark.beta_analysis.points)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.reversal_spark.volatility_score && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Volatility Score</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{formatValue(data.calculation_details.reversal_spark.volatility_score.value)}</span>
                  <span className={getPointsColor(data.calculation_details.reversal_spark.volatility_score.points, 3)}>
                    +{formatValue(data.calculation_details.reversal_spark.volatility_score.points)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Risk Modifiers Layer */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <button
          onClick={() => toggleLayer('risk')}
          className="w-full p-4 flex items-center justify-between hover:bg-slate-700 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="w-4 h-4 bg-amber-500 rounded"></div>
            <span className="font-semibold text-white">Risk Context (±10 Adjustment)</span>
            <span className="text-sm text-slate-400">
              {data.layer_scores?.risk_adjustment && data.layer_scores.risk_adjustment > 0 ? 'Positive' : 
               data.layer_scores?.risk_adjustment && data.layer_scores.risk_adjustment < 0 ? 'Negative' : 'Neutral'}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-amber-400">
              {data.layer_scores?.risk_adjustment && data.layer_scores.risk_adjustment > 0 ? '+' : ''}
              {formatValue(data.layer_scores?.risk_adjustment)}
            </span>
            <span className="text-slate-400">
              {expandedLayer === 'risk' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'risk' && data.calculation_details?.risk_modifiers && (
          <div className="p-4 border-t border-slate-700 space-y-3">
            <div className="text-sm text-slate-300 mb-3">
              Market context adjustments based on company size, dividend protection, and sector trends.
            </div>

            {data.calculation_details.risk_modifiers.market_cap_safety && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Market Cap Safety</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{data.calculation_details.risk_modifiers.market_cap_safety.tier}</span>
                  <span className={data.calculation_details.risk_modifiers.market_cap_safety.adjustment >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {data.calculation_details.risk_modifiers.market_cap_safety.adjustment >= 0 ? '+' : ''}
                    {formatValue(data.calculation_details.risk_modifiers.market_cap_safety.adjustment)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.risk_modifiers.dividend_protection && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Dividend Protection</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">{formatValue(data.calculation_details.risk_modifiers.dividend_protection.yield * 100)}% yield</span>
                  <span className={data.calculation_details.risk_modifiers.dividend_protection.adjustment >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {data.calculation_details.risk_modifiers.dividend_protection.adjustment >= 0 ? '+' : ''}
                    {formatValue(data.calculation_details.risk_modifiers.dividend_protection.adjustment)}
                  </span>
                </div>
              </div>
            )}

            {data.calculation_details.risk_modifiers.sector_momentum && (
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Sector Momentum</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white">Score: {formatValue(data.calculation_details.risk_modifiers.sector_momentum.score)}</span>
                  <span className={data.calculation_details.risk_modifiers.sector_momentum.adjustment >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {data.calculation_details.risk_modifiers.sector_momentum.adjustment >= 0 ? '+' : ''}
                    {formatValue(data.calculation_details.risk_modifiers.sector_momentum.adjustment)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default LayerBreakdown; 