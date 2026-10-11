"""
Professional Walk-Forward Training

Simulates real trading conditions by using time-based splits
Prevents lookahead bias that simple train/test splits create

Example:
Train: Jan-Mar  → Test: Apr
Train: Feb-Apr  → Test: May
Train: Mar-May  → Test: Jun

This matches how real trading works: train on past, test on future
"""

import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report
import joblib
from datetime import datetime, timedelta


DATA_FOLDER = "data"
MODEL_FOLDER = "models"


def load_all_data():
    """Load and concatenate all labeled training data"""
    dfs = []
    for file in os.listdir(DATA_FOLDER):
        if file.startswith("labeled_features_") and file.endswith("_1h.csv"):
            df = pd.read_csv(os.path.join(DATA_FOLDER, file))
            # Add timestamp if not present
            if "timestamp" not in df.columns:
                df["sort_order"] = range(len(df))
            dfs.append(df)
    
    if not dfs:
        raise ValueError("No labeled data found!")
    
    return pd.concat(dfs, ignore_index=True)


def walk_forward_analysis(window_days=90, test_days=30):
    """
    Professional walk-forward analysis
    
    Args:
        window_days: Training window size (90 days)
        test_days: Test window size (30 days)
    
    Returns:
        Overall statistics across all windows
    """
    
    df = load_all_data()
    
    # Remove labels=0
    df = df[df["label"] != 0].reset_index(drop=True)
    
    print("\n" + "="*70)
    print("WALK-FORWARD TRAINING ANALYSIS (Professional)")
    print("="*70)
    
    total_test_samples = 0
    total_correct = 0
    all_accuracies = []
    
    # Simulate walk-forward windows
    # Use row index as proxy for time (since real timestamps often missing)
    total_rows = len(df)
    window_size = int(total_rows * (window_days / 180))  # Assume ~180 days total
    test_size = int(total_rows * (test_days / 180))
    
    window_num = 0
    
    # Create overlapping windows
    for start_idx in range(0, total_rows - window_size - test_size, test_size // 2):
        window_num += 1
        
        train_end = start_idx + window_size
        test_end = train_end + test_size
        
        if test_end > total_rows:
            break
        
        # Train/Test split (time-based)
        train_data = df.iloc[start_idx:train_end]
        test_data = df.iloc[train_end:test_end]
        
        if len(train_data) < 100 or len(test_data) < 50:
            continue
        
        X_train = train_data[[col for col in train_data.columns if col != "label"]]
        y_train = train_data["label"]
        X_test = test_data[[col for col in test_data.columns if col != "label"]]
        y_test = test_data["label"]
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Calibrate
        calibrated = CalibratedClassifierCV(model, method="isotonic", cv=3)
        calibrated.fit(X_train, y_train)
        
        # Test
        preds = calibrated.predict(X_test)
        accuracy = accuracy_score(y_test, preds)
        
        all_accuracies.append(accuracy)
        total_correct += (preds == y_test.values).sum()
        total_test_samples += len(y_test)
        
        print(f"Window {window_num:2d} | Train: {len(train_data):4d} samples | "
              f"Test: {len(test_data):3d} samples | Accuracy: {accuracy:.4f}")
    
    if all_accuracies:
        avg_accuracy = np.mean(all_accuracies)
        std_accuracy = np.std(all_accuracies)
        overall_accuracy = total_correct / total_test_samples
        
        print("\n" + "="*70)
        print(f"WALK-FORWARD RESULTS:")
        print(f"Average Accuracy: {avg_accuracy:.4f} ± {std_accuracy:.4f}")
        print(f"Overall Accuracy: {overall_accuracy:.4f}")
        print(f"Total Windows: {window_num}")
        print(f"Total Test Samples: {total_test_samples}")
        print("="*70 + "\n")
        
        return {
            "avg_accuracy": avg_accuracy,
            "std_accuracy": std_accuracy,
            "overall_accuracy": overall_accuracy,
            "windows": window_num,
            "is_robust": std_accuracy < 0.05  # Low variance = robust model
        }
    
    return None


def train_production_model():
    """
    After walk-forward validation passes,
    train final production model on ALL data
    """
    
    df = load_all_data()
    df = df[df["label"] != 0].reset_index(drop=True)
    
    X = df[[col for col in df.columns if col != "label"]]
    y = df["label"]
    
    print("\nTraining final production model on all data...")
    
    model = RandomForestClassifier(
        n_estimators=600,
        max_depth=15,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X, y)
    
    # Calibrate on subset
    split_idx = int(len(X) * 0.8)
    calibrated = CalibratedClassifierCV(
        model, 
        method="isotonic", 
        cv=3
    )
    calibrated.fit(X.iloc[:split_idx], y.iloc[:split_idx])
    
    # Save
    if not os.path.exists(MODEL_FOLDER):
        os.makedirs(MODEL_FOLDER)
    
    model_path = os.path.join(MODEL_FOLDER, "model_1h_production.pkl")
    joblib.dump(calibrated, model_path)
    
    print(f"✅ Production model saved: {model_path}")
    
    return calibrated


if __name__ == "__main__":
    results = walk_forward_analysis()
    if results and results["is_robust"]:
        print("✅ Walk-forward validation PASSED - Model is robust")
        train_production_model()
    else:
        print("❌ Walk-forward validation FAILED - Model needs improvement")
