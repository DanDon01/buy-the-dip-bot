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
    '52_week_high': extraDetails?.['52_week_high']
  })) || [];

  // Calculate Y-axis domain to focus on price range
  const calculateYAxisDomain = () => {
    if (chartData.length === 0) return [0, 100];
    
    const prices = chartData.map((item: any) => item.price).filter((price: number) => price > 0);
    const high52w = extraDetails?.['52_week_high'];
    
    if (prices.length === 0) return [0, 100];
    
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices, high52w || 0);
    
    // Start Y-axis 15% below the lowest price for better focus
    const yAxisMin = minPrice * 0.85;
    // Add 5% padding above the highest value
    const yAxisMax = maxPrice * 1.05;
    
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
            <h2 className="text-2xl font-bold text-white mb-2">Price vs 52-Week High</h2>
            <p className="text-slate-400">Historical price movement showing potential dip opportunities</p>
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
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Individual Radar Chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-white mb-2">{stock.ticker} Score Radar</h2>
            <p className="text-slate-400">Multi-dimensional analysis of all scoring factors</p>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#475569" />
                <PolarAngleAxis 
                  dataKey="subject"
                  tick={(props: any) => {
                    const { x, y, payload, index } = props;
                    const color = radarColors[index % radarColors.length];
                    
                    // Calculate center point (assuming center is around 150,150 for typical radar size)
                    const centerX = 150;
                    const centerY = 150;
                    
                    // Calculate direction from center to current position
                    const dx = x - centerX;
                    const dy = y - centerY;
                    
                    // Normalize and extend outward by 20 pixels
                    const length = Math.sqrt(dx * dx + dy * dy);
                    const offsetDistance = 20;
                    const newX = x + (dx / length) * offsetDistance;
                    const newY = y + (dy / length) * offsetDistance;
                    
                    return (
                      <text
                        x={newX}
                        y={newY}
                        fill={color}
                        fontSize={12}
                        textAnchor="middle"
                        dominantBaseline="central"
                        className="font-medium"
                      >
                        {payload.value}
                      </text>
                    );
                  }}
                  className="text-slate-300"
                />
                <PolarRadiusAxis 
                  angle={90} 
                  domain={[0, 10]} 
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  tickCount={6}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #475569', 
                    borderRadius: '8px' 
                  }}
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      // Only show tooltip for the main score data, filter out layer data
                      const scoreData = payload.find((item: any) => item.name === 'Score');
                      if (scoreData) {
                        return (
                          <div style={{
                            backgroundColor: '#1e293b',
                            border: '1px solid #475569',
                            borderRadius: '8px',
                            padding: '8px'
                          }}>
                            <p style={{ color: '#cbd5e1', margin: 0 }}>
                              {`${label}: ${typeof scoreData.value === 'number' ? scoreData.value.toFixed(2) : scoreData.value || 'N/A'}`}
                            </p>
                          </div>
                        );
                      }
                    }
                    return null;
                  }}
                />
                
                {/* Create multiple overlapping radars with different colors */}
                {radarColors.map((color, colorIndex) => (
                  <Radar
                    key={`color-${colorIndex}`}
                    name={`Layer ${colorIndex}`}
                    dataKey="A"
                    stroke={color}
                    fill={color}
                    fillOpacity={0.08}
                    strokeWidth={1}
                    dot={false}
                    isAnimationActive={false}
                  />
                ))}
                
                {/* Main radar with colored dots on top */}
                <Radar
                  name="Score"
                  dataKey="A"
                  stroke="transparent"
                  fill="transparent"
                  fillOpacity={0}
                  strokeWidth={0}
                  dot={(dotProps: any) => {
                    const { cx = 0, cy = 0, index = 0 } = dotProps;
                    const safeIndex = typeof index === 'number' && !isNaN(index) ? index : 0;
                    const safeCx = typeof cx === 'number' && !isNaN(cx) ? cx : 0;
                    const safeCy = typeof cy === 'number' && !isNaN(cy) ? cy : 0;
                    const color = radarColors[safeIndex % radarColors.length];
                    return (
                      <circle
                        key={`radar-dot-${safeIndex}`}
                        cx={safeCx}
                        cy={safeCy}
                        r={5}
                        fill={color}
                        stroke={color}
                        strokeWidth={2}
                      />
                    );
                  }}
                  isAnimationActive={false}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
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
          
          <div className="grid grid-cols-1 gap-4">
            {extraDetails ? (
              <>
                <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
                  <div className="flex items-center justify-between">
                    <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">Market Cap</h3>
                    <p className="text-xl font-bold text-white">
                      {extraDetails.market_cap ? `$${(extraDetails.market_cap / 1_000_000_000).toFixed(2)}B` : 'N/A'}
                    </p>
                  </div>
                </div>
                
                <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
                  <div className="flex items-center justify-between">
                    <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">Forward P/E</h3>
                    <p className="text-xl font-bold text-white">
                      {extraDetails.forward_pe ? extraDetails.forward_pe.toFixed(2) : 'N/A'}
                    </p>
                  </div>
                </div>
                
                <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
                  <div className="flex items-center justify-between">
                    <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">Dividend Yield</h3>
                    <p className="text-xl font-bold text-white">
                      {extraDetails.dividend_yield ? `${(extraDetails.dividend_yield * 100).toFixed(2)}%` : 'N/A'}
                    </p>
                  </div>
                </div>

                <div className="bg-slate-700 border border-slate-600 p-4 rounded-lg hover:border-slate-500 transition-colors">
                  <div className="flex items-center justify-between">
                    <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">52-Week Range</h3>
                    <p className="text-xl font-bold text-white">
                      {extraDetails['52_week_low'] && extraDetails['52_week_high'] 
                        ? `$${extraDetails['52_week_low'].toFixed(2)} - $${extraDetails['52_week_high'].toFixed(2)}`
                        : 'N/A'}
                    </p>
                  </div>
                </div>
              </>
            ) : !detailsError ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-pulse text-slate-400">Loading market details...</div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StockDetailPage; 