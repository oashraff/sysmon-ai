# Troubleshooting Guide

## Common Issues & Solutions

### Installation Issues

#### ImportError: No module named 'sysmon_ai'

**Problem**: Package not installed or virtual environment not activated.

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall package
pip install -e ".[dev]"
```

#### ModuleNotFoundError: No module named 'psutil'

**Problem**: Dependencies not installed.

**Solution**:
```bash
pip install -e ".[dev]"
```

---

### Runtime Issues

#### "Database not connected" error

**Problem**: Database connection not established.

**Solution**:
```bash
# Initialize database first
sysmon init

# Or check DB path in config
cat config.yaml | grep db_path
```

#### "No training data available"

**Problem**: Not enough samples collected for training.

**Solution**:
```bash
# Check sample count
sysmon export --window 1h --to /dev/null

# Collect more data
sysmon start --duration 1h

# Train with smaller window
sysmon train --window 1h
```

#### "Model not trained" when running detect

**Problem**: Anomaly model not trained yet.

**Solution**:
```bash
# Train model first
sysmon train --window 7d

# Or with less data
sysmon train --window 1h
```

#### High CPU usage (> 3%)

**Problem**: Sampling too fast or model too complex.

**Solution**:
Edit `config.yaml`:
```yaml
sampling:
  rate_seconds: 5.0  # Reduce sampling frequency

anomaly:
  n_estimators: 50   # Reduce model complexity
  max_samples: 128
```

#### High memory usage (> 150MB)

**Problem**: History too large or feature matrix too big.

**Solution**:
```yaml
dashboard:
  default_view_hours: 1  # Reduce history

features:
  short_window: 3
  long_window: 15
```

#### "Permission denied" on macOS

**Problem**: macOS security settings blocking psutil.

**Solution**:
```bash
# Grant terminal full disk access in:
# System Preferences > Security & Privacy > Privacy > Full Disk Access
```

---

### Dashboard Issues

#### Dashboard not updating

**Problem**: No data being collected or refresh rate too slow.

**Solution**:
```bash
# Start collector in separate terminal
sysmon start

# Check refresh rate
cat config.yaml | grep refresh_rate

# Adjust in config:
dashboard:
  refresh_rate: 1.0
```

#### Unicode characters not displaying

**Problem**: Terminal doesn't support Unicode.

**Solution**:
```yaml
# Enable ASCII fallback
dashboard:
  ascii_fallback: true
```

#### Colors not showing

**Problem**: Terminal doesn't support colors or TERM not set.

**Solution**:
```bash
# Check TERM
echo $TERM

# Set if needed
export TERM=xterm-256color
```

#### Dashboard freezes

**Problem**: Too much data or slow database queries.

**Solution**:
```bash
# Prune old data
sqlite3 sysmon.db "DELETE FROM samples WHERE ts < $(date -v-7d +%s);"
sqlite3 sysmon.db "VACUUM;"

# Reduce history
dashboard:
  default_view_hours: 1
```

---

### Detection Issues

#### High false positive rate (> 5%)

**Problem**: Threshold not calibrated or contamination too high.

**Solution**:
```yaml
anomaly:
  contamination: 0.01  # Lower contamination
  target_fpr: 0.03     # Stricter FPR target
```

Then retrain:
```bash
sysmon train --window 7d
```

#### Low detection rate (missing anomalies)

**Problem**: Threshold too strict or baseline includes anomalies.

**Solution**:
```yaml
anomaly:
  contamination: 0.10   # Higher contamination
  target_fpr: 0.08      # Looser FPR
  baseline_window_days: 14  # Longer baseline
```

#### "Contamination" parameter unclear

**Explanation**: Contamination is the **expected proportion of anomalies** in the training data. Default 0.05 means we expect ~5% anomalies in baseline.

- Set lower (0.01) if baseline is very clean
- Set higher (0.10) if baseline has known anomalies

---

### Performance Issues

#### Write latency > 10ms

**Problem**: Disk I/O bottleneck or batch size too large.

**Solution**:
```yaml
sampling:
  batch_size: 50       # Smaller batches
  rate_seconds: 2.0    # Reduce sampling rate

storage:
  wal_checkpoint_interval: 500  # More frequent checkpoints
```

#### Dropped samples during collection

**Problem**: Queue overflow due to backpressure.

**Solution**:
```yaml
sampling:
  max_queue_size: 20000  # Larger queue
  batch_size: 200        # Bigger batches for faster writes
```

---

### Evaluation Issues

#### Evaluation takes too long

**Problem**: Too many samples or complex model.

**Solution**:
```bash
# Use fewer samples for quick tests
sysmon evaluate --train-samples 10000 --test-samples 2000

# Reduce model complexity
anomaly:
  n_estimators: 50
  max_samples: 128
```

#### "Not enough data for validation split"

**Problem**: Training set too small.

**Solution**:
```bash
# Generate more samples
sysmon evaluate --train-samples 5000
```

#### Accuracy below 94%

**Problem**: Model underfitting or data too noisy.

**Solution**:
```yaml
anomaly:
  n_estimators: 200    # More trees
  max_samples: 512     # Larger sample size per tree
