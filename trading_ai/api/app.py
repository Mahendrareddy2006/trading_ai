"""FastAPI Backend Application & Real-Time WebSocket Server.

Features:
- Validated REST endpoints for market data, predictions, models, training, backtesting, positions, and risk
- WebSocket endpoint `/ws/live` for streaming real-time prices, predictions, and positions
- Background non-blocking execution worker
- Safe CORS and startup database initialization
"""

import asyncio
from datetime import datetime, timezone
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from trading_ai.config.settings import settings
from trading_ai.core.events import event_bus
from trading_ai.core.logging import get_logger
from trading_ai.core.security import decrypt_credential
from trading_ai.data.manager import data_manager
from trading_ai.database.models import User, ExchangeCredential
from trading_ai.execution.binance_client import binance_futures_client, BinanceFuturesClient
from trading_ai.execution.paper import paper_engine
from trading_ai.inference.predictor import model_predictor
from trading_ai.risk.engine import risk_engine
from trading_ai.strategies.ml_strategy import MLMultiTimeframeStrategy
from trading_ai.training.trainer import model_trainer, MODELS_DIR

from trading_ai.api.auth import auth_router
from trading_ai.api.exchange import exchange_router
from trading_ai.api.watchlist import watchlist_router
from trading_ai.api.news import news_router
from trading_ai.api.notifications import notification_router
from trading_ai.services.notification_service import notification_service
from trading_ai.database.session import SessionLocal, init_db, get_db
from trading_ai.api.deps import get_optional_current_user

logger = get_logger("API")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Advanced AI Cryptocurrency Trading Research & Paper-Trading Platform"
)

# CORS Middleware with explicit origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth_router)
app.include_router(exchange_router)
app.include_router(watchlist_router)
app.include_router(news_router)
app.include_router(notification_router)


