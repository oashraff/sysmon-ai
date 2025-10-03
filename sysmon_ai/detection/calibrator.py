"""Threshold calibration utilities."""

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)


def find_threshold_for_fpr(
    scores: np.ndarray,
    target_fpr: float,
) -> float:
    """
    Find score threshold that achieves target false positive rate.

    Args:
        scores: Anomaly scores (lower = more anomalous)
        target_fpr: Target false positive rate (0-1)

    Returns:
        Threshold value
    """
    percentile = target_fpr * 100
    threshold = np.percentile(scores, percentile)
    return float(threshold)


def compute_fpr_tpr(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
) -> Tuple[float, float]:
    """
    Compute FPR and TPR at given threshold.

    Args:
        scores: Anomaly scores
        labels: True labels (1=anomaly, 0=normal)
        threshold: Detection threshold

    Returns:
        Tuple of (fpr, tpr)
    """
    predictions = (scores < threshold).astype(int)

    tp = np.sum((predictions == 1) & (labels == 1))
    fp = np.sum((predictions == 1) & (labels == 0))
    tn = np.sum((predictions == 0) & (labels == 0))
    fn = np.sum((predictions == 0) & (labels == 1))

    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return fpr, tpr


def compute_precision_recall(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
) -> Tuple[float, float]:
    """
    Compute precision and recall at threshold.

    Args:
        scores: Anomaly scores
        labels: True labels (1=anomaly, 0=normal)
        threshold: Detection threshold

    Returns:
        Tuple of (precision, recall)
    """
    predictions = (scores < threshold).astype(int)

    tp = np.sum((predictions == 1) & (labels == 1))
    fp = np.sum((predictions == 1) & (labels == 0))
    fn = np.sum((predictions == 0) & (labels == 1))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return precision, recall
