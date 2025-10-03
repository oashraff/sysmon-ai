"""Isolation Forest anomaly detection model."""

import logging
from typing import Any, Dict, Optional

import numpy as np
from sklearn.ensemble import IsolationForest as SklearnIF

from sysmon_ai.models.base import BaseModel

logger = logging.getLogger(__name__)


class IsolationForestModel(BaseModel):
    """
    Isolation Forest for anomaly detection.

    Uses sklearn's IsolationForest with auto-tuning capabilities.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_samples: int = 256,
        contamination: float = 0.05,
        random_state: int = 42,
    ):
        """
        Initialize Isolation Forest model.

        Args:
            n_estimators: Number of trees
            max_samples: Number of samples per tree
            contamination: Expected proportion of anomalies
            random_state: Random seed
        """
        super().__init__(random_state=random_state)
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination

        self._model = SklearnIF(
            n_estimators=n_estimators,
            max_samples=max_samples,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )

        self._threshold: Optional[float] = None

    def fit(
        self, X: np.ndarray, y: Optional[np.ndarray] = None
    ) -> "IsolationForestModel":
        """
        Fit Isolation Forest on training data.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Ignored (unsupervised)

        Returns:
            Self for chaining
        """
        logger.info(f"Training Isolation Forest on {X.shape[0]} samples...")
        self._model.fit(X)
        self._is_fitted = True
        logger.info("Isolation Forest training complete")
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomaly labels (-1 for anomaly, 1 for normal).

        Args:
            X: Feature matrix

        Returns:
            Array of predictions
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted")

        return self._model.predict(X)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Compute anomaly scores for samples.

        Args:
            X: Feature matrix

        Returns:
            Array of anomaly scores (more negative = more anomalous)
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted")

        return self._model.score_samples(X)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """
        Compute decision function (same as score_samples).

        Args:
            X: Feature matrix

        Returns:
            Array of decision scores
        """
        return self.score_samples(X)

    def calibrate_threshold(
        self,
        X_val: np.ndarray,
        target_fpr: float = 0.05,
    ) -> float:
        """
        Calibrate detection threshold on validation set to achieve target FPR.

        Args:
            X_val: Validation feature matrix (assumed normal)
            target_fpr: Target false positive rate

        Returns:
            Calibrated threshold
        """
        scores = self.score_samples(X_val)

        # Find threshold at target percentile
        percentile = target_fpr * 100
        threshold = np.percentile(scores, percentile)

        self._threshold = threshold
        logger.info(
            f"Calibrated threshold: {threshold:.4f} (target FPR={target_fpr})"
        )

        return threshold

    def predict_with_threshold(self, X: np.ndarray) -> np.ndarray:
        """
        Predict using calibrated threshold.

        Args:
            X: Feature matrix

        Returns:
            Boolean array (True = anomaly)
        """
        if self._threshold is None:
            raise RuntimeError("Threshold not calibrated")

        scores = self.score_samples(X)
        return scores < self._threshold

    def get_threshold(self) -> Optional[float]:
        """Get current threshold."""
        return self._threshold

    def set_threshold(self, threshold: float) -> None:
        """Set detection threshold."""
        self._threshold = threshold

    def get_params(self) -> Dict[str, Any]:
        """Get model parameters."""
        return {
            "n_estimators": self.n_estimators,
            "max_samples": self.max_samples,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "threshold": self._threshold,
        }
