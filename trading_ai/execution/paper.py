"""Paper Trading Execution Engine.

Simulates exchange matching and position management:
- Maintains virtual cash, equity, and position balances
- Models realistic execution slippage and Binance futures taker fees (0.04%)
- Tracks protective Stop-Loss and Take-Profit execution
- Non-blocking evaluation per symbol (symbol A never blocks symbol B)
- Persists executed trades and emits real-time events to WebSocket bus
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from trading_ai.config.settings import settings
from trading_ai.core.events import event_bus
from trading_ai.core.logging import get_logger, trade_logger
from trading_ai.database.models import OrderRecord, PositionRecord, TradeRecord
from trading_ai.database.session import SessionLocal
from trading_ai.risk.engine import risk_engine

logger = get_logger("PaperExecution")


class PaperExecutionEngine:
    """Manages simulated exchange state and non-blocking order matching."""

    def __init__(
        self,
        initial_balance: float = settings.INITIAL_PAPER_BALANCE,
        taker_fee_pct: float = 0.0004,  # 0.04% taker fee
        slippage_pct: float = 0.0005     # 0.05% estimated slippage
    ):
        self.cash = initial_balance
        self.taker_fee_pct = taker_fee_pct
        self.slippage_pct = slippage_pct
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []

    @property
    def equity(self) -> float:
        """Total equity = cash balance + sum of open positions unrealized PnL."""
        unrealized = sum(p.get("unrealized_pnl", 0.0) for p in self.positions.values())
        return self.cash + unrealized

    def get_open_positions_list(self) -> List[Dict[str, Any]]:
        return list(self.positions.values())

    def open_position(
        self,
        symbol: str,
        side: str,  # "LONG" or "SHORT"
        entry_price: float,
        quantity: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        leverage: int = settings.DEFAULT_LEVERAGE,
        strategy_name: str = "ML_Strategy",
        model_version: str = "v1.0"
    ) -> Optional[Dict[str, Any]]:
        """Simulates opening a new leveraged position with protective orders."""
        if symbol in self.positions:
            logger.warning(f"Position already open for {symbol}. Rejecting open_position.")
            return None

        # Apply slippage on entry
        fill_price = entry_price * (1 + self.slippage_pct) if side == "LONG" else entry_price * (1 - self.slippage_pct)

        notional = fill_price * quantity
        fee = notional * self.taker_fee_pct
        self.cash -= fee  # Deduct entry transaction fee

        if side == "LONG":
            sl_price = fill_price * (1.0 - stop_loss_pct)
            tp_price = fill_price * (1.0 + take_profit_pct)
        else:
            sl_price = fill_price * (1.0 + stop_loss_pct)
            tp_price = fill_price * (1.0 - take_profit_pct)

        pos_id = str(uuid.uuid4())[:8]
        position = {
            "id": pos_id,
            "symbol": symbol,
            "side": side,
            "entry_price": round(fill_price, 4),
            "current_price": round(fill_price, 4),
            "quantity": quantity,
            "leverage": leverage,
            "notional": round(notional, 2),
            "stop_loss": round(sl_price, 4),
            "take_profit": round(tp_price, 4),
            "unrealized_pnl": 0.0,
            "return_pct": 0.0,
            "fee_paid": round(fee, 4),
            "strategy_name": strategy_name,
            "model_version": model_version,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "status": "OPEN"
        }

        self.positions[symbol] = position
        trade_logger.info(f"OPEN | {symbol} {side} | Qty: {quantity} @ {fill_price:.2f} | SL: {sl_price:.2f} | TP: {tp_price:.2f}")

        # Persist to database
        try:
            with SessionLocal() as db:
                db_pos = PositionRecord(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    entry_price=fill_price,
                    current_price=fill_price,
                    leverage=leverage,
                    unrealized_pnl=0.0,
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    status="OPEN"
                )
                db.merge(db_pos)
                db.commit()
        except Exception as e:
            logger.error(f"Error persisting position to DB: {e}")

        return position

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "MANUAL"
    ) -> Optional[Dict[str, Any]]:
        """Closes an active position, applies exit fees, updates cash and risk stats."""
        if symbol not in self.positions:
            return None

        pos = self.positions.pop(symbol)
        side = pos["side"]
        qty = pos["quantity"]
        entry = pos["entry_price"]

        # Apply slippage on exit
        fill_price = exit_price * (1 - self.slippage_pct) if side == "LONG" else exit_price * (1 + self.slippage_pct)
        exit_notional = fill_price * qty
        exit_fee = exit_notional * self.taker_fee_pct

        # PnL math
        if side == "LONG":
            gross_pnl = (fill_price - entry) * qty
        else:
            gross_pnl = (entry - fill_price) * qty

        total_fees = pos.get("fee_paid", 0.0) + exit_fee
        net_pnl = gross_pnl - exit_fee
        return_pct = (net_pnl / (entry * qty / pos.get("leverage", 1))) * 100.0

        self.cash += net_pnl

        trade_record = {
            "trade_id": str(uuid.uuid4())[:8],
            "symbol": symbol,
            "side": side,
            "entry_price": round(entry, 4),
            "exit_price": round(fill_price, 4),
            "quantity": qty,
            "leverage": pos.get("leverage", 1),
            "gross_pnl": round(gross_pnl, 2),
            "fees": round(total_fees, 4),
            "net_pnl": round(net_pnl, 2),
            "return_pct": round(return_pct, 2),
            "exit_reason": reason,
            "strategy_name": pos.get("strategy_name", "ML_Strategy"),
            "model_version": pos.get("model_version", "v1.0"),
            "opened_at": pos["opened_at"],
            "closed_at": datetime.now(timezone.utc).isoformat()
        }

        self.trades.append(trade_record)
        trade_logger.info(
            f"CLOSE | {symbol} {side} | Exit: {fill_price:.2f} ({reason}) | "
            f"Net PnL: ${net_pnl:.2f} ({return_pct:+.2f}%)"
        )

        # Notify Risk Engine of outcome
        risk_engine.record_trade_outcome(net_pnl, side)

        # Persist to database
        try:
            with SessionLocal() as db:
                db_trade = TradeRecord(
                    trade_id=trade_record["trade_id"],
                    symbol=symbol,
                    side=side,
                    entry_price=entry,
                    exit_price=fill_price,
                    quantity=qty,
                    leverage=pos.get("leverage", 1),
                    gross_pnl=gross_pnl,
                    fee=total_fees,
                    net_pnl=net_pnl,
                    return_pct=return_pct,
                    exit_reason=reason,
                    strategy_name=trade_record["strategy_name"],
                    model_version=trade_record["model_version"]
                )
                db.add(db_trade)

                # Update position status in DB
                db_pos = db.query(PositionRecord).filter(PositionRecord.symbol == symbol).first()
                if db_pos:
                    db_pos.status = "CLOSED"
                    db_pos.closed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as e:
            logger.error(f"Error persisting trade to DB: {e}")

        return trade_record

    def on_price_update(
        self,
        symbol: str,
        current_price: float,
        high: Optional[float] = None,
        low: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Non-blocking tick check for SL / TP triggers and unrealized PnL updates."""
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        high_price = high or current_price
        low_price = low or current_price

        pos["current_price"] = current_price
        side = pos["side"]
        qty = pos["quantity"]
        entry = pos["entry_price"]
        sl = pos["stop_loss"]
        tp = pos["take_profit"]

        # 1. Check Take-Profit & Stop-Loss triggers
        if side == "LONG":
            pos["unrealized_pnl"] = round((current_price - entry) * qty, 2)
            if low_price <= sl:
                return self.close_position(symbol, sl, reason="STOP_LOSS")
            elif high_price >= tp:
                return self.close_position(symbol, tp, reason="TAKE_PROFIT")
        else:  # SHORT
            pos["unrealized_pnl"] = round((entry - current_price) * qty, 2)
            if high_price >= sl:
                return self.close_position(symbol, sl, reason="STOP_LOSS")
            elif low_price <= tp:
                return self.close_position(symbol, tp, reason="TAKE_PROFIT")

        pos["return_pct"] = round((pos["unrealized_pnl"] / (entry * qty / pos.get("leverage", 1))) * 100.0, 2)
        return None


paper_engine = PaperExecutionEngine()