@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
def health_check():
    """Readiness and liveness probe for Render and external health checks."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "trading_mode": settings.TRADING_MODE,
        "is_paper_trading": settings.is_paper_trading,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

ml_strategy = MLMultiTimeframeStrategy(
    edge_threshold=settings.ML_EDGE_THRESHOLD,
    min_probability=settings.ML_MIN_PROBABILITY
)

# Active real-time market prices & 24h stats cache (populated dynamically from exchange)
live_prices: Dict[str, float] = {}
live_ticker_stats: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Pydantic Schemas
# ============================================================================
class KillSwitchRequest(BaseModel):
    active: bool
    reason: Optional[str] = "Manual dashboard toggle"


class TrainingRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    model_type: str = "random_forest"
    n_estimators: int = 35
    max_depth: int = 6


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    initial_balance: float = 10000.0
    sl_pct: float = 0.015
    tp_pct: float = 0.030
    risk_per_trade: float = 0.01
    use_ml_model: bool = True


# ============================================================================
# Background Worker for Real-Time Market Feed & Paper Trading
# ============================================================================
async def live_trading_loop():
    """Background task pulling real Binance market prices and evaluating strategy."""
    logger.info("Starting background paper-trading tick loop with real Binance market feed...")

    # Fetch initial real-time market prices on startup
    try:
        init_tickers = data_manager.fetch_realtime_tickers(settings.default_symbols)
        for sym, t_data in init_tickers.items():
            live_prices[sym] = t_data["price"]
            live_ticker_stats[sym] = t_data
        logger.info(f"Initialized real live prices: {live_prices}")
    except Exception as e:
        logger.warning(f"Initial ticker fetch warning: {e}")

    while True:
        try:
            # 1. Fetch real-time ticker data from Binance
            real_tickers = data_manager.fetch_realtime_tickers(settings.default_symbols)
            for symbol in settings.default_symbols:
                if symbol in real_tickers:
                    t_info = real_tickers[symbol]
                    current_price = t_info["price"]
                    live_prices[symbol] = current_price
                    live_ticker_stats[symbol] = t_info
                elif symbol in live_prices:
                    current_price = live_prices[symbol]
                else:
                    live_candles = data_manager.get_live_candles(symbol, "1h", limit=3)
                    current_price = float(live_candles[-1]["close"]) if live_candles else 100.0
                    live_prices[symbol] = current_price

                # 2. Update paper engine positions with real current price
                paper_engine.on_price_update(symbol, current_price)

                # 2b. Evaluate Price-Range & Price-Crossing Alerts
                try:
                    db_sess = SessionLocal()
                    notification_service.evaluate_price_alerts(db_sess, symbol, current_price)
                    db_sess.close()
                except Exception as e:
                    logger.debug(f"Error evaluating price alerts for {symbol}: {e}")

                # 3. Evaluate Strategy with live candles if flat
                if symbol not in paper_engine.positions:
                    candles_1h = data_manager.get_live_candles(symbol, "1h", limit=100)
                    if candles_1h and len(candles_1h) >= 40:
                        candles_5m = data_manager.get_live_candles(symbol, "5m", limit=100)
                        candles_dict = {"1h": candles_1h, "5m": candles_5m}

                        decision = ml_strategy.evaluate(symbol, candles_dict)

                        if decision.action in ["BUY", "SELL"]:
                            valid, qty, reason = risk_engine.validate_trade_order(
                                symbol=symbol,
                                side="LONG" if decision.action == "BUY" else "SHORT",
                                price=current_price,
                                stop_loss_pct=decision.stop_loss_pct,
                                current_equity=paper_engine.equity,
                                open_positions=paper_engine.get_open_positions_list()
                            )
                            if valid and qty > 0:
                                paper_engine.open_position(
                                    symbol=symbol,
                                    side="LONG" if decision.action == "BUY" else "SHORT",
                                    entry_price=current_price,
                                    quantity=qty,
                                    stop_loss_pct=decision.stop_loss_pct,
                                    take_profit_pct=decision.take_profit_pct
                                )

                # 4. Broadcast Real Live Tick Event over WebSocket
                t_stat = live_ticker_stats.get(symbol, {})
                await event_bus.emit("TICK", {
                    "symbol": symbol,
                    "market_type": t_stat.get("market_type", "USDⓈ-M Perp"),
                    "price": current_price,
                    "change_24h": t_stat.get("change_24h", 0.0),
                    "change_24h_abs": t_stat.get("change_24h_abs", 0.0),
                    "high_24h": t_stat.get("high_24h", current_price),
                    "low_24h": t_stat.get("low_24h", current_price),
                    "volume_24h": t_stat.get("volume_24h", 0.0),
                    "quote_volume_24h": t_stat.get("quote_volume_24h", 0.0),
                    "mark_price": t_stat.get("mark_price", current_price),
                    "funding_rate": t_stat.get("funding_rate", 0.0),
                    "bid_price": t_stat.get("bid_price", current_price),
                    "ask_price": t_stat.get("ask_price", current_price),
                    "spread": t_stat.get("spread", 0.0),
                    "equity": round(paper_engine.equity, 2),
                    "cash": round(paper_engine.cash, 2),
                    "unrealized_pnl": round(paper_engine.unrealized_pnl, 2),
                    "open_positions": len(paper_engine.positions),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_stale": False
                })

            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in live trading loop: {e}")
            await asyncio.sleep(4)


@app.on_event("startup")
async def on_startup():
    init_db()
    logger.info("Database initialized successfully.")
    ensure_seed_models()
    asyncio.create_task(live_trading_loop())
    asyncio.create_task(scheduled_notification_loop())


async def scheduled_notification_loop():
    """Background scheduler for hourly portfolio summaries and breaking news monitoring."""
    from trading_ai.database.session import SessionLocal
    from trading_ai.services.notification_service import notification_service
    from trading_ai.services.news_service import news_service

    logger.info("Started scheduled notification & news monitor loop (Hourly summaries + Breaking news alerts).")
    await asyncio.sleep(5)

    while True:
        try:
            db_session = SessionLocal()
            try:
                # 1. Hourly Summary Cadence Check & Dispatch
                notification_service.run_scheduled_summaries(db_session)

                # 2. News Ingestion & Real-Time Breaking News Multi-Channel Dispatch
                articles = news_service.refresh_news(force=False)
                if articles:
                    notification_service.evaluate_news_articles(db_session, articles)
            finally:
                db_session.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in scheduled notification background loop: {e}")

        await asyncio.sleep(60)


def ensure_seed_models():
    """Trains a baseline model on BTCUSDT 1h if no models exist in models_dir."""
    existing = [f for f in os.listdir(MODELS_DIR) if f.endswith(".joblib")]
    if not existing:
        logger.info("No trained models found on disk. Training initial baseline model on BTCUSDT_1h.csv...")
        candles = data_manager.load_candles("BTCUSDT", "1h")
        if candles and len(candles) >= 80:
            try:
                model_trainer.train_and_evaluate(candles, "BTCUSDT", "1h", model_type="random_forest")
                logger.info("Seed model successfully trained!")
            except Exception as e:
                logger.error(f"Seed model training error: {e}")


# ============================================================================
# REST Endpoints
# ============================================================================
@app.get("/api/health")
def get_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": settings.TRADING_MODE,
        "is_paper": settings.is_paper_trading,
        "kill_switch": risk_engine.kill_switch_active,
        "version": settings.APP_VERSION
    }


@app.get("/api/config")
def get_config():
    return {
        "trading_mode": settings.TRADING_MODE,
        "kill_switch_active": risk_engine.kill_switch_active,
        "initial_paper_balance": settings.INITIAL_PAPER_BALANCE,
        "symbols": settings.default_symbols,
        "max_risk_per_trade": settings.MAX_RISK_PER_TRADE,
        "default_leverage": settings.DEFAULT_LEVERAGE,
        "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT,
        "max_drawdown_pct": settings.MAX_DRAWDOWN_PCT,
        "cooldown_minutes": settings.COOLDOWN_MINUTES,
        "telegram_enabled": settings.TELEGRAM_ENABLED
    }


@app.get("/api/market/symbols")
def get_symbols():
    return {"symbols": settings.default_symbols}


@app.get("/api/market/tickers")
def get_market_tickers():
    """Returns real-time 24h ticker metrics directly from Binance."""
    if not live_ticker_stats:
        tickers = data_manager.fetch_realtime_tickers(settings.default_symbols)
        for sym, t in tickers.items():
            live_ticker_stats[sym] = t
            live_prices[sym] = t["price"]
    return {"tickers": live_ticker_stats}


@app.get("/api/market/candles")
def get_candles(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    limit: int = Query(100, le=500)
):
    """Returns real live candles from Binance up to the current minute."""
    candles = data_manager.get_live_candles(symbol, timeframe, limit=limit)
    return {"symbol": symbol, "timeframe": timeframe, "candles": candles[-limit:]}


@app.get("/api/predictions/latest")
def get_latest_predictions():
    results = []
    for symbol in settings.default_symbols:
        candles = data_manager.get_live_candles(symbol, "1h", limit=120)
        if candles and len(candles) >= 40:
            pred = model_predictor.predict(candles, symbol, "1h")
            results.append(pred.to_dict())
        else:
            results.append({
                "symbol": symbol,
                "timeframe": "1h",
                "direction": "NEUTRAL",
                "predicted_class": 0,
                "edge": 0.0,
                "confidence": 0.33,
                "regime": "UNKNOWN",
                "probabilities": {"BUY": 0.33, "SELL": 0.33, "NEUTRAL": 0.34},
                "abstention_reason": "INSUFFICIENT_HISTORICAL_DATA",
                "model_version": "NONE"
            })
    return {"predictions": results}


@app.get("/api/models")
def list_models():
    models = []
    if os.path.exists(MODELS_DIR):
        import joblib
        for f in os.listdir(MODELS_DIR):
            if f.endswith(".joblib"):
                path = os.path.join(MODELS_DIR, f)
                try:
                    meta = joblib.load(path)
                    models.append({
                        "model_id": meta.get("model_id", f),
                        "symbol": meta.get("symbol", "UNKNOWN"),
                        "timeframe": meta.get("timeframe", "1h"),
                        "model_type": meta.get("model_type", "random_forest"),
                        "created_at": meta.get("created_at"),
                        "metrics": meta.get("metrics", {}),
                        "feature_importances": meta.get("feature_importances", {}),
                        "sample_counts": meta.get("sample_counts", {})
                    })
                except Exception as e:
                    logger.error(f"Error reading model {f}: {e}")
    return {"models": models}


@app.post("/api/training/start")
def start_training(req: TrainingRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]

    def run_training_task(jid: str, sym: str, tf: str, mtype: str, n_est: int, depth: int):
        logger.info(f"Background Training Job {jid} started for {sym}...")
        candles = data_manager.load_candles(sym, tf)
        if not candles or len(candles) < 80:
            candles, _ = data_manager.sync_historical_data(sym, tf, target_candles=1000)

        if candles and len(candles) >= 80:
            model_trainer.train_and_evaluate(
                candles=candles,
                symbol=sym,
                timeframe=tf,
                model_type=mtype,
                hyperparams={"n_estimators": n_est, "max_depth": depth}
            )
            logger.info(f"Background Training Job {jid} completed successfully.")

    background_tasks.add_task(
        run_training_task, job_id, req.symbol, req.timeframe, req.model_type, req.n_estimators, req.max_depth
    )

    return {"status": "SUBMITTED", "job_id": job_id, "symbol": req.symbol, "timeframe": req.timeframe}


@app.post("/api/backtest/run")
def run_backtest(req: BacktestRequest):
    candles = data_manager.load_candles(req.symbol, req.timeframe)
    if not candles or len(candles) < 40:
        raise HTTPException(status_code=400, detail=f"Insufficient candles for {req.symbol} ({req.timeframe}).")

    bundle = None
    if req.use_ml_model:
        bundle = model_predictor.get_latest_model_bundle(req.symbol, req.timeframe)

    from trading_ai.backtesting.engine import backtest_engine
    backtest_engine.initial_balance = req.initial_balance
    result = backtest_engine.run_backtest(
        candles=candles,
        symbol=req.symbol,
        sl_pct=req.sl_pct,
        tp_pct=req.tp_pct,
        risk_per_trade=req.risk_per_trade,
        model_bundle=bundle
    )
    return result


@app.get("/api/positions")
def get_positions():
    return {
        "positions": paper_engine.get_open_positions_list(),
        "cash": round(paper_engine.cash, 2),
        "equity": round(paper_engine.equity, 2),
        "total_unrealized_pnl": round(paper_engine.equity - paper_engine.cash, 2)
    }


@app.post("/api/positions/{symbol}/close")
def close_position(symbol: str):
    if symbol not in paper_engine.positions:
        raise HTTPException(status_code=404, detail=f"No open position found for {symbol}")
    current_price = live_prices.get(symbol, paper_engine.positions[symbol]["current_price"])
    trade = paper_engine.close_position(symbol, current_price, reason="MANUAL_CLOSE")
    return {"status": "CLOSED", "trade": trade}


@app.get("/api/trades")
def get_trades(limit: int = 50):
    trades = paper_engine.trades[-limit:]
    trades.reverse()
    return {"trades": trades}


# ============================================================================
# Authenticated Binance Exchange Account Endpoints (Read-Only)
# ============================================================================
def get_user_exchange_client(user: Optional[User], db: Session) -> Tuple[BinanceFuturesClient, Optional[ExchangeCredential]]:
    """Resolves authenticated user's encrypted credentials; prevents cross-user exposure."""
    if user:
        cred = db.query(ExchangeCredential).filter(
            ExchangeCredential.user_id == user.id,
            ExchangeCredential.exchange_name == "binance",
            ExchangeCredential.is_active == True
        ).first()
        if cred:
            try:
                key = decrypt_credential(cred.encrypted_api_key)
                secret = decrypt_credential(cred.encrypted_api_secret)
                client = BinanceFuturesClient(api_key=key, api_secret=secret, testnet=cred.is_testnet)
                return client, cred
            except Exception as e:
                logger.error(f"Failed to decrypt user exchange credentials: {e}")
                return BinanceFuturesClient(api_key="", api_secret=""), None
        # User is admin without credentials in DB, allow root .env dev fallback
        if user.is_superuser and binance_futures_client.is_configured:
            return binance_futures_client, None
        return BinanceFuturesClient(api_key="", api_secret=""), None

    # Unauthenticated: if admin dev mode with root .env, return root client
    return binance_futures_client, None


