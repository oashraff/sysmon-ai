"""Anomaly detector orchestration."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from sysmon_ai.data import Repository
from sysmon_ai.features import FeatureTransformer
from sysmon_ai.models import IsolationForestModel, deserialize_model, serialize_model

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    End-to-end anomaly detection pipeline.

    Coordinates feature transformation, model training/inference, and event extraction.
    """

    def __init__(
        self,
        repository: Repository,
        feature_transformer: FeatureTransformer,
        model: IsolationForestModel,
    ):
        """
        Initialize detector.

        Args:
            repository: Repository for data access
            feature_transformer: Feature transformer
            model: Anomaly detection model
        """
        self.repository = repository
        self.feature_transformer = feature_transformer
        self.model = model

    def train(
        self,
        start_ts: int,
        end_ts: int,
        host: Optional[str] = None,
        val_split: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Train anomaly detection model on baseline data.

        Args:
            start_ts: Training window start
            end_ts: Training window end
            host: Optional host filter
            val_split: Validation split ratio for calibration

        Returns:
            Training metrics dict
        """
        logger.info(f"Training anomaly detector from {start_ts} to {end_ts}...")

        # Load training data
        df = self.repository.read_samples(start_ts, end_ts, host)

        if df.empty:
            raise ValueError("No training data available")

        logger.info(f"Loaded {len(df)} samples for training")

        # Split train/val
        split_idx = int(len(df) * (1 - val_split))
        train_df = df.iloc[:split_idx]
        val_df = df.iloc[split_idx:]

        # Fit transformer and transform
        X_train = self.feature_transformer.fit_transform(train_df)
        X_val = self.feature_transformer.transform(val_df)

        # Train model
        self.model.fit(X_train)

        # Calibrate threshold on validation set
        threshold = self.model.calibrate_threshold(
            X_val,
            target_fpr=0.05,
        )

        # Save model
        self._save_model()

        return {
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "threshold": threshold,
            "features": len(self.feature_transformer.get_feature_names()),
        }

    def detect(
        self,
        start_ts: int,
        end_ts: int,
        host: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        """
        Run anomaly detection on time range.

        Args:
            start_ts: Detection window start
            end_ts: Detection window end
            host: Optional host filter

        Returns:
            Tuple of (samples_df, scores, is_anomaly)
        """
        if not self.model.is_fitted():
            raise RuntimeError("Model not trained")

        # Load data
        df = self.repository.read_samples(start_ts, end_ts, host)

        if df.empty:
            return df, np.array([]), np.array([])

        # Transform
        X = self.feature_transformer.transform(df)

        # Score
        scores = self.model.score_samples(X)
        is_anomaly = self.model.predict_with_threshold(X)

        return df, scores, is_anomaly

    def detect_live(
        self,
        df: pd.DataFrame,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run detection on live data.

        Args:
            df: Live samples dataframe

        Returns:
            Tuple of (scores, is_anomaly)
        """
        if not self.model.is_fitted():
            raise RuntimeError("Model not trained")

        X = self.feature_transformer.transform(df)
        scores = self.model.score_samples(X)
        is_anomaly = self.model.predict_with_threshold(X)

        return scores, is_anomaly

    def extract_anomalies(
        self,
        df: pd.DataFrame,
        scores: np.ndarray,
        is_anomaly: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """
        Extract anomaly events with context.

        Args:
            df: Samples dataframe
            scores: Anomaly scores
            is_anomaly: Boolean anomaly flags

        Returns:
            List of anomaly event dicts
        """
        anomalies = []

        for idx in np.where(is_anomaly)[0]:
            sample = df.iloc[idx]
            score = scores[idx]

            # Find most anomalous metrics
            metric_values = {
                "cpu_pct": sample["cpu_pct"],
                "mem_pct": sample["mem_pct"],
                "disk_read_bps": sample["disk_read_bps"],
                "disk_write_bps": sample["disk_write_bps"],
                "net_up_bps": sample["net_up_bps"],
                "net_down_bps": sample["net_down_bps"],
            }

            # Simple heuristic: flag high percentage metrics
            flagged_metrics = [
                k for k, v in metric_values.items()
                if "pct" in k and v > 80
            ]

            if not flagged_metrics:
                # Flag I/O metrics if very high
                flagged_metrics = [
                    k for k, v in metric_values.items()
                    if "bps" in k and v > 10**7  # > 10MB/s
                ]

            anomalies.append({
                "ts": int(sample["ts"]),
                "score": float(score),
                "metric_tags": ",".join(flagged_metrics) if flagged_metrics else "general",
                "explanation": self._explain_anomaly(sample, score),
            })

        return anomalies

    def _explain_anomaly(self, sample: pd.Series, score: float) -> str:
        """Generate human-readable explanation."""
        parts = []

        if sample["cpu_pct"] > 80:
            parts.append(f"high CPU ({sample['cpu_pct']:.1f}%)")
        if sample["mem_pct"] > 80:
            parts.append(f"high memory ({sample['mem_pct']:.1f}%)")
        if sample["disk_write_bps"] > 10**7:
            parts.append(f"high disk write ({sample['disk_write_bps']/1e6:.1f} MB/s)")
        if sample["net_down_bps"] > 10**7:
            parts.append(f"high network download ({sample['net_down_bps']/1e6:.1f} MB/s)")

        if parts:
            return f"Anomaly score {score:.3f}: " + ", ".join(parts)
        else:
            return f"Anomaly score {score:.3f}: unusual pattern detected"

    def _save_model(self) -> None:
        """Save model and transformer to repository."""
        # Serialize model
        model_blob = serialize_model(self.model)

        # Save to repository
        self.repository.save_model(
            name="isolation_forest",
            algo="IsolationForest",
            version="1.0",
            blob=model_blob,
            meta=self.model.get_params(),
        )

        # Save transformer
        transformer_blob = serialize_model(self.feature_transformer)
        self.repository.save_model(
            name="feature_transformer",
            algo="FeatureTransformer",
            version="1.0",
            blob=transformer_blob,
        )

        logger.info("Model and transformer saved")

    def load_model(self) -> bool:
        """
        Load model and transformer from repository.

        Returns:
            True if loaded successfully
        """
        # Load model
        model_data = self.repository.load_model("isolation_forest")
        if not model_data:
            return False

        self.model = deserialize_model(model_data["blob"])
        logger.info("Loaded isolation forest model")

        # Load transformer
        transformer_data = self.repository.load_model("feature_transformer")
        if not transformer_data:
            return False

        self.feature_transformer = deserialize_model(transformer_data["blob"])
        logger.info("Loaded feature transformer")

        return True
