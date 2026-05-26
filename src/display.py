"""
Terminal display — Rich-powered UI with full stats dashboard.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from .watcher import Stats


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


def _bar(count: int, max_count: int, width: int = 18) -> str:
    filled = round((count / max_count) * width) if max_count else 0
    return "█" * filled + "░" * (width - filled)


class Display:
    def __init__(self) -> None:
        self.console = Console()

    # ── decorative ───────────────────────────────
    def banner(self) -> None:
        self.console.print(Panel.fit(
            "[bold cyan]SmartWatch[/]  [dim]Automated File Organizer Bot[/]",
            border_style="cyan",
            padding=(0, 4),
        ))
        self.console.print()

    # ── live output ──────────────────────────────
    def info(self, msg: str) -> None:
        self.console.print(f"  [dim]{self._ts()}[/]  {msg}")

    def moved(self, filename: str, folder: str, dry: bool = False, renamed: bool = False) -> None:
        if dry:
            tag = "[yellow]DRY[/]"
        elif renamed:
            tag = "[magenta]DUP[/]"
        else:
            tag = "[green]MOV[/]"
        self.console.print(
            f"  [dim]{self._ts()}[/]  {tag}  "
            f"[white]{filename}[/] [dim]→[/] [cyan]{folder}/[/]"
        )

    def error(self, msg: str) -> None:
        self.console.print(f"  [dim]{self._ts()}[/]  [red bold]ERR[/]  {msg}")

    # ── shutdown dashboard ───────────────────────
    def summary(self, stats: "Stats") -> None:
        self.console.print()

        cats = stats.by_category
        if not cats:
            self.console.print("  [dim]Nothing moved this session.[/]\n")
            return

        max_count = max(cats.values())
        most_common = max(cats, key=cats.__getitem__)

        # ── category breakdown table ──
        table = Table(
            title="Category Breakdown",
            border_style="dim",
            show_header=True,
            header_style="bold dim",
            padding=(0, 1),
        )
        table.add_column("Folder",     style="cyan",    min_width=16)
        table.add_column("Bar",        style="green",   min_width=20, no_wrap=True)
        table.add_column("Files",      justify="right", style="bold white")
        table.add_column("Size",       justify="right", style="dim")

        for folder, count in sorted(cats.items(), key=lambda x: -x[1]):
            bar   = _bar(count, max_count)
            size  = _fmt_bytes(stats.bytes_by_category.get(folder, 0))
            table.add_row(folder, bar, str(count), size)

        self.console.print(table)
        self.console.print()

        # ── totals panel ──
        lines = [
            f"  [green]Moved[/]       {stats.moved} files",
            f"  [yellow]Skipped[/]     {stats.skipped} files",
            f"  [magenta]Duplicates[/]  {stats.duplicates} renamed",
            f"  [red]Errors[/]      {stats.errors}",
            f"  [cyan]Size moved[/]  {_fmt_bytes(stats.bytes_moved)}",
            f"  [bold]Top type[/]    {most_common}",
        ]
        self.console.print(Panel(
            "\n".join(lines),
            title="[bold]Session Summary[/]",
            border_style="cyan",
            padding=(0, 2),
        ))
        self.console.print()

    @staticmethod
    def _ts() -> str:
        return datetime.now().strftime("%H:%M:%S")
