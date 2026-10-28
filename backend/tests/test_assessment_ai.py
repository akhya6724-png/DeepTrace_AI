from app.analysis.assessment import build_assessment


def make_inputs(ai):
    return {
        "metadata": {"status": "ok", "findings": [], "exif_present": True},
        "ela": {"status": "ok", "findings": []},
        "indicators_status": "ok",
        "ai": ai,
        "provenance": {
            "status": "ok",
            "credentials_detected": False,
            "verification": "not_performed",
        },
    }


def test_ai_generated_prediction_is_reported_as_a_finding():
    result = build_assessment(**make_inputs({
        "status": "ok",
        "prediction": "ai_generated",
        "method": "Test detector",
        "confidence": 0.91,
    }))

    assert any(f["id"] == "ai_detector_flag" for f in result["findings"])
    assert "not proof" in result["summary"].lower()


def test_real_image_likely_does_not_prove_authenticity():
    result = build_assessment(**make_inputs({
        "status": "ok",
        "prediction": "real_image_likely",
        "method": "Test detector",
        "confidence": 0.01,
    }))

    assert not any(f["id"] == "ai_detector_flag" for f in result["findings"])
    assert "not proof" in result["summary"].lower()


def test_unavailable_detector_is_not_reported_as_performed():
    result = build_assessment(**make_inputs({
        "status": "unavailable",
        "prediction": None,
        "method": None,
        "confidence": None,
    }))

    assert any(
        "AI-image detection was not performed" in item
        for item in result["rationale"]
    )


def test_scoring_note_does_not_claim_a_calibrated_probability():
    result = build_assessment(**make_inputs({
        "status": "ok",
        "prediction": "real_image_likely",
        "method": "Test detector",
        "confidence": 0.01,
    }))

    assert "calibrated" in result["scoring_note"].lower()
    assert "probability" in result["scoring_note"].lower()
def test_ai_generated_likely_prediction_is_reported():
    result = build_assessment(**make_inputs({
        "status": "ok",
        "prediction": "ai_generated_likely",
        "method": "Test detector",
        "confidence": 0.91,
    }))

    assert any(
        f["id"] == "ai_detector_flag"
        for f in result["findings"]
    )  