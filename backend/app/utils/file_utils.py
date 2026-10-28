"""Safe helpers for IDs, filenames and storage paths."""

import os
import re
import shutil
import uuid
from pathlib import Path

ANALYSIS_ID_RE = re.compile(r"^[0-9a-f]{32}$")
EVIDENCE_NAME_RE = re.compile(r"^[a-z0-9_]{1,40}\.(png|jpg)$")


def new_analysis_id() -> str:
    return uuid.uuid4().hex


def is_valid_analysis_id(value) -> bool:
    return isinstance(value, str) and bool(ANALYSIS_ID_RE.match(value))


def is_valid_evidence_name(value) -> bool:
    return isinstance(value, str) and bool(EVIDENCE_NAME_RE.match(value))


def sanitize_filename(name: str | None) -> str:
    """Display-only filename: no directories, no control characters, max 100 chars."""
    if not name:
        return "unknown"
    base = os.path.basename(str(name).replace("\\", "/"))
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return base[:100] or "unknown"


def safe_join(base: Path, *parts: str) -> Path:
    """Join and resolve a path, refusing anything that escapes ``base``."""
    base_resolved = base.resolve()
    candidate = base_resolved.joinpath(*parts).resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        raise ValueError("Path escapes the storage directory.")
    return candidate


def remove_directory(base: Path, name: str) -> None:
    """Delete ``base/name`` (a directory) only if it really lives inside ``base``."""
    target = safe_join(base, name)
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)


def remove_file(base: Path, name: str) -> None:
    """Delete ``base/name`` (a file) only if it really lives inside ``base``."""
    target = safe_join(base, name)
    if target.is_file():
        try:
            target.unlink()
        except OSError:
            pass
