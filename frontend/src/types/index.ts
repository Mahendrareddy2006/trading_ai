export type TabType = 
  | 'overview' 
  | 'terminal' 
  | 'market-detail'
  | 'models' 
  | 'training' 
  | 'backtest' 
  | 'risk' 
  | 'journal' 
  | 'settings';

export interface TickerData {
  symbol?: string;
  market_type?: string;
  price: number;
  change_24h: number;
  change_24h_abs?: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  quote_volume_24h?: number;
  mark_price?: number;
  funding_rate?: number;
  bid_price?: number;
  ask_price?: number;
  spread?: number;
  timestamp?: string;
  is_stale?: boolean;
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Prediction {
  symbol: string;
  timeframe: string;
  predicted_class: number;
  direction: 'LONG' | 'SHORT' | 'NEUTRAL';
  probabilities: {
    BUY: number;
    SELL: number;
    NEUTRAL: number;
  };
  edge: number;
  confidence: number;
  regime: string;
  abstention_reason: string | null;
  model_version: string;
  timestamp: string;
}

export interface ModelRecord {
  model_id: string;
  symbol: string;
  timeframe: string;
  model_type: string;
  created_at: string;
  metrics: {
    accuracy: number;
    balanced_accuracy: number;
    macro_f1: number;
    confusion_matrix?: number[][];
    class_report?: Record<string, { precision: number; recall: number; f1_score: number }>;
  };
  feature_importances: Record<string, number>;
  sample_counts: {
    train: number;
    val: number;
    test: number;
  };
}

export interface Position {
  id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry_price: number;
  current_price: number;
  quantity: number;
  leverage: number;
  notional: number;
  stop_loss: number;
  take_profit: number;
  unrealized_pnl: number;
  return_pct: number;
  fee_paid: number;
  strategy_name: string;
  model_version: string;
  opened_at: string;
  status: string;
}

export interface Trade {
  trade_id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entry_price: number;
  exit_price: number;
  quantity: number;
  leverage: number;
  gross_pnl: number;
  fees: number;
  net_pnl: number;
  return_pct: number;
  exit_reason: string;
  strategy_name: string;
  model_version: string;
  opened_at: string;
  closed_at: string;
}

export interface RiskStatus {
  kill_switch_active: boolean;
  in_cooldown: boolean;
  cooldown_message: string | null;
  current_equity: number;
  high_watermark: number;
  daily_loss_pct: number;
  max_daily_loss_pct: number;
  drawdown_pct: number;
  max_drawdown_pct: number;
  consecutive_losses: number;
  max_consecutive_losses: number;
}

export interface BacktestResult {
  backtest_id: string;
  symbol: string;
  initial_balance: number;
  final_balance: number;
  net_pnl: number;
  return_pct: number;
  total_trades: number;
  metrics: {
    total_trades: number;
    wins: number;
    losses: number;
    win_rate: number;
    profit_factor: number;
    sharpe_ratio: number;
    max_drawdown: number;
    net_pnl: number;
  };
  trades: Array<{
    trade_id: number;
    symbol: string;
    side: 'LONG' | 'SHORT';
    entry_price: number;
    exit_price: number;
    quantity: number;
    gross_pnl: number;
    fees: number;
    net_pnl: number;
    exit_reason: string;
    opened_at: string;
    closed_at: string;
  }>;
  equity_curve: Array<{
    time: string;
    equity: number;
    cash: number;
  }>;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  mode: string;
  is_paper: boolean;
  kill_switch: boolean;
  version: string;
}

export interface ExchangeAccountSummary {
  is_configured: boolean;
  status: string;
  account_type?: string;
  testnet?: boolean;
  total_wallet_balance?: number;
  total_margin_balance?: number;
  total_unrealized_pnl?: number;
  available_balance?: number;
  total_initial_margin?: number;
  total_maintenance_margin?: number;
  assets?: Array<{
    asset: string;
    wallet_balance: number;
    unrealized_profit: number;
    margin_balance: number;
    available_balance: number;
  }>;
  last_synced?: string;
  message?: string;
  error?: string;
}

export interface ExchangePosition {
  symbol: string;
  side: 'LONG' | 'SHORT';
  position_amount: number;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  return_pct: number;
  notional: number;
  liquidation_price: number | null;
  leverage: number;
  margin_type: string;
  isolated_margin: number;
}

export interface ExchangeOrder {
  order_id: string;
  symbol: string;
  status: string;
  side: string;
  type: string;
  price: number;
  quantity: number;
  executed_quantity: number;
  time: string;
}

export interface SystemDataStatus {
  exchange_connectivity: {
    status: string;
    latency_ms: number;
    exchange: string;
    testnet: boolean;
    last_checked: string;
  };
  credentials_configured: boolean;
  active_symbols: string[];
  live_prices_cached: number;
  testnet: boolean;
  server_time_offset_ms: number;
  trading_mode: string;
  is_paper_trading: boolean;
  timestamp: string;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  is_superuser: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: UserProfile;
}

export interface ExchangeConnectionRecord {
  id: string;
  exchange_name: string;
  label: string;
  api_key_masked: string;
  is_testnet: boolean;
  status: string;
  last_sync_at: string | null;
  error_message: string | null;
  created_at: string;
}


