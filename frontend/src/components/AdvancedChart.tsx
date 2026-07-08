import { useEffect, useState } from 'react';
import {
  ComposedChart, Line, Area, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';

interface ChartPoint {
  date: string;
  close: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  bbUpper: number | null;
  bbLower: number | null;
  rsi: number | null;
  macd: number | null;
  macdSignal: number | null;
  macdHist: number | null;
}

interface ChartPayload {
  ticker: string;
  points: ChartPoint[];
  meta: {
    bars: number;
    last_close: number | null;
    period_high: number | null;
    drop_from_period_high_pct: number | null;
  };
}

type OverlayKey = 'sma20' | 'sma50' | 'sma200' | 'bollinger';

const PERIODS = ['3mo', '6mo', '1y', '2y'] as const;

const OVERLAYS: { key: OverlayKey; label: string; color: string }[] = [
  { key: 'sma20', label: 'SMA 20', color: '#f59e0b' },
  { key: 'sma50', label: 'SMA 50', color: '#a855f7' },
  { key: 'sma200', label: 'SMA 200', color: '#ef4444' },
  { key: 'bollinger', label: 'Bollinger', color: '#38bdf8' },
];

const tooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #475569',
  borderRadius: '8px',
};

function AdvancedChart({ ticker }: { ticker: string }) {
  const [data, setData] = useState<ChartPayload | null>(null);
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>('6mo');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    sma20: true, sma50: true, sma200: false, bollinger: false,
  });
  const [showRsi, setShowRsi] = useState(true);
  const [showMacd, setShowMacd] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `http://localhost:5001/api/stock/${ticker}/chart?period=${period}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = await res.json();
        if (!cancelled) setData(payload);
      } catch (e) {
        if (!cancelled) setError('Chart data unavailable');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [ticker, period]);

  const toggleOverlay = (key: OverlayKey) =>
    setOverlays((prev) => ({ ...prev, [key]: !prev[key] }));

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 h-96 flex items-center justify-center">
        <span className="text-slate-400 animate-pulse">Loading advanced chart…</span>
      </div>
    );
  }

  if (error || !data || data.points.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <p className="text-slate-400">📉 {error ?? 'No chart data available'}</p>
      </div>
    );
  }

  const priceFormatter = (value: unknown, name: unknown): [string, string] => [
    typeof value === 'number' ? `$${value.toFixed(2)}` : '—',
    String(name ?? ''),
  ];

  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Advanced Chart</h2>
          <p className="text-slate-400 text-sm">
            {data.meta.bars} bars
            {data.meta.drop_from_period_high_pct != null &&
              ` · ${data.meta.drop_from_period_high_pct.toFixed(1)}% below period high`}
          </p>
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {OVERLAYS.map(({ key, label, color }) => (
          <button
            key={key}
            onClick={() => toggleOverlay(key)}
            className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
              overlays[key]
                ? 'border-transparent text-white'
                : 'border-slate-600 text-slate-400 hover:text-slate-200'
            }`}
            style={overlays[key] ? { backgroundColor: color } : undefined}
          >
            {label}
          </button>
        ))}
        <button
          onClick={() => setShowRsi((v) => !v)}
          className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
            showRsi ? 'bg-emerald-600 border-transparent text-white'
                    : 'border-slate-600 text-slate-400 hover:text-slate-200'
          }`}
        >
          RSI
        </button>
        <button
          onClick={() => setShowMacd((v) => !v)}
          className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
            showMacd ? 'bg-cyan-600 border-transparent text-white'
                     : 'border-slate-600 text-slate-400 hover:text-slate-200'
          }`}
        >
          MACD
        </button>
      </div>

      {/* Price panel */}
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data.points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
            <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} minTickGap={40} />
            <YAxis
              stroke="#94a3b8"
              fontSize={11}
              domain={['auto', 'auto']}
              tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={priceFormatter} />
            <Legend wrapperStyle={{ color: '#cbd5e1' }} />
            {overlays.bollinger && (
              <>
                <Area type="monotone" dataKey="bbUpper" name="BB Upper"
                      stroke="#38bdf8" strokeWidth={1} fill="none" dot={false}
                      strokeDasharray="3 3" connectNulls />
                <Area type="monotone" dataKey="bbLower" name="BB Lower"
                      stroke="#38bdf8" strokeWidth={1} fill="#38bdf8"
                      fillOpacity={0.06} dot={false} strokeDasharray="3 3" connectNulls />
              </>
            )}
            <Line type="monotone" dataKey="close" name="Close" stroke="#3b82f6"
                  strokeWidth={2} dot={false} connectNulls />
            {overlays.sma20 && (
              <Line type="monotone" dataKey="sma20" name="SMA 20" stroke="#f59e0b"
                    strokeWidth={1.5} dot={false} connectNulls />
            )}
            {overlays.sma50 && (
              <Line type="monotone" dataKey="sma50" name="SMA 50" stroke="#a855f7"
                    strokeWidth={1.5} dot={false} connectNulls />
            )}
            {overlays.sma200 && (
              <Line type="monotone" dataKey="sma200" name="SMA 200" stroke="#ef4444"
                    strokeWidth={1.5} dot={false} connectNulls />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* RSI panel */}
      {showRsi && (
        <div className="h-36 mt-4">
          <p className="text-slate-400 text-xs mb-1">RSI (14) — oversold &lt; 30, overbought &gt; 70</p>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.points}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} minTickGap={40} />
              <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={10} ticks={[0, 30, 50, 70, 100]} />
              <Tooltip contentStyle={tooltipStyle} />
              <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="4 4" />
              <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="rsi" name="RSI" stroke="#10b981"
                    strokeWidth={1.5} dot={false} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* MACD panel */}
      {showMacd && (
        <div className="h-36 mt-8">
          <p className="text-slate-400 text-xs mb-1">MACD (12/26/9)</p>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.points}>
              <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
              <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} minTickGap={40} />
              <YAxis stroke="#94a3b8" fontSize={10} />
              <Tooltip contentStyle={tooltipStyle} />
              <ReferenceLine y={0} stroke="#64748b" />
              <Bar dataKey="macdHist" name="Histogram" fill="#38bdf8" opacity={0.5} />
              <Line type="monotone" dataKey="macd" name="MACD" stroke="#06b6d4"
                    strokeWidth={1.5} dot={false} connectNulls />
              <Line type="monotone" dataKey="macdSignal" name="Signal" stroke="#f97316"
                    strokeWidth={1.5} dot={false} connectNulls />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default AdvancedChart;
