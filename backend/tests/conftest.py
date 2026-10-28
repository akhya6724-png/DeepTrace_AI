import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
# app.main creates a default app at import time; keep that out of the real storage folder.
os.environ.setdefault("DEEPTRACE_STORAGE_DIR", tempfile.mkdtemp(prefix="deeptrace_import_"))
os.environ.setdefault("DEEPTRACE_LOAD_DOTENV", "0")

from app.config import Settings  # noqa: E402
from app.database import AnalysisRepository  # noqa: E402
from app.services.analysis_service import AnalysisService  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    return Settings(storage_dir=tmp_path / "storage", max_upload_bytes=2 * 1024 * 1024,
                    max_pixels=4_000_000, retention_days=0)


@pytest.fixture
def service(settings):
    repo = AnalysisRepository(settings.db_path)
    svc = AnalysisService(settings, repo)
    svc.ensure_storage()
    repo.init()
    return svc


@pytest.fixture
def client(settings):
    from fastapi.testclient import TestClient
    from app.main import create_app

    with TestClient(create_app(settings)) as test_client:
        yield test_client
