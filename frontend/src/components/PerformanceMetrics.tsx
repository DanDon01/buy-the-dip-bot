import React from 'react';

interface PerformanceData {
  total_stocks?: number;
  avg_score?: number;
  top_scorer?: string;
  top_score?: number;
  last_update?: string;
}

interface PerformanceMetricsProps {
  data: PerformanceData;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ data }) => {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-blue-400'; 
    if (score >= 40) return 'text-yellow-400';
    if (score >= 20) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreGrade = (score: number) => {
    if (score >= 90) return 'A+';
    if (score >= 80) return 'A';
    if (score >= 70) return 'B';
    if (score >= 60) return 'C';
    if (score >= 50) return 'D';
    return 'F';
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <h3 className="text-xl font-bold text-white mb-6">System Performance Overview</h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {/* Total Stocks */}
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-400 mb-2">
            {data.total_stocks || 0}
          </div>
          <div className="text-sm text-slate-400">Stocks Analyzed</div>
          <div className="mt-2 w-full bg-slate-700 rounded-full h-1">
            <div 
              className="h-1 bg-blue-400 rounded-full transition-all duration-300"
              style={{ width: `${Math.min((data.total_stocks || 0) / 100 * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Average Score */}
        <div className="text-center">
          <div className={`text-3xl font-bold mb-2 ${getScoreColor(data.avg_score || 0)}`}>
            {(data.avg_score || 0).toFixed(1)}
          </div>
          <div className="text-sm text-slate-400">Average Score</div>
          <div className="mt-2 text-xs font-medium">
            Grade: <span className={getScoreColor(data.avg_score || 0)}>
              {getScoreGrade(data.avg_score || 0)}
            </span>
          </div>
        </div>

        {/* Top Performer */}
        <div className="text-center">
          <div className="text-3xl font-bold text-green-400 mb-2">
            {data.top_scorer || 'N/A'}
          </div>
          <div className="text-sm text-slate-400">Top Performer</div>
          <div className="mt-2 text-xs text-green-300">
            Score: {(data.top_score || 0).toFixed(1)}
          </div>
        </div>

        {/* Last Update */}
        <div className="text-center">
          <div className="text-3xl font-bold text-amber-400 mb-2">
            📊
          </div>
          <div className="text-sm text-slate-400">Last Updated</div>
          <div className="mt-2 text-xs text-amber-300">
            {data.last_update ? new Date(data.last_update).toLocaleDateString() : 'Unknown'}
          </div>
        </div>
      </div>

      {/* Performance Indicators */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center text-sm">
          <div className="flex items-center justify-center space-x-2">
            <div className="w-3 h-3 bg-green-400 rounded-full"></div>
            <span className="text-slate-300">Quality Stocks: High Grade (A-B)</span>
          </div>
          <div className="flex items-center justify-center space-x-2">
            <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
            <span className="text-slate-300">Potential Dips: Monitoring (C-D)</span>
          </div>
          <div className="flex items-center justify-center space-x-2">
            <div className="w-3 h-3 bg-red-400 rounded-full"></div>
            <span className="text-slate-300">Avoid: Poor Quality (F)</span>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="mt-4 p-3 bg-slate-700 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm text-slate-300">System Status</span>
          </div>
          <div className="text-sm text-green-400 font-medium">
            🎯 4-Layer Methodology Active
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceMetrics; 