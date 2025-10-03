"""Base model interface and abstractions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np


class BaseModel(ABC):
    """Abstract base class for ML models."""

    def __init__(self, random_state: int = 42):
        """
        Initialize base model.

        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        self._is_fitted = False

    @abstractmethod
    def fit(
        self, X: np.ndarray, y: Optional[np.ndarray] = None
    ) -> "BaseModel":
        """
        Fit model on training data.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Optional target vector

        Returns:
            Self for chaining
        """

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions.

        Args:
            X: Feature matrix (n_samples, n_features)

        Returns:
            Predictions array
        """

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """
        Get model parameters.

        Returns:
            Dict of parameter names and values
        """

    def is_fitted(self) -> bool:
        """Check if model is fitted."""
        return self._is_fitted