```

---

### Platform-Specific Issues

#### macOS: "cpu_temp" always None

**Expected behavior**: CPU temperature not available on macOS via psutil.

**Solution**: This is normal. Temperature monitoring primarily works on Linux.

#### Windows: Path issues with backslashes

**Problem**: Windows path separators causing issues.

**Solution**:
```bash
# Use forward slashes in config
storage:
  db_path: "C:/Users/YourName/sysmon.db"
```

#### Linux: Permission errors reading /proc

**Problem**: Insufficient permissions for some metrics.

**Solution**:
```bash
# Run with sudo (not recommended for production)
sudo sysmon start

# Or adjust permissions (safer)
sudo setcap cap_sys_ptrace=ep $(which python3)
```

---

### Database Issues

#### "database is locked"

**Problem**: Concurrent access conflict (WAL should prevent this).

**Solution**:
```bash
# Check if WAL is enabled
sqlite3 sysmon.db "PRAGMA journal_mode;"
# Should return: wal

# If not, reinit
sysmon init
```

#### Database file growing too large

**Problem**: Retention not pruning or too long.

**Solution**:
```yaml
storage:
  retention_days: 7  # Shorter retention
```

Manual cleanup:
```bash
sqlite3 sysmon.db "DELETE FROM samples WHERE ts < $(date -v-7d +%s);"
sqlite3 sysmon.db "VACUUM;"
```

#### Corrupted database

**Problem**: Unexpected shutdown or disk error.

**Solution**:
```bash
# Check integrity
sqlite3 sysmon.db "PRAGMA integrity_check;"

# If corrupted, backup and reinit
mv sysmon.db sysmon.db.bak
sysmon init
```

---

### Configuration Issues

#### Environment variables not overriding config

**Problem**: Incorrect env variable names.

**Solution**:
```bash
# Correct format: SYSMON_<SECTION>_<KEY>
export SYSMON_SAMPLING_RATE=2.0
export SYSMON_DB_PATH=/custom/path.db
export SYSMON_LOG_LEVEL=DEBUG
```

#### Config file not found

**Problem**: Wrong path or file doesn't exist.

**Solution**:
```bash
# Check current directory
ls -la config.yaml

# Create from example
cp config.example.yaml config.yaml

# Or specify path
sysmon start --config /path/to/config.yaml
```

---

### Testing Issues

#### pytest: "No module named 'pytest'"

**Problem**: Dev dependencies not installed.

**Solution**:
```bash
pip install -e ".[dev]"
```

#### Tests failing with import errors

**Problem**: Package not installed in editable mode.

**Solution**:
```bash
pip install -e .
pytest tests/
```

#### Coverage report not generated

**Problem**: pytest-cov not installed.

**Solution**:
```bash
pip install pytest-cov
pytest --cov=sysmon_ai --cov-report=html
```

---

### Logging Issues

#### No log file created

**Problem**: Log directory doesn't exist.

**Solution**:
```bash
# Create logs directory
mkdir -p logs

# Or specify full path in config
logging:
  file_path: /tmp/sysmon.log
```

#### Log file too large

**Problem**: Rotation not working or backup count too high.

**Solution**:
```yaml
logging:
  max_bytes: 5242880   # 5MB
  backup_count: 3       # Keep 3 backups
```

---

## Debugging Tips

### Enable debug logging

```bash
sysmon start --log-level DEBUG
```

Or in config:
```yaml
logging:
  level: DEBUG
```

### Check database contents

```bash
# Sample count
sqlite3 sysmon.db "SELECT COUNT(*) FROM samples;"

# Recent samples
sqlite3 sysmon.db "SELECT * FROM samples ORDER BY ts DESC LIMIT 10;"

# Events
sqlite3 sysmon.db "SELECT * FROM events ORDER BY ts DESC;"
```

### Monitor resource usage

```bash
# While running sysmon
ps aux | grep sysmon
top -p $(pgrep -f sysmon)
```

### Profile performance

```bash
python -m cProfile -o profile.stats -m sysmon_ai.cli start --duration 1m
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumtime').print_stats(20)"
```

### Check for memory leaks

```bash
pip install memory_profiler
python -m memory_profiler sysmon_ai/cli.py start --duration 1m
```

---

## Getting Help

If issues persist:

1. **Check logs**: `tail -f logs/sysmon.log`
2. **Verify installation**: `python verify_installation.py`
3. **Review docs**: README.md, QUICKSTART.md, ARCHITECTURE.md
4. **Run tests**: `pytest tests/ -v`
5. **Check GitHub Issues**: (if available)

---

## Known Limitations

1. **CPU temperature**: Only available on Linux
2. **Process details**: Limited on some platforms
3. **Network interfaces**: Aggregated across all interfaces
4. **Disk I/O**: System-wide, not per-process
5. **Memory accuracy**: Varies by platform

---

*For additional support, review the documentation or open an issue on GitHub.*
