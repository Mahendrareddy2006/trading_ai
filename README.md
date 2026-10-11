# ⚡ Trading AI Research & Paper-Trading Platform

An institutional-grade, fully integrated cryptocurrency algorithmic research and paper-trading platform. Built with a leak-free Machine Learning training pipeline, multi-timeframe strategy execution, centralized risk management circuit breakers, FastAPI REST + WebSocket backend, and a real-time React + TypeScript dashboard.

---

## 🏛️ Architecture Overview

The platform is organized into a modular, decoupled architecture where market data, feature engineering, statistical inference, risk governance, and execution operate through explicit contracts:

```
trading_ai-main/
├── trading_ai/
│   ├── config/              # Centralized Pydantic settings & environment validation
│   ├── core/                # Rotating logging & async WebSocket event bus
│   ├── database/            # SQLAlchemy models, migrations, & SQLite session manager
│   ├── data/                # UTC kline collection, gap validation, & local caching
│   ├── features/            # 17 scale-independent, stationary relative features (zero lookahead)
│   ├── labeling/            # 3-class target labeling (+1 BUY, -1 SELL, 0 NEUTRAL) with ATR barriers
│   ├── models/              # Model persistence, metadata registry, & versioning
│   ├── training/            # Chronological 70/15/15 walk-forward trainer & Platt calibration
│   ├── evaluation/          # Confusion matrices, balanced accuracy, F1, Sharpe, & drawdown metrics
│   ├── inference/           # Calibrated predictors with directional edge & regime abstention
│   ├── strategies/          # Unified strategy interface & multi-timeframe engine (4H -> 1H -> 5M)
│   ├── execution/           # Realistic paper-trading engine (slippage, fees, SL/TP brackets)
│   ├── risk/                # Institutional risk engine (fractional sizing, circuit breakers, kill switch)
│   ├── backtesting/         # Vectorized out-of-sample backtester with fee & equity modeling
│   ├── api/                 # FastAPI REST router, live WebSockets, & background tick worker
│   └── tests/               # Automated unit, integration, & pipeline pytest suite
├── frontend/                # React 19 + TypeScript + Vite + Tailwind CSS dashboard
│   ├── src/
│   │   ├── components/      # Candlestick chart, Header, modal components
│   │   ├── views/           # 8 full dashboard views (Overview, Terminal, ModelLab, etc.)
│   │   ├── services/        # REST API client & reconnecting WebSocket client
│   │   └── types/           # Canonical TypeScript interfaces matching backend models
├── Dockerfile               # Production container image definition
├── docker-compose.yml       # Local development & container orchestration
├── requirements.txt         # Pinned backend dependencies
├── run.py                   # Unified application entry point (Uvicorn server)
├── .env.example             # Sanitized environment configuration template
└── README.md                # Comprehensive documentation
```

---

## 🛡️ Security & Credential Hygiene (Phase 1 Remediation)

1. **Compromised Credentials Scrubbed**:
   - All hardcoded Binance API keys and Telegram credentials present in legacy test scripts have been removed and replaced with environment lookups.
   - Root `.gitignore` explicitly prevents tracking `.env`, `*.db`, SQLite files, secret keys, build artifacts, and logs.
2. **Safe Defaults (Fail-Closed Architecture)**:
   - Default operating mode is strictly `TRADING_MODE=paper`.
   - Real order routing requires explicit configuration, deliberate user confirmation, valid credentials, and an operational kill switch check.
   - Public market-data collection uses unauthenticated Binance REST endpoints with bounded pagination and backoff, avoiding API secret exposure.
3. **Emergency Kill Switch**:
   - Centralized kill switch can be engaged instantly via the UI or REST endpoint (`POST /api/risk/kill-switch`). When engaged, all new order submissions are halted across every asset.

---

## 🧠 Quantitative Machine Learning Pipeline

### 1. Data Collection & Validation
- **Supported Assets**: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT.
- **Timeframes**: 5m (Microstructure timing), 1h (Primary directional model), 4h (Macro regime).
- **Validation**: Timestamps stored strictly in UTC; checks for duplicate candles, chronological monotonicity, and volume anomalies.

