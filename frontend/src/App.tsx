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
import { Header } from './components/Header';
import { OverviewView } from './views/OverviewView';
import { TerminalView } from './views/TerminalView';
import { ModelLabView } from './views/ModelLabView';
import { TrainingView } from './views/TrainingView';
import { BacktestView } from './views/BacktestView';
import { PortfolioRiskView } from './views/PortfolioRiskView';
import { JournalView } from './views/JournalView';
import { SettingsView } from './views/SettingsView';

export function App() {
  const [currentTab, setCurrentTab] = useState<TabType>('overview');
  const [wsConnected, setWsConnected] = useState(false);

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

  // Selected symbol & timeframe for terminal
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');

  // Load Initial API Data
  const loadInitialData = useCallback(async () => {
    try {
      const [h, r, pData, tr, m, pred, tick] = await Promise.allSettled([
        api.getHealth(),
        api.getRiskStatus(),
        api.getPositions(),
        api.getTrades(50),
        api.getModels(),
        api.getPredictions(),
        api.getTickers()
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
              price: event.price,
              change_24h: event.change_24h ?? prev[event.symbol]?.change_24h ?? 0,
              high_24h: event.high_24h ?? prev[event.symbol]?.high_24h ?? event.price,
              low_24h: event.low_24h ?? prev[event.symbol]?.low_24h ?? event.price,
              volume_24h: event.volume_24h ?? prev[event.symbol]?.volume_24h ?? 0,
            }
          }));
        }
        if (event.equity !== undefined) setEquity(event.equity);
        if (event.cash !== undefined) setCash(event.cash);
        if (event.unrealized_pnl !== undefined) setUnrealizedPnl(event.unrealized_pnl);

        // Refresh candles if tick matches selected symbol
        if (event.symbol === selectedSymbol) {
          fetchCandles();
        }
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
  }, [selectedSymbol, fetchCandles]);

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
          />
        )}

        {currentTab === 'terminal' && (
          <TerminalView
            candles={candles}
            symbol={selectedSymbol}
            timeframe={selectedTimeframe}
            onSymbolChange={setSelectedSymbol}
            onTimeframeChange={setSelectedTimeframe}
            prediction={currentPrediction}
            activePosition={activePosition}
            ticker={tickers[selectedSymbol]}
            onClosePosition={handleClosePosition}
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

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-xs font-mono text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span>Trading AI Research & Execution Platform</span>
            <span>•</span>
            <span className="text-emerald-500">Paper Trading Engine Active</span>
          </div>
          <div className="flex items-center gap-4">
            <span>UTC Clock: {new Date().toISOString().slice(11, 19)}</span>
            <span>•</span>
            <span className="text-slate-400">Strict Anti-Leakage Protocol</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
