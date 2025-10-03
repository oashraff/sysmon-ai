"""Platform detection and capability checking."""

import platform
import sys
from typing import Optional


def get_platform() -> str:
    """
    Get normalized platform name.

    Returns:
        'linux', 'darwin', or 'windows'
    """
    return sys.platform


def is_linux() -> bool:
    """Check if running on Linux."""
    return sys.platform.startswith("linux")


def is_macos() -> bool:
    """Check if running on macOS."""
    return sys.platform == "darwin"


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def supports_cpu_temp() -> bool:
    """
    Check if platform supports CPU temperature reading.

    Returns:
        True if CPU temp is available
    """
    # CPU temp generally available on Linux, limited on macOS/Windows
    return is_linux()


def get_cpu_count() -> int:
    """Get number of CPU cores."""
    import os

    return os.cpu_count() or 1


def get_hostname() -> str:
    """Get system hostname."""
    return platform.node()


def get_os_info() -> dict[str, str]:
    """
    Get OS information.

    Returns:
        Dict with system, release, version, machine
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
    }


def can_render_unicode() -> bool:
    """
    Check if terminal supports Unicode rendering.

    Returns:
        True if Unicode is supported
    """
    try:
        sys.stdout.encoding
        # Test sparkline character
        "█".encode(sys.stdout.encoding or "utf-8")
        return True
    except (AttributeError, UnicodeEncodeError):
        return False