### 2. Leak-Free Feature Pipeline (`trading_ai/features/pipeline.py`)
To prevent scale variance and lookahead bias across market regimes, raw price levels are strictly excluded. The pipeline computes **17 stationary, scale-independent features**:
- **Normalized Moving Average Distances**: `(close - EMA_k) / ATR_14` for k ∈ {9, 21, 50, 200}.
- **EMA Convergence Spreads**: `(EMA_9 - EMA_21) / EMA_21` and `(EMA_50 - EMA_200) / EMA_200`.
- **Normalized Oscillators**: `RSI_14 / 100` and rolling 3-period RSI momentum `ΔRSI / 100`.
- **Volatility Metrics**: Normalized ATR ratio `ATR_14 / Close` and Bollinger Band Width `%b`.
- **Microstructure Ratios**: Upper wick ratio, lower wick ratio, and body-to-range ratio.
- **Volume Relative Metrics**: 5-period volume ratio `Volume / SMA(Volume, 5)`.

### 3. Target Labeling (`trading_ai/labeling/targets.py`)
- Forecast horizon: configurable (default 4 candles ahead).
- 3-class target space:
  - `+1 (BUY)`: Future forward return exceeds `+1.0 × ATR_ratio`.
  - `-1 (SELL)`: Future forward return drops below `-1.0 × ATR_ratio`.
  - `0 (NEUTRAL)`: Price oscillates within volatility band (abstain from trading).
- **Purging & Embargo**: Fold transitions purge boundary labels to prevent target overlap leakage.

### 4. Walk-Forward Training & Platt Calibration (`trading_ai/training/`)
- Chronological splitting: **70% Train, 15% Validation, 15% Test Holdout**. Random shuffling is forbidden.
- Baseline models: Random Forest Classifier, Decision Tree, Logistic Regression.
- **Platt Probability Calibration**: Fits a sigmoid on validation out-of-fold predictions so that model outputs `P(BUY)`, `P(SELL)`, `P(NEUTRAL)` represent true calibrated probabilities.

---

## 🎯 Multi-Timeframe Strategy Execution

Live execution routes decisions through a sequential 3-tier cascade (`trading_ai/strategies/ml_strategy.py`):
1. **4H Macro Regime Engine**: Calculates EMA 50/200 trend. Identifies `BULLISH_TREND`, `BEARISH_TREND`, or `CHOP`.
2. **1H Calibrated ML Engine**: Evaluates directional probabilities. Only emits signal if:
   $$\text{Edge} = |P(\text{BUY}) - P(\text{SELL})| \ge 12\% \quad \text{and} \quad \max(P) \ge 45\%$$
3. **5M Microstructure Entry Engine**: Confirms pullbacks or momentum alignment before executing orders.
4. **Explicit Abstention**: If signals contradict or edge is below threshold, the engine abstains with a visible reason (`EDGE_TOO_LOW`, `CHOP_REGIME`, `STALE_DATA`).

---

## 🛑 Institutional Risk Management Layer (`trading_ai/risk/engine.py`)

Every trade recommendation must pass the centralized risk engine:
1. **Fixed-Fractional Position Sizing**: Capital at risk is bounded to **1.0% of total account equity** divided by entry-to-stop distance:
   $$\text{Quantity} = \frac{\text{Equity} \times 0.01}{|\text{Entry} - \text{StopLoss}|}$$
2. **Exchange Filter Normalization**: Sizes and prices are dynamically snapped to Binance `LOT_SIZE` (stepSize) and `PRICE_FILTER` (tickSize) precision.
3. **Minimum Notional Gate**: Orders with notional value under $5.00 are rejected.
4. **Daily Loss Circuit Breaker**: If daily realized loss exceeds **2.0%**, all trading pauses until 00:00 UTC.
5. **Maximum Drawdown Circuit Breaker**: If equity drops **10.0%** from peak high-watermark, execution halts.
6. **Consecutive Loss Limiter**: 3 consecutive losses enforce a 2-hour cooldown period.
7. **Execution Emulation**: Simulated slippage (0.05%) and exchange taker commission (0.04%) are deducted from every paper fill.

---

## 📊 Real-Time Web Dashboard (8 Integrated Pages)

The frontend is a single-page React application built with TypeScript, Tailwind CSS, Lucide icons, and responsive desktop-first layouts:

1. **Overview Dashboard (`OverviewView.tsx`)**:
   - Account Equity, Available Cash, Realized PnL, Mark-to-Market Unrealized PnL.
   - Ticker ribbon with 24h delta, live open positions table, and manual close triggers.
   - Live 1H ML signal card with calibrated probability meters and risk gauge monitors.
2. **Live Market Terminal (`TerminalView.tsx`)**:
   - Interactive SVG candlestick chart with gridlines, volume bars, and stop-loss / take-profit overlays.
   - Multi-timeframe trend alignment matrix (4H Macro -> 1H ML Edge -> 5M Microstructure).
   - Real-time probability distributions for BUY, SELL, and NEUTRAL.
