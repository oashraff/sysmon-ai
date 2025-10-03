"""Evaluation orchestration and reporting."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sysmon_ai.data import Repository
from sysmon_ai.detection import AnomalyDetector
from sysmon_ai.evaluation.metrics import (
    compute_classification_metrics,
    compute_lead_time,
    compute_pr_curve,
    compute_roc_curve,
)
from sysmon_ai.evaluation.simulate import SyntheticDataGenerator

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)


class Evaluator:
    """
    Evaluates anomaly detection performance.

    Generates synthetic data, trains model, and computes metrics.
    """

    def __init__(
        self,
        detector: AnomalyDetector,
        repository: Repository,
        output_dir: Path,
    ):
        """
        Initialize evaluator.

        Args:
            detector: Anomaly detector
            repository: Repository for data
            output_dir: Directory for evaluation outputs
        """
        self.detector = detector
        self.repository = repository
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_evaluation(
        self,
        n_train: int = 100000,
        n_test: int = 20000,
        contamination: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Run full evaluation pipeline.

        Args:
            n_train: Number of training samples
            n_test: Number of test samples
            contamination: Anomaly contamination rate

        Returns:
            Evaluation results dict
        """
        logger.info("Starting evaluation...")

        # Generate synthetic data
        generator = SyntheticDataGenerator()

        start_ts = 1000000000
        train_df = generator.generate_baseline(n_train, start_ts, interval=1)

        test_start_ts = start_ts + n_train
        test_df_clean = generator.generate_baseline(n_test, test_start_ts, interval=1)

        # Inject anomalies into test set
        anomaly_types = ["cpu_spike", "memory_leak", "io_storm", "network_flood"]
        test_df, y_true = generator.inject_anomalies(
            test_df_clean, anomaly_types, contamination
        )

        # Write to repository
        logger.info("Writing training data to repository...")
        self.repository.write_samples(train_df.to_dict("records"))

        logger.info("Writing test data to repository...")
        self.repository.write_samples(test_df.to_dict("records"))

        # Train model
        logger.info("Training model...")
        train_metrics = self.detector.train(
            start_ts=start_ts,
            end_ts=start_ts + n_train - 1,
        )

        # Detect on test set
        logger.info("Running detection on test set...")
        _, y_scores, y_pred = self.detector.detect(
            start_ts=test_start_ts,
            end_ts=test_start_ts + n_test - 1,
        )

        # Compute metrics
        logger.info("Computing evaluation metrics...")
        metrics = compute_classification_metrics(y_true, y_pred, y_scores)

        # Lead time
        timestamps = test_df["ts"].values
        lead_time_metrics = compute_lead_time(y_true, y_pred, timestamps)
        metrics.update(lead_time_metrics)

        # Generate plots
        self._plot_roc_curve(y_true, y_scores)
        self._plot_pr_curve(y_true, y_scores)
        self._plot_score_distribution(y_true, y_scores)

        # Save results
        results = {
            "train_samples": n_train,
            "test_samples": n_test,
            "contamination": contamination,
            "train_metrics": train_metrics,
            "test_metrics": metrics,
        }

        results_path = self.output_dir / "evaluation_results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Evaluation complete. Results saved to {results_path}")
        logger.info(f"Metrics: {metrics}")

        return results

    def _plot_roc_curve(self, y_true: np.ndarray, y_scores: np.ndarray) -> None:
        """Plot ROC curve."""
        fpr, tpr, _ = compute_roc_curve(y_true, y_scores)

        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, linewidth=2, label="ROC curve")
        plt.plot([0, 1], [0, 1], "k--", label="Random")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curve")
        plt.legend()
        plt.grid(True, alpha=0.3)

        output_path = self.output_dir / "roc_curve.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"ROC curve saved to {output_path}")

    def _plot_pr_curve(self, y_true: np.ndarray, y_scores: np.ndarray) -> None:
        """Plot precision-recall curve."""
        precision, recall, _ = compute_pr_curve(y_true, y_scores)

        plt.figure(figsize=(8, 6))
        plt.plot(recall, precision, linewidth=2, label="PR curve")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title("Precision-Recall Curve")
        plt.legend()
        plt.grid(True, alpha=0.3)

        output_path = self.output_dir / "pr_curve.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"PR curve saved to {output_path}")

    def _plot_score_distribution(
        self, y_true: np.ndarray, y_scores: np.ndarray
    ) -> None:
        """Plot anomaly score distributions."""
        normal_scores = y_scores[y_true == 0]
        anomaly_scores = y_scores[y_true == 1]

        plt.figure(figsize=(10, 6))
        plt.hist(
            normal_scores, bins=50, alpha=0.5, label="Normal", color="blue", density=True
        )
        plt.hist(
            anomaly_scores,
            bins=50,
            alpha=0.5,
            label="Anomaly",
            color="red",
            density=True,
        )
        plt.xlabel("Anomaly Score")
        plt.ylabel("Density")
        plt.title("Score Distribution")
        plt.legend()
        plt.grid(True, alpha=0.3)

        output_path = self.output_dir / "score_distribution.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"Score distribution saved to {output_path}")
