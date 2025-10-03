"""Repository pattern for SQLite database access."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from sysmon_ai.utils import now_utc_ts

logger = logging.getLogger(__name__)


class Repository:
    """SQLite repository with WAL mode for concurrent access."""

    def __init__(self, db_path: str):
        """
        Initialize repository with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Establish database connection with optimized PRAGMAs."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )

        # Enable WAL mode and performance optimizations
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        self._conn.execute("PRAGMA temp_store=MEMORY")
        self._conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap

        logger.info(f"Database connected: {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    def initialize_schema(self) -> None:
        """Initialize database schema from SQL file."""
        if not self._conn:
            raise RuntimeError("Database not connected")

        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        self._conn.executescript(schema_sql)
        logger.info("Database schema initialized")

    def write_samples(self, samples: List[Dict[str, Any]]) -> int:
        """
        Batch insert metric samples.

        Args:
            samples: List of sample dicts with keys matching schema

        Returns:
            Number of rows inserted
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        if not samples:
            return 0

        insert_sql = """
            INSERT INTO samples (
                ts, host, cpu_pct, mem_pct, disk_read_bps, disk_write_bps,
                net_up_bps, net_down_bps, swap_pct, proc_count, cpu_temp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        rows = [
            (
                s["ts"],
                s["host"],
                s["cpu_pct"],
                s["mem_pct"],
                s["disk_read_bps"],
                s["disk_write_bps"],
                s["net_up_bps"],
                s["net_down_bps"],
                s["swap_pct"],
                s["proc_count"],
                s.get("cpu_temp"),
            )
            for s in samples
        ]

        cursor = self._conn.executemany(insert_sql, rows)
        count = cursor.rowcount
        logger.debug(f"Inserted {count} samples")
        return count

    def read_samples(
        self,
        start_ts: int,
        end_ts: int,
        host: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Read samples in time range.

        Args:
            start_ts: Start timestamp (inclusive)
            end_ts: End timestamp (inclusive)
            host: Optional host filter

        Returns:
            DataFrame with samples
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        query = """
            SELECT ts, host, cpu_pct, mem_pct, disk_read_bps, disk_write_bps,
                   net_up_bps, net_down_bps, swap_pct, proc_count, cpu_temp
            FROM samples
            WHERE ts BETWEEN ? AND ?
        """
        params: Tuple[Any, ...] = (start_ts, end_ts)

        if host:
            query += " AND host = ?"
            params = (start_ts, end_ts, host)

        query += " ORDER BY ts ASC"

        df = pd.read_sql_query(query, self._conn, params=params)
        logger.debug(f"Read {len(df)} samples from {start_ts} to {end_ts}")
        return df

    def save_model(
        self,
        name: str,
        algo: str,
        version: str,
        blob: bytes,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Save serialized model to database.

        Args:
            name: Model name/identifier
            algo: Algorithm name
            version: Model version
            blob: Serialized model bytes
            meta: Optional metadata dict
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        meta_json = json.dumps(meta) if meta else None

        self._conn.execute(
            """
            INSERT OR REPLACE INTO models (name, algo, version, trained_at, meta_json, blob)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, algo, version, now_utc_ts(), meta_json, blob),
        )
        logger.info(f"Model saved: {name} (algo={algo}, version={version})")

    def load_model(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load serialized model from database.

        Args:
            name: Model name/identifier

        Returns:
            Dict with keys: algo, version, trained_at, meta, blob
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        cursor = self._conn.execute(
            "SELECT algo, version, trained_at, meta_json, blob FROM models WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        algo, version, trained_at, meta_json, blob = row
        meta = json.loads(meta_json) if meta_json else None

        return {
            "algo": algo,
            "version": version,
            "trained_at": trained_at,
            "meta": meta,
            "blob": blob,
        }

    def write_event(
        self,
        event_type: str,
        score: Optional[float] = None,
        metric_tags: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> int:
        """
        Write anomaly/forecast event.

        Args:
            event_type: Event type (anomaly, forecast, etc.)
            score: Anomaly score or confidence
            metric_tags: Comma-separated metric tags
            explanation: Human-readable explanation

        Returns:
            Event ID
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        cursor = self._conn.execute(
            """
            INSERT INTO events (ts, type, score, metric_tags, explanation)
            VALUES (?, ?, ?, ?, ?)
            """,
            (now_utc_ts(), event_type, score, metric_tags, explanation),
        )
        event_id = cursor.lastrowid
        logger.info(f"Event written: {event_type} (id={event_id})")
        return event_id

    def read_events(
        self,
        start_ts: int,
        end_ts: int,
        event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read events in time range.

        Args:
            start_ts: Start timestamp
            end_ts: End timestamp
            event_type: Optional event type filter

        Returns:
            List of event dicts
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        query = """
            SELECT id, ts, type, score, metric_tags, explanation
            FROM events
            WHERE ts BETWEEN ? AND ?
        """
        params: Tuple[Any, ...] = (start_ts, end_ts)

        if event_type:
            query += " AND type = ?"
            params = (start_ts, end_ts, event_type)

        query += " ORDER BY ts DESC"

        cursor = self._conn.execute(query, params)
        events = [
            {
                "id": row[0],
                "ts": row[1],
                "type": row[2],
                "score": row[3],
                "metric_tags": row[4],
                "explanation": row[5],
            }
            for row in cursor.fetchall()
        ]

        return events

    def prune_old_samples(self, retention_days: int) -> int:
        """
        Delete samples older than retention period.

        Args:
            retention_days: Number of days to retain

        Returns:
            Number of rows deleted
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        cutoff_ts = now_utc_ts() - (retention_days * 86400)

        cursor = self._conn.execute("DELETE FROM samples WHERE ts < ?", (cutoff_ts,))
        deleted = cursor.rowcount

        if deleted > 0:
            self._conn.execute("VACUUM")
            logger.info(f"Pruned {deleted} old samples (retention={retention_days}d)")

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dict with row counts and size info
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        cursor = self._conn.execute("SELECT COUNT(*) FROM samples")
        sample_count = cursor.fetchone()[0]

        cursor = self._conn.execute("SELECT COUNT(*) FROM models")
        model_count = cursor.fetchone()[0]

        cursor = self._conn.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]

        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "sample_count": sample_count,
            "model_count": model_count,
            "event_count": event_count,
            "db_size_mb": db_size / (1024 * 1024),
        }
