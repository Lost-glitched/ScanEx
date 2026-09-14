# Arnav Sahu
# 24BCE2976

"""Data models for Layer C Mosaic Risk Engine."""

from typing import Any
from pydantic import BaseModel, Field

from app.adversarial_router import AdversarialResponse
from app.models import ScanResponse
from app.priority import Priority


class Convergence(BaseModel):
    """A cross-file correlated risk finding."""

    entity_type: str
    representative_text: str
    source_files: list[str]
    priority: Priority
    explanation: str


class Association(BaseModel):
    """A cross-type PERSON -> ORG heuristic inference."""

    person_text: str
    org_text: str
    org_filename: str
    explanation: str
    confidence_label: str = "low"  # always "low" — heuristic, not evidence


class MosaicFilePayload(BaseModel):
    """Per-file input result containing Layer A baseline and optional Layer B adversarial data."""

    filename: str
    scan: ScanResponse
    adversarial: AdversarialResponse | None = None


class MosaicRequest(BaseModel):
    """Payload sent to the /scan/mosaic endpoint."""

    files: list[MosaicFilePayload]


class MosaicResult(BaseModel):
    """Aggregate output of the cross-file correlation pass."""

    convergences: list[Convergence] = Field(default_factory=list)
    possible_associations: list[Association] = Field(default_factory=list)
    mosaic_score: float = 0.0
    file_count: int = 0
    error: str | None = None
