"""Centralized Risk Management Engine.

Enforces institutional safeguards:
- Fixed-fractional position sizing based on stop-loss distance
- Minimum notional and precision rounding
- Portfolio-wide exposure and correlation guards
- 2% Daily Loss Circuit Breaker
- 10% Trailing Drawdown Circuit Breaker
- 3 Consecutive Losses Circuit Breaker
- Properly expiring 15-minute cooldown timer
- Manual Emergency Kill Switch
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple

from trading_ai.config.settings import settings
from trading_ai.core.logging import get_logger

logger = get_logger("RiskEngine")

# Common Binance Futures symbol lot specifications
SYMBOL_FILTERS = {
    "BTCUSDT": {"min_qty": 0.001, "step_size": 0.001, "min_notional": 5.0, "tick_size": 0.10},
    "ETHUSDT": {"min_qty": 0.01,  "step_size": 0.01,  "min_notional": 5.0, "tick_size": 0.01},
    "BNBUSDT": {"min_qty": 0.01,  "step_size": 0.01,  "min_notional": 5.0, "tick_size": 0.01},
    "SOLUSDT": {"min_qty": 0.1,   "step_size": 0.1,   "min_notional": 5.0, "tick_size": 0.01},
}


class RiskEngine:
    """Evaluates risk viability of proposed orders and enforces portfolio circuit breakers."""

    def __init__(self):
        self.kill_switch_active = settings.SAFE_KILL_SWITCH_ACTIVE
        self.max_risk_per_trade = settings.MAX_RISK_PER_TRADE
        self.max_daily_loss_pct = settings.MAX_DAILY_LOSS_PCT
        self.max_drawdown_pct = settings.MAX_DRAWDOWN_PCT
        self.max_consecutive_losses = settings.MAX_CONSECUTIVE_LOSSES
        self.cooldown_duration_sec = settings.COOLDOWN_MINUTES * 60
        self.max_open_positions = settings.MAX_OPEN_POSITIONS
        self.max_leverage = settings.DEFAULT_LEVERAGE

        # Runtime State
        self.high_watermark = settings.INITIAL_PAPER_BALANCE
        self.daily_start_balance = settings.INITIAL_PAPER_BALANCE
        self.current_day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        self.consecutive_losses = 0
        self.cooldown_until: Optional[float] = None
        self.cooldown_reason: Optional[str] = None

    def toggle_kill_switch(self, active: bool, reason: str = "User toggle"):
        """Emergency kill switch to halt all new order generation."""
        self.kill_switch_active = active
        status = "ACTIVATED" if active else "DEACTIVATED"
        logger.warning(f"🚨 KILL SWITCH {status}: {reason}")

    def update_equity_watermark(self, current_equity: float):
        """Updates high watermark and checks daily rollover."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self.current_day_str:
            self.current_day_str = today
            self.daily_start_balance = current_equity
            logger.info(f"Daily risk reset for {today}. Starting balance: ${current_equity:.2f}")

        if current_equity > self.high_watermark:
            self.high_watermark = current_equity

    def record_trade_outcome(self, net_pnl: float, direction: str):
        """Updates streak counters and cooldown state upon trade close."""
        if net_pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"Loss recorded. Consecutive losses: {self.consecutive_losses}")
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.trigger_cooldown(f"Hit {self.consecutive_losses} consecutive losses")
        else:
            self.consecutive_losses = 0
            # Expire cooldown on successful trade
            self.cooldown_until = None
            self.cooldown_reason = None

    def trigger_cooldown(self, reason: str):
        """Engages temporary trading cooldown timer."""
        self.cooldown_until = time.time() + self.cooldown_duration_sec
        self.cooldown_reason = reason
        logger.warning(f"Cooldown active until {datetime.fromtimestamp(self.cooldown_until, timezone.utc)}: {reason}")

    def is_cooldown_active(self) -> Tuple[bool, Optional[str]]:
        """Checks if cooldown is currently active with proper expiration."""
        if self.cooldown_until is not None:
            now = time.time()
            if now < self.cooldown_until:
                remaining = int(self.cooldown_until - now)
                return True, f"In cooldown ({remaining}s remaining): {self.cooldown_reason}"
            else:
                self.cooldown_until = None
                self.cooldown_reason = None
        return False, None

    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        stop_loss_pct: float,
        equity: float
    ) -> Tuple[float, Optional[str]]:
        """Fixed-fractional position sizing:

        Position Value = (Equity * Risk_Pct) / Stop_Loss_Pct
        Quantity = Position_Value / Price
        """
        if price <= 0 or stop_loss_pct <= 0 or equity <= 0:
            return 0.0, "INVALID_INPUTS_FOR_SIZING"

        # Capital at risk for this trade
        risk_capital = equity * self.max_risk_per_trade

        # Maximum notional allowed based on max leverage
        max_notional = equity * self.max_leverage

        # Desired notional to match stop-loss risk
        desired_notional = risk_capital / stop_loss_pct
        allocated_notional = min(desired_notional, max_notional)

        raw_qty = allocated_notional / price

        # Symbol precision and exchange filters
        filt = SYMBOL_FILTERS.get(symbol, {"min_qty": 0.001, "step_size": 0.001, "min_notional": 5.0})
        step = filt["step_size"]
        min_qty = filt["min_qty"]
        min_notional = filt["min_notional"]

        # Round to step size
        qty = round(raw_qty - (raw_qty % step), 6)

        if qty < min_qty:
            return 0.0, f"QUANTITY_BELOW_MIN_QTY ({qty} < {min_qty})"

        if (qty * price) < min_notional:
            return 0.0, f"NOTIONAL_BELOW_EXCHANGE_MINIMUM ({qty * price:.2f} < {min_notional})"

        return qty, None

    def validate_trade_order(
        self,
        symbol: str,
        side: str,
        price: float,
        stop_loss_pct: float,
        current_equity: float,
        open_positions: List[Dict[str, Any]]
    ) -> Tuple[bool, float, str]:
        """Runs complete pre-trade risk validation stack."""
        self.update_equity_watermark(current_equity)

        # 1. Kill Switch Check
        if self.kill_switch_active:
            return False, 0.0, "REJECTED: EMERGENCY_KILL_SWITCH_ACTIVE"

        # 2. Cooldown Check
        in_cooldown, cooldown_msg = self.is_cooldown_active()
        if in_cooldown:
            return False, 0.0, f"REJECTED: {cooldown_msg}"

        # 3. Daily Loss Limit Check
        daily_loss_pct = (self.daily_start_balance - current_equity) / self.daily_start_balance
        if daily_loss_pct >= self.max_daily_loss_pct:
            return False, 0.0, f"REJECTED: DAILY_LOSS_LIMIT_REACHED ({daily_loss_pct*100:.2f}% >= {self.max_daily_loss_pct*100:.1f}%)"

        # 4. Trailing Drawdown Limit Check
        drawdown_pct = (self.high_watermark - current_equity) / self.high_watermark
        if drawdown_pct >= self.max_drawdown_pct:
            return False, 0.0, f"REJECTED: MAX_DRAWDOWN_LIMIT_REACHED ({drawdown_pct*100:.2f}% >= {self.max_drawdown_pct*100:.1f}%)"

        # 5. Concurrent Positions Check
        if len(open_positions) >= self.max_open_positions:
            return False, 0.0, f"REJECTED: MAX_OPEN_POSITIONS_REACHED ({len(open_positions)}/{self.max_open_positions})"

        # Check existing position for same symbol
        for pos in open_positions:
            if pos.get("symbol") == symbol and pos.get("status") == "OPEN":
                return False, 0.0, f"REJECTED: POSITION_ALREADY_EXISTS_FOR_{symbol}"

        # 6. Correlation / Directional Exposure Check
        same_direction_count = sum(1 for p in open_positions if p.get("side") == side and p.get("status") == "OPEN")
        if same_direction_count >= 2:
            return False, 0.0, f"REJECTED: CONCENTRATION_RISK (Already 2 {side} positions open)"

        # 7. Position Sizing
        quantity, size_err = self.calculate_position_size(symbol, price, stop_loss_pct, current_equity)
        if quantity <= 0:
            return False, 0.0, f"REJECTED: SIZING_ERROR ({size_err})"

        return True, quantity, "RISK_VALIDATION_PASSED"

    def get_status(self, current_equity: float) -> Dict[str, Any]:
        """Provides snapshot of risk utilization for API and UI."""
        self.update_equity_watermark(current_equity)
        daily_loss_pct = max(0.0, (self.daily_start_balance - current_equity) / self.daily_start_balance)
        drawdown_pct = max(0.0, (self.high_watermark - current_equity) / self.high_watermark)
        in_cooldown, cooldown_msg = self.is_cooldown_active()

        return {
            "kill_switch_active": self.kill_switch_active,
            "in_cooldown": in_cooldown,
            "cooldown_message": cooldown_msg,
            "current_equity": round(current_equity, 2),
            "high_watermark": round(self.high_watermark, 2),
            "daily_loss_pct": round(daily_loss_pct * 100, 2),
            "max_daily_loss_pct": round(self.max_daily_loss_pct * 100, 2),
            "drawdown_pct": round(drawdown_pct * 100, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct * 100, 2),
            "consecutive_losses": self.consecutive_losses,
            "max_consecutive_losses": self.max_consecutive_losses
        }


risk_engine = RiskEngine()
