export type TabType = 
  | 'overview' 
  | 'terminal' 
  | 'models' 
  | 'training' 
  | 'backtest' 
  | 'risk' 
  | 'journal' 
  | 'settings';

export interface TickerData {
  price: number;
  change_24h: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
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
