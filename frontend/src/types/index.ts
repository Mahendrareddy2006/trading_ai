export type TabType = 
  | 'overview' 
  | 'terminal' 
  | 'market-detail'
  | 'news'
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

export interface NewsArticle {
  id: string;
  title: string;
  source: string;
  url: string;
  image_url: string | null;
  summary: string;
  published_at: string;
  categories: string[];
}

export interface NewsFeedResponse {
  status: string;
  total: number;
  count: number;
  limit: number;
  offset: number;
  category: string;
  categories: string[];
  last_updated: string;
  is_stale: boolean;
  articles: NewsArticle[];
}

export interface NotificationSettings {
  user_id: string;
  telegram_enabled: boolean;
  telegram_status: 'NOT_CONFIGURED' | 'VALIDATING' | 'CONNECTED' | 'INVALID_CREDENTIALS' | 'CONFIGURATION_ERROR' | 'PROVIDER_UNAVAILABLE' | string;
  telegram_chat_id_masked: string | null;
  telegram_has_custom_token: boolean;
  telegram_verified: boolean;
  telegram_verified_at: string | null;
  telegram_sender_info: string | null;
  telegram_last_delivery: string | null;
  telegram_last_error: string | null;
  server_telegram_configured: boolean;
  telegram_chat_id?: string;
  telegram_bot_token?: string;

  whatsapp_enabled: boolean;
  whatsapp_status: 'NOT_CONFIGURED' | 'VALIDATING' | 'CONNECTED' | 'INVALID_CREDENTIALS' | 'CONFIGURATION_ERROR' | 'PROVIDER_UNAVAILABLE' | string;
  whatsapp_phone_number_masked: string | null;
  whatsapp_phone_number_id_masked: string | null;
  whatsapp_verified: boolean;
  whatsapp_verified_at: string | null;
  whatsapp_sender_info: string | null;
  whatsapp_last_delivery: string | null;
  whatsapp_last_error: string | null;
  server_whatsapp_configured: boolean;
  whatsapp_provider: string;
  whatsapp_phone_number?: string;

  in_app_enabled: boolean;
  in_app_status: string;
  in_app_verified_at: string | null;

  all_coins: boolean;
  selected_coins: string[];
  available_symbols: string[];

  ml_alerts_enabled: boolean;
  ml_min_confidence: number;
  ml_min_edge: number;
  ml_notify_buy: boolean;
  ml_notify_sell: boolean;
  ml_notify_neutral: boolean;
  ml_timeframes: string[];

  news_alerts_enabled: boolean;
  news_categories: string[];

  risk_alerts_enabled: boolean;
  notify_circuit_breaker: boolean;
  notify_daily_loss: boolean;
  notify_drawdown: boolean;
  notify_consecutive_losses: boolean;
  notify_service_health: boolean;

  delivery_mode: string;
  summary_frequency: string;
  summary_time: string;
  summary_timezone: string;
  last_summary_sent_at: string | null;

  env_writable?: boolean;
  is_cloud?: boolean;
  platform?: string;
}

export interface ConfigureWhatsAppPayload {
  api_token: string;
  phone_number_id: string;
  recipient_phone?: string;
  provider?: string;
  save_to_local_env?: boolean;
}

export interface ConfigureTelegramPayload {
  bot_token: string;
  chat_id?: string;
  save_to_local_env?: boolean;
}

export interface ChannelConfigureResponse {
  status: string;
  verified: boolean;
  verified_at: string;
  sender_info: string;
  message: string;
  env_updated: boolean;
  env_message: string;
}

export interface PriceAlertRule {
  id: string;
  user_id: string;
  symbol: string;
  condition_type: 'entering_range' | 'exiting_range' | 'crossing_up' | 'crossing_down';
  lower_boundary: number | null;
  upper_boundary: number | null;
  target_price: number | null;
  channels: string;
  is_active: boolean;
  last_evaluated_price: number | null;
  last_state: string | null;
  last_triggered_at: string | null;
  cooldown_seconds: number;
  created_at: string;
}

export interface InAppNotification {
  id: string;
  title: string;
  message: string;
  category: 'ml_signal' | 'price_alert' | 'market_news' | 'risk_event' | 'system';
  severity: 'info' | 'success' | 'warning' | 'critical';
  symbol: string | null;
  metadata: Record<string, any>;
  is_read: boolean;
  created_at: string;
}

export interface DeliveryLog {
  id: string;
  channel: string;
  category: string;
  status: string;
  recipient: string;
  error_message: string | null;
  payload_preview: string | null;
  created_at: string;
}



