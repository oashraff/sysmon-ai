"""System metrics sampler using psutil."""

import logging
import time
from typing import Any, Dict, Optional

import psutil

from sysmon_ai.utils import now_utc_ts, supports_cpu_temp

logger = logging.getLogger(__name__)


class MetricsSampler:
    """Samples system metrics via psutil."""

    def __init__(self, host: str):
        """
        Initialize sampler.

        Args:
            host: Host identifier for samples
        """
        self.host = host
        self._last_disk_io: Optional[Any] = None
        self._last_net_io: Optional[Any] = None
        self._last_sample_time: Optional[float] = None

    def sample(self) -> Dict[str, Any]:
        """
        Sample current system metrics.

        Returns:
            Dict with metric values and timestamp
        """
        current_time = time.time()
        sample_data = {
            "ts": now_utc_ts(),
            "host": self.host,
            "cpu_pct": self._get_cpu_pct(),
            "mem_pct": self._get_mem_pct(),
            "swap_pct": self._get_swap_pct(),
            "proc_count": self._get_proc_count(),
        }

        # Calculate rates for disk and network
        time_delta = (
            current_time - self._last_sample_time
            if self._last_sample_time
            else 1.0
        )

        disk_io = self._get_disk_io_rates(time_delta)
        sample_data.update(disk_io)

        net_io = self._get_net_io_rates(time_delta)
        sample_data.update(net_io)

        # CPU temperature (optional)
        if supports_cpu_temp():
            sample_data["cpu_temp"] = self._get_cpu_temp()
        else:
            sample_data["cpu_temp"] = None

        self._last_sample_time = current_time

        return sample_data

    def _get_cpu_pct(self) -> float:
        """Get CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Failed to get CPU%: {e}")
            return 0.0

    def _get_mem_pct(self) -> float:
        """Get memory usage percentage."""
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            logger.warning(f"Failed to get memory%: {e}")
            return 0.0

    def _get_swap_pct(self) -> float:
        """Get swap usage percentage."""
        try:
            swap = psutil.swap_memory()
            return swap.percent
        except Exception as e:
            logger.warning(f"Failed to get swap%: {e}")
            return 0.0

    def _get_proc_count(self) -> int:
        """Get number of running processes."""
        try:
            return len(psutil.pids())
        except Exception as e:
            logger.warning(f"Failed to get process count: {e}")
            return 0

    def _get_disk_io_rates(self, time_delta: float) -> Dict[str, float]:
        """
        Calculate disk I/O rates in bytes/sec.

        Args:
            time_delta: Time since last sample

        Returns:
            Dict with disk_read_bps and disk_write_bps
        """
        try:
            current_io = psutil.disk_io_counters()

            if self._last_disk_io and time_delta > 0:
                read_bps = (
                    current_io.read_bytes - self._last_disk_io.read_bytes
                ) / time_delta
                write_bps = (
                    current_io.write_bytes - self._last_disk_io.write_bytes
                ) / time_delta
            else:
                read_bps = write_bps = 0.0

            self._last_disk_io = current_io

            return {
                "disk_read_bps": max(0.0, read_bps),
                "disk_write_bps": max(0.0, write_bps),
            }
        except Exception as e:
            logger.warning(f"Failed to get disk I/O: {e}")
            return {"disk_read_bps": 0.0, "disk_write_bps": 0.0}

    def _get_net_io_rates(self, time_delta: float) -> Dict[str, float]:
        """
        Calculate network I/O rates in bytes/sec.

        Args:
            time_delta: Time since last sample

        Returns:
            Dict with net_up_bps and net_down_bps
        """
        try:
            current_io = psutil.net_io_counters()

            if self._last_net_io and time_delta > 0:
                up_bps = (
                    current_io.bytes_sent - self._last_net_io.bytes_sent
                ) / time_delta
                down_bps = (
                    current_io.bytes_recv - self._last_net_io.bytes_recv
                ) / time_delta
            else:
                up_bps = down_bps = 0.0

            self._last_net_io = current_io

            return {
                "net_up_bps": max(0.0, up_bps),
                "net_down_bps": max(0.0, down_bps),
            }
        except Exception as e:
            logger.warning(f"Failed to get network I/O: {e}")
            return {"net_up_bps": 0.0, "net_down_bps": 0.0}

    def _get_cpu_temp(self) -> Optional[float]:
        """Get CPU temperature (Linux only)."""
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Try common sensor names
                    for key in [
                        "coretemp",
                        "k10temp",
                        "zenpower",
                        "cpu_thermal",
                    ]:
                        if key in temps and temps[key]:
                            return temps[key][0].current
            return None
        except Exception as e:
            logger.debug(f"Failed to get CPU temp: {e}")
            return None
