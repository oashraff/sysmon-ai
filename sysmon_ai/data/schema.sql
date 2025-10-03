-- SQLite schema for system monitoring
-- Version: 1.0

-- Samples table: stores time-series metrics
CREATE TABLE IF NOT EXISTS samples (
    ts INTEGER NOT NULL,
    host TEXT NOT NULL,
    cpu_pct REAL NOT NULL,
    mem_pct REAL NOT NULL,
    disk_read_bps REAL NOT NULL,
    disk_write_bps REAL NOT NULL,
    net_up_bps REAL NOT NULL,
    net_down_bps REAL NOT NULL,
    swap_pct REAL NOT NULL,
    proc_count INTEGER NOT NULL,
    cpu_temp REAL
);

CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts);
CREATE INDEX IF NOT EXISTS idx_samples_host_ts ON samples(host, ts);

-- Models table: stores serialized ML models
CREATE TABLE IF NOT EXISTS models (
    name TEXT PRIMARY KEY,
    algo TEXT NOT NULL,
    version TEXT NOT NULL,
    trained_at INTEGER NOT NULL,
    meta_json TEXT,
    blob BLOB NOT NULL
);

-- Events table: stores anomaly/forecast events
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    type TEXT NOT NULL,
    score REAL,
    metric_tags TEXT,
    explanation TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, strftime('%s', 'now'));
