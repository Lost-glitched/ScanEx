# Arnav Sahu
# 24BCE2976

"""Shared internal and response models for baseline scanning."""

from typing import Any

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A detected entity and its analyzer confidence."""

    entity_type: str
    text: str
    confidence: float


class RedactionFailure(BaseModel):
    """Text recovered from beneath a probable PDF redaction box."""

    page: int
    recovered_text: str


class ScanMetadata(BaseModel):
    """Metadata fields shared by all file types."""

    gps: dict[str, float] | None = None
    device: str | None = None
    timestamps: dict[str, str | None] = Field(default_factory=lambda: {"created": None, "modified": None})
    author: str | None = None
    last_modified_by: str | None = None
    hidden_content: list[dict[str, str]] = Field(default_factory=list)


class ScanResponse(BaseModel):
    """Public baseline scan response."""

    filename: str
    file_type: str
    metadata: ScanMetadata
    pii_findings: list[Finding]
    financial_findings: list[Finding]
    redaction_failures: list[RedactionFailure]
    severity_flags: list[str]
    error: str | None = None


class ExtractionResult:
    """Internal extractor output, including text used only for analysis."""

    def __init__(self) -> None:
        self.metadata = ScanMetadata()
        self.text = ""
        self.redaction_failures: list[RedactionFailure] = []
        self.severity_flags: list[str] = []
        self.extra: dict[str, Any] = {}