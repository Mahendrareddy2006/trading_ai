import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Newspaper, 
  Search, 
  RefreshCw, 
  ExternalLink, 
  Clock, 
  TrendingUp, 
  TrendingDown, 
  Sparkles, 
  AlertCircle, 
  Globe,
  Tag,
  Filter,
  ArrowUpDown
} from 'lucide-react';
import { NewsArticle, TickerData } from '../types';
import { api } from '../services/api';

interface MarketNewsViewProps {
  tickers?: Record<string, TickerData>;
}

interface CategoryFilter {
  id: string;
  label: string;
}

const CATEGORIES: CategoryFilter[] = [
  { id: 'all', label: 'All News' },
  { id: 'bitcoin', label: 'Bitcoin' },
  { id: 'ethereum', label: 'Ethereum' },
  { id: 'altcoins', label: 'Altcoins' },
  { id: 'regulation', label: 'Regulation' },
  { id: 'macro', label: 'Macro & Economy' },
  { id: 'exchanges', label: 'Exchanges' },
  { id: 'defi', label: 'DeFi & Web3' },
];

export const MarketNewsView: React.FC<MarketNewsViewProps> = ({ tickers = {} }) => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Filters & Controls
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest');
  const [displayCount, setDisplayCount] = useState<number>(12);

  // Fetch news from backend service
  const fetchNews = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const data = await api.getNews({
        limit: 100, // Fetch full feed batch for fast, responsive client filtering & search
        refresh: isManualRefresh
      });
      setArticles(data.articles || []);
      setIsStale(data.is_stale);
      setLastUpdated(data.last_updated);
    } catch (err: any) {
      console.error('Failed to load market news:', err);
      setError(err?.message || 'Unable to connect to live crypto news feeds.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  // Extract unique publisher sources from live articles
  const availableSources = useMemo(() => {
    const set = new Set<string>();
    articles.forEach((a) => {
      if (a.source) set.add(a.source);
    });
    return Array.from(set).sort();
  }, [articles]);

  // Compute category article counts for tab badges
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: articles.length };
    for (const cat of CATEGORIES) {
      if (cat.id === 'all') continue;
      counts[cat.id] = articles.filter((a) => a.categories.includes(cat.id)).length;
    }
    return counts;
  }, [articles]);

  // Filtered & Sorted Articles
  const filteredArticles = useMemo(() => {
    let result = articles;

    // 1. Category filter
    if (selectedCategory !== 'all') {
      result = result.filter((a) => a.categories.includes(selectedCategory));
    }

    // 2. Source filter
    if (selectedSource !== 'all') {
      result = result.filter((a) => a.source.toLowerCase() === selectedSource.toLowerCase());
    }

    // 3. Search query across title and summary
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      result = result.filter(
        (a) =>
          a.title.toLowerCase().includes(query) ||
          (a.summary && a.summary.toLowerCase().includes(query))
      );
    }

    // 4. Sort order
    return [...result].sort((a, b) => {
      const timeA = new Date(a.published_at).getTime();
      const timeB = new Date(b.published_at).getTime();
      return sortOrder === 'newest' ? timeB - timeA : timeA - timeB;
    });
  }, [articles, selectedCategory, selectedSource, searchQuery, sortOrder]);

  const visibleArticles = useMemo(() => {
    return filteredArticles.slice(0, displayCount);
  }, [filteredArticles, displayCount]);

  // Format relative publication time
  const formatTimeAgo = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMinutes / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMinutes < 1) return 'Just now';
      if (diffMinutes < 60) return `${diffMinutes}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${diffDays}d ago`;
    } catch {
      return dateStr;
    }
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source.toLowerCase()) {
      case 'cointelegraph':
        return 'bg-amber-950/70 text-amber-300 border-amber-800/50';
      case 'coindesk':
        return 'bg-emerald-950/70 text-emerald-300 border-emerald-800/50';
      case 'decrypt':
        return 'bg-indigo-950/70 text-indigo-300 border-indigo-800/50';
      default:
        return 'bg-slate-800 text-cyan-300 border-slate-700';
    }
  };

  // Tickers to show in the compact market context strip
  const marketStripSymbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'];

  return (
    <div className="space-y-6">
      
      {/* Section A: Header & Refresh Summary */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 sm:p-6 backdrop-blur-xl shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-950/50 border border-white/10">
              <Newspaper className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-black text-slate-100 tracking-tight">
                  MARKET NEWS & INTELLIGENCE
                </h1>
                {isStale ? (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-300 border border-amber-800/60 font-bold">
                    CACHED
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 font-bold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    LIVE FEEDS
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Multi-source crypto newsfeed curated from Cointelegraph, CoinDesk & Decrypt
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <div className="hidden sm:flex flex-col text-right text-[11px] font-mono text-slate-400">
              <span className="text-slate-500">Last Synced</span>
              <span className="text-slate-300">{new Date(lastUpdated).toLocaleTimeString()}</span>
            </div>
          )}

          <button
            onClick={() => fetchNews(true)}
            disabled={refreshing || loading}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-cyan-300 border border-slate-700/80 hover:border-cyan-700/60 rounded-xl text-xs font-semibold transition-all shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span>{refreshing ? 'Fetching...' : 'Sync News'}</span>
          </button>
        </div>
      </div>

      {/* Section D: Compact Market Context Strip */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3 backdrop-blur-sm shadow-md overflow-x-auto">
        <div className="flex items-center gap-4 min-w-max text-xs font-mono">
          <div className="flex items-center gap-1.5 text-slate-400 font-semibold pr-2 border-r border-slate-800">
            <Globe className="w-3.5 h-3.5 text-cyan-400" />
            <span>LIVE ASSETS</span>
          </div>
          {marketStripSymbols.map((sym) => {
            const t = tickers[sym];
            if (!t) return null;
            const isUp = (t.change_24h ?? 0) >= 0;
            return (
              <div key={sym} className="flex items-center gap-2 px-2 py-0.5 rounded bg-slate-950/60 border border-slate-800/60">
                <span className="font-bold text-slate-300">{sym.replace('USDT', '')}</span>
                <span className="font-black text-slate-100">
                  ${t.price ? t.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'}
                </span>
                <span className={`text-[10px] font-bold flex items-center ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isUp ? <TrendingUp className="w-2.5 h-2.5 mr-0.5" /> : <TrendingDown className="w-2.5 h-2.5 mr-0.5" />}
                  {isUp ? '+' : ''}{(t.change_24h ?? 0).toFixed(2)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section B: Category Filter Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none" aria-label="Category Filters">
        {CATEGORIES.map((cat) => {
          const active = selectedCategory === cat.id;
          const count = categoryCounts[cat.id] ?? 0;
          return (
            <button
              key={cat.id}
              onClick={() => {
                setSelectedCategory(cat.id);
                setDisplayCount(12);
              }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-150 ${
                active
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/40 font-bold'
                  : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800/90 border border-slate-800/80'
              }`}
            >
              <span>{cat.label}</span>
              <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                active ? 'bg-cyan-900 text-cyan-200' : 'bg-slate-800 text-slate-500'
              }`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search & Source Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
        {/* Search Input */}
        <div className="sm:col-span-6 relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setDisplayCount(12);
            }}
            placeholder="Search headlines, Bitcoin ETFs, liquidations, SEC..."
            className="w-full pl-9 pr-4 py-2 bg-slate-900/90 border border-slate-800 rounded-xl text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-600 focus:ring-1 focus:ring-cyan-600 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-2.5 text-xs text-slate-500 hover:text-slate-300 font-mono"
            >
              Clear
            </button>
          )}
        </div>

        {/* Source Dropdown */}
        <div className="sm:col-span-3">
          <select
            value={selectedSource}
            onChange={(e) => {
              setSelectedSource(e.target.value);
              setDisplayCount(12);
            }}
            className="w-full px-3 py-2 bg-slate-900/90 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-600 focus:ring-1 focus:ring-cyan-600 transition-all"
          >
            <option value="all">All Publishers ({articles.length})</option>
            {availableSources.map((src) => (
              <option key={src} value={src}>
                {src}
              </option>
            ))}
          </select>
        </div>

        {/* Sort Order Toggle */}
        <div className="sm:col-span-3">
          <button
            onClick={() => setSortOrder((prev) => (prev === 'newest' ? 'oldest' : 'newest'))}
            className="w-full flex items-center justify-between px-3 py-2 bg-slate-900/90 border border-slate-800 rounded-xl text-xs font-mono text-slate-300 hover:bg-slate-800 transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <ArrowUpDown className="w-3.5 h-3.5 text-cyan-400" />
              <span>Sort:</span>
            </span>
            <span className="font-bold text-cyan-400 uppercase">
              {sortOrder === 'newest' ? 'Newest First' : 'Oldest First'}
            </span>
          </button>
        </div>
      </div>

      {/* Section C: News Feed Grid */}
      
      {/* Loading Skeleton */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-pulse">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
            <div key={i} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-4">
              <div className="h-44 w-full bg-slate-800 rounded-xl" />
              <div className="flex justify-between items-center">
                <div className="h-4 w-24 bg-slate-800 rounded" />
                <div className="h-3 w-16 bg-slate-800 rounded" />
              </div>
              <div className="h-5 w-full bg-slate-800 rounded" />
              <div className="h-4 w-3/4 bg-slate-800 rounded" />
              <div className="h-3 w-full bg-slate-850 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="py-12 flex flex-col items-center justify-center text-center border border-dashed border-rose-900/40 rounded-2xl bg-rose-950/10 p-6">
          <AlertCircle className="w-10 h-10 text-rose-400 mb-3" />
          <h3 className="text-base font-bold text-rose-300">Live Crypto News Feed Error</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-lg">{error}</p>
          <button
            onClick={() => fetchNews(true)}
            className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-semibold rounded-xl transition-colors"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Populated Articles Grid */}
      {!loading && !error && visibleArticles.length > 0 && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {visibleArticles.map((article) => {
              const timeAgo = formatTimeAgo(article.published_at);
              const sourceBadgeClass = getSourceBadgeColor(article.source);

              return (
                <article
                  key={article.id}
                  className="group bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-cyan-800/50 rounded-2xl p-4 sm:p-5 flex flex-col justify-between backdrop-blur-sm shadow-lg hover:shadow-cyan-950/20 transition-all duration-200"
                >
                  <div className="space-y-3">
                    {/* Optional Thumbnail Image */}
                    {article.image_url ? (
                      <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-slate-950 border border-slate-800/80">
                        <img
                          src={article.image_url}
                          alt={article.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          loading="lazy"
                          onError={(e) => {
                            // Hide image container on broken image link
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                      </div>
                    ) : null}

                    {/* Meta Top: Source & Timestamp */}
                    <div className="flex items-center justify-between gap-2">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${sourceBadgeClass}`}>
                        {article.source}
                      </span>
                      <span 
                        className="text-[11px] font-mono text-slate-400 flex items-center gap-1"
                        title={new Date(article.published_at).toLocaleString()}
                      >
                        <Clock className="w-3 h-3 text-slate-500" />
                        {timeAgo}
                      </span>
                    </div>

                    {/* Headline */}
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block group/link"
                    >
                      <h3 className="text-sm font-bold text-slate-100 group-hover/link:text-cyan-300 transition-colors line-clamp-2 leading-snug">
                        {article.title}
                      </h3>
                    </a>

                    {/* Summary */}
                    {article.summary && (
                      <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed font-sans">
                        {article.summary}
                      </p>
                    )}
                  </div>

                  {/* Card Footer: Category Badges & Read Link */}
                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2 text-xs">
                    <div className="flex flex-wrap items-center gap-1">
                      {article.categories
                        .filter((c) => c !== 'all')
                        .slice(0, 3)
                        .map((cat) => (
                          <span
                            key={cat}
                            className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400"
                          >
                            #{cat}
                          </span>
                        ))}
                    </div>

                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors shrink-0"
                    >
                      <span>Read Story</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </article>
              );
            })}
          </div>

          {/* Load More Button */}
          {filteredArticles.length > visibleArticles.length && (
            <div className="flex justify-center pt-2 pb-4">
              <button
                onClick={() => setDisplayCount((prev) => prev + 12)}
                className="px-6 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-cyan-300 border border-slate-750 hover:border-cyan-800 rounded-xl text-xs font-semibold font-mono transition-all shadow-md"
              >
                Load More Headlines ({filteredArticles.length - visibleArticles.length} remaining)
              </button>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredArticles.length === 0 && (
        <div className="py-16 flex flex-col items-center justify-center text-center border border-dashed border-slate-800 rounded-2xl bg-slate-900/30 p-6">
          <Newspaper className="w-10 h-10 text-slate-600 mb-3" />
          <h3 className="text-base font-bold text-slate-300">No news articles match your filter</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md">
            Try adjusting your search query, selecting another category, or clearing the publisher filter.
          </p>
          <button
            onClick={() => {
              setSelectedCategory('all');
              setSelectedSource('all');
              setSearchQuery('');
            }}
            className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs font-mono font-semibold rounded-xl transition-colors"
          >
            Reset Filters
          </button>
        </div>
      )}

      {/* Bottom Legal & Safety Banner */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-500">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>
            External market news is provided for contextual research and education only. It does not constitute investment advice or automated order triggers.
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span>Sources: Cointelegraph • CoinDesk • Decrypt</span>
        </div>
      </div>

    </div>
  );
};

export default MarketNewsView;
