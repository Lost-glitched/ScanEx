# Arnav Sahu
# 24BCE2976

"""FastAPI router for Layer C Mosaic Risk Engine."""

import logging
from fastapi import APIRouter, HTTPException

from app.mosaic import build_mosaic_report
from app.mosaic_models import MosaicRequest, MosaicResult

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.post("/scan/mosaic", response_model=MosaicResult)
async def scan_mosaic(request: MosaicRequest) -> MosaicResult:
    """Run stateless in-memory cross-file correlation over already scanned file results."""

    if len(request.files) < 2:
        raise HTTPException(
            status_code=400,
            detail="Mosaic correlation requires at least 2 scanned files.",
        )

    try:
        return build_mosaic_report(request.files)
    except Exception as exc:
        LOGGER.exception("Mosaic analysis failed unexpectedly: %s", exc)
        return MosaicResult(
            convergences=[],
            mosaic_score=0.0,
            file_count=len(request.files),
            error="Mosaic analysis failed to correlate file findings.",
        )
