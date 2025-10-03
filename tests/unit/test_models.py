"""Unit tests for IsolationForestModel."""

import numpy as np
import pytest

from sysmon_ai.models import IsolationForestModel


@pytest.fixture
def sample_data() -> np.ndarray:
    """Create sample feature matrix."""
    np.random.seed(42)
    # Normal data
    X_normal = np.random.randn(1000, 10)

    # Add some anomalies
    X_anomaly = np.random.randn(50, 10) * 5 + 10

    X = np.vstack([X_normal, X_anomaly])
    np.random.shuffle(X)

    return X


def test_isolation_forest_fit(sample_data: np.ndarray) -> None:
    """Test model fitting."""
    model = IsolationForestModel(n_estimators=50, random_state=42)

    model.fit(sample_data)

    assert model.is_fitted()


def test_isolation_forest_predict(sample_data: np.ndarray) -> None:
    """Test predictions."""
    model = IsolationForestModel(n_estimators=50, random_state=42)
    model.fit(sample_data)

    predictions = model.predict(sample_data)

    assert predictions.shape[0] == sample_data.shape[0]
    assert set(predictions).issubset({-1, 1})


def test_isolation_forest_score_samples(sample_data: np.ndarray) -> None:
    """Test anomaly scoring."""
    model = IsolationForestModel(n_estimators=50, random_state=42)
    model.fit(sample_data)

    scores = model.score_samples(sample_data)

    assert scores.shape[0] == sample_data.shape[0]
    assert not np.isnan(scores).any()


def test_isolation_forest_calibrate_threshold(sample_data: np.ndarray) -> None:
    """Test threshold calibration."""
    model = IsolationForestModel(n_estimators=50, random_state=42)
    model.fit(sample_data)

    # Calibrate on validation set (assumed normal)
    X_val = np.random.randn(200, 10)
    threshold = model.calibrate_threshold(X_val, target_fpr=0.05)

    assert isinstance(threshold, float)
    assert model.get_threshold() == threshold


def test_isolation_forest_predict_with_threshold(sample_data: np.ndarray) -> None:
    """Test prediction with custom threshold."""
    model = IsolationForestModel(n_estimators=50, random_state=42)
    model.fit(sample_data)

    X_val = np.random.randn(200, 10)
    model.calibrate_threshold(X_val, target_fpr=0.05)

    predictions = model.predict_with_threshold(sample_data)

    assert predictions.shape[0] == sample_data.shape[0]
    assert predictions.dtype == bool
    assert 0 < predictions.sum() < len(predictions)  # Some anomalies detected
