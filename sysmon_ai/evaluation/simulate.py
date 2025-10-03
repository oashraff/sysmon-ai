"""Synthetic data generation and anomaly injection."""

import logging
import random
from typing import List, Tuple

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class SyntheticDataGenerator:
    """
    Generates synthetic system metrics with realistic patterns.

    Includes normal baseline and injected anomalies for evaluation.
    """

    def __init__(self, host: str = "synthetic", random_state: int = 42):
        """
        Initialize generator.

        Args:
            host: Host identifier
            random_state: Random seed
        """
        self.host = host
        self.random_state = random_state
        random.seed(random_state)
        np.random.seed(random_state)

    def generate_baseline(
        self,
        n_samples: int,
        start_ts: int,
        interval: int = 1,
    ) -> pd.DataFrame:
        """
        Generate normal baseline data.

        Args:
            n_samples: Number of samples to generate
            start_ts: Starting timestamp
            interval: Seconds between samples

        Returns:
            DataFrame with synthetic samples
        """
        logger.info(f"Generating {n_samples:,} baseline samples...")

        timestamps = [start_ts + i * interval for i in range(n_samples)]

        # Generate realistic patterns with daily/hourly cycles
        t = np.arange(n_samples)

        # CPU: baseline 20-40% with daily cycle
        cpu_base = 30 + 10 * np.sin(t * 2 * np.pi / (86400 / interval))
        cpu_noise = np.random.normal(0, 5, n_samples)
        cpu_pct = np.clip(cpu_base + cpu_noise, 0, 100)

        # Memory: slowly growing trend
        mem_base = 40 + (t / n_samples) * 20
        mem_noise = np.random.normal(0, 3, n_samples)
        mem_pct = np.clip(mem_base + mem_noise, 0, 100)

        # Disk I/O: sporadic bursts
        disk_read = np.abs(np.random.lognormal(10, 2, n_samples))
        disk_write = np.abs(np.random.lognormal(10, 2, n_samples))

        # Network: daytime pattern
        net_up_base = 10**6 * (
            1 + 0.5 * np.sin(t * 2 * np.pi / (86400 / interval))
        )
        net_up = np.abs(
            np.random.lognormal(np.log(net_up_base), 0.5, n_samples)
        )

        net_down_base = (
            5 * 10**6 * (1 + 0.5 * np.sin(t * 2 * np.pi / (86400 / interval)))
        )
        net_down = np.abs(
            np.random.lognormal(np.log(net_down_base), 0.5, n_samples)
        )

        # Swap: low and stable
        swap_pct = np.clip(np.random.normal(5, 2, n_samples), 0, 100)

        # Process count: stable
        proc_count = np.random.poisson(200, n_samples)

        df = pd.DataFrame(
            {
                "ts": timestamps,
                "host": self.host,
                "cpu_pct": cpu_pct,
                "mem_pct": mem_pct,
                "disk_read_bps": disk_read,
                "disk_write_bps": disk_write,
                "net_up_bps": net_up,
                "net_down_bps": net_down,
                "swap_pct": swap_pct,
                "proc_count": proc_count,
                "cpu_temp": None,
            }
        )

        logger.info(f"Generated baseline: {len(df)} samples")
        return df

    def inject_anomalies(
        self,
        df: pd.DataFrame,
        anomaly_types: List[str],
        contamination: float = 0.05,
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Inject anomalies into baseline data.

        Args:
            df: Baseline dataframe
            anomaly_types: List of anomaly types to inject
            contamination: Fraction of anomalous samples

        Returns:
            Tuple of (modified_df, labels) where labels[i]=1 means anomaly
        """
        logger.info(f"Injecting anomalies (contamination={contamination})...")

        df = df.copy()
        n_samples = len(df)
        n_anomalies = int(n_samples * contamination)

        labels = np.zeros(n_samples, dtype=int)

        # Select random indices for anomalies
        anomaly_indices = np.random.choice(
            n_samples, size=n_anomalies, replace=False
        )

        for idx in anomaly_indices:
            anomaly_type = random.choice(anomaly_types)

            if anomaly_type == "cpu_spike":
                df.at[idx, "cpu_pct"] = np.random.uniform(90, 100)
            elif anomaly_type == "memory_leak":
                df.at[idx, "mem_pct"] = np.random.uniform(85, 100)
            elif anomaly_type == "io_storm":
                df.at[idx, "disk_read_bps"] = np.random.uniform(10**8, 10**9)
                df.at[idx, "disk_write_bps"] = np.random.uniform(10**8, 10**9)
            elif anomaly_type == "network_flood":
                df.at[idx, "net_up_bps"] = np.random.uniform(10**8, 10**9)
                df.at[idx, "net_down_bps"] = np.random.uniform(10**8, 10**9)
            elif anomaly_type == "swap_pressure":
                df.at[idx, "swap_pct"] = np.random.uniform(80, 100)

            labels[idx] = 1

        anomaly_counts = dict(
            zip(*np.unique(labels, return_counts=True))
        )
        logger.info(f"Injected {n_anomalies} anomalies: {anomaly_counts}")
        return df, labels
