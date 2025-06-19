import { useEffect, useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import ActionCenter from './ActionCenter';

interface Stock {
  ticker: string;
  score: number;
  price: number;
}

const StockSidebar = () => {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const fetchStocks = async () => {
      try {
        const res = await fetch('http://localhost:5001/api/stocks');
        if (!res.ok) throw new Error('Failed to fetch stocks');
        const data = await res.json();
        setStocks(data);
      } catch (err: any) {
        setError(err.message);
      }
    };
    fetchStocks();
  }, []);

  const topStocks = stocks.slice(0, 5);
  const remainingStocks = stocks.slice(5);

  return (
    <div className="space-y-6">
      {/* Navigation Buttons */}
      <div className="space-y-2">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `flex items-center px-3 py-3 rounded-lg transition-all duration-200 ${
              isActive
                ? 'bg-blue-600 text-white shadow-lg'
                : 'hover:bg-slate-700 text-slate-300 hover:text-white'
            }`
          }
        >
          <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Dashboard
        </NavLink>

        <NavLink
          to="/buylist"
          className={({ isActive }) =>
            `flex items-center px-3 py-3 rounded-lg transition-all duration-200 ${
              isActive
                ? 'bg-yellow-600 text-white shadow-lg'
                : 'hover:bg-slate-700 text-slate-300 hover:text-white'
            }`
          }
        >
          <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
          Buy List
        </NavLink>
      </div>

      {/* Top Performers Section */}
      <div>
        <h2 className="text-lg font-semibold text-slate-200 mb-4 px-2">Top Performers</h2>
        <div className="space-y-1">
          {topStocks.map((stock, index) => (
            <NavLink
              key={stock.ticker}
              to={`/stock/${stock.ticker}`}
              className={({ isActive }) =>
                `block px-3 py-3 rounded-lg transition-all duration-200 ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'hover:bg-slate-700 text-slate-300 hover:text-white'
                }`
              }
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center text-xs font-bold">
                    {index + 1}
                  </div>
                  <div>
                    <div className="font-semibold text-sm">{stock.ticker}</div>
                    <div className="text-xs text-slate-400">${stock.price?.toFixed(2) || 'N/A'}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-green-400">{stock.score.toFixed(1)}</div>
                  <div className="text-xs text-slate-500">score</div>
                </div>
              </div>
            </NavLink>
          ))}
        </div>
      </div>

      {/* Show More Stocks */}
      {remainingStocks.length > 0 && (
        <div>
          <button
            onClick={() => setShowAll(!showAll)}
            className="w-full text-left px-3 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors duration-200"
          >
            {showAll ? '▼ Show Less' : `▶ Show ${remainingStocks.length} More Stocks`}
          </button>
          {showAll && (
            <div className="space-y-1 mt-2">
              {remainingStocks.map((stock, index) => (
                <NavLink
                  key={stock.ticker}
                  to={`/stock/${stock.ticker}`}
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'hover:bg-slate-700 text-slate-400 hover:text-white'
                    }`
                  }
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-6 h-6 bg-slate-600 rounded flex items-center justify-center text-xs">
                        {topStocks.length + index + 1}
                      </div>
                      <span className="text-sm">{stock.ticker}</span>
                    </div>
                    <span className="text-xs text-green-400">{stock.score.toFixed(1)}</span>
                  </div>
                </NavLink>
              ))}
            </div>
          )}
        </div>
      )}

      <ActionCenter />

      {error && (
        <div className="px-3 py-2 bg-red-900 border border-red-700 rounded-lg">
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}
    </div>
  );
};

export default StockSidebar; 