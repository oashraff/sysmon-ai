"""Unit tests for FeatureTransformer."""

import numpy as np
import pandas as pd
import pytest

from sysmon_ai.features import FeatureTransformer


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create sample dataframe for testing."""
    np.random.seed(42)
    n = 100

    return pd.DataFrame({
        "ts": np.arange(1000000, 1000000 + n),
        "host": ["test"] * n,
        "cpu_pct": np.random.uniform(20, 80, n),
        "mem_pct": np.random.uniform(30, 70, n),
        "disk_read_bps": np.random.uniform(0, 10**7, n),
        "disk_write_bps": np.random.uniform(0, 10**7, n),
        "net_up_bps": np.random.uniform(0, 10**6, n),
        "net_down_bps": np.random.uniform(0, 10**6, n),
        "swap_pct": np.random.uniform(0, 10, n),
    })


def test_feature_transformer_fit_transform(sample_df: pd.DataFrame) -> None:
    """Test fit_transform produces correct shape."""
    transformer = FeatureTransformer()

    X = transformer.fit_transform(sample_df)

    assert X.shape[0] == len(sample_df)
    assert X.shape[1] > 0  # Should have many features
    assert not np.isnan(X).any()
    assert transformer._is_fitted


def test_feature_transformer_transform(sample_df: pd.DataFrame) -> None:
    """Test transform after fitting."""
    transformer = FeatureTransformer()

    # Fit on first half
    train_df = sample_df.iloc[:50]
    X_train = transformer.fit_transform(train_df)

    # Transform second half
    test_df = sample_df.iloc[50:]
    X_test = transformer.transform(test_df)

    assert X_test.shape[1] == X_train.shape[1]
    assert not np.isnan(X_test).any()


def test_feature_transformer_get_feature_names(sample_df: pd.DataFrame) -> None:
    """Test feature name retrieval."""
    transformer = FeatureTransformer()
    transformer.fit_transform(sample_df)

    feature_names = transformer.get_feature_names()

    assert len(feature_names) > 0
    assert "cpu_pct" in feature_names  # Raw metric
    assert any("lag" in name for name in feature_names)  # Lag features
    assert any("rmean" in name for name in feature_names)  # Rolling stats
    assert any("ema" in name for name in feature_names)  # EMA features
    assert any("slope" in name for name in feature_names)  # Slope features
