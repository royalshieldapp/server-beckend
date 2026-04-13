"""
XGBoost Risk Predictor
Predicts future risk scores for H3 cells using gradient boosting
"""
import xgboost as xgb
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from pathlib import Path
import pickle
import logging

from .feature_engineering import get_feature_engineer

logger = logging.getLogger(__name__)


class RiskPredictor:
    """
    XGBoost-based risk predictor for H3 cells
    
    Predicts:
    - Risk score (0-100) for each cell
    - Probability of high-risk events
    - Feature importance for explainability
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize risk predictor
        
        Args:
            model_path: Path to saved model (if loading pre-trained)
        """
        self.model = None
        self.feature_engineer = get_feature_engineer()
        self.feature_names = None
        self.model_params = {
            "objective": "reg:squarederror",
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "min_child_weight": 3,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "gamma": 0.1,
            "random_state": 42
        }
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
            logger.info(f"Loaded pre-trained model from {model_path}")
    
    def train(
        self,
        events: List[Dict[str, Any]],
        pois: List[Dict[str, Any]] = None,
        lookback_days: int = 90,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train XGBoost model on historical data
        
        Args:
            events: Historical events for training
            pois: Points of interest
            lookback_days: Days of history to use
            validation_split: Fraction of data for validation
        
        Returns:
            Training metrics and results
        """
        logger.info("Training XGBoost risk predictor...")
        
        # Create training dataset
        df = self.feature_engineer.create_training_dataset(
            events,
            pois,
            lookback_days
        )
        
        # Remove cells with no events (zero risk)
        df = df[df["risk_score"] > 0].copy()
        
        if len(df) < 10:
            logger.warning(f"Not enough data for training ({len(df)} cells)")
            return {
                "status": "error",
                "message": "Insufficient training data"
            }
        
        # Split features and target
        target_col = "risk_score"
        id_col = "h3_cell"
        feature_cols = [col for col in df.columns if col not in [target_col, id_col]]
        
        X = df[feature_cols]
        y = df[target_col]
        
        self.feature_names = feature_cols
        
        # Train/validation split
        split_idx = int(len(df) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Train XGBoost model
        self.model = xgb.XGBRegressor(**self.model_params)
        
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        val_score = self.model.score(X_val, y_val)
        
        # Get feature importance
        feature_importance = self._get_feature_importance()
        
        logger.info(f"Training complete: R²_train={train_score:.3f}, R²_val={val_score:.3f}")
        
        return {
            "status": "success",
            "r2_train": train_score,
            "r2_val": val_score,
            "n_samples_train": len(X_train),
            "n_samples_val": len(X_val),
            "n_features": len(feature_cols),
            "feature_importance": feature_importance[:10]  # Top 10
        }
    
    def predict(
        self,
        h3_cells: List[str],
        current_events: List[Dict[str, Any]],
        current_pois: List[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Predict risk scores for H3 cells
        
        Args:
            h3_cells: List of H3 cell IDs to predict for
            current_events: Recent events
            current_pois: Current POIs
        
        Returns:
            Dictionary mapping H3 cell ID -> predicted risk score
        """
        if self.model is None:
            logger.error("Model not trained. Call train() first.")
            return {}
        
        predictions = {}
        
        for h3_cell in h3_cells:
            # Extract features for this cell
            features = self.feature_engineer.prepare_prediction_features(
                h3_cell,
                current_events,
                current_pois
            )
            
            # Ensure features match training feature order
            feature_vector = [features.get(fname, 0.0) for fname in self.feature_names]
            
            # Predict
            X = np.array(feature_vector).reshape(1, -1)
            risk_score = float(self.model.predict(X)[0])
            
            # Clip to valid range
            risk_score = max(0.0, min(100.0, risk_score))
            
            predictions[h3_cell] = risk_score
        
        logger.info(f"Generated predictions for {len(predictions)} cells")
        return predictions
    
    def predict_batch(
        self,
        events: List[Dict[str, Any]],
        pois: List[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Predict risk for all cells with events (batch mode)
        
        Args:
            events: Current events
            pois: Current POIs
        
        Returns:
            Dictionary mapping H3 cell ID -> predicted risk score
        """
        if self.model is None:
            logger.error("Model not trained. Call train() first.")
            return {}
        
        # Create feature dataset
        df = self.feature_engineer.create_training_dataset(
            events,
            pois,
            lookback_days=30
        )
        
        # Extract features
        X = df[self.feature_names]
        h3_cells = df["h3_cell"].tolist()
        
        # Predict
        predictions_array = self.model.predict(X)
        
        # Clip and convert to dict
        predictions = {}
        for h3_cell, risk_score in zip(h3_cells, predictions_array):
            predictions[h3_cell] = float(max(0.0, min(100.0, risk_score)))
        
        logger.info(f"Batch predicted {len(predictions)} cells")
        return predictions
    
    def _get_feature_importance(self) -> List[Dict[str, Any]]:
        """Get feature importance from trained model"""
        if self.model is None:
            return []
        
        importance_scores = self.model.feature_importances_
        
        importance_list = [
            {
                "feature": fname,
                "importance": float(score)
            }
            for fname, score in zip(self.feature_names, importance_scores)
        ]
        
        # Sort by importance
        importance_list.sort(key=lambda x: x["importance"], reverse=True)
        
        return importance_list
    
    def save_model(self, path: str):
        """Save trained model to disk"""
        if self.model is None:
            logger.error("No model to save")
            return
        
        model_data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "model_params": self.model_params
        }
        
        with open(path, "wb") as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load trained model from disk"""
        with open(path, "rb") as f:
            model_data = pickle.load(f)
        
        self.model = model_data["model"]
        self.feature_names = model_data["feature_names"]
        self.model_params = model_data.get("model_params", {})
        
        logger.info(f"Model loaded from {path}")
    
    def get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to categorical level"""
        if risk_score >= 75:
            return "CRITICAL"
        elif risk_score >= 50:
            return "HIGH"
        elif risk_score >= 25:
            return "MEDIUM"
        else:
            return "LOW"


# Singleton
_risk_predictor = None

def get_risk_predictor(model_path: str = None) -> RiskPredictor:
    """Get singleton risk predictor instance"""
    global _risk_predictor
    if _risk_predictor is None:
        _risk_predictor = RiskPredictor(model_path)
    return _risk_predictor
