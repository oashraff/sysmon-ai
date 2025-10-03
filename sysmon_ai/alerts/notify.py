"""Local notification system."""

import logging
import sys
from typing import Any, Dict

logger = logging.getLogger(__name__)


class Notifier:
    """
    Local notification system.

    Supports console output and optional system notifications.
    """

    def __init__(self, enable_sound: bool = False):
        """
        Initialize notifier.

        Args:
            enable_sound: Whether to play alert sound
        """
        self.enable_sound = enable_sound

    def notify(self, alert: Dict[str, Any]) -> None:
        """
        Send notification for alert.

        Args:
            alert: Alert dict with message, severity, etc.
        """
        severity = alert.get("severity", "info")
        message = alert.get("message", "")

        # Console notification with color
        if severity == "critical":
            color = "\033[91m"  # Red
        elif severity == "warning":
            color = "\033[93m"  # Yellow
        else:
            color = "\033[92m"  # Green

        reset = "\033[0m"

        print(f"\n{color}[{severity.upper()}] {message}{reset}", file=sys.stderr)

        # Sound alert
        if self.enable_sound and severity in ("critical", "warning"):
            self._play_sound()

    def _play_sound(self) -> None:
        """Play alert sound (platform-specific)."""
        try:
            # Simple terminal bell
            print("\a", end="", flush=True)
        except Exception as e:
            logger.debug(f"Failed to play sound: {e}")
