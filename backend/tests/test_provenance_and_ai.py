from app.analysis.ai_detection import run_ai_detection
from app.analysis.provenance import inspect_provenance
from tests.helpers import jpeg_bytes, jpeg_with_c2pa_marker, png_bytes, webp_bytes
from PIL import Image


def test_ai_detector_unavailable_by_default():
    r = run_ai_detection(Image.new("RGB", (8, 8)), "none")
    assert r["status"] == "unavailable" and r["prediction"] is None and r["confidence"] is None


def test_unknown_detector_is_unavailable_not_fabricated():
    r = run_ai_detection(Image.new("RGB", (8, 8)), "does-not-exist")
    assert r["status"] == "unavailable" and r["prediction"] is None


def test_no_credentials():
    for data, fmt in ((jpeg_bytes(), "JPEG"), (png_bytes(), "PNG"), (webp_bytes(), "WEBP")):
        r = inspect_provenance(data, fmt)
        assert r["status"] == "no_credentials_detected" and r["credentials_detected"] is False


def test_credentials_detected_but_never_verified():
    r = inspect_provenance(jpeg_with_c2pa_marker(), "JPEG")
    assert r["status"] == "credentials_detected_unverified"
    assert r["verification"] == "not_performed"
