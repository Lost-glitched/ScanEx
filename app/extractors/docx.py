# Arnav Sahu
# 24BCE2976

"""DOCX properties, comments, tracked authors, and visible text extraction."""

from datetime import datetime
from io import BytesIO
from xml.etree import ElementTree
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
    result.text = "\n".join(
        "".join(run.text or "" for run in paragraph.runs if run.font.hidden is not True)
        for paragraph in document.paragraphs
    )
    properties = document.core_properties
    result.metadata.author = properties.author or None
    result.metadata.last_modified_by = properties.last_modified_by or None
    result.metadata.timestamps = {"created": _value(properties.created), "modified": _value(properties.modified)}
    result.metadata.hidden_content.append({"type": "revision", "location": "core_properties.revision", "summary": str(properties.revision)})
    with ZipFile(BytesIO(content)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        document_root = ElementTree.fromstring(xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        hidden_text = "".join(
            text_node.text or ""
            for run in document_root.findall(".//w:r", namespace)
            if run.find("w:rPr/w:vanish", namespace) is not None
            for text_node in run.findall(".//w:t", namespace)
        )
        if hidden_text and hidden_text not in result.text:
            result.metadata.hidden_content.append({"type": "hidden_text_run", "location": "word/document.xml", "summary": hidden_text})
            result.severity_flags.append("hidden_text_run")
        authors = {
            author
            for revision in document_root.findall(".//w:ins", namespace) + document_root.findall(".//w:del", namespace)
            if (author := revision.get(f"{{{namespace['w']}}}author"))
        }
        if authors:
            result.metadata.hidden_content.append({"type": "tracked_change_authors", "location": "word/document.xml", "summary": ", ".join(sorted(authors))})
        if "word/comments.xml" in archive.namelist():
            comments_root = ElementTree.fromstring(archive.read("word/comments.xml"))
            comments = comments_root.findall(".//w:comment", namespace)
            for comment in comments:
                author = comment.get(f"{{{namespace['w']}}}author") or "Unknown author"
                text = "".join(text_node.text or "" for text_node in comment.findall(".//w:t", namespace))
                result.metadata.hidden_content.append({"type": "comment", "location": "word/comments.xml", "summary": f"{author}: {text}"})
        elif "commentRangeStart" in xml:
            result.metadata.hidden_content.append({"type": "comments", "location": "word/comments.xml", "summary": "Document comments are present."})
    if result.metadata.author and result.metadata.author not in result.text:
        result.severity_flags.append("author_visible_text_mismatch")
    if result.metadata.last_modified_by and result.metadata.last_modified_by not in result.text:
        result.severity_flags.append("last_modified_by_visible_text_mismatch")
    return result