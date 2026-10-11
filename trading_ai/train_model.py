import pandas as pd
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.calibration import CalibratedClassifierCV  # Professional: Probability calibration

# ==============================
# CONFIG
# ==============================

DATA_FOLDER = "data"
MODEL_FOLDER = "models"
MODEL_NAME = "model_1h.pkl"

FEATURE_COLUMNS = [
    "ema_9",
    "ema_21",
    "rsi",
    "atr",
    "vol_ratio",
    "dist_ema9",
    "ema_trend_strength",
    "momentum_3",
    "rsi_change",
    "atr_ratio"
]

# ==============================
# LOAD DATA
# ==============================

def load_data():
    dfs = []

    for file in os.listdir(DATA_FOLDER):
        if file.startswith("labeled_features_") and file.endswith("_1h.csv"):
            df = pd.read_csv(os.path.join(DATA_FOLDER, file))
            dfs.append(df)

    if not dfs:
        raise ValueError("No labeled 1H data found!")

    df = pd.concat(dfs, ignore_index=True)

    # Remove sideways labels
    df = df[df["label"] != 0]

    return df

# ==============================
# TRAIN MODEL
# ==============================

def train():
    df = load_data()

    print("Total samples after filtering:", len(df))
    print("Label distribution:")
    print(df["label"].value_counts())
    print()

    # Feature selection
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    # Time-based split (NO shuffle)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = RandomForestClassifier(
        n_estimators=600,
        max_depth=15,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)
    
    # ==============================
    # PROBABILITY CALIBRATION (PROFESSIONAL)
    # ==============================
    # Random Forest probabilities are not well-calibrated
    # Use isotonic regression to calibrate probabilities
    print("\n⚙️  Calibrating model probabilities (isotonic regression)...")
    calibrated_model = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calibrated_model.fit(X_train, y_train)
    print("✅ Calibration complete")
    
    # Use calibrated model for predictions and save it
    model = calibrated_model

    # Predictions
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)

    print("\n==============================")
    print("ACCURACY:", accuracy_score(y_test, predictions))
    print("==============================\n")

    print("Classification Report:\n")
    print(classification_report(y_test, predictions))

    # ==============================
    # CONFIDENCE ANALYSIS
    # ==============================

    confidence = probabilities.max(axis=1)

    print("\nConfidence Analysis:")
    print("Average confidence:", round(confidence.mean(), 3))
    print("Signals > 0.60:", (confidence > 0.60).sum())
    print("Signals > 0.65:", (confidence > 0.65).sum())
    print("Signals > 0.70:", (confidence > 0.70).sum())

    high_conf_mask = confidence > 0.65
    filtered_preds = predictions[high_conf_mask]
    filtered_true = y_test.values[high_conf_mask]

    print("\nFiltered (>0.65) Accuracy:",
      accuracy_score(filtered_true, filtered_preds))

    # ==============================
    # FEATURE IMPORTANCE
    # ==============================

    importances = pd.Series(
        model.feature_importances_,
        index=FEATURE_COLUMNS
    ).sort_values(ascending=False)

    print("\nTop Feature Importances:\n")
    print(importances)

    # ==============================
    # SAVE MODEL
    # ==============================

    if not os.path.exists(MODEL_FOLDER):
        os.makedirs(MODEL_FOLDER)

    model_path = os.path.join(MODEL_FOLDER, MODEL_NAME)
    joblib.dump(model, model_path)

    print(f"\nModel saved to {model_path}")
    print("✅ Calibrated model ready for professional edge-based trading")


# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    train()