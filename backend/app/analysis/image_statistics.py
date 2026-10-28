"""Measurable, deterministic image indicators.

These are descriptive measurements. None of them is a tamper detector on its own.
"""

import cv2
import numpy as np
from PIL import Image

from app.analysis.common import json_safe_float, to_rgb

# Standard libjpeg luminance quantization table (quality 50), natural (row-major) order.
STD_LUMA = [
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99,
]


def _indicator(name, value, method, explanation, limitations):
    return {"name": name, "value": value, "method": method,
            "explanation": explanation, "limitations": limitations}


def _scaled_table(quality: int) -> list:
    scale = 5000 // quality if quality < 50 else 200 - 2 * quality
    return [min(max((t * scale + 50) // 100, 1), 255) for t in STD_LUMA]


def estimate_jpeg_quality(table: list) -> tuple[int, bool]:
    """Closest libjpeg-standard quality for a luminance table, and whether it matches exactly."""
    best_q, best_dist = 1, None
    for q in range(1, 101):
        dist = sum(abs(a - b) for a, b in zip(_scaled_table(q), table))
        if best_dist is None or dist < best_dist:
            best_q, best_dist = q, dist
    return best_q, best_dist == 0


def compute_statistics(image: Image.Image, source_format: str) -> list:
    rgb = to_rgb(image)
    arr = np.asarray(rgb)
    height, width = arr.shape[:2]
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    indicators = []

    indicators.append(_indicator(
        "dimensions_and_aspect_ratio",
        {"width": width, "height": height, "aspect_ratio": round(width / height, 4),
         "megapixels": round(width * height / 1e6, 3)},
        "Read decoded pixel dimensions.",
        "Basic geometry. Unusual sizes can hint at cropping or platform resizing.",
        ["Many legitimate workflows crop or resize images. Dimensions alone prove nothing."],
    ))

    channels = {}
    for i, name in enumerate(("red", "green", "blue")):
        ch = arr[:, :, i].astype(np.float64)
        channels[name] = {"mean": round(float(ch.mean()), 3), "std": round(float(ch.std()), 3)}
    channels["luminance"] = {"mean": round(float(gray.mean()), 3), "std": round(float(gray.std()), 3)}
    indicators.append(_indicator(
        "channel_statistics", channels,
        "Mean and standard deviation of 8-bit pixel values per channel.",
        "Describes overall brightness, colour balance and contrast.",
        ["Depends on image content and camera or editing settings; not a manipulation test."],
    ))

    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    p = hist / hist.sum()
    nz = p[p > 0]
    entropy = float(-(nz * np.log2(nz)).sum())
    indicators.append(_indicator(
        "luminance_histogram",
        {"entropy_bits": round(entropy, 3),
         "share_pure_black": round(float(p[0]), 5), "share_pure_white": round(float(p[255]), 5)},
        "Histogram of 8-bit luminance; Shannon entropy and share of clipped values.",
        "Entropy summarises tonal variety. Large clipped shares indicate blown highlights or crushed shadows.",
        ["Graphics, screenshots and night photos legitimately have unusual histograms."],
    ))

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    indicators.append(_indicator(
        "sharpness_laplacian_variance", json_safe_float(round(lap_var, 3)),
        "Variance of the Laplacian of the luminance image.",
        "Higher values mean more fine detail and edges. Very low values indicate a smooth or blurred image.",
        ["Depends on scene content and resolution; cannot be compared across different images."],
    ))

    if height >= 3 and width >= 3:
        kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float64)
        response = cv2.filter2D(gray.astype(np.float64), -1, kernel, borderType=cv2.BORDER_REFLECT)
        inner = response[1:-1, 1:-1]
        sigma = float(np.sqrt(np.pi / 2.0) / 6.0 * np.abs(inner).mean())
        indicators.append(_indicator(
            "noise_estimate_sigma", json_safe_float(round(sigma, 4)),
            "Immerkaer fast noise-variance estimator on the luminance image.",
            "Estimated standard deviation of image noise (0-255 units). Compare with similar images from the same source.",
            ["Textured regions inflate the estimate, and denoising, compression and resizing lower it.",
             "A single global value cannot show local noise inconsistencies."],
        ))

    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        alpha = np.asarray(image.convert("RGBA"))[:, :, 3]
        indicators.append(_indicator(
            "transparency", {"share_not_fully_opaque": round(float((alpha < 255).mean()), 5)},
            "Share of pixels whose alpha is below 255.",
            "The image has a transparency channel; analyses composite it over white.",
            ["Transparency is normal for logos, stickers and cut-outs."],
        ))

    if source_format == "JPEG":
        tables = getattr(image, "quantization", None) or {}
        if tables:
            luma = list(tables.get(0, []))
            value = {"table_count": len(tables)}
            if len(luma) == 64:
                quality, exact = estimate_jpeg_quality(luma)
                value.update({"closest_standard_quality": quality, "exact_match_to_standard_table": exact})
            indicators.append(_indicator(
                "jpeg_quantization", value,
                "Read the embedded quantization tables and compare the luminance table with libjpeg's standard scaling.",
                "Shows the compression strength used when the file was last saved. An exact match suggests a libjpeg-style encoder; "
                "a non-match suggests custom tables (common for cameras and some editors).",
                ["Cannot reveal earlier compression generations or what was edited.",
                 "Two different programs can produce identical tables."],
            ))

    return indicators
