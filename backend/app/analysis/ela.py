"""Feature C: Error Level Analysis (ELA).

ELA re-saves the image as JPEG at a fixed quality and shows how much each pixel changes.
It is a VISUAL AID for a human examiner. No automatic threshold is applied, because no
validated threshold exists: edges, texture, text and recompression all produce bright
areas in unmanipulated images.
"""

import io

import numpy as np
from PIL import Image

from app.analysis.common import json_safe_float, make_finding, to_rgb

BLOCK_SIZE = 16

LIMITATIONS = [
    "Bright areas do NOT prove tampering: sharp edges, fine texture, text, overlays and resizing all raise error levels.",
    "A dark or uniform ELA image does NOT prove authenticity: heavy recompression, resizing or a re-saved edit can hide differences.",
    "ELA is most meaningful for images that were last saved as JPEG; for PNG/WebP the JPEG round-trip changes the representation.",
    "Results depend strongly on the chosen JPEG quality and on any earlier compression the image has been through.",
    "No automatic suspicious-region detection is performed. Highlighting regions would require a validated method.",
]


def run_ela(image: Image.Image, quality: int, source_format: str) -> tuple[dict, Image.Image]:
    rgb = to_rgb(image)

    buffer = io.BytesIO()
    rgb.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as re_encoded:
        recompressed = re_encoded.convert("RGB")
        recompressed.load()

    diff = np.abs(
        np.asarray(rgb, dtype=np.int16) - np.asarray(recompressed, dtype=np.int16)
    ).astype(np.uint8)
    magnitude = diff.mean(axis=2, dtype=np.float32)  # per-pixel mean over R, G, B

    stats = {
        "mean": json_safe_float(round(float(magnitude.mean()), 4)),
        "std": json_safe_float(round(float(magnitude.std()), 4)),
        "median": json_safe_float(round(float(np.median(magnitude)), 4)),
        "p95": json_safe_float(round(float(np.percentile(magnitude, 95)), 4)),
        "p99": json_safe_float(round(float(np.percentile(magnitude, 99)), 4)),
        "max_channel_difference": int(diff.max()),
        "share_of_pixels_with_mean_difference_ge_8": json_safe_float(
            round(float((magnitude >= 8).mean()), 6)
        ),
        "scale": "0-255 pixel-value units (mean absolute difference across R, G, B)",
    }

    block_stats = None
    h, w = magnitude.shape
    hb, wb = h // BLOCK_SIZE, w // BLOCK_SIZE
    if hb * wb >= 16:
        blocks = magnitude[: hb * BLOCK_SIZE, : wb * BLOCK_SIZE].reshape(
            hb, BLOCK_SIZE, wb, BLOCK_SIZE
        ).mean(axis=(1, 3))
        median = float(np.median(blocks))
        p95 = float(np.percentile(blocks, 95))
        block_stats = {
            "block_size_px": BLOCK_SIZE,
            "block_count": int(hb * wb),
            "block_mean_median": round(median, 4),
            "block_mean_p95": round(p95, 4),
            "block_mean_max": round(float(blocks.max()), 4),
            "p95_to_median_ratio": json_safe_float(round(p95 / max(median, 0.01), 3)),
            "note": "Descriptive only. No threshold is applied to these numbers.",
        }

    # Scale for visibility. 99.5th percentile avoids one hot pixel flattening the picture.
    reference = max(float(np.percentile(magnitude, 99.5)), 1.0)
    factor = min(255.0 / reference, 255.0)
    visual = np.clip(diff.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    evidence_image = Image.fromarray(visual, "RGB")

    is_jpeg = source_format == "JPEG"
    interpretability = (
        "Source is JPEG: ELA is applicable, but interpretation still requires expert judgement."
        if is_jpeg
        else f"Source is {source_format}, not JPEG: the JPEG round-trip changes the representation, "
        "so ELA output must be interpreted with extra caution."
    )

    result = {
        "status": "ok",
        "method": "jpeg_recompression_difference",
        "jpeg_quality": quality,
        "source_format": source_format,
        "interpretability": interpretability,
        "difference_statistics": stats,
        "block_statistics": block_stats,
        "visualization": {
            "amplification_factor": round(factor, 2),
            "scaling": "Differences multiplied by the amplification factor and clipped to 255.",
        },
        "evidence_url": None,
        "explanation": (
            f"The image was re-encoded as JPEG at quality {quality} and compared pixel by pixel with the "
            "original. The evidence image shows the amplified absolute difference. Regions that change more "
            "than their surroundings may have a different compression history, but many ordinary causes exist."
        ),
        "limitations": LIMITATIONS,
        "findings": [
            make_finding(
                id="ela_visualization", source="ela",
                title="ELA visualization generated for manual review", strength="informational",
                observation=f"Mean recompression difference is {stats['mean']} (0-255 scale); 99th percentile {stats['p99']}.",
                method=f"JPEG re-encode at quality {quality}, absolute difference, amplification x{round(factor, 2)}.",
                why_it_matters="Large, sharply bounded areas with a different error level than similar nearby content can prompt closer examination.",
                alternative_explanations=[
                    "Edges, texture, text and logos naturally show higher error levels.",
                    "Differences in earlier compression or resizing can create the same pattern.",
                ],
                additional_evidence_needed=["Other methods (noise analysis, clone detection), the original file, source verification."],
                evidence={"mean": stats["mean"], "p99": stats["p99"]},
            )
        ],
    }
    return result, evidence_image
