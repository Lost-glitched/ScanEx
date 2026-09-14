# Arnav Sahu
# 24BCE2976

"""PDF metadata, revision, and recoverable-redaction extraction."""

import re
from io import BytesIO

import pdfplumber
from pypdf import PdfReader

from app.models import ExtractionResult, RedactionFailure


def _dark(color: object) -> bool:
    """Return whether a pdfplumber fill color appears black or dark."""

    if color is None:
        return False
    values = color if isinstance(color, (tuple, list)) else (color,)
    try:
        return sum(float(value) for value in values[:3]) / min(3, len(values)) < 0.25
    except (TypeError, ValueError):
        return False


def extract(content: bytes) -> ExtractionResult:
    """Extract PDF metadata and flag text hidden below dark filled rectangles."""

    reader = PdfReader(BytesIO(content))
    result = ExtractionResult()
    metadata = reader.metadata or {}
    result.metadata.author = metadata.get("/Author") or None
    result.metadata.timestamps = {"created": str(metadata.get("/CreationDate")) if metadata.get("/CreationDate") else None, "modified": str(metadata.get("/ModDate")) if metadata.get("/ModDate") else None}
    result.metadata.hidden_content.append({"type": "producer", "location": "PDF metadata", "summary": str(metadata.get("/Producer"))}) if metadata.get("/Producer") else None
    result.text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(re.findall(rb"startxref", content)) > 1:
        result.metadata.hidden_content.append({"type": "incremental_updates", "location": "PDF xref", "summary": "Multiple xref sections indicate prior revisions may remain embedded."})
        result.severity_flags.append("pdf_incremental_updates")
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for rectangle in page.rects:
                fill = rectangle.get("non_stroking_color") or rectangle.get("fill")
                if not _dark(fill):
                    continue
                bbox = (rectangle["x0"], rectangle["top"], rectangle["x1"], rectangle["bottom"])
                recovered = page.crop(bbox, strict=False).extract_text() or ""
                if recovered.strip():
                    result.redaction_failures.append(RedactionFailure(page=page_number, recovered_text=recovered.strip()))
                    result.severity_flags.append("redaction_failure")
    return result