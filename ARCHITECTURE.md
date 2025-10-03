# Project Structure

```
sysmon_ai/
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions CI/CD
├── sysmon_ai/
│   ├── __init__.py
│   ├── cli.py                     # Typer-based CLI
│   ├── config.py                  # Configuration management
│   ├── logging_setup.py           # Logging configuration
│   ├── alerts/
│   │   ├── __init__.py
│   │   ├── rules.py               # Alert rules engine
│   │   └── notify.py              # Local notifications
│   ├── data/
│   │   ├── __init__.py
│   │   ├── schema.sql             # SQLite schema
│   │   └── repository.py          # Repository pattern for DB access
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── detector.py            # Anomaly detector orchestration
│   │   ├── calibrator.py          # Threshold calibration
│   │   └── events.py              # Event data structures
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── simulate.py            # Synthetic data generation
│   │   ├── metrics.py             # Evaluation metrics
│   │   └── evaluate.py            # Evaluation orchestration
│   ├── features/
│   │   ├── __init__.py
│   │   ├── windows.py             # Windowed features
│   │   └── transformers.py        # Feature transformation
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── sampler.py             # Metrics sampler (psutil)
│   │   └── writer.py              # Batching writer
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # Base model interface
│   │   ├── isolation_forest.py   # IsolationForest model
│   │   ├── forecaster.py          # Time-to-threshold forecaster
│   │   └── persistence.py         # Model serialization
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── dashboard.py           # Rich terminal dashboard
│   │   └── panels.py              # Dashboard panels
│   └── utils/
│       ├── __init__.py
│       ├── timeutils.py           # Time utilities
│       ├── sparkline.py           # ASCII visualization
│       └── platform.py            # Platform detection
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest configuration
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_features.py
│   │   ├── test_models.py
│   │   └── test_repository.py
│   └── integration/
│       ├── __init__.py
│       └── test_workflow.py
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE
├── Makefile
├── README.md
├── QUICKSTART.md
├── config.example.yaml
├── pyproject.toml
├── setup.sh
└── verify_installation.py
```

## Key Design Patterns

### 1. **Repository Pattern** (`data/repository.py`)
- Abstracts SQLite access
- Handles transactions, connection pooling
- Provides clean interface for data operations

### 2. **Strategy Pattern** (`models/base.py`)
- Common `BaseModel` interface
- Easy to swap ML algorithms
- Supports different forecasters

### 3. **Observer Pattern** (`alerts/`)
- Rule engine evaluates conditions
- Notifier subscribes to events
- Decoupled alert logic

### 4. **Facade Pattern** (`cli.py`)
- Simple CLI interface
- Hides complex orchestration
- Coordinates multiple components

### 5. **Factory Pattern** (`features/transformers.py`)
- Feature engineering pipeline
- Configurable window sizes
- Reusable transformations

## Data Flow

```
┌──────────┐
│  psutil  │
└────┬─────┘
     │
     v
┌──────────────┐
│   Sampler    │ (1s cadence)
└──────┬───────┘
       │
       v
┌──────────────┐
│ BatchWriter  │ (backpressure)
└──────┬───────┘
       │
       v
┌──────────────┐
│  SQLite WAL  │ (concurrent reads/writes)
└──────┬───────┘
       │
       v
┌──────────────┐
│  Repository  │
└──────┬───────┘
       │
       ├─────────────────────┐
       v                     v
┌──────────────┐    ┌───────────────┐
│   Features   │    │   Dashboard   │
└──────┬───────┘    └───────────────┘
       │
       ├──────────────┬─────────────┐
       v              v             v
┌─────────────┐ ┌──────────┐ ┌──────────┐
│ IsolForest  │ │Forecaster│ │  Events  │
└─────┬───────┘ └────┬─────┘ └────┬─────┘
      │              │            │
      └──────────────┴────────────┘
                     │
                     v
            ┌────────────────┐
            │   Alerting     │
            └────────────────┘
```

## Module Responsibilities

### Core Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `cli.py` | ~450 | CLI commands and orchestration |
| `config.py` | ~200 | Configuration with env overrides |
| `repository.py` | ~300 | SQLite data access layer |

### Feature Engineering

| Module | Lines | Purpose |
|--------|-------|---------|
| `windows.py` | ~150 | Rolling windows, lags, slopes |
| `transformers.py` | ~200 | ML feature transformation |

### Machine Learning

| Module | Lines | Purpose |
|--------|-------|---------|
| `base.py` | ~50 | Model interface |
| `isolation_forest.py` | ~150 | Anomaly detection |
| `forecaster.py` | ~200 | Time-to-threshold prediction |
| `detector.py` | ~250 | End-to-end detection pipeline |

### UI & Alerts

| Module | Lines | Purpose |
|--------|-------|---------|
| `dashboard.py` | ~300 | Live terminal dashboard |
| `panels.py` | ~200 | Dashboard components |
| `rules.py` | ~200 | Alert rule engine |

### Evaluation

| Module | Lines | Purpose |
|--------|-------|---------|
| `simulate.py` | ~150 | Synthetic data generation |
| `metrics.py` | ~150 | Evaluation metrics |
| `evaluate.py` | ~200 | Evaluation orchestration |

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Sample collection | O(1) | psutil calls |
| Batch write | O(n) | n = batch size |
| Feature transform | O(m·w) | m = metrics, w = window |
| IsolationForest fit | O(n·t·log(s)) | t = trees, s = samples |
| IsolationForest score | O(t·log(s)) | per sample |
| Dashboard render | O(h) | h = history size |

### Space Complexity

| Component | Memory | Notes |
|-----------|--------|-------|
| Sample queue | ~1MB | 10k samples |
| Feature matrix | ~10MB | 1k samples × 100 features |
| IsolationForest | ~50MB | 100 trees × 256 samples |
| Dashboard history | ~1MB | 100 recent samples |
| SQLite cache | 64MB | Configured PRAGMA |

## Testing Strategy

### Unit Tests (~80% coverage target)
- Individual components in isolation
- Mock external dependencies
- Fast execution (< 1s per test)

### Integration Tests
- End-to-end workflows
- Real database operations
- Slower but comprehensive

### Performance Tests
- Benchmarks for critical paths
- Memory profiling
- Regression detection

### Test Organization

```
tests/
├── unit/
│   ├── test_features.py      # Feature engineering
│   ├── test_models.py         # ML models
│   ├── test_repository.py     # Data access
│   ├── test_sampler.py        # Metrics collection
│   └── test_utils.py          # Utilities
├── integration/
│   ├── test_workflow.py       # E2E workflows
│   ├── test_cli.py            # CLI commands
│   └── test_dashboard.py      # UI integration
└── conftest.py                # Fixtures
```

## Configuration Precedence

1. **Command-line flags** (highest priority)
2. **Environment variables** (`SYSMON_*`)
3. **Config file** (`config.yaml`)
4. **Defaults** (lowest priority)

Example:
```bash
export SYSMON_DB_PATH=/custom/path.db  # Overrides config.yaml
sysmon start --db /another/path.db     # Overrides env var
```

## Error Handling

### Graceful Degradation
- CPU temp unavailable on macOS → skip gracefully
- Queue full → drop oldest samples, log warning
- Model not trained → inform user, exit cleanly
- Dashboard render error → continue with next frame

### Logging Levels
- **DEBUG**: Detailed diagnostics
- **INFO**: Normal operations (default)
- **WARNING**: Non-critical issues
- **ERROR**: Failures requiring attention

## Security & Privacy

- All data stored locally
- No network calls at runtime
- Optional anonymized host ID
- No telemetry or tracking
- Open source, auditable
