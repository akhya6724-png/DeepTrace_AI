"""Feature E: content-credentials (C2PA) inspection.

This module only DETECTS whether a C2PA/JUMBF container is embedded, by walking the file
structure (JPEG APP11 segments, PNG ``caBX`` chunk, WebP ``C2PA`` chunk).

It does NOT verify signatures or certificate chains: no C2PA verification library is
bundled. So the result is always either:
  * ``no_credentials_detected``
  * ``credentials_detected_unverified``   (verification: ``not_performed``)
It never reports an image as authentic.
"""

LIMITATIONS = [
    "Detection of an embedded structure is not verification: signatures and certificate chains were not checked.",
    "Absence of credentials is not evidence of manipulation. Most platforms and tools strip them.",
    "Even a valid credential only documents claimed history; it does not prove that what the image depicts is true.",
    "Use a full C2PA verifier (for example the open-source c2patool or the Content Credentials verify site) for verification.",
]


def _scan_jpeg(raw: bytes) -> dict | None:
    i, size, segments, total = 2, len(raw), 0, 0
    label = False
    while i + 4 <= size:
        if raw[i] != 0xFF:
            break
        marker = raw[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        if marker in (0xDA, 0xD9):  # start of scan / end of image
            break
        if 0xD0 <= marker <= 0xD8 or marker == 0x01:
            i += 2
            continue
        length = int.from_bytes(raw[i + 2:i + 4], "big")
        if length < 2:
            break
        payload = raw[i + 4:i + 2 + length]
        if marker == 0xEB and b"jumb" in payload[:32]:
            segments += 1
            total += len(payload)
            label = label or b"c2pa" in payload
        i += 2 + length
    if segments and label:
        return {"container": "JPEG APP11 (JUMBF) segments", "segments": segments, "bytes": total}
    return None


def _scan_png(raw: bytes) -> dict | None:
    i, size = 8, len(raw)
    while i + 12 <= size:
        length = int.from_bytes(raw[i:i + 4], "big")
        ctype = raw[i + 4:i + 8]
        if ctype == b"caBX":
            return {"container": "PNG caBX chunk", "segments": 1, "bytes": length}
        if ctype == b"IEND":
            break
        i += 12 + length
    return None


def _scan_webp(raw: bytes) -> dict | None:
    i, size = 12, len(raw)
    while i + 8 <= size:
        fourcc = raw[i:i + 4]
        length = int.from_bytes(raw[i + 4:i + 8], "little")
        if fourcc == b"C2PA":
            return {"container": "WebP C2PA chunk", "segments": 1, "bytes": length}
        i += 8 + length + (length & 1)
    return None


def inspect_provenance(raw: bytes, image_format: str) -> dict:
    scanners = {"JPEG": _scan_jpeg, "PNG": _scan_png, "WEBP": _scan_webp}
    found = scanners.get(image_format, lambda _r: None)(raw)
    if found:
        return {
            "status": "credentials_detected_unverified",
            "credentials_detected": True,
            "verification": "not_performed",
            "container": found["container"],
            "evidence": {"segments": found["segments"], "embedded_bytes": found["bytes"]},
            "explanation": (
                "An embedded content-credentials (C2PA/JUMBF) data structure was found, but this installation "
                "cannot verify its signature or certificate chain, so its claims are unverified."
            ),
            "limitations": LIMITATIONS,
        }
    return {
        "status": "no_credentials_detected",
        "credentials_detected": False,
        "verification": "not_applicable",
        "container": None,
        "evidence": {},
        "explanation": "No embedded content-credentials (C2PA) data structure was detected in this file.",
        "limitations": LIMITATIONS,
    }
