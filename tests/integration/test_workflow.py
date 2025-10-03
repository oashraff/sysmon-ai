"""Integration test for end-to-end workflow."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sysmon_ai.data import Repository
from sysmon_ai.detection import AnomalyDetector
from sysmon_ai.evaluation import SyntheticDataGenerator
from sysmon_ai.features import FeatureTransformer
from sysmon_ai.models import IsolationForestModel


@pytest.mark.integration
def test_end_to_end_workflow() -> None:
    """Test complete workflow from data generation to detection."""

    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        # Initialize repository
        repo = Repository(str(db_path))
        repo.connect()
        repo.initialize_schema()

        # Generate synthetic data
        generator = SyntheticDataGenerator(random_state=42)
        train_df = generator.generate_baseline(n_samples=1000, start_ts=1000000, interval=1)
        test_df = generator.generate_baseline(n_samples=200, start_ts=1001000, interval=1)

        # Inject anomalies
        test_df, labels = generator.inject_anomalies(
            test_df, ["cpu_spike", "memory_leak"], contamination=0.1
        )

        # Write to database
        repo.write_samples(train_df.to_dict("records"))
        repo.write_samples(test_df.to_dict("records"))

        # Create detector
        model = IsolationForestModel(n_estimators=50, random_state=42)
        transformer = FeatureTransformer()
        detector = AnomalyDetector(repo, transformer, model)

        # Train
        train_metrics = detector.train(
            start_ts=1000000,
            end_ts=1000999,
            val_split=0.2,
        )

        assert train_metrics["train_samples"] > 0
        assert train_metrics["threshold"] is not None

        # Detect
        df, scores, is_anomaly = detector.detect(
            start_ts=1001000,
            end_ts=1001199,
        )

        assert len(df) == 200
        assert len(scores) == 200
        assert len(is_anomaly) == 200

        # Verify some anomalies detected
        anomaly_count = int(is_anomaly.sum())
        assert anomaly_count > 0
        assert anomaly_count < len(is_anomaly)

        # Extract events
        events = detector.extract_anomalies(df, scores, is_anomaly)
        assert len(events) == anomaly_count

        # Save events
        for event in events:
            event_id = repo.write_event(
                event_type="anomaly",
                score=event["score"],
                metric_tags=event["metric_tags"],
                explanation=event["explanation"],
            )
            assert event_id > 0

        # Verify events saved
        saved_events = repo.read_events(0, 2000000000)
        assert len(saved_events) == len(events)

        repo.close()

    finally:
        if db_path.exists():
            db_path.unlink()
