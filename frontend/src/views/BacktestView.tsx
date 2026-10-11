import React, { useState } from 'react';
import { 
  History, 
  Play, 
  Loader2, 
  TrendingUp, 
  TrendingDown, 
  ShieldAlert, 
  Activity,
  ArrowUpRight
} from 'lucide-react';
import { BacktestResult } from '../types';
import { api } from '../services/api';

export const BacktestView: React.FC = () => {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [initialBalance, setInitialBalance] = useState(10000);
  const [slPct, setSlPct] = useState(1.5);
  const [tpPct, setTpPct] = useState(3.0);
  const [riskPerTrade, setRiskPerTrade] = useState(1.0);
  const [useMlModel, setUseMlModel] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.runBacktest({
        symbol,
        timeframe,
        initial_balance: Number(initialBalance),
        sl_pct: Number(slPct),
        tp_pct: Number(tpPct),
        risk_per_trade: Number(riskPerTrade),
        use_ml_model: useMlModel
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Backtest execution failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <History className="w-5 h-5 text-cyan-400" />
          <span>OUT-OF-SAMPLE BACKTESTING ENGINE</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Simulate realistic historical performance using time-aligned out-of-sample predictions, 0.05% slippage, and 0.04% maker/taker exchange fee models.
        </p>
      </div>

      {/* Config Form */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
        <form onSubmit={handleRunBacktest} className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-7 gap-4 items-end font-mono text-xs">
          <div>
            <label className="block text-slate-400 mb-1">SYMBOL</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            >
              <option value="BTCUSDT">BTCUSDT</option>
              <option value="ETHUSDT">ETHUSDT</option>
              <option value="BNBUSDT">BNBUSDT</option>
              <option value="SOLUSDT">SOLUSDT</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">TIMEFRAME</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            >
              <option value="1h">1h (Hourly)</option>
              <option value="5m">5m (Micro)</option>
              <option value="4h">4h (Macro)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1">START CAPITAL ($)</label>
            <input
              type="number"
              value={initialBalance}
              onChange={(e) => setInitialBalance(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            />
          </div>

          <div>
            <label className="block text-slate-400 mb-1">STOP LOSS (%)</label>
            <input
              type="number"
              step="0.1"
              value={slPct}
              onChange={(e) => setSlPct(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            />
          </div>

          <div>
            <label className="block text-slate-400 mb-1">TAKE PROFIT (%)</label>
            <input
              type="number"
              step="0.1"
              value={tpPct}
              onChange={(e) => setTpPct(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            />
          </div>

          <div>
            <label className="block text-slate-400 mb-1">STRATEGY</label>
            <select
              value={useMlModel ? 'ml' : 'rule'}
              onChange={(e) => setUseMlModel(e.target.value === 'ml')}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            >
              <option value="ml">AI Model Signals</option>
              <option value="rule">Rule Baseline</option>
            </select>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-bold flex items-center justify-center gap-1.5 shadow-md shadow-cyan-900/30 transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>SIMULATING...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>RUN TEST</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-xs font-mono text-rose-300">
          Backtest Error: {error}
        </div>
      )}

      {/* Results Display */}
      {result && (
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <span className="text-[10px] font-mono text-slate-500 uppercase">FINAL BALANCE</span>
              <p className="text-xl font-black text-slate-100 font-mono mt-1">
                ${result.final_balance.toFixed(2)}
              </p>
              <span className={`text-xs font-mono font-bold flex items-center gap-0.5 mt-0.5 ${
                result.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {result.net_pnl >= 0 ? '+' : ''}${result.net_pnl.toFixed(2)} ({result.return_pct.toFixed(2)}%)
              </span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <span className="text-[10px] font-mono text-slate-500 uppercase">SHARPE RATIO</span>
              <p className="text-xl font-black text-cyan-400 font-mono mt-1">
                {result.metrics.sharpe_ratio.toFixed(2)}
              </p>
              <span className="text-[10px] text-slate-500 font-mono">Annualized metric</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <span className="text-[10px] font-mono text-slate-500 uppercase">MAX DRAWDOWN</span>
              <p className="text-xl font-black text-rose-400 font-mono mt-1">
                {result.metrics.max_drawdown.toFixed(2)}%
              </p>
              <span className="text-[10px] text-slate-500 font-mono">Peak to trough</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <span className="text-[10px] font-mono text-slate-500 uppercase">WIN RATE</span>
              <p className="text-xl font-black text-emerald-400 font-mono mt-1">
                {result.metrics.win_rate.toFixed(1)}%
              </p>
              <span className="text-[10px] text-slate-500 font-mono">{result.metrics.wins}W / {result.metrics.losses}L</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <span className="text-[10px] font-mono text-slate-500 uppercase">PROFIT FACTOR</span>
              <p className="text-xl font-black text-indigo-400 font-mono mt-1">
                {result.metrics.profit_factor.toFixed(2)}
              </p>
              <span className="text-[10px] text-slate-500 font-mono">Gross Gain / Loss</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
              <span className="text-[10px] font-mono text-slate-500 uppercase">TOTAL TRADES</span>
              <p className="text-xl font-black text-slate-200 font-mono mt-1">
                {result.metrics.total_trades}
              </p>
              <span className="text-[10px] text-slate-500 font-mono">Executed fills</span>
            </div>
          </div>

          {/* Cumulative Equity Curve Chart */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
            <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-3 flex items-center justify-between">
              <span>EQUITY CURVE SIMULATION</span>
              <span className="text-xs font-mono text-slate-400">Account Equity ($)</span>
            </h3>

            {result.equity_curve && result.equity_curve.length > 1 ? (
              <div className="relative h-64 w-full">
                {(() => {
                  const pts = result.equity_curve;
                  const minEq = Math.min(...pts.map((p) => p.equity)) * 0.98;
                  const maxEq = Math.max(...pts.map((p) => p.equity)) * 1.02;
                  const range = maxEq - minEq || 1;
                  const width = 800;
                  const height = 240;

                  const getX = (idx: number) => (idx / (pts.length - 1)) * (width - 60) + 10;
                  const getY = (val: number) => height - 30 - ((val - minEq) / range) * (height - 50);

                  const pathD = pts
                    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i).toFixed(1)} ${getY(p.equity).toFixed(1)}`)
                    .join(' ');

                  const areaD = `${pathD} L ${getX(pts.length - 1).toFixed(1)} ${height - 30} L ${getX(0).toFixed(1)} ${height - 30} Z`;

                  return (
                    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
                      {/* Grid Lines */}
                      {[minEq, (minEq + maxEq) / 2, maxEq].map((val, idx) => (
                        <g key={idx}>
                          <line x1="10" y1={getY(val)} x2={width - 50} y2={getY(val)} stroke="#1e293b" strokeDasharray="3 3" />
                          <text x={width - 45} y={getY(val) + 4} fill="#64748b" fontSize="10" fontFamily="JetBrains Mono">
                            ${val.toFixed(0)}
                          </text>
                        </g>
                      ))}

                      {/* Area Fill */}
                      <path d={areaD} fill="url(#equityGrad)" />
                      {/* Line */}
                      <path d={pathD} fill="none" stroke="#06b6d4" strokeWidth="2.5" />

                      <defs>
                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                    </svg>
                  );
                })()}
              </div>
            ) : (
              <div className="h-44 flex items-center justify-center text-xs text-slate-500 font-mono">
                No closed trades during this backtest window.
              </div>
            )}
          </div>

          {/* Trade-by-Trade Table */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
            <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-3">
              SIMULATED TRADE EXECUTION LOG
            </h3>

            {result.trades && result.trades.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2 font-medium">#</th>
                      <th className="pb-2 font-medium">SIDE</th>
                      <th className="pb-2 font-medium">ENTRY</th>
                      <th className="pb-2 font-medium">EXIT</th>
                      <th className="pb-2 font-medium">QTY</th>
                      <th className="pb-2 font-medium">FEES</th>
                      <th className="pb-2 font-medium">NET P&L</th>
                      <th className="pb-2 font-medium">EXIT REASON</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {result.trades.map((t, idx) => {
                      const isProfit = t.net_pnl >= 0;
                      return (
                        <tr key={idx} className="hover:bg-slate-800/40">
                          <td className="py-2.5 text-slate-500">{idx + 1}</td>
                          <td className="py-2.5">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              t.side === 'LONG' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'
                            }`}>
                              {t.side}
                            </span>
                          </td>
                          <td className="py-2.5 text-slate-300">${t.entry_price.toFixed(2)}</td>
                          <td className="py-2.5 text-slate-300">${t.exit_price.toFixed(2)}</td>
                          <td className="py-2.5 text-slate-400">{t.quantity.toFixed(4)}</td>
                          <td className="py-2.5 text-slate-400">${t.fees.toFixed(2)}</td>
                          <td className={`py-2.5 font-bold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isProfit ? '+' : ''}${t.net_pnl.toFixed(2)}
                          </td>
                          <td className="py-2.5 text-slate-400 text-[11px]">{t.exit_reason}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono py-4 text-center">No trades triggered.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
