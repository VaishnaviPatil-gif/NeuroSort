#!/usr/bin/env python3
"""
NeuroSort — Automated File Organizer Bot

Usage:
  python main.py --watch ~/Downloads
  python main.py --watch ~/Downloads --dry-run
  python main.py --undo
"""

import argparse
import signal
import sys
import time
from pathlib import Path

from src.watcher import FileWatcher
from src.history import undo
from src.logger  import get_logger
from src.display import Display

logger  = get_logger(__name__)
display = Display()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="NeuroSort: automated file organizer bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py --watch ~/Downloads
  python main.py --watch ~/Downloads --dry-run
  python main.py --watch ~/Desktop --config config/rules.yaml
  python main.py --undo
        """,
    )
    p.add_argument("--watch",   type=Path,        metavar="DIR",    help="Directory to monitor")
    p.add_argument("--dry-run", action="store_true",                 help="Preview moves without applying")
    p.add_argument("--config",  type=Path, default=Path("config/rules.yaml"), help="Rules config (YAML)")
    p.add_argument("--undo",    action="store_true",                 help="Reverse all moves from last session")
    return p.parse_args()


def run_watch(args: argparse.Namespace) -> None:
    watch_dir = args.watch.expanduser().resolve()
    if not watch_dir.exists():
        display.error(f"Directory not found: {watch_dir}")
        sys.exit(1)

    display.info(f"Watching:  [bold cyan]{watch_dir}[/]")
    display.info(f"Config:    [dim]{args.config}[/]")
    display.info(f"Dry run:   [bold]{'yes' if args.dry_run else 'no'}[/]")
    display.console.print()

    watcher = FileWatcher(watch_dir=watch_dir, config_path=args.config, dry_run=args.dry_run)

    def _shutdown(sig, frame):
        display.info("\n[yellow]Shutting down…[/]")
        watcher.stop()
        display.summary(watcher.stats)
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    watcher.start()
    while True:
        time.sleep(1)


def main() -> None:
    args = parse_args()
    display.banner()

    if args.undo:
        undo(display)
        return

    if not args.watch:
        display.error("Provide [bold]--watch DIR[/] or [bold]--undo[/]. Run with --help for usage.")
        sys.exit(1)

    run_watch(args)


if __name__ == "__main__":
    main()
