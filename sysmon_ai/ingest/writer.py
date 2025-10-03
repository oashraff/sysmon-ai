"""Batching writer with backpressure handling."""

import logging
import queue
import threading
import time
from typing import Any, Dict, List

from sysmon_ai.data import Repository

logger = logging.getLogger(__name__)


class BatchWriter:
    """
    Batching writer that accumulates samples and writes to repository.

    Handles backpressure by dropping oldest samples when queue is full.
    """

    def __init__(
        self,
        repository: Repository,
        batch_size: int = 100,
        max_queue_size: int = 10000,
        flush_interval: float = 1.0,
    ):
        """
        Initialize batch writer.

        Args:
            repository: Repository instance for writing
            batch_size: Number of samples per batch write
            max_queue_size: Maximum queue size before dropping
            flush_interval: Max seconds between flushes
        """
        self.repository = repository
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size
        self.flush_interval = flush_interval

        self._queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=max_queue_size)
        self._running = False
        self._thread: threading.Thread | None = None
        self._dropped_count = 0
        self._written_count = 0

    def start(self) -> None:
        """Start background writer thread."""
        if self._running:
            logger.warning("Writer already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._thread.start()
        logger.info("Batch writer started")

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop background writer and flush remaining samples.

        Args:
            timeout: Max seconds to wait for flush
        """
        if not self._running:
            return

        self._running = False

        if self._thread:
            self._thread.join(timeout=timeout)

        # Final flush
        self._flush()

        logger.info(
            f"Batch writer stopped (written={self._written_count}, "
            f"dropped={self._dropped_count})"
        )

    def enqueue(self, sample: Dict[str, Any]) -> bool:
        """
        Add sample to write queue.

        Args:
            sample: Sample dict to write

        Returns:
            True if enqueued, False if dropped due to backpressure
        """
        try:
            self._queue.put_nowait(sample)
            return True
        except queue.Full:
            self._dropped_count += 1
            if self._dropped_count % 1000 == 0:
                logger.warning(
                    f"Queue full, dropped {self._dropped_count} samples total"
                )
            return False

    def _writer_loop(self) -> None:
        """Background writer loop."""
        batch: List[Dict[str, Any]] = []
        last_flush = time.time()

        while self._running or not self._queue.empty():
            try:
                # Get sample with timeout to allow periodic flushes
                try:
                    sample = self._queue.get(timeout=0.1)
                    batch.append(sample)
                except queue.Empty:
                    pass

                # Flush if batch full or interval elapsed
                now = time.time()
                should_flush = (
                    len(batch) >= self.batch_size
                    or (batch and now - last_flush >= self.flush_interval)
                )

                if should_flush and batch:
                    self._write_batch(batch)
                    batch.clear()
                    last_flush = now

            except Exception as e:
                logger.error(f"Writer loop error: {e}", exc_info=True)
                time.sleep(0.1)

        # Final flush
        if batch:
            self._write_batch(batch)

    def _write_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Write batch to repository."""
        try:
            start = time.time()
            count = self.repository.write_samples(batch)
            elapsed = time.time() - start

            self._written_count += count

            if elapsed > 0.1:  # Log slow writes
                logger.warning(
                    f"Slow batch write: {count} samples in {elapsed:.3f}s"
                )
            else:
                logger.debug(f"Wrote {count} samples in {elapsed:.3f}s")

        except Exception as e:
            logger.error(f"Failed to write batch: {e}", exc_info=True)

    def _flush(self) -> None:
        """Flush all queued samples."""
        batch = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
                if len(batch) >= self.batch_size:
                    self._write_batch(batch)
                    batch.clear()
            except queue.Empty:
                break

        if batch:
            self._write_batch(batch)

    def get_stats(self) -> Dict[str, int]:
        """Get writer statistics."""
        return {
            "written": self._written_count,
            "dropped": self._dropped_count,
            "queued": self._queue.qsize(),
        }
