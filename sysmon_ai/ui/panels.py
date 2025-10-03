"""Rich terminal dashboard panels."""

import logging
from typing import Any, Dict, List, Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sysmon_ai.utils import format_duration, horizontal_bar, sparkline

logger = logging.getLogger(__name__)


class MetricPanel:
    """Base metric panel for dashboard."""

    def __init__(self, title: str, unit: str = "%"):
        """
        Initialize metric panel.

        Args:
            title: Panel title
            unit: Measurement unit
        """
        self.title = title
        self.unit = unit

    def render(
        self,
        current: float,
        history: List[float],
        threshold: Optional[float] = None,
        is_anomaly: bool = False,
    ) -> Panel:
        """
        Render metric panel.

        Args:
            current: Current value
            history: Historical values for sparkline
            threshold: Optional threshold for coloring
            is_anomaly: Whether current value is anomalous

        Returns:
            Rendered Panel
        """
        # Determine color
        if is_anomaly:
            color = "red"
        elif threshold and current >= threshold:
            color = "yellow"
        elif current >= 80:
            color = "orange"
        else:
            color = "green"

        # Build content
        content = Text()
        content.append(f"{current:.1f}{self.unit}\n", style=f"bold {color}")

        # Sparkline
        if history:
            spark = sparkline(history)
            content.append(f"Trend: {spark}\n", style="dim")

        # Bar
        max_val = threshold if threshold else 100
        bar = horizontal_bar(current, max_val, width=30)
        content.append(f"{bar}\n", style=color)

        # Anomaly badge
        if is_anomaly:
            content.append("⚠️  ANOMALY", style="bold red")

        return Panel(
            content,
            title=self.title,
            border_style=color,
            expand=False,
        )


class SystemStatsPanel:
    """System statistics panel."""

    @staticmethod
    def render(stats: Dict[str, Any]) -> Panel:
        """
        Render system stats.

        Args:
            stats: Dict with system information

        Returns:
            Rendered Panel
        """
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        for key, value in stats.items():
            table.add_row(key, str(value))

        return Panel(table, title="System", border_style="blue")


class AlertsPanel:
    """Recent alerts panel."""

    @staticmethod
    def render(alerts: List[Dict[str, Any]], max_alerts: int = 10) -> Panel:
        """
        Render recent alerts.

        Args:
            alerts: List of alert dicts
            max_alerts: Maximum alerts to show

        Returns:
            Rendered Panel
        """
        if not alerts:
            return Panel(
                Text("No recent alerts", style="dim"),
                title="Alerts",
                border_style="green",
            )

        content = Text()
        for alert in alerts[:max_alerts]:
            alert.get("ts", 0)
            msg = alert.get("explanation", "Unknown")
            alert_type = alert.get("type", "anomaly")

            style = "red" if alert_type == "anomaly" else "yellow"
            content.append("• ", style=style)
            content.append(f"{msg}\n", style="white")

        border_color = (
            "red"
            if any(a.get("type") == "anomaly" for a in alerts[:3])
            else "yellow"
        )

        return Panel(
            content,
            title=f"Alerts ({len(alerts)})",
            border_style=border_color,
        )


class ForecastPanel:
    """Forecast information panel."""

    @staticmethod
    def render(forecasts: Dict[str, Dict[str, float]]) -> Panel:
        """
        Render forecast panel.

        Args:
            forecasts: Dict mapping metric to forecast data

        Returns:
            Rendered Panel
        """
        if not forecasts:
            return Panel(
                Text("No forecasts available", style="dim"),
                title="Forecasts",
                border_style="blue",
            )

        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Time to Threshold", style="white")
        table.add_column("Confidence", style="dim")

        for metric, data in forecasts.items():
            time_min = data.get("time_to_threshold_minutes", 0)
            lower = data.get("confidence_lower", 0)
            upper = data.get("confidence_upper", 0)

            time_str = format_duration(time_min * 60)

            # Color based on urgency
            if time_min < 60:  # < 1 hour
                style = "red"
            elif time_min < 1440:  # < 24 hours
                style = "yellow"
            else:
                style = "green"

            table.add_row(
                metric,
                Text(time_str, style=style),
                f"±{format_duration((upper - lower) * 60 / 2)}",
            )

        return Panel(table, title="Forecasts (48-72h)", border_style="blue")
