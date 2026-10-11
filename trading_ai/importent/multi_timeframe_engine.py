# =========================
# IMPORTS
# =========================
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import joblib
import pandas as pd
import time
import csv
from datetime import datetime, timezone

from trading_ai.real_time.trend_4h import detect_trend
from trading_ai.real_time.entry_5m import check_entry
from trading_ai.real_time.trade_monitor import monitor_trades
from trading_ai.real_time.telegram_alert import send_alert


# =========================
# BASE DIRECTORY FIX
# =========================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =========================
# CONFIG
# =========================

# Professional edge-based thresholds
EDGE_THRESHOLD = 0.15

# Trade quality scoring weights
SCORE_REQUIREMENTS = {
    "4h_trend_aligned": 1,      # +1 if 4H trend aligns with signal
    "1h_strong_edge": 1,        # +1 if 1H edge > threshold
    "volume_confirmation": 1,   # +1 if volume indicator strong
    "momentum_strong": 1        # +1 if momentum indicator strong
}
MIN_QUALITY_SCORE = 3  # Need at least 3/4 confirmations


# =========================
# LOG SIGNAL PERFORMANCE
# =========================

def log_signal(direction, confidence):
    log_path = os.path.join(BASE_DIR, "performance_log.csv")

    with open(log_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now(timezone.utc),
            direction,
            round(confidence, 3)
        ])


# =========================
# GET 1H ML BIAS (EDGE-BASED)
# =========================

def get_1h_bias():
    """
    Professional 1H signal using EDGE instead of confidence.
    Returns (edge_value, direction, probs_dict)
    """
    from trading_ai.real_time.predict_1h import (
        fetch_1h_data,
        add_features,
        FEATURE_COLUMNS
    )

    # ✅ FIXED MODEL PATH
    model_path = os.path.join(BASE_DIR, "models", "model_1h.pkl")

    model = joblib.load(model_path)

    df = fetch_1h_data()
    df = add_features(df)

    latest = df.iloc[-1]

    X = pd.DataFrame(
        [latest[FEATURE_COLUMNS].values],
        columns=FEATURE_COLUMNS
    )

    probabilities = model.predict_proba(X)[0]
    classes = model.classes_

    prob_dict = dict(zip(classes, probabilities))

    up_prob = prob_dict.get(1, 0)
    down_prob = prob_dict.get(-1, 0)
    
    # Professional: Calculate edge
    edge = up_prob - down_prob
    direction = "UP" if edge > 0 else "DOWN"

    return abs(edge), direction, prob_dict


# =========================
# TRADE QUALITY SCORING
# =========================

def calculate_trade_score(trend_4h, edge_1h, up_prob, down_prob):
    """
    Professional trade quality scoring.
    
    Score components:
    1. Trend alignment (4H trend matches signal)
    2. Strong 1H edge
    3. Volume confirmation (implicit in probabilities)
    4. Momentum strength (implicit in probabilities)
    
    Returns score 0-4. Only trade if score >= 3.
    """
    score = 0
    details = {}
    
    # Component 1: 4H Trend Alignment
    if trend_4h in ["UP", "DOWN"]:
        score += 1
        details["4h_trend"] = "✅ Strong trend exists"
    else:
        details["4h_trend"] = "⚠️  Weak/neutral trend"
    
    # Component 2: 1H Strong Edge
    if edge_1h > EDGE_THRESHOLD:
        score += 1
        details["1h_edge"] = f"✅ Strong edge: {edge_1h:.3f}"
    else:
        details["1h_edge"] = f"⚠️  Weak edge: {edge_1h:.3f}"
    
    # Component 3: Probability separation (model conviction)
    prob_separation = abs(up_prob - down_prob)
    if prob_separation > 0.20:  # Clear probability spread
        score += 1
        details["conviction"] = f"✅ Clear conviction: {prob_separation:.3f}"
    else:
        details["conviction"] = f"⚠️  Uncertain model: {prob_separation:.3f}"
    
    # Component 4: Not near 50-50 (strong prediction)
    winner_prob = max(up_prob, down_prob)
    if winner_prob > 0.55:  # Clearly favors one direction
        score += 1
        details["certainty"] = f"✅ Model certain: {winner_prob:.3f}"
    else:
        details["certainty"] = f"⚠️  Model unsure: {winner_prob:.3f}"
    
    return score, details

