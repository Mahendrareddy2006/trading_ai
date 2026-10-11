import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Power, 
  Layers, 
  Activity, 
  CheckCircle2, 
  Lock,
  Wallet,
  Key,
  RefreshCw,
  ExternalLink,
  Eye,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import { 
  Position, 
  RiskStatus, 
  ExchangeAccountSummary, 
  ExchangePosition, 
  ExchangeOrder 
} from '../types';
import { api } from '../services/api';

interface PortfolioRiskViewProps {
  cash: number;
  equity: number;
  positions: Position[];
  riskStatus: RiskStatus | null;
  onToggleKillSwitch: () => void;
  onClosePosition: (symbol: string) => void;
}

export const PortfolioRiskView: React.FC<PortfolioRiskViewProps> = ({
  cash,
  equity,
  positions,
  riskStatus,
  onToggleKillSwitch,
  onClosePosition
}) => {
  const [activeTab, setActiveTab] = useState<'paper' | 'real'>('paper');
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  
  // Real Exchange Data State
  const [exchangeSummary, setExchangeSummary] = useState<ExchangeAccountSummary | null>(null);
  const [exchangePositions, setExchangePositions] = useState<ExchangePosition[]>([]);
  const [exchangeOrders, setExchangeOrders] = useState<ExchangeOrder[]>([]);
  const [loadingReal, setLoadingReal] = useState(false);
  const [realError, setRealError] = useState<string | null>(null);

  const killSwitchActive = riskStatus?.kill_switch_active ?? false;
  const inCooldown = riskStatus?.in_cooldown ?? false;

  const totalNotional = positions.reduce((acc, p) => acc + (p.notional || 0), 0);
  const exposurePct = equity > 0 ? (totalNotional / equity) * 100 : 0;

  const fetchRealAccountData = async () => {
    setLoadingReal(true);
    setRealError(null);
    try {
      const [sum, pos, ord] = await Promise.all([
        api.getExchangeAccountSummary(),
        api.getExchangePositions(),
        api.getExchangeOpenOrders()
      ]);
      setExchangeSummary(sum);
      setExchangePositions(pos.positions || []);
      setExchangeOrders(ord.orders || []);
      if (sum.error) setRealError(sum.error);
    } catch (err: any) {
      setRealError(err?.message || 'Failed to connect to exchange account API');
    } finally {
      setLoadingReal(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'real') {
      fetchRealAccountData();
    }
  }, [activeTab]);

  return (
    <div className="space-y-6">
      {/* Account Type Selector Strip */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-xl p-3 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('paper')}
            className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-2 ${
              activeTab === 'paper'
                ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-cyan-300" />
            <span>Simulated Paper Portfolio ($10,000 Sandbox)</span>
          </button>

          <button
            onClick={() => setActiveTab('real')}
            className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-2 ${
              activeTab === 'real'
                ? 'bg-amber-600 text-white shadow-lg shadow-amber-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <Wallet className="w-4 h-4 text-amber-300" />
            <span>Real Binance USDⓈ-M Futures (Read-Only)</span>
            {exchangeSummary?.is_configured ? (
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            ) : (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-normal">Setup</span>
            )}
          </button>
        </div>

        {activeTab === 'paper' && (
          <button
            onClick={() => setConfirmModalOpen(true)}
            className={`px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 transition-all shadow-md ${
              killSwitchActive
                ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse'
                : 'bg-slate-950 hover:bg-rose-950/60 text-rose-400 border border-rose-900/40'
            }`}
          >
            <Power className="w-3.5 h-3.5" />
            <span>{killSwitchActive ? 'KILL SWITCH ENGAGED' : 'ENGAGE KILL SWITCH'}</span>
          </button>
        )}

        {activeTab === 'real' && (
          <button
            onClick={fetchRealAccountData}
            disabled={loadingReal}
            className="px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingReal ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh Account</span>
          </button>
        )}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: SIMULATED PAPER PORTFOLIO */}
      {/* ========================================================================= */}
      {activeTab === 'paper' && (
        <div className="space-y-6">
          {/* Active Cooldown Banner */}
          {inCooldown && (
            <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 flex items-center gap-3 text-amber-300 text-xs font-mono">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <div>
                <span className="font-bold">CIRCUIT BREAKER COOLDOWN ACTIVE: </span>
                <span>{riskStatus?.cooldown_message || 'Trading paused due to consecutive loss limit.'}</span>
              </div>
            </div>
          )}

          {/* Circuit Breaker Gauges */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Daily Loss Gauge */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono text-slate-400 uppercase">Daily Loss Limit</span>
                <span className="text-xs font-mono text-cyan-400 font-bold">Max {riskStatus?.max_daily_loss_pct || 2.0}%</span>
              </div>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-2xl font-black font-mono text-slate-100">
                  {(riskStatus?.daily_loss_pct || 0).toFixed(2)}%
                </span>
                <span className="text-xs font-mono text-slate-500">Utilization</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${(riskStatus?.daily_loss_pct || 0) > 1.5 ? 'bg-rose-500' : 'bg-cyan-500'}`}
                  style={{ width: `${Math.min(100, ((riskStatus?.daily_loss_pct || 0) / (riskStatus?.max_daily_loss_pct || 2.0)) * 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                Resets automatically at 00:00 UTC daily.
              </p>
            </div>

            {/* Trailing Drawdown Gauge */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono text-slate-400 uppercase">Max Trailing Drawdown</span>
                <span className="text-xs font-mono text-rose-400 font-bold">Max {riskStatus?.max_drawdown_pct || 10.0}%</span>
              </div>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-2xl font-black font-mono text-slate-100">
                  {(riskStatus?.drawdown_pct || 0).toFixed(2)}%
                </span>
                <span className="text-xs font-mono text-slate-500">High Watermark: ${riskStatus?.high_watermark?.toFixed(2) || '10,000.00'}</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${(riskStatus?.drawdown_pct || 0) > 7.0 ? 'bg-rose-500' : 'bg-indigo-500'}`}
                  style={{ width: `${Math.min(100, ((riskStatus?.drawdown_pct || 0) / (riskStatus?.max_drawdown_pct || 10.0)) * 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                Calculated from all-time portfolio peak.
              </p>
            </div>

            {/* Consecutive Loss Counter */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono text-slate-400 uppercase">Consecutive Loss Circuit</span>
                <span className="text-xs font-mono text-amber-400 font-bold">Limit: {riskStatus?.max_consecutive_losses || 3}</span>
              </div>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-2xl font-black font-mono text-slate-100">
                  {riskStatus?.consecutive_losses || 0} / {riskStatus?.max_consecutive_losses || 3}
                </span>
                <span className="text-xs font-mono text-slate-500">Losses</span>
              </div>
              <div className="flex gap-2 mt-2">
                {[1, 2, 3].map((step) => {
                  const filled = (riskStatus?.consecutive_losses || 0) >= step;
                  return (
                    <div 
                      key={step} 
                      className={`flex-1 h-2 rounded-full ${filled ? 'bg-rose-500' : 'bg-slate-800'}`} 
                    />
                  );
                })}
              </div>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                Triggers 2-hour cooldown upon 3 consecutive losses.
              </p>
            </div>
          </div>

          {/* Portfolio Exposure Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
              <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-3 flex items-center justify-between">
                <span>PAPER CAPITAL ALLOCATION</span>
                <Layers className="w-4 h-4 text-cyan-400" />
              </h3>
              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between text-slate-300">
                  <span>Cash Balance:</span>
                  <span className="text-slate-100 font-bold">${cash.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Open Notional:</span>
                  <span className="text-slate-100 font-bold">${totalNotional.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Exposure Ratio:</span>
                  <span className="text-cyan-400 font-bold">{exposurePct.toFixed(1)}% of Equity</span>
                </div>
              </div>
            </div>

            {/* Risk Governance Summary */}
            <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
              <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-3 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>INSTITUTIONAL RISK RULES</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-400">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Fixed-Fractional Sizing:</strong> Risk budget strictly bounded at 1.0% equity per trade.</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Exchange Precision:</strong> All orders rounded against Binance LOT_SIZE and PRICE_FILTER.</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Min-Notional Gate:</strong> Fills rejected if notional value &lt; $5.00 min threshold.</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0 mt-0.5" />
                  <span><strong>Protective Orders:</strong> Every entry submits synthetic stop-loss and take-profit brackets.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: REAL BINANCE USDⓈ-M FUTURES (READ-ONLY ACCOUNT) */}
      {/* ========================================================================= */}
      {activeTab === 'real' && (
        <div className="space-y-6">
          {/* Unconfigured State: Secure Local Configuration Guide */}
          {(!exchangeSummary || !exchangeSummary.is_configured) && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-2xl space-y-6">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
                  <Lock className="w-7 h-7" />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-100">
                      Real Binance Futures Credentials Not Configured
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-400 border border-amber-800/40">
                      READ-ONLY PROTOCOL
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed max-w-3xl">
                    To display your verified Binance USDⓈ-M Futures balance, active margin, unrealized PnL, open positions, and orders, configure read-only API credentials locally. The application strictly rejects fake numbers and fails closed when credentials are absent.
                  </p>
                </div>
              </div>

              {/* Step-by-step Setup Guide */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Step 1: Binance Permission Policy */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3 text-xs">
                  <div className="flex items-center gap-2 text-cyan-400 font-bold font-mono">
                    <Key className="w-4 h-4" />
                    <span>STEP 1: Create Read-Only API Key</span>
                  </div>
                  <ul className="space-y-2 text-slate-300 font-mono text-[11px] list-disc list-inside">
                    <li>Log into your Binance account and go to <strong>API Management</strong>.</li>
                    <li>Create a new System-Generated API key (e.g. named <code>trading-ai-dashboard</code>).</li>
                    <li>
                      <span className="text-emerald-400 font-bold">ENABLE: </span>
                      <code>Can Read</code> (or <code>Enable Reading</code>).
                    </li>
                    <li>
                      <span className="text-rose-400 font-bold">STRICTLY DISABLE: </span>
                      <code>Enable Futures</code>, <code>Spot & Margin Trading</code>, and <code>Enable Withdrawals</code>.
                    </li>
                    <li className="text-slate-400">Never enable withdrawals. The dashboard operates in read-only monitoring mode.</li>
                  </ul>
                </div>

                {/* Step 2: Configure Local .env */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-3 text-xs">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold font-mono">
                    <ShieldCheck className="w-4 h-4" />
                    <span>STEP 2: Add to Local .env File</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Open or create the file <code className="text-slate-200">.env</code> in your project root directory and add:
                  </p>
                  <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-cyan-300 select-all overflow-x-auto">
{`BINANCE_API_KEY=your_actual_binance_api_key
BINANCE_API_SECRET=your_actual_binance_secret_key`}
                  </pre>
                  <p className="text-[10px] text-slate-500">
                    Note: <code>.env</code> is git-ignored and never committed or shared. Secrets are stored exclusively on your local machine and never logged or sent to the browser.
                  </p>
                </div>
              </div>

              {/* Refresh Action */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                <span className="text-xs font-mono text-slate-500">
                  After updating your .env file, restart the server or click Refresh.
                </span>
                <button
                  onClick={fetchRealAccountData}
                  disabled={loadingReal}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold flex items-center gap-2"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingReal ? 'animate-spin' : ''}`} />
                  <span>Verify Connection Now</span>
                </button>
              </div>
            </div>
          )}

          {/* Configured State: Display Verified Live Account Balances & Metrics */}
          {exchangeSummary && exchangeSummary.is_configured && (
            <div className="space-y-6">
              {/* Account Status Badge */}
              <div className={`border rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 ${
                exchangeSummary.status === 'CONNECTED'
                  ? 'bg-slate-900/80 border-emerald-900/40'
                  : 'bg-amber-950/30 border-amber-800/60'
              }`}>
                <div className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full ${
                    exchangeSummary.status === 'CONNECTED' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                  }`} />
                  <div>
                    <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2 font-mono">
                      <span>BINANCE USDⓈ-M FUTURES LIVE ACCOUNT</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        exchangeSummary.status === 'CONNECTED'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                          : 'bg-amber-950 text-amber-300 border border-amber-800/50'
                      }`}>
                        {exchangeSummary.status === 'CONNECTED' ? 'VERIFIED REAL ACCOUNT' : 'AUTH VERIFICATION FAILED'}
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      Account Type: {exchangeSummary.account_type || 'USDT-M Futures'} | Status: {exchangeSummary.status}
                    </p>
                  </div>
                </div>

                <div className="text-right font-mono text-xs text-slate-400">
                  <span>Last Sync: {exchangeSummary.last_synced ? new Date(exchangeSummary.last_synced).toLocaleTimeString() : 'Recent'} UTC</span>
                </div>
              </div>

              {/* Authentication Error Diagnostic Banner */}
              {exchangeSummary.status !== 'CONNECTED' && (
                <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/80 text-amber-200 text-xs font-mono space-y-2">
                  <div className="flex items-center gap-2 font-bold text-amber-300">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>Credentials Detected, but Binance Rejected Account Authentication</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    {exchangeSummary.message || exchangeSummary.error || 'Authentication error from exchange.'}
                  </p>
                  <div className="pt-2 border-t border-amber-900/40 text-[11px] text-slate-400 space-y-1">
                    <p><strong>Troubleshooting Steps on Binance:</strong></p>
                    <ul className="list-disc list-inside space-y-0.5">
                      <li>Go to <strong>Binance &gt; API Management</strong> and inspect the API key.</li>
                      <li>Ensure <strong>Enable Reading</strong> is checked.</li>
                      <li>If <em>"Restrict access to trusted IPs only"</em> is enabled, whitelist your current outbound IP or switch to unrestricted.</li>
                      <li>Ensure this API key is associated with your <strong>USDⓈ-M Futures</strong> account.</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Total Wallet Balance */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg">
                  <span className="text-xs font-mono text-slate-400 uppercase">Total Wallet Balance</span>
                  <div className="mt-2 text-2xl font-black font-mono text-slate-100">
                    ${(exchangeSummary.total_wallet_balance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">USDT Collateral</span>
                </div>

                {/* Available Balance */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg">
                  <span className="text-xs font-mono text-slate-400 uppercase">Available Free Margin</span>
                  <div className="mt-2 text-2xl font-black font-mono text-emerald-400">
                    ${(exchangeSummary.available_balance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Ready for new orders</span>
                </div>

                {/* Total Unrealized PnL */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg">
                  <span className="text-xs font-mono text-slate-400 uppercase">Total Unrealized PnL</span>
                  <div className={`mt-2 text-2xl font-black font-mono ${(exchangeSummary.total_unrealized_pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {(exchangeSummary.total_unrealized_pnl ?? 0) >= 0 ? '+' : ''}${(exchangeSummary.total_unrealized_pnl ?? 0).toFixed(2)}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Mark-to-market futures</span>
                </div>

                {/* Margin Balance / Equity */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 shadow-lg">
                  <span className="text-xs font-mono text-slate-400 uppercase">Total Margin Balance</span>
                  <div className="mt-2 text-2xl font-black font-mono text-cyan-400">
                    ${(exchangeSummary.total_margin_balance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">
                    Initial Margin: ${(exchangeSummary.total_initial_margin ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Real Open Positions Table */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-100 text-sm tracking-wide font-mono flex items-center gap-2">
                    <Activity className="w-4 h-4 text-cyan-400" />
                    <span>REAL BINANCE OPEN POSITIONS ({exchangePositions.length})</span>
                  </h3>
                </div>

                {exchangePositions.length === 0 ? (
                  <div className="p-8 text-center text-xs font-mono text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800">
                    No active positions found on your Binance Futures account.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="py-2 px-3">Symbol</th>
                          <th className="py-2 px-3">Side</th>
                          <th className="py-2 px-3 text-right">Size</th>
                          <th className="py-2 px-3 text-right">Entry Price</th>
                          <th className="py-2 px-3 text-right">Mark Price</th>
                          <th className="py-2 px-3 text-right">Liq Price</th>
                          <th className="py-2 px-3 text-right">Leverage</th>
                          <th className="py-2 px-3 text-right">Unrealized PnL</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {exchangePositions.map((p, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/30">
                            <td className="py-2.5 px-3 font-bold text-slate-200">{p.symbol}</td>
                            <td className="py-2.5 px-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                p.side === 'LONG' || p.position_amount > 0 
                                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40' 
                                  : 'bg-rose-950 text-rose-400 border border-rose-800/40'
                              }`}>
                                {p.side}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-200">{Math.abs(p.position_amount)}</td>
                            <td className="py-2.5 px-3 text-right text-slate-300">${p.entry_price.toFixed(2)}</td>
                            <td className="py-2.5 px-3 text-right text-slate-300">${p.mark_price.toFixed(2)}</td>
                            <td className="py-2.5 px-3 text-right text-amber-400">
                              {p.liquidation_price !== null ? `$${p.liquidation_price.toFixed(2)}` : '--'}
                            </td>
                            <td className="py-2.5 px-3 text-right text-indigo-300">{p.leverage}x</td>
                            <td className={`py-2.5 px-3 text-right font-bold ${p.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Real Open Orders Table */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-100 text-sm tracking-wide font-mono flex items-center gap-2">
                    <Layers className="w-4 h-4 text-amber-400" />
                    <span>REAL BINANCE OPEN ORDERS ({exchangeOrders.length})</span>
                  </h3>
                </div>

                {exchangeOrders.length === 0 ? (
                  <div className="p-8 text-center text-xs font-mono text-slate-500 bg-slate-950/40 rounded-xl border border-slate-800">
                    No open resting orders found on your Binance Futures account.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="py-2 px-3">Order ID</th>
                          <th className="py-2 px-3">Symbol</th>
                          <th className="py-2 px-3">Side</th>
                          <th className="py-2 px-3">Type</th>
                          <th className="py-2 px-3 text-right">Price</th>
                          <th className="py-2 px-3 text-right">Orig Qty</th>
                          <th className="py-2 px-3 text-right">Executed Qty</th>
                          <th className="py-2 px-3 text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {exchangeOrders.map((o) => (
                          <tr key={o.order_id} className="hover:bg-slate-800/30">
                            <td className="py-2.5 px-3 text-slate-400">#{o.order_id}</td>
                            <td className="py-2.5 px-3 font-bold text-slate-200">{o.symbol}</td>
                            <td className="py-2.5 px-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                o.side === 'BUY' ? 'text-emerald-400' : 'text-rose-400'
                              }`}>
                                {o.side}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-300">{o.type}</td>
                            <td className="py-2.5 px-3 text-right text-slate-200">${o.price.toFixed(2)}</td>
                            <td className="py-2.5 px-3 text-right text-slate-300">{o.quantity}</td>
                            <td className="py-2.5 px-3 text-right text-slate-300">{o.executed_quantity}</td>
                            <td className="py-2.5 px-3 text-right text-cyan-400 font-bold">{o.status}</td>
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

      {/* Confirmation Modal for Kill Switch */}
      {confirmModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400 font-bold">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base text-slate-100">Confirm Kill Switch Action</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed font-mono">
              {killSwitchActive
                ? 'Disengaging the kill switch will allow the strategy engine to resume generating new paper orders.'
                : 'Engaging the kill switch immediately halts all new order generation across every symbol and prevents any new risk exposure.'}
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setConfirmModalOpen(false)}
                className="px-4 py-2 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onToggleKillSwitch();
                  setConfirmModalOpen(false);
                }}
                className={`px-4 py-2 rounded-lg text-xs font-mono font-bold text-white ${
                  killSwitchActive ? 'bg-cyan-600 hover:bg-cyan-500' : 'bg-rose-600 hover:bg-rose-500'
                }`}
              >
                {killSwitchActive ? 'Disengage Kill Switch' : 'Engage Kill Switch'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
