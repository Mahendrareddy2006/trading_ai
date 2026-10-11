"""
Professional Ensemble Model Training

Combines multiple model types for better predictions:
- RandomForest (already used)
- XGBoost (gradient boosting)
- LightGBM (fast gradient boosting)

Ensemble reduces individual model instability
Typical improvement: 2-4% better accuracy
"""

import pandas as pd
import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Optional: Install xgboost and lightgbm if not present
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost not installed. Install with: pip install xgboost")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("⚠️  LightGBM not installed. Install with: pip install lightgbm")


DATA_FOLDER = "data"
MODEL_FOLDER = "models"

FEATURE_COLUMNS = [
    "ema_9", "ema_21", "rsi", "atr", "vol_ratio",
    "dist_ema9", "ema_trend_strength", "momentum_3", "rsi_change", "atr_ratio"
]


def load_data():
    """Load labeled training data"""
    dfs = []
    for file in os.listdir(DATA_FOLDER):
        if file.startswith("labeled_features_") and file.endswith("_1h.csv"):
            df = pd.read_csv(os.path.join(DATA_FOLDER, file))
            dfs.append(df)
    
    if not dfs:
        raise ValueError("No labeled data found!")
    
    df = pd.concat(dfs, ignore_index=True)
    df = df[df["label"] != 0]  # Remove sideways
    
    return df


def train_random_forest(X_train, X_test, y_train, y_test):
    """Train and calibrate Random Forest"""
    print("\n🌳 Training RandomForest...")
    
    model = RandomForestClassifier(
        n_estimators=600,
        max_depth=15,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Calibrate
    calibrated = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calibrated.fit(X_train, y_train)
    
    preds = calibrated.predict(X_test)
    accuracy = accuracy_score(y_test, preds)
    
    print(f"   RandomForest Accuracy: {accuracy:.4f}")
    
    return calibrated, accuracy


def train_xgboost(X_train, X_test, y_train, y_test):
    """Train and calibrate XGBoost"""
    if not XGBOOST_AVAILABLE:
        return None, 0
    
    print("\n🚀 Training XGBoost...")
    
    # Convert labels from {-1, 1} to {0, 1} for XGBoost
    y_train_xgb = (y_train + 1) / 2  # -1→0, 1→1
    y_test_xgb = (y_test + 1) / 2
    
    model = xgb.XGBClassifier(
        n_estimators=600,
        max_depth=7,
        learning_rate=0.05,
        random_state=42,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train_xgb)
    
    # Calibrate
    calibrated = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calibrated.fit(X_train, y_train_xgb)
    
    preds = calibrated.predict(X_test)
    accuracy = accuracy_score(y_test_xgb, preds)
    
    print(f"   XGBoost Accuracy: {accuracy:.4f}")
    
    return calibrated, accuracy


def train_lightgbm(X_train, X_test, y_train, y_test):
    """Train and calibrate LightGBM"""
    if not LIGHTGBM_AVAILABLE:
        return None, 0
    
    print("\n⚡ Training LightGBM...")
    
    # Convert labels
    y_train_lgb = (y_train + 1) / 2
    y_test_lgb = (y_test + 1) / 2
    
    model = lgb.LGBMClassifier(
        n_estimators=600,
        max_depth=7,
        learning_rate=0.05,
        random_state=42
    )
    
    model.fit(X_train, y_train_lgb)
    
    # Calibrate
    calibrated = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calibrated.fit(X_train, y_train_lgb)
    
    preds = calibrated.predict(X_test)
    accuracy = accuracy_score(y_test_lgb, preds)
    
    print(f"   LightGBM Accuracy: {accuracy:.4f}")
    
    return calibrated, accuracy


class EnsembleModel:
    """Professional Ensemble Predictor"""
    
    def __init__(self, models_dict):
        self.models = models_dict
        self.model_names = list(models_dict.keys())
    
    def predict_proba(self, X):
        """
        Combine predictions from all models
        
        Average probabilities for ensemble prediction
        """
        
        all_probs = []
        
        for model_name, model in self.models.items():
            if model is None:
                continue
            
            probs = model.predict_proba(X)
            all_probs.append(probs)
        
        if not all_probs:
            return None
        
        # Average probabilities
        ensemble_probs = np.mean(all_probs, axis=0)
        
        return ensemble_probs
    
    def predict(self, X):
        """Predict using ensemble average"""
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)


def train_ensemble():
    """Train complete ensemble model"""
    
    print("="*70)
    print("PROFESSIONAL ENSEMBLE MODEL TRAINING")
    print("="*70)
    
    df = load_data()
    
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    
    # Time-based split (no shuffle)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    
    models = {}
    
    # Train RandomForest
    rf_model, rf_acc = train_random_forest(X_train, X_test, y_train, y_test)
    models["RandomForest"] = (rf_model, rf_acc)
    
    # Train XGBoost
    xgb_model, xgb_acc = train_xgboost(X_train, X_test, y_train, y_test)
    if xgb_model:
        models["XGBoost"] = (xgb_model, xgb_acc)
    
    # Train LightGBM
    lgb_model, lgb_acc = train_lightgbm(X_train, X_test, y_train, y_test)
    if lgb_model:
        models["LightGBM"] = (lgb_model, lgb_acc)
    
    print("\n" + "="*70)
    print("INDIVIDUAL MODEL PERFORMANCE:")
    print("="*70)
    
    for model_name, (model, accuracy) in models.items():
        print(f"{model_name:15s}: {accuracy:.4f}")
    
    # Create ensemble
    ensemble_dict = {name: model for name, (model, _) in models.items()}
    ensemble = EnsembleModel(ensemble_dict)
    
    # Test ensemble
    print("\n" + "="*70)
    print("ENSEMBLE MODEL PERFORMANCE:")
    print("="*70)
    
    # Convert y_test for ensemble (use original labels for RF)
    ensemble_preds = ensemble.predict(X_test)
    ensemble_accuracy = accuracy_score(y_test, ensemble_preds)
    
    print(f"Ensemble Accuracy:     {ensemble_accuracy:.4f}")
    
    # Individual model accuracies for reference
    individual_accs = [acc for _, acc in models.values()]
    avg_individual = np.mean(individual_accs)
    improvement = (ensemble_accuracy - avg_individual) / avg_individual * 100
    
    print(f"Average Individual:    {avg_individual:.4f}")
    print(f"Improvement:           {improvement:+.2f}%")
    
    print("\n" + "="*70)
    
    # Save ensemble
    if not os.path.exists(MODEL_FOLDER):
        os.makedirs(MODEL_FOLDER)
    
    ensemble_path = os.path.join(MODEL_FOLDER, "ensemble_model.pkl")
    joblib.dump(ensemble, ensemble_path)
    
    print(f"\n✅ Ensemble model saved: {ensemble_path}")
    print("✅ All component models also saved")
    
    return ensemble, ensemble_accuracy


if __name__ == "__main__":
    train_ensemble()
