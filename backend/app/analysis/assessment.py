"""Explainable overall assessment.

Aggregates ONLY the real outputs of implemented checks. There is no numeric "fake
probability": no calibrated, validated model exists to produce one honestly.
"""

GLOBAL_LIMITATIONS = [
    "DeepTrace AI is an investigative aid, not an infallible authenticity verifier.",
    "The implemented checks cannot detect many kinds of manipulation, including most AI-generated or well-made edits.",
    "A result of 'no strong indicators' does not prove an image is authentic or unedited.",
    "Metadata can be removed, edited or fabricated; its absence or presence proves nothing by itself.",
    "ELA and statistics are heuristics for human review and have known false positives and false negatives.",
    "AI-image detection and cryptographic provenance verification are only as available as reported in this result.",
]

CATEGORY_SUMMARIES = {
    "no_strong_indicators_found": (
        "The implemented checks did not find strong indicators of manipulation. This is NOT proof that the image is "
        "authentic: these checks cannot detect many kinds of manipulation, including AI-generated images."
    ),
    "inconclusive": (
        "One weak indicator was found. Weak indicators have many harmless explanations, so the evidence is inconclusive."
    ),
    "potential_manipulation_indicators": (
        "Indicators that warrant further investigation were found. They are not proof of manipulation: each has "
        "alternative explanations listed below."
    ),
    "analysis_incomplete": (
        "One or more core checks failed, so the assessment is incomplete and should not be relied on."
    ),
}

CORE_CHECKS = ("metadata", "ela", "statistics")


def build_assessment(*, metadata: dict, ela: dict, indicators_status: str, ai: dict, provenance: dict) -> dict:
    checks = [
        {"name": "validation", "status": "ok", "detail": "File decoded successfully."},
        {"name": "metadata", "status": metadata.get("status", "error"), "detail": metadata.get("error")},
        {"name": "ela", "status": ela.get("status", "error"), "detail": ela.get("error")},
        {"name": "statistics", "status": indicators_status, "detail": None},
        {"name": "ai_detection", "status": ai.get("status", "error"), "detail": ai.get("error")},
        {"name": "provenance", "status": provenance.get("status", "error"), "detail": None},
    ]
    failed = [c["name"] for c in checks if c["name"] in CORE_CHECKS and c["status"] == "error"]

    findings = []
    for source in (metadata, ela):
        findings.extend(source.get("findings", []) or [])

    
    if ai.get("status") == "ok":
        prediction = ai.get("prediction")

        if prediction in ("ai_generated", "ai_generated_likely"):
            findings.append({
                "id": "ai_detector_flag",
                "source": "ai_detection",
                "title": "AI detector flagged the image",
                "strength": "moderate",
                "observation": (
                    f"Detector '{ai.get('method')}' returned "
                    f"the prediction '{prediction}'."
                ),
                "method": "Pretrained detector inference.",
                "why_it_matters": (
                    "This is a model-based signal that warrants further review; "
                    "it does not establish that the image is AI-generated."
                ),
                "alternative_explanations": [
                    "AI detectors can produce false positives.",
                    "The model score is not a calibrated probability.",
                ],
                "additional_evidence_needed": [
                    "Original source and provenance records.",
                    "Independent detector results or expert review.",
                ],
                "evidence": {
                    "confidence_as_reported_by_model": ai.get("confidence")
                },
            })

        elif prediction == "real_image_likely":
            findings.append({
                "id": "ai_detector_real_likely",
                "source": "ai_detection",
                "title": "AI detector classified the image as likely real",
                "strength": "informational",
                "observation": (
                    "The detector returned a likely-real classification. "
                    "This does not prove authenticity or rule out manipulation."
                ),
                "method": "Pretrained detector inference.",
                "why_it_matters": (
                    "This records the detector's output without treating it "
                    "as proof that the image is genuine."
                ),
                "alternative_explanations": [
                    "The detector may miss AI-generated or manipulated images.",
                    "Performance can vary across image sources and processing methods.",
                ],
                "additional_evidence_needed": [
                    "Original source, provenance records, and independent verification."
                ],
                "evidence": {
                    "confidence_as_reported_by_model": ai.get("confidence")
                },
            })


    if provenance.get("credentials_detected"):
        findings.append({
            "id": "credentials_unverified", "source": "provenance",
            "title": "Content credentials embedded but not verified", "strength": "informational",
            "observation": f"A C2PA/JUMBF structure was found ({provenance.get('container')}).",
            "method": "File-structure scan; signatures were not checked.",
            "why_it_matters": "If valid, credentials can document the image's claimed capture and edit history.",
            "alternative_explanations": ["The structure could be invalid, altered or copied from another file."],
            "additional_evidence_needed": ["Verification with a full C2PA verifier."],
            "evidence": provenance.get("evidence", {}),
        })

    moderate = [f for f in findings if f["strength"] == "moderate"]
    weak = [f for f in findings if f["strength"] == "weak"]

    if failed:
        category = "analysis_incomplete"
    elif moderate or len(weak) >= 2:
        category = "potential_manipulation_indicators"
    elif len(weak) == 1:
        category = "inconclusive"
    else:
        category = "no_strong_indicators_found"

    rationale = []
    if failed:
        rationale.append("Failed core checks: " + ", ".join(failed) + ".")
    if moderate:
        rationale.append(f"{len(moderate)} moderate indicator(s): " + "; ".join(f["title"] for f in moderate) + ".")
    if weak:
        rationale.append(f"{len(weak)} weak indicator(s): " + "; ".join(f["title"] for f in weak) + ".")
    if not moderate and not weak and not failed:
        rationale.append("No moderate or weak indicators were produced by the implemented checks.")
   
    if ai.get("status") != "ok":
        rationale.append(
            "AI-image detection was not performed, so AI-generated content cannot be assessed."
        )
    elif ai.get("prediction") == "ai_generated_likely":
        rationale.append(
            "The AI detector flagged the image as likely AI-generated. "
            "This is a model-based indicator, not proof that the image is fake."
        )
    elif ai.get("prediction") == "real_image_likely":
        rationale.append(
            "The AI detector classified the image as likely real. "
            "This does not prove that the image is authentic or unmanipulated."
        )
    else:
        rationale.append(
            "The AI detector returned a result that could not be interpreted "
            "by the current assessment logic."
        )

    if provenance.get("verification") != "verified":
        rationale.append(
            "Content credentials were not cryptographically verified."
        )

    rationale.append(
        "ELA output is provided for manual inspection and is not scored automatically."
    )


    steps = [
        "Run a reverse image search to find earlier or higher-quality versions of the image.",
        "Identify the original source and ask for the original, unedited file.",
        "Check the claimed date, place and context against independent sources.",
    ]
    if moderate or weak:
        steps.append("Review each finding's 'additional evidence needed' list in this report.")
    if not metadata.get("exif_present"):
        steps.append("Request the original file with metadata intact; this copy has none.")
    if provenance.get("credentials_detected"):
        steps.append("Verify the embedded content credentials with a full C2PA verifier.")
    if ai.get("status") != "ok":
        steps.append("Consider a validated AI-image detector or expert review if AI generation is a concern.")

    return {
        "category": category,
        "summary": CATEGORY_SUMMARIES[category],
        "rationale": rationale,
        "findings": findings,
        "checks": checks,
        "recommended_next_steps": steps,
        "scoring_note": (
    "The AI detector may return a numeric model score. This score is not a calibrated "
    "probability and must not be interpreted as the probability that an image is fake "
    "or authentic. No validated overall fake-probability is calculated."
),
    }
