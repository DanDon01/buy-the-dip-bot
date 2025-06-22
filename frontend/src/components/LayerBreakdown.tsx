import React, { useState } from 'react';

interface LayerData {
  layer_details?: {
    quality_gate?: {
      quality_grade?: string;
      passes_quality_gate?: boolean;
      quality_score?: number;
    };
    dip_signal?: {
      dip_grade?: string;
      dip_classification?: string;
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
            <span className={`text-sm ${getGradeColor(data.layer_details?.quality_gate?.quality_grade || 'F')}`}>
              Grade {data.layer_details?.quality_gate?.quality_grade || 'F'}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-blue-400">{data.layer_details?.quality_gate?.quality_score || 0}/35</span>
            <span className="text-slate-400">
              {expandedLayer === 'quality' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'quality' && (
          <div className="p-4 border-t border-slate-700">
            <div className="text-sm text-slate-300">
              Business quality analysis including cash flow, profitability, debt management, valuation, and business quality metrics.
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
            <span className={`text-sm ${getGradeColor(data.layer_details?.dip_signal?.dip_grade || 'F')}`}>
              Grade {data.layer_details?.dip_signal?.dip_grade || 'F'}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-red-400">{data.layer_details?.dip_signal?.dip_classification || 'no_dip'}</span>
            <span className="text-slate-400">
              {expandedLayer === 'dip' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'dip' && (
          <div className="p-4 border-t border-slate-700">
            <div className="text-sm text-slate-300">
              Core dip detection analyzing price drops, RSI levels, volume spikes, and moving average positioning.
            </div>
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
            <span className={`text-sm ${getGradeColor(data.layer_details?.reversal_spark?.reversal_grade || 'F')}`}>
              Grade {data.layer_details?.reversal_spark?.reversal_grade || 'F'}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-green-400">{data.layer_details?.reversal_spark?.total_signals || 0} signals</span>
            <span className="text-slate-400">
              {expandedLayer === 'reversal' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'reversal' && (
          <div className="p-4 border-t border-slate-700">
            <div className="text-sm text-slate-300">
              Early momentum shift detection through MACD signals, volume patterns, and candlestick analysis.
            </div>
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
            <span className="text-sm text-slate-400">{data.layer_details?.risk_modifiers?.risk_level || 'neutral'}</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-amber-400">
              {data.layer_details?.risk_modifiers?.total_risk_adjustment && data.layer_details.risk_modifiers.total_risk_adjustment > 0 ? '+' : ''}
              {data.layer_details?.risk_modifiers?.total_risk_adjustment?.toFixed(1) || 0}
            </span>
            <span className="text-slate-400">
              {expandedLayer === 'risk' ? '▼' : '▶'}
            </span>
          </div>
        </button>

        {expandedLayer === 'risk' && (
          <div className="p-4 border-t border-slate-700">
            <div className="text-sm text-slate-300">
              Market context adjustments based on sector momentum, volatility regime, liquidity risk, and macro timing.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LayerBreakdown; 