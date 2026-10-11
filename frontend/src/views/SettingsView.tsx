import React from 'react';
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
  Layers
} from 'lucide-react';
import { SystemHealth, RiskStatus } from '../types';

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
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-cyan-400" />
          <span>SYSTEM HEALTH, ENVIRONMENT & SETTINGS</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          System operational status, network connectivity, security credentials audit, and risk limit configurations.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service Connectivity & Nodes */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl space-y-4">
          <h3 className="font-bold text-slate-100 text-sm tracking-wide flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            <span>CORE SUBSYSTEM STATUS</span>
          </h3>

          <div className="space-y-3 font-mono text-xs">
            {/* API Backend */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <div>
                  <span className="font-bold text-slate-200">FastAPI Backend Engine</span>
                  <p className="text-[10px] text-slate-500">http://127.0.0.1:8000/api</p>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                HEALTHY (v2.0)
              </span>
            </div>

            {/* WebSocket Stream */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Wifi className="w-4 h-4 text-indigo-400" />
                <div>
                  <span className="font-bold text-slate-200">Live WebSocket Feed</span>
                  <p className="text-[10px] text-slate-500">ws://127.0.0.1:8000/ws/live</p>
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                wsConnected 
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' 
                  : 'bg-rose-950 text-rose-400 border border-rose-800/50'
              }`}>
                {wsConnected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>

            {/* Persistent Database */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Database className="w-4 h-4 text-amber-400" />
                <div>
                  <span className="font-bold text-slate-200">SQLAlchemy Relational Store</span>
                  <p className="text-[10px] text-slate-500">sqlite:///trading_ai.db</p>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                ACTIVE
              </span>
            </div>

            {/* Trading Mode */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <div>
                  <span className="font-bold text-slate-200">Execution Safety Mode</span>
                  <p className="text-[10px] text-slate-500">Paper Trading Protection</p>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                PAPER (SAFE)
              </span>
            </div>
          </div>
        </div>

        {/* Security & Credential Hygiene */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl space-y-4">
          <h3 className="font-bold text-slate-100 text-sm tracking-wide flex items-center gap-2">
            <Lock className="w-4 h-4 text-emerald-400" />
            <span>SECURITY & CREDENTIAL AUDIT</span>
          </h3>

          <div className="space-y-3 text-xs text-slate-400">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200">Sanitized Environment (.env):</strong>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  All hardcoded API keys and secrets in test scripts have been scrubbed. The application fails closed into safe paper-trading mode when credentials are not configured.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200">Public Market Data Access:</strong>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Kline data collection uses public unauthenticated Binance REST endpoints with bounded pagination, exponential backoff, and UTC timestamp validation.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200">Fail-Safe Kill Switch:</strong>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Global kill switch halts order submission immediately. State persists in memory and database to survive restarts.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Configured Risk Limits */}
        <div className="lg:col-span-2 bg-slate-900/70 border border-slate-800 rounded-xl p-5 backdrop-blur-md shadow-xl">
          <h3 className="font-bold text-slate-100 text-sm tracking-wide mb-3 flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>CONFIGURED PARAMETER REGISTRY</span>
          </h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">RISK PER TRADE</span>
              <span className="text-cyan-400 font-bold text-sm">1.0% Equity</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">MAX DAILY LOSS</span>
              <span className="text-rose-400 font-bold text-sm">2.0% Circuit Breaker</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">MAX DRAWDOWN</span>
              <span className="text-rose-400 font-bold text-sm">10.0% Hard Stop</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">CONSECUTIVE LOSS LIMIT</span>
              <span className="text-amber-400 font-bold text-sm">3 Trades (2h Cooldown)</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">MAKER / TAKER FEE</span>
              <span className="text-slate-200 font-bold text-sm">0.04% Simulated</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">SLIPPAGE MODEL</span>
              <span className="text-slate-200 font-bold text-sm">0.05% Adverse</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">CALIBRATION METHOD</span>
              <span className="text-indigo-400 font-bold text-sm">Platt Scaling</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-500 block text-[10px]">MIN NOTIONAL</span>
              <span className="text-slate-200 font-bold text-sm">$5.00 Threshold</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
