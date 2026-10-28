"""Feature A: upload validation.

We never trust the filename, extension or browser-supplied content type. The bytes are
opened with Pillow and the real format, size and decodability are checked.
"""

import hashlib
import io
import warnings
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.utils.file_utils import sanitize_filename

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ValidationError(Exception):
    """An upload was rejected. ``message`` is safe to show to the user."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class ValidatedImage:
    image: Image.Image
    raw_bytes: bytes
    properties: dict


def validate_image(
    raw_bytes: bytes,
    filename: str | None,
    max_bytes: int = 10 * 1024 * 1024,
    max_pixels: int = 25_000_000,
) -> ValidatedImage:
    if not raw_bytes:
        raise ValidationError("The uploaded file is empty.", 400)
    if len(raw_bytes) > max_bytes:
        raise ValidationError(
            f"File is too large. Maximum allowed size is {max_bytes / 1_048_576:.0f} MB.", 413
        )

    try:
        with warnings.catch_warnings():
            # Treat Pillow's decompression-bomb warning as an error.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            probe = Image.open(io.BytesIO(raw_bytes))
            fmt = probe.format
            width, height = probe.size
            if fmt not in ALLOWED_FORMATS:
                raise ValidationError(
                    f"Unsupported image format: {fmt}. Allowed formats: JPEG, PNG, WebP.", 415
                )
            # Check size from the header BEFORE decoding any pixels.
            if width <= 0 or height <= 0 or width * height > max_pixels:
                raise ValidationError(
                    f"Image is too large to process safely (limit {max_pixels / 1e6:.0f} megapixels).",
                    413,
                )
            probe.verify()  # integrity check; invalidates the object
            image = Image.open(io.BytesIO(raw_bytes))
            image.load()  # force full decode so corruption fails here
    except ValidationError:
        raise
    except UnidentifiedImageError:
        raise ValidationError("This file is not a recognizable image.", 415)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("Image dimensions are too large to process safely.", 413)
    except Exception:
        raise ValidationError("The image file appears to be corrupted or unreadable.", 422)

    properties = {
        "original_filename": sanitize_filename(filename),
        "format": fmt,
        "mime_type": MIME_TYPES[fmt],
        "width": width,
        "height": height,
        "megapixels": round(width * height / 1_000_000, 2),
        "color_mode": image.mode,
        "frame_count": int(getattr(image, "n_frames", 1) or 1),
        "file_size_bytes": len(raw_bytes),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
    }
    return ValidatedImage(image=image, raw_bytes=raw_bytes, properties=properties)
