"""DeepTrace AI backend entry point.

Run from the ``backend`` folder:  uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router, root_router
from app.config import APP_NAME, APP_VERSION, Settings
from app.database import AnalysisRepository
from app.services.analysis_service import AnalysisService

logger = logging.getLogger("deeptrace")

DESCRIPTION = (
    "Explainable digital image forensics. Upload a suspicious image and receive metadata findings, "
    "Error Level Analysis, image statistics, AI-detector status, content-credential detection and a PDF report. "
    "DeepTrace AI is an investigative aid, not an infallible authenticity verifier."
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    repo = AnalysisRepository(settings.db_path)
    service = AnalysisService(settings, repo)
    service.ensure_storage()
    repo.init()
    removed = service.cleanup_expired()
    if removed:
        logger.info("Retention cleanup removed %d old analyses", removed)

    app = FastAPI(title=f"{APP_NAME} API", description=DESCRIPTION, version=APP_VERSION)
    app.state.settings = settings
    app.state.service = service

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception):
        logger.error("Unhandled error: %s", type(exc).__name__)  # never log image content
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    app.include_router(root_router)
    app.include_router(api_router)
    return app


app = create_app()
