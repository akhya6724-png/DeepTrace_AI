"""Feature B: metadata and file inspection.

Everything here is an OBSERVATION about the file. Metadata can be removed, edited or
fabricated, so nothing in this module proves manipulation or authenticity. Missing
metadata is common (messaging apps, social media and screenshots strip it).
"""

import re
from datetime import datetime

from PIL import ExifTags, Image

from app.analysis.common import json_safe_float, make_finding

EXIF_IFD = 0x8769
GPS_IFD = 0x8825

EDITING_SOFTWARE_KEYWORDS = [
    "photoshop", "lightroom", "gimp", "affinity", "paint.net", "pixlr", "snapseed",
    "canva", "picsart", "facetune", "capture one", "luminar", "darktable", "photopea",
]
AI_TOOL_KEYWORDS = [
    "stable diffusion", "midjourney", "dall-e", "dall·e", "firefly", "comfyui",
    "automatic1111", "novelai", "leonardo.ai", "imagen",
]
# Tags dropped entirely (binary blobs / internal pointers).
DROPPED_TAGS = {"MakerNote", "GPSInfo", "ExifOffset", "InteroperabilityIFDPointer"}
# Tags that identify people or specific devices: reported as present, value withheld.
SENSITIVE_TAGS = {
    "Artist", "Copyright", "CameraOwnerName", "OwnerName", "XPAuthor",
    "BodySerialNumber", "LensSerialNumber", "SerialNumber", "ImageUniqueID",
}
ORIENTATION_NAMES = {
    1: "Normal", 2: "Mirrored horizontally", 3: "Rotated 180", 4: "Mirrored vertically",
    5: "Mirrored + rotated 90 CW", 6: "Rotated 90 CW", 7: "Mirrored + rotated 270 CW",
    8: "Rotated 270 CW",
}
TIMESTAMP_GAP_SECONDS = 60


def _clean(value):
    """Convert EXIF values into JSON-safe, readable values."""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="ignore").strip("\x00 ")
        printable = text.isprintable() and text
        return text[:200] if printable else f"<{len(value)} bytes>"
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value][:20]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value[:200]
    if isinstance(value, float):
        return json_safe_float(value)
    try:
        return json_safe_float(float(value))  # Pillow IFDRational
    except (TypeError, ValueError):
        return str(value)[:200]


def _named(ifd) -> dict:
    out = {}
    for tag, val in ifd.items():
        name = ExifTags.TAGS.get(tag, f"Tag_{tag}")
        if name in DROPPED_TAGS:
            continue
        out[name] = "[redacted: personal or device identifier]" if name in SENSITIVE_TAGS else _clean(val)
    return out


