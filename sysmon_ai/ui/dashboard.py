"""Terminal dashboard with Rich."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sysmon_ai.ui.panels import AlertsPanel, ForecastPanel, MetricPanel, SystemStatsPanel
from sysmon_ai.utils import format_duration, get_hostname

logger = logging.getLogger(__name__)


class Dashboard:
    """
    Live terminal dashboard using Rich.

    Displays system metrics, anomalies, and forecasts in real-time.
    """

    def __init__(
        self,
        refresh_rate: float = 1.0,
        show_forecasts: bool = True,
    ):
        """
        Initialize dashboard.

        Args:
            refresh_rate: Refresh interval in seconds
            show_forecasts: Whether to show forecast panel
        """
        self.refresh_rate = refresh_rate
        self.show_forecasts = show_forecasts
        self.console = Console()

        # Metric history
        self._history: Dict[str, List[float]] = {
            "cpu": [],
            "mem": [],
            "disk_read": [],
            "disk_write": [],
            "net_up": [],
            "net_down": [],
        }
        self._max_history = 100

        # Panels
        self.cpu_panel = MetricPanel("CPU", "%")
        self.mem_panel = MetricPanel("Memory", "%")
        self.disk_panel = MetricPanel("Disk I/O", "MB/s")
        self.net_panel = MetricPanel("Network", "MB/s")

        self._start_time = time.time()

    def render_frame(
        self,
        sample: Dict[str, Any],
        anomalies: Optional[Dict[str, bool]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
        forecasts: Optional[Dict[str, Dict[str, float]]] = None,
        db_stats: Optional[Dict[str, Any]] = None,
    ) -> Layout:
        """
        Render single dashboard frame.

        Args:
            sample: Current sample data
            anomalies: Dict of metric -> is_anomaly
            alerts: List of recent alerts
            forecasts: Forecast data
            db_stats: Database statistics

        Returns:
            Rendered Layout
        """
        # Update history
        self._update_history(sample)

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        # Header
        layout["header"].update(self._render_header(sample))

        # Body
        body_layout = Layout()
        body_layout.split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        # Left: metrics
        left_layout = Layout()
        left_layout.split_row(
            Layout(name="cpu_mem"),
            Layout(name="io"),
        )

        cpu_mem_layout = Layout()
        cpu_mem_layout.split_column(
            Layout(name="cpu"),
            Layout(name="mem"),
        )

        io_layout = Layout()
        io_layout.split_column(
            Layout(name="disk"),
            Layout(name="net"),
        )

        # Render metric panels
        anomalies = anomalies or {}

        cpu_mem_layout["cpu"].update(
            self.cpu_panel.render(
                sample.get("cpu_pct", 0),
                self._history["cpu"],
                threshold=90,
                is_anomaly=anomalies.get("cpu", False),
            )
        )

        cpu_mem_layout["mem"].update(
            self.mem_panel.render(
                sample.get("mem_pct", 0),
                self._history["mem"],
                threshold=90,
                is_anomaly=anomalies.get("mem", False),
            )
        )

        disk_read_mb = sample.get("disk_read_bps", 0) / 1e6
        disk_write_mb = sample.get("disk_write_bps", 0) / 1e6
        disk_total = disk_read_mb + disk_write_mb

        io_layout["disk"].update(
            Panel(
                Text(f"Read:  {disk_read_mb:>8.2f} MB/s\n", style="cyan")
                + Text(f"Write: {disk_write_mb:>8.2f} MB/s", style="magenta"),
                title="Disk I/O",
                border_style="blue",
            )
        )

        net_up_mb = sample.get("net_up_bps", 0) / 1e6
        net_down_mb = sample.get("net_down_bps", 0) / 1e6

        io_layout["net"].update(
            Panel(
                Text(f"Upload:   {net_up_mb:>8.2f} MB/s\n", style="cyan")
                + Text(f"Download: {net_down_mb:>8.2f} MB/s", style="magenta"),
                title="Network",
                border_style="blue",
            )
        )

        left_layout["cpu_mem"].update(cpu_mem_layout)
        left_layout["io"].update(io_layout)

        # Right: alerts and forecasts
        right_layout = Layout()

        if self.show_forecasts and forecasts:
            right_layout.split_column(
                Layout(name="alerts", ratio=2),
                Layout(name="forecasts", ratio=1),
            )
            right_layout["forecasts"].update(ForecastPanel.render(forecasts))
        else:
            right_layout.split_column(Layout(name="alerts"))

        right_layout["alerts"].update(AlertsPanel.render(alerts or []))

        body_layout["left"].update(left_layout)
        body_layout["right"].update(right_layout)

        layout["body"].update(body_layout)

        # Footer
        layout["footer"].update(self._render_footer(db_stats))

        return layout

    def _render_header(self, sample: Dict[str, Any]) -> Panel:
        """Render header bar."""
        uptime = format_duration(time.time() - self._start_time)
        host = sample.get("host", get_hostname())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header_text = Text()
        header_text.append("🖥️  ", style="bold")
        header_text.append(f"{host}", style="bold cyan")
        header_text.append(f"  |  Uptime: {uptime}", style="dim")
        header_text.append(f"  |  {now}", style="dim")
        header_text.append(f"  |  Refresh: {self.refresh_rate:.1f}s", style="dim")

        return Panel(header_text, style="bold white on blue")

    def _render_footer(self, db_stats: Optional[Dict[str, Any]]) -> Panel:
        """Render footer bar."""
        footer_text = Text()
        footer_text.append("Controls: ", style="bold")
        footer_text.append("[q]", style="bold red")
        footer_text.append(" quit  ", style="dim")
        footer_text.append("[f]", style="bold yellow")
        footer_text.append(" toggle forecast  ", style="dim")
        footer_text.append("[r]", style="bold green")
        footer_text.append(" reload", style="dim")

        if db_stats:
            samples = db_stats.get("sample_count", 0)
            size_mb = db_stats.get("db_size_mb", 0)
            footer_text.append(f"  |  DB: {samples:,} samples, {size_mb:.1f} MB", style="dim")

        return Panel(footer_text, style="white on black")

    def _update_history(self, sample: Dict[str, Any]) -> None:
        """Update metric history."""
        self._history["cpu"].append(sample.get("cpu_pct", 0))
        self._history["mem"].append(sample.get("mem_pct", 0))
        self._history["disk_read"].append(sample.get("disk_read_bps", 0) / 1e6)
        self._history["disk_write"].append(sample.get("disk_write_bps", 0) / 1e6)
        self._history["net_up"].append(sample.get("net_up_bps", 0) / 1e6)
        self._history["net_down"].append(sample.get("net_down_bps", 0) / 1e6)

        # Trim history
        for key in self._history:
            if len(self._history[key]) > self._max_history:
                self._history[key] = self._history[key][-self._max_history :]

    def run_live(
        self,
        data_callback: Any,
        stop_event: Any,
    ) -> None:
        """
        Run live dashboard with data callback.

        Args:
            data_callback: Callable that returns (sample, anomalies, alerts, forecasts, db_stats)
            stop_event: Threading event to signal stop
        """
        with Live(
            self.render_frame({}, {}, [], {}, {}),
            refresh_per_second=1 / self.refresh_rate,
            console=self.console,
        ) as live:
            while not stop_event.is_set():
                try:
                    data = data_callback()
                    if data:
                        sample, anomalies, alerts, forecasts, db_stats = data
                        layout = self.render_frame(
                            sample, anomalies, alerts, forecasts, db_stats
                        )
                        live.update(layout)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Dashboard error: {e}", exc_info=True)

                time.sleep(self.refresh_rate)
