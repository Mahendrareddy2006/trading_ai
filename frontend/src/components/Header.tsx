import React, { useState, useRef, useEffect } from 'react';
import { 
  Activity, 
  Terminal, 
  CandlestickChart as ChartIcon,
  Newspaper,
  BrainCircuit, 
  FlaskConical, 
  History, 
  ShieldAlert, 
  BookOpen, 
  Settings as SettingsIcon,
  Power,
  Lock,
  LogOut,
  UserCheck,
  Menu,
  X,
  ChevronDown,
  Bell
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
  unreadCount?: number;
  onOpenNotifications?: () => void;
}

interface NavItem {
  id: TabType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description?: string;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onSelectTab,
  health,
  riskStatus,
  wsConnected,
  onToggleKillSwitch,
  unreadCount = 0,
  onOpenNotifications = () => {}
}) => {
  const { user, isAuthenticated, openLoginModal, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [labDropdownOpen, setLabDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setLabDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdown on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setLabDropdownOpen(false);
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Primary market tabs
  const primaryTabs: NavItem[] = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'terminal', label: 'Market Terminal', icon: Terminal },
    { id: 'market-detail', label: 'Chart & Detail', icon: ChartIcon },
    { id: 'news', label: 'Market News', icon: Newspaper },
    { id: 'risk', label: 'Portfolio & Risk', icon: ShieldAlert },
  ];

  // Secondary Research & Lab group tabs
  const researchTabs: NavItem[] = [
    { id: 'models', label: 'Model Lab', icon: BrainCircuit, description: 'Neural architecture & weights' },
    { id: 'training', label: 'Training', icon: FlaskConical, description: 'Retrain models on new data' },
    { id: 'backtest', label: 'Backtesting', icon: History, description: 'Vectorized & event-driven' },
    { id: 'journal', label: 'Trade Journal', icon: BookOpen, description: 'Execution logs & analytics' },
  ];

  const killSwitchActive = riskStatus?.kill_switch_active ?? false;
  const isResearchActive = researchTabs.some((t) => t.id === currentTab);
  const activeResearchItem = researchTabs.find((t) => t.id === currentTab);

  const handleTabClick = (tabId: TabType) => {
    onSelectTab(tabId);
    setLabDropdownOpen(false);
    setMobileMenuOpen(false);
  };

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/95 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-2 sm:gap-4">
          
          {/* Left: Branding & Status Indicators */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => handleTabClick('overview')}
              className="flex items-center gap-2.5 text-left group focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 rounded-lg p-0.5"
              title="Trading AI Dashboard"
            >
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-950/60 ring-1 ring-white/10 group-hover:scale-105 transition-transform duration-200">
                <span className="text-white font-black text-lg select-none">⚡</span>
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="font-extrabold text-slate-100 tracking-tight text-sm sm:text-base group-hover:text-cyan-400 transition-colors">
                    TRADING AI
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-cyan-400 border border-slate-700/80 font-semibold">
                    v2.0
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
                  <span className="flex items-center gap-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
                    <span className="hidden sm:inline">{wsConnected ? 'LIVE FEED' : 'CONNECTING'}</span>
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="px-1.5 py-0.2 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800/40 font-semibold text-[10px]">
                    {health?.is_paper ? 'PAPER' : 'SIMULATION'}
                  </span>
                </div>
              </div>
            </button>
          </div>

          {/* Center: Desktop Navigation Bar (Visible on lg and larger) */}
          <nav className="hidden lg:flex items-center gap-1 shrink-0" aria-label="Main Navigation">
            {/* Primary Tab Links */}
            {primaryTabs.map((tab) => {
              const Icon = tab.icon;
              const active = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabClick(tab.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 ${
                    active
                      ? 'bg-slate-800/90 text-cyan-400 border border-slate-700 shadow-sm shadow-cyan-950/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                  }`}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className={`w-3.5 h-3.5 ${active ? 'text-cyan-400' : 'text-slate-500'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}

            {/* Research & Lab Dropdown Menu */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setLabDropdownOpen((prev) => !prev)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 ${
                  isResearchActive
                    ? 'bg-slate-800/90 text-indigo-400 border border-slate-700 shadow-sm shadow-indigo-950/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                }`}
                aria-expanded={labDropdownOpen}
                aria-haspopup="true"
              >
                <BrainCircuit className={`w-3.5 h-3.5 ${isResearchActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                <span>{isResearchActive && activeResearchItem ? activeResearchItem.label : 'Research & Lab'}</span>
                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${labDropdownOpen ? 'rotate-180 text-cyan-400' : 'text-slate-500'}`} />
              </button>

              {/* Dropdown Menu Popup */}
              {labDropdownOpen && (
                <div className="absolute left-0 mt-2 w-56 rounded-xl bg-slate-900/95 border border-slate-800 shadow-2xl backdrop-blur-xl p-1.5 z-50 animate-in fade-in slide-in-from-top-1 duration-150">
                  <div className="px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-800/80 mb-1">
                    AI Research & Modeling
                  </div>
                  {researchTabs.map((item) => {
                    const ItemIcon = item.icon;
                    const active = currentTab === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => handleTabClick(item.id)}
                        className={`w-full flex items-start gap-2.5 px-2.5 py-2 rounded-lg text-left transition-colors text-xs ${
                          active
                            ? 'bg-slate-800 text-indigo-300 font-bold border border-slate-700/80'
                            : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                        }`}
                      >
                        <ItemIcon className={`w-4 h-4 mt-0.5 shrink-0 ${active ? 'text-indigo-400' : 'text-slate-400'}`} />
                        <div>
                          <div className="font-semibold text-xs leading-none mb-1">{item.label}</div>
                          {item.description && (
                            <div className="text-[10px] text-slate-500 font-mono leading-tight">{item.description}</div>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Settings Tab */}
            <button
              onClick={() => handleTabClick('settings')}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 ${
                currentTab === 'settings'
                  ? 'bg-slate-800/90 text-cyan-400 border border-slate-700 shadow-sm shadow-cyan-950/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
              }`}
            >
              <SettingsIcon className={`w-3.5 h-3.5 ${currentTab === 'settings' ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>Settings</span>
            </button>
          </nav>

          {/* Right Controls: Account, Kill Switch, Mobile Menu Button */}
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            {/* User Session Badge / Login */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-1.5">
                <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 shadow-sm">
                  <UserCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  <span className="max-w-[100px] truncate">{user.username}</span>
                  {user.is_superuser && (
                    <span className="text-[10px] bg-cyan-950 text-cyan-400 px-1 py-0.2 rounded border border-cyan-800 font-bold">
                      ADMIN
                    </span>
                  )}
                </div>
                <button
                  onClick={logout}
                  title="Sign out of current session"
                  className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={openLoginModal}
                className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-cyan-300 border border-slate-800 hover:border-cyan-800/60 rounded-lg text-xs font-semibold transition-all shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              >
                <Lock className="w-3.5 h-3.5 text-cyan-400" />
                <span>Sign In</span>
              </button>
            )}

            {/* Notification Center Bell */}
            <button
              onClick={onOpenNotifications}
              title="Open In-App Notifications Drawer"
              className="relative p-2 text-slate-400 hover:text-cyan-300 hover:bg-slate-800/80 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 flex items-center justify-center min-w-[16px] h-4 px-1 text-[9px] font-mono font-bold text-white bg-rose-600 rounded-full animate-pulse border border-slate-950">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </button>

            {/* Emergency Kill Switch */}
            <button
              onClick={onToggleKillSwitch}
              className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 ${
                killSwitchActive
                  ? 'bg-rose-600 text-white animate-pulse border border-rose-500 shadow-rose-950/60'
                  : 'bg-slate-900 text-slate-300 hover:bg-rose-950/50 hover:text-rose-300 border border-slate-800 hover:border-rose-900/60'
              }`}
              title="Emergency kill switch stops all new order generation"
            >
              <Power className="w-3.5 h-3.5 shrink-0" />
              <span className="hidden md:inline">
                {killSwitchActive ? 'KILL SWITCH ENGAGED' : 'KILL SWITCH'}
              </span>
              <span className="md:hidden">
                {killSwitchActive ? 'HALTED' : 'KILL'}
              </span>
            </button>

            {/* Mobile / Tablet Menu Button (Visible < lg) */}
            <button
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="lg:hidden p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5 text-cyan-400" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile / Tablet Responsive Drawer Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-800/90 bg-slate-950/98 backdrop-blur-2xl px-4 py-4 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="space-y-4 max-h-[calc(100vh-5rem)] overflow-y-auto">
            
            {/* Primary Markets Section */}
            <div>
              <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-cyan-400 font-bold">
                Market Operations
              </div>
              <div className="grid grid-cols-2 gap-1.5 mt-1.5">
                {primaryTabs.map((tab) => {
                  const Icon = tab.icon;
                  const active = currentTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab.id)}
                      className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-semibold text-left transition-colors ${
                        active
                          ? 'bg-slate-800 text-cyan-400 border border-slate-700'
                          : 'text-slate-300 hover:bg-slate-900 hover:text-white border border-transparent'
                      }`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-cyan-400' : 'text-slate-400'}`} />
                      <span className="truncate">{tab.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* AI Research & Lab Section */}
            <div>
              <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-indigo-400 font-bold">
                AI Research & Models
              </div>
              <div className="grid grid-cols-2 gap-1.5 mt-1.5">
                {researchTabs.map((item) => {
                  const Icon = item.icon;
                  const active = currentTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleTabClick(item.id)}
                      className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-semibold text-left transition-colors ${
                        active
                          ? 'bg-slate-800 text-indigo-300 border border-slate-700'
                          : 'text-slate-300 hover:bg-slate-900 hover:text-white border border-transparent'
                      }`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 ${active ? 'text-indigo-400' : 'text-slate-400'}`} />
                      <span className="truncate">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Settings & System Section */}
            <div className="pt-2 border-t border-slate-800/80 flex flex-col gap-2">
              <button
                onClick={() => handleTabClick('settings')}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs font-semibold text-left transition-colors ${
                  currentTab === 'settings'
                    ? 'bg-slate-800 text-cyan-400 border border-slate-700'
                    : 'text-slate-300 hover:bg-slate-900 hover:text-white border border-transparent'
                }`}
              >
                <SettingsIcon className="w-4 h-4 text-slate-400" />
                <span>System Settings</span>
              </button>

              {/* Mobile Auth Button if not authenticated */}
              {!isAuthenticated && (
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openLoginModal();
                  }}
                  className="flex items-center justify-center gap-2 px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs font-semibold text-cyan-400 hover:bg-slate-800"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>Sign In to Account</span>
                </button>
              )}

              {/* Status summary banner */}
              <div className="px-3 py-2 rounded-lg bg-slate-900/60 border border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1.5">
                  <span className={`inline-block w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-rose-500'}`} />
                  {wsConnected ? 'WebSocket Online' : 'Connecting'}
                </span>
                <span className="text-emerald-400 font-semibold">
                  {health?.is_paper ? 'Paper Mode' : 'Sandbox'}
                </span>
              </div>
            </div>

          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
