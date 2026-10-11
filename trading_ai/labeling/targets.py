"""Target Labeling Engine: 3-Class Target Generator.

Labels:
-  1 : BUY / LONG Opportunity
- -1 : SELL / SHORT Opportunity
-  0 : NEUTRAL / NO TRADE
"""

from typing import Any, Dict, List, Tuple


class TargetLabeler:
    def __init__(
        self,
        horizon: int = 4,
        vol_multiplier: float = 1.0,
        min_threshold_pct: float = 0.003  # 0.3% minimum price movement
    ):
        self.horizon = horizon
        self.vol_multiplier = vol_multiplier
        self.min_threshold_pct = min_threshold_pct

    def compute_labels(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Labels feature records with future returns and discrete targets.

        Drops the last `horizon` records where future price is unknown.
        """
        n = len(features)
        if n <= self.horizon:
            return []

        out = []
        for i in range(n - self.horizon):
            curr = features[i]
            future = features[i + self.horizon]

            curr_close = curr["close"]
            future_close = future["close"]

            ret = (future_close - curr_close) / curr_close
            atr_ratio = curr.get("atr_ratio", 0.01)

            # Volatility-adjusted barrier threshold
            threshold = max(self.min_threshold_pct, atr_ratio * self.vol_multiplier)

            if ret > threshold:
                target = 1
            elif ret < -threshold:
                target = -1
            else:
                target = 0

            labeled = dict(curr)
            labeled["future_return"] = round(ret, 5)
            labeled["target"] = target
            out.append(labeled)

        return out

    def get_class_distribution(self, labeled: List[Dict[str, Any]]) -> Dict[str, float]:
        if not labeled:
            return {}
        total = len(labeled)
        buys = sum(1 for r in labeled if r.get("target") == 1)
        sells = sum(1 for r in labeled if r.get("target") == -1)
        neutrals = sum(1 for r in labeled if r.get("target") == 0)
        return {
            "BUY (1)": round((buys / total) * 100, 2),
            "SELL (-1)": round((sells / total) * 100, 2),
            "NEUTRAL (0)": round((neutrals / total) * 100, 2)
        }


target_labeler = TargetLabeler()
