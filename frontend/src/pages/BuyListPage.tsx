import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

interface BuyListStock {
  ticker: string;
  price: number;
  score: number;
  addedDate: string;
}

const BuyListPage = () => {
  const [buyList, setBuyList] = useState<BuyListStock[]>([]);

  useEffect(() => {
    // Load buy list from localStorage
    const saved = localStorage.getItem('buyList');
    if (saved) {
      setBuyList(JSON.parse(saved));
    }
  }, []);

  const removeFromBuyList = (ticker: string) => {
    const updated = buyList.filter(stock => stock.ticker !== ticker);
    setBuyList(updated);
    localStorage.setItem('buyList', JSON.stringify(updated));
  };

  const clearBuyList = () => {
    setBuyList([]);
    localStorage.removeItem('buyList');
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-slate-700 pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2 flex items-center">
              <svg className="w-8 h-8 mr-3 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
              My Buy List
            </h1>
            <p className="text-lg text-slate-400">Your starred stocks for potential dip-buying opportunities</p>
          </div>
          {buyList.length > 0 && (
            <button
              onClick={clearBuyList}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Buy List Content */}
      {buyList.length === 0 ? (
        <div className="text-center py-16">
          <svg className="w-16 h-16 mx-auto text-slate-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
          <h2 className="text-2xl font-bold text-slate-400 mb-2">No Stocks in Buy List</h2>
          <p className="text-slate-500 mb-6">Star some stocks from the analysis pages to add them here</p>
          <Link
            to="/"
            className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            Browse Stocks
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {buyList.map((stock) => (
            <div key={stock.ticker} className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <Link
                  to={`/stock/${stock.ticker}`}
                  className="text-xl font-bold text-white hover:text-blue-400 transition-colors"
                >
                  {stock.ticker}
                </Link>
                <button
                  onClick={() => removeFromBuyList(stock.ticker)}
                  className="text-slate-400 hover:text-red-400 transition-colors"
                  title="Remove from buy list"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">Price:</span>
                  <span className="text-green-400 font-semibold">${stock.price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Score:</span>
                  <span className="text-blue-400 font-semibold">{stock.score.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Added:</span>
                  <span className="text-slate-300">{new Date(stock.addedDate).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-700">
                <Link
                  to={`/stock/${stock.ticker}`}
                  className="w-full inline-flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  View Analysis
                  <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BuyListPage; 