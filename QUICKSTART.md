# Quickstart Guide

## Installation

1. **Clone and install:**
   ```bash
   cd /Users/omarashraf/Desktop/symson_ai
   pip install -e ".[dev]"
   ```

2. **Set up pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Getting Started

### 1. Initialize the system

```bash
sysmon init
```

This creates:
- `sysmon.db` - SQLite database
- `config.yaml` - Configuration file

### 2. Start collecting metrics

In one terminal, start the collector:

```bash
sysmon start --duration 1h
```

This will collect system metrics for 1 hour. For continuous collection, omit `--duration`.

### 3. Train the anomaly detection model

After collecting baseline data (recommended: 7 days), train the model:

```bash
sysmon train --window 7d
```

For quick testing with less data:

```bash
sysmon train --window 1h
```

### 4. Launch the dashboard

```bash
sysmon dashboard
```

You'll see:
- Live CPU, Memory, Disk I/O, and Network metrics
- Trend sparklines
- Recent alerts
- System statistics

Press `q` to quit, `f` to toggle forecasts, `r` to reload config.

## Quick Evaluation

To test the system with synthetic data:

```bash
sysmon evaluate --train-samples 10000 --test-samples 2000 --output evaluation/
```

This will:
1. Generate synthetic baseline data with realistic patterns
2. Inject anomalies (CPU spikes, memory leaks, I/O storms, network floods)
3. Train the model
4. Run detection
5. Generate evaluation metrics and plots

Results saved to `evaluation/`:
- `evaluation_results.json` - Metrics (accuracy, precision, recall, FPR, AUC)
- `roc_curve.png` - ROC curve
- `pr_curve.png` - Precision-Recall curve
- `score_distribution.png` - Score distributions

## Common Workflows

### Continuous monitoring with alerts

1. Start collector in background:
   ```bash
   nohup sysmon start > /dev/null 2>&1 &
   ```

2. Train model daily:
   ```bash
   sysmon train --window 7d
   ```

3. Run detection and save events:
   ```bash
   sysmon detect --window 1h --save-events
   ```

### Export data for analysis

```bash
# Export last 24 hours to CSV
sysmon export --window 24h --to data.csv --format csv

# Export to JSON
sysmon export --window 24h --to data.json --format json
```

### Custom configuration

1. Copy example config:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` to customize:
   - Sampling rate
   - Thresholds
   - Model parameters
   - Dashboard settings

3. Use custom config:
   ```bash
   sysmon start --config config.yaml
   ```

## Performance Tips

1. **For low-overhead monitoring:**
   - Set `sampling.rate_seconds: 5.0` (5-second intervals)
   - Reduce `anomaly.n_estimators: 50`

2. **For high-frequency monitoring:**
   - Keep `sampling.rate_seconds: 1.0`
   - Increase `sampling.batch_size: 200` for better write performance

3. **For disk space:**
   - Set `storage.retention_days: 7` for shorter retention
   - Run pruning: The repository automatically prunes old data

## Troubleshooting

### "No training data available"

Ensure metrics are being collected:
```bash
# Check database stats
sqlite3 sysmon.db "SELECT COUNT(*) FROM samples;"
```

If zero, run `sysmon start` first.

### "Model not trained"

Run training before detection:
```bash
sysmon train --window 1h
```

### Dashboard not updating

Check that metrics are being collected:
```bash
# In another terminal
sysmon start
```

### High CPU usage

Reduce sampling rate or model complexity in `config.yaml`:
```yaml
sampling:
  rate_seconds: 5.0

anomaly:
  n_estimators: 50
  max_samples: 128
```

## Next Steps

- Explore the [README.md](README.md) for architecture details
- Check [config.example.yaml](config.example.yaml) for all configuration options
- Review evaluation results to understand detection performance
- Integrate alerts into your monitoring workflow

## Development

Run tests:
```bash
make test
```

Format code:
```bash
make format
```

Lint:
```bash
make lint
```

See `Makefile` for all available commands.
