# Arnav Sahu
# 24BCE2976

"""FastAPI entrypoint for ExposureScan Layer A."""

import asyncio
from contextlib import asynccontextmanager
import logging
import os
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models import ScanMetadata, ScanResponse
from app.scan import scan_bytes, sniff_content_type, sniff_type, warm_analyzer
from app.adversarial_router import router as adversarial_router

LOGGER = logging.getLogger(__name__)
BASELINE_SCAN_TIMEOUT_SECONDS = float(os.getenv("BASELINE_SCAN_TIMEOUT_SECONDS", "30.0"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the Presidio analyzer and spaCy model in background during server startup."""

    def _warm() -> None:
        try:
            LOGGER.info("Pre-warming Presidio analyzer and spaCy model...")
            warm_analyzer()
            LOGGER.info("Presidio analyzer ready.")
        except Exception:
            LOGGER.exception("Failed to pre-warm analyzer during startup.")

    asyncio.create_task(asyncio.to_thread(_warm))
    yield


app = FastAPI(title="ExposureScan Baseline Forensic Scan", version="1.0.0", lifespan=lifespan)
app.include_router(adversarial_router)
MAX_UPLOAD_SIZE = 25 * 1024 * 1024

_cors_origins = {"http://localhost:5173", "http://localhost:3000"}
for configured_origin in os.getenv("CORS_ORIGINS", "").split(","):
    if configured_origin.strip():
        _cors_origins.add(configured_origin.strip())
configured_api_url = os.getenv("VITE_API_BASE_URL", "")
if configured_api_url:
    parsed_api_url = urlparse(configured_api_url)
    if parsed_api_url.scheme and parsed_api_url.netloc:
        _cors_origins.add(f"{parsed_api_url.scheme}://{parsed_api_url.netloc}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extension_type(filename: str) -> str | None:
    """Return the supported family implied by a filename extension."""

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {"jpg": "image", "jpeg": "image", "png": "image", "heic": "image", "docx": "docx", "xlsx": "xlsx", "pptx": "pptx", "pdf": "pdf"}.get(extension)


def _error_response(filename: str, file_type: str, message: str) -> ScanResponse:
    """Build a graceful public error response without exception details."""

    return ScanResponse(filename=filename, file_type=file_type, metadata=ScanMetadata(), pii_findings=[], financial_findings=[], redaction_failures=[], severity_flags=[], error=message)


@app.post("/scan/baseline", response_model=ScanResponse)
async def baseline_scan(file: UploadFile = File(...)) -> ScanResponse | Any:
    """Extract metadata and PII from one uploaded supported file within the configured timeout."""

    filename = file.filename or "unnamed"
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the 25 MB size limit.")
    extension_type = _extension_type(filename)
    detected_type = sniff_type(content, filename)
    if not extension_type:
        raise HTTPException(status_code=415, detail="Unsupported file type. Supported types are JPG, JPEG, PNG, HEIC, DOCX, XLSX, PPTX, and PDF.")
    if detected_type is None:
        if sniff_content_type(content) is not None:
            raise HTTPException(status_code=415, detail="File content does not match its extension or supported container type.")
        return _error_response(filename, extension_type, "The file is corrupted, empty, or cannot be parsed as the declared supported type.")
    try:
        return await asyncio.wait_for(asyncio.to_thread(scan_bytes, content, filename), timeout=BASELINE_SCAN_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        LOGGER.exception("Baseline scan timed out for %s", filename)
        return _error_response(filename, detected_type, f"Baseline scan timed out after {int(BASELINE_SCAN_TIMEOUT_SECONDS)} seconds.")
    except Exception as exc:
        LOGGER.exception("Baseline scan failed for %s", filename)
        return _error_response(filename, detected_type, "The file could not be fully processed; a partial result was not available.")