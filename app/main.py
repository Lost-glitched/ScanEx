# Arnav Sahu
# 24BCE2976

"""FastAPI entrypoint for ExposureScan Layer A."""

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.models import ScanMetadata, ScanResponse
from app.scan import scan_bytes, sniff_content_type, sniff_type
from app.adversarial_router import router as adversarial_router

LOGGER = logging.getLogger(__name__)
app = FastAPI(title="ExposureScan Baseline Forensic Scan", version="1.0.0")
app.include_router(adversarial_router)


def _extension_type(filename: str) -> str | None:
    """Return the supported family implied by a filename extension."""

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {"jpg": "image", "jpeg": "image", "png": "image", "heic": "image", "docx": "docx", "xlsx": "xlsx", "pptx": "pptx", "pdf": "pdf"}.get(extension)


def _error_response(filename: str, file_type: str, message: str) -> ScanResponse:
    """Build a graceful public error response without exception details."""

    return ScanResponse(filename=filename, file_type=file_type, metadata=ScanMetadata(), pii_findings=[], financial_findings=[], redaction_failures=[], severity_flags=[], error=message)


@app.post("/scan/baseline", response_model=ScanResponse)
async def baseline_scan(file: UploadFile = File(...)) -> ScanResponse | Any:
    """Extract metadata and PII from one uploaded supported file within ten seconds."""

    filename = file.filename or "unnamed"
    content = await file.read()
    extension_type = _extension_type(filename)
    detected_type = sniff_type(content, filename)
    if not extension_type:
        raise HTTPException(status_code=415, detail="Unsupported file type. Supported types are JPG, JPEG, PNG, HEIC, DOCX, XLSX, PPTX, and PDF.")
    if detected_type is None:
        if sniff_content_type(content) is not None:
            raise HTTPException(status_code=415, detail="File content does not match its extension or supported container type.")
        return _error_response(filename, extension_type, "The file is corrupted, empty, or cannot be parsed as the declared supported type.")
    try:
        return await asyncio.wait_for(asyncio.to_thread(scan_bytes, content, filename), timeout=10.0)
    except asyncio.TimeoutError:
        LOGGER.exception("Baseline scan timed out for %s", filename)
        return _error_response(filename, detected_type, "Baseline scan timed out after 10 seconds.")
    except Exception as exc:
        LOGGER.exception("Baseline scan failed for %s", filename)
        return _error_response(filename, detected_type, "The file could not be fully processed; a partial result was not available.")