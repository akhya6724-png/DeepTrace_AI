"""Shared helpers for analysis modules."""

import math

import numpy as np
from PIL import Image

STRENGTHS = ("informational", "weak", "moderate")


def make_finding(
    *,
    id: str,
    source: str,
    title: str,
    strength: str,
    observation: str,
    method: str,
    why_it_matters: str,
    alternative_explanations: list,
    additional_evidence_needed: list,
    evidence: dict | None = None,
) -> dict:
    """Build a finding. Every finding states what, how, why, alternatives and next evidence."""
    assert strength in STRENGTHS
    return {
        "id": id,
        "source": source,
        "title": title,
        "strength": strength,
        "observation": observation,
        "method": method,
        "why_it_matters": why_it_matters,
        "alternative_explanations": alternative_explanations,
        "additional_evidence_needed": additional_evidence_needed,
        "evidence": evidence or {},
    }


def to_rgb(image: Image.Image) -> Image.Image:
    """Convert any Pillow image to 8-bit RGB (alpha composited over white)."""
    if image.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
        arr = np.asarray(image, dtype=np.float64)
        top = arr.max() if arr.size else 0
        if top > 255:
            arr = arr / 256.0 if top <= 65535 else arr * (255.0 / top)
        gray = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")
        return gray.convert("RGB")
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")


def json_safe_float(value) -> float | None:
    """NaN/Infinity are not valid JSON, so map them to None."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None
