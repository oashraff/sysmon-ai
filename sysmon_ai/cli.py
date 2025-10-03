"""Command-line interface using Typer."""

import sys
import threading
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from sysmon_ai import __version__
from sysmon_ai.config import Config
from sysmon_ai.data import Repository
from sysmon_ai.detection import AnomalyDetector
from sysmon_ai.evaluation import Evaluator
from sysmon_ai.features import FeatureTransformer
from sysmon_ai.ingest import BatchWriter, MetricsSampler
from sysmon_ai.logging_setup import setup_logging
from sysmon_ai.models import IsolationForestModel
from sysmon_ai.ui import Dashboard
from sysmon_ai.utils import get_time_range, parse_duration

app = typer.Typer(
    name="sysmon",
    help="Terminal-based system monitor with local AI anomaly detection",
    add_completion=False,
)

console = Console()


@app.command()
def init(
    db_path: str = typer.Option("sysmon.db", "--db", help="Database path"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Config file path"
    ),
) -> None:
    """Initialize database and configuration."""
    console.print(
        f"[bold cyan]Initializing sysmon v{__version__}...[/bold cyan]"
    )

    # Load or create config
    config = Config.load(config_path) if config_path else Config()

    # Override DB path if specified
    if db_path:
        config.storage.db_path = db_path

    # Setup logging
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file_path,
    )

    # Initialize repository
    repo = Repository(config.storage.db_path)
    repo.connect()
    repo.initialize_schema()

    stats = repo.get_stats()
    console.print(f"✓ Database initialized at: {config.storage.db_path}")
    console.print(f"  Samples: {stats['sample_count']:,}")
    console.print(f"  Size: {stats['db_size_mb']:.2f} MB")

    # Save config
    if not config_path:
        config_path = Path("config.yaml")

    config.save(config_path)
    console.print(f"✓ Configuration saved to: {config_path}")

    repo.close()
    console.print("[bold green]✓ Initialization complete[/bold green]")


@app.command()
def start(
    db_path: str = typer.Option("sysmon.db", "--db", help="Database path"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Config file"
    ),
    duration: Optional[str] = typer.Option(
        None, "--duration", help="Run duration (e.g., '1h', '7d')"
    ),
) -> None:
    """Start metrics collection."""
    config = Config.load(config_path) if config_path else Config()
    if db_path:
        config.storage.db_path = db_path

    logger = setup_logging(
        level=config.logging.level, log_file=config.logging.file_path
    )

    console.print("[bold cyan]Starting metrics collector...[/bold cyan]")
    console.print(f"  Host: {config.host}")
    console.print(f"  Sampling rate: {config.sampling.rate_seconds}s")
    console.print(f"  Database: {config.storage.db_path}")

    # Initialize components
    repo = Repository(config.storage.db_path)
    repo.connect()

    sampler = MetricsSampler(config.host)
    writer = BatchWriter(
        repo,
        batch_size=config.sampling.batch_size,
        max_queue_size=config.sampling.max_queue_size,
    )

    writer.start()

    # Collection loop
    try:
        start_time = time.time()
        end_time = (
            start_time + parse_duration(duration) if duration else float("inf")
        )
        sample_count = 0

        while time.time() < end_time:
            sample = sampler.sample()
            writer.enqueue(sample)
            sample_count += 1

            if sample_count % 100 == 0:
                stats = writer.get_stats()
                logger.info(
                    f"Collected {sample_count} samples "
                    f"(written={stats['written']}, queued={stats['queued']}, "
                    f"dropped={stats['dropped']})"
                )

            time.sleep(config.sampling.rate_seconds)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping collector...[/yellow]")
    finally:
        writer.stop()
        repo.close()

        stats = writer.get_stats()
        console.print("[bold green]✓ Collection stopped[/bold green]")
        console.print(f"  Total written: {stats['written']:,}")
        console.print(f"  Dropped: {stats['dropped']:,}")


