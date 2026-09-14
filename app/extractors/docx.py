# Arnav Sahu
# 24BCE2976

"""DOCX properties, comments, tracked authors, and visible text extraction."""

from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

from docx import Document

from app.models import ExtractionResult


def _value(value: object) -> str | None:
    """Convert an optional document property into a response-safe string."""

    return value.isoformat() if isinstance(value, datetime) else str(value) if value else None


def extract(content: bytes) -> ExtractionResult:
    """Extract DOCX core properties, visible text, comments, and revision authors."""

    document = Document(BytesIO(content))
    result = ExtractionResult()
    result.text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    properties = document.core_properties
    result.metadata.author = properties.author or None
    result.metadata.last_modified_by = properties.last_modified_by or None
    result.metadata.timestamps = {"created": _value(properties.created), "modified": _value(properties.modified)}
    result.metadata.hidden_content.append({"type": "revision", "location": "core_properties.revision", "summary": str(properties.revision)})
    with ZipFile(BytesIO(content)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        authors = set()
        for marker in ("w:ins w:author=\"", "w:del w:author=\""):
            remainder = xml
            while marker in remainder:
                remainder = remainder.split(marker, 1)[1]
                authors.add(remainder.split("\"", 1)[0])
        if authors:
            result.metadata.hidden_content.append({"type": "tracked_change_authors", "location": "word/document.xml", "summary": ", ".join(sorted(authors))})
        if "commentRangeStart" in xml or "comments.xml" in archive.namelist():
            result.metadata.hidden_content.append({"type": "comments", "location": "word/comments.xml", "summary": "Document comments are present."})
    if result.metadata.author and result.metadata.author not in result.text:
        result.severity_flags.append("author_visible_text_mismatch")
    if result.metadata.last_modified_by and result.metadata.last_modified_by not in result.text:
        result.severity_flags.append("last_modified_by_visible_text_mismatch")
    return result