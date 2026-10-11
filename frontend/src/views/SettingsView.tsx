import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  ShieldCheck, 
  Server, 
  Wifi, 
  Database, 
  Lock, 
  CheckCircle2, 
  AlertTriangle,
  Cpu,
  Layers,
  Activity,
  Globe,
  Key,
  RefreshCw,
  Trash2,
  Eye,
  EyeOff,
  Link2,
  Info,
  ShieldAlert
} from 'lucide-react';
import { SystemHealth, RiskStatus, SystemDataStatus, ExchangeConnectionRecord } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface SettingsViewProps {
  health: SystemHealth | null;
  riskStatus: RiskStatus | null;
  wsConnected: boolean;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  health,
  riskStatus,
  wsConnected
}) => {
  const { isAuthenticated, openLoginModal } = useAuth();
  const [activeTab, setActiveTab] = useState<'connections' | 'health' | 'risk'>('connections');
  const [dataStatus, setDataStatus] = useState<SystemDataStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);

  // Exchange Connections state
  const [connections, setConnections] = useState<ExchangeConnectionRecord[]>([]);
  const [loadingConnections, setLoadingConnections] = useState(false);
  const [label, setLabel] = useState('Binance USDⓈ-M Futures');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [isTestnet, setIsTestnet] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const fetchStatus = async () => {
    setLoadingStatus(true);
    try {
      const status = await api.getSystemDataStatus();
      setDataStatus(status);
    } catch (e) {
      console.error('Failed to load system data status:', e);
    } finally {
      setLoadingStatus(false);
    }
  };

  const fetchConnections = async () => {
    if (!isAuthenticated) return;
    setLoadingConnections(true);
    try {
      const conns = await api.getExchangeConnections();
      setConnections(conns);
    } catch (e) {
      console.error('Failed to load exchange connections:', e);
    } finally {
      setLoadingConnections(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    if (isAuthenticated) {
      fetchConnections();
    }
  }, [isAuthenticated]);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim() || !apiSecret.trim()) return;

    setSubmitting(true);
    setFeedback(null);
    try {
      const res = await api.connectExchange({
        exchange: 'binance_futures',
        label: label.trim() || 'Binance USDⓈ-M Futures',
        api_key: apiKey.trim(),
        api_secret: apiSecret.trim(),
        testnet: isTestnet
      });

      setFeedback({ type: 'success', message: res.message || 'Connected successfully! Read-only permissions validated.' });
      setApiKey('');
      setApiSecret('');
      fetchConnections();
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Connection validation failed.' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteConnection = async (id: string) => {
    if (!window.confirm('Are you sure you want to remove this connection? Your encrypted credentials will be purged from the server.')) {
      return;
    }
    try {
      await api.deleteExchangeConnection(id);
      setConnections((prev) => prev.filter((c) => c.id !== id));
      setFeedback({ type: 'success', message: 'Credentials deleted and purged from the secure store.' });
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Failed to remove connection.' });
    }
  };

  const handleSyncConnection = async (id: string) => {
    try {
      const res = await api.syncExchangeConnection(id);
      fetchConnections();
      setFeedback({ type: 'success', message: res.message || 'Connection re-verified successfully.' });
    } catch (e: any) {
      setFeedback({ type: 'error', message: e.message || 'Synchronization failed.' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-cyan-400" />
            <span>PLATFORM SETTINGS & EXCHANGE INTEGRATIONS</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage user exchange connections, audit security parameters, and monitor system health.
          </p>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('connections')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'connections'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Exchange Connections
          </button>
          <button
            onClick={() => setActiveTab('health')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'health'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            System Health & Audit
          </button>
          <button
            onClick={() => setActiveTab('risk')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'risk'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Risk Registry
          </button>
        </div>
      </div>

      {/* Feedback banner */}
      {feedback && (
        <div className={`p-4 rounded-xl border flex items-start gap-3 text-xs ${
          feedback.type === 'success'
            ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
            : 'bg-rose-950/60 border-rose-800 text-rose-300'
        }`}>
          {feedback.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p className="font-semibold">{feedback.message}</p>
          </div>
          <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-200 text-xs">Dismiss</button>
        </div>
      )}

      {/* TAB 1: EXCHANGE CONNECTIONS */}
      {activeTab === 'connections' && (
        <div className="space-y-6">
          {!isAuthenticated ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center backdrop-blur-md">
              <Lock className="w-10 h-10 text-cyan-400 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-100">Private Account Access Required</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 mb-4">
                To connect and monitor your private Binance Futures account, please sign in to your authorized user session.
              </p>
              <button
                onClick={openLoginModal}
                className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs rounded-lg shadow-lg shadow-cyan-900/40 transition-all"
              >
                Sign In to Connect Exchange
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Connect New Key Form (7 cols) */}
              <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-xl">
                <div className="flex items-center gap-2.5 mb-4 border-b border-slate-800 pb-3">
                  <Link2 className="w-5 h-5 text-cyan-400" />
                  <div>
                    <h3 className="font-bold text-slate-100 text-sm">Connect Binance USDⓈ-M Futures Account</h3>
                    <p className="text-[11px] text-slate-400">Read-only account balance, open positions, and margin monitoring</p>
                  </div>
                </div>

                <form onSubmit={handleConnect} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                      Connection Label
                    </label>
                    <input
                      type="text"
                      value={label}
                      onChange={(e) => setLabel(e.target.value)}
                      placeholder="My Primary Binance Account"
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                      Binance API Key
                    </label>
                    <input
                      type="text"
                      required
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="Enter 64-character Binance API key"
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase tracking-wider">
                      Binance API Secret
                    </label>
                    <div className="relative">
                      <input
                        type={showSecret ? 'text' : 'password'}
                        required
                        value={apiSecret}
                        onChange={(e) => setApiSecret(e.target.value)}
                        placeholder="••••••••••••••••••••••••••••••••"
                        className="w-full pl-3 pr-10 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                      />
                      <button
                        type="button"
                        onClick={() => setShowSecret(!showSecret)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300"
                      >
                        {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="checkbox"
                      id="testnet-toggle"
                      checked={isTestnet}
                      onChange={(e) => setIsTestnet(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-950 text-cyan-600 focus:ring-cyan-500"
                    />
                    <label htmlFor="testnet-toggle" className="text-xs text-slate-300 font-mono cursor-pointer">
                      Use Binance Futures Testnet (<code className="text-cyan-400">testnet.binancefuture.com</code>)
                    </label>
                  </div>

                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={submitting || !apiKey.trim() || !apiSecret.trim()}
                      className="w-full py-2.5 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs rounded-lg shadow-lg shadow-cyan-900/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {submitting ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>Testing & Validating with Binance...</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Validate & Securely Store Connection</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>

              {/* Security Advisory & Protocol (5 cols) */}
              <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-3 border-b border-slate-800 pb-3">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-bold text-slate-100 text-sm">Security & Isolation Policy</h3>
                  </div>

                  <div className="space-y-3 text-xs text-slate-300">
                    <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
                      <strong className="text-cyan-400 block mb-0.5">1. Read-Only Permission Required</strong>
                      <p className="text-[11px] text-slate-400">
                        In Binance API Management, only enable "Enable Reading" under USDⓈ-M Futures. Never enable "Enable Spot & Margin Trading", "Enable Futures" order execution, or "Enable Withdrawals".
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
                      <strong className="text-cyan-400 block mb-0.5">2. AES-256-GCM Encryption at Rest</strong>
                      <p className="text-[11px] text-slate-400">
                        Your credentials are encrypted using authenticated envelope encryption with separate managed master keys. Plaintext keys are never logged or returned to the browser.
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80">
                      <strong className="text-cyan-400 block mb-0.5">3. Outbound IP Whitelisting</strong>
                      <p className="text-[11px] text-slate-400">
                        If your Binance account requires IP restrictions, whitelist your outbound server IP. The system will report your outbound IP if an IP mismatch occurs.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 text-[10px] text-slate-500 font-mono">
                  <span>Server-level safety barrier: Real order execution endpoints are permanently disabled.</span>
                </div>
              </div>

              {/* Connected Accounts Table (12 cols) */}
              <div className="lg:col-span-12 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-xl">
                <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Key className="w-5 h-5 text-cyan-400" />
                    <h3 className="font-bold text-slate-100 text-sm">Your Active Exchange Connections</h3>
                  </div>
                  <button
                    onClick={fetchConnections}
                    className="text-xs text-slate-400 hover:text-cyan-400 flex items-center gap-1 font-mono"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingConnections ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>

                {connections.length === 0 ? (
                  <div className="py-8 text-center text-slate-500 font-mono text-xs">
                    <p>No exchange connections configured for your account.</p>
                    <p className="text-[11px] text-slate-600 mt-1">Connect your read-only Binance Futures key above to monitor real equity and margin.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-[10px] text-slate-500 uppercase tracking-wider">
                          <th className="py-2.5 px-3">Label</th>
                          <th className="py-2.5 px-3">Exchange</th>
                          <th className="py-2.5 px-3">Masked API Key</th>
                          <th className="py-2.5 px-3">Environment</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Last Synchronized</th>
                          <th className="py-2.5 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {connections.map((c) => (
                          <tr key={c.id} className="hover:bg-slate-800/40 transition-colors">
                            <td className="py-3 px-3 font-bold text-slate-200">{c.label}</td>
                            <td className="py-3 px-3 text-slate-400">Binance USDⓈ-M Futures</td>
                            <td className="py-3 px-3 text-cyan-400">{c.api_key_masked}</td>
                            <td className="py-3 px-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] ${
                                c.is_testnet ? 'bg-amber-950 text-amber-400 border border-amber-800' : 'bg-slate-800 text-slate-300'
                              }`}>
                                {c.is_testnet ? 'TESTNET' : 'PRODUCTION'}
                              </span>
                            </td>
                            <td className="py-3 px-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                c.status === 'CONNECTED'
                                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                                  : c.status === 'IP_RESTRICTED'
                                  ? 'bg-amber-950 text-amber-400 border border-amber-800/60'
                                  : 'bg-rose-950 text-rose-400 border border-rose-800/60'
                              }`}>
                                {c.status}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-slate-400 text-[11px]">
                              {c.last_sync_at ? new Date(c.last_sync_at).toLocaleString() : 'Never'}
                            </td>
                            <td className="py-3 px-3 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <button
                                  onClick={() => handleSyncConnection(c.id)}
                                  title="Test connection"
                                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors"
                                >
                                  Test
                                </button>
                                <button
                                  onClick={() => handleDeleteConnection(c.id)}
                                  title="Purge credentials"
                                  className="p-1 rounded bg-rose-950/60 hover:bg-rose-900 text-rose-400 hover:text-white transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: SYSTEM HEALTH & AUDIT */}
      {activeTab === 'health' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Real Exchange Connectivity */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl space-y-4">
            <h3 className="font-bold text-slate-100 text-sm tracking-wide flex items-center gap-2">
              <Globe className="w-4 h-4 text-cyan-400" />
              <span>BINANCE USDⓈ-M FUTURES EXCHANGE LINK</span>
            </h3>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div>
                  <span className="font-bold text-slate-200">Official Endpoint</span>
                  <p className="text-[10px] text-slate-500">https://fapi.binance.com (Futures REST & WS)</p>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                  {dataStatus?.exchange_connectivity?.exchange || 'BINANCE USDⓈ-M FUTURES'}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center gap-2.5">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <div>
                    <span className="font-bold text-slate-200">Public Market Data Stream</span>
                    <p className="text-[10px] text-slate-500">
                      20 active Perpetual pairs subscribed
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                    {dataStatus?.exchange_connectivity?.status || 'CONNECTED'}
                  </span>
                  {dataStatus?.exchange_connectivity?.latency_ms !== undefined && (
                    <p className="text-[10px] text-slate-400 mt-1 font-mono">
                      Latency: {dataStatus.exchange_connectivity.latency_ms.toFixed(1)}ms
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center gap-2.5">
                  <Key className="w-4 h-4 text-amber-400" />
                  <div>
                    <span className="font-bold text-slate-200">Authenticated Account API</span>
                    <p className="text-[10px] text-slate-500">User-scoped encrypted storage</p>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  connections.length > 0
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  {connections.length > 0 ? `${connections.length} ACTIVE CONNECTION` : 'UNCONFIGURED (SAFE)'}
                </span>
              </div>

              {dataStatus?.server_time_offset_ms !== undefined && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <span className="text-slate-400">Server Clock Offset</span>
                  <span className="text-slate-200 font-bold">{dataStatus.server_time_offset_ms.toFixed(1)} ms</span>
                </div>
              )}
            </div>
          </div>

          {/* Core Subsystem Status */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl space-y-4">
            <h3 className="font-bold text-slate-100 text-sm tracking-wide flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              <span>CORE SUBSYSTEM STATUS</span>
            </h3>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center gap-2.5">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  <div>
                    <span className="font-bold text-slate-200">FastAPI Backend Engine</span>
                    <p className="text-[10px] text-slate-500">API Gateway with Auth Guard</p>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                  HEALTHY (v2.0)
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center gap-2.5">
                  <Wifi className="w-4 h-4 text-indigo-400" />
                  <div>
                    <span className="font-bold text-slate-200">Live WebSocket Feed</span>
                    <p className="text-[10px] text-slate-500">Multi-symbol real-time fanout</p>
                  </div>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  wsConnected ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'
                }`}>
                  {wsConnected ? 'CONNECTED' : 'DISCONNECTED'}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center gap-2.5">
                  <Database className="w-4 h-4 text-amber-400" />
                  <div>
                    <span className="font-bold text-slate-200">Relational SQLite Store</span>
                    <p className="text-[10px] text-slate-500">User, Credentials & Watchlists</p>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                  ACTIVE
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <div>
                    <span className="font-bold text-slate-200">Execution Safety Mode</span>
                    <p className="text-[10px] text-slate-500">Live Orders Strictly Disabled</p>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                  PAPER ONLY
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CONFIGURED RISK REGISTRY */}
      {activeTab === 'risk' && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-xl">
          <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-4 flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>CONFIGURED PARAMETER REGISTRY</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-mono text-xs">
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Risk Per Trade</span>
              <span className="text-cyan-400 font-bold text-base mt-1 block">1.0% Equity</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Max Daily Loss</span>
              <span className="text-rose-400 font-bold text-base mt-1 block">2.0% Circuit Breaker</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Max Drawdown</span>
              <span className="text-rose-400 font-bold text-base mt-1 block">10.0% Hard Stop</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Consecutive Loss Limit</span>
              <span className="text-amber-400 font-bold text-base mt-1 block">3 Trades (2h Cooldown)</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Maker / Taker Fee</span>
              <span className="text-slate-200 font-bold text-base mt-1 block">0.04% Simulated</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Slippage Model</span>
              <span className="text-slate-200 font-bold text-base mt-1 block">0.05% Adverse</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