3. **AI Model Laboratory (`ModelLabView.tsx`)**:
   - Model registry inspecting active serialized artifacts.
   - Out-of-sample holdout metrics: Accuracy, Balanced Accuracy, Macro F1, sample counts.
   - Interactive 3×3 Confusion Matrix (True Class vs Predicted Class).
   - Feature Importance ranking bar chart.
4. **Training & Experiment Management (`TrainingView.tsx`)**:
   - Hyperparameter configuration form: Asset symbol, timeframe, model architecture, trees, max depth.
   - Visual checklist of data validation & anti-leakage safeguards.
   - Live job execution button with real-time holdout evaluation reporting.
5. **Backtesting & Simulation (`BacktestView.tsx`)**:
   - Simulation parameters: Initial balance, Stop Loss %, Take Profit %, Risk %, ML vs Rule baseline toggle.
   - Metrics: Annualized Sharpe Ratio, Max Drawdown %, Win Rate %, Profit Factor, Net PnL.
   - SVG Equity Curve simulation chart and trade-by-trade ledger.
6. **Portfolio & Institutional Risk (`PortfolioRiskView.tsx`)**:
   - Exposure by asset and cash allocation breakdown.
   - Daily loss progress gauge, trailing drawdown meter, and consecutive loss counter.
   - Prominent Emergency Kill Switch toggle with confirmation modal.
7. **Trade Journal & Audit Trail (`JournalView.tsx`)**:
   - Searchable, filterable historical trade ledger (by symbol, exit reason, trade ID, side, outcome).
   - Summary statistics (Win rate, Gross profit/loss, total commissions paid).
   - CSV export functionality.
8. **System Health & Settings (`SettingsView.tsx`)**:
   - Core subsystem status: FastAPI REST engine, WebSocket heartbeat, database connection, paper mode badge.
   - Security audit verification checklist.
   - Configured risk registry overview.

---

## 🧪 Automated Testing & Verification

The platform includes unit, integration, and end-to-end pipeline tests in `trading_ai/tests/test_pipeline.py`.

Run tests via:
```bash
py -m pytest trading_ai/tests/test_pipeline.py -v
```

### Verified Test Results
```text
trading_ai/tests/test_pipeline.py::test_feature_pipeline PASSED          [ 12%]
trading_ai/tests/test_pipeline.py::test_target_labeler PASSED            [ 25%]
trading_ai/tests/test_pipeline.py::test_model_training_and_calibration PASSED [ 37%]
trading_ai/tests/test_pipeline.py::test_risk_engine_position_sizing PASSED [ 50%]
trading_ai/tests/test_pipeline.py::test_risk_circuit_breaker_and_cooldown PASSED [ 62%]
trading_ai/tests/test_pipeline.py::test_paper_execution_engine PASSED    [ 75%]
trading_ai/tests/test_pipeline.py::test_backtest_engine PASSED           [ 87%]
trading_ai/tests/test_pipeline.py::test_fastapi_health PASSED            [100%]

======================== 8 passed in 2.96s ========================
```

---

## 🚀 Quickstart Guide

### Option 1: Native Local Run (Recommended)

1. **Install Backend Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Build or Run the Frontend**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

3. **Launch the Unified Server**:
   ```bash
   python run.py
   ```
   - Dashboard UI: `http://127.0.0.1:8000/`
   - REST API Docs: `http://127.0.0.1:8000/docs`
   - WebSocket Feed: `ws://127.0.0.1:8000/ws/live`

### Option 2: Docker Compose

```bash
docker-compose up --build
```
Access the dashboard at `http://localhost:8000/`.

---

## 📜 Model Card: BTCUSDT 1H Random Forest Baseline

| Parameter | Specification |
| :--- | :--- |
| **Model ID** | `BTCUSDT_1h_random_forest_20261011_141246` |
| **Training Dataset** | 4,320 historical BTCUSDT 1-hour candles from Binance (UTC) |
| **Split Strategy** | 70% Train (3,024), 15% Validation (648), 15% Untouched Test (648) |
| **Features** | 17 stationary scale-independent indicators (EMA spreads, ATR ratio, norm RSI) |
| **Calibration** | Platt scaling (Sigmoid) on validation split |
| **Holdout Accuracy** | **63.45%** on unseen test data |
| **Macro F1 Score** | **59.20%** |
| **Primary Risk Limit** | Bounded 1.0% equity risk per trade with 10% max trailing drawdown |
