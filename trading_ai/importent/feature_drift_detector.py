"""
Professional Feature Drift Monitoring

Detects when market conditions change significantly
from training data distribution (Data Distribution Shift)

If drift detected → Model becomes unreliable → Retrain recommended
"""

import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
import os

DATA_FOLDER = "data"
DRIFT_THRESHOLD = 0.05  # 5% threshold for statistically significant drift


def load_training_data():
    """Load original training data for distribution comparison"""
    dfs = []
    for file in os.listdir(DATA_FOLDER):
        if file.startswith("features_") and file.endswith("_1h.csv"):
            df = pd.read_csv(os.path.join(DATA_FOLDER, file))
            dfs.append(df)
    
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def detect_drift(live_df, training_df=None):
    """
    Professional drift detection using Kolmogorov-Smirnov test
    
    Returns:
        (has_drift: bool, p_values: dict, report: str)
    """
    
    if training_df is None:
        training_df = load_training_data()
    
    if training_df is None:
        return False, {}, "No training data found"
    
    # Features to monitor (most important ones)
    features_to_check = [
        "ema_9", "ema_21", "rsi", "atr", "vol_ratio",
        "dist_ema9", "ema_trend_strength", "momentum_3"
    ]
    
    p_values = {}
    drifted_features = []
    
    print("\n" + "="*60)
    print("FEATURE DRIFT DETECTION (Professional)")
    print("="*60)
    
    for feature in features_to_check:
        if feature not in live_df.columns or feature not in training_df.columns:
            continue
        
        # Kolmogorov-Smirnov test
        # H0: Distributions are the same
        # If p-value < 0.05: Reject H0 → Distributions differ significantly
        statistic, p_value = ks_2samp(
            training_df[feature].dropna(),
            live_df[feature].dropna()
        )
        
        p_values[feature] = p_value
        
        if p_value < DRIFT_THRESHOLD:
            drifted_features.append(feature)
            status = "⚠️  DRIFTED"
        else:
            status = "✅ OK"
        
        print(f"{feature:20s} | p-value: {p_value:.4f} | {status}")
    
    has_drift = len(drifted_features) > 0
    
    report = f"\n{'='*60}\n"
    if has_drift:
        report += f"⚠️  DRIFT DETECTED: {len(drifted_features)} features drifted\n"
        report += f"Affected features: {', '.join(drifted_features)}\n"
        report += "Recommendation: Retrain model with recent data\n"
    else:
        report += "✅ No significant drift detected\n"
        report += "Model distribution still valid\n"
    report += f"{'='*60}\n"
    
    print(report)
    
    return has_drift, p_values, report


def monitor_drift_continuous(live_data_stream):
    """
    Continuous drift monitoring (for live trading)
    
    Call periodically to check if model needs retraining
    """
    training_data = load_training_data()
    
    if training_data is None:
        return {"status": "NO_TRAINING_DATA"}
    
    # Use recent 100 candles
    recent_data = live_data_stream.tail(100)
    
    has_drift, p_values, report = detect_drift(recent_data, training_data)
    
    return {
        "has_drift": has_drift,
        "p_values": p_values,
        "report": report,
        "action": "RETRAIN_RECOMMENDED" if has_drift else "CONTINUE_TRADING"
    }


if __name__ == "__main__":
    print("Feature drift detector module loaded")