@app.command()
def train(
    db_path: str = typer.Option("sysmon.db", "--db", help="Database path"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Config file"
    ),
    window: str = typer.Option(
        "7d", "--window", help="Training window duration"
    ),
    host: Optional[str] = typer.Option(None, "--host", help="Filter by host"),
) -> None:
    """Train anomaly detection model."""
    config = Config.load(config_path) if config_path else Config()
    if db_path:
        config.storage.db_path = db_path

    logger = setup_logging(level=config.logging.level)

    console.print("[bold cyan]Training anomaly detection model...[/bold cyan]")
    console.print(f"  Window: {window}")
    console.print(f"  Database: {config.storage.db_path}")

    # Initialize components
    repo = Repository(config.storage.db_path)
    repo.connect()

    model = IsolationForestModel(
        n_estimators=config.anomaly.n_estimators,
        max_samples=config.anomaly.max_samples,
        contamination=config.anomaly.contamination,
        random_state=config.anomaly.random_state,
    )

    transformer = FeatureTransformer()

    detector = AnomalyDetector(repo, transformer, model)

    # Determine training range
    start_ts, end_ts = get_time_range(window)

    try:
        metrics = detector.train(start_ts, end_ts, host)

        console.print("[bold green]✓ Training complete[/bold green]")
        console.print(f"  Training samples: {metrics['train_samples']:,}")
        console.print(f"  Validation samples: {metrics['val_samples']:,}")
        console.print(f"  Features: {metrics['features']}")
        console.print(f"  Threshold: {metrics['threshold']:.4f}")

    except Exception as e:
        console.print(f"[bold red]✗ Training failed: {e}[/bold red]")
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        repo.close()


