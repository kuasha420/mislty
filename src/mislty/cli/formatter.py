"""
mislty.cli.formatter
~~~~~~~~~~~~~~~~~~~~

Terminal formatting engine for the MisLTy CLI suite.
Provides zero-dependency ANSI color styling, Unicode status gauges,
clean tabular alignment, and automatic TTY/NO_COLOR detection.
"""

from __future__ import annotations

import os
import sys
from typing import Any, List, Optional, Sequence


class Colors:
    """ANSI color and formatting escape sequences."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class TerminalFormatter:
    """
    Format strings with optional ANSI styling and visual glyphs.
    Respects NO_COLOR standard and terminal redirection.
    """

    def __init__(self, force_color: Optional[bool] = None) -> None:
        if force_color is not None:
            self._color_enabled = force_color
        else:
            no_color = bool(os.environ.get("NO_COLOR"))
            is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
            self._color_enabled = is_tty and not no_color

    @property
    def color_enabled(self) -> bool:
        return self._color_enabled

    def style(self, text: str, *styles: str) -> str:
        """Apply styles if color is enabled; otherwise return text unchanged."""
        if not self._color_enabled or not styles:
            return text
        prefix = "".join(styles)
        return f"{prefix}{text}{Colors.RESET}"

    def bold(self, text: str) -> str:
        return self.style(text, Colors.BOLD)

    def green(self, text: str, bold: bool = False) -> str:
        return self.style(text, Colors.BOLD if bold else "", Colors.GREEN)

    def red(self, text: str, bold: bool = False) -> str:
        return self.style(text, Colors.BOLD if bold else "", Colors.RED)

    def yellow(self, text: str, bold: bool = False) -> str:
        return self.style(text, Colors.BOLD if bold else "", Colors.YELLOW)

    def cyan(self, text: str, bold: bool = False) -> str:
        return self.style(text, Colors.BOLD if bold else "", Colors.CYAN)

    def blue(self, text: str, bold: bool = False) -> str:
        return self.style(text, Colors.BOLD if bold else "", Colors.BLUE)

    def dim(self, text: str) -> str:
        return self.style(text, Colors.DIM)

    def format_signal_meter(self, rssi: Optional[int], dbm: Optional[int] = None, width: int = 10) -> str:
        """
        Render a visual Unicode signal meter: e.g. [████████░░] -65 dBm (4 bars).
        """
        if rssi is None or rssi == 99 or rssi <= 0:
            return self.dim("[░░░░░░░░░░] No Signal")

        # 3GPP CSQ 0-31
        clamped_csq = min(31, max(0, rssi))
        ratio = clamped_csq / 31.0
        filled_count = round(ratio * width)
        empty_count = width - filled_count

        bar = "█" * filled_count + "░" * empty_count

        # Color based on signal strength
        if clamped_csq >= 20:
            meter = self.green(f"[{bar}]", bold=True)
            bars_label = self.green("4/4 bars")
        elif clamped_csq >= 14:
            meter = self.cyan(f"[{bar}]")
            bars_label = self.cyan("3/4 bars")
        elif clamped_csq >= 8:
            meter = self.yellow(f"[{bar}]")
            bars_label = self.yellow("2/4 bars")
        else:
            meter = self.red(f"[{bar}]")
            bars_label = self.red("1/4 bars (weak)")

        dbm_str = f" {dbm} dBm" if dbm is not None else ""
        return f"{meter} {clamped_csq}/31{dbm_str} ({bars_label})"

    def format_badge(self, state: bool, on_text: str = "ONLINE", off_text: str = "OFFLINE") -> str:
        """Render colored state badge."""
        if state:
            return self.green(f"● {on_text}", bold=True)
        return self.red(f"○ {off_text}", bold=True)

    def format_bytes(self, num_bytes: Union[int, float]) -> str:
        """Format byte counts into human-readable KiB, MiB, GiB."""
        num = float(num_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(num) < 1024.0:
                return f"{num:.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} PB"

    def format_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[Any]],
        padding: int = 2,
    ) -> str:
        """Render an aligned monospace text table."""
        if not headers:
            return ""

        str_headers = [str(h) for h in headers]
        str_rows = [[str(cell) for cell in row] for row in rows]

        # Calculate max column widths
        col_widths = [len(h) for h in str_headers]
        for row in str_rows:
            for idx, cell in enumerate(row):
                if idx < len(col_widths):
                    col_widths[idx] = max(col_widths[idx], len(cell))
                else:
                    col_widths.append(len(cell))

        pad_str = " " * padding

        # Header line
        header_line = pad_str.join(
            h.ljust(col_widths[i]) for i, h in enumerate(str_headers)
        )
        sep_line = pad_str.join("-" * col_widths[i] for i in range(len(str_headers)))

        lines = [self.bold(header_line), self.dim(sep_line)]

        # Row lines
        for row in str_rows:
            formatted_cells = []
            for i, cell in enumerate(row):
                width = col_widths[i] if i < len(col_widths) else len(cell)
                formatted_cells.append(cell.ljust(width))
            lines.append(pad_str.join(formatted_cells))

        return "\n".join(lines)
