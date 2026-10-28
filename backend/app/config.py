"""Application configuration.

Values come from environment variables (prefix ``DEEPTRACE_``). A ``.env`` file in the
backend folder is read if present. Nothing here is secret; no API keys are needed.
"""

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "DeepTrace AI"
APP_VERSION = "1.0.0"
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader (KEY=VALUE lines). Existing environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(int(raw), minimum)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    storage_dir: Path = BACKEND_DIR / "storage"
    database_path: Path | None = None
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 25_000_000
    ela_quality: int = 90
    cors_origins: tuple = ("http://localhost:5173", "http://127.0.0.1:5173")
    retention_days: int = 30          # 0 disables automatic cleanup
    include_gps_values: bool = False  # GPS coordinates are redacted unless enabled
    store_preview: bool = True        # keep a downscaled preview for the PDF report
    ai_detector: str = "none"

    @property
    def db_path(self) -> Path:
        return self.database_path or (self.storage_dir / "deeptrace.db")

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def evidence_dir(self) -> Path:
        return self.storage_dir / "evidence"

    @property
    def reports_dir(self) -> Path:
        return self.storage_dir / "reports"

    @classmethod
    def from_env(cls) -> "Settings":
        if os.environ.get("DEEPTRACE_LOAD_DOTENV", "1") != "0":
            _load_dotenv(BACKEND_DIR / ".env")
        storage = Path(os.environ.get("DEEPTRACE_STORAGE_DIR") or (BACKEND_DIR / "storage"))
        if not storage.is_absolute():
            storage = BACKEND_DIR / storage
        db = os.environ.get("DEEPTRACE_DATABASE_PATH")
        origins_raw = os.environ.get("DEEPTRACE_CORS_ORIGINS")
        origins = (
            tuple(o.strip() for o in origins_raw.split(",") if o.strip())
            if origins_raw is not None
            else cls.cors_origins
        )
        return cls(
            storage_dir=storage,
            database_path=Path(db) if db else None,
            max_upload_bytes=_env_int("DEEPTRACE_MAX_UPLOAD_MB", 10) * 1024 * 1024,
            max_pixels=_env_int("DEEPTRACE_MAX_PIXELS", 25_000_000, 1000),
            ela_quality=min(_env_int("DEEPTRACE_ELA_QUALITY", 90), 100),
            cors_origins=origins,
            retention_days=_env_int("DEEPTRACE_RETENTION_DAYS", 30, 0),
            include_gps_values=_env_bool("DEEPTRACE_INCLUDE_GPS_VALUES", False),
            store_preview=_env_bool("DEEPTRACE_STORE_PREVIEW", True),
            ai_detector=os.environ.get("DEEPTRACE_AI_DETECTOR", "none").strip().lower() or "none",
        )
