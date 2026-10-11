import React from 'react';
import { 
  Activity, 
  Terminal, 
  CandlestickChart as ChartIcon,
  BrainCircuit, 
  FlaskConical, 
  History, 
  ShieldAlert, 
  BookOpen, 
  Settings as SettingsIcon,
  Power,
  Lock,
  LogOut,
  UserCheck
} from 'lucide-react';
import { TabType, SystemHealth, RiskStatus } from '../types';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  health: SystemHealth | null;
  riskStatus: RiskStatus | null;
  wsConnected: boolean;
  onToggleKillSwitch: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onSelectTab,
  health,
  riskStatus,
  wsConnected,
  onToggleKillSwitch
}) => {
  const { user, isAuthenticated, openLoginModal, logout } = useAuth();

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: Activity },
    { id: 'terminal' as TabType, label: 'Market Terminal', icon: Terminal },
    { id: 'market-detail' as TabType, label: 'Chart & Detail', icon: ChartIcon },
    { id: 'models' as TabType, label: 'Model Lab', icon: BrainCircuit },
    { id: 'training' as TabType, label: 'Training', icon: FlaskConical },
    { id: 'backtest' as TabType, label: 'Backtesting', icon: History },
    { id: 'risk' as TabType, label: 'Portfolio & Risk', icon: ShieldAlert },
    { id: 'journal' as TabType, label: 'Trade Journal', icon: BookOpen },
    { id: 'settings' as TabType, label: 'Settings', icon: SettingsIcon },
  ];

  const killSwitchActive = riskStatus?.kill_switch_active ?? false;

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Mode */}
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-900/40">
              <span className="text-white font-black text-xl">⚡</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-slate-100 tracking-tight text-base">TRADING AI</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-cyan-400 border border-slate-700">
                  v2.0
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                <span className="flex items-center gap-1.5">
                  <span className={`inline-block w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
                  {wsConnected ? 'LIVE FEED' : 'CONNECTING'}
                </span>
                <span>•</span>
                <span className="px-1.5 py-0.2 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 font-semibold text-[11px]">
                  {health?.is_paper ? 'PAPER TRADING' : 'SIMULATION'}
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden lg:flex items-center gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onSelectTab(tab.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                    active
                      ? 'bg-slate-800 text-cyan-400 border border-slate-700 shadow-inner'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${active ? 'text-cyan-400' : 'text-slate-500'}`} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Auth & Emergency Controls */}
          <div className="flex items-center gap-3">
            {/* User Session Badge / Login */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2">
                <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-300">
                  <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{user.username}</span>
                  {user.is_superuser && (
                    <span className="text-[10px] bg-cyan-950 text-cyan-400 px-1 py-0.2 rounded border border-cyan-800">
                      ADMIN
                    </span>
                  )}
                </div>
                <button
                  onClick={logout}
                  title="Sign out of private session"
                  className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 rounded-lg transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={openLoginModal}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-cyan-300 border border-slate-800 hover:border-cyan-800 rounded-lg text-xs font-semibold transition-all shadow-sm"
              >
                <Lock className="w-3.5 h-3.5 text-cyan-400" />
                <span>Sign In</span>
              </button>
            )}

            {/* Emergency Kill Switch */}
            <button
              onClick={onToggleKillSwitch}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 shadow-md ${
                killSwitchActive
                  ? 'bg-rose-600 text-white animate-pulse border border-rose-500 shadow-rose-950/60'
                  : 'bg-slate-900 text-slate-300 hover:bg-rose-950/50 hover:text-rose-300 border border-slate-800 hover:border-rose-900/60'
              }`}
              title="Emergency kill switch stops all new order generation"
            >
              <Power className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{killSwitchActive ? 'KILL SWITCH ENGAGED' : 'KILL SWITCH'}</span>
            </button>
          </div>
        </div>

        {/* Mobile Navigation bar */}
        <div className="flex lg:hidden overflow-x-auto py-2 gap-2 border-t border-slate-800/60">
          {tabs.map((tab) => {
            const active = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`px-3 py-1 text-xs whitespace-nowrap rounded-md font-medium ${
                  active ? 'bg-slate-800 text-cyan-400 font-bold' : 'text-slate-400'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