@app.command()
def detect(
    db_path: str = typer.Option("sysmon.db", "--db", help="Database path"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Config file"
    ),
    window: str = typer.Option("1h", "--window", help="Detection window"),
    host: Optional[str] = typer.Option(None, "--host", help="Filter by host"),
    save_events: bool = typer.Option(
        True, "--save-events/--no-save-events", help="Save events to DB"
    ),
) -> None:
    """Run anomaly detection on historical data."""
    config = Config.load(config_path) if config_path else Config()
    if db_path:
        config.storage.db_path = db_path

    logger = setup_logging(level=config.logging.level)

    console.print("[bold cyan]Running anomaly detection...[/bold cyan]")

    # Initialize
    repo = Repository(config.storage.db_path)
    repo.connect()

    model = IsolationForestModel(random_state=config.anomaly.random_state)
    transformer = FeatureTransformer()
    detector = AnomalyDetector(repo, transformer, model)

    # Load model
    if not detector.load_model():
        console.print(
            "[bold red]✗ No trained model found. "
            "Run 'sysmon train' first.[/bold red]"
        )
        repo.close()
        sys.exit(1)

    # Detect
    start_ts, end_ts = get_time_range(window)

    try:
        df, scores, is_anomaly = detector.detect(start_ts, end_ts, host)

        anomaly_count = int(is_anomaly.sum())
        console.print("[bold green]✓ Detection complete[/bold green]")
        console.print(f"  Samples: {len(df):,}")
        anomaly_pct = 100 * anomaly_count / len(df)
        console.print(f"  Anomalies: {anomaly_count:,} ({anomaly_pct:.2f}%)")

        # Extract and save events
        if save_events and anomaly_count > 0:
            events = detector.extract_anomalies(df, scores, is_anomaly)
            for event in events:
                repo.write_event(
                    event_type="anomaly",
                    score=event["score"],
                    metric_tags=event["metric_tags"],
                    explanation=event["explanation"],
                )

            console.print(f"  Saved {len(events)} events to database")

    except Exception as e:
        console.print(f"[bold red]✗ Detection failed: {e}[/bold red]")
        logger.error(f"Detection failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        repo.close()


@app.command()
def dashboard(
    db_path: str = typer.Option("sysmon.db", "--db", help="Database path"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Config file"
    ),
) -> None:
    """Launch live dashboard."""
    config = Config.load(config_path) if config_path else Config()
    if db_path:
        config.storage.db_path = db_path

    setup_logging(level=config.logging.level)

    console.print("[bold cyan]Launching dashboard...[/bold cyan]")
    console.print("  Press Ctrl+C to stop")

    # Initialize components
    repo = Repository(config.storage.db_path)
    repo.connect()

    sampler = MetricsSampler(config.host)
    dashboard_ui = Dashboard(refresh_rate=config.dashboard.refresh_rate)

    # Load detector if available
    model = IsolationForestModel(random_state=config.anomaly.random_state)
    transformer = FeatureTransformer()
    detector = AnomalyDetector(repo, transformer, model)
    detector.load_model()  # Ignore if not found

    stop_event = threading.Event()

    def data_callback() -> tuple:
        sample = sampler.sample()
        db_stats = repo.get_stats()

        # TODO: Implement live detection and alerts
        anomalies = {}
        alerts = []
        forecasts = {}

        return sample, anomalies, alerts, forecasts, db_stats

    try:
        dashboard_ui.run_live(data_callback, stop_event)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        repo.close()
        console.print("\n[bold green]✓ Dashboard stopped[/bold green]")


@app.command()
def evaluate(
    db_path: str = typer.Option(
        "sysmon_eval.db", "--db", help="Evaluation database"
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Config file"
    ),
    output_dir: Path = typer.Option(
        "evaluation", "--output", help="Output directory"
    ),
    train_samples: int = typer.Option(
        100000, "--train-samples", help="Training samples"
    ),
    test_samples: int = typer.Option(
        20000, "--test-samples", help="Test samples"
    ),
) -> None:
    """Run evaluation with synthetic data."""
    config = Config.load(config_path) if config_path else Config()
    if db_path:
        config.storage.db_path = db_path

    logger = setup_logging(level=config.logging.level)

    console.print("[bold cyan]Running evaluation...[/bold cyan]")
    console.print(f"  Training samples: {train_samples:,}")
    console.print(f"  Test samples: {test_samples:,}")
    console.print(f"  Output: {output_dir}")

    # Initialize
    repo = Repository(config.storage.db_path)
    repo.connect()
    repo.initialize_schema()

    model = IsolationForestModel(
        n_estimators=config.anomaly.n_estimators,
        max_samples=config.anomaly.max_samples,
        contamination=config.anomaly.contamination,
        random_state=config.anomaly.random_state,
    )

    transformer = FeatureTransformer()
    detector = AnomalyDetector(repo, transformer, model)

    evaluator = Evaluator(detector, repo, output_dir)

    try:
        results = evaluator.run_evaluation(
            n_train=train_samples,
            n_test=test_samples,
            contamination=0.05,
        )

        console.print("[bold green]✓ Evaluation complete[/bold green]")
        console.print(f"  Accuracy: {results['test_metrics']['accuracy']:.2%}")
        console.print(
            f"  Precision: {results['test_metrics']['precision']:.2%}"
        )
        console.print(f"  Recall: {results['test_metrics']['recall']:.2%}")
        console.print(f"  FPR: {results['test_metrics']['fpr']:.2%}")
        console.print(f"  AUC: {results['test_metrics']['auc']:.3f}")

    except Exception as e:
        console.print(f"[bold red]✗ Evaluation failed: {e}[/bold red]")
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        repo.close()


@app.command()
def export(
    db_path: str = typer.Option("sysmon.db", "--db", help="Database path"),
    window: str = typer.Option("24h", "--window", help="Export window"),
    output: Path = typer.Option("export.csv", "--to", help="Output file"),
    format: str = typer.Option(
        "csv", "--format", help="Output format (csv, json)"
    ),
) -> None:
    """Export samples to file."""
    console.print("[bold cyan]Exporting data...[/bold cyan]")

    repo = Repository(db_path)
    repo.connect()

    start_ts, end_ts = get_time_range(window)
    df = repo.read_samples(start_ts, end_ts)

    if format == "csv":
        df.to_csv(output, index=False)
    elif format == "json":
        df.to_json(output, orient="records", indent=2)
    else:
        console.print(f"[bold red]✗ Unknown format: {format}[/bold red]")
        repo.close()
        sys.exit(1)

    repo.close()

    console.print(
        f"[bold green]✓ Exported {len(df):,} samples to {output}[/bold green]"
    )


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"sysmon v{__version__}")


if __name__ == "__main__":
    app()
