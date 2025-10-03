"""Windowed feature extraction from time-series data."""

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureWindows:
    """Creates rolling windows and computes aggregations."""

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 30,
        lag_periods: List[int] = [1, 2, 3, 5],
    ):
        """
        Initialize feature windows.

        Args:
            short_window: Short rolling window size
            long_window: Long rolling window size
            lag_periods: List of lag periods to compute
        """
        self.short_window = short_window
        self.long_window = long_window
        self.lag_periods = lag_periods

    def add_lags(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Add lagged features.

        Args:
            df: Input dataframe
            columns: Columns to lag

        Returns:
            DataFrame with added lag columns
        """
        result = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            for lag in self.lag_periods:
                lag_col = f"{col}_lag{lag}"
                result[lag_col] = result[col].shift(lag)

        return result

    def add_rolling_stats(
        self,
        df: pd.DataFrame,
        columns: List[str],
    ) -> pd.DataFrame:
        """
        Add rolling mean and std for short and long windows.

        Args:
            df: Input dataframe
            columns: Columns to compute rolling stats

        Returns:
            DataFrame with added rolling stats
        """
        result = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            # Short window
            result[f"{col}_rmean_s"] = (
                result[col].rolling(window=self.short_window, min_periods=1).mean()
            )
            result[f"{col}_rstd_s"] = (
                result[col].rolling(window=self.short_window, min_periods=1).std()
            )

            # Long window
            result[f"{col}_rmean_l"] = (
                result[col].rolling(window=self.long_window, min_periods=1).mean()
            )
            result[f"{col}_rstd_l"] = (
                result[col].rolling(window=self.long_window, min_periods=1).std()
            )

        return result

    def add_ema(
        self,
        df: pd.DataFrame,
        columns: List[str],
        alphas: List[float] = [0.1, 0.3],
    ) -> pd.DataFrame:
        """
        Add exponential moving averages.

        Args:
            df: Input dataframe
            columns: Columns to compute EMA
            alphas: List of alpha values

        Returns:
            DataFrame with added EMA columns
        """
        result = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            for alpha in alphas:
                ema_col = f"{col}_ema{int(alpha*10)}"
                result[ema_col] = result[col].ewm(alpha=alpha, adjust=False).mean()

        return result

    def add_slope(
        self,
        df: pd.DataFrame,
        columns: List[str],
        window: int = 10,
    ) -> pd.DataFrame:
        """
        Add linear slope over recent window.

        Args:
            df: Input dataframe
            columns: Columns to compute slope
            window: Window size for slope calculation

        Returns:
            DataFrame with added slope columns
        """
        result = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            slopes = []
            values = result[col].values

            for i in range(len(values)):
                if i < window - 1:
                    slopes.append(0.0)
                else:
                    window_vals = values[i - window + 1 : i + 1]
                    x = np.arange(window)
                    # Simple linear regression
                    slope = np.polyfit(x, window_vals, 1)[0] if len(window_vals) == window else 0.0
                    slopes.append(slope)

            result[f"{col}_slope"] = slopes

        return result

    def add_burstiness(
        self,
        df: pd.DataFrame,
        io_columns: List[str],
        window: int = 10,
    ) -> pd.DataFrame:
        """
        Add burstiness ratio (ratio of max to mean in window).

        Args:
            df: Input dataframe
            io_columns: I/O columns (disk, network)
            window: Window size

        Returns:
            DataFrame with burstiness features
        """
        result = df.copy()

        for col in io_columns:
            if col not in df.columns:
                continue

            rolling_max = result[col].rolling(window=window, min_periods=1).max()
            rolling_mean = result[col].rolling(window=window, min_periods=1).mean()

            # Avoid division by zero
            burst_ratio = rolling_max / (rolling_mean + 1e-6)
            result[f"{col}_burst"] = burst_ratio

        return result
