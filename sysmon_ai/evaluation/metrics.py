"""Evaluation metrics computation."""

import logging
from typing import Dict, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

logger = logging.getLogger(__name__)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_scores: np.ndarray,
) -> Dict[str, float]:
    """
    Compute classification metrics.

    Args:
        y_true: True labels (1=anomaly, 0=normal)
        y_pred: Predicted labels
        y_scores: Anomaly scores (lower = more anomalous)

    Returns:
        Dict with accuracy, precision, recall, fpr, auc
    """
    # Convert scores to higher-is-more-anomalous
    y_scores_inverted = -y_scores

    # Basic metrics
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)

    # FPR
    tn = np.sum((y_pred == 0) & (y_true == 0))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # AUC
    try:
        auc = roc_auc_score(y_true, y_scores_inverted)
    except Exception as e:
        logger.warning(f"Could not compute AUC: {e}")
        auc = 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "fpr": fpr,
        "auc": auc,
    }


def compute_roc_curve(
    y_true: np.ndarray,
    y_scores: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute ROC curve.

    Args:
        y_true: True labels
        y_scores: Anomaly scores (lower = more anomalous)

    Returns:
        Tuple of (fpr, tpr, thresholds)
    """
    # Invert scores
    y_scores_inverted = -y_scores
    return roc_curve(y_true, y_scores_inverted)


def compute_pr_curve(
    y_true: np.ndarray,
    y_scores: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute precision-recall curve.

    Args:
        y_true: True labels
        y_scores: Anomaly scores (lower = more anomalous)

    Returns:
        Tuple of (precision, recall, thresholds)
    """
    y_scores_inverted = -y_scores
    return precision_recall_curve(y_true, y_scores_inverted)


def compute_lead_time(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    timestamps: np.ndarray,
) -> Dict[str, float]:
    """
    Compute detection lead time metrics.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        timestamps: Timestamps for each sample

    Returns:
        Dict with mean/median lead time in seconds
    """
    lead_times = []

    # Find true anomaly runs
    anomaly_starts = np.where(np.diff(y_true, prepend=0) == 1)[0]

    for start_idx in anomaly_starts:
        # Find first detection in window after start
        detection_window = y_pred[start_idx : start_idx + 100]
        detected_indices = np.where(detection_window == 1)[0]

        if len(detected_indices) > 0:
            first_detection = start_idx + detected_indices[0]
            lead_time = timestamps[first_detection] - timestamps[start_idx]
            lead_times.append(lead_time)

    if not lead_times:
        return {"mean_lead_time": 0.0, "median_lead_time": 0.0}

    return {
        "mean_lead_time": float(np.mean(lead_times)),
        "median_lead_time": float(np.median(lead_times)),
    }
