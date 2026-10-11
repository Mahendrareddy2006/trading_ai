import os
import json
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATS_FILE = os.path.join(BASE_DIR, "statistics_state.json")


# ==========================================================
# LOAD / SAVE
# ==========================================================
def load_stats():
    if not os.path.exists(STATS_FILE):
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "daily_pnl": 0.0,
            "last_day": time.strftime("%Y-%m-%d")
        }

    with open(STATS_FILE, "r") as f:
        return json.load(f)


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)


# ==========================================================
# RESET DAILY PNL IF NEW DAY
# ==========================================================
def reset_daily_if_needed(stats):
    today = time.strftime("%Y-%m-%d")

    if stats["last_day"] != today:
        stats["daily_pnl"] = 0.0
        stats["last_day"] = today

    return stats


# ==========================================================
# RECORD TRADE RESULT
# ==========================================================
def record_trade_result(pnl, edge=None):
    """
    Professional: Track P&L by edge bucket
    to correlate signal quality with returns
    """
    stats = load_stats()
    stats = reset_daily_if_needed(stats)

    stats["total_trades"] += 1
    stats["total_pnl"] += pnl
    stats["daily_pnl"] += pnl

    if pnl > 0:
        stats["wins"] += 1
    else:
        stats["losses"] += 1
    
    # Professional: Track edge-based statistics
    if edge is not None:
        if "edge_stats" not in stats:
            stats["edge_stats"] = {}
        
        edge_bucket = f"{edge:.2f}"  # Bucket by edge value
        if edge_bucket not in stats["edge_stats"]:
            stats["edge_stats"][edge_bucket] = {"trades": 0, "wins": 0, "pnl": 0}
        
        stats["edge_stats"][edge_bucket]["trades"] += 1
        stats["edge_stats"][edge_bucket]["pnl"] += pnl
        if pnl > 0:
            stats["edge_stats"][edge_bucket]["wins"] += 1

    save_stats(stats)


def get_edge_correlation():
    """
    Professional analysis:
    Returns win rate by edge bucket
    
    Example output:
    edge 0.15-0.20: 52% win rate
    edge 0.20-0.25: 58% win rate
    edge >0.30: 65% win rate
    """
    stats = load_stats()
    
    if "edge_stats" not in stats:
        return None
    
    print("\n" + "="*50)
    print("EDGE-BASED PERFORMANCE ANALYSIS")
    print("="*50)
    
    for edge_bucket in sorted(stats["edge_stats"].keys()):
        data = stats["edge_stats"][edge_bucket]
        if data["trades"] > 0:
            win_rate = (data["wins"] / data["trades"]) * 100
            avg_pnl = data["pnl"] / data["trades"]
            print(f"Edge {edge_bucket}: {data['trades']} trades | "
                  f"{win_rate:.1f}% win rate | "
                  f"Avg P&L: {avg_pnl:.4f}")


# ==========================================================
# GET STATISTICS
# ==========================================================
def get_statistics():

    stats = load_stats()
    stats = reset_daily_if_needed(stats)

    total = stats["total_trades"]

    if total > 0:
        win_rate = (stats["wins"] / total) * 100
    else:
        win_rate = 0

    return {
        "total_trades": total,
        "wins": stats["wins"],
        "losses": stats["losses"],
        "win_rate": round(win_rate, 2),
        "total_pnl": round(stats["total_pnl"], 2),
        "daily_pnl": round(stats["daily_pnl"], 2)
    }