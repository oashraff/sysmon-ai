"""Alert rules and triggers."""

import logging
from typing import Any, Dict, List, Optional

from sysmon_ai.config import ThresholdConfig
from sysmon_ai.detection import AnomalyEvent, ForecastEvent

logger = logging.getLogger(__name__)


class AlertRule:
    """Base alert rule."""

    def __init__(self, name: str, severity: str = "warning"):
        """
        Initialize rule.

        Args:
            name: Rule name
            severity: Severity level (info, warning, critical)
        """
        self.name = name
        self.severity = severity

    def evaluate(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Evaluate rule on data.

        Args:
            data: Input data dict

        Returns:
            Alert message if triggered, None otherwise
        """
        raise NotImplementedError


class ThresholdRule(AlertRule):
    """Metric threshold alert rule."""

    def __init__(
        self,
        name: str,
        metric: str,
        threshold: float,
        severity: str = "warning",
    ):
        """
        Initialize threshold rule.

        Args:
            name: Rule name
            metric: Metric name
            threshold: Threshold value
            severity: Severity level
        """
        super().__init__(name, severity)
        self.metric = metric
        self.threshold = threshold

    def evaluate(self, data: Dict[str, Any]) -> Optional[str]:
        """Evaluate threshold."""
        value = data.get(self.metric)
        if value is None:
            return None

        if value >= self.threshold:
            return f"{self.metric} exceeded threshold: {value:.1f} >= {self.threshold}"

        return None


class AnomalyRule(AlertRule):
    """Anomaly detection alert rule."""

    def __init__(self, name: str = "anomaly_detected"):
        """Initialize anomaly rule."""
        super().__init__(name, severity="critical")

    def evaluate(self, data: Dict[str, Any]) -> Optional[str]:
        """Check for anomaly flag."""
        if data.get("is_anomaly"):
            score = data.get("score", 0)
            return f"Anomaly detected (score={score:.3f})"
        return None


class ForecastRule(AlertRule):
    """Forecast-based alert rule."""

    def __init__(
        self,
        name: str,
        metric: str,
        horizon_hours: int = 24,
    ):
        """
        Initialize forecast rule.

        Args:
            name: Rule name
            metric: Metric name
            horizon_hours: Alert if forecast within this horizon
        """
        super().__init__(name, severity="warning")
        self.metric = metric
        self.horizon_hours = horizon_hours

    def evaluate(self, data: Dict[str, Any]) -> Optional[str]:
        """Evaluate forecast."""
        forecast = data.get("forecast", {}).get(self.metric)
        if not forecast:
            return None

        time_min = forecast.get("time_to_threshold_minutes", float("inf"))

        if time_min < (self.horizon_hours * 60):
            hours = time_min / 60
            return f"{self.metric} will reach threshold in {hours:.1f}h"

        return None


class RuleEngine:
    """
    Evaluates alert rules and generates alerts.

    Manages multiple rules and deduplication.
    """

    def __init__(self, thresholds: ThresholdConfig):
        """
        Initialize rule engine.

        Args:
            thresholds: Threshold configuration
        """
        self.thresholds = thresholds
        self.rules: List[AlertRule] = []
        self._last_alerts: Dict[str, float] = {}
        self._cooldown_seconds = 60  # Prevent alert spam

        # Default rules
        self._add_default_rules()

    def _add_default_rules(self) -> None:
        """Add default threshold rules."""
        self.rules.append(
            ThresholdRule("cpu_high", "cpu_pct", self.thresholds.cpu_pct, "warning")
        )
        self.rules.append(
            ThresholdRule("mem_high", "mem_pct", self.thresholds.mem_pct, "warning")
        )
        self.rules.append(
            ThresholdRule("swap_high", "swap_pct", self.thresholds.swap_pct, "warning")
        )
        self.rules.append(AnomalyRule())

    def add_rule(self, rule: AlertRule) -> None:
        """Add custom rule."""
        self.rules.append(rule)

    def evaluate(
        self,
        data: Dict[str, Any],
        current_ts: float,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all rules and return triggered alerts.

        Args:
            data: Input data
            current_ts: Current timestamp

        Returns:
            List of alert dicts
        """
        alerts = []

        for rule in self.rules:
            # Check cooldown
            last_alert_ts = self._last_alerts.get(rule.name, 0)
            if current_ts - last_alert_ts < self._cooldown_seconds:
                continue

            # Evaluate rule
            message = rule.evaluate(data)
            if message:
                alerts.append({
                    "rule": rule.name,
                    "severity": rule.severity,
                    "message": message,
                    "ts": current_ts,
                })
                self._last_alerts[rule.name] = current_ts
                logger.info(f"Alert triggered: {rule.name} - {message}")

        return alerts
