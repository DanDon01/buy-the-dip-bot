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
  // 52-week price data
  '52_week_high'?: number;
  '52_week_low'?: number;
  pct_below_52w_high?: number;
  // Additional financial data
  pe_ratio?: number;
  dividend_yield?: number;
  market_cap?: number;
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

  // Calculate 52-week position and suggested buy prices
  const high52w = data['52_week_high'] || price * 1.3;
  const low52w = data['52_week_low'] || price * 0.7;
  const pctBelow52w = data.pct_below_52w_high || ((high52w - price) / high52w) * 100;
  const rangePosition = ((price - low52w) / (high52w - low52w)) * 100;
  
  // Calculate suggested buy prices based on technical levels
  const conservativeBuyPrice = price * 0.95; // 5% below current
  const aggressiveBuyPrice = price * 0.90; // 10% below current
  const dipTargetPrice = high52w * 0.75; // 25% below 52w high

  const getActionColor = (action: string) => {
    switch (action?.toUpperCase()) {
      case 'STRONG BUY':
        return 'bg-gradient-to-r from-green-600 to-green-500 text-white shadow-lg shadow-green-500/25';
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
        return '📊';
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

  const getDipAnalysis = () => {
    if (pctBelow52w >= 40) {
      return {
        level: 'Deep Value Opportunity',
        color: 'text-green-400',
        icon: '💎',
        description: 'Stock is at a significant discount from its highs, presenting a compelling value opportunity.'
      };
    } else if (pctBelow52w >= 20) {
      return {
        level: 'Quality Dip',
        color: 'text-blue-400',
        icon: '🎯',
        description: 'Stock is in the sweet spot dip range, ideal for dollar-cost averaging.'
      };
    } else if (pctBelow52w >= 10) {
      return {
        level: 'Minor Pullback',
        color: 'text-yellow-400',
        icon: '📊',
        description: 'Stock has pulled back modestly, may offer limited upside potential.'
      };
    } else {
      return {
        level: 'Near Highs',
        color: 'text-red-400',
        icon: '⚠️',
        description: 'Stock is trading near its highs, consider waiting for a better entry point.'
      };
    }
  };

  const dipAnalysis = getDipAnalysis();

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      {/* Header Section */}
      <div className="bg-gradient-to-r from-slate-700 to-slate-800 p-6 border-b border-slate-600">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h3 className="text-2xl font-bold text-white">Investment Recommendation</h3>
            {/* Dippy Egg for exceptional scores (85+) */}
            {(data.score || 0) >= 85 && (
              <div className="flex items-center space-x-2 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-full px-3 py-1 border border-yellow-500/30">
                <img 
                  src="/images/dippyegg.png" 
                  alt="Dippy Egg - Exceptional Dip Opportunity" 
                  className="w-8 h-8 animate-bounce"
                  style={{ filter: 'drop-shadow(0 4px 8px rgba(255, 193, 7, 0.3))' }}
                />
                <span className="text-yellow-400 font-bold text-sm">Dippy Pick!</span>
              </div>
            )}
          </div>
          <div className="text-right">
            <div className="text-sm text-slate-400">Overall Grade</div>
            <div className={`text-3xl font-bold ${
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

      <div className="p-6">
        {/* Main Content - Better Balanced Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          
          {/* Left Column - Action & Score (Larger - 1.5/4 width) */}
          <div className="xl:col-span-1 space-y-6">
            {/* Action Button with Ping Effect - Enhanced */}
            <div className="text-center space-y-6 bg-gradient-to-br from-slate-700/50 to-slate-800/80 rounded-xl p-6 border border-slate-600/50">
              {/* Icon Display */}
              <div className="flex items-center justify-center mb-4">
                <div className="relative">
                  <div className="text-6xl filter drop-shadow-lg">
                    {getActionIcon(recommendation.action || '')}
                  </div>
                  {recommendation.action?.toUpperCase() === 'STRONG BUY' && (
                    <div className="absolute inset-0 rounded-full">
                      <div className="animate-ping absolute inset-0 rounded-full bg-green-400/30 scale-150"></div>
                      <div className="animate-pulse absolute inset-0 rounded-full bg-green-400/20 scale-125"></div>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Action Button with Enhanced Ping */}
              <div className="relative inline-block w-full">
                {recommendation.action?.toUpperCase() === 'STRONG BUY' && (
                  <>
                    <div className="absolute -inset-1 rounded-xl bg-gradient-to-r from-green-400 to-green-600 opacity-30 blur animate-pulse"></div>
                    <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-green-400 to-green-600 opacity-50 animate-ping"></div>
                  </>
                )}
                <div className={`relative w-full px-6 py-4 rounded-xl font-bold text-lg transition-all duration-300 transform hover:scale-105 ${getActionColor(recommendation.action || '')} shadow-lg`}>
                  {recommendation.action || 'NO RECOMMENDATION'}
                </div>
              </div>
              
              {/* Confidence Level - Enhanced */}
              <div className="mt-6 bg-slate-800/60 rounded-lg p-4 border border-slate-600/30">
                <div className="text-sm text-slate-400 mb-2">Confidence Level</div>
                <div className={`text-xl font-bold ${getConfidenceColor(recommendation.confidence || '')} flex items-center justify-center space-x-2`}>
                  <span>{recommendation.confidence?.toUpperCase() || 'UNKNOWN'}</span>
                  {recommendation.confidence?.toLowerCase() === 'high' && <span className="text-green-400">🔥</span>}
                  {recommendation.confidence?.toLowerCase() === 'medium' && <span className="text-yellow-400">⚡</span>}
                  {recommendation.confidence?.toLowerCase() === 'low' && <span className="text-red-400">⚠️</span>}
                </div>
              </div>
            </div>

            {/* Score Display - Enhanced */}
            <div className="bg-gradient-to-br from-blue-900/30 to-slate-800/80 rounded-xl p-8 text-center border border-blue-500/20 shadow-xl">
              <div className="text-sm text-slate-400 mb-3 uppercase tracking-wider">Investment Score</div>
              <div className="relative">
                <div className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400 mb-2 filter drop-shadow-lg">
                  {(data.score || 0).toFixed(1)}
                </div>
                <div className="absolute inset-0 text-5xl font-bold text-blue-400/20 blur-sm">
                  {(data.score || 0).toFixed(1)}
                </div>
              </div>
              <div className="text-sm text-slate-500 mb-4">out of 100</div>
              
              {/* Score Bar */}
              <div className="w-full bg-slate-700 rounded-full h-3 mb-2 overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-1000 ease-out shadow-lg"
                  style={{ width: `${Math.min((data.score || 0), 100)}%` }}
                >
                  <div className="h-full bg-gradient-to-r from-white/20 to-transparent rounded-full"></div>
                </div>
              </div>
              
              {/* Score Grade Indicator */}
              <div className="flex justify-center items-center space-x-2 mt-3">
                <div className={`px-3 py-1 rounded-full text-xs font-bold ${
                  (data.score || 0) >= 80 ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                  (data.score || 0) >= 60 ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                  (data.score || 0) >= 40 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                  'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {(data.score || 0) >= 80 ? 'EXCELLENT' :
                   (data.score || 0) >= 60 ? 'GOOD' :
                   (data.score || 0) >= 40 ? 'FAIR' : 'POOR'}
                </div>
              </div>
            </div>
          </div>

          {/* Middle Column - Price Analysis (2/4 width) */}
          <div className="xl:col-span-2 space-y-4">
            {/* 52-Week Range */}
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-white">52-Week Price Range</h4>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${dipAnalysis.color} bg-slate-600`}>
                  {dipAnalysis.icon} {dipAnalysis.level}
                </div>
              </div>
              
              {/* Price Range Bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-slate-400 mb-2">
                  <span>${low52w.toFixed(2)}</span>
                  <span className="font-medium text-white">${price.toFixed(2)}</span>
                  <span>${high52w.toFixed(2)}</span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-2 relative">
                  <div 
                    className="bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 h-2 rounded-full"
                    style={{ width: '100%' }}
                  ></div>
                  <div 
                    className="absolute top-0 h-2 w-0.5 bg-white rounded-full shadow-lg"
                    style={{ left: `${rangePosition}%`, transform: 'translateX(-50%)' }}
                  ></div>
                </div>
                <div className="text-center mt-1">
                  <span className="text-xs text-slate-300">
                    {pctBelow52w.toFixed(1)}% below 52-week high
                  </span>
                </div>
              </div>

              {/* Price Stats */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-600 rounded p-2 text-center">
                  <div className="text-xs text-slate-400">Current</div>
                  <div className="text-sm font-bold text-green-400">${price.toFixed(2)}</div>
                </div>
                <div className="bg-slate-600 rounded p-2 text-center">
                  <div className="text-xs text-slate-400">Position</div>
                  <div className="text-sm font-bold text-blue-400">{rangePosition.toFixed(0)}%</div>
                </div>
              </div>
            </div>

            {/* Suggested Buy Prices */}
            <div className="bg-slate-700 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-white mb-3">Suggested Entry Points</h4>
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-slate-600 rounded p-2 text-center">
                  <div className="text-xs text-slate-400">Conservative</div>
                  <div className="text-sm font-bold text-green-400">${conservativeBuyPrice.toFixed(2)}</div>
                  <div className="text-xs text-slate-500">-5%</div>
                </div>
                <div className="bg-slate-600 rounded p-2 text-center">
                  <div className="text-xs text-slate-400">Aggressive</div>
                  <div className="text-sm font-bold text-yellow-400">${aggressiveBuyPrice.toFixed(2)}</div>
                  <div className="text-xs text-slate-500">-10%</div>
                </div>
                <div className="bg-slate-600 rounded p-2 text-center">
                  <div className="text-xs text-slate-400">Deep Value</div>
                  <div className="text-sm font-bold text-red-400">${dipTargetPrice.toFixed(2)}</div>
                  <div className="text-xs text-slate-500">-25%</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Details, Compliance & Strategy (1/4 width) */}
          <div className="xl:col-span-1 space-y-4">
            {/* Investment Thesis */}
            {recommendation.reason && (
              <div className="bg-slate-700 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-400 mb-2">Investment Thesis</h4>
                <p className="text-xs text-white leading-relaxed">{recommendation.reason}</p>
              </div>
            )}

            {/* Methodology Compliance */}
            <div className="bg-slate-700 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-slate-400 mb-3">Methodology Compliance</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300">Quality Gate</span>
                  <span className={`text-xs font-medium ${compliance.passes_quality_gate ? 'text-green-400' : 'text-red-400'}`}>
                    {compliance.passes_quality_gate ? '✅ PASS' : '❌ FAIL'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300">Dip Sweet Spot</span>
                  <span className={`text-xs font-medium ${compliance.in_dip_sweet_spot ? 'text-green-400' : 'text-red-400'}`}>
                    {compliance.in_dip_sweet_spot ? '🎯 YES' : '❌ NO'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-300">Reversal Signals</span>
                  <span className={`text-xs font-medium ${compliance.has_reversal_signals ? 'text-green-400' : 'text-red-400'}`}>
                    {compliance.has_reversal_signals ? '📈 DETECTED' : '📉 NONE'}
                  </span>
                </div>
              </div>
            </div>

            {/* Investment Details */}
            <div className="bg-slate-700 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-slate-400 mb-3">Investment Details</h4>
              <div className="space-y-2 text-xs">
                {recommendation.hold_period && (
                  <div className="flex justify-between">
                    <span className="text-slate-300">Hold Period:</span>
                    <span className="text-blue-400 font-medium">{recommendation.hold_period}</span>
                  </div>
                )}
                {recommendation.risk_assessment && (
                  <div className="flex justify-between">
                    <span className="text-slate-300">Risk Level:</span>
                    <span className="text-yellow-400 font-medium">{recommendation.risk_assessment}</span>
                  </div>
                )}
                {data.pe_ratio && (
                  <div className="flex justify-between">
                    <span className="text-slate-300">P/E Ratio:</span>
                    <span className="text-white font-medium">{data.pe_ratio.toFixed(1)}</span>
                  </div>
                )}
                {data.dividend_yield && (
                  <div className="flex justify-between">
                    <span className="text-slate-300">Dividend Yield:</span>
                    <span className="text-cyan-400 font-medium">{(data.dividend_yield * 100).toFixed(2)}%</span>
                  </div>
                )}
                {data.market_cap && (
                  <div className="flex justify-between">
                    <span className="text-slate-300">Market Cap:</span>
                    <span className="text-amber-400 font-medium">${(data.market_cap / 1_000_000_000).toFixed(1)}B</span>
                  </div>
                )}
              </div>
            </div>

            {/* Strategic Recommendation - Moved here */}
            <div className={`rounded-lg p-4 border ${
              pctBelow52w >= 20 ? 'bg-green-900/20 border-green-500/30' : 
              pctBelow52w >= 10 ? 'bg-yellow-900/20 border-yellow-500/30' : 
              'bg-red-900/20 border-red-500/30'
            }`}>
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-sm">{dipAnalysis.icon}</span>
                <h4 className={`text-sm font-semibold ${dipAnalysis.color}`}>
                  Strategy
                </h4>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed">
                {pctBelow52w >= 20 
                  ? `Excellent dip opportunity! Consider dollar-cost averaging with partial positions at current levels.`
                  : pctBelow52w >= 10 
                  ? `Moderate opportunity. Consider starting with smaller position sizes.`
                  : `Near highs. Consider setting buy orders at lower levels.`
                }
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Section - Key Strengths & Risks */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          
          {/* Key Strengths */}
          {recommendation.key_strengths && recommendation.key_strengths.length > 0 && (
            <div className="bg-gradient-to-br from-green-900/20 to-green-800/10 border border-green-500/20 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-green-400 mb-3 flex items-center">
                <span className="mr-2">✨</span>Key Strengths
              </h4>
              <ul className="space-y-1">
                {recommendation.key_strengths.slice(0, 3).map((strength, index) => (
                  <li key={index} className="text-green-200 text-xs flex items-start">
                    <span className="mr-2 text-green-400 mt-0.5">•</span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Key Risks */}
          {recommendation.key_risks && recommendation.key_risks.length > 0 && (
            <div className="bg-gradient-to-br from-red-900/20 to-red-800/10 border border-red-500/20 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-red-400 mb-3 flex items-center">
                <span className="mr-2">⚠️</span>Key Risks
              </h4>
              <ul className="space-y-1">
                {recommendation.key_risks.slice(0, 3).map((risk, index) => (
                  <li key={index} className="text-red-200 text-xs flex items-start">
                    <span className="mr-2 text-red-400 mt-0.5">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InvestmentRecommendation; 