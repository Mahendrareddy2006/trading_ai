# 🚀 Trading AI — Crypto Market Analytics & Paper Trading Platform

An AI-powered cryptocurrency market analysis platform built with Python, FastAPI, React, and machine learning. It combines multi-timeframe market analysis, real-time market monitoring, risk analytics, and configurable notifications in a unified dashboard.

## ✨ Features

- 📊 **Multi-Timeframe Analysis** — Analyze market trends across 5-minute, 1-hour, and 4-hour timeframes.
- 📈 **Live Market Terminal** — Monitor cryptocurrency market prices and market movements.
- 🧠 **Machine Learning Signals** — Generate model-based market signals with configurable confidence thresholds.
- 📰 **Crypto Market News** — View cryptocurrency news and market developments.
- 🔔 **Multi-Channel Notifications** — Configurable alerts through Telegram, WhatsApp Business, and in-app notifications, depending on provider configuration.
- 🎯 **Price Alerts** — Configure alerts for selected coins and target price levels.
- 🛡️ **Risk Management** — Review risk metrics and portfolio information.
- 🧪 **Paper Trading** — Test strategies without placing live trades.
- ⚙️ **Settings & Integrations** — Manage notification preferences and supported exchange connections.
- 🧾 **Testing & Deployment** — Includes backend tests and deployment configuration.

## 🛠️ Tech Stack

**Backend**
- Python
- FastAPI
- Pandas
- Scikit-learn
- SQLAlchemy

**Frontend**
- React
- TypeScript
- Vite

**Integrations & Infrastructure**
- Binance USDⓈ-M Futures market data
- Telegram Bot API
- WhatsApp Business Cloud API / supported provider integration
- SQLite or configured database
- Vercel (frontend deployment)
- Render (backend deployment)

## 🏗️ Architecture

- **Frontend:** Interactive dashboard for market monitoring, analytics, and notification settings.
- **Backend:** FastAPI services for market data, analytics, APIs, and notification dispatch.
- **Machine Learning:** Model-based analysis and signal generation.
- **Notification System:** Routes configured alerts to supported delivery channels.
- **Deployment:** Frontend and backend can be deployed independently.

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Mahendrareddy2006/trading_ai.git
cd trading_ai
```

### 2. Set up the Python environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a local `.env` file using `.env.example` as a reference. Add only the credentials and settings required by the integrations you intend to use.

Keep all API keys, tokens, passwords, and other secrets out of Git. Never expose backend credentials in frontend code.

### 4. Run the application

Use the startup command documented for the current project configuration. For example, if `run.py` is the configured entry point:

```bash
python run.py
```

Run the frontend separately using the scripts defined in `frontend/package.json`.

## 🧪 Testing

Run the available backend tests with:

```bash
python -m pytest
```

Run frontend checks using the scripts defined in `frontend/package.json`.

## ☁️ Deployment

The intended deployment setup is:

- **Frontend:** Vercel
- **Backend:** Render

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for project-specific deployment instructions and required environment variables.

## 🔐 Security & Trading Safety

- Paper trading is the intended operating mode.
- Market signals are informational and are not guarantees of future performance.
- Never commit `.env` files, API secrets, access tokens, or passwords.
- Use restricted exchange API permissions and trusted IP restrictions where supported.
- Configure notification providers on the backend; do not expose provider credentials to the browser.
- Verify that each external integration is configured and tested before relying on it.

## 📦 Machine Learning Models

Trained model files (`.pkl`) may not be included in the repository because of their size. Follow the project's training instructions or configure the required model files locally before using features that depend on them.

## ⚠️ Disclaimer

This project is intended for educational, analytical, and experimental use. Cryptocurrency markets are volatile. Model predictions can be wrong, and this software does not guarantee profits or provide financial advice. Paper-trading results do not guarantee real-market performance.

## 👨‍💻 Author

**Mahendra Reddy**

GitHub: [@Mahendrareddy2006](https://github.com/Mahendrareddy2006)
