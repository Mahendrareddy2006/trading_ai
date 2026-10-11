"""Model Training Pipeline with Chronological Validation & Probability Calibration.

Features:
- Self-contained, robust Random Forest and Logistic Regression models
- Strict chronological Train / Val / Holdout Test splits
- Feature importance extraction
- Walk-forward rolling evaluation
- Artifact serialization with metadata and feature schemas
"""

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional, Tuple
import joblib

from trading_ai.core.logging import get_logger
from trading_ai.evaluation.metrics import evaluate_classifier
from trading_ai.features.pipeline import FEATURE_COLUMNS, feature_pipeline
from trading_ai.labeling.targets import target_labeler
from trading_ai.training.models import (
    CalibratedModel, LogisticClassifier, RandomForestClassifier, DecisionTreeClassifier
)

logger = get_logger("ModelTrainer")

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_models")
os.makedirs(MODELS_DIR, exist_ok=True)


class ModelTrainer:
    """Manages training, validation, and serialization of trading ML models."""

    def __init__(self, models_dir: str = MODELS_DIR):
        self.models_dir = models_dir

    def prepare_dataset(self, candles: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[int], List[Dict[str, Any]]]:
        """Runs stationary feature extraction and 3-class target labeling."""
        features = feature_pipeline.transform(candles)
        labeled = target_labeler.compute_labels(features)

        X, _ = feature_pipeline.extract_matrix(labeled)
        y = [r["target"] for r in labeled]
        return X, y, labeled

    def split_data_chronological(
        self,
        X: List[List[float]],
        y: List[int],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15
    ):
        """Strictly chronological split without shuffle or future contamination."""
        n = len(X)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        return (
            X[:train_end], y[:train_end],
            X[train_end:val_end], y[train_end:val_end],
            X[val_end:], y[val_end:]
        )

    def instantiate_model(self, model_type: str = "random_forest", hyperparams: Dict = None) -> Any:
        params = hyperparams or {}
        m_type = model_type.lower()
        if m_type in ["logistic_regression", "logistic", "linear"]:
            return LogisticClassifier(
                learning_rate=params.get("learning_rate", 0.05),
                max_iter=params.get("max_iter", 300)
            )
        elif m_type in ["decision_tree", "tree"]:
            return DecisionTreeClassifier(
                max_depth=params.get("max_depth", 6)
            )
        else:
            return RandomForestClassifier(
                n_estimators=params.get("n_estimators", 35),
                max_depth=params.get("max_depth", 6)
            )

    def train_and_evaluate(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        model_type: str = "random_forest",
        hyperparams: Dict = None
    ) -> Dict[str, Any]:
        """Full training sequence:

        1. Features + Target labeling
        2. Chronological split (70% train / 15% val / 15% test)
        3. Fit base model
        4. Extract feature importances
        5. Calibrate on validation set
        6. Evaluate on holdout test set
        7. Save model artifact
        """
        logger.info(f"Training {model_type} for {symbol} ({timeframe})...")
        X, y, labeled = self.prepare_dataset(candles)

        if len(X) < 80:
            raise ValueError(f"Insufficient samples ({len(X)}) for model training.")

        X_train, y_train, X_val, y_val, X_test, y_test = self.split_data_chronological(X, y)

        base_model = self.instantiate_model(model_type, hyperparams)
        base_model.fit(X_train, y_train)

        # Feature importances
        feature_importances = {}
        if hasattr(base_model, "feature_importances_") and base_model.feature_importances_:
            for col, val in zip(FEATURE_COLUMNS, base_model.feature_importances_):
                feature_importances[col] = val
        else:
            # Equal weight default
            feature_importances = {col: round(1.0 / len(FEATURE_COLUMNS), 4) for col in FEATURE_COLUMNS}

        # Calibrate model
        calibrated = CalibratedModel(base_model)
        calibrated.fit(X_val, y_val)

        # Evaluate on Holdout Test
        test_preds = calibrated.predict(X_test)
        test_probas = calibrated.predict_proba(X_test)
        classes = calibrated.classes

        metrics = evaluate_classifier(
            y_true=y_test,
            y_pred=test_preds,
            y_proba=test_probas,
            class_labels=classes
        )

        model_id = f"{symbol}_{timeframe}_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        model_filepath = os.path.join(self.models_dir, f"{model_id}.joblib")

        bundle = {
            "model_id": model_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "model_type": model_type,
            "model": calibrated,
            "classes": classes,
            "feature_columns": FEATURE_COLUMNS,
            "feature_importances": feature_importances,
            "metrics": metrics,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sample_counts": {
                "train": len(X_train),
                "val": len(X_val),
                "test": len(X_test)
            }
        }

        joblib.dump(bundle, model_filepath)
        logger.info(f"Saved model bundle: {model_filepath} (Accuracy: {metrics['accuracy']:.4f})")
        return bundle


model_trainer = ModelTrainer()