def _parse_exif_date(text):
    try:
        return datetime.strptime(str(text).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def _extract_xmp(raw: bytes) -> str | None:
    start = raw.find(b"<x:xmpmeta")
    if start < 0:
        return None
    end = raw.find(b"</x:xmpmeta>", start)
    end = end + len(b"</x:xmpmeta>") if end > 0 else start + 65536
    return raw[start:min(end, start + 1_000_000)].decode("utf-8", errors="ignore")


def extract_metadata(image: Image.Image, raw_bytes: bytes, include_gps_values: bool = False) -> dict:
    exif = image.getexif()
    exif_main = _named(exif)
    exif_sub, gps_raw = {}, {}
    try:
        exif_sub = _named(exif.get_ifd(EXIF_IFD))
    except Exception:
        pass
    try:
        gps_raw = {
            ExifTags.GPSTAGS.get(t, f"GPS_{t}"): _clean(v)
            for t, v in exif.get_ifd(GPS_IFD).items()
        }
    except Exception:
        pass
    exif_all = {**exif_main, **exif_sub}

    container_info = {}
    for key, val in image.info.items():
        if key in ("exif", "icc_profile", "xmp", "XML:com.adobe.xmp"):
            continue
        container_info[str(key)] = _clean(val)

    xmp = _extract_xmp(raw_bytes)
    xmp_creator_tool = None
    if xmp:
        m = re.search(r'CreatorTool(?:>|=")([^<"]{1,200})', xmp)
        xmp_creator_tool = m.group(1).strip() if m else None
    flags = {"has_exif": bool(exif_all), "has_xmp": xmp is not None,
             "has_icc_profile": "icc_profile" in image.info}

    # ---- summary -----------------------------------------------------------------
    timestamps = {}
    for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        parsed = _parse_exif_date(exif_all.get(key))
        if parsed:
            timestamps[key] = parsed.isoformat()
    orientation = exif_all.get("Orientation")
    summary = {
        "camera_make": exif_all.get("Make"),
        "camera_model": exif_all.get("Model"),
        "software": exif_all.get("Software"),
        "xmp_creator_tool": xmp_creator_tool,
        "orientation": orientation,
        "orientation_description": ORIENTATION_NAMES.get(orientation) if isinstance(orientation, int) else None,
        "timestamps": timestamps,
    }
    gps = {"present": bool(gps_raw), "fields": sorted(gps_raw.keys()),
           "values_included": bool(include_gps_values and gps_raw)}
    if include_gps_values and gps_raw:
        gps["values"] = gps_raw

    # ---- findings ----------------------------------------------------------------
    findings = []

    if not exif_all:
        findings.append(make_finding(
            id="exif_absent", source="metadata", title="No EXIF metadata found",
            strength="informational",
            observation="The file contains no readable EXIF metadata.",
            method="Parsed EXIF with Pillow (main IFD and Exif sub-IFD).",
            why_it_matters="Without EXIF there is no capture-device or timestamp information to cross-check.",
            alternative_explanations=[
                "Messaging apps, social networks, screenshots and export tools routinely strip EXIF.",
                "The original file may never have had EXIF (for example, a generated graphic).",
            ],
            additional_evidence_needed=["The original file from the source, ideally with its metadata intact."],
            evidence={"exif_fields_found": 0},
        ))
    elif exif_all.get("Make") or exif_all.get("Model"):
        camera = " ".join(str(exif_all[k]) for k in ("Make", "Model") if exif_all.get(k))
        findings.append(make_finding(
            id="camera_info", source="metadata", title="Camera information declared",
            strength="informational",
            observation=f"The file declares a capture device: {camera}.",
            method="Read the EXIF Make and Model fields.",
            why_it_matters="Declared device data can be compared with other claims about where the image came from.",
            alternative_explanations=["These fields can be edited or copied from another image."],
            additional_evidence_needed=["Independent confirmation of the device or the original file."],
            evidence={"Make": exif_all.get("Make"), "Model": exif_all.get("Model")},
        ))

    software_values = [s for s in (exif_all.get("Software"), xmp_creator_tool) if s]
    for software in dict.fromkeys(str(s) for s in software_values):
        edited = any(k in software.lower() for k in EDITING_SOFTWARE_KEYWORDS)
        findings.append(make_finding(
            id="editing_software_recorded" if edited else "software_tag_present",
            source="metadata",
            title="Image-editing software recorded" if edited else "Software tag present",
            strength="weak" if edited else "informational",
            observation=f"The metadata names the software '{software}'.",
            method="Read the EXIF Software field and the XMP CreatorTool, matched against a keyword list.",
            why_it_matters="It shows the file was last saved by that program, so edits are possible.",
            alternative_explanations=[
                "Editors are also used for harmless changes (cropping, brightness, format conversion).",
                "Cameras and phones also write the Software field (firmware or OS version).",
            ],
            additional_evidence_needed=["The original file, or a description of what edits were made."],
            evidence={"software": software},
        ))

    haystack = " ".join(
        [str(s) for s in software_values]
        + [f"{k} {v}" for k, v in container_info.items()]
        + [xmp or ""]
    ).lower()
    ai_hits = [k for k in AI_TOOL_KEYWORDS if k in haystack]
    if "steps:" in haystack and "sampler" in haystack:
        ai_hits.append("generation parameters text (Steps/Sampler)")
    if "trainedalgorithmicmedia" in haystack:
        ai_hits.append("IPTC digital source type: trained algorithmic media")
    if ai_hits:
        findings.append(make_finding(
            id="ai_tool_trace", source="metadata",
            title="Metadata text associated with AI image generation",
            strength="moderate",
            observation="Embedded metadata mentions AI image tools, generation parameters or an AI digital-source-type label.",
            method="Keyword search of EXIF Software, container text chunks and the XMP packet.",
            why_it_matters="Self-declared metadata of this kind suggests an AI-assisted workflow was involved.",
            alternative_explanations=[
                "Anyone can add or copy such text, so it could be a false label.",
                "An AI tool may have been used on only part of the image, or only for minor retouching.",
            ],
            additional_evidence_needed=["Provenance records, the generating tool's own output, or a validated AI-image detector."],
            evidence={"matched": ai_hits},
        ))

    original = _parse_exif_date(exif_all.get("DateTimeOriginal"))
    modified = _parse_exif_date(exif_all.get("DateTime"))
    if original and modified:
        gap = abs((modified - original).total_seconds())
        if gap > TIMESTAMP_GAP_SECONDS:
            findings.append(make_finding(
                id="timestamp_gap", source="metadata",
                title="Capture and modification timestamps differ",
                strength="weak",
                observation=f"DateTimeOriginal is {original.isoformat()} and DateTime is {modified.isoformat()} (gap about {int(gap)} seconds).",
                method=f"Compared two EXIF timestamps; gaps over {TIMESTAMP_GAP_SECONDS} s are reported.",
                why_it_matters="A later modification time means the file was saved again after capture.",
                alternative_explanations=[
                    "Rotation, format conversion or export from a photo library also re-saves the file.",
                    "Camera clocks can be wrong or reset.",
                ],
                additional_evidence_needed=["The original file, or the edit history from the device or software."],
                evidence={"DateTimeOriginal": original.isoformat(), "DateTime": modified.isoformat()},
            ))

    ex_w, ex_h = exif_all.get("PixelXDimension"), exif_all.get("PixelYDimension")
    if isinstance(ex_w, int) and isinstance(ex_h, int) and (ex_w, ex_h) != image.size:
        findings.append(make_finding(
            id="dimension_mismatch", source="metadata",
            title="EXIF dimensions differ from the actual image size", strength="weak",
            observation=f"EXIF states {ex_w}x{ex_h}; the decoded image is {image.size[0]}x{image.size[1]}.",
            method="Compared EXIF PixelXDimension/PixelYDimension with the decoded size.",
            why_it_matters="Suggests the image was resized or cropped after the EXIF block was written.",
            alternative_explanations=["Resizing and cropping are routine and not deceptive in themselves."],
            additional_evidence_needed=["The original, uncropped file."],
            evidence={"exif": [ex_w, ex_h], "actual": list(image.size)},
        ))

    if gps["present"]:
        findings.append(make_finding(
            id="gps_present", source="metadata", title="GPS location data present",
            strength="informational",
            observation="The file embeds GPS fields." + ("" if include_gps_values else " Coordinates are withheld from this report."),
            method="Read the EXIF GPS IFD.",
            why_it_matters="Location claims can be compared with the story attached to the image. It is also a privacy risk when sharing the file.",
            alternative_explanations=["Location data can be fabricated or copied."],
            additional_evidence_needed=["Independent confirmation of the location (landmarks, satellite imagery)."],
            evidence={"gps_fields": gps["fields"]},
        ))

    return {
        "status": "ok",
        "exif_present": bool(exif_all),
        "exif": exif_all,
        "summary": summary,
        "gps": gps,
        "container_info": container_info,
        "flags": flags,
        "findings": findings,
        "notes": [
            "Sensitive identifiers (owner, author, serial numbers) are reported as present but their values are withheld.",
            "GPS coordinates are withheld unless explicitly enabled in the server configuration.",
        ],
        "limitations": [
            "Metadata can be removed, edited, copied or fabricated.",
            "Missing metadata is not evidence of manipulation or AI generation.",
            "Present metadata does not prove authenticity.",
        ],
    }
