import React, { useState, useEffect, useCallback } from 'react';
import { 
  TabType, 
  SystemHealth, 
  RiskStatus, 
  Position, 
  Trade, 
  ModelRecord, 
  Prediction, 
  Candle,
  TickerData
} from './types';
import { api } from './services/api';
import { liveWs } from './services/websocket';
import { AuthProvider } from './context/AuthContext';
import { AuthModal } from './components/AuthModal';
import { Header } from './components/Header';
import { OverviewView } from './views/OverviewView';
import { TerminalView } from './views/TerminalView';
import { MarketDetailView } from './views/MarketDetailView';
import { ModelLabView } from './views/ModelLabView';
import { TrainingView } from './views/TrainingView';
import { BacktestView } from './views/BacktestView';
import { PortfolioRiskView } from './views/PortfolioRiskView';
import { JournalView } from './views/JournalView';
import { SettingsView } from './views/SettingsView';
import { MarketNewsView } from './views/MarketNewsView';
import { NotificationDrawer } from './components/NotificationDrawer';

function MainApp() {
  const [currentTab, setCurrentTab] = useState<TabType>('overview');
  const [wsConnected, setWsConnected] = useState(false);
  const [isNotificationDrawerOpen, setIsNotificationDrawerOpen] = useState(false);
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0);

  // Core Data State
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [riskStatus, setRiskStatus] = useState<RiskStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [cash, setCash] = useState(10000);
  const [equity, setEquity] = useState(10000);
  const [unrealizedPnl, setUnrealizedPnl] = useState(0);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [tickers, setTickers] = useState<Record<string, TickerData>>({});
  const [symbols, setSymbols] = useState<string[]>([
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 
    'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 
    'LTCUSDT', 'BCHUSDT', 'TRXUSDT', 'ARBUSDT', 'SUIUSDT', 
    'APTUSDT', 'NEARUSDT', 'UNIUSDT', 'ETCUSDT', 'FILUSDT'
  ]);

  // Selected symbol & timeframe for terminal & market detail
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');

  // Load Initial API Data
  const loadInitialData = useCallback(async () => {
    try {
      const [h, r, pData, tr, m, pred, tick, symList] = await Promise.allSettled([
        api.getHealth(),
        api.getRiskStatus(),
        api.getPositions(),
        api.getTrades(50),
        api.getModels(),
        api.getPredictions(),
        api.getTickers(),
        api.getSymbols()
      ]);

      if (h.status === 'fulfilled') setHealth(h.value);
      if (r.status === 'fulfilled') setRiskStatus(r.value);
      if (pData.status === 'fulfilled') {
        setPositions(pData.value.positions);
        setCash(pData.value.cash);
        setEquity(pData.value.equity);
        setUnrealizedPnl(pData.value.total_unrealized_pnl);
      }
      if (tr.status === 'fulfilled') setTrades(tr.value);
      if (m.status === 'fulfilled') setModels(m.value);
      if (pred.status === 'fulfilled') setPredictions(pred.value);
      if (tick.status === 'fulfilled') setTickers(tick.value);
      if (symList.status === 'fulfilled' && symList.value?.length > 0) {
        setSymbols(symList.value);
      }
    } catch (e) {
      console.error('Error fetching initial data:', e);
    }
  }, []);

  // Fetch candles when symbol or timeframe changes
  const fetchCandles = useCallback(async () => {
    try {
      const c = await api.getCandles(selectedSymbol, selectedTimeframe, 80);
      setCandles(c);
    } catch (e) {
      console.error('Error fetching candles:', e);
    }
  }, [selectedSymbol, selectedTimeframe]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Periodic unread notification count check
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await api.getUnreadNotificationCount();
      if (res && typeof res.unread_count === 'number') {
        setUnreadNotificationCount(res.unread_count);
      }
    } catch {
      // Silently ignore if unauthenticated or offline
    }
  }, []);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 15000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  useEffect(() => {
    fetchCandles();
  }, [fetchCandles]);

  // WebSocket Subscription
  useEffect(() => {
    liveWs.connect();

    const checkInterval = setInterval(() => {
      setWsConnected(liveWs.getStatus());
    }, 1000);

    const unsubscribe = liveWs.subscribe((event) => {
      if (event.type === 'SNAPSHOT' && event.data) {
        if (event.data.tickers) setTickers(event.data.tickers);
        if (event.data.equity !== undefined) setEquity(event.data.equity);
        if (event.data.cash !== undefined) setCash(event.data.cash);
        if (event.data.unrealized_pnl !== undefined) setUnrealizedPnl(event.data.unrealized_pnl);
      } else if (event.type === 'TICK') {
        if (event.symbol && event.price) {
          setTickers((prev) => ({
            ...prev,
            [event.symbol]: {
              symbol: event.symbol,
              market_type: event.market_type || 'USDⓈ-M Perp',
              price: event.price,
              change_24h: event.change_24h ?? prev[event.symbol]?.change_24h ?? 0,
              change_24h_abs: event.change_24h_abs ?? prev[event.symbol]?.change_24h_abs ?? 0,
              high_24h: event.high_24h ?? prev[event.symbol]?.high_24h ?? event.price,
              low_24h: event.low_24h ?? prev[event.symbol]?.low_24h ?? event.price,
              volume_24h: event.volume_24h ?? prev[event.symbol]?.volume_24h ?? 0,
              quote_volume_24h: event.quote_volume_24h ?? prev[event.symbol]?.quote_volume_24h ?? 0,
              mark_price: event.mark_price ?? prev[event.symbol]?.mark_price ?? event.price,
              funding_rate: event.funding_rate ?? prev[event.symbol]?.funding_rate ?? 0,
              bid_price: event.bid_price ?? prev[event.symbol]?.bid_price ?? event.price,
              ask_price: event.ask_price ?? prev[event.symbol]?.ask_price ?? event.price,
              spread: event.spread ?? prev[event.symbol]?.spread ?? 0,
              timestamp: event.timestamp || new Date().toISOString(),
              is_stale: event.is_stale ?? false
            }
          }));
        }
        if (event.equity !== undefined) setEquity(event.equity);
        if (event.cash !== undefined) setCash(event.cash);
        if (event.unrealized_pnl !== undefined) setUnrealizedPnl(event.unrealized_pnl);
      } else if (event.type === 'position_opened' || event.type === 'position_closed') {
        api.getPositions().then((p) => {
          setPositions(p.positions);
          setCash(p.cash);
          setEquity(p.equity);
          setUnrealizedPnl(p.total_unrealized_pnl);
        });
        api.getTrades().then(setTrades);
      } else if (event.type === 'prediction') {
        api.getPredictions().then(setPredictions);
      } else if (event.type === 'risk_alert' || event.type === 'cooldown_triggered') {
        api.getRiskStatus().then(setRiskStatus);
      }
    });

    return () => {
      clearInterval(checkInterval);
      unsubscribe();
    };
  }, [selectedSymbol]);

  // Action: Toggle Emergency Kill Switch
  const handleToggleKillSwitch = async () => {
    try {
      const currentActive = riskStatus?.kill_switch_active ?? false;
      const res = await api.toggleKillSwitch(!currentActive, 'User action from UI');
      setRiskStatus((prev) => prev ? { ...prev, kill_switch_active: res.kill_switch_active } : null);
    } catch (e) {
      console.error('Failed to toggle kill switch:', e);
    }
  };

  // Action: Manual Close Position
  const handleClosePosition = async (sym: string) => {
    try {
      await api.closePosition(sym);
      const [posData, trData] = await Promise.all([api.getPositions(), api.getTrades()]);
      setPositions(posData.positions);
      setCash(posData.cash);
      setEquity(posData.equity);
      setUnrealizedPnl(posData.total_unrealized_pnl);
      setTrades(trData);
    } catch (e) {
      console.error(`Failed to close position for ${sym}:`, e);
    }
  };

  // Action: Refresh Models
  const handleRefreshModels = async () => {
    try {
      const m = await api.getModels();
      setModels(m);
    } catch (e) {
      console.error('Error refreshing models:', e);
    }
  };

  const activePosition = positions.find((p) => p.symbol === selectedSymbol);
  const currentPrediction = predictions.find((p) => p.symbol === selectedSymbol) || predictions[0] || null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* Sticky Header Navigation */}
      <Header
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        health={health}
        riskStatus={riskStatus}
        wsConnected={wsConnected}
        onToggleKillSwitch={handleToggleKillSwitch}
        unreadCount={unreadNotificationCount}
        onOpenNotifications={() => setIsNotificationDrawerOpen(true)}
      />

      {/* Main View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {currentTab === 'overview' && (
          <OverviewView
            cash={cash}
            equity={equity}
            unrealizedPnl={unrealizedPnl}
            positions={positions}
            predictions={predictions}
            riskStatus={riskStatus}
            trades={trades}
            tickers={tickers}
            onClosePosition={handleClosePosition}
            onRefresh={loadInitialData}
            onNavigateToNews={() => setCurrentTab('news')}
          />
        )}

        {currentTab === 'news' && (
          <MarketNewsView tickers={tickers} />
        )}

        {currentTab === 'terminal' && (
          <TerminalView
            tickers={tickers}
            selectedSymbol={selectedSymbol}
            onSelectSymbol={setSelectedSymbol}
            onOpenDetail={(sym) => {
              setSelectedSymbol(sym);
              setCurrentTab('market-detail');
            }}
            wsConnected={wsConnected}
          />
        )}

        {currentTab === 'market-detail' && (
          <MarketDetailView
            symbol={selectedSymbol}
            onSymbolChange={setSelectedSymbol}
            symbols={symbols}
            ticker={tickers[selectedSymbol]}
            activePosition={activePosition}
            prediction={currentPrediction}
            onClosePosition={handleClosePosition}
            onRefreshData={loadInitialData}
          />
        )}

        {currentTab === 'models' && (
          <ModelLabView
            models={models}
          />
        )}

        {currentTab === 'training' && (
          <TrainingView
            onTrainingComplete={() => {
              handleRefreshModels();
              api.getPredictions().then(setPredictions);
            }}
          />
        )}

        {currentTab === 'backtest' && (
          <BacktestView />
        )}

        {currentTab === 'risk' && (
          <PortfolioRiskView
            cash={cash}
            equity={equity}
            positions={positions}
            riskStatus={riskStatus}
            onToggleKillSwitch={handleToggleKillSwitch}
            onClosePosition={handleClosePosition}
          />
        )}

        {currentTab === 'journal' && (
          <JournalView trades={trades} />
        )}

        {currentTab === 'settings' && (
          <SettingsView
            health={health}
            riskStatus={riskStatus}
            wsConnected={wsConnected}
          />
        )}
      </main>

      {/* Global Auth Modal */}
      <AuthModal />

      {/* Persistent Notification Drawer */}
      <NotificationDrawer
        isOpen={isNotificationDrawerOpen}
        onClose={() => {
          setIsNotificationDrawerOpen(false);
          fetchUnreadCount();
        }}
        onOpenSettings={() => {
          setIsNotificationDrawerOpen(false);
          setCurrentTab('settings');
        }}
        onUnreadCountChange={setUnreadNotificationCount}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-xs font-mono text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span>Trading AI Research & Paper-Trading Platform</span>
            <span>•</span>
            <span className="text-emerald-500">Paper Engine Active (Zero Live Order Risk)</span>
          </div>
          <div className="flex items-center gap-4">
            <span>UTC Clock: {new Date().toISOString().slice(11, 19)}</span>
            <span>•</span>
            <span className="text-slate-400">Binance Futures Market Data</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
