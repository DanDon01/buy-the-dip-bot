import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  api, ApiError,
  type PortfolioSummary, type PositionSizeSuggestion,
} from '../lib/api';

const fmtMoney = (v: number | null | undefined) =>
  v == null ? '—' : v.toLocaleString('en-US', { style: 'currency', currency: 'USD' });

const pnlColor = (v: number | null | undefined) =>
  v == null ? 'text-slate-400' : v >= 0 ? 'text-emerald-400' : 'text-red-400';

function StatCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
      <p className="text-slate-400 text-sm mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ?? 'text-white'}`}>{value}</p>
    </div>
  );
}

const PortfolioPage = () => {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Trade form state
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('');
  const [price, setPrice] = useState('');
  const [busy, setBusy] = useState(false);

  // Position sizing
  const [sizeTicker, setSizeTicker] = useState('');
  const [sizing, setSizing] = useState<PositionSizeSuggestion | null>(null);
  const [sizingError, setSizingError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSummary(await api.get<PortfolioSummary>('/api/portfolio'));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load portfolio');
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const submitTrade = async (side: 'buy' | 'sell') => {
    if (!ticker || !price || (side === 'buy' && !shares)) {
      setMessage('Ticker, price' + (side === 'buy' ? ' and shares' : '') + ' are required.');
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      if (side === 'buy') {
        await api.post('/api/portfolio/position', {
          ticker, shares: Number(shares), price: Number(price),
        });
        setMessage(`Bought ${shares} ${ticker.toUpperCase()} @ $${price}`);
      } else {
        await api.post('/api/portfolio/sell', {
          ticker, shares: shares ? Number(shares) : null, price: Number(price),
        });
        setMessage(`Sold ${ticker.toUpperCase()} @ $${price}`);
      }
      setTicker(''); setShares(''); setPrice('');
      await load();
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : 'Trade failed');
    } finally {
      setBusy(false);
    }
  };

  const fetchSizing = async () => {
    if (!sizeTicker) return;
    setSizing(null);
    setSizingError(null);
    try {
      setSizing(await api.get<PositionSizeSuggestion>(
        `/api/portfolio/position-size/${sizeTicker.toUpperCase()}`));
    } catch (e) {
      setSizingError(e instanceof Error ? e.message : 'No sizing data');
    }
  };

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-700 rounded-xl p-6">
        <p className="text-red-300">💼 {error}</p>
      </div>
    );
  }
  if (!summary) {
    return <p className="text-slate-400 animate-pulse p-6">Loading portfolio…</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">💼 Portfolio</h1>
        <p className="text-slate-400">
          Holdings, P&amp;L and risk-based position sizing
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Market Value" value={fmtMoney(summary.total_market_value)} />
        <StatCard label="Cost Basis" value={fmtMoney(summary.total_cost)} />
        <StatCard label="Unrealized P&L" value={fmtMoney(summary.total_unrealized_pnl)}
                  accent={pnlColor(summary.total_unrealized_pnl)} />
        <StatCard label="Realized P&L" value={fmtMoney(summary.total_realized_pnl)}
                  accent={pnlColor(summary.total_realized_pnl)} />
      </div>

      {/* Holdings table */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-bold text-white mb-4">Open Positions</h2>
        {summary.positions.length === 0 ? (
          <p className="text-slate-400">No open positions — record a buy below.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 pr-4">Ticker</th>
                  <th className="text-right py-2 px-4">Shares</th>
                  <th className="text-right py-2 px-4">Avg Cost</th>
                  <th className="text-right py-2 px-4">Price</th>
                  <th className="text-right py-2 px-4">Value</th>
                  <th className="text-right py-2 px-4">P&L</th>
                  <th className="text-right py-2 pl-4">P&L %</th>
                </tr>
              </thead>
              <tbody>
                {summary.positions.map((p) => (
                  <tr key={p.ticker} className="border-b border-slate-700/50 text-slate-200">
                    <td className="py-3 pr-4">
                      <Link to={`/stock/${p.ticker}`}
                            className="font-semibold text-blue-400 hover:text-blue-300">
                        {p.ticker}
                      </Link>
                    </td>
                    <td className="text-right px-4">{p.shares}</td>
                    <td className="text-right px-4">{fmtMoney(p.avg_cost)}</td>
                    <td className="text-right px-4">{fmtMoney(p.current_price)}</td>
                    <td className="text-right px-4">{fmtMoney(p.market_value)}</td>
                    <td className={`text-right px-4 ${pnlColor(p.unrealized_pnl)}`}>
                      {fmtMoney(p.unrealized_pnl)}
                    </td>
                    <td className={`text-right pl-4 ${pnlColor(p.unrealized_pnl_pct)}`}>
                      {p.unrealized_pnl_pct == null ? '—' : `${p.unrealized_pnl_pct.toFixed(1)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Record trade */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Record a Trade</h2>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
                   placeholder="Ticker"
                   className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-slate-500" />
            <input value={shares} onChange={(e) => setShares(e.target.value)}
                   placeholder="Shares" type="number" min="0"
                   className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-slate-500" />
            <input value={price} onChange={(e) => setPrice(e.target.value)}
                   placeholder="Price" type="number" min="0" step="0.01"
                   className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-slate-500" />
          </div>
          <div className="flex gap-3">
            <button onClick={() => submitTrade('buy')} disabled={busy}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold py-2 rounded-lg transition-colors">
              Buy
            </button>
            <button onClick={() => submitTrade('sell')} disabled={busy}
                    className="flex-1 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-semibold py-2 rounded-lg transition-colors">
              Sell
            </button>
          </div>
          <p className="text-slate-500 text-xs mt-2">
            Selling with an empty share count closes the whole position.
          </p>
          {message && <p className="text-amber-300 text-sm mt-3">{message}</p>}
        </div>

        {/* Position sizing */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Position Sizing</h2>
          <div className="flex gap-3 mb-4">
            <input value={sizeTicker}
                   onChange={(e) => setSizeTicker(e.target.value.toUpperCase())}
                   onKeyDown={(e) => e.key === 'Enter' && fetchSizing()}
                   placeholder="Ticker (must be in the data cache)"
                   className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-slate-500" />
            <button onClick={fetchSizing}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-4 rounded-lg transition-colors">
              Suggest
            </button>
          </div>
          {sizingError && <p className="text-red-400 text-sm">{sizingError}</p>}
          {sizing && (
            <div className="space-y-2 text-sm text-slate-200">
              <div className="flex justify-between"><span className="text-slate-400">Suggested shares</span><span className="font-bold text-white">{sizing.shares}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Position value</span><span>{fmtMoney(sizing.position_value)} ({sizing.position_pct_of_capital}% of capital)</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Stop-loss</span><span>{fmtMoney(sizing.stop_price)}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Capital at risk</span><span>{fmtMoney(sizing.risk_budget)}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Conviction</span><span>{sizing.conviction_multiplier}×{sizing.capped_by_max_position ? ' (capped)' : ''}</span></div>
            </div>
          )}
          <p className="text-slate-500 text-xs mt-3">
            Sizing risks a fixed % of capital with an ATR-derived stop, scaled by the
            stock's dip score. Tune the parameters in <code>cache/portfolio.json</code>.
          </p>
        </div>
      </div>

      {/* Recent closed trades */}
      {summary.closed_trades.length > 0 && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Recent Closed Trades</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 pr-4">Ticker</th>
                  <th className="text-right py-2 px-4">Shares</th>
                  <th className="text-right py-2 px-4">Buy</th>
                  <th className="text-right py-2 px-4">Sell</th>
                  <th className="text-right py-2 px-4">P&L</th>
                  <th className="text-right py-2 pl-4">Closed</th>
                </tr>
              </thead>
              <tbody>
                {[...summary.closed_trades].reverse().map((t, i) => (
                  <tr key={`${t.ticker}-${t.closed}-${i}`}
                      className="border-b border-slate-700/50 text-slate-200">
                    <td className="py-2 pr-4 font-semibold">{t.ticker}</td>
                    <td className="text-right px-4">{t.shares}</td>
                    <td className="text-right px-4">{fmtMoney(t.buy_price)}</td>
                    <td className="text-right px-4">{fmtMoney(t.sell_price)}</td>
                    <td className={`text-right px-4 ${pnlColor(t.realized_pnl)}`}>
                      {fmtMoney(t.realized_pnl)} ({t.realized_pnl_pct.toFixed(1)}%)
                    </td>
                    <td className="text-right pl-4 text-slate-400">
                      {t.closed?.slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioPage;
