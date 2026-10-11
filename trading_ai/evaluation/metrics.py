"""Classification and Financial Performance Metrics.

Provides:
- Multi-class Accuracy & Balanced Accuracy
- Confusion Matrix
- Precision, Recall, F1-Score per class and Macro-F1
- Financial Sharpe Ratio, Drawdown, Win Rate, and Profit Factor

Runs cleanly without external C-extensions.
"""

from collections import Counter
import math
from typing import Any, Dict, List


def evaluate_classifier(
    y_true: List[int],
    y_pred: List[int],
    y_proba: List[List[float]] = None,
    class_labels: List[int] = [-1, 0, 1]
) -> Dict[str, Any]:
    """Computes comprehensive classification metrics."""
    n = len(y_true)
    if n == 0:
        return {"accuracy": 0.0, "balanced_accuracy": 0.0, "macro_f1": 0.0}

    # Accuracy
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    acc = correct / n

    # Confusion matrix & per-class precision / recall
    label_to_idx = {l: i for i, l in enumerate(class_labels)}
    k = len(class_labels)
    cm = [[0 for _ in range(k)] for _ in range(k)]

    for yt, yp in zip(y_true, y_pred):
        if yt in label_to_idx and yp in label_to_idx:
            cm[label_to_idx[yt]][label_to_idx[yp]] += 1

    recalls = []
    class_report = {}
    f1_scores = []

    for c in class_labels:
        idx = label_to_idx[c]
        tp = cm[idx][idx]
        actual_pos = sum(cm[idx])
        pred_pos = sum(cm[r][idx] for r in range(k))

        prec = tp / pred_pos if pred_pos > 0 else 0.0
        rec = tp / actual_pos if actual_pos > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        recalls.append(rec)
        f1_scores.append(f1)
        class_report[str(c)] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "support": actual_pos
        }

    bal_acc = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    return {
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "confusion_matrix": cm,
        "classes": class_labels,
        "class_report": class_report
    }


def calculate_financial_performance(
    trades: List[Dict[str, Any]],
    risk_free_rate: float = 0.0
) -> Dict[str, Any]:
    """Computes trading economic metrics: Sharpe, Drawdown, Win Rate, Profit Factor."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "net_pnl": 0.0
        }

    pnl_list = [t.get("net_pnl", 0.0) for t in trades]
    wins = [p for p in pnl_list if p > 0]
    losses = [abs(p) for p in pnl_list if p < 0]

    win_rate = (len(wins) / len(trades)) * 100.0 if trades else 0.0
    profit_factor = (sum(wins) / sum(losses)) if sum(losses) > 0 else (99.0 if sum(wins) > 0 else 1.0)

    # Max Drawdown
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnl_list:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio
    n = len(pnl_list)
    mean_pnl = sum(pnl_list) / n
    variance = sum((p - mean_pnl) ** 2 for p in pnl_list) / n
    std_pnl = math.sqrt(variance)
    sharpe = ((mean_pnl - risk_free_rate) / (std_pnl + 1e-9)) * math.sqrt(365 * 24) if std_pnl > 0 else 0.0

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(float(profit_factor), 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 2),
        "net_pnl": round(float(sum(pnl_list)), 2)
    }
