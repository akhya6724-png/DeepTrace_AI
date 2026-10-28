import pytest

from app.analysis.validation import ValidationError, validate_image
from tests.helpers import gif_bytes, jpeg_bytes, png_bytes, webp_bytes

@pytest.mark.parametrize(
    "data,fmt",
    [
        (jpeg_bytes(), "JPEG"),
        (png_bytes(), "PNG"),
        (webp_bytes(), "WEBP"),
    ],
    ids=["jpeg", "png", "webp"],
)
def test_valid_formats(data, fmt):
    v = validate_image(data, "x.bin")
    assert v.properties["format"] == fmt
    assert len(v.properties["sha256"]) == 64


def test_empty_file():
    with pytest.raises(ValidationError) as e:
        validate_image(b"", "a.jpg")
    assert e.value.status_code == 400


def test_text_renamed_as_image():
    with pytest.raises(ValidationError) as e:
        validate_image(b"this is just text, not an image", "photo.jpg")
    assert e.value.status_code == 415


def test_unsupported_format_gif():
    with pytest.raises(ValidationError) as e:
        validate_image(gif_bytes(), "a.gif")
    assert e.value.status_code == 415


def test_corrupted_image():
    data = jpeg_bytes()
    with pytest.raises(ValidationError) as e:
        validate_image(data[: len(data) // 2], "a.jpg")
    assert e.value.status_code == 422


def test_oversized_file():
    with pytest.raises(ValidationError) as e:
        validate_image(jpeg_bytes(), "a.jpg", max_bytes=1000)
    assert e.value.status_code == 413


def test_too_many_pixels():
    with pytest.raises(ValidationError) as e:
        validate_image(png_bytes(300, 300), "a.png", max_pixels=10_000)
    assert e.value.status_code == 413


def test_filename_is_sanitised():
    v = validate_image(jpeg_bytes(), "..\\..\\etc/passwd\x00.jpg")
    assert "/" not in v.properties["original_filename"] and "\\" not in v.properties["original_filename"]
