"""Evaluation package."""

from .evaluate import Evaluator
from .metrics import (
    compute_classification_metrics,
    compute_lead_time,
    compute_pr_curve,
    compute_roc_curve,
)
from .simulate import SyntheticDataGenerator

__all__ = [
    "SyntheticDataGenerator",
    "Evaluator",
    "compute_classification_metrics",
    "compute_roc_curve",
    "compute_pr_curve",
    "compute_lead_time",
]
