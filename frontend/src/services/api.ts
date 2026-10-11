import {
  AuthResponse,
  BacktestResult,
  Candle,
  ExchangeAccountSummary,
  ExchangeConnectionRecord,
  ExchangeOrder,
  ExchangePosition,
  ModelRecord,
  Position,
  Prediction,
  RiskStatus,
  SystemDataStatus,
  SystemHealth,
  TickerData,
  Trade,
  UserProfile
} from '../types';

export const getApiBaseUrl = (): string => {
  const envUrl = (import.meta as any).env?.VITE_API_BASE_URL;
  if (envUrl) {
    return envUrl.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined' && window.location.origin.includes('localhost')) {
    return 'http://127.0.0.1:8000/api';
  }
  return '/api';
};

const API_BASE = getApiBaseUrl();

export function getAuthHeaders(includeContentType = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeContentType) {
    headers['Content-Type'] = 'application/json';
  }
  const token = typeof window !== 'undefined' ? localStorage.getItem('trading_ai_token') : null;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  // System & Health
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

  async getTickers(): Promise<Record<string, TickerData>> {
    const res = await fetch(`${API_BASE}/market/tickers`);
    if (!res.ok) throw new Error('Failed to fetch tickers');
    const data = await res.json();
    return data.tickers || {};
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
      headers: getAuthHeaders(true),
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
      headers: getAuthHeaders(true),
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
      method: 'POST',
      headers: getAuthHeaders(false)
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
      headers: getAuthHeaders(true),
      body: JSON.stringify({ active, reason })
    });
    if (!res.ok) throw new Error('Failed to toggle kill switch');
    return res.json();
  },

  // Exchange Read-Only Account Endpoints (Scoped to authenticated user)
  async getExchangeAccountSummary(): Promise<ExchangeAccountSummary> {
    const res = await fetch(`${API_BASE}/account/summary`, {
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error('Failed to fetch exchange account summary');
    return res.json();
  },

  async getExchangePositions(): Promise<{ positions: ExchangePosition[]; is_configured: boolean; error: string | null }> {
    const res = await fetch(`${API_BASE}/account/positions`, {
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error('Failed to fetch exchange positions');
    return res.json();
  },

  async getExchangeOpenOrders(): Promise<{ orders: ExchangeOrder[]; is_configured: boolean; error: string | null }> {
    const res = await fetch(`${API_BASE}/account/open-orders`, {
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error('Failed to fetch exchange open orders');
    return res.json();
  },

  async getSystemDataStatus(): Promise<SystemDataStatus> {
    const res = await fetch(`${API_BASE}/system/data-status`);
    if (!res.ok) throw new Error('Failed to fetch system data status');
    return res.json();
  },

  // Authentication Endpoints
  async login(usernameOrEmail: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email: usernameOrEmail, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
      throw new Error(err.detail || 'Invalid username or password');
    }
    return res.json();
  },

  async register(username: string, email: string, password: string): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }
    return res.json();
  },

  async getMe(): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error('Session expired or unauthorized');
    return res.json();
  },

  async logout(): Promise<void> {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(false)
    }).catch(() => {});
  },

  // Exchange Connection Management (User-Scoped)
  async getExchangeConnections(): Promise<ExchangeConnectionRecord[]> {
    const res = await fetch(`${API_BASE}/exchange/connections`, {
      headers: getAuthHeaders(false)
    });
    if (!res.ok) {
      if (res.status === 401) return [];
      throw new Error('Failed to fetch exchange connections');
    }
    const data = await res.json();
    return data.connections || [];
  },

  async connectExchange(payload: {
    exchange?: string;
    label?: string;
    api_key: string;
    api_secret: string;
    testnet?: boolean;
  }): Promise<{ status: string; connection_id: string; message: string }> {
    const res = await fetch(`${API_BASE}/exchange/connect`, {
      method: 'POST',
      headers: getAuthHeaders(true),
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to connect exchange' }));
      throw new Error(err.detail || 'Connection validation failed');
    }
    return res.json();
  },

  async deleteExchangeConnection(connectionId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/exchange/connections/${connectionId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error('Failed to remove exchange connection');
  },

  async syncExchangeConnection(connectionId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/exchange/connections/${connectionId}/sync`, {
      method: 'POST',
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error('Failed to synchronize exchange credentials');
    return res.json();
  },

  // User Watchlist & Favorites
  async getWatchlist(): Promise<string[]> {
    const res = await fetch(`${API_BASE}/watchlist`, {
      headers: getAuthHeaders(false)
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.symbols || [];
  },

  async addToWatchlist(symbol: string): Promise<string[]> {
    const res = await fetch(`${API_BASE}/watchlist/${symbol}`, {
      method: 'POST',
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error(`Failed to add ${symbol} to watchlist`);
    const data = await res.json();
    return data.symbols || [];
  },

  async removeFromWatchlist(symbol: string): Promise<string[]> {
    const res = await fetch(`${API_BASE}/watchlist/${symbol}`, {
      method: 'DELETE',
      headers: getAuthHeaders(false)
    });
    if (!res.ok) throw new Error(`Failed to remove ${symbol} from watchlist`);
    const data = await res.json();
    return data.symbols || [];
  }
};
