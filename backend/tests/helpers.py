"""Synthetic test images. No downloads, no ground-truth claims about real photos."""

import io

import numpy as np
from PIL import Image, PngImagePlugin


def make_pixels(width=320, height=240, seed=1):
    rng = np.random.default_rng(seed)
    base = np.linspace(0, 255, width * height).reshape(height, width)[:, :, None] * np.array([1.0, 0.8, 0.6])
    noise = rng.normal(0, 6, (height, width, 3))
    return Image.fromarray((base + noise).clip(0, 255).astype("uint8"))


def jpeg_bytes(width=320, height=240, quality=85, exif=None, seed=1) -> bytes:
    buf = io.BytesIO()
    kwargs = {"quality": quality}
    if exif is not None:
        kwargs["exif"] = exif
    make_pixels(width, height, seed).save(buf, "JPEG", **kwargs)
    return buf.getvalue()


def png_bytes(width=200, height=150, text=None) -> bytes:
    buf = io.BytesIO()
    info = None
    if text:
        info = PngImagePlugin.PngInfo()
        for k, v in text.items():
            info.add_text(k, v)
    make_pixels(width, height).save(buf, "PNG", pnginfo=info)
    return buf.getvalue()


def webp_bytes(width=200, height=150) -> bytes:
    buf = io.BytesIO()
    make_pixels(width, height).save(buf, "WEBP")
    return buf.getvalue()


def gif_bytes() -> bytes:
    buf = io.BytesIO()
    make_pixels(40, 40).convert("P").save(buf, "GIF")
    return buf.getvalue()


def exif_with_edit_info():
    ex = Image.Exif()
    ex[0x010F] = "TestCam"
    ex[0x0110] = "X1"
    ex[0x0131] = "Adobe Photoshop 25.0"
    ex[0x0132] = "2024:01:01 10:30:00"       # DateTime (modified)
    ex[0x013B] = "Jane Doe"                  # Artist (personal data)
    ex.get_ifd(0x8769)[0x9003] = "2024:01:01 10:00:00"  # DateTimeOriginal
    return ex


def jpeg_with_c2pa_marker() -> bytes:
    """A JPEG with a fake APP11 JUMBF segment labelled c2pa. Structure only; not a real manifest."""
    data = jpeg_bytes()
    payload = b"JP\x00\x00" + b"\x00\x00\x00\x20jumb\x00\x00\x00\x18jumdc2pa\x00" + b"x" * 8
    segment = b"\xff\xeb" + (len(payload) + 2).to_bytes(2, "big") + payload
    return data[:2] + segment + data[2:]
