import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  ShieldCheck, 
  AlertTriangle, 
  Activity, 
  ArrowUpRight, 
  ArrowDownRight,
  RefreshCw,
  XCircle
} from 'lucide-react';
import { Position, Prediction, RiskStatus, Trade, TickerData } from '../types';

interface OverviewViewProps {
  cash: number;
  equity: number;
  unrealizedPnl: number;
  positions: Position[];
  predictions: Prediction[];
  riskStatus: RiskStatus | null;
  trades: Trade[];
  tickers: Record<string, TickerData>;
  onClosePosition: (symbol: string) => void;
  onRefresh: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  cash,
  equity,
  unrealizedPnl,
  positions,
  predictions,
  riskStatus,
  trades,
  tickers,
  onClosePosition,
  onRefresh
}) => {
  const latestPrediction = predictions[0] || null;

  // Realized PnL from trades
  const realizedPnl = trades.reduce((acc, t) => acc + (t.net_pnl || 0), 0);
  const totalReturnPct = equity > 0 ? ((realizedPnl + unrealizedPnl) / (equity - realizedPnl - unrealizedPnl || 10000)) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner / Ticker Strip with Real Live Exchange Data */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {(Object.keys(tickers).length >= 4 ? Object.keys(tickers).slice(0, 4) : ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']).map((sym) => {
          const pred = predictions.find((p) => p.symbol === sym);
          const t = tickers[sym];
          const price = t?.price;
          const change = t?.change_24h ?? 0;
          const isUp = change >= 0;

          return (
            <div key={sym} className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 backdrop-blur-sm shadow-md">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-slate-200">{sym}</span>
                <span className={`text-[11px] font-mono font-bold flex items-center ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isUp ? '+' : ''}{change.toFixed(2)}%
                </span>
              </div>

              <div className="mt-1 flex items-baseline justify-between">
                <span className="text-base font-black font-mono text-slate-100">
                  {price ? `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '--'}
                </span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  pred?.direction === 'LONG' 
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' 
                    : pred?.direction === 'SHORT'
                    ? 'bg-rose-950 text-rose-400 border border-rose-800/50'
                    : 'bg-slate-800 text-slate-400'
                }`}>
                  {pred?.direction || 'NEUTRAL'}
                </span>
              </div>

              <div className="mt-1 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                <span>Vol: {t?.volume_24h ? t.volume_24h.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '--'}</span>
                <span className="uppercase text-slate-400 font-semibold">{pred?.regime || 'LIVE'}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Equity */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Paper Account Equity</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">
              SIMULATED
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-100 font-mono">
              ${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className={totalReturnPct >= 0 ? 'text-emerald-400 flex items-center font-semibold' : 'text-rose-400 flex items-center font-semibold'}>
              {totalReturnPct >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
              {totalReturnPct.toFixed(2)}%
            </span>
            <span className="text-[11px] text-slate-500 font-mono">Base: $10,000 Sandbox</span>
          </div>
        </div>

        {/* Available Cash */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Available Cash</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2">
            <span className="text-2xl font-black text-slate-100 font-mono">
              ${cash.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-500 font-mono">
            {positions.length} active position{positions.length === 1 ? '' : 's'}
          </div>
        </div>

        {/* Unrealized PnL */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Unrealized P&L</span>
            {unrealizedPnl >= 0 ? <TrendingUp className="w-4 h-4 text-emerald-400" /> : <TrendingDown className="w-4 h-4 text-rose-400" />}
          </div>
          <div className="mt-2">
            <span className={`text-2xl font-black font-mono ${unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {unrealizedPnl >= 0 ? '+' : ''}${unrealizedPnl.toFixed(2)}
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-500 font-mono">
            Mark-to-market live valuation
          </div>
        </div>

        {/* Realized PnL */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Realized P&L</span>
            <ShieldCheck className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2">
            <span className={`text-2xl font-black font-mono ${realizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {realizedPnl >= 0 ? '+' : ''}${realizedPnl.toFixed(2)}
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-500 font-mono">
            Across {trades.length} closed trades
          </div>
        </div>
      </div>

      {/* Main Grid: Active Positions & Latest ML Signal */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Positions Table (2 Columns) */}
        <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-100 text-sm tracking-wide">ACTIVE POSITIONS</h3>
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-slate-800 text-slate-300">
                {positions.length}
              </span>
            </div>
            <button 
              onClick={onRefresh}
              className="text-slate-400 hover:text-slate-200 text-xs flex items-center gap-1 font-mono transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>

          {positions.length === 0 ? (
            <div className="h-44 flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500">
              <Activity className="w-8 h-8 stroke-1 text-slate-600 mb-2" />
              <p className="text-sm font-medium">No open positions</p>
              <p className="text-xs text-slate-500 mt-1">Multi-timeframe engine is actively scanning market signals</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="pb-2 font-medium">SYMBOL</th>
                    <th className="pb-2 font-medium">SIDE</th>
                    <th className="pb-2 font-medium">ENTRY</th>
                    <th className="pb-2 font-medium">MARK</th>
                    <th className="pb-2 font-medium">SIZE</th>
                    <th className="pb-2 font-medium">SL / TP</th>
                    <th className="pb-2 font-medium text-right">UNREALIZED PnL</th>
                    <th className="pb-2 font-medium text-center">ACTION</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {positions.map((pos) => {
                    const isLong = pos.side === 'LONG';
                    const pnlPositive = pos.unrealized_pnl >= 0;
                    return (
                      <tr key={pos.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3 font-bold text-slate-100">{pos.symbol}</td>
                        <td className="py-3">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            isLong ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'
                          }`}>
                            {pos.side} {pos.leverage}x
                          </span>
                        </td>
                        <td className="py-3 text-slate-300">${pos.entry_price.toFixed(2)}</td>
                        <td className="py-3 text-slate-300">${pos.current_price.toFixed(2)}</td>
                        <td className="py-3 text-slate-400">{pos.quantity.toFixed(4)}</td>
                        <td className="py-3 text-slate-400">
                          <span className="text-rose-400">${pos.stop_loss.toFixed(1)}</span> / <span className="text-emerald-400">${pos.take_profit.toFixed(1)}</span>
                        </td>
                        <td className={`py-3 text-right font-bold ${pnlPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {pnlPositive ? '+' : ''}${pos.unrealized_pnl.toFixed(2)} ({pos.return_pct.toFixed(2)}%)
                        </td>
                        <td className="py-3 text-center">
                          <button
                            onClick={() => onClosePosition(pos.symbol)}
                            className="p-1 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 rounded transition-colors"
                            title="Market Close Position"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Latest ML Signal & Risk Status (1 Column) */}
        <div className="space-y-6">
          {/* Signal Card */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
            <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-3 flex items-center justify-between">
              <span>LATEST ML PREDICTION</span>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                1-HOUR MODEL
              </span>
            </h3>

            {latestPrediction ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <div>
                    <span className="text-xs text-slate-400 font-mono">{latestPrediction.symbol}</span>
                    <p className={`text-xl font-black ${
                      latestPrediction.direction === 'LONG' ? 'text-emerald-400' : latestPrediction.direction === 'SHORT' ? 'text-rose-400' : 'text-slate-400'
                    }`}>
                      {latestPrediction.direction}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Confidence</span>
                    <p className="text-lg font-mono font-bold text-slate-200">
                      {(latestPrediction.confidence * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Probability Distribution */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[11px] font-mono text-slate-400">
                    <span>Calibrated Probabilities</span>
                    <span>Edge: {(latestPrediction.edge * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-3 rounded-full bg-slate-800 flex overflow-hidden">
                    <div 
                      style={{ width: `${latestPrediction.probabilities.BUY * 100}%` }}
                      className="bg-emerald-500 h-full transition-all duration-300"
                      title={`BUY: ${(latestPrediction.probabilities.BUY * 100).toFixed(1)}%`}
                    />
                    <div 
                      style={{ width: `${latestPrediction.probabilities.NEUTRAL * 100}%` }}
                      className="bg-slate-600 h-full transition-all duration-300"
                      title={`NEUTRAL: ${(latestPrediction.probabilities.NEUTRAL * 100).toFixed(1)}%`}
                    />
                    <div 
                      style={{ width: `${latestPrediction.probabilities.SELL * 100}%` }}
                      className="bg-rose-500 h-full transition-all duration-300"
                      title={`SELL: ${(latestPrediction.probabilities.SELL * 100).toFixed(1)}%`}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] font-mono text-slate-500">
                    <span className="text-emerald-400">BUY {(latestPrediction.probabilities.BUY * 100).toFixed(0)}%</span>
                    <span>NEU {(latestPrediction.probabilities.NEUTRAL * 100).toFixed(0)}%</span>
                    <span className="text-rose-400">SELL {(latestPrediction.probabilities.SELL * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {latestPrediction.abstention_reason && (
                  <div className="p-2.5 rounded bg-amber-950/30 border border-amber-900/50 text-[11px] font-mono text-amber-300 flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>Filter: {latestPrediction.abstention_reason}</span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono py-6 text-center">Awaiting initial model inference...</p>
            )}
          </div>

          {/* Institutional Risk Budget Card */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
            <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-3 flex items-center justify-between">
              <span>RISK CIRCUIT BREAKERS</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </h3>

            <div className="space-y-3 font-mono text-xs">
              {/* Daily Loss */}
              <div>
                <div className="flex justify-between text-slate-400 mb-1">
                  <span>Daily Loss (Max {riskStatus?.max_daily_loss_pct || 2.0}%)</span>
                  <span className={(riskStatus?.daily_loss_pct || 0) > 1.5 ? 'text-rose-400 font-bold' : 'text-slate-200'}>
                    {(riskStatus?.daily_loss_pct || 0).toFixed(2)}%
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${(riskStatus?.daily_loss_pct || 0) > 1.5 ? 'bg-rose-500' : 'bg-cyan-500'}`} 
                    style={{ width: `${Math.min(100, ((riskStatus?.daily_loss_pct || 0) / (riskStatus?.max_daily_loss_pct || 2.0)) * 100)}%` }}
                  />
                </div>
              </div>

              {/* Drawdown */}
              <div>
                <div className="flex justify-between text-slate-400 mb-1">
                  <span>Trailing DD (Max {riskStatus?.max_drawdown_pct || 10.0}%)</span>
                  <span className={(riskStatus?.drawdown_pct || 0) > 7.0 ? 'text-rose-400 font-bold' : 'text-slate-200'}>
                    {(riskStatus?.drawdown_pct || 0).toFixed(2)}%
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${(riskStatus?.drawdown_pct || 0) > 7.0 ? 'bg-rose-500' : 'bg-indigo-500'}`} 
                    style={{ width: `${Math.min(100, ((riskStatus?.drawdown_pct || 0) / (riskStatus?.max_drawdown_pct || 10.0)) * 100)}%` }}
                  />
                </div>
              </div>

              {/* Consecutive Losses */}
              <div className="pt-1 flex items-center justify-between text-[11px] border-t border-slate-800/80">
                <span className="text-slate-400">Consecutive Losses:</span>
                <span className="font-bold text-slate-200">
                  {riskStatus?.consecutive_losses || 0} / {riskStatus?.max_consecutive_losses || 3}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
