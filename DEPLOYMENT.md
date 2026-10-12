# Trading AI Platform — Production Deployment Guide

This guide provides step-by-step instructions for deploying the **Trading AI Platform** to **Render** (FastAPI backend) and **Vercel** (React/Vite SPA frontend) in private, secure, paper-trading mode.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │             Vercel (Frontend)           │
                      │  - Single Page Application (React/Vite) │
                      │  - Environment: VITE_API_BASE_URL       │
                      │  - SPA Rewrites via vercel.json         │
                      └────────────────────┬────────────────────┘
                                           │ HTTPS (REST API)
                                           │ WSS (Live Stream)
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │             Render (Backend)            │
                      │  - FastAPI Web Service on 0.0.0.0:$PORT │
                      │  - Health Check: /api/health            │
                      │  - Strict CORS Allowlist for Vercel     │
                      │  - Paper-Trading Virtual Risk Sandbox   │
                      └────────────┬───────────────┬────────────┘
                                   │               │
                 Official Bot API  ▼               ▼  Meta Graph API v18.0
                      ┌──────────────────┐   ┌───────────────────────────┐
                      │   Telegram Bot   │   │  WhatsApp Business Cloud  │
                      │   Alert Channel  │   │       Alert Channel       │
                      └──────────────────┘   └───────────────────────────┘
```

---

## Pre-Deployment Git & Security Verification

Before pushing to a remote Git repository:

1. **Verify that secrets are not tracked by Git:**
   ```bash
   git status --ignored
   ```
   Confirm that `.env`, `*.db`, `node_modules/`, and `dist/` remain ignored.

2. **Verify no credentials in git diff:**
   ```bash
   git diff --staged
   ```

3. **Push to a Private Git Repository:**
   ```bash
   git remote add origin https://github.com/your-username/trading_ai.git
   git branch -M main
   git push -u origin main
   ```
   *(Ensure the repository visibility is set to **Private**).*

---

## Part 1: Backend Deployment on Render

### Step 1: Create the Web Service
1. Sign in to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your private repository (`trading_ai`).
4. Select or confirm the service settings:
   - **Name:** `trading-ai-backend`
   - **Region:** `Oregon (US West)` (or your preferred region)
   - **Branch:** `main`
   - **Root Directory:** *(leave blank — repository root)*
   - **Runtime:** `Python`
   - **Build Command:** `pip install --no-cache-dir -r requirements.txt`
   - **Start Command:** `uvicorn trading_ai.api.app:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Plan:** `Starter` (or higher)

### Step 2: Configure Health Check Path
Under **Advanced Settings**:
- **Health Check Path:** `/api/health`

### Step 3: Configure Render Environment Variables
Under the **Environment** tab of your Render service, add the following variables:

| Variable Name | Example / Format | Required | Purpose |
|---|---|---|---|
| `PYTHON_VERSION` | `3.12.0` | Yes | Supported Python version |
| `TRADING_MODE` | `paper` | Yes | Enforces simulated risk execution only |
| `ALLOW_PUBLIC_SIGNUP` | `false` | Yes | Restricts registration for private use |
| `SECRET_KEY` | *(generate random 64-char string)* | Yes | JWT token signing key |
| `ENCRYPTION_MASTER_KEY` | *(generate random Fernet key or 32-char string)* | Yes | Encrypts exchange credentials at rest |
| `CORS_ORIGINS` | `https://your-project.vercel.app` | Yes | Exact Vercel origin (add localhost for dev) |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` or `sqlite:///./trading_ai.db` | Yes | Persistent database connection string |
| `INITIAL_ADMIN_EMAIL` | `admin@tradingai.local` | Yes | Default provisioned administrator email |
| `INITIAL_ADMIN_PASSWORD` | *(strong admin password)* | Yes | Default provisioned administrator password |
| `SAFE_KILL_SWITCH_ACTIVE` | `false` | Yes | Initial state of risk kill switch |
| `INITIAL_PAPER_BALANCE` | `10000.0` | Yes | Virtual starting paper balance ($USDT) |

