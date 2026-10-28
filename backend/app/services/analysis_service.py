"""Orchestrates one analysis: validate -> analyse -> assess -> store -> report."""

import logging
import os
from datetime import datetime, timedelta, timezone

from PIL import Image

from app.analysis.ai_detection import run_ai_detection
from app.analysis.assessment import GLOBAL_LIMITATIONS, build_assessment
from app.analysis.ela import LIMITATIONS as ELA_LIMITATIONS
from app.analysis.ela import run_ela
from app.analysis.image_statistics import compute_statistics
from app.analysis.metadata import extract_metadata
from app.analysis.provenance import inspect_provenance
from app.analysis.report import generate_report
from app.analysis.validation import validate_image
from app.config import Settings
from app.database import AnalysisRepository
from app.utils.file_utils import (
    is_valid_analysis_id,
    is_valid_evidence_name,
    new_analysis_id,
    remove_directory,
    remove_file,
    safe_join,
)

logger = logging.getLogger("deeptrace.service")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisService:
    def __init__(self, settings: Settings, repo: AnalysisRepository):
        self.settings = settings
        self.repo = repo

    # -- storage ------------------------------------------------------------------
    def ensure_storage(self) -> None:
        for d in (self.settings.uploads_dir, self.settings.evidence_dir, self.settings.reports_dir):
            d.mkdir(parents=True, exist_ok=True)

    def storage_ok(self) -> bool:
        return all(
            d.is_dir() and os.access(d, os.W_OK)
            for d in (self.settings.evidence_dir, self.settings.reports_dir)
        )

    def _remove_artifacts(self, analysis_id: str) -> None:
        remove_directory(self.settings.evidence_dir, analysis_id)
        remove_file(self.settings.reports_dir, f"report_{analysis_id}.pdf")

    # -- main workflow ------------------------------------------------------------
    def analyze(self, raw: bytes, filename: str | None) -> dict:
        # Raises ValidationError for bad uploads. The upload itself is processed in memory
        # and is never written to disk.
        validated = validate_image(raw, filename, self.settings.max_upload_bytes, self.settings.max_pixels)
        image, props = validated.image, validated.properties
        fmt = props["format"]

        analysis_id = new_analysis_id()
        created_at = _now().isoformat(timespec="seconds")
        warnings_list: list = []
        evidence: list = []

        try:
            # Metadata
            try:
                metadata = extract_metadata(image, validated.raw_bytes, self.settings.include_gps_values)
            except Exception as exc:
                logger.exception("metadata failed")
                metadata = {"status": "error", "error": f"Metadata extraction failed ({type(exc).__name__}).",
                            "findings": [], "limitations": ["Metadata could not be analysed."]}
                warnings_list.append("Metadata analysis failed.")

            # ELA
            ela_image = None
            try:
                ela, ela_image = run_ela(image, self.settings.ela_quality, fmt)
            except Exception as exc:
                logger.exception("ela failed")
                ela = {"status": "error", "error": f"ELA failed ({type(exc).__name__}).",
                       "method": None, "jpeg_quality": None, "source_format": fmt,
                       "explanation": "ELA could not be computed for this image.",
                       "limitations": ELA_LIMITATIONS, "findings": []}
                warnings_list.append("ELA failed.")

            # Statistics
            try:
                indicators = compute_statistics(image, fmt)
                indicators_status = "ok"
            except Exception:
                logger.exception("statistics failed")
                indicators, indicators_status = [], "error"
                warnings_list.append("Image statistics failed.")

            # AI detection and provenance
            ai = run_ai_detection(image, self.settings.ai_detector)
            if ai.get("status") == "error":
                warnings_list.append("The configured AI detector failed.")
            try:
                provenance = inspect_provenance(validated.raw_bytes, fmt)
            except Exception:
                logger.exception("provenance failed")
                provenance = {"status": "error", "credentials_detected": False, "verification": "not_performed",
                              "container": None, "evidence": {},
                              "explanation": "Provenance inspection failed.", "limitations": []}
                warnings_list.append("Provenance inspection failed.")

            # Evidence files
            ela_path = preview_path = None
            evidence_dir = safe_join(self.settings.evidence_dir, analysis_id)
            self.ensure_storage()
            if ela_image is not None:
                try:
                    evidence_dir.mkdir(parents=True, exist_ok=True)
                    ela_path = evidence_dir / "ela.png"
                    ela_image.save(ela_path, "PNG")
                    url = f"/api/v1/analyses/{analysis_id}/evidence/ela.png"
                    ela["evidence_url"] = url
                    evidence.append({"name": "ela.png", "url": url, "content_type": "image/png",
                                     "description": "Amplified Error Level Analysis difference image."})
                except Exception:
                    logger.exception("saving ELA evidence failed")
                    ela_path = None
                    warnings_list.append("ELA evidence image could not be saved.")
            if self.settings.store_preview:
                try:
                    evidence_dir.mkdir(parents=True, exist_ok=True)
                    preview = image.copy()
                    preview.thumbnail((800, 800))
                    if preview.mode not in ("RGB", "L"):
                        from app.analysis.common import to_rgb
                        preview = to_rgb(preview)
                    preview_path = evidence_dir / "preview.jpg"
                    preview.convert("RGB").save(preview_path, "JPEG", quality=85)
                    url = f"/api/v1/analyses/{analysis_id}/evidence/preview.jpg"
                    evidence.append({"name": "preview.jpg", "url": url, "content_type": "image/jpeg",
                                     "description": "Downscaled preview of the analysed image (the original upload is not stored)."})
                except Exception:
                    logger.exception("saving preview failed")
                    preview_path = None
                    warnings_list.append("Preview image could not be saved.")

            assessment = build_assessment(
                metadata=metadata, ela=ela, indicators_status=indicators_status, ai=ai, provenance=provenance
            )
            core_failed = any(c["status"] == "error" for c in assessment["checks"])
            result = {
                "analysis_id": analysis_id,
                "created_at": created_at,
                "status": "partial" if (core_failed or warnings_list) else "completed",
                "image_info": props,
                "metadata": metadata,
                "ela": ela,
                "indicators": indicators,
                "ai_detection": ai,
                "provenance": provenance,
                "overall_assessment": assessment,
                "limitations": GLOBAL_LIMITATIONS,
                "evidence": evidence,
                "report_url": None,
                "warnings": warnings_list,
            }

            # PDF report
            report_file = f"report_{analysis_id}.pdf"
            try:
                generate_report(result, safe_join(self.settings.reports_dir, report_file), ela_path, preview_path)
                result["report_url"] = f"/api/v1/analyses/{analysis_id}/report"
            except Exception:
                logger.exception("report generation failed")
                report_file = None
                result["warnings"].append("PDF report could not be generated.")
                result["status"] = "partial"

            self.repo.save(result, report_file)
            return result
        except Exception:
            self._remove_artifacts(analysis_id)
            raise

    # -- retrieval ----------------------------------------------------------------
    def get(self, analysis_id: str) -> dict | None:
        if not is_valid_analysis_id(analysis_id):
            return None
        return self.repo.get(analysis_id)

    def list(self, limit: int, offset: int):
        return self.repo.list(limit, offset)

    def report_path(self, analysis_id: str):
        if not is_valid_analysis_id(analysis_id) or self.repo.get(analysis_id) is None:
            return None
        path = safe_join(self.settings.reports_dir, f"report_{analysis_id}.pdf")
        return path if path.is_file() else None

    def evidence_path(self, analysis_id: str, name: str):
        if not (is_valid_analysis_id(analysis_id) and is_valid_evidence_name(name)):
            return None
        result = self.repo.get(analysis_id)
        if result is None or name not in {e.get("name") for e in result.get("evidence", [])}:
            return None
        path = safe_join(self.settings.evidence_dir, analysis_id, name)
        return path if path.is_file() else None

    def delete(self, analysis_id: str) -> bool:
        if not is_valid_analysis_id(analysis_id):
            return False
        deleted = self.repo.delete(analysis_id)
        if deleted:
            self._remove_artifacts(analysis_id)
        return deleted

    def cleanup_expired(self) -> int:
        """Delete analyses older than the retention period (0 = keep forever)."""
        days = self.settings.retention_days
        if days <= 0:
            return 0
        cutoff = (_now() - timedelta(days=days)).isoformat(timespec="seconds")
        count = 0
        for analysis_id in self.repo.ids_older_than(cutoff):
            if self.delete(analysis_id):
                count += 1
        return count
