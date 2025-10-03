"""Configuration management with YAML + environment overrides."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class SamplingConfig:
    """Metrics sampling configuration."""

    rate_seconds: float = 1.0
    batch_size: int = 100
    max_queue_size: int = 10000


@dataclass
class StorageConfig:
    """Database storage configuration."""

    db_path: str = "sysmon.db"
    retention_days: int = 30
    wal_checkpoint_interval: int = 1000


@dataclass
class AnomalyConfig:
    """Anomaly detection configuration."""

    contamination: float = 0.05
    n_estimators: int = 100
    max_samples: int = 256
    random_state: int = 42
    baseline_window_days: int = 7
    target_fpr: float = 0.05


@dataclass
class ForecastConfig:
    """Forecasting configuration."""

    horizon_hours: int = 72
    min_training_samples: int = 1000
    algo: str = "linear"  # linear or gbr
    confidence_level: float = 0.95


@dataclass
class ThresholdConfig:
    """Alert thresholds for metrics."""

    cpu_pct: float = 90.0
    mem_pct: float = 90.0
    disk_pct: float = 85.0
    swap_pct: float = 80.0


@dataclass
class DashboardConfig:
    """Dashboard UI configuration."""

    refresh_rate: float = 1.0
    default_view_hours: int = 1
    enable_images: bool = True
    ascii_fallback: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    file_path: str = "logs/sysmon.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class Config:
    """Master configuration."""

    host: str = field(default_factory=lambda: os.uname().nodename)
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    anomaly: AnomalyConfig = field(default_factory=AnomalyConfig)
    forecast: ForecastConfig = field(default_factory=ForecastConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """
        Load configuration from YAML file with environment overrides.

        Args:
            path: Path to YAML config file. If None, uses default config.

        Returns:
            Config instance with merged values.
        """
        config_dict: Dict[str, Any] = {}

        if path and path.exists():
            with open(path, "r") as f:
                config_dict = yaml.safe_load(f) or {}

        # Environment overrides
        env_mapping = {
            "SYSMON_HOST": ("host",),
            "SYSMON_DB_PATH": ("storage", "db_path"),
            "SYSMON_SAMPLING_RATE": ("sampling", "rate_seconds"),
            "SYSMON_LOG_LEVEL": ("logging", "level"),
        }

        for env_key, path_tuple in env_mapping.items():
            if env_val := os.getenv(env_key):
                current = config_dict
                for key in path_tuple[:-1]:
                    current = current.setdefault(key, {})
                current[path_tuple[-1]] = _parse_env_value(env_val)

        return cls(
            host=config_dict.get("host", os.uname().nodename),
            sampling=_build_nested(SamplingConfig, config_dict.get("sampling", {})),
            storage=_build_nested(StorageConfig, config_dict.get("storage", {})),
            anomaly=_build_nested(AnomalyConfig, config_dict.get("anomaly", {})),
            forecast=_build_nested(ForecastConfig, config_dict.get("forecast", {})),
            thresholds=_build_nested(ThresholdConfig, config_dict.get("thresholds", {})),
            dashboard=_build_nested(DashboardConfig, config_dict.get("dashboard", {})),
            logging=_build_nested(LoggingConfig, config_dict.get("logging", {})),
        )

    def save(self, path: Path) -> None:
        """Save configuration to YAML file."""
        config_dict = {
            "host": self.host,
            "sampling": {
                "rate_seconds": self.sampling.rate_seconds,
                "batch_size": self.sampling.batch_size,
                "max_queue_size": self.sampling.max_queue_size,
            },
            "storage": {
                "db_path": self.storage.db_path,
                "retention_days": self.storage.retention_days,
                "wal_checkpoint_interval": self.storage.wal_checkpoint_interval,
            },
            "anomaly": {
                "contamination": self.anomaly.contamination,
                "n_estimators": self.anomaly.n_estimators,
                "max_samples": self.anomaly.max_samples,
                "random_state": self.anomaly.random_state,
                "baseline_window_days": self.anomaly.baseline_window_days,
                "target_fpr": self.anomaly.target_fpr,
            },
            "forecast": {
                "horizon_hours": self.forecast.horizon_hours,
                "min_training_samples": self.forecast.min_training_samples,
                "algo": self.forecast.algo,
                "confidence_level": self.forecast.confidence_level,
            },
            "thresholds": {
                "cpu_pct": self.thresholds.cpu_pct,
                "mem_pct": self.thresholds.mem_pct,
                "disk_pct": self.thresholds.disk_pct,
                "swap_pct": self.thresholds.swap_pct,
            },
            "dashboard": {
                "refresh_rate": self.dashboard.refresh_rate,
                "default_view_hours": self.dashboard.default_view_hours,
                "enable_images": self.dashboard.enable_images,
                "ascii_fallback": self.dashboard.ascii_fallback,
            },
            "logging": {
                "level": self.logging.level,
                "file_path": self.logging.file_path,
                "max_bytes": self.logging.max_bytes,
                "backup_count": self.logging.backup_count,
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False)


def _build_nested(cls: type, data: Dict[str, Any]) -> Any:
    """Build dataclass instance from dict."""
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def _parse_env_value(value: str) -> Any:
    """Parse environment variable value to appropriate type."""
    if value.lower() in ("true", "yes", "1"):
        return True
    if value.lower() in ("false", "no", "0"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
