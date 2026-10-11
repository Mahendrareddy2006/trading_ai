import React, { useState } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Power, 
  DollarSign, 
  Layers, 
  Activity,
  CheckCircle2,
  Lock
} from 'lucide-react';
import { Position, RiskStatus } from '../types';

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
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);

  const killSwitchActive = riskStatus?.kill_switch_active ?? false;
  const inCooldown = riskStatus?.in_cooldown ?? false;

  const totalNotional = positions.reduce((acc, p) => acc + (p.notional || 0), 0);
  const exposurePct = equity > 0 ? (totalNotional / equity) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Header with Prominent Kill Switch */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-500" />
            <span>PORTFOLIO & INSTITUTIONAL RISK CONTROLS</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Centralized risk engine enforcing fixed-fractional sizing, daily loss caps, trailing drawdown stops, and emergency kill switches.
          </p>
        </div>

        {/* Big Kill Switch Button */}
        <div>
          <button
            onClick={() => setConfirmModalOpen(true)}
            className={`px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all shadow-lg ${
              killSwitchActive
                ? 'bg-rose-600 hover:bg-rose-500 text-white animate-pulse shadow-rose-900/50'
                : 'bg-slate-900 hover:bg-rose-950 text-rose-400 border border-rose-900/50 hover:border-rose-700'
            }`}
          >
            <Power className="w-4 h-4" />
            <span>{killSwitchActive ? 'EMERGENCY KILL SWITCH ENGAGED' : 'ENGAGE EMERGENCY KILL SWITCH'}</span>
          </button>
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400 font-bold">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base text-slate-100">Confirm Kill Switch Action</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed font-mono">
              {killSwitchActive
                ? 'Disengaging the kill switch will allow the strategy engine to resume generating new paper/live orders.'
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
            <span>CAPITAL ALLOCATION</span>
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
  );
};
