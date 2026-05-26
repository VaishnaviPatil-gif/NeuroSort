"""
Config loader — extended rule schema:
  extensions, contains, size_gt/lt, time_based, ignore patterns.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .logger import get_logger

logger = get_logger(__name__)

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ──────────────────────────────────────────────
# Size parser: "10MB" → bytes
# ──────────────────────────────────────────────
_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)?$", re.IGNORECASE)
_SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}

def parse_size(value: Any) -> int:
    """Convert '10MB', '500KB', or bare int (bytes) to int bytes."""
    if isinstance(value, int):
        return value
    m = _SIZE_RE.match(str(value).strip())
    if not m:
        raise ValueError(f"Unrecognised size: {value!r}")
    num, unit = float(m.group(1)), (m.group(2) or "B").upper()
    return int(num * _SIZE_UNITS[unit])


# ──────────────────────────────────────────────
# Time-based subfolder helper
# ──────────────────────────────────────────────
def time_subfolder(mode: str) -> str:
    """Return a relative subfolder path based on the current date."""
    now = datetime.now()
    modes = {
        "year":       now.strftime("%Y"),
        "year_month": now.strftime("%Y") + "/" + now.strftime("%B"),   # 2026/May
        "date":       now.strftime("%Y-%m-%d"),
        "today":      "Today",
        "week":       f"Week {now.strftime('%W')} – {now.strftime('%Y')}",
        "this_week":  "This Week",
    }
    if mode not in modes:
        raise ValueError(f"Unknown time_based mode: {mode!r}. "
                         f"Choose from: {list(modes)}")
    return modes[mode]


# ──────────────────────────────────────────────
# Rule dataclass
# ──────────────────────────────────────────────
@dataclass
class FileRule:
    folder: str
    extensions: set[str]              = field(default_factory=set)
    contains:   list[str]             = field(default_factory=list)
    size_gt:    Optional[int]         = None   # bytes
    size_lt:    Optional[int]         = None   # bytes
    time_based: Optional[str]         = None   # "year_month" | "year" | "date" | "today" | "week"
    description: str                  = ""

    # ── matching ────────────────────────────────
    def matches(self, path: Path) -> bool:
        """All specified criteria must pass (AND logic).
        Within `contains`, any match suffices (OR logic)."""
        suffix    = path.suffix.lower().lstrip(".")
        name_low  = path.name.lower()

        if self.extensions and suffix not in self.extensions:
            return False

        if self.contains and not any(c.lower() in name_low for c in self.contains):
            return False

        if self.size_gt is not None or self.size_lt is not None:
            try:
                sz = path.stat().st_size
            except OSError:
                return False
            if self.size_gt is not None and sz <= self.size_gt:
                return False
            if self.size_lt is not None and sz >= self.size_lt:
                return False

        # Rule must have at least one criterion
        return self._has_criteria()

    def _has_criteria(self) -> bool:
        return bool(
            self.extensions
            or self.contains
            or self.size_gt is not None
            or self.size_lt is not None
        )

    # ── destination folder (with optional time subfolder) ──
    def dest_subdir(self) -> str:
        if self.time_based:
            return self.folder + "/" + time_subfolder(self.time_based)
        return self.folder


# ──────────────────────────────────────────────
# Ignore patterns
# ──────────────────────────────────────────────
class IgnoreList:
    def __init__(self, patterns: list[str]) -> None:
        self.patterns = [p.lower() for p in patterns]

    def matches(self, path: Path) -> bool:
        name = path.name.lower()
        for pat in self.patterns:
            if fnmatch.fnmatch(name, pat):
                return True
            if name == pat:
                return True
        return False


# ──────────────────────────────────────────────
# Built-in defaults
# ──────────────────────────────────────────────
DEFAULT_RULES: list[dict[str, Any]] = [
    {"folder": "Images",      "extensions": ["jpg","jpeg","png","gif","bmp","webp","svg","ico","tiff","heic"], "time_based": "year_month"},
    {"folder": "Videos",      "extensions": ["mp4","mkv","avi","mov","wmv","flv","webm","m4v","mpeg"]},
    {"folder": "Audio",       "extensions": ["mp3","wav","flac","aac","ogg","m4a","wma","opus"]},
    {"folder": "Documents",   "extensions": ["pdf","doc","docx","xls","xlsx","ppt","pptx","odt","ods","odp"], "time_based": "year_month"},
    {"folder": "Text",        "extensions": ["txt","md","rst","csv","json","xml","yaml","yml","toml","ini","log"]},
    {"folder": "Archives",    "extensions": ["zip","tar","gz","bz2","xz","7z","rar","tgz"]},
    {"folder": "Code",        "extensions": ["py","js","ts","jsx","tsx","html","css","java","cpp","c","h","go","rs","rb","sh","bat","php"]},
    {"folder": "Executables", "extensions": ["exe","msi","dmg","pkg","deb","rpm","appimage"]},
    {"folder": "Fonts",       "extensions": ["ttf","otf","woff","woff2","eot"]},
    {"folder": "Ebooks",      "extensions": ["epub","mobi","azw","azw3","fb2"]},
]

DEFAULT_IGNORE = ["*.tmp", "*.crdownload", "*.part", ".DS_Store", "desktop.ini", "thumbs.db"]


# ──────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────
def _parse_rules(raw: list[dict]) -> list[FileRule]:
    rules = []
    for entry in raw:
        size_gt = parse_size(entry["size_gt"]) if "size_gt" in entry else None
        size_lt = parse_size(entry["size_lt"]) if "size_lt" in entry else None
        rule = FileRule(
            folder      = entry["folder"],
            extensions  = {e.lower().lstrip(".") for e in entry.get("extensions", [])},
            contains    = [c for c in entry.get("contains", [])],
            size_gt     = size_gt,
            size_lt     = size_lt,
            time_based  = entry.get("time_based"),
            description = entry.get("description", ""),
        )
        rules.append(rule)
    return rules


def load_config(config_path: Path) -> tuple[list[FileRule], IgnoreList]:
    if config_path.exists() and _HAS_YAML:
        try:
            with config_path.open() as f:
                data = yaml.safe_load(f)
            rules   = _parse_rules(data.get("rules", []))
            ignores = IgnoreList(data.get("ignore", DEFAULT_IGNORE))
            logger.info(f"Loaded {len(rules)} rules + ignore list from {config_path}")
            return rules, ignores
        except Exception as exc:
            logger.warning(f"Failed to load config ({exc}), using defaults")

    logger.info("Using built-in default rules")
    return _parse_rules(DEFAULT_RULES), IgnoreList(DEFAULT_IGNORE)
