import React, { useState } from 'react';
import { 
  BookOpen, 
  Search, 
  Download, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Tag, 
  Filter
} from 'lucide-react';
import { Trade } from '../types';

interface JournalViewProps {
  trades: Trade[];
}

export const JournalView: React.FC<JournalViewProps> = ({ trades }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sideFilter, setSideFilter] = useState<'ALL' | 'LONG' | 'SHORT'>('ALL');
  const [outcomeFilter, setOutcomeFilter] = useState<'ALL' | 'WIN' | 'LOSS'>('ALL');

  const filteredTrades = trades.filter((t) => {
    const matchesSearch = 
      t.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.exit_reason.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.trade_id.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesSide = sideFilter === 'ALL' || t.side === sideFilter;
    const matchesOutcome = 
      outcomeFilter === 'ALL' || 
      (outcomeFilter === 'WIN' && t.net_pnl > 0) || 
      (outcomeFilter === 'LOSS' && t.net_pnl <= 0);

    return matchesSearch && matchesSide && matchesOutcome;
  });

  const totalClosed = trades.length;
  const winTrades = trades.filter((t) => t.net_pnl > 0);
  const winRate = totalClosed > 0 ? (winTrades.length / totalClosed) * 100 : 0;
  const totalNetPnl = trades.reduce((acc, t) => acc + (t.net_pnl || 0), 0);
  const totalFees = trades.reduce((acc, t) => acc + (t.fees || 0), 0);

  const handleExportCsv = () => {
    if (trades.length === 0) return;
    const headers = ['Trade ID,Symbol,Side,Entry,Exit,Qty,Gross PnL,Fees,Net PnL,Return %,Exit Reason,Opened At,Closed At'];
    const rows = trades.map((t) => 
      `"${t.trade_id}","${t.symbol}","${t.side}",${t.entry_price},${t.exit_price},${t.quantity},${t.gross_pnl},${t.fees},${t.net_pnl},${t.return_pct},"${t.exit_reason}","${t.opened_at}","${t.closed_at}"`
    );
    const blob = new Blob([[...headers, ...rows].join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades_export_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-400" />
            <span>TRADE JOURNAL & AUDIT TRAIL</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Full audit history of paper and live trade executions with fill slippage, commission deductions, and exit reasons.
          </p>
        </div>

        <button
          onClick={handleExportCsv}
          disabled={trades.length === 0}
          className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-mono font-semibold flex items-center gap-2 transition-colors disabled:opacity-40"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export CSV</span>
        </button>
      </div>

      {/* Analytics KPI Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-[10px] font-mono text-slate-500 uppercase">CLOSED TRADES</span>
          <p className="text-xl font-black text-slate-100 font-mono mt-1">{totalClosed}</p>
          <span className="text-xs text-slate-500 font-mono">{winTrades.length} Wins / {totalClosed - winTrades.length} Losses</span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-[10px] font-mono text-slate-500 uppercase">WIN RATE</span>
          <p className="text-xl font-black text-emerald-400 font-mono mt-1">{winRate.toFixed(1)}%</p>
          <span className="text-xs text-slate-500 font-mono">Profit factor baseline</span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-[10px] font-mono text-slate-500 uppercase">TOTAL REALIZED P&L</span>
          <p className={`text-xl font-black font-mono mt-1 ${totalNetPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {totalNetPnl >= 0 ? '+' : ''}${totalNetPnl.toFixed(2)}
          </p>
          <span className="text-xs text-slate-500 font-mono">Net of exchange fees</span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-[10px] font-mono text-slate-500 uppercase">TOTAL COMMISSIONS</span>
          <p className="text-xl font-black text-amber-400 font-mono mt-1">${totalFees.toFixed(2)}</p>
          <span className="text-xs text-slate-500 font-mono">0.04% taker fee model</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by symbol, exit reason, or trade ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Side Filter */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
            {(['ALL', 'LONG', 'SHORT'] as const).map((side) => (
              <button
                key={side}
                onClick={() => setSideFilter(side)}
                className={`px-2.5 py-1 rounded ${sideFilter === side ? 'bg-slate-800 text-cyan-400 font-bold' : 'text-slate-400'}`}
              >
                {side}
              </button>
            ))}
          </div>

          {/* Outcome Filter */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
            {(['ALL', 'WIN', 'LOSS'] as const).map((outcome) => (
              <button
                key={outcome}
                onClick={() => setOutcomeFilter(outcome)}
                className={`px-2.5 py-1 rounded ${outcomeFilter === outcome ? 'bg-slate-800 text-cyan-400 font-bold' : 'text-slate-400'}`}
              >
                {outcome}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Trades Ledger Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
        {filteredTrades.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500 font-mono">
            No trades match the current filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-2 font-medium">TRADE ID</th>
                  <th className="pb-2 font-medium">SYMBOL</th>
                  <th className="pb-2 font-medium">SIDE</th>
                  <th className="pb-2 font-medium">ENTRY</th>
                  <th className="pb-2 font-medium">EXIT</th>
                  <th className="pb-2 font-medium">QTY</th>
                  <th className="pb-2 font-medium">FEES</th>
                  <th className="pb-2 font-medium">NET P&L</th>
                  <th className="pb-2 font-medium">EXIT REASON</th>
                  <th className="pb-2 font-medium">TIMESTAMP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredTrades.map((t) => {
                  const isProfit = t.net_pnl > 0;
                  return (
                    <tr key={t.trade_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 text-slate-500 font-mono">{t.trade_id.slice(-8)}</td>
                      <td className="py-3 font-bold text-slate-100">{t.symbol}</td>
                      <td className="py-3">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          t.side === 'LONG' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'
                        }`}>
                          {t.side}
                        </span>
                      </td>
                      <td className="py-3 text-slate-300">${t.entry_price.toFixed(2)}</td>
                      <td className="py-3 text-slate-300">${t.exit_price.toFixed(2)}</td>
                      <td className="py-3 text-slate-400">{t.quantity.toFixed(4)}</td>
                      <td className="py-3 text-slate-400">${t.fees.toFixed(2)}</td>
                      <td className={`py-3 font-bold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isProfit ? '+' : ''}${t.net_pnl.toFixed(2)} ({t.return_pct.toFixed(2)}%)
                      </td>
                      <td className="py-3 text-slate-400 text-[11px]">{t.exit_reason}</td>
                      <td className="py-3 text-slate-500 text-[10px]">{t.closed_at}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
