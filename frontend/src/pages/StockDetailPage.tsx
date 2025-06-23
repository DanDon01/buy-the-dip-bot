import { useEffect, useState } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import LayeredRadarChart from '../components/LayeredRadarChart';
import InvestmentRecommendation from '../components/InvestmentRecommendation';
import LayerBreakdown from '../components/LayerBreakdown';

const StockDetailPage = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const location = useLocation();
  const [stock, setStock] = useState<any>(null);
  const [extraDetails, setExtraDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [stockError, setStockError] = useState<string | null>(null);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [isStarred, setIsStarred] = useState(false);
  
  // Get scoring data from navigation state (from scoring tuning page)
  const scoringData = location.state?.scoringData;

  useEffect(() => {
    if (ticker) {
      // Check if stock is in buy list
      const buyList = JSON.parse(localStorage.getItem('buyList') || '[]');
      setIsStarred(buyList.some((stock: any) => stock.ticker === ticker.toUpperCase()));

      const fetchStockData = async () => {
        setLoading(true);
        setStock(null);
        setExtraDetails(null);
        setStockError(null);
        setDetailsError(null);

        try {
          const stockRes = await fetch(`http://localhost:5001/api/stock/${ticker}`);
          if (!stockRes.ok) {
            const errData = await stockRes.json();
            throw new Error(errData.error || 'Stock not found');
          }
          const stockData = await stockRes.json();
          
          // Merge with scoring data if available (from scoring tuning page)
          if (scoringData) {
            const mergedData = {
              ...stockData,
              score: scoringData.score,
              layer_scores: scoringData.layer_scores,
              calculation_details: scoringData.calculation_details,
              investment_recommendation: {
                action: scoringData.recommendation,
                confidence: 'high',
                reason: `Scored using ${scoringData.methodology}`
              },
              methodology_compliance: {
                passes_quality_gate: scoringData.layer_scores?.quality_gate > 0,
                in_dip_sweet_spot: scoringData.layer_scores?.dip_signal > 0,
                has_reversal_signals: scoringData.layer_scores?.reversal_spark > 0
              },
              overall_grade: scoringData.score >= 80 ? 'A' : 
                           scoringData.score >= 70 ? 'B' : 
                           scoringData.score >= 60 ? 'C' : 
                           scoringData.score >= 40 ? 'D' : 'F',
              enhanced_score: scoringData.score,
              // Store the scoring methodology and parameters
              scoring_methodology: scoringData.methodology,
              scoring_parameters: scoringData.parameters
            };
            setStock(mergedData);
            console.log('Merged stock data with scoring:', mergedData.calculation_details ? 'Has calculation details' : 'No calculation details');
          } else {
            setStock(stockData);
          }

          try {
            const detailsRes = await fetch(`http://localhost:5001/api/stock_details/${ticker}`);
            if (detailsRes.ok) {
              const detailsData = await detailsRes.json();
              setExtraDetails(detailsData);
            } else {
              const errData = await detailsRes.json();
              throw new Error(errData.error || 'Could not fetch extra details');
            }
          } catch (detailsErr: any) {
            setDetailsError(detailsErr.message);
          }

        } catch (err: any) {
          setStockError(err.message);
        } finally {
          setLoading(false);
        }
      };
      fetchStockData();
    }
  }, [ticker, scoringData]);

  const toggleStar = () => {
    if (!stock) return;

    const buyList = JSON.parse(localStorage.getItem('buyList') || '[]');
    
    if (isStarred) {
      // Remove from buy list
      const updated = buyList.filter((s: any) => s.ticker !== stock.ticker);
      localStorage.setItem('buyList', JSON.stringify(updated));
      setIsStarred(false);
    } else {
      // Add to buy list with scoring data
      const newStock = {
        ticker: stock.ticker,
        price: stock.price,
        score: scoringData ? scoringData.score : stock.score,
        addedDate: new Date().toISOString(),
        // Include scoring methodology and data if available
        ...(scoringData && {
          scoring_methodology: scoringData.methodology,
          layer_scores: scoringData.layer_scores,
          recommendation: scoringData.recommendation,
          has_enhanced_scoring: true,
          scoring_parameters: scoringData.parameters
        })
      };
      buyList.push(newStock);
      localStorage.setItem('buyList', JSON.stringify(buyList));
      setIsStarred(true);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-pulse text-xl text-slate-300">Loading {ticker} analysis...</div>
          <div className="mt-2 text-sm text-slate-500">Fetching market data and scoring details...</div>
        </div>
      </div>
    );
  }

  if (stockError) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-red-400 text-xl">Error Loading Stock Data</div>
          <p className="mt-2 text-slate-400">{stockError}</p>
        </div>
      </div>
    );
  }
  
  if (!stock) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-slate-400 text-xl">📈 Select a Stock</div>
          <p className="mt-2 text-slate-500">Choose a stock from the sidebar to view detailed analysis</p>
        </div>
      </div>
    );
  }

  const chartData = stock.history?.map((item: any) => ({
    date: new Date(item.date).toLocaleDateString(),
    price: item.price,
    '52_week_high': extraDetails?.['52_week_high'],
    '52_week_low': extraDetails?.['52_week_low']
  })) || [];

  // Calculate Y-axis domain to show complete 52-week range
  const calculateYAxisDomain = () => {
    if (chartData.length === 0) return [0, 100];
    
    const prices = chartData.map((item: any) => item.price).filter((price: number) => price > 0);
    const high52w = extraDetails?.['52_week_high'];
    const low52w = extraDetails?.['52_week_low'];
    
    if (prices.length === 0) return [0, 100];
    
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices, high52w || 0);
    
    // Use 52-week low if available, otherwise fall back to historical min
    const absoluteLow = low52w ? Math.min(low52w, minPrice) : minPrice;
    const absoluteHigh = high52w ? Math.max(high52w, maxPrice) : maxPrice;
    
    // Start Y-axis 10% below the 52-week low for complete range view
    const yAxisMin = absoluteLow * 0.90;
    // Add 5% padding above the highest value
    const yAxisMax = absoluteHigh * 1.05;
    
    return [yAxisMin, yAxisMax];
  };

  const [yAxisMin, yAxisMax] = calculateYAxisDomain();

  // Color array for different factors
  const radarColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  // Create radar chart data for individual stock with color mapping
  const radarData: any[] = [];
  const colorMap: { [key: string]: string } = {};

  // Add overall score
  radarData.push({
    subject: 'Overall Score',
    A: stock.score,
    fullMark: 10
  });
  colorMap['Overall Score'] = radarColors[0];

  // Add individual score components if available
  if (stock.score_details) {
    Object.entries(stock.score_details).forEach(([key, value]: [string, any], index) => {
      const factorName = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      radarData.push({
        subject: factorName,
        A: value * 10, // Scale to 0-10
        fullMark: 10
      });
      colorMap[factorName] = radarColors[(index + 1) % radarColors.length];
    });
  }
  
  // Color calculation function for scores - more subtle version
  const getScoreColor = (value: number) => {
    // Normalize value to 0-1 range (assuming max score is 1)
    const normalized = Math.min(Math.max(value, 0), 1);
    
    if (normalized <= 0.5) {
      // Muted red to amber (0-0.5)
      const ratio = normalized * 2;
      return `rgb(${220}, ${Math.round(140 + 80 * ratio)}, ${Math.round(60 * ratio)})`;
    } else {
      // Amber to muted green (0.5-1)
      const ratio = (normalized - 0.5) * 2;
      return `rgb(${Math.round(220 - 100 * ratio)}, ${220}, ${Math.round(60 + 80 * ratio)})`;
    }
  };

  // Technical explanations for each metric
  const getMetricExplanation = (key: string) => {
    const explanations: { [key: string]: string } = {
      'volume_spike': 'Measures unusual trading volume compared to average. High values indicate increased market interest and potential price movement.',
      'short_float': 'Percentage of shares sold short. High short interest can lead to short squeezes when price rises.',
      'rsi': 'Relative Strength Index - momentum oscillator measuring speed of price changes. Values below 30 suggest oversold conditions.',
      'price_drop': 'Recent price decline from highs. Higher values indicate potential buying opportunities at discounted prices.',
      'pe': 'Price-to-Earnings ratio evaluation. Lower values may indicate undervalued stocks relative to earnings.',
      'macd_bull_cross': 'MACD bullish crossover signal. Indicates potential upward momentum when moving averages cross positively.',
      'div_yield': 'Dividend yield attractiveness. Higher yields provide better income potential for dividend investors.',
      'beta': 'Stock volatility relative to market. Lower beta suggests less volatile, more stable price movements.',
      'below_sma50': 'Price position relative to 50-day moving average. Being below may indicate oversold conditions.',
      'below_sma200': 'Price position relative to 200-day moving average. Being below long-term average may signal value opportunity.'
    };
    return explanations[key] || 'Technical analysis metric used in stock scoring algorithm.';
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-slate-700 pb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">{stock.ticker}</h1>
              <div className="flex items-center space-x-6 text-lg">
                <span className="text-slate-300">
                  Price: <span className="font-semibold text-green-400">${stock.price.toFixed(2)}</span>
                </span>
                <span className="text-slate-300">
                  Score: <span className="font-semibold text-blue-400">{stock.score.toFixed(2)}</span>
                </span>
              </div>
              {/* Show scoring methodology if available */}
              {scoringData && (
                <div className="mt-3">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-900 text-purple-300">
                    Scored using: {scoringData.methodology}
                  </span>
                </div>
              )}
            </div>
            <button
              onClick={toggleStar}
              className={`p-3 rounded-lg transition-all duration-200 ${
                isStarred 
                  ? 'bg-yellow-600 text-white hover:bg-yellow-700' 
                  : 'bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-yellow-400'
              }`}
              title={isStarred ? 'Remove from buy list' : 'Add to buy list'}
            >
              <svg className="w-6 h-6" fill={isStarred ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            </button>
          </div>
          <div className="text-right">
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-600">
              <div className="text-xs text-slate-400 uppercase tracking-wider">Buy Signal</div>
              <div className={`text-2xl font-bold ${stock.score > 7 ? 'text-green-400' : stock.score > 5 ? 'text-yellow-400' : 'text-red-400'}`}>
                {stock.score > 7 ? 'STRONG' : stock.score > 5 ? 'MODERATE' : 'WEAK'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced 4-Layer Analysis */}
      <div className="space-y-8">
        {/* Investment Recommendation */}
        {stock && stock.ticker && typeof stock.price === 'number' && (
          <InvestmentRecommendation 
            data={stock} 
            ticker={stock.ticker} 
            price={stock.price} 
          />
        )}
        
        {/* 4-Layer Methodology Radar Chart */}
        {stock && stock.ticker && (
          <LayeredRadarChart 
            data={stock} 
            ticker={stock.ticker} 
          />
        )}
        
        {/* Layer-by-Layer Breakdown */}
        {stock && stock.ticker && (
          <LayerBreakdown 
            data={stock} 
            ticker={stock.ticker} 
          />
        )}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Price Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-white mb-2">Price vs 52-Week Range</h2>
            <p className="text-slate-400">Historical price movement within 52-week high/low range showing dip opportunities</p>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis 
                  stroke="#94a3b8" 
                  fontSize={12} 
                  domain={[yAxisMin, yAxisMax]}
                  tickFormatter={(value) => `$${value.toFixed(2)}`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #475569', 
                    borderRadius: '8px' 
                  }}
                  formatter={(value: any, name: string) => [
                    `$${Number(value).toFixed(2)}`,
                    name
                  ]}
                />
                <Legend wrapperStyle={{ color: '#cbd5e1' }}/>
                <Line 
                  type="monotone" 
                  name="Current Price" 
                  dataKey="price" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={false} 
                />
                {extraDetails && (
                  <Line 
                    type="monotone" 
                    name="52-Week High" 
                    dataKey="52_week_high" 
                    stroke="#ef4444" 
                    strokeDasharray="5 5" 
                    strokeWidth={2}
                    dot={false} 
                  />
                )}
                {extraDetails && extraDetails['52_week_low'] && (
                  <Line 
                    type="monotone" 
                    name="52-Week Low" 
                    dataKey="52_week_low" 
                    stroke="#10b981" 
                    strokeDasharray="8 3" 
                    strokeWidth={2}
                    dot={false} 
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Volume Analysis for Dip Detection */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-white mb-2">Volume Analysis</h2>
            <p className="text-slate-400">Volume patterns and signals critical for identifying dip buying opportunities</p>
          </div>
          
          {/* Check if volume data is available */}
          {(!stock.volume || !stock.avg_volume || isNaN(stock.volume) || isNaN(stock.avg_volume)) ? (
            <div className="bg-amber-900/50 border border-amber-700 p-6 rounded-lg">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-amber-400 text-xl">⚠️</span>
                <h3 className="text-lg font-semibold text-amber-300">Volume Data Not Available</h3>
              </div>
              <div className="text-amber-200 space-y-2">
                <p>Current volume data is missing or incomplete for this stock.</p>
                <div className="text-sm text-amber-300 bg-amber-900/30 p-3 rounded mt-3">
                  <div className="font-medium mb-1">📊 Data Status:</div>
                  <div>• Current Volume: {stock.volume ? (stock.volume / 1000000).toFixed(1) + 'M' : 'Not Available'}</div>
                  <div>• Average Volume: {stock.avg_volume ? (stock.avg_volume / 1000000).toFixed(1) + 'M' : 'Not Available'}</div>
                </div>
                <div className="text-sm text-amber-300 mt-3">
                  <strong>💡 To get volume data:</strong> Run data collection to gather current volume information from market APIs.
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Volume Spike Analysis */}
              <div className="bg-slate-700 border border-slate-600 p-6 rounded-lg">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-red-400">📊</span>
                  <h3 className="text-lg font-semibold text-white">Volume Spike Detection</h3>
                </div>
                
                <div className="space-y-4">
                  {/* Current Volume vs Average */}
                  <div className="bg-slate-800 p-4 rounded-lg">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-slate-300">Current vs Average</span>
                      <span className={`font-bold text-lg ${
                        (stock.volume / stock.avg_volume) >= 2.0 ? 'text-red-400' :
                        (stock.volume / stock.avg_volume) >= 1.5 ? 'text-orange-400' :
                        (stock.volume / stock.avg_volume) >= 1.2 ? 'text-yellow-400' : 'text-slate-400'
                      }`}>
                        {(stock.volume / stock.avg_volume).toFixed(1)}x
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      Current: {(stock.volume / 1000000).toFixed(1)}M | Avg: {(stock.avg_volume / 1000000).toFixed(1)}M
                    </div>
                    
                    {/* Volume Classification */}
                    <div className="mt-3">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        (stock.volume / stock.avg_volume) >= 3.0 ? 'bg-red-900 text-red-300' :
                        (stock.volume / stock.avg_volume) >= 2.0 ? 'bg-orange-900 text-orange-300' :
                        (stock.volume / stock.avg_volume) >= 1.5 ? 'bg-yellow-900 text-yellow-300' :
                        (stock.volume / stock.avg_volume) >= 1.2 ? 'bg-blue-900 text-blue-300' : 'bg-slate-700 text-slate-400'
                      }`}>
                        {
                          (stock.volume / stock.avg_volume) >= 3.0 ? '🚨 Extreme Spike' :
                          (stock.volume / stock.avg_volume) >= 2.0 ? '🔥 Strong Spike' :
                          (stock.volume / stock.avg_volume) >= 1.5 ? '⚡ Moderate Spike' :
                          (stock.volume / stock.avg_volume) >= 1.2 ? '📈 Mild Increase' : '😴 Normal Volume'
                        }
                      </span>
                    </div>
                  </div>
                  
                  {/* Sweet Spot Indicator */}
                  <div className={`p-3 rounded-lg border-2 ${
                    (stock.volume / stock.avg_volume) >= 1.5 && (stock.volume / stock.avg_volume) <= 3.0 ?
                    'border-green-500 bg-green-900/30' : 'border-slate-600 bg-slate-800'
                  }`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-lg ${
                        (stock.volume / stock.avg_volume) >= 1.5 && (stock.volume / stock.avg_volume) <= 3.0 ?
                        'text-green-400' : 'text-slate-400'
                      }`}>
                        {(stock.volume / stock.avg_volume) >= 1.5 && (stock.volume / stock.avg_volume) <= 3.0 ? '🎯' : '📍'}
                      </span>
                      <span className={`font-medium ${
                        (stock.volume / stock.avg_volume) >= 1.5 && (stock.volume / stock.avg_volume) <= 3.0 ?
                        'text-green-300' : 'text-slate-400'
                      }`}>
                        Dip Hunting Sweet Spot
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      Optimal volume range: 1.5x - 3.0x average for dip opportunities
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Volume Signals & Patterns */}
              <div className="bg-slate-700 border border-slate-600 p-6 rounded-lg">
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-green-400">🔍</span>
                  <h3 className="text-lg font-semibold text-white">Volume Signals</h3>
                </div>
                
                <div className="space-y-3">
                  {/* Capitulation Signal */}
                  <div className={`p-3 rounded-lg ${
                    (stock.volume / stock.avg_volume) >= 2.0 && 
                    stock.prev_close && ((stock.price - stock.prev_close) / stock.prev_close) * 100 <= -3.0 ?
                    'bg-red-900/50 border border-red-700' : 'bg-slate-800'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-red-400">💥</span>
                        <span className="text-sm font-medium text-white">Capitulation Signal</span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded ${
                        (stock.volume / stock.avg_volume) >= 2.0 && 
                        stock.prev_close && ((stock.price - stock.prev_close) / stock.prev_close) * 100 <= -3.0 ?
                        'bg-red-800 text-red-200' : 'bg-slate-700 text-slate-400'
                      }`}>
                        {(stock.volume / stock.avg_volume) >= 2.0 && 
                         stock.prev_close && ((stock.price - stock.prev_close) / stock.prev_close) * 100 <= -3.0 ? 'ACTIVE' : 'Inactive'}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      High volume + significant price drop = potential selling climax
                    </div>
                  </div>
                  
                  {/* Accumulation Signal */}
                  <div className={`p-3 rounded-lg ${
                    (stock.volume / stock.avg_volume) >= 1.3 &&
                    stock.prev_close && Math.abs(((stock.price - stock.prev_close) / stock.prev_close) * 100) <= 2.0 ?
                    'bg-green-900/50 border border-green-700' : 'bg-slate-800'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-green-400">📈</span>
                        <span className="text-sm font-medium text-white">Accumulation Signal</span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded ${
                        (stock.volume / stock.avg_volume) >= 1.3 &&
                        stock.prev_close && Math.abs(((stock.price - stock.prev_close) / stock.prev_close) * 100) <= 2.0 ?
                        'bg-green-800 text-green-200' : 'bg-slate-700 text-slate-400'
                      }`}>
                        {(stock.volume / stock.avg_volume) >= 1.3 &&
                         stock.prev_close && Math.abs(((stock.price - stock.prev_close) / stock.prev_close) * 100) <= 2.0 ? 'ACTIVE' : 'Inactive'}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Above average volume + price stability = smart money buying
                    </div>
                  </div>
                  
                  {/* Volume Trend */}
                  <div className="p-3 rounded-lg bg-slate-800">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-blue-400">📊</span>
                        <span className="text-sm font-medium text-white">Volume Trend</span>
                      </div>
                      <span className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-300">
                        {(stock.volume / stock.avg_volume) > 1.2 ? '📈 Increasing' : 
                         (stock.volume / stock.avg_volume) < 0.8 ? '📉 Decreasing' : '➡️ Stable'}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Current vs historical average volume trend
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Volume Metrics Summary */}
              <div className="lg:col-span-2">
                <div className="bg-slate-700 border border-slate-600 p-6 rounded-lg">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-yellow-400">📋</span>
                    <h3 className="text-lg font-semibold text-white">Volume Analysis Summary</h3>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {/* Current Volume */}
                    <div className="text-center p-3 bg-slate-800 rounded-lg">
                      <div className="text-lg font-bold text-white">
                        {(stock.volume / 1000000).toFixed(1)}M
                      </div>
                      <div className="text-xs text-slate-400">Current Volume</div>
                    </div>
                    
                    {/* Average Volume */}
                    <div className="text-center p-3 bg-slate-800 rounded-lg">
                      <div className="text-lg font-bold text-white">
                        {(stock.avg_volume / 1000000).toFixed(1)}M
                      </div>
                      <div className="text-xs text-slate-400">Historical Average</div>
                    </div>
                    
                    {/* Volume Ratio */}
                    <div className="text-center p-3 bg-slate-800 rounded-lg">
                      <div className={`text-lg font-bold ${
                        (stock.volume / stock.avg_volume) >= 2.0 ? 'text-red-400' :
                        (stock.volume / stock.avg_volume) >= 1.5 ? 'text-orange-400' :
                        'text-white'
                      }`}>
                        {(stock.volume / stock.avg_volume).toFixed(2)}x
                      </div>
                      <div className="text-xs text-slate-400">Volume Ratio</div>
                    </div>
                    
                    {/* Dip Opportunity Indicator */}
                    <div className="text-center p-3 bg-slate-800 rounded-lg">
                      <div className={`text-lg font-bold ${
                        (stock.volume / stock.avg_volume) >= 1.5 && 
                        (stock.volume / stock.avg_volume) <= 3.0 ?
                        'text-green-400' : 'text-slate-400'
                      }`}>
                        {(stock.volume / stock.avg_volume) >= 1.5 && 
                         (stock.volume / stock.avg_volume) <= 3.0 ? '🎯' : '⏸️'}
                      </div>
                      <div className="text-xs text-slate-400">Dip Opportunity</div>
                    </div>
                  </div>
                  
                  {/* Volume Interpretation */}
                  <div className="mt-4 p-4 bg-slate-800 rounded-lg">
                    <h4 className="text-sm font-semibold text-white mb-2">💡 Volume Analysis Interpretation</h4>
                    <div className="text-sm text-slate-300 space-y-1">
                      {(stock.volume / stock.avg_volume) >= 3.0 && (
                        <div className="flex items-start gap-2">
                          <span className="text-red-400 mt-0.5">⚠️</span>
                          <span>Extreme volume spike may indicate distribution or panic selling. Exercise caution.</span>
                        </div>
                      )}
                      {(stock.volume / stock.avg_volume) >= 1.5 && (stock.volume / stock.avg_volume) < 3.0 && (
                        <div className="flex items-start gap-2">
                          <span className="text-green-400 mt-0.5">✅</span>
                          <span>Volume in optimal range for dip opportunities. Increased interest with controlled selling.</span>
                        </div>
                      )}
                      {(stock.volume / stock.avg_volume) < 1.5 && (
                        <div className="flex items-start gap-2">
                          <span className="text-yellow-400 mt-0.5">📊</span>
                          <span>Normal to low volume. May lack conviction for significant price movement.</span>
                        </div>
                      )}
                      <div className="flex items-start gap-2">
                        <span className="text-blue-400 mt-0.5">💭</span>
                        <span>Volume analysis works best when combined with price action and technical indicators.</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Score Details and Market Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Enhanced Score Breakdown */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
          <h2 className="text-2xl font-bold text-white mb-6">
            {scoringData ? 'New Scoring Results' : 'Current Score Breakdown'}
          </h2>
          
          {/* Layer Scores Grid */}
          {(scoringData?.layer_scores || stock.layer_scores) && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              {/* Quality Gate */}
              <div className="bg-slate-700 border-2 border-blue-600/30 p-4 rounded-lg text-center hover:bg-slate-600 transition-all duration-300">
                <h3 className="text-blue-400 text-sm font-medium uppercase tracking-wider mb-2">Quality Gate</h3>
                <p className="text-2xl font-bold mb-2 text-blue-400">
                  {((scoringData?.layer_scores?.quality_gate || stock.layer_scores?.quality_gate || 0)).toFixed(1)}
                </p>
                <div className="text-xs text-slate-400">/ 35 points</div>
                <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
                  <div 
                    className="h-1 rounded-full transition-all duration-300 bg-blue-500"
                    style={{ 
                      width: `${Math.min(((scoringData?.layer_scores?.quality_gate || stock.layer_scores?.quality_gate || 0) / 35) * 100, 100)}%`
                    }}
                  ></div>
                </div>
              </div>

              {/* Dip Signal */}
              <div className="bg-slate-700 border-2 border-red-600/30 p-4 rounded-lg text-center hover:bg-slate-600 transition-all duration-300">
                <h3 className="text-red-400 text-sm font-medium uppercase tracking-wider mb-2">Dip Signal</h3>
                <p className="text-2xl font-bold mb-2 text-red-400">
                  {((scoringData?.layer_scores?.dip_signal || stock.layer_scores?.dip_signal || 0)).toFixed(1)}
                </p>
                <div className="text-xs text-slate-400">/ 45 points</div>
                <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
                  <div 
                    className="h-1 rounded-full transition-all duration-300 bg-red-500"
                    style={{ 
                      width: `${Math.min(((scoringData?.layer_scores?.dip_signal || stock.layer_scores?.dip_signal || 0) / 45) * 100, 100)}%`
                    }}
                  ></div>
                </div>
              </div>

              {/* Reversal Spark */}
              <div className="bg-slate-700 border-2 border-green-600/30 p-4 rounded-lg text-center hover:bg-slate-600 transition-all duration-300">
                <h3 className="text-green-400 text-sm font-medium uppercase tracking-wider mb-2">Reversal Spark</h3>
                <p className="text-2xl font-bold mb-2 text-green-400">
                  {((scoringData?.layer_scores?.reversal_spark || stock.layer_scores?.reversal_spark || 0)).toFixed(1)}
                </p>
                <div className="text-xs text-slate-400">/ 15 points</div>
                <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
                  <div 
                    className="h-1 rounded-full transition-all duration-300 bg-green-500"
                    style={{ 
                      width: `${Math.min(((scoringData?.layer_scores?.reversal_spark || stock.layer_scores?.reversal_spark || 0) / 15) * 100, 100)}%`
                    }}
                  ></div>
                </div>
              </div>

              {/* Risk Adjustment */}
              <div className="bg-slate-700 border-2 border-amber-600/30 p-4 rounded-lg text-center hover:bg-slate-600 transition-all duration-300">
                <h3 className="text-amber-400 text-sm font-medium uppercase tracking-wider mb-2">Risk Adjustment</h3>
                <p className="text-2xl font-bold mb-2 text-amber-400">
                  {(scoringData?.layer_scores?.risk_adjustment || stock.layer_scores?.risk_adjustment || 0) >= 0 ? '+' : ''}
                  {((scoringData?.layer_scores?.risk_adjustment || stock.layer_scores?.risk_adjustment || 0)).toFixed(1)}
                </p>
                <div className="text-xs text-slate-400">± 10 points</div>
                <div className="w-full bg-slate-600 rounded-full h-1 mt-2">
                  <div 
                    className="h-1 rounded-full transition-all duration-300 bg-amber-500"
                    style={{ 
                      width: `${Math.min(Math.abs((scoringData?.layer_scores?.risk_adjustment || stock.layer_scores?.risk_adjustment || 0)) * 10, 100)}%`
                    }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          {/* Key Financial Metrics */}
          <div className="border-t border-slate-700 pt-6">
            <h3 className="text-lg font-semibold text-white mb-4">Key Metrics</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {/* P/E Ratio */}
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">P/E Ratio</span>
                <span className={`font-bold ${
                  stock.pe_ratio ? (stock.pe_ratio <= 20 ? 'text-green-400' : stock.pe_ratio <= 30 ? 'text-yellow-400' : 'text-red-400') : 'text-slate-400'
                }`}>
                  {stock.pe_ratio ? stock.pe_ratio.toFixed(1) : 'N/A'}
                </span>
              </div>
              
              {/* Drop from 52W High */}
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Drop from 52W High</span>
                <span className={`font-bold ${
                  stock.pct_below_52w_high ? (stock.pct_below_52w_high >= 20 ? 'text-green-400' : stock.pct_below_52w_high >= 10 ? 'text-yellow-400' : 'text-red-400') : 'text-slate-400'
                }`}>
                  {stock.pct_below_52w_high ? `${stock.pct_below_52w_high.toFixed(1)}%` : 'N/A'}
                </span>
              </div>

              {/* Dividend Yield */}
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Dividend Yield</span>
                <span className={`font-bold ${
                  stock.dividend_yield ? (stock.dividend_yield >= 0.03 ? 'text-green-400' : stock.dividend_yield >= 0.015 ? 'text-yellow-400' : 'text-orange-400') : 'text-slate-400'
                }`}>
                  {stock.dividend_yield ? `${(stock.dividend_yield * 100).toFixed(2)}%` : 'None'}
                </span>
              </div>

              {/* Beta */}
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Beta (Volatility)</span>
                <span className={`font-bold ${
                  stock.beta ? (stock.beta <= 1.2 ? 'text-green-400' : stock.beta <= 1.5 ? 'text-yellow-400' : 'text-red-400') : 'text-slate-400'
                }`}>
                  {stock.beta ? stock.beta.toFixed(2) : 'N/A'}
                </span>
              </div>

              {/* Debt to Equity */}
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded">
                <span className="text-slate-300">Debt/Equity</span>
                <span className={`font-bold ${
                  stock.debt_to_equity ? (stock.debt_to_equity <= 0.5 ? 'text-green-400' : stock.debt_to_equity <= 1.0 ? 'text-yellow-400' : 'text-red-400') : 'text-slate-400'
                }`}>
                  {stock.debt_to_equity ? stock.debt_to_equity.toFixed(2) : 'N/A'}
                </span>
              </div>

              {/* Overall Score */}
              <div className="flex justify-between items-center bg-slate-700 p-3 rounded border border-amber-600/30">
                <span className="text-slate-300 font-medium">Overall Score</span>
                <span className={`font-bold text-xl ${
                  (scoringData?.score || stock.score || 0) >= 70 ? 'text-green-400' : 
                  (scoringData?.score || stock.score || 0) >= 50 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {(scoringData?.score || stock.score || 0).toFixed(1)}/100
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Market Details */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
          <h2 className="text-2xl font-bold text-white mb-6">Market Details</h2>
          {detailsError && (
            <div className="mb-4 p-3 bg-yellow-900/50 border border-yellow-700 rounded-lg">
              <p className="text-yellow-300 text-sm">⚠️ {detailsError}</p>
            </div>
          )}
          
          {/* Company Name Header */}
          {stock.company_name && (
            <div className="mb-6 pb-4 border-b border-slate-600">
              <div className="flex items-center gap-4">
                {stock.logo && (
                  <img 
                    src={stock.logo} 
                    alt={`${stock.company_name} logo`}
                    className="w-12 h-12 rounded-lg object-contain bg-white p-1"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                )}
                <div>
                  <h3 className="text-xl font-semibold text-white">{stock.company_name}</h3>
                  <p className="text-slate-400 text-sm">{stock.ticker}</p>
                </div>
              </div>
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Company Information */}
            <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-blue-400">🏢</span>
                <h3 className="text-lg font-semibold text-white">Company Information</h3>
              </div>
              <div className="space-y-2 text-sm">
                {stock.country && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Country:</span>
                    <span className="text-white">{stock.country}</span>
                  </div>
                )}
                {stock.sector && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Sector:</span>
                    <span className="text-white">{stock.sector}</span>
                  </div>
                )}
                {stock.industry && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Industry:</span>
                    <span className="text-white">{stock.industry}</span>
                  </div>
                )}
                {stock.finnhub_industry && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Classification:</span>
                    <span className="text-white">{stock.finnhub_industry}</span>
                  </div>
                )}
                {stock.ipo_date && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">IPO Date:</span>
                    <span className="text-white">{stock.ipo_date}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Contact & Links */}
            <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-green-400">📞</span>
                <h3 className="text-lg font-semibold text-white">Contact & Links</h3>
              </div>
              <div className="space-y-2 text-sm">
                {stock.website && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Website:</span>
                    <a 
                      href={stock.website.startsWith('http') ? stock.website : `https://${stock.website}`}
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 underline"
                    >
                      Visit Site
                    </a>
                  </div>
                )}
                {stock.phone && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Phone:</span>
                    <span className="text-white">{stock.phone}</span>
                  </div>
                )}
                {stock.exchange && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Exchange:</span>
                    <span className="text-white">{stock.exchange}</span>
                  </div>
                )}
                {stock.currency && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Currency:</span>
                    <span className="text-white">{stock.currency}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Trading Information */}
            <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-purple-400">📊</span>
                <h3 className="text-lg font-semibold text-white">Trading Information</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Avg Volume:</span>
                  <span className="text-white">
                    {stock.avg_volume ? (stock.avg_volume / 1000000).toFixed(1) + 'M' : 'N/A'}
                  </span>
                </div>
                {stock.shares_outstanding && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Shares Outstanding:</span>
                    <span className="text-white">
                      {(stock.shares_outstanding / 1000000).toFixed(1)}M
                    </span>
                  </div>
                )}
                {stock.finnhub_shares_outstanding && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Shares (Finnhub):</span>
                    <span className="text-white">
                      {(stock.finnhub_shares_outstanding / 1000000).toFixed(1)}M
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Financial Summary */}
            <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-yellow-400">💰</span>
                <h3 className="text-lg font-semibold text-white">Financial Summary</h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Market Cap:</span>
                  <span className="text-white">
                    ${stock.market_cap ? (stock.market_cap / 1000000000).toFixed(1) + 'B' : 'N/A'}
                  </span>
                </div>
                {stock.pe && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">P/E Ratio:</span>
                    <span className="text-white">{stock.pe.toFixed(2)}</span>
                  </div>
                )}
                {stock.dividend_yield && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Dividend Yield:</span>
                    <span className="text-white">{(stock.dividend_yield * 100).toFixed(2)}%</span>
                  </div>
                )}
                {stock.beta && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Beta:</span>
                    <span className="text-white">{stock.beta.toFixed(2)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StockDetailPage; 