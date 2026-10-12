import React, { useState, useEffect, useMemo } from 'react';
import { TickerData } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  Search, 
  Star, 
  ArrowUpDown, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Clock, 
  BarChart2, 
  CheckCircle2, 
  AlertTriangle,
  ExternalLink,
  Flame,
  LayoutGrid,
  Table as TableIcon
} from 'lucide-react';

interface TerminalViewProps {
  tickers: Record<string, TickerData>;
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  onOpenDetail?: (symbol: string) => void;
  wsConnected: boolean;
}

export const TerminalView: React.FC<TerminalViewProps> = ({
  tickers,
  selectedSymbol,
  onSelectSymbol,
  onOpenDetail,
  wsConnected
}) => {
  const { isAuthenticated } = useAuth();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'favorites' | 'gainers' | 'losers' | 'volume'>('all');
  const [sortField, setSortField] = useState<'symbol' | 'price' | 'change_24h' | 'quote_volume_24h' | 'funding_rate'>('quote_volume_24h');
  const [sortAsc, setSortAsc] = useState(false);
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [isWatchlistLoading, setIsWatchlistLoading] = useState(false);

  // Load user watchlist
  useEffect(() => {
    if (isAuthenticated) {
      api.getWatchlist().then(setWatchlist).catch(() => {});
    } else {
      const local = localStorage.getItem('guest_watchlist');
      if (local) {
        try { setWatchlist(JSON.parse(local)); } catch (e) {}
      }
    }
  }, [isAuthenticated]);

  const toggleFavorite = async (sym: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const isFav = watchlist.includes(sym);
    if (isAuthenticated) {
      setIsWatchlistLoading(true);
      try {
        if (isFav) {
          const updated = await api.removeFromWatchlist(sym);
          setWatchlist(updated);
        } else {
          const updated = await api.addToWatchlist(sym);
          setWatchlist(updated);
        }
      } catch (err) {
        console.error('Failed to update watchlist:', err);
      } finally {
        setIsWatchlistLoading(false);
      }
    } else {
      const updated = isFav ? watchlist.filter((s) => s !== sym) : [...watchlist, sym];
      setWatchlist(updated);
      localStorage.setItem('guest_watchlist', JSON.stringify(updated));
    }
  };

  // Convert tickers dict to array
  const tickerList = useMemo(() => {
    return Object.entries(tickers).map(([sym, t]) => ({
      symbol: sym,
      market_type: t.market_type || 'Spot (Kraken Public)',
      price: t.price || 0,
      change_24h: t.change_24h || 0,
      change_24h_abs: t.change_24h_abs || 0,
      high_24h: t.high_24h || t.price || 0,
      low_24h: t.low_24h || t.price || 0,
      volume_24h: t.volume_24h || 0,
      quote_volume_24h: t.quote_volume_24h || 0,
      mark_price: t.mark_price || t.price || 0,
      funding_rate: t.funding_rate || 0,
      bid_price: t.bid_price || t.price || 0,
      ask_price: t.ask_price || t.price || 0,
      spread: t.spread || 0,
      timestamp: t.timestamp || new Date().toISOString(),
      is_stale: t.is_stale || false
    }));
  }, [tickers]);

  // Filter & Search
  const filteredTickers = useMemo(() => {
    return tickerList.filter((item) => {
      const matchesSearch = item.symbol.toLowerCase().includes(search.toLowerCase().trim());
      if (!matchesSearch) return false;

      if (filter === 'favorites') return watchlist.includes(item.symbol);
      if (filter === 'gainers') return item.change_24h > 0;
      if (filter === 'losers') return item.change_24h < 0;
      if (filter === 'volume') return (item.quote_volume_24h || item.volume_24h) > 50000000;
      return true;
    });
  }, [tickerList, search, filter, watchlist]);

  // Sort
  const sortedTickers = useMemo(() => {
    return [...filteredTickers].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === 'symbol') {
        return sortAsc ? a.symbol.localeCompare(b.symbol) : b.symbol.localeCompare(a.symbol);
      }

      valA = Number(valA) || 0;
      valB = Number(valB) || 0;
      return sortAsc ? valA - valB : valB - valA;
    });
  }, [filteredTickers, sortField, sortAsc]);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const lastUpdated = tickerList.length > 0 ? tickerList[0].timestamp : null;

  return (
    <div className="space-y-6">
      {/* Real-time Status Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-xl shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">Market Venue</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="font-bold text-slate-100 text-sm">Kraken Public Market Data</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60 font-mono font-semibold">
                Live Feed
              </span>
            </div>
          </div>

          <div className="h-8 w-px bg-slate-800 hidden sm:block" />

          <div>
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">Active Symbols</span>
            <span className="font-extrabold text-slate-100 font-mono text-sm mt-0.5 block">
              {tickerList.length} Instruments Subscribed
            </span>
          </div>

          <div className="h-8 w-px bg-slate-800 hidden sm:block" />

          <div>
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block">Connectivity</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`inline-block w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-md shadow-emerald-950' : 'bg-rose-500'}`} />
              <span className="text-xs font-mono font-medium text-slate-200">
                {wsConnected ? 'WebSocket Feed Online' : 'Reconnecting...'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-1.5 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : 'Syncing...'}</span>
          </div>
          <div className="flex items-center gap-1.5 bg-emerald-950/40 text-emerald-300 border border-emerald-800/40 px-3 py-1.5 rounded-lg">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Real Exchange Feeds</span>
          </div>
        </div>
      </div>

      {/* Controls Bar: Search, Category Filters, View Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search coin (e.g. BTC, SOL, ARB)..."
            className="w-full pl-9 pr-4 py-2 bg-slate-950/90 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'all'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40'
                : 'text-slate-400 hover:text-slate-200 bg-slate-950/60 hover:bg-slate-800 border border-slate-800'
            }`}
          >
            All ({tickerList.length})
          </button>
          <button
            onClick={() => setFilter('favorites')}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'favorites'
                ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-950/40'
                : 'text-slate-400 hover:text-amber-400 bg-slate-950/60 hover:bg-slate-800 border border-slate-800'
            }`}
          >
            <Star className="w-3.5 h-3.5 fill-current" />
            <span>Watchlist ({watchlist.length})</span>
          </button>
          <button
            onClick={() => setFilter('gainers')}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'gainers'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/40'
                : 'text-slate-400 hover:text-emerald-400 bg-slate-950/60 hover:bg-slate-800 border border-slate-800'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Gainers</span>
          </button>
          <button
            onClick={() => setFilter('losers')}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'losers'
                ? 'bg-rose-600 text-white shadow-md shadow-rose-900/40'
                : 'text-slate-400 hover:text-rose-400 bg-slate-950/60 hover:bg-slate-800 border border-slate-800'
            }`}
          >
            <TrendingDown className="w-3.5 h-3.5" />
            <span>Losers</span>
          </button>
          <button
            onClick={() => setFilter('volume')}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filter === 'volume'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/40'
                : 'text-slate-400 hover:text-indigo-400 bg-slate-950/60 hover:bg-slate-800 border border-slate-800'
            }`}
          >
            <Flame className="w-3.5 h-3.5" />
            <span>High Volume</span>
          </button>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setViewMode('table')}
            title="Table View"
            className={`p-1.5 rounded-md text-xs transition-colors ${viewMode === 'table' ? 'bg-slate-800 text-cyan-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <TableIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('grid')}
            title="Cards View"
            className={`p-1.5 rounded-md text-xs transition-colors ${viewMode === 'grid' ? 'bg-slate-800 text-cyan-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Terminal View: Table or Grid */}
      {sortedTickers.length === 0 ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-12 text-center text-slate-500">
          <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-slate-600" />
          <p className="text-sm font-semibold text-slate-400">No trading pairs match your active search or filter.</p>
          <p className="text-xs mt-1 text-slate-600">Try resetting filters or search query.</p>
        </div>
      ) : viewMode === 'table' ? (
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-md shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                  <th className="py-3 px-4 w-12 text-center">Fav</th>
                  <th className="py-3 px-4 cursor-pointer hover:text-slate-200" onClick={() => handleSort('symbol')}>
                    <div className="flex items-center gap-1.5">
                      <span>Symbol</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('price')}>
                    <div className="flex items-center justify-end gap-1.5">
                      <span>Last Price</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('change_24h')}>
                    <div className="flex items-center justify-end gap-1.5">
                      <span>24h Change</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">24h High / Low</th>
                  <th className="py-3 px-4 text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('quote_volume_24h')}>
                    <div className="flex items-center justify-end gap-1.5">
                      <span>24h Volume (USDT)</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">Mark Price</th>
                  <th className="py-3 px-4 text-right cursor-pointer hover:text-slate-200" onClick={() => handleSort('funding_rate')}>
                    <div className="flex items-center justify-end gap-1.5">
                      <span>Funding Rate</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">Spread</th>
                  <th className="py-3 px-4 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {sortedTickers.map((t) => {
                  const isUp = t.change_24h >= 0;
                  const isFav = watchlist.includes(t.symbol);
                  const isSelected = selectedSymbol === t.symbol;

                  return (
                    <tr
                      key={t.symbol}
                      onClick={() => onSelectSymbol(t.symbol)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-cyan-950/40 border-l-4 border-cyan-500'
                          : 'hover:bg-slate-800/40'
                      }`}
                    >
                      {/* Favorite Star */}
                      <td className="py-3.5 px-4 text-center">
                        <button
                          onClick={(e) => toggleFavorite(t.symbol, e)}
                          className={`p-1 rounded hover:scale-125 transition-transform ${
                            isFav ? 'text-amber-400' : 'text-slate-600 hover:text-slate-400'
                          }`}
                        >
                          <Star className={`w-4 h-4 ${isFav ? 'fill-current' : ''}`} />
                        </button>
                      </td>

                      {/* Symbol & Market Type */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-extrabold text-slate-100 text-sm tracking-tight">{t.symbol}</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800/90 text-cyan-400 font-sans border border-slate-700">
                            {t.market_type}
                          </span>
                        </div>
                      </td>

                      {/* Last Price */}
                      <td className="py-3.5 px-4 text-right font-bold text-slate-100 text-sm">
                        ${t.price > 10 ? t.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : t.price.toFixed(4)}
                      </td>

                      {/* 24h Change */}
                      <td className="py-3.5 px-4 text-right">
                        <div className={`inline-flex items-center gap-1 font-bold px-2 py-0.5 rounded ${
                          isUp ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-800/40' : 'text-rose-400 bg-rose-950/40 border border-rose-800/40'
                        }`}>
                          {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                          <span>{isUp ? '+' : ''}{t.change_24h.toFixed(2)}%</span>
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {isUp ? '+' : ''}${t.change_24h_abs.toFixed(2)}
                        </div>
                      </td>

                      {/* 24h High / Low */}
                      <td className="py-3.5 px-4 text-right text-[11px]">
                        <div className="text-emerald-400">H: ${t.high_24h.toLocaleString()}</div>
                        <div className="text-rose-400">L: ${t.low_24h.toLocaleString()}</div>
                      </td>

                      {/* 24h Volume */}
                      <td className="py-3.5 px-4 text-right font-medium text-slate-300">
                        ${(t.quote_volume_24h / 1_000_000).toLocaleString('en-US', { maximumFractionDigits: 1 })}M
                      </td>

                      {/* Mark Price */}
                      <td className="py-3.5 px-4 text-right text-slate-300">
                        ${t.mark_price > 10 ? t.mark_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : t.mark_price.toFixed(4)}
                      </td>

                      {/* Funding Rate */}
                      <td className="py-3.5 px-4 text-right">
                        <span className={`px-1.5 py-0.5 rounded text-[11px] font-medium ${
                          t.funding_rate >= 0 ? 'text-cyan-400 bg-cyan-950/50' : 'text-amber-400 bg-amber-950/50'
                        }`}>
                          {t.funding_rate >= 0 ? '+' : ''}{t.funding_rate.toFixed(4)}%
                        </span>
                      </td>

                      {/* Spread */}
                      <td className="py-3.5 px-4 text-right text-slate-400 text-[11px]">
                        ${t.spread.toFixed(2)}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectSymbol(t.symbol);
                            if (onOpenDetail) onOpenDetail(t.symbol);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-cyan-700 hover:text-white text-slate-300 text-[11px] transition-colors border border-slate-700 inline-flex items-center gap-1"
                        >
                          <span>Chart</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Grid Cards View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {sortedTickers.map((t) => {
            const isUp = t.change_24h >= 0;
            const isFav = watchlist.includes(t.symbol);
            const isSelected = selectedSymbol === t.symbol;

            return (
              <div
                key={t.symbol}
                onClick={() => onSelectSymbol(t.symbol)}
                className={`p-4 rounded-xl border backdrop-blur-md cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-slate-900 border-cyan-500 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-500'
                    : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-slate-100 text-base tracking-tight">{t.symbol}</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-cyan-400 font-mono">
                      Perp
                    </span>
                  </div>
                  <button
                    onClick={(e) => toggleFavorite(t.symbol, e)}
                    className={`p-1 rounded hover:scale-125 transition-transform ${
                      isFav ? 'text-amber-400' : 'text-slate-600 hover:text-slate-400'
                    }`}
                  >
                    <Star className={`w-4 h-4 ${isFav ? 'fill-current' : ''}`} />
                  </button>
                </div>

                <div className="flex items-baseline justify-between mb-3">
                  <div className="font-mono text-xl font-black text-slate-100">
                    ${t.price > 10 ? t.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : t.price.toFixed(4)}
                  </div>
                  <div className={`font-mono font-bold text-xs px-2 py-0.5 rounded flex items-center gap-1 ${
                    isUp ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-800/40' : 'text-rose-400 bg-rose-950/40 border border-rose-800/40'
                  }`}>
                    {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    <span>{isUp ? '+' : ''}{t.change_24h.toFixed(2)}%</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono pt-3 border-t border-slate-800/80 text-slate-400">
                  <div>
                    <span className="text-slate-500 block text-[9px] uppercase">24h Volume</span>
                    <span className="text-slate-200 font-medium">
                      ${(t.quote_volume_24h / 1_000_000).toFixed(1)}M
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-slate-500 block text-[9px] uppercase">Funding (8h)</span>
                    <span className={t.funding_rate >= 0 ? 'text-cyan-400' : 'text-amber-400'}>
                      {t.funding_rate >= 0 ? '+' : ''}{t.funding_rate.toFixed(4)}%
                    </span>
                  </div>
                </div>

                <div className="mt-3 pt-2 flex items-center justify-between text-[10px] font-mono text-slate-500">
                  <span>Mark: ${t.mark_price.toFixed(2)}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectSymbol(t.symbol);
                      if (onOpenDetail) onOpenDetail(t.symbol);
                    }}
                    className="text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
                  >
                    <span>View Detail</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
