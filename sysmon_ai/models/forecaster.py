"""Time-to-threshold forecasting models."""

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression

from sysmon_ai.models.base import BaseModel

logger = logging.getLogger(__name__)


class TimeToThresholdForecaster(BaseModel):
    """
    Forecasts time until metric reaches threshold.

    Supports linear regression and gradient boosting.
    """

    def __init__(
        self,
        algo: str = "linear",
        random_state: int = 42,
        confidence_level: float = 0.95,
    ):
        """
        Initialize forecaster.

        Args:
            algo: Algorithm to use ('linear' or 'gbr')
            random_state: Random seed
            confidence_level: Confidence level for intervals
        """
        super().__init__(random_state=random_state)
        self.algo = algo
        self.confidence_level = confidence_level

        if algo == "linear":
            self._model = LinearRegression()
        elif algo == "gbr":
            self._model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=3,
                random_state=random_state,
            )
        else:
            raise ValueError(f"Unknown algo: {algo}")

        self._std: Optional[float] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> "TimeToThresholdForecaster":
        """
        Fit forecasting model.

        Args:
            X: Feature matrix
            y: Target vector (time to threshold in minutes)

        Returns:
            Self for chaining
        """
        logger.info(
            f"Training {self.algo} forecaster on {X.shape[0]} samples..."
        )
        self._model.fit(X, y)

        # Compute residual std for confidence intervals
        predictions = self._model.predict(X)
        residuals = y - predictions
        self._std = np.std(residuals)

        self._is_fitted = True
        logger.info(f"Forecaster training complete (std={self._std:.2f})")
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict time to threshold.

        Args:
            X: Feature matrix

        Returns:
            Array of predicted minutes
        """
        if not self._is_fitted:
            raise RuntimeError("Model not fitted")

        return self._model.predict(X)

    def predict_with_confidence(
        self,
        X: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Predict with confidence intervals.

        Args:
            X: Feature matrix

        Returns:
            Tuple of (predictions, lower_bounds, upper_bounds)
        """
        predictions = self.predict(X)

        if self._std is None:
            # No confidence intervals available
            return predictions, predictions, predictions

        # Simple prediction interval using residual std
        z_score = 1.96 if self.confidence_level >= 0.95 else 1.645
        margin = z_score * self._std

        lower = np.maximum(0, predictions - margin)
        upper = predictions + margin

        return predictions, lower, upper

    def get_params(self) -> Dict[str, Any]:
        """Get model parameters."""
        params = {
            "algo": self.algo,
            "random_state": self.random_state,
            "confidence_level": self.confidence_level,
            "residual_std": self._std,
        }

        if hasattr(self._model, "get_params"):
            params["model_params"] = self._model.get_params()

        return params


class MultiMetricForecaster:
    """
    Manages separate forecasters for multiple metrics.

    Each metric gets its own model with threshold-specific training.
    """

    def __init__(
        self,
        metrics: list[str],
        thresholds: Dict[str, float],
        algo: str = "linear",
        random_state: int = 42,
    ):
        """
        Initialize multi-metric forecaster.

        Args:
            metrics: List of metric names
            thresholds: Dict mapping metric to threshold value
            algo: Algorithm for each forecaster
            random_state: Random seed
        """
        self.metrics = metrics
        self.thresholds = thresholds
        self.algo = algo
        self.random_state = random_state

        self._forecasters: Dict[str, TimeToThresholdForecaster] = {
            metric: TimeToThresholdForecaster(
                algo=algo,
                random_state=random_state,
            )
            for metric in metrics
        }

    def fit_metric(
        self,
        metric: str,
        X: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """
        Fit forecaster for specific metric.

        Args:
            metric: Metric name
            X: Feature matrix
            y: Time-to-threshold target
        """
        if metric not in self._forecasters:
            raise ValueError(f"Unknown metric: {metric}")

        self._forecasters[metric].fit(X, y)

    def predict_metric(
        self,
        metric: str,
        X: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Predict time-to-threshold for metric.

        Args:
            metric: Metric name
            X: Feature matrix

        Returns:
            Tuple of (predictions, lower, upper)
        """
        if metric not in self._forecasters:
            raise ValueError(f"Unknown metric: {metric}")

        return self._forecasters[metric].predict_with_confidence(X)

    def is_fitted(self, metric: str) -> bool:
        """Check if metric forecaster is fitted."""
        return self._forecasters[metric].is_fitted()
