"""Service-level tests (no HTTP) followed by API tests (need fastapi/httpx)."""

import io

from app.config import Settings
from app.database import AnalysisRepository
from app.services.analysis_service import AnalysisService
from tests.helpers import exif_with_edit_info, jpeg_bytes, png_bytes

REQUIRED_KEYS = {"analysis_id", "created_at", "status", "image_info", "metadata", "ela", "indicators",
                 "ai_detection", "provenance", "overall_assessment", "limitations", "evidence", "report_url"}


def test_service_full_result(service):
    r = service.analyze(jpeg_bytes(), "photo.jpg")
    assert REQUIRED_KEYS <= set(r)
    assert r["status"] == "completed"
    assert r["ai_detection"]["status"] == "unavailable"
    assert r["limitations"] and r["overall_assessment"]["category"] in (
        "no_strong_indicators_found", "inconclusive", "potential_manipulation_indicators", "analysis_incomplete")
    assert "calibrated probability" in r["overall_assessment"]["scoring_note"]


def test_clean_image_is_not_called_authentic(service):
    r = service.analyze(png_bytes(), "clean.png")
    a = r["overall_assessment"]
    assert a["category"] == "no_strong_indicators_found"
    assert "not proof" in a["summary"].lower()


def test_ai_metadata_trace_raises_category(service):
    r = service.analyze(png_bytes(text={"parameters": "Steps: 20, Sampler: Euler"}), "gen.png")
    assert r["overall_assessment"]["category"] == "potential_manipulation_indicators"


def test_single_weak_indicator_is_inconclusive(service):
    ex = exif_with_edit_info()
    ex[0x0131] = "Camera Firmware 1.0"   # not editing software
    r = service.analyze(jpeg_bytes(exif=ex), "x.jpg")
    assert r["overall_assessment"]["category"] == "inconclusive"  # only timestamp_gap is weak


def test_no_filesystem_paths_in_result(service, settings):
    r = service.analyze(jpeg_bytes(), "../../etc/passwd.jpg")
    assert str(settings.storage_dir) not in str(r)


def test_persistence_survives_restart(service, settings):
    r = service.analyze(jpeg_bytes(), "a.jpg")
    fresh = AnalysisService(settings, AnalysisRepository(settings.db_path))
    again = fresh.get(r["analysis_id"])
    assert again is not None and again["analysis_id"] == r["analysis_id"]


def test_delete_removes_only_its_own_files(service, settings):
    a = service.analyze(jpeg_bytes(seed=1), "a.jpg")
    b = service.analyze(jpeg_bytes(seed=2), "b.jpg")
    assert service.delete(a["analysis_id"]) is True
    assert not (settings.evidence_dir / a["analysis_id"]).exists()
    assert not (settings.reports_dir / f"report_{a['analysis_id']}.pdf").exists()
    assert service.get(b["analysis_id"]) is not None
    assert (settings.reports_dir / f"report_{b['analysis_id']}.pdf").is_file()


def test_unknown_and_malicious_ids(service):
    assert service.get("0" * 32) is None
    assert service.get("../../etc/passwd") is None
    assert service.delete("../x") is False
    assert service.evidence_path("0" * 32, "ela.png") is None


def test_evidence_path_traversal_blocked(service):
    r = service.analyze(jpeg_bytes(), "a.jpg")
    assert service.evidence_path(r["analysis_id"], "ela.png") is not None
    assert service.evidence_path(r["analysis_id"], "../../deeptrace.db") is None
    assert service.evidence_path(r["analysis_id"], "other.png") is None


def test_retention_cleanup(tmp_path):
    s = Settings(storage_dir=tmp_path / "s", retention_days=1)
    repo = AnalysisRepository(s.db_path)
    svc = AnalysisService(s, repo)
    svc.ensure_storage()
    repo.init()
    r = svc.analyze(jpeg_bytes(), "a.jpg")
    import sqlite3
    with sqlite3.connect(str(s.db_path)) as c:
        c.execute("UPDATE analyses SET created_at = '2000-01-01T00:00:00+00:00'")
    assert svc.cleanup_expired() == 1 and svc.get(r["analysis_id"]) is None