#### Public Market Data & Optional Channel Variables:
| Variable Name | Example / Format | Purpose |
|---|---|---|
| `MARKET_DATA_PROVIDER` | `kraken` | Public market data provider (`kraken` default, `bybit`, or `composite`). Zero credentials needed! |
| `TELEGRAM_BOT_TOKEN` | `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | `987654321` | Recipient Telegram Chat ID |
| `TELEGRAM_ENABLED` | `true` | Enable Telegram alert channel |
| `WHATSAPP_API_TOKEN` | `EAAG...` | Meta System User Access Token |
| `WHATSAPP_PHONE_NUMBER_ID` | `104829104820194` | Meta WhatsApp Phone Number ID |
| `WHATSAPP_ENABLED` | `true` | Enable WhatsApp alert channel |
| `WHATSAPP_PROVIDER` | `meta` | Messaging provider (`meta` or `twilio`) |
| `BINANCE_API_KEY` | *(strictly optional)* | Only for private real account balance sync; NOT needed for market data |
| `BINANCE_API_SECRET` | *(strictly optional)* | Only for private real account balance sync; NOT needed for market data |
| `BINANCE_TESTNET` | `false` | Toggle testnet vs production Binance endpoints for private sync |

> [!NOTE]
> Render provides a **Managed PostgreSQL** service. If you provision a Render PostgreSQL database, copy the **Internal Database URL** and set it as `DATABASE_URL`. SQLAlchemy will automatically convert `postgres://` to `postgresql://` and safely migrate missing columns on startup without deleting data.

### Step 4: Deploy and Verify Backend
1. Click **Create Web Service**.
2. Once the build completes and status shows **Live**, open:
   ```
   https://trading-ai-backend.onrender.com/api/health
   ```
3. Expect response:
   ```json
   {
     "status": "healthy",
     "app": "Trading AI Platform",
     "version": "2.0.0",
     "trading_mode": "paper",
     "is_paper_trading": true,
     "timestamp": "..."
   }
   ```

---

## Part 2: Frontend Deployment on Vercel

### Step 1: Create Project on Vercel
1. Log in to your [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your private repository (`trading_ai`).

### Step 2: Configure Project Build Settings
- **Framework Preset:** `Vite`
- **Root Directory:** Click Edit and select `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`

### Step 3: Add Frontend Environment Variables
In the **Environment Variables** section:

| Key | Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `https://trading-ai-backend.onrender.com` | Deployed Render backend URL |

> [!IMPORTANT]
> Do NOT set any backend secrets (like `SECRET_KEY`, `BINANCE_API_SECRET`, or `WHATSAPP_API_TOKEN`) in Vercel. `VITE_` variables are public and bundled into browser JavaScript.

### Step 4: Deploy and Verify Frontend
1. Click **Deploy**.
2. Once deployed, visit your assigned Vercel URL (e.g. `https://trading-ai-frontend.vercel.app`).
3. Copy your exact Vercel domain.
4. Return to **Render** → `trading-ai-backend` → **Environment** and update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://trading-ai-frontend.vercel.app
   ```
   Render will automatically redeploy the backend with the new allowed origin.

---

## Part 3: Notification Channels Configuration

Once both frontend and backend are live:

### 1. Telegram Bot Linking
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, choose a name and username, and copy the **HTTP API Token**.
3. Open Telegram and search for `@userinfobot` to find your numeric **Id** (Chat ID).
4. Send a message (e.g., `/start`) to your newly created bot to grant it permission to message you.
5. In your deployed Trading AI Dashboard, navigate to **Notification Center** → **Telegram Bot Card** → click **Configure Telegram Bot**.
6. Enter the Bot Token and your numeric Chat ID, then click **Verify & Connect**.
7. The server calls `https://api.telegram.org/bot<token>/getMe` and `/getChat`.
8. Once verified, the badge immediately updates to **CONNECTED** and shows your bot username.
9. Click **Test Telegram Message** to verify live delivery.

### 2. WhatsApp Business Cloud API Linking
1. Log in to [Meta for Developers](https://developers.facebook.com).
2. Create or open your WhatsApp Business app.
3. Under **WhatsApp** → **API Setup**:
   - Copy your **Phone Number ID**.
   - Generate a System User Access Token with `whatsapp_business_messaging` permissions.
4. In your deployed Trading AI Dashboard, navigate to **Notification Center** → **WhatsApp Business Card** → click **Configure WhatsApp Credentials**.
5. Enter:
   - **Phone Number ID** (e.g. `104829104820194`)
   - **Meta System User Access Token**
   - **Recipient Phone Number** in international E.164 format (e.g. `+14155552671`)
6. Click **Verify & Connect**.
7. The server validates the Phone Number ID directly with Meta Graph API (`GET /v18.0/{id}`) without sending unsolicited messages.
8. Once verified, the badge updates to **CONNECTED** and displays the verified sender name.
9. Click **Test WhatsApp Message** to receive a verification alert on your phone.

---

## Part 4: Trading Safety Protections

- **Strict Paper Trading:** The platform runs exclusively in paper-trading simulation mode (`TRADING_MODE=paper`).
- **Read-Only API Boundaries:** The exchange client contains zero code paths for placing, modifying, or canceling live orders on Binance.
- **Emergency Kill Switch:** Accessible in the header navbar and settings. Engaging the kill switch immediately halts all simulated order executions and dispatches institutional risk alerts across all channels.
