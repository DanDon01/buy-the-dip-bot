import React from 'react';

interface InvestmentData {
  investment_recommendation?: {
    action?: string;
    confidence?: string;
    reason?: string;
    hold_period?: string;
    risk_assessment?: string;
    key_strengths?: string[];
    key_risks?: string[];
  };
  methodology_compliance?: {
    passes_quality_gate?: boolean;
    in_dip_sweet_spot?: boolean;
    has_reversal_signals?: boolean;
    methodology_grade?: string;
  };
  overall_grade?: string;
  score?: number;
}

interface InvestmentRecommendationProps {
  data: InvestmentData;
  ticker: string;
  price: number;
}

const InvestmentRecommendation: React.FC<InvestmentRecommendationProps> = ({ 
  data, 
  ticker, 
  price 
}) => {
  const recommendation = data.investment_recommendation || {};
  const compliance = data.methodology_compliance || {};

  const getActionColor = (action: string) => {
    switch (action?.toUpperCase()) {
      case 'STRONG BUY':
        return 'bg-green-600 text-white';
      case 'BUY':
        return 'bg-green-500 text-white';
      case 'WEAK BUY':
        return 'bg-green-400 text-white';
      case 'HOLD':
        return 'bg-yellow-500 text-white';
      case 'WEAK SELL':
        return 'bg-orange-500 text-white';
      case 'SELL':
        return 'bg-red-500 text-white';
      case 'AVOID':
        return 'bg-red-600 text-white';
      default:
        return 'bg-slate-600 text-slate-300';
    }
  };

  const getActionIcon = (action: string) => {
    switch (action?.toUpperCase()) {
      case 'STRONG BUY':
        return '🚀';
      case 'BUY':
        return '📈';
      case 'WEAK BUY':
        return '📊';
      case 'HOLD':
        return '🤝';
      case 'WEAK SELL':
        return '📉';
      case 'SELL':
        return '🔻';
      case 'AVOID':
        return '⚠️';
      default:
        return '❓';
    }
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence?.toLowerCase()) {
      case 'high':
        return 'text-green-400';
      case 'medium':
        return 'text-yellow-400';
      case 'low':
        return 'text-red-400';
      default:
        return 'text-slate-400';
    }
  };

  const getComplianceIcon = (passes: boolean) => {
    return passes ? '✅' : '❌';
  };

  return (
    <div className="space-y-6">
      {/* Main Recommendation Card */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-white">Investment Recommendation</h3>
          <div className="text-right">
            <div className="text-sm text-slate-400">Current Price</div>
            <div className="text-lg font-semibold text-green-400">${price.toFixed(2)}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Recommendation Details */}
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">{getActionIcon(recommendation.action || '')}</span>
              <div>
                <div className={`inline-block px-4 py-2 rounded-lg font-bold ${getActionColor(recommendation.action || '')}`}>
                  {recommendation.action || 'NO RECOMMENDATION'}
                </div>
                <div className="mt-1 text-sm text-slate-400">
                  Confidence: <span className={`font-medium ${getConfidenceColor(recommendation.confidence || '')}`}>
                    {recommendation.confidence?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
              </div>
            </div>

            {recommendation.reason && (
              <div className="bg-slate-700 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Reasoning</div>
                <div className="text-white">{recommendation.reason}</div>
              </div>
            )}

            {/* Key Strengths */}
            {recommendation.key_strengths && recommendation.key_strengths.length > 0 && (
              <div className="bg-slate-700 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-2">Key Strengths</div>
                <ul className="space-y-1">
                  {recommendation.key_strengths.map((strength, index) => (
                    <li key={index} className="text-green-300 text-sm flex items-start">
                      <span className="mr-2 text-green-400">✓</span>
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Key Risks */}
            {recommendation.key_risks && recommendation.key_risks.length > 0 && (
              <div className="bg-slate-700 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-2">Key Risks</div>
                <ul className="space-y-1">
                  {recommendation.key_risks.map((risk, index) => (
                    <li key={index} className="text-red-300 text-sm flex items-start">
                      <span className="mr-2 text-red-400">⚠</span>
                      <span>{risk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {recommendation.hold_period && (
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Recommended Hold Period:</span>
                <span className="text-blue-400 font-medium">{recommendation.hold_period}</span>
              </div>
            )}

            {recommendation.risk_assessment && (
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Risk Assessment:</span>
                <span className="text-yellow-400 font-medium">{recommendation.risk_assessment}</span>
              </div>
            )}
          </div>

          {/* Score Summary */}
          <div className="space-y-4">
            <div className="text-center">
              <div className="text-sm text-slate-400 mb-1">Overall Score</div>
              <div className="text-4xl font-bold text-blue-400 mb-1">
                {(data.score || 0).toFixed(1)}
              </div>
              <div className="text-sm text-slate-500">out of 100+</div>
            </div>

            <div className="text-center">
              <div className="text-sm text-slate-400 mb-1">Overall Grade</div>
              <div className={`text-2xl font-bold ${
                data.overall_grade === 'A+' || data.overall_grade === 'A' ? 'text-green-400' :
                data.overall_grade === 'B+' || data.overall_grade === 'B' ? 'text-blue-400' :
                data.overall_grade === 'C+' || data.overall_grade === 'C' ? 'text-yellow-400' :
                data.overall_grade === 'D+' || data.overall_grade === 'D' ? 'text-orange-400' :
                'text-red-400'
              }`}>
                {data.overall_grade || 'F'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Methodology Compliance */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h4 className="text-lg font-bold text-white mb-4">Methodology Compliance</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
              <span className="text-slate-300">Quality Gate</span>
              <div className="flex items-center space-x-2">
                <span>{getComplianceIcon(compliance.passes_quality_gate || false)}</span>
                <span className={compliance.passes_quality_gate ? 'text-green-400' : 'text-red-400'}>
                  {compliance.passes_quality_gate ? 'PASS' : 'FAIL'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
              <span className="text-slate-300">Sweet Spot Dip</span>
              <div className="flex items-center space-x-2">
                <span>{getComplianceIcon(compliance.in_dip_sweet_spot || false)}</span>
                <span className={compliance.in_dip_sweet_spot ? 'text-green-400' : 'text-red-400'}>
                  {compliance.in_dip_sweet_spot ? 'YES' : 'NO'}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
              <span className="text-slate-300">Reversal Signals</span>
              <div className="flex items-center space-x-2">
                <span>{getComplianceIcon(compliance.has_reversal_signals || false)}</span>
                <span className={compliance.has_reversal_signals ? 'text-green-400' : 'text-red-400'}>
                  {compliance.has_reversal_signals ? 'DETECTED' : 'NONE'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
              <span className="text-slate-300">Methodology Grade</span>
              <div className="flex items-center space-x-2">
                <span className={`font-bold ${
                  compliance.methodology_grade === 'A+' || compliance.methodology_grade === 'A' ? 'text-green-400' :
                  compliance.methodology_grade === 'B+' || compliance.methodology_grade === 'B' ? 'text-blue-400' :
                  compliance.methodology_grade === 'C+' || compliance.methodology_grade === 'C' ? 'text-yellow-400' :
                  compliance.methodology_grade === 'D+' || compliance.methodology_grade === 'D' ? 'text-orange-400' :
                  'text-red-400'
                }`}>
                  {compliance.methodology_grade || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Sweet Spot Indicator */}
        {compliance.in_dip_sweet_spot && (
          <div className="mt-4 p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
            <div className="flex items-center space-x-2 text-green-400">
              <span>🎯</span>
              <span className="font-semibold">Sweet Spot Opportunity!</span>
            </div>
            <div className="text-sm text-green-300 mt-1">
              This stock is in the ideal 15-40% dip range with quality fundamentals.
            </div>
          </div>
        )}

        {/* Quality Gate Failure Warning */}
        {!compliance.passes_quality_gate && (
          <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
            <div className="flex items-center space-x-2 text-red-400">
              <span>⚠️</span>
              <span className="font-semibold">Quality Gate Failure</span>
            </div>
            <div className="text-sm text-red-300 mt-1">
              Poor business fundamentals detected. Consider avoiding this investment.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InvestmentRecommendation; 