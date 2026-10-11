import React, { useState, useEffect, useCallback } from 'react';
import { 
  Newspaper, 
  ExternalLink, 
  RefreshCw, 
  ArrowRight, 
  AlertCircle,
  Clock,
  Sparkles
} from 'lucide-react';
import { NewsArticle } from '../types';
import { api } from '../services/api';

interface LatestNewsWidgetProps {
  onNavigateToNews: () => void;
}

export const LatestNewsWidget: React.FC<LatestNewsWidgetProps> = ({ onNavigateToNews }) => {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const fetchNews = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const data = await api.getNews({ limit: 6, refresh: isManualRefresh });
      setArticles(data.articles || []);
      setIsStale(data.is_stale);
      setLastUpdated(data.last_updated);
    } catch (err: any) {
      console.error('Failed to load latest market news:', err);
      setError(err?.message || 'Unable to connect to live crypto news feeds.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

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
        return 'bg-amber-950/70 text-amber-300 border-amber-800/40';
      case 'coindesk':
        return 'bg-emerald-950/70 text-emerald-300 border-emerald-800/40';
      case 'decrypt':
        return 'bg-indigo-950/70 text-indigo-300 border-indigo-800/40';
      default:
        return 'bg-slate-800 text-cyan-300 border-slate-700';
    }
  };

  return (
    <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl transition-all">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/50 text-cyan-400">
            <Newspaper className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-100 text-sm tracking-wide">
                LATEST MARKET NEWS & INTELLIGENCE
              </h3>
              {isStale && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/50">
                  CACHED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Live crypto journalism from Cointelegraph, CoinDesk & Decrypt
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchNews(true)}
            disabled={refreshing || loading}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors text-xs flex items-center gap-1 font-mono disabled:opacity-50"
            title="Refresh news feed"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          <button
            onClick={onNavigateToNews}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 hover:text-cyan-200 border border-cyan-800/60 rounded-lg text-xs font-semibold transition-all group"
          >
            <span>Full News Terminal</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-pulse">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="p-4 rounded-lg bg-slate-950/50 border border-slate-800/60 space-y-3">
              <div className="flex justify-between items-center">
                <div className="h-4 w-20 bg-slate-800 rounded" />
                <div className="h-3 w-14 bg-slate-800 rounded" />
              </div>
              <div className="h-4 w-full bg-slate-800 rounded" />
              <div className="h-4 w-4/5 bg-slate-800 rounded" />
              <div className="h-3 w-full bg-slate-850 rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="py-8 flex flex-col items-center justify-center text-center border border-dashed border-rose-900/40 rounded-lg bg-rose-950/10 p-4">
          <AlertCircle className="w-8 h-8 text-rose-400 mb-2" />
          <p className="text-sm font-semibold text-rose-300">Market news feed unavailable</p>
          <p className="text-xs text-slate-400 mt-1 max-w-md">{error}</p>
          <button
            onClick={() => fetchNews(true)}
            className="mt-3 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded-lg transition-colors"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Populated Articles Grid */}
      {!loading && !error && articles.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {articles.map((article) => {
            const timeAgo = formatTimeAgo(article.published_at);
            const sourceBadgeClass = getSourceBadgeColor(article.source);

            return (
              <a
                key={article.id}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group p-4 rounded-xl bg-slate-950/60 hover:bg-slate-900/90 border border-slate-800/80 hover:border-cyan-800/50 transition-all duration-200 flex flex-col justify-between shadow-sm hover:shadow-cyan-950/20"
              >
                <div>
                  {/* Card Meta Top: Source & Timestamp */}
                  <div className="flex items-center justify-between gap-2 mb-2">
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
                  <h4 className="text-xs font-bold text-slate-200 group-hover:text-cyan-300 transition-colors line-clamp-2 leading-snug">
                    {article.title}
                  </h4>

                  {/* Summary */}
                  {article.summary && (
                    <p className="text-[11px] text-slate-400 mt-2 line-clamp-2 leading-relaxed font-sans">
                      {article.summary}
                    </p>
                  )}
                </div>

                {/* Card Footer: Category Tags & External Link */}
                <div className="mt-3 pt-2.5 border-t border-slate-850/80 flex items-center justify-between text-[10px] font-mono text-slate-500">
                  <div className="flex items-center gap-1 overflow-hidden">
                    {article.categories
                      .filter((c) => c !== 'all')
                      .slice(0, 2)
                      .map((cat) => (
                        <span key={cat} className="uppercase px-1.5 py-0.2 rounded bg-slate-800/80 text-slate-400 text-[9px]">
                          #{cat}
                        </span>
                      ))}
                  </div>
                  <span className="flex items-center gap-1 text-slate-400 group-hover:text-cyan-400 transition-colors shrink-0">
                    <span>Read</span>
                    <ExternalLink className="w-3 h-3" />
                  </span>
                </div>
              </a>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && articles.length === 0 && (
        <div className="h-32 flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
          <Newspaper className="w-6 h-6 text-slate-600 mb-1" />
          <p>No headlines found currently</p>
        </div>
      )}

      {/* Market Safety & Disclaimer Footer */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-500">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span>External intelligence only — never treated as automated execution signals.</span>
        </div>
        {lastUpdated && (
          <span className="text-slate-400">
            Updated: {new Date(lastUpdated).toLocaleTimeString()}
          </span>
        )}
      </div>
    </section>
  );
};

export default LatestNewsWidget;
