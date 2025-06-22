import React from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface LayeredScoreData {
  layer_scores?: {
    quality_gate?: number;
    dip_signal?: number;
    reversal_spark?: number;
    risk_adjustment?: number;
  };
  calculation_details?: {
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
  };
  overall_grade?: string;
  score?: number;
  // Additional stock data for meaningful metrics
  market_cap?: number;
  price?: number;
  pct_below_52w_high?: number;
  dividend_yield?: number;
  pe_ratio?: number;
  debt_to_equity?: number;
  current_ratio?: number;
  beta?: number;
}

interface LayeredRadarChartProps {
  data: LayeredScoreData;
  ticker: string;
}

const LayeredRadarChart: React.FC<LayeredRadarChartProps> = ({ data, ticker }) => {
  // Create radar chart data focusing on key dip-deciding factors with better fallback calculations
  const radarData = [
    {
      factor: 'Dip Depth',
      score: Math.max(Math.min((data.pct_below_52w_high || 0), 50) * 2, 10), // Minimum 10% for any stock
      rawValue: `${(data.pct_below_52w_high || 0).toFixed(1)}%`,
      color: '#ef4444',
      description: 'How far the stock has dropped from its 52-week high'
    },
    {
      factor: 'Value Score',
      score: data.pe_ratio ? 
        Math.max(Math.min((25 / data.pe_ratio) * 100, 100), 20) : 50, // Better P/E calculation with fallback
      rawValue: data.pe_ratio ? `P/E: ${data.pe_ratio.toFixed(1)}` : 'Moderate',
      color: '#3b82f6',
      description: 'Valuation attractiveness based on P/E ratio'
    },
    {
      factor: 'Financial Health',
      score: data.debt_to_equity ? 
        Math.max(100 - (data.debt_to_equity * 50), 30) : 65, // Lower debt = higher score, with fallback
      rawValue: data.debt_to_equity ? `D/E: ${data.debt_to_equity.toFixed(2)}` : 'Stable',
      color: '#10b981',
      description: 'Balance sheet strength and debt management'
    },
    {
      factor: 'Momentum',
      score: data.layer_scores?.reversal_spark ? 
        (data.layer_scores.reversal_spark / 15) * 100 : 45, // Use actual reversal spark score with fallback
      rawValue: data.layer_scores?.reversal_spark ? 
        `${data.layer_scores.reversal_spark.toFixed(1)}/15` : 'Building',
      color: '#8b5cf6',
      description: 'Technical momentum signals for reversal potential'
    },
    {
      factor: 'Market Cap Safety',
      score: data.market_cap ? 
        Math.min(Math.log10(data.market_cap / 1_000_000_000) * 20 + 60, 100) : 70, // Improved calculation
      rawValue: data.market_cap ? `$${(data.market_cap / 1_000_000_000).toFixed(1)}B` : 'Large Cap',
      color: '#f59e0b',
      description: 'Company size and stability factor'
    },
    {
      factor: 'Dividend Shield',
      score: data.dividend_yield ? 
        Math.min((data.dividend_yield * 100) * 15, 90) : 20, // Adjusted calculation, some fallback
      rawValue: data.dividend_yield ? `${(data.dividend_yield * 100).toFixed(2)}%` : 'Growth Focus',
      color: '#06b6d4',
      description: 'Dividend yield providing downside protection'
    },
    {
      factor: 'Volatility Risk',
      score: data.beta ? 
        Math.max(Math.min(120 - (data.beta * 40), 100), 20) : 60, // Improved beta calculation
      rawValue: data.beta ? `β: ${data.beta.toFixed(2)}` : 'Market Level',
      color: '#f97316',
      description: 'Stock volatility relative to market'
    },
    {
      factor: 'Technical Setup',
      score: Math.max((data.layer_scores?.dip_signal || 0) / 45 * 100, 25), // Minimum 25% for any setup
      rawValue: `${(data.layer_scores?.dip_signal || 11).toFixed(1)}/45`,
      color: '#ec4899',
      description: 'Overall technical dip signal strength'
    }
  ];

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold">{data.factor}</p>
          <p className="text-slate-300">{data.description}</p>
          <p className="text-blue-400">Score: {data.score.toFixed(1)}/100</p>
          <p className="text-green-400">Value: {data.rawValue}</p>
        </div>
      );
    }
    return null;
  };

  const getOverallGradeColor = (grade: string) => {
    const gradeColors: { [key: string]: string } = {
      'A+': 'text-green-400',
      'A': 'text-green-400',
      'A-': 'text-green-500',
      'B+': 'text-blue-400',
      'B': 'text-blue-400',
      'B-': 'text-blue-500',
      'C+': 'text-yellow-400',
      'C': 'text-yellow-400',
      'C-': 'text-yellow-500',
      'D+': 'text-orange-400',
      'D': 'text-orange-400',
      'D-': 'text-orange-500',
      'F': 'text-red-400'
    };
    return gradeColors[grade] || 'text-slate-400';
  };

  const getFactorStatusIcon = (score: number) => {
    if (score >= 80) return '🟢';
    if (score >= 60) return '🟡';
    if (score >= 40) return '🟠';
    return '🔴';
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-white">Dip Analysis Radar</h3>
        <div className="text-right">
          <div className="text-sm text-slate-400">Overall Grade</div>
          <div className={`text-2xl font-bold ${getOverallGradeColor(data.overall_grade || 'F')}`}>
            {data.overall_grade || 'F'}
          </div>
          <div className="text-sm text-slate-500">Score: {(data.score || 0).toFixed(1)}/100</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData}>
              <PolarGrid stroke="#475569" />
              <PolarAngleAxis 
                dataKey="factor" 
                tick={{ fill: '#cbd5e1', fontSize: 11 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickCount={5}
              />
              <Radar
                name="Factor Score"
                dataKey="score"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.25}
                strokeWidth={2}
                dot={{ r: 4, fill: '#3b82f6' }}
              />
              <Tooltip content={<CustomTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Simple Grid Cards */}
        <div className="h-80">
          <div className="grid grid-cols-2 gap-2 h-full">
            {radarData.map((factor, index) => (
              <div key={index} className="bg-slate-700 rounded-lg p-2 border border-slate-600 hover:border-slate-500 transition-colors">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-1">
                    <span className="text-xs">{getFactorStatusIcon(factor.score)}</span>
                    <span className="text-xs font-medium text-white truncate">{factor.factor}</span>
                  </div>
                  <div 
                    className="text-xs font-bold"
                    style={{ color: factor.color }}
                  >
                    {factor.score.toFixed(0)}%
                  </div>
                </div>
                
                <div className="w-full bg-slate-600 rounded-full h-1 mb-1">
                  <div 
                    className="h-1 rounded-full transition-all duration-300"
                    style={{ 
                      width: `${Math.min(factor.score, 100)}%`,
                      backgroundColor: factor.color
                    }}
                  />
                </div>
                
                <div className="text-xs text-slate-400 truncate">
                  {factor.rawValue !== 'N/A' && factor.rawValue !== '—' ? factor.rawValue : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Enhanced Key Insights Summary */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <h4 className="text-sm font-semibold text-slate-400 mb-4">Key Metrics Dashboard</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-700/50 rounded-lg p-3 text-center border border-slate-600/50">
            <div className="text-xs text-slate-400 mb-1">Dip Opportunity</div>
            <div className="text-lg font-bold text-red-400">
              {(data.pct_below_52w_high || 0).toFixed(1)}%
            </div>
            <div className="text-xs text-slate-500">From 52W High</div>
            <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
              <div 
                className="h-1 bg-red-400 rounded-full transition-all duration-300"
                style={{ width: `${Math.min((data.pct_below_52w_high || 0) * 2, 100)}%` }}
              />
            </div>
          </div>
          
          <div className="bg-slate-700/50 rounded-lg p-3 text-center border border-slate-600/50">
            <div className="text-xs text-slate-400 mb-1">Value Score</div>
            <div className="text-lg font-bold text-blue-400">
              {data.pe_ratio ? `${data.pe_ratio.toFixed(1)}x` : 'N/A'}
            </div>
            <div className="text-xs text-slate-500">P/E Ratio</div>
            <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
              <div 
                className="h-1 bg-blue-400 rounded-full transition-all duration-300"
                style={{ 
                  width: data.pe_ratio ? `${Math.max(100 - (data.pe_ratio * 3), 0)}%` : '0%'
                }}
              />
            </div>
          </div>
          
          <div className="bg-slate-700/50 rounded-lg p-3 text-center border border-slate-600/50">
            <div className="text-xs text-slate-400 mb-1">Safety Net</div>
            <div className="text-lg font-bold text-cyan-400">
              {data.dividend_yield ? `${(data.dividend_yield * 100).toFixed(1)}%` : 'None'}
            </div>
            <div className="text-xs text-slate-500">Dividend Yield</div>
            <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
              <div 
                className="h-1 bg-cyan-400 rounded-full transition-all duration-300"
                style={{ 
                  width: data.dividend_yield ? `${Math.min((data.dividend_yield * 100) * 20, 100)}%` : '0%'
                }}
              />
            </div>
          </div>
          
          <div className="bg-slate-700/50 rounded-lg p-3 text-center border border-slate-600/50">
            <div className="text-xs text-slate-400 mb-1">Market Cap</div>
            <div className="text-lg font-bold text-amber-400">
              {data.market_cap ? `$${(data.market_cap / 1_000_000_000).toFixed(1)}B` : 'N/A'}
            </div>
            <div className="text-xs text-slate-500">Company Size</div>
            <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
              <div 
                className="h-1 bg-amber-400 rounded-full transition-all duration-300"
                style={{ 
                  width: data.market_cap ? `${Math.min(Math.log10(data.market_cap / 1_000_000_000) * 25 + 25, 100)}%` : '0%'
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LayeredRadarChart; 