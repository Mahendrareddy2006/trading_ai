import {
  BacktestResult,
  Candle,
  ModelRecord,
  Position,
  Prediction,
  RiskStatus,
  SystemHealth,
  Trade
} from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export const api = {
  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async getConfig(): Promise<any> {
    const res = await fetch(`${API_BASE}/config`);
    if (!res.ok) throw new Error('Failed to fetch config');
    return res.json();
  },

  async getSymbols(): Promise<string[]> {
    const res = await fetch(`${API_BASE}/market/symbols`);
    if (!res.ok) throw new Error('Failed to fetch symbols');
    const data = await res.json();
    return data.symbols;
  },

  async getCandles(symbol: string, timeframe: string, limit = 100): Promise<Candle[]> {
    const res = await fetch(`${API_BASE}/market/candles?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch candles');
    const data = await res.json();
    return data.candles;
  },

  async getPredictions(): Promise<Prediction[]> {
    const res = await fetch(`${API_BASE}/predictions/latest`);
    if (!res.ok) throw new Error('Failed to fetch predictions');
    const data = await res.json();
    return data.predictions;
  },

  async getModels(): Promise<ModelRecord[]> {
    const res = await fetch(`${API_BASE}/models`);
    if (!res.ok) throw new Error('Failed to fetch models');
    const data = await res.json();
    return data.models;
  },

  async startTraining(params: {
    symbol: string;
    timeframe: string;
    model_type: string;
    n_estimators: number;
    max_depth: number;
  }): Promise<{ status: string; job_id: string }> {
    const res = await fetch(`${API_BASE}/training/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) throw new Error('Failed to start training');
    return res.json();
  },

  async runBacktest(params: {
    symbol: string;
    timeframe: string;
    initial_balance: number;
    sl_pct: number;
    tp_pct: number;
    risk_per_trade: number;
    use_ml_model: boolean;
  }): Promise<BacktestResult> {
    const res = await fetch(`${API_BASE}/backtest/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Backtest failed');
    }
    return res.json();
  },

  async getPositions(): Promise<{
    positions: Position[];
    cash: number;
    equity: number;
    total_unrealized_pnl: number;
  }> {
    const res = await fetch(`${API_BASE}/positions`);
    if (!res.ok) throw new Error('Failed to fetch positions');
    return res.json();
  },

  async closePosition(symbol: string): Promise<any> {
    const res = await fetch(`${API_BASE}/positions/${symbol}/close`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to close position for ${symbol}`);
    return res.json();
  },

  async getTrades(limit = 50): Promise<Trade[]> {
    const res = await fetch(`${API_BASE}/trades?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch trades');
    const data = await res.json();
    return data.trades;
  },

  async getRiskStatus(): Promise<RiskStatus> {
    const res = await fetch(`${API_BASE}/risk/status`);
    if (!res.ok) throw new Error('Failed to fetch risk status');
    return res.json();
  },

  async toggleKillSwitch(active: boolean, reason?: string): Promise<{ kill_switch_active: boolean }> {
    const res = await fetch(`${API_BASE}/risk/kill-switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active, reason })
    });
    if (!res.ok) throw new Error('Failed to toggle kill switch');
    return res.json();
  }
};
