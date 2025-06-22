import React from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface LayeredScoreData {
  layer_scores?: {
    quality_gate?: number;
    dip_signal?: number;
    reversal_spark?: number;
    risk_adjustment?: number;
  };
  layer_details?: {
    quality_gate?: {
      quality_grade?: string;
      passes_quality_gate?: boolean;
      quality_score?: number;
      financial_strength?: number;
      valuation_score?: number;
    };
    dip_signal?: {
      dip_grade?: string;
      dip_classification?: string;
      drop_severity_score?: number;
      rsi_oversold_score?: number;
      volume_signature_score?: number;
      sma_positioning_score?: number;
    };
    reversal_spark?: {
      reversal_grade?: string;
      reversal_strength?: string;
      total_signals?: number;
    };
    risk_modifiers?: {
      risk_level?: string;
      market_regime?: string;
      total_risk_adjustment?: number;
    };
  };
  overall_grade?: string;
  score?: number;
}

interface LayeredRadarChartProps {
  data: LayeredScoreData;
  ticker: string;
}

const LayeredRadarChart: React.FC<LayeredRadarChartProps> = ({ data, ticker }) => {
  // Prepare radar chart data for the 4-layer methodology
  const radarData = [
    {
      layer: 'Quality Gate',
      score: data.layer_scores?.quality_gate || 0,
      maxScore: 35,
      percentage: ((data.layer_scores?.quality_gate || 0) / 35) * 100,
      grade: data.layer_details?.quality_gate?.quality_grade || 'F',
      color: '#3b82f6', // Blue
      description: 'Business Quality Filter'
    },
    {
      layer: 'Dip Signal',
      score: data.layer_scores?.dip_signal || 0,
      maxScore: 45,
      percentage: ((data.layer_scores?.dip_signal || 0) / 45) * 100,
      grade: data.layer_details?.dip_signal?.dip_grade || 'F',
      color: '#ef4444', // Red
      description: 'Core Dip Detection'
    },
    {
      layer: 'Reversal Spark',
      score: data.layer_scores?.reversal_spark || 0,
      maxScore: 15,
      percentage: ((data.layer_scores?.reversal_spark || 0) / 15) * 100,
      grade: data.layer_details?.reversal_spark?.reversal_grade || 'F',
      color: '#10b981', // Green
      description: 'Momentum Shift Signals'
    },
    {
      layer: 'Risk Context',
      score: Math.abs(data.layer_scores?.risk_adjustment || 0),
      maxScore: 10,
      percentage: (Math.abs(data.layer_scores?.risk_adjustment || 0) / 10) * 100,
      grade: data.layer_details?.risk_modifiers?.risk_level || 'neutral',
      color: '#f59e0b', // Amber
      description: 'Market Context Adjustment'
    }
  ];

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold">{data.layer}</p>
          <p className="text-slate-300">{data.description}</p>
          <p className="text-blue-400">Score: {data.score.toFixed(1)}/{data.maxScore}</p>
          <p className="text-green-400">Grade: {data.grade}</p>
          <p className="text-amber-400">Performance: {data.percentage.toFixed(1)}%</p>
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

  const getLayerStatusIcon = (score: number, maxScore: number, grade: string) => {
    const percentage = (score / maxScore) * 100;
    if (percentage >= 80) return '🟢';
    if (percentage >= 60) return '🟡';
    if (percentage >= 40) return '🟠';
    return '🔴';
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-white">4-Layer Methodology Analysis</h3>
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
                dataKey="layer" 
                tick={{ fill: '#cbd5e1', fontSize: 12 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickCount={5}
              />
              <Radar
                name="Performance %"
                dataKey="percentage"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Tooltip content={<CustomTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Layer Details */}
        <div className="space-y-4">
          {radarData.map((layer, index) => (
            <div key={index} className="bg-slate-700 rounded-lg p-4 border border-slate-600">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span>{getLayerStatusIcon(layer.score, layer.maxScore, layer.grade)}</span>
                  <span className="font-semibold text-white">{layer.layer}</span>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-blue-400">
                    {layer.score.toFixed(1)}/{layer.maxScore}
                  </div>
                  <div className="text-xs text-slate-400">
                    {layer.percentage.toFixed(1)}%
                  </div>
                </div>
              </div>
              
              <div className="mb-2">
                <div className="w-full bg-slate-600 rounded-full h-2">
                  <div 
                    className="h-2 rounded-full transition-all duration-300"
                    style={{ 
                      width: `${Math.min(layer.percentage, 100)}%`,
                      backgroundColor: layer.color
                    }}
                  />
                </div>
              </div>
              
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">{layer.description}</span>
                <span className={`font-medium ${
                  layer.grade === 'A+' || layer.grade === 'A' ? 'text-green-400' :
                  layer.grade === 'B+' || layer.grade === 'B' ? 'text-blue-400' :
                  layer.grade === 'C+' || layer.grade === 'C' ? 'text-yellow-400' :
                  layer.grade === 'D+' || layer.grade === 'D' ? 'text-orange-400' :
                  'text-red-400'
                }`}>
                  Grade {layer.grade}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Methodology Summary */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-xs">
          <div>
            <div className="text-slate-400">Quality Gate</div>
            <div className="text-blue-400 font-medium">35% Weight</div>
            <div className="text-slate-500">Business Filter</div>
          </div>
          <div>
            <div className="text-slate-400">Dip Signal</div>
            <div className="text-red-400 font-medium">45% Weight</div>
            <div className="text-slate-500">Core Detection</div>
          </div>
          <div>
            <div className="text-slate-400">Reversal Spark</div>
            <div className="text-green-400 font-medium">15% Weight</div>
            <div className="text-slate-500">Momentum Shift</div>
          </div>
          <div>
            <div className="text-slate-400">Risk Context</div>
            <div className="text-amber-400 font-medium">±10% Adj</div>
            <div className="text-slate-500">Market Context</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LayeredRadarChart; 