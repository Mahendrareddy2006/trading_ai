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
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from trading_ai.config.settings import settings
from trading_ai.core.events import event_bus
from trading_ai.core.logging import get_logger
from trading_ai.data.manager import data_manager
from trading_ai.database.session import init_db
from trading_ai.execution.paper import paper_engine
from trading_ai.inference.predictor import model_predictor
from trading_ai.risk.engine import risk_engine
from trading_ai.strategies.ml_strategy import MLMultiTimeframeStrategy
from trading_ai.training.trainer import model_trainer, MODELS_DIR

logger = get_logger("API")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Advanced AI Cryptocurrency Trading Research & Paper-Trading Platform"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ml_strategy = MLMultiTimeframeStrategy(
    edge_threshold=settings.ML_EDGE_THRESHOLD,
    min_probability=settings.ML_MIN_PROBABILITY
)

# Active market prices cache
live_prices: Dict[str, float] = {
    "BTCUSDT": 91500.0,
    "ETHUSDT": 3150.0,
    "BNBUSDT": 620.0,
    "SOLUSDT": 185.0
}


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
# Background Worker for Live Paper Trading Simulation
# ============================================================================
async def live_trading_loop():
    """Background task simulating tick arrivals and strategy evaluation."""
    logger.info("Starting background paper-trading tick loop...")
    while True:
        try:
            for symbol in settings.default_symbols:
                # 1. Fetch real latest candle or fallback to simulated tick
                candles_1h = data_manager.load_candles(symbol, "1h")
                if candles_1h:
                    base_price = float(candles_1h[-1]["close"])
                else:
                    base_price = live_prices.get(symbol, 1000.0)

                # Micro tick jitter for live demonstration
                jitter = (hash(f"{symbol}_{datetime.now().second}") % 100 - 50) * 0.0001
                current_price = round(base_price * (1.0 + jitter), 2)
                live_prices[symbol] = current_price

                # 2. Update paper engine positions
                paper_engine.on_price_update(symbol, current_price)

                # 3. Evaluate Strategy if flat
                if symbol not in paper_engine.positions and candles_1h and len(candles_1h) >= 40:
                    candles_5m = data_manager.load_candles(symbol, "5m")
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

                # 4. Broadcast Tick Event
                await event_bus.emit("TICK", {
                    "symbol": symbol,
                    "price": current_price,
                    "equity": round(paper_engine.equity, 2),
                    "open_positions": len(paper_engine.positions)
                })

            await asyncio.sleep(3)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in live trading loop: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def on_startup():
    init_db()
    logger.info("Database initialized successfully.")
    ensure_seed_models()
    asyncio.create_task(live_trading_loop())


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


@app.get("/api/market/candles")
def get_candles(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    limit: int = Query(100, le=500)
):
    candles = data_manager.load_candles(symbol, timeframe)
    if not candles:
        candles = data_manager.fetch_binance_klines(symbol, timeframe, limit=limit)
    return {"symbol": symbol, "timeframe": timeframe, "candles": candles[-limit:]}


@app.get("/api/predictions/latest")
def get_latest_predictions():
    results = []
    for symbol in settings.default_symbols:
        candles = data_manager.load_candles(symbol, "1h")
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


@app.get("/api/risk/status")
def get_risk_status():
    return risk_engine.get_status(current_equity=paper_engine.equity)


@app.post("/api/risk/kill-switch")
def toggle_kill_switch(req: KillSwitchRequest):
    risk_engine.toggle_kill_switch(req.active, reason=req.reason or "Dashboard toggle")
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
                "equity": round(paper_engine.equity, 2),
                "cash": round(paper_engine.cash, 2),
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

