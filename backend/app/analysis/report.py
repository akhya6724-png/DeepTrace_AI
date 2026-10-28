"""PDF report generation with ReportLab."""

import os
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

CATEGORY_LABELS = {
    "no_strong_indicators_found": "No strong indicators found by the implemented checks",
    "inconclusive": "Inconclusive",
    "potential_manipulation_indicators": "Potential manipulation indicators - further investigation needed",
    "analysis_incomplete": "Analysis incomplete",
}
NAVY = colors.HexColor("#0b1f4d")
BLUE = colors.HexColor("#1d4ed8")
LIGHT = colors.HexColor("#eef2ff")

_styles = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=_styles["BodyText"], fontSize=9, leading=12)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=10, textColor=colors.HexColor("#444444"))
H1 = ParagraphStyle("h1", parent=_styles["Title"], textColor=NAVY, fontSize=22, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=_styles["Heading2"], textColor=BLUE, fontSize=13, spaceBefore=10, spaceAfter=4)
H3 = ParagraphStyle("h3", parent=_styles["Heading3"], textColor=NAVY, fontSize=10, spaceBefore=6, spaceAfter=2)


def _p(text, style=BODY):
    return Paragraph(escape("" if text is None else str(text)), style)


def _bullets(items, style=BODY):
    return [Paragraph("&bull; " + escape(str(i)), style) for i in (items or [])]


