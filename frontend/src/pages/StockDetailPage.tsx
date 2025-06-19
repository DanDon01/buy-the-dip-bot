import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

const StockDetailPage = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const [stock, setStock] = useState<any>(null);
  const [extraDetails, setExtraDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [stockError, setStockError] = useState<string | null>(null);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [isStarred, setIsStarred] = useState(false);

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
          setStock(stockData);

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
  }, [ticker]);

  const toggleStar = () => {
    if (!stock) return;

    const buyList = JSON.parse(localStorage.getItem('buyList') || '[]');
    
    if (isStarred) {
      // Remove from buy list
      const updated = buyList.filter((s: any) => s.ticker !== stock.ticker);
      localStorage.setItem('buyList', JSON.stringify(updated));
      setIsStarred(false);
    } else {
      // Add to buy list
      const newStock = {
        ticker: stock.ticker,
        price: stock.price,
        score: stock.score,
        addedDate: new Date().toISOString()
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

  // Create radar chart data for individual stock
  const radarData = [{
    factor: 'Overall Score',
    value: stock.score,
    fullMark: 10
  }];

  // Add individual score components if available
  if (stock.score_details) {
    Object.entries(stock.score_details).forEach(([key, value]: [string, any]) => {
      radarData.push({
        factor: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value: value * 10, // Scale to 0-10
        fullMark: 10
      });
    });
  }

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
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #475569', 
                    borderRadius: '8px' 
                  }} 
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
                  dataKey="factor" 
                  tick={{ fill: '#cbd5e1', fontSize: 12 }}
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
                />
                <Radar 
                  name={stock.ticker}
                  dataKey="value" 
                  stroke="#3b82f6" 
                  fill="#3b82f6" 
                  fillOpacity={0.2} 
                  strokeWidth={2} 
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Score Details and Market Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Score Breakdown */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-8">
          <h2 className="text-2xl font-bold text-white mb-6">Score Breakdown</h2>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(stock.score_details).map(([key, value]: [string, any]) => (
              <div key={key} className="bg-slate-700 border border-slate-600 p-4 rounded-lg text-center hover:border-slate-500 transition-colors">
                <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-2">
                  {key.replace(/_/g, ' ')}
                </h3>
                <p className="text-2xl font-bold text-white">{value.toFixed(2)}</p>
                <div className="w-full bg-slate-600 rounded-full h-1 mt-3">
                  <div 
                    className="bg-blue-500 h-1 rounded-full transition-all duration-300" 
                    style={{ width: `${Math.min(value * 10, 100)}%` }}
                  ></div>
                </div>
              </div>
            ))}
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