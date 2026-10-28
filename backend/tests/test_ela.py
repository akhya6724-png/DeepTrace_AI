import numpy as np
from PIL import Image

from app.analysis.ela import run_ela
from app.analysis.validation import validate_image
from tests.helpers import jpeg_bytes, png_bytes


def test_ela_output_shape_and_fields():
    v = validate_image(jpeg_bytes(), "a.jpg")
    result, img = run_ela(v.image, 90, "JPEG")
    assert result["status"] == "ok" and result["jpeg_quality"] == 90
    assert img.size == v.image.size and img.mode == "RGB"
    assert result["limitations"] and result["explanation"]
    for key in ("mean", "std", "median", "p95", "p99"):
        assert key in result["difference_statistics"]


def test_ela_is_deterministic():
    v = validate_image(jpeg_bytes(), "a.jpg")
    r1, i1 = run_ela(v.image, 90, "JPEG")
    r2, i2 = run_ela(v.image, 90, "JPEG")
    assert r1["difference_statistics"] == r2["difference_statistics"]
    assert np.array_equal(np.asarray(i1), np.asarray(i2))


def test_ela_png_is_flagged_as_cautious():
    v = validate_image(png_bytes(), "a.png")
    result, _ = run_ela(v.image, 90, "PNG")
    assert "caution" in result["interpretability"].lower()


def test_ela_handles_transparency():
    rgba = Image.new("RGBA", (64, 64), (10, 200, 30, 128))
    result, img = run_ela(rgba, 90, "PNG")
    assert result["status"] == "ok" and img.size == (64, 64)


def test_ela_makes_no_tamper_claim():
    v = validate_image(jpeg_bytes(), "a.jpg")
    result, _ = run_ela(v.image, 90, "JPEG")
    assert all(f["strength"] == "informational" for f in result["findings"])
