"""SQLite persistence for analysis history (standard library only, parameterized SQL)."""

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("deeptrace.database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    assessment_category TEXT,
    image_summary TEXT NOT NULL,
    result_json TEXT NOT NULL,
    report_file TEXT
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses (created_at);
"""


class StoredDataError(Exception):
    """A stored row could not be decoded."""


class AnalysisRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create(self) -> None:
        with self._conn() as conn:
            row = conn.execute("PRAGMA quick_check").fetchone()
            if row is None or row[0] != "ok":
                raise sqlite3.DatabaseError("database failed integrity check")
            conn.executescript(SCHEMA)

    def init(self) -> None:
        """Create tables. A corrupt database file is set aside and a fresh one is created."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._create()
        except sqlite3.DatabaseError:
            backup = self.db_path.with_name(f"{self.db_path.name}.corrupt-{int(time.time())}")
            logger.error("Database unreadable; moving it aside to %s", backup.name)
            self.db_path.replace(backup)
            self._create()

    def ping(self) -> bool:
        try:
            with self._conn() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def save(self, result: dict, report_file: str | None) -> None:
        info = result.get("image_info") or {}
        summary = {k: info.get(k) for k in
                   ("original_filename", "format", "width", "height", "file_size_bytes", "sha256")}
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO analyses (id, created_at, status, assessment_category, image_summary, result_json, report_file) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (result["analysis_id"], result["created_at"], result["status"],
                 (result.get("overall_assessment") or {}).get("category"),
                 json.dumps(summary), json.dumps(result), report_file),
            )

    def get(self, analysis_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT result_json FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["result_json"])
        except (TypeError, ValueError) as exc:
            raise StoredDataError("Stored analysis is corrupted.") from exc

    def list(self, limit: int, offset: int) -> tuple[list, int]:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
            rows = conn.execute(
                "SELECT id, created_at, status, assessment_category, image_summary, report_file "
                "FROM analyses ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        items = []
        for row in rows:
            try:
                summary = json.loads(row["image_summary"])
            except (TypeError, ValueError):
                summary = {}
            items.append({
                "analysis_id": row["id"],
                "created_at": row["created_at"],
                "status": row["status"],
                "assessment_category": row["assessment_category"],
                "original_filename": summary.get("original_filename"),
                "format": summary.get("format"),
                "width": summary.get("width"),
                "height": summary.get("height"),
                "report_url": f"/api/v1/analyses/{row['id']}/report" if row["report_file"] else None,
            })
        return items, total

    def delete(self, analysis_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
            return cur.rowcount > 0

    def ids_older_than(self, cutoff_iso: str) -> list:
        with self._conn() as conn:
            rows = conn.execute("SELECT id FROM analyses WHERE created_at < ?", (cutoff_iso,)).fetchall()
        return [r["id"] for r in rows]
