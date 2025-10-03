"""Event data structures."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AnomalyEvent:
    """Anomaly event data."""

    ts: int
    score: float
    metric_tags: str
    explanation: str
    host: Optional[str] = None


@dataclass
class ForecastEvent:
    """Forecast event data."""

    ts: int
    metric: str
    threshold: float
    time_to_threshold_minutes: float
    confidence_lower: float
    confidence_upper: float
    host: Optional[str] = None

    def is_critical(self, horizon_hours: int = 24) -> bool:
        """Check if forecast is within critical horizon."""
        return self.time_to_threshold_minutes < (horizon_hours * 60)
