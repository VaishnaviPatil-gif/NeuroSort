"""
Core file watcher — watchdog observer + rule-based organizer.
"""

from __future__ import annotations

import shutil
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import load_config, FileRule, IgnoreList
from .history import record as record_move
from .logger import get_logger
from .display import Display

logger  = get_logger(__name__)
display = Display()


# ──────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────
@dataclass
class Stats:
    moved:      int = 0
    skipped:    int = 0
    errors:     int = 0
    duplicates: int = 0          # files renamed to avoid collision
    bytes_moved: int = 0
    by_category:       dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_by_category: dict[str, int] = field(default_factory=lambda: defaultdict(int))


# ──────────────────────────────────────────────
# Watchdog event handler
# ──────────────────────────────────────────────
class FileEventHandler(FileSystemEventHandler):
    def __init__(self, organizer: "FileOrganizer") -> None:
        super().__init__()
        self.organizer = organizer
        self._processing: set[str] = set()
        self._lock = threading.Lock()

    def _handle(self, src_path: str) -> None:
        path = Path(src_path)
        if path.name.startswith((".", "~", "_")):
            return
        key = str(path)
        with self._lock:
            if key in self._processing:
                return
            self._processing.add(key)
        try:
            self.organizer.process(path)
        finally:
            with self._lock:
                self._processing.discard(key)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle(event.dest_path)


# ──────────────────────────────────────────────
# Organizer
# ──────────────────────────────────────────────
class FileOrganizer:
    def __init__(
        self,
        watch_dir: Path,
        rules:     list[FileRule],
        ignores:   IgnoreList,
        dry_run:   bool,
    ) -> None:
        self.watch_dir = watch_dir
        self.rules     = rules
        self.ignores   = ignores
        self.dry_run   = dry_run
        self.stats     = Stats()

    # ── rule matching ────────────────────────────
    def _match(self, path: Path) -> Optional[FileRule]:
        for rule in self.rules:
            if rule.matches(path):
                return rule
        return None

    # ── process one file ─────────────────────────
    def process(self, path: Path) -> None:
        if not path.exists() or path.is_dir():
            return

        # Ignore list
        if self.ignores.matches(path):
            logger.debug(f"Ignored: {path.name}")
            self.stats.skipped += 1
            return

        rule = self._match(path)
        if rule is None:
            logger.debug(f"No rule matched: {path.name}")
            self.stats.skipped += 1
            return

        subdir    = rule.dest_subdir()          # may include time subfolders
        dest_dir  = self.watch_dir / subdir
        dest_path = dest_dir / path.name

        # Collision resolution
        is_dupe = False
        if dest_path.exists():
            is_dupe = True
            counter = 1
            while dest_path.exists():
                dest_path = dest_dir / f"{path.stem}_{counter}{path.suffix}"
                counter  += 1

        try:
            file_bytes = path.stat().st_size
        except OSError:
            file_bytes = 0

        if self.dry_run:
            display.moved(path.name, subdir, dry=True)
            self._tally(subdir, file_bytes, is_dupe)
            return

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest_path))
            record_move(path, dest_path)
            display.moved(path.name, subdir, dry=False, renamed=is_dupe)
            logger.info(f"Moved: {path.name} → {subdir}/")
            self._tally(subdir, file_bytes, is_dupe)
        except Exception as exc:
            logger.error(f"Failed to move {path.name}: {exc}")
            display.error(f"Error moving {path.name}: {exc}")
            self.stats.errors += 1

    def _tally(self, folder: str, nbytes: int, is_dupe: bool) -> None:
        self.stats.moved                     += 1
        self.stats.bytes_moved               += nbytes
        self.stats.by_category[folder]       += 1
        self.stats.bytes_by_category[folder] += nbytes
        if is_dupe:
            self.stats.duplicates += 1


# ──────────────────────────────────────────────
# Watcher (lifecycle)
# ──────────────────────────────────────────────
class FileWatcher:
    def __init__(self, watch_dir: Path, config_path: Path, dry_run: bool) -> None:
        self.watch_dir = watch_dir
        self.dry_run   = dry_run

        rules, ignores = load_config(config_path)
        self.organizer = FileOrganizer(watch_dir, rules, ignores, dry_run)
        self.stats     = self.organizer.stats

        self._observer = Observer()
        self._handler  = FileEventHandler(self.organizer)

    def start(self) -> None:
        display.info("Processing existing files…")
        for f in sorted(self.watch_dir.glob("*")):
            if f.is_file():
                self.organizer.process(f)

        self._observer.schedule(self._handler, str(self.watch_dir), recursive=False)
        self._observer.start()
        display.info("[green]Bot is live — press Ctrl+C to stop.[/]\n")

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