# =========================
# MAIN ENGINE LOGIC
# =========================

def main():
    print("\n========== MULTI TIMEFRAME ENGINE (PROFESSIONAL) ==========")

    # Step 1 — Detect 4H Trend
    trend_4h = detect_trend()
    
    # Skip trading in bad regimes
    if trend_4h in ["RANGE", "HIGH_VOL"]:
        print(f"\n⛔ Market regime unfavorable ({trend_4h}). No trades.")
        return

    # Step 2 — Get 1H ML Bias (EDGE-BASED)
    edge_1h, direction_1h, prob_dict = get_1h_bias()
    up_prob = prob_dict.get(1, 0)
    down_prob = prob_dict.get(-1, 0)

    print(f"\n4H Trend: {trend_4h}")
    print(f"1H Edge: {edge_1h:.3f} ({direction_1h})")

    # =========================
    # TRADE QUALITY SCORING
    # =========================
    
    score, score_details = calculate_trade_score(trend_4h, edge_1h, up_prob, down_prob)
    
    print(f"\n📊 TRADE QUALITY SCORE: {score}/4")
    for component, status in score_details.items():
        print(f"  {status}")
    
    if score < MIN_QUALITY_SCORE:
        print(f"\n⛔ Low quality score ({score} < {MIN_QUALITY_SCORE}). No trade.")
        return
    
    print(f"\n✅ High quality score ({score} >= {MIN_QUALITY_SCORE}). Proceeding...")

    # =========================
    # LONG FLOW (EDGE-BASED)
    # =========================

    if (
        trend_4h == "UP"
        and direction_1h == "UP"
        and edge_1h > EDGE_THRESHOLD
    ):
        print("\n✅ Higher timeframe LONG bias confirmed.")
        print("Checking 5M entry...")

        if check_entry("LONG"):
            print("🚀 FINAL LONG ENTRY CONFIRMED")

            log_signal("LONG", edge_1h)

            send_alert(
                f"🚀 FINAL LONG ENTRY CONFIRMED\n"
                f"4H: UP | 1H Edge: {edge_1h:.3f}\n"
                f"Quality Score: {score}/4"
            )

    # =========================
    # SHORT FLOW (EDGE-BASED)
    # =========================

    elif (
        trend_4h == "DOWN"
        and direction_1h == "DOWN"
        and edge_1h > EDGE_THRESHOLD
    ):
        print("\n✅ Higher timeframe SHORT bias confirmed.")
        print("Checking 5M entry...")

        if check_entry("SHORT"):
            print("🔥 FINAL SHORT ENTRY CONFIRMED")

            log_signal("SHORT", edge_1h)

            send_alert(
                f"🔥 FINAL SHORT ENTRY CONFIRMED\n"
                f"4H: DOWN | 1H Edge: {edge_1h:.3f}\n"
                f"Quality Score: {score}/4"
            )

    else:
        print("\n⛔ No high-quality trading bias. Stand aside.")


# =========================
# LOOP SYSTEM (EVERY 5 MIN)
# =========================

def run_loop():
    print("🚀 Starting Live AI Trading System...")

    while True:
        now = datetime.now(timezone.utc)

        # Run only at exact 5-minute marks
        if now.minute % 5 == 0 and now.second < 5:
            print("\nRunning engine at:", now)

            main()              # check new entries
            monitor_trades()    # update TP/SL status

            time.sleep(60)  # prevent double execution

        time.sleep(1)


# =========================
# START ENGINE
# =========================

if __name__ == "__main__":
    run_loop()
