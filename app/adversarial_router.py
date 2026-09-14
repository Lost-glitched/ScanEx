# Arnav Sahu
# 24BCE2976

"""FastAPI route for the independent adversarial inference layer."""

import logging
import time
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.adversarial import run_adversarial_scan
from app.vlm import VLMAnalysis

router = APIRouter()
LOGGER = logging.getLogger(__name__)


class AdversarialResponse(BaseModel):
    """Public response shape for an adversarial image scan."""

    filename: str
    vlm_analysis: VLMAnalysis | None = None
    geolocation: dict[str, float] | None = None
    severity_flags: list[str] = Field(default_factory=list)
    error: str | None = None


def _image_content_type(content: bytes) -> str | None:
    """Detect supported image formats from magic bytes without trusting names."""

    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(content) > 12 and content[4:8] == b"ftyp" and content[8:12] in {b"heic", b"heix", b"mif1", b"hevc"}:
        return "heic"
    return None


def _extension_type(filename: str) -> str | None:
    """Detect the supported image family from a filename extension."""

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return extension if extension in {"jpg", "jpeg", "png", "heic"} else None


@router.post("/scan/adversarial", response_model=AdversarialResponse)
async def adversarial_scan(file: UploadFile = File(...)) -> AdversarialResponse:
    """Run local VLM and GeoCLIP inference over one uploaded image."""

    filename = file.filename or "unnamed"
    content = await file.read()
    extension_type = _extension_type(filename)
    content_type = _image_content_type(content)
    if extension_type is None:
        raise HTTPException(status_code=415, detail="Unsupported image type. Supported types are JPG, JPEG, PNG, and HEIC.")
    if content_type is None or (extension_type in {"jpg", "jpeg"} and content_type != "jpg") or extension_type != "jpeg" and extension_type != content_type:
        raise HTTPException(status_code=415, detail="Image content does not match its extension or supported image type.")
    started_at = time.perf_counter()
    try:
        # TEMP: request timeout removed for diagnosis, see fix-adversarial-latency-prompt.md.
        result = await run_adversarial_scan(content)
        LOGGER.info(
            "Adversarial scan completed for %s in %.2fs",
            filename,
            time.perf_counter() - started_at,
        )
        return AdversarialResponse(filename=filename, **result)
    except Exception:
        elapsed = time.perf_counter() - started_at
        LOGGER.exception("Adversarial scan failed for %s after %.2fs", filename, elapsed)
        return AdversarialResponse(
            filename=filename,
            error="Adversarial scan failed while running local inference.",
        )