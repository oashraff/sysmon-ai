"""Unit tests for Repository."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from sysmon_ai.data import Repository


@pytest.fixture
def temp_db() -> Path:
    """Create temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def repository(temp_db: Path) -> Repository:
    """Create and initialize repository."""
    repo = Repository(str(temp_db))
    repo.connect()
    repo.initialize_schema()
    yield repo
    repo.close()


def test_repository_initialization(repository: Repository) -> None:
    """Test repository initialization."""
    stats = repository.get_stats()

    assert stats["sample_count"] == 0
    assert stats["model_count"] == 0
    assert stats["event_count"] == 0


def test_repository_write_samples(repository: Repository) -> None:
    """Test writing samples."""
    samples = [
        {
            "ts": 1000000,
            "host": "test",
            "cpu_pct": 50.0,
            "mem_pct": 60.0,
            "disk_read_bps": 1000.0,
            "disk_write_bps": 2000.0,
            "net_up_bps": 500.0,
            "net_down_bps": 1500.0,
            "swap_pct": 5.0,
            "proc_count": 200,
            "cpu_temp": None,
        },
        {
            "ts": 1000001,
            "host": "test",
            "cpu_pct": 55.0,
            "mem_pct": 65.0,
            "disk_read_bps": 1100.0,
            "disk_write_bps": 2100.0,
            "net_up_bps": 550.0,
            "net_down_bps": 1550.0,
            "swap_pct": 5.5,
            "proc_count": 205,
            "cpu_temp": None,
        },
    ]

    count = repository.write_samples(samples)

    assert count == 2

    stats = repository.get_stats()
    assert stats["sample_count"] == 2


def test_repository_read_samples(repository: Repository) -> None:
    """Test reading samples."""
    # Write samples
    samples = [
        {
            "ts": 1000000 + i,
            "host": "test",
            "cpu_pct": 50.0 + i,
            "mem_pct": 60.0,
            "disk_read_bps": 1000.0,
            "disk_write_bps": 2000.0,
            "net_up_bps": 500.0,
            "net_down_bps": 1500.0,
            "swap_pct": 5.0,
            "proc_count": 200,
            "cpu_temp": None,
        }
        for i in range(10)
    ]

    repository.write_samples(samples)

    # Read back
    df = repository.read_samples(1000000, 1000005)

    assert len(df) == 6
    assert "cpu_pct" in df.columns
    assert df["cpu_pct"].iloc[0] == 50.0


def test_repository_save_load_model(repository: Repository) -> None:
    """Test model persistence."""
    blob = b"fake_model_data"
    meta = {"n_estimators": 100, "contamination": 0.05}

    repository.save_model(
        name="test_model",
        algo="IsolationForest",
        version="1.0",
        blob=blob,
        meta=meta,
    )

    loaded = repository.load_model("test_model")

    assert loaded is not None
    assert loaded["algo"] == "IsolationForest"
    assert loaded["version"] == "1.0"
    assert loaded["blob"] == blob
    assert loaded["meta"] == meta


def test_repository_write_read_events(repository: Repository) -> None:
    """Test event persistence."""
    event_id = repository.write_event(
        event_type="anomaly",
        score=0.95,
        metric_tags="cpu,mem",
        explanation="High CPU and memory usage",
    )

    assert event_id > 0

    events = repository.read_events(0, 2000000000)

    assert len(events) == 1
    assert events[0]["type"] == "anomaly"
    assert events[0]["score"] == 0.95
