from app.analysis.metadata import extract_metadata
from app.analysis.validation import validate_image
from tests.helpers import exif_with_edit_info, jpeg_bytes, png_bytes


def _meta(data):
    v = validate_image(data, "t")
    return extract_metadata(v.image, v.raw_bytes)


def _ids(meta):
    return {f["id"] for f in meta["findings"]}


def test_exif_fields_and_findings():
    m = _meta(jpeg_bytes(exif=exif_with_edit_info()))
    assert m["exif_present"] and m["summary"]["camera_make"] == "TestCam"
    assert {"camera_info", "editing_software_recorded", "timestamp_gap"} <= _ids(m)
    assert m["summary"]["timestamps"]["DateTimeOriginal"] == "2024-01-01T10:00:00"


def test_personal_fields_are_redacted():
    m = _meta(jpeg_bytes(exif=exif_with_edit_info()))
    assert "Jane Doe" not in str(m)


def test_missing_exif_is_informational_only():
    m = _meta(png_bytes())
    assert not m["exif_present"] and "exif_absent" in _ids(m)
    f = next(f for f in m["findings"] if f["id"] == "exif_absent")
    assert f["strength"] == "informational"
    assert any("strip" in a.lower() for a in f["alternative_explanations"])


def test_ai_text_trace_detected():
    m = _meta(png_bytes(text={"parameters": "a cat\nSteps: 20, Sampler: Euler a, Seed: 1"}))
    assert "ai_tool_trace" in _ids(m)


def test_output_is_json_serialisable():
    import json
    json.dumps(_meta(jpeg_bytes(exif=exif_with_edit_info())))
