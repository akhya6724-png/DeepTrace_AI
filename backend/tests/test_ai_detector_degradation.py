"""The API must start and report honestly when the ONNX model or runtime is unavailable."""
import builtins
from pathlib import Path

from PIL import Image

from app.analysis import ai_detection
from app.analysis.ai_detection import detector_ready, run_ai_detection


def test_missing_model_file_is_unavailable_not_error(monkeypatch):
    ai_detection._load_session.cache_clear()
    monkeypatch.setattr(ai_detection, "MODEL_PATH", Path("does/not/exist.onnx"))
    r = run_ai_detection(Image.new("RGB", (64, 64)), "onnx")
    assert r["status"] == "unavailable"
    assert r["prediction"] is None and r["confidence"] is None
    assert "not performed" in r["explanation"].lower()
    assert detector_ready() is False


def test_missing_runtime_is_unavailable_not_crash(monkeypatch):
    ai_detection._load_session.cache_clear()
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "onnxruntime":
            raise ImportError("simulated: onnxruntime not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    r = run_ai_detection(Image.new("RGB", (64, 64)), "onnx")
    assert r["status"] == "unavailable"
    assert "onnxruntime" in r["explanation"].lower()
    assert r["confidence"] is None
    assert detector_ready() is False


def test_module_imports_without_onnxruntime():
    # The module must not import onnxruntime at import time.
    source = Path(ai_detection.__file__).read_text(encoding="utf-8")
    top_level = [ln for ln in source.splitlines() if ln.startswith(("import ", "from "))]
    assert not any("onnxruntime" in ln for ln in top_level)
