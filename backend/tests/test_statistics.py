import json

from app.analysis.image_statistics import compute_statistics, estimate_jpeg_quality
from app.analysis.validation import validate_image
from tests.helpers import jpeg_bytes, png_bytes


def test_statistics_fields_and_determinism():
    v = validate_image(jpeg_bytes(), "a.jpg")
    a = compute_statistics(v.image, "JPEG")
    b = compute_statistics(v.image, "JPEG")
    assert a == b
    names = {i["name"] for i in a}
    assert {"channel_statistics", "sharpness_laplacian_variance", "noise_estimate_sigma", "jpeg_quantization"} <= names
    for i in a:
        assert i["method"] and i["explanation"] and i["limitations"]
    json.dumps(a)


def test_jpeg_quality_estimate_matches_encoder():
    v = validate_image(jpeg_bytes(quality=75), "a.jpg")
    q = next(i for i in compute_statistics(v.image, "JPEG") if i["name"] == "jpeg_quantization")
    assert q["value"]["closest_standard_quality"] == 75 and q["value"]["exact_match_to_standard_table"]


def test_png_has_no_jpeg_indicator():
    v = validate_image(png_bytes(), "a.png")
    assert "jpeg_quantization" not in {i["name"] for i in compute_statistics(v.image, "PNG")}


def test_estimate_quality_roundtrip():
    from app.analysis.image_statistics import _scaled_table
    assert estimate_jpeg_quality(_scaled_table(30)) == (30, True)