def test_corrupt_database_is_recovered(tmp_path):
    s = Settings(storage_dir=tmp_path / "s")
    s.storage_dir.mkdir(parents=True)
    s.db_path.write_bytes(b"this is not a sqlite database at all" * 50)
    repo = AnalysisRepository(s.db_path)
    repo.init()
    assert repo.ping() and repo.list(10, 0) == ([], 0)


# ---------------------------------------------------------------- API (need fastapi)
def _upload(client, data, name="photo.jpg", mime="image/jpeg"):
    return client.post("/api/v1/analyze", files={"file": (name, io.BytesIO(data), mime)})


def test_api_upload_and_fetch(client):
    r = _upload(client, jpeg_bytes(exif=exif_with_edit_info()))
    assert r.status_code == 200, r.text
    body = r.json()
    assert REQUIRED_KEYS <= set(body)
    assert body["ai_detection"]["status"] == "unavailable"
    again = client.get(f"/api/v1/analyses/{body['analysis_id']}")
    assert again.status_code == 200 and again.json()["analysis_id"] == body["analysis_id"]


def test_api_evidence_and_report(client):
    body = _upload(client, jpeg_bytes()).json()
    ev = client.get(body["evidence"][0]["url"])
    assert ev.status_code == 200 and ev.headers["content-type"] == "image/png"
    rep = client.get(body["report_url"])
    assert rep.status_code == 200 and rep.headers["content-type"] == "application/pdf"
    assert rep.content.startswith(b"%PDF") and len(rep.content) > 1000


def test_api_history_pagination_order(client):
    ids = [_upload(client, jpeg_bytes(seed=i)).json()["analysis_id"] for i in range(3)]
    page = client.get("/api/v1/analyses?limit=2&offset=0").json()
    assert page["total"] == 3 and len(page["items"]) == 2
    assert page["items"][0]["analysis_id"] == ids[-1]  # newest first
    assert client.get("/api/v1/analyses?limit=0").status_code == 422


def test_api_unknown_ids_404(client):
    for path in ("/api/v1/analyses/" + "0" * 32, "/api/v1/analyses/not-an-id",
                 "/api/v1/analyses/" + "0" * 32 + "/report",
                 "/api/v1/analyses/" + "0" * 32 + "/evidence/ela.png"):
        assert client.get(path).status_code == 404
    assert client.delete("/api/v1/analyses/" + "0" * 32).status_code == 404


def test_api_evidence_traversal(client):
    aid = _upload(client, jpeg_bytes()).json()["analysis_id"]
    for name in ("..%2F..%2Fdeeptrace.db", "%2e%2e%2fsecret.png", "ela.png%00", "other.png"):
        assert client.get(f"/api/v1/analyses/{aid}/evidence/{name}").status_code == 404


def test_api_delete(client):
    body = _upload(client, jpeg_bytes()).json()
    assert client.delete(f"/api/v1/analyses/{body['analysis_id']}").status_code == 200
    assert client.get(f"/api/v1/analyses/{body['analysis_id']}").status_code == 404
    assert client.get(body["report_url"]).status_code == 404


def test_api_rejects_bad_uploads(client):
    assert _upload(client, b"plain text", "a.jpg").status_code == 415
    assert _upload(client, jpeg_bytes()[:3000], "a.jpg").status_code == 422
    assert _upload(client, b"", "a.jpg").status_code == 400
    assert _upload(client, b"x" * (2 * 1024 * 1024 + 10), "big.jpg").status_code == 413
    assert client.post("/api/v1/analyze").status_code == 422                       # missing file
    assert client.post("/api/v1/analyze", data={"file": "not a file"}).status_code == 422
    assert client.post("/api/v1/analyze", json={"a": 1}).status_code == 422        # wrong body type
