"""
Move history — write JSONL log of every move, support --undo.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from .logger import get_logger

logger    = get_logger(__name__)
HIST_FILE = Path("logs/move_history.jsonl")


def record(src: Path, dest: Path) -> None:
    """Append one move record to the JSONL history file."""
    HIST_FILE.parent.mkdir(exist_ok=True)
    entry = {"src": str(src), "dest": str(dest), "ts": datetime.now().isoformat()}
    with HIST_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def load_history() -> list[dict]:
    if not HIST_FILE.exists():
        return []
    entries = []
    with HIST_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def undo(display) -> None:
    """Reverse every recorded move (most-recent first), then clear history."""
    from .display import Display
    display: Display

    entries = load_history()
    if not entries:
        display.info("[yellow]No move history found — nothing to undo.[/]")
        return

    display.info(f"Undoing [bold]{len(entries)}[/] moves (most-recent first)…\n")

    undone = errors = missing = 0
    for entry in reversed(entries):
        dest = Path(entry["dest"])
        src  = Path(entry["src"])

        if not dest.exists():
            display.info(f"  [dim]MISS[/]  [yellow]{dest.name}[/] — not at expected location, skipping")
            missing += 1
            continue
        try:
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest), str(src))
            display.info(f"  [cyan]UNDO[/]  [white]{dest.name}[/] [dim]→[/] [cyan]{src.parent}/[/]")
            logger.info(f"Undone: {dest} → {src}")
            undone += 1
        except Exception as exc:
            display.error(f"Failed to undo {dest.name}: {exc}")
            logger.error(f"Undo error for {dest}: {exc}")
            errors += 1

    display.console.print(
        f"\n  [green]Undone:[/] {undone}  "
        f"[yellow]Missing:[/] {missing}  "
        f"[red]Errors:[/] {errors}\n"
    )

    if errors == 0:
        HIST_FILE.unlink(missing_ok=True)
        display.info("[dim]History cleared.[/]")
    else:
        display.info("[dim]History kept (some errors occurred).[/]")