@app.get("/api/account/summary")
def get_exchange_account_summary(
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Returns actual Binance USD(S)-M Futures wallet balance, margin, and unrealized PnL."""
    client, cred = get_user_exchange_client(user, db)
    if not client.is_configured:
        return {
            "is_configured": False,
            "status": "NOT_CONNECTED",
            "message": "No exchange account connected. Go to Settings -> Exchange Connections to connect your read-only Binance API key.",
            "account_type": "Binance USD(S)-M Futures",
            "testnet": client.testnet
        }
    summary, err = client.get_account_summary()
    if cred:
        if err is None and summary.get("status") == "CONNECTED":
            cred.last_sync_at = datetime.now(timezone.utc)
            cred.status = "CONNECTED"
            cred.error_message = None
            db.commit()
        elif err or summary.get("status") in ["AUTH_FAILED", "PERMISSION_DENIED", "IP_RESTRICTED"]:
            cred.status = summary.get("status", "AUTH_FAILED")
            cred.error_message = str(summary.get("error") or err)
            db.commit()
    return summary


@app.get("/api/account/positions")
def get_exchange_positions(
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Returns actual active open positions on Binance USD(S)-M Futures."""
    client, _ = get_user_exchange_client(user, db)
    if not client.is_configured:
        return {"positions": [], "is_configured": False, "error": None}
    positions, err = client.get_account_positions()
    return {
        "positions": positions,
        "is_configured": True,
        "error": err
    }


@app.get("/api/account/open-orders")
def get_exchange_open_orders(
    symbol: Optional[str] = None,
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Returns actual open orders on Binance Futures."""
    client, _ = get_user_exchange_client(user, db)
    if not client.is_configured:
        return {"orders": [], "is_configured": False, "error": None}
    orders, err = client.get_open_orders(symbol=symbol)
    return {
        "orders": orders,
        "is_configured": True,
        "error": err
    }


@app.get("/api/account/trades")
def get_exchange_user_trades(
    symbol: str = "BTCUSDT",
    limit: int = 50,
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Returns actual executed fills on Binance Futures."""
    client, _ = get_user_exchange_client(user, db)
    if not client.is_configured:
        return {"trades": [], "is_configured": False, "error": None}
    trades, err = client.get_user_trades(symbol=symbol, limit=limit)
    return {
        "trades": trades,
        "is_configured": True,
        "error": err
    }


@app.get("/api/system/data-status")
def get_system_data_status():
    """Returns health of exchange connectivity, latency, and data streams."""
    ping_info = binance_futures_client.get_server_ping()
    return {
        "exchange_connectivity": ping_info,
        "credentials_configured": binance_futures_client.is_configured,
        "active_symbols": settings.default_symbols,
        "live_prices_cached": len(live_prices),
        "testnet": binance_futures_client.testnet,
        "server_time_offset_ms": binance_futures_client.time_offset_ms,
        "trading_mode": settings.TRADING_MODE,
        "is_paper_trading": settings.is_paper_trading,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/risk/status")
def get_risk_status():
    return risk_engine.get_status(current_equity=paper_engine.equity)


@app.post("/api/risk/kill-switch")
def toggle_kill_switch(req: KillSwitchRequest):
    risk_engine.toggle_kill_switch(req.active, reason=req.reason or "Dashboard toggle")
    try:
        db_sess = SessionLocal()
        notification_service.dispatch_risk_alert(
            db=db_sess,
            event_type="kill_switch_toggled",
            severity="critical" if req.active else "info",
            details=f"Emergency kill switch was {'ENGAGED' if req.active else 'RELEASED'}. Reason: {req.reason or 'User action'}"
        )
        db_sess.close()
    except Exception as e:
        logger.error(f"Error dispatching kill switch alert: {e}")
    return {"kill_switch_active": risk_engine.kill_switch_active}


# ============================================================================
# WebSocket Endpoint
# ============================================================================
@app.websocket("/ws/live")
async def websocket_live_stream(websocket: WebSocket):
    await websocket.accept()
    queue = asyncio.Queue(maxsize=100)
    event_bus.register_ws_queue(queue)
    logger.info("WebSocket client connected to live stream.")

    try:
        await websocket.send_json({
            "type": "SNAPSHOT",
            "data": {
                "prices": live_prices,
                "tickers": live_ticker_stats,
                "equity": round(paper_engine.equity, 2),
                "cash": round(paper_engine.cash, 2),
                "unrealized_pnl": round(paper_engine.unrealized_pnl, 2),
                "positions": paper_engine.get_open_positions_list(),
                "kill_switch": risk_engine.kill_switch_active
            }
        })

        while True:
            msg = await queue.get()
            await websocket.send_json(msg)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
    finally:
        event_bus.unregister_ws_queue(queue)


# ============================================================================
# Frontend Static Asset Serving
# ============================================================================
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(os.path.join(frontend_dist, "index.html")):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not Found")
        target = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

