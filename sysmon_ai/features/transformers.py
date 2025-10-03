"""Feature transformers for ML model input."""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from sysmon_ai.features.windows import FeatureWindows

logger = logging.getLogger(__name__)


class FeatureTransformer:
    """
    Transforms raw samples into ML-ready features.

    Handles feature engineering, scaling, and missing value imputation.
    """

    def __init__(
        self,
        metric_columns: Optional[List[str]] = None,
        short_window: int = 5,
        long_window: int = 30,
        lag_periods: Optional[List[int]] = None,
    ):
        """
        Initialize feature transformer.

        Args:
            metric_columns: List of metric columns to use. If None, uses defaults.
            short_window: Short rolling window
            long_window: Long rolling window
            lag_periods: Lag periods to compute
        """
        self.metric_columns = metric_columns or [
            "cpu_pct",
            "mem_pct",
            "disk_read_bps",
            "disk_write_bps",
            "net_up_bps",
            "net_down_bps",
            "swap_pct",
        ]

        self.io_columns = [
            "disk_read_bps",
            "disk_write_bps",
            "net_up_bps",
            "net_down_bps",
        ]

        self.windows = FeatureWindows(
            short_window=short_window,
            long_window=long_window,
            lag_periods=lag_periods or [1, 2, 3, 5],
        )

        self.scaler = StandardScaler()
        self._feature_names: Optional[List[str]] = None
        self._is_fitted = False

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Fit transformer and transform data.

        Args:
            df: Input dataframe with raw samples

        Returns:
            Transformed feature matrix
        """
        features_df = self._engineer_features(df)

        # Fit scaler
        X = features_df.values
        X_scaled = self.scaler.fit_transform(X)

        self._feature_names = features_df.columns.tolist()
        self._is_fitted = True

        logger.info(f"Fitted transformer with {X_scaled.shape[1]} features")
        return X_scaled

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """
        Transform data using fitted transformer.

        Args:
            df: Input dataframe with raw samples

        Returns:
            Transformed feature matrix
        """
        if not self._is_fitted:
            raise RuntimeError("Transformer not fitted. Call fit_transform first.")

        features_df = self._engineer_features(df)

        # Ensure same columns as training
        if self._feature_names:
            # Add missing columns with zeros
            for col in self._feature_names:
                if col not in features_df.columns:
                    features_df[col] = 0.0

            # Select and reorder columns
            features_df = features_df[self._feature_names]

        X = features_df.values
        X_scaled = self.scaler.transform(X)

        return X_scaled

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply feature engineering pipeline.

        Args:
            df: Raw samples dataframe

        Returns:
            DataFrame with engineered features
        """
        # Start with raw metrics
        features = df[self.metric_columns].copy()

        # Add lags
        features = self.windows.add_lags(features, self.metric_columns)

        # Add rolling stats
        features = self.windows.add_rolling_stats(features, self.metric_columns)

        # Add EMA
        features = self.windows.add_ema(features, self.metric_columns)

        # Add slopes
        features = self.windows.add_slope(features, self.metric_columns)

        # Add burstiness for I/O metrics
        features = self.windows.add_burstiness(features, self.io_columns)

        # Drop rows with NaN (initial lag periods)
        features = features.fillna(0.0)

        return features

    def get_feature_names(self) -> List[str]:
        """Get list of feature names after transformation."""
        if not self._feature_names:
            return []
        return self._feature_names.copy()

    def get_feature_importance_map(self) -> Dict[str, int]:
        """
        Get mapping of feature names to indices.

        Returns:
            Dict mapping feature name to column index
        """
        if not self._feature_names:
            return {}
        return {name: i for i, name in enumerate(self._feature_names)}
