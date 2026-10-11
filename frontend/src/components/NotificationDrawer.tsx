import React, { useState, useEffect, useCallback } from 'react';
import { 
  Bell, 
  X, 
  CheckCheck, 
  Trash2, 
  ExternalLink, 
  Clock, 
  TrendingUp, 
  ShieldAlert, 
  BrainCircuit, 
  Newspaper, 
  Settings,
  RefreshCw
} from 'lucide-react';
import { InAppNotification } from '../types';
import { api } from '../services/api';

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenSettings: () => void;
  onUnreadCountChange?: (count: number) => void;
}

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({
  isOpen,
  onClose,
  onOpenSettings,
  onUnreadCountChange
}) => {
  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getInAppNotifications({
        category: filterCategory === 'all' ? undefined : filterCategory,
        unread_only: unreadOnly,
        limit: 50
      });
      setNotifications(data.notifications || []);
      const unread = (data.notifications || []).filter(n => !n.is_read).length;
      if (onUnreadCountChange) onUnreadCountChange(unread);
    } catch (e) {
      console.error('Failed to load notifications:', e);
    } finally {
      setLoading(false);
    }
  }, [filterCategory, unreadOnly, onUnreadCountChange]);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      const unread = notifications.filter(n => n.id !== id && !n.is_read).length;
      if (onUnreadCountChange) onUnreadCountChange(unread);
    } catch (e) {
      console.error('Failed to mark notification read:', e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      if (onUnreadCountChange) onUnreadCountChange(0);
    } catch (e) {
      console.error('Failed to mark all read:', e);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteNotification(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
      const unread = notifications.filter(n => n.id !== id && !n.is_read).length;
      if (onUnreadCountChange) onUnreadCountChange(unread);
    } catch (e) {
      console.error('Failed to delete notification:', e);
    }
  };

  const formatTimeAgo = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${diffDays}d ago`;
    } catch {
      return dateStr;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'ml_signal':
        return <BrainCircuit className="w-4 h-4 text-cyan-400" />;
      case 'price_alert':
        return <TrendingUp className="w-4 h-4 text-amber-400" />;
      case 'market_news':
        return <Newspaper className="w-4 h-4 text-indigo-400" />;
      case 'risk_event':
        return <ShieldAlert className="w-4 h-4 text-rose-400" />;
      default:
        return <Bell className="w-4 h-4 text-slate-400" />;
    }
  };

  if (!isOpen) return null;

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col">
          
          {/* Header */}
          <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between gap-3 bg-slate-900/60">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400">
                <Bell className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-slate-100 text-sm">Notifications</h3>
                  {unreadCount > 0 && (
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-cyan-900 text-cyan-200 border border-cyan-700 font-bold">
                      {unreadCount} unread
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 font-mono">Live alert logs & updates</p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={fetchNotifications}
                title="Refresh notifications"
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  title="Mark all as read"
                  className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <CheckCheck className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Category Filter Pills */}
          <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-950 flex items-center gap-1.5 overflow-x-auto text-[11px] font-mono scrollbar-none">
            {[
              { id: 'all', label: 'All' },
              { id: 'ml_signal', label: 'ML Signals' },
              { id: 'price_alert', label: 'Price Alerts' },
              { id: 'market_news', label: 'News' },
              { id: 'risk_event', label: 'Risk' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setFilterCategory(tab.id)}
                className={`px-2.5 py-1 rounded-lg font-medium whitespace-nowrap transition-colors ${
                  filterCategory === tab.id
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* List Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
            {loading && notifications.length === 0 ? (
              <div className="py-12 text-center text-slate-500 font-mono text-xs">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
                <span>Loading alerts...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-16 text-center text-slate-500 font-mono text-xs">
                <Bell className="w-8 h-8 mx-auto mb-2 text-slate-700 stroke-1" />
                <p className="text-slate-400 font-medium">No alerts found</p>
                <p className="text-[11px] text-slate-600 mt-1">Configure ML thresholds or price alerts to start receiving notifications.</p>
              </div>
            ) : (
              notifications.map(n => (
                <div
                  key={n.id}
                  className={`p-3 rounded-xl border transition-all ${
                    n.is_read
                      ? 'bg-slate-900/40 border-slate-850 opacity-75 hover:opacity-100'
                      : 'bg-slate-900/90 border-slate-800 shadow-md ring-1 ring-cyan-500/10'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 shrink-0">
                        {getCategoryIcon(n.category)}
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <h4 className="font-bold text-xs text-slate-200 leading-snug">{n.title}</h4>
                          {!n.is_read && (
                            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1 mt-0.5">
                          <Clock className="w-2.5 h-2.5" />
                          {formatTimeAgo(n.created_at)}
                          {n.symbol && (
                            <>
                              <span>•</span>
                              <span className="text-cyan-400 font-semibold">{n.symbol}</span>
                            </>
                          )}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      {!n.is_read && (
                        <button
                          onClick={() => handleMarkAsRead(n.id)}
                          title="Mark read"
                          className="p-1 text-slate-500 hover:text-cyan-400 rounded transition-colors"
                        >
                          <CheckCheck className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(n.id)}
                        title="Delete"
                        className="p-1 text-slate-500 hover:text-rose-400 rounded transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <p className="mt-2 text-xs text-slate-300 leading-relaxed font-sans whitespace-pre-line pl-8">
                    {n.message}
                  </p>

                  {n.metadata?.url && (
                    <div className="mt-2 pl-8">
                      <a
                        href={n.metadata.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] font-mono text-cyan-400 hover:underline"
                      >
                        <span>View Source Article</span>
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Footer Action */}
          <div className="p-3 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
            <span className="text-[10px] font-mono text-slate-500">
              Instant alerts & summaries active
            </span>
            <button
              onClick={() => {
                onClose();
                onOpenSettings();
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition-colors"
            >
              <Settings className="w-3.5 h-3.5 text-cyan-400" />
              <span>Notification Center</span>
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};

export default NotificationDrawer;