def _kv(rows, widths=(5 * cm, 11.5 * cm)):
    data = [[_p(k, SMALL), _p(v)] for k, v in rows]
    if not data:
        return Spacer(1, 2)
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c7d2fe")),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _image(path, max_w=16 * cm, max_h=9 * cm):
    try:
        with Image.open(path) as im:
            w, h = im.size
        scale = min(max_w / w, max_h / h, 1e6)
        return RLImage(str(path), width=w * scale, height=h * scale)
    except Exception:
        return _p("(image could not be embedded)", SMALL)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(2 * cm, 1.1 * cm, "DeepTrace AI - investigative aid, not an infallible authenticity verifier.")
    canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def generate_report(result: dict, output_path: Path, ela_image_path: Path | None = None,
                    preview_path: Path | None = None) -> None:
    """Write the PDF to ``output_path``. Every section is optional; missing data never raises."""
    info = result.get("image_info") or {}
    meta = result.get("metadata") or {}
    ela = result.get("ela") or {}
    ai = result.get("ai_detection") or {}
    prov = result.get("provenance") or {}
    assess = result.get("overall_assessment") or {}
    story = []

    story += [_p("DeepTrace AI", H1), _p("Explainable image forensic report", BODY), Spacer(1, 6)]
    story.append(_kv([
        ("Analysis ID", result.get("analysis_id")),
        ("Created (UTC)", result.get("created_at")),
        ("Analysis status", result.get("status")),
    ]))

    story.append(_p("Overall assessment", H2))
    story.append(_p(CATEGORY_LABELS.get(assess.get("category"), assess.get("category") or "Not available"), H3))
    story.append(_p(assess.get("summary")))
    story += _bullets(assess.get("rationale"))
    if assess.get("scoring_note"):
        story.append(_p(assess["scoring_note"], SMALL))

    story.append(_p("1. Image summary", H2))
    story.append(_kv([
        ("File name (as uploaded)", info.get("original_filename")),
        ("Format / MIME", f"{info.get('format')} / {info.get('mime_type')}"),
        ("Dimensions", f"{info.get('width')} x {info.get('height')} px ({info.get('megapixels')} MP)"),
        ("Color mode", info.get("color_mode")),
        ("File size", f"{info.get('file_size_bytes')} bytes"),
        ("SHA-256", info.get("sha256")),
    ]))
    if preview_path and Path(preview_path).is_file():
        story += [Spacer(1, 6), _image(preview_path, 12 * cm, 7 * cm)]

    story.append(_p("2. File and metadata findings", H2))
    if meta.get("status") == "ok":
        s = meta.get("summary") or {}
        story.append(_kv([
            ("EXIF present", meta.get("exif_present")),
            ("Camera", " ".join(x for x in (s.get("camera_make"), s.get("camera_model")) if x) or "not declared"),
            ("Software", s.get("software") or s.get("xmp_creator_tool") or "not declared"),
            ("Timestamps", s.get("timestamps") or "none"),
            ("GPS", "present (coordinates withheld)" if (meta.get("gps") or {}).get("present") else "none"),
        ]))
        exif_rows = list((meta.get("exif") or {}).items())[:40]
        if exif_rows:
            story += [_p("EXIF fields (first 40)", H3), _kv(exif_rows)]
        story += _bullets(meta.get("limitations"), SMALL)
    else:
        story.append(_p(f"Metadata analysis unavailable: {meta.get('error', 'not run')}"))

    story.append(_p("3. Forensic analysis", H2))
    if ela.get("status") == "ok":
        st = ela.get("difference_statistics") or {}
        story.append(_p("Error Level Analysis (ELA)", H3))
        story.append(_p(ela.get("explanation")))
        story.append(_p(ela.get("interpretability"), SMALL))
        story.append(_kv([
            ("JPEG quality used", ela.get("jpeg_quality")),
            ("Mean difference", st.get("mean")), ("99th percentile", st.get("p99")),
            ("Amplification", (ela.get("visualization") or {}).get("amplification_factor")),
        ]))
        if ela_image_path and Path(ela_image_path).is_file():
            story += [Spacer(1, 6), _image(ela_image_path, 14 * cm, 9 * cm)]
        story.append(_p("ELA limitations", H3))
        story += _bullets(ela.get("limitations"), SMALL)
    else:
        story.append(_p(f"ELA unavailable: {ela.get('error', 'not run')}"))

    indicators = result.get("indicators") or []
    if indicators:
        story.append(_p("Image statistics", H3))
        for ind in indicators:
            story.append(KeepTogether([
                _p(ind.get("name"), SMALL),
                _p(ind.get("value")),
                _p("Method: " + str(ind.get("method")), SMALL),
                _p("Limitations: " + "; ".join(ind.get("limitations") or []), SMALL),
                Spacer(1, 3),
            ]))

    story.append(_p("4. AI-origin detector", H2))
    story.append(_kv([
        ("Status", ai.get("status")), ("Prediction", ai.get("prediction") or "none"),
        ("Method", ai.get("method") or "none"),
    ]))
    story.append(_p(ai.get("explanation")))
    story += _bullets(ai.get("limitations"), SMALL)

    story.append(_p("5. Provenance (content credentials)", H2))
    story.append(_kv([
        ("Status", prov.get("status")), ("Verification", prov.get("verification")),
        ("Container", prov.get("container") or "none"),
    ]))
    story.append(_p(prov.get("explanation")))
    story += _bullets(prov.get("limitations"), SMALL)

    story.append(_p("6. Findings and explanations", H2))
    findings = assess.get("findings") or []
    if not findings:
        story.append(_p("No findings were produced by the implemented checks."))
    for f in findings:
        story.append(KeepTogether([
            _p(f"{f.get('title')}  [{f.get('strength')}]", H3),
            _p("Observed: " + str(f.get("observation"))),
            _p("Measured by: " + str(f.get("method")), SMALL),
            _p("Why it may matter: " + str(f.get("why_it_matters")), SMALL),
            _p("Alternative explanations: " + "; ".join(f.get("alternative_explanations") or []), SMALL),
            _p("Additional evidence needed: " + "; ".join(f.get("additional_evidence_needed") or []), SMALL),
        ]))

    story.append(_p("7. Evidence references", H2))
    ev = result.get("evidence") or []
    story += _bullets([f"{e.get('name')}: {e.get('description')}" for e in ev]) or [_p("None")]

    story.append(_p("8. Recommended next investigative steps", H2))
    story += _bullets(assess.get("recommended_next_steps"))

    story.append(_p("9. Limitations and disclaimer", H2))
    story += _bullets(result.get("limitations"))
    story.append(Spacer(1, 6))
    story.append(_p(
        "This report is an investigative aid based on the listed automated checks. It is not a legal, forensic or "
        "journalistic determination, and it does not establish that an image is authentic or fake.", SMALL))

    output_path = Path(output_path)
    tmp = output_path.with_suffix(".tmp")
    doc = SimpleDocTemplate(str(tmp), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm, title="DeepTrace AI Report",
                            author="DeepTrace AI")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    os.replace(tmp, output_path)
