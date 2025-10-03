"""ASCII sparkline generation for terminal display."""

from typing import List, Optional


def sparkline(
    data: List[float],
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    height: int = 1,
) -> str:
    """
    Generate ASCII sparkline from data.

    Args:
        data: List of numeric values
        min_val: Minimum value for scaling. If None, uses min(data)
        max_val: Maximum value for scaling. If None, uses max(data)
        height: Height of sparkline (1-8)

    Returns:
        ASCII sparkline string

    Examples:
        >>> sparkline([1, 2, 3, 4, 5])
        '▁▂▃▅█'
        >>> sparkline([5, 4, 3, 2, 1])
        '█▅▃▂▁'
    """
    if not data:
        return ""

    if len(data) == 1:
        return "▄"

    # Block characters (8 levels)
    blocks = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    min_val = min_val if min_val is not None else min(data)
    max_val = max_val if max_val is not None else max(data)

    if max_val == min_val:
        return "▄" * len(data)

    # Normalize to 0-8 range
    normalized = [
        int(((val - min_val) / (max_val - min_val)) * 8)
        for val in data
    ]

    return "".join(blocks[min(n, 8)] for n in normalized)


def horizontal_bar(
    value: float,
    max_value: float,
    width: int = 20,
    filled: str = "█",
    empty: str = "░",
) -> str:
    """
    Generate horizontal bar chart.

    Args:
        value: Current value
        max_value: Maximum value
        width: Width of bar in characters
        filled: Character for filled portion
        empty: Character for empty portion

    Returns:
        Horizontal bar string

    Examples:
        >>> horizontal_bar(50, 100, width=10)
        '█████░░░░░'
    """
    if max_value <= 0:
        return empty * width

    filled_width = int((value / max_value) * width)
    filled_width = min(filled_width, width)

    return filled * filled_width + empty * (width - filled_width)


def mini_histogram(data: List[float], bins: int = 10, height: int = 5) -> List[str]:
    """
    Generate ASCII histogram lines.

    Args:
        data: Data values
        bins: Number of histogram bins
        height: Height of histogram in lines

    Returns:
        List of ASCII lines representing histogram
    """
    if not data:
        return [" " * bins]

    min_val = min(data)
    max_val = max(data)

    if max_val == min_val:
        return [" " * bins for _ in range(height)]

    # Create bins
    bin_width = (max_val - min_val) / bins
    counts = [0] * bins

    for val in data:
        bin_idx = int((val - min_val) / bin_width)
        bin_idx = min(bin_idx, bins - 1)
        counts[bin_idx] += 1

    max_count = max(counts)
    if max_count == 0:
        return [" " * bins for _ in range(height)]

    # Generate lines
    lines = []
    for h in range(height, 0, -1):
        line = ""
        threshold = (h / height) * max_count
        for count in counts:
            line += "█" if count >= threshold else " "
        lines.append(line)

    return lines
