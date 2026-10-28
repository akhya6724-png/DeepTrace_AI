"""HTTP routes. Thin layer: all logic lives in the service and analysis modules."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.analysis.validation import ValidationError
from app.config import APP_NAME, APP_VERSION
from app.database import StoredDataError
from app.schemas import (
    AnalysisListResponse,
    AnalysisResponse,
    ApiHealthResponse,
    DeleteResponse,
    ErrorResponse,
    HealthResponse,
    RootResponse,
)
from app.services.analysis_service import AnalysisService

logger = logging.getLogger("deeptrace.api")

root_router = APIRouter(tags=["system"])
api_router = APIRouter(prefix="/api/v1")

NOT_FOUND = "Analysis not found."
MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg"}


def get_service(request: Request) -> AnalysisService:
    return request.app.state.service


# ---- system -----------------------------------------------------------------------
@root_router.get("/", response_model=RootResponse, summary="Application info")
def root():
    return {"name": APP_NAME, "version": APP_VERSION, "status": "running", "docs_url": "/docs"}


@root_router.get("/health", response_model=HealthResponse, summary="Health check")
def health():
    return {"status": "ok", "service": APP_NAME}


@api_router.get("/health", response_model=ApiHealthResponse, tags=["system"], summary="Versioned health check")
def api_health(service: AnalysisService = Depends(get_service)):
    detector = service.settings.ai_detector
    if detector in ("", "none"):
        detector_status = "unavailable"
    else:
        from app.analysis.ai_detection import detector_ready

        detector_status = "available" if detector_ready() else "unavailable"
    services = {
        "database": "ok" if service.repo.ping() else "error",
        "storage": "ok" if service.storage_ok() else "error",
        "ai_detector": detector_status,
        "provenance_verification": "unavailable",
    }
    overall = "ok" if services["database"] == "ok" and services["storage"] == "ok" else "degraded"
    return {"status": overall, "version": APP_VERSION, "services": services}


# ---- analysis ---------------------------------------------------------------------
@api_router.post(
    "/analyze",
    response_model=AnalysisResponse,
    tags=["analysis"],
    summary="Upload an image and receive an explainable forensic analysis",
    responses={
        400: {"model": ErrorResponse}, 413: {"model": ErrorResponse},
        415: {"model": ErrorResponse}, 422: {"model": ErrorResponse},
    },
)
async def analyze_image(
    file: UploadFile = File(..., description="JPEG, PNG or WebP image (multipart form field 'file')."),
    service: AnalysisService = Depends(get_service),
):
    limit = service.settings.max_upload_bytes
    raw = await file.read(limit + 1)  # never read more than limit + 1 bytes
    filename = file.filename
    await file.close()
    try:
        return await run_in_threadpool(service.analyze, raw, filename)
    except ValidationError as err:
        raise HTTPException(status_code=err.status_code, detail=err.message)


@api_router.get("/analyses", response_model=AnalysisListResponse, tags=["history"],
                summary="List previous analyses (newest first)")
def list_analyses(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: AnalysisService = Depends(get_service),
):
    items, total = service.list(limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@api_router.get("/analyses/{analysis_id}", response_model=AnalysisResponse, tags=["history"],
                summary="Get a stored analysis", responses={404: {"model": ErrorResponse}})
def get_analysis(analysis_id: str, service: AnalysisService = Depends(get_service)):
    try:
        result = service.get(analysis_id)
    except StoredDataError:
        raise HTTPException(status_code=500, detail="Stored analysis data is corrupted.")
    if result is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return result


@api_router.get("/analyses/{analysis_id}/report", tags=["history"],
                summary="Download the PDF report", responses={404: {"model": ErrorResponse}},
                response_class=FileResponse)
def download_report(analysis_id: str, service: AnalysisService = Depends(get_service)):
    path = service.report_path(analysis_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path, media_type="application/pdf",
                        filename=f"deeptrace_report_{analysis_id}.pdf")


@api_router.get("/analyses/{analysis_id}/evidence/{evidence_name}", tags=["history"],
                summary="Get a generated evidence image (for example ela.png)",
                responses={404: {"model": ErrorResponse}}, response_class=FileResponse)
def get_evidence(analysis_id: str, evidence_name: str, service: AnalysisService = Depends(get_service)):
    path = service.evidence_path(analysis_id, evidence_name)
    if path is None:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return FileResponse(path, media_type=MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream"))


@api_router.delete("/analyses/{analysis_id}", response_model=DeleteResponse, tags=["history"],
                   summary="Delete an analysis and its stored files",
                   responses={404: {"model": ErrorResponse}})
def delete_analysis(analysis_id: str, service: AnalysisService = Depends(get_service)):
    if not service.delete(analysis_id):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return {"analysis_id": analysis_id, "deleted": True}
