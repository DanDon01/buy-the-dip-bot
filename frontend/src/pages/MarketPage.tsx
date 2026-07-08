import { useCallback, useEffect, useState } from 'react';
import {
  api, type BacktestReport, type SectorRotation,
} from '../lib/api';

const PHASE_STYLES: Record<string, string> = {
  leading: 'bg-emerald-900/60 text-emerald-300 border-emerald-700',
  improving: 'bg-sky-900/60 text-sky-300 border-sky-700',
  weakening: 'bg-amber-900/60 text-amber-300 border-amber-700',
  lagging: 'bg-red-900/60 text-red-300 border-red-700',
  unknown: 'bg-slate-700 text-slate-300 border-slate-600',
};

const pct = (v: number | null | undefined, digits = 1) =>
  v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`;

const pctColor = (v: number | null | undefined) =>
  v == null ? 'text-slate-400' : v >= 0 ? 'text-emerald-400' : 'text-red-400';

const MarketPage = () => {
  const [rotation, setRotation] = useState<SectorRotation | null>(null);
  const [rotationError, setRotationError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [backtests, setBacktests] = useState<BacktestReport[]>([]);

  const loadRotation = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    try {
      setRotation(await api.get<SectorRotation>(
        `/api/sectors${refresh ? '?refresh=1' : ''}`));
      setRotationError(null);
    } catch (e) {
      setRotationError(e instanceof Error ? e.message : 'Sector data unavailable');
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadRotation();
    api.get<BacktestReport[]>('/api/backtests').then(setBacktests).catch(() => {});
  }, [loadRotation]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">🌐 Market Context</h1>
        <p className="text-slate-400">
          Sector rotation and strategy backtests — both feed the Risk Modifiers
          scoring layer
        </p>
      </div>

      {/* Sector rotation */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-white">Sector Rotation</h2>
            {rotation && (
              <p className="text-slate-400 text-sm">
                vs SPY ({pct(rotation.benchmark.return_1m_pct)} 1m,{' '}
                {pct(rotation.benchmark.return_3m_pct)} 3m) · updated{' '}
                {rotation.generated?.slice(0, 16).replace('T', ' ')}
              </p>
            )}
          </div>
          <button onClick={() => loadRotation(true)} disabled={refreshing}
                  className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors">
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>

        {rotationError && (
          <p className="text-amber-300 text-sm mb-2">
            {rotationError} — run <code>python cli.py --sectors</code> or press Refresh.
          </p>
        )}

        {rotation && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 pr-3">#</th>
                  <th className="text-left py-2 pr-4">Sector</th>
                  <th className="text-left py-2 px-3">ETF</th>
                  <th className="text-right py-2 px-3">1m</th>
                  <th className="text-right py-2 px-3">3m</th>
                  <th className="text-right py-2 px-3">6m</th>
                  <th className="text-right py-2 px-3">RS 1m</th>
                  <th className="text-right py-2 px-3">RS 3m</th>
                  <th className="text-left py-2 pl-4">Phase</th>
                </tr>
              </thead>
              <tbody>
                {rotation.sectors.map((s) => (
                  <tr key={s.etf} className="border-b border-slate-700/50 text-slate-200">
                    <td className="py-2.5 pr-3 text-slate-500">{s.momentum_rank}</td>
                    <td className="pr-4 font-medium">{s.sector}</td>
                    <td className="px-3 text-slate-400">{s.etf}</td>
                    <td className={`text-right px-3 ${pctColor(s.return_1m_pct)}`}>{pct(s.return_1m_pct)}</td>
                    <td className={`text-right px-3 ${pctColor(s.return_3m_pct)}`}>{pct(s.return_3m_pct)}</td>
                    <td className={`text-right px-3 ${pctColor(s.return_6m_pct)}`}>{pct(s.return_6m_pct)}</td>
                    <td className={`text-right px-3 ${pctColor(s.rel_strength_1m_pct)}`}>{pct(s.rel_strength_1m_pct)}</td>
                    <td className={`text-right px-3 ${pctColor(s.rel_strength_3m_pct)}`}>{pct(s.rel_strength_3m_pct)}</td>
                    <td className="pl-4">
                      <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${PHASE_STYLES[s.phase] ?? PHASE_STYLES.unknown}`}>
                        {s.phase}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Backtests */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-bold text-white mb-1">Backtest History</h2>
        <p className="text-slate-400 text-sm mb-4">
          Run <code>python cli.py --backtest</code> to validate the methodology, then{' '}
          <code>--optimize-weights</code> to learn better score weights.
        </p>
        {backtests.length === 0 ? (
          <p className="text-slate-400">No backtest reports yet.</p>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {backtests.map((b) => (
              <div key={b.file} className="bg-slate-900/60 border border-slate-700 rounded-lg p-4">
                <p className="text-slate-400 text-xs mb-3">
                  {b.generated?.slice(0, 16).replace('T', ' ')} · {b.file}
                </p>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-slate-500 text-xs">Trades</p>
                    <p className="text-white font-bold">{b.summary.total_trades ?? '—'}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">Win rate</p>
                    <p className="text-white font-bold">
                      {b.summary.win_rate_pct != null ? `${b.summary.win_rate_pct}%` : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">Avg return</p>
                    <p className={`font-bold ${pctColor(b.summary.avg_return_pct)}`}>
                      {pct(b.summary.avg_return_pct, 2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">vs SPY</p>
                    <p className={`font-bold ${pctColor(b.summary.avg_excess_return_pct)}`}>
                      {pct(b.summary.avg_excess_return_pct, 2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">Sharpe</p>
                    <p className="text-white font-bold">{b.summary.sharpe_ratio ?? '—'}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">Max DD</p>
                    <p className="text-white font-bold">
                      {b.summary.max_drawdown_pct != null ? `${b.summary.max_drawdown_pct}%` : '—'}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketPage;
