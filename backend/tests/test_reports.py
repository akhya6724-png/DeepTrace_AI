from app.analysis.report import generate_report
from tests.helpers import jpeg_bytes


def test_pdf_created_and_non_empty(service, settings):
    r = service.analyze(jpeg_bytes(), "a.jpg")
    pdf = settings.reports_dir / f"report_{r['analysis_id']}.pdf"
    assert pdf.is_file() and pdf.stat().st_size > 1000
    assert pdf.read_bytes().startswith(b"%PDF")
    assert r["report_url"].endswith("/report")


def test_report_unique_filenames(service, settings):
    a = service.analyze(jpeg_bytes(seed=1), "a.jpg")
    b = service.analyze(jpeg_bytes(seed=2), "b.jpg")
    assert a["analysis_id"] != b["analysis_id"]
    assert len(list(settings.reports_dir.glob("report_*.pdf"))) == 2


def test_report_survives_missing_optional_sections(tmp_path):
    out = tmp_path / "minimal.pdf"
    generate_report({"analysis_id": "x", "created_at": "now"}, out)
    assert out.is_file() and out.stat().st_size > 500


def test_report_escapes_markup_in_metadata(tmp_path):
    out = tmp_path / "evil.pdf"
    generate_report({"analysis_id": "<b>x</b>", "image_info": {"original_filename": "<script>&</script>"},
                     "metadata": {"status": "ok", "exif": {"Software": "<i>&amp;"}}}, out)
    assert out.stat().st_size > 500
