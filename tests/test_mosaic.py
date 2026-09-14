# Arnav Sahu
# 24BCE2976

"""Tests for Layer C Mosaic Risk Engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Finding, ScanMetadata, ScanResponse
from app.adversarial_router import AdversarialResponse
from app.vlm import Observation, VLMAnalysis
from app.mosaic import (
    haversine_km,
    normalize_entity,
    find_convergences,
    find_geo_convergences,
    score_mosaic,
    build_mosaic_report,
)
from app.mosaic_models import MosaicFilePayload, MosaicRequest

client = TestClient(app)


def _sample_scan(filename: str, findings: list[Finding] | None = None, gps: dict | None = None) -> ScanResponse:
    """Helper to create a small ScanResponse fixture."""

    return ScanResponse(
        filename=filename,
        file_type="pdf",
        metadata=ScanMetadata(gps=gps),
        pii_findings=findings or [],
        financial_findings=[],
        redaction_failures=[],
        severity_flags=[],
        overall_priority="low",
        error=None,
    )


def test_normalize_entity() -> None:
    """Verify entity normalization collapses org suffixes, punctuation, and whitespace."""

    assert normalize_entity("Acme Corp.") == "acme"
    assert normalize_entity("ACME, Inc.") == "acme"
    assert normalize_entity("acme limited") == "acme"
    assert normalize_entity("Acme LLC") == "acme"
    assert normalize_entity("Acme Private Limited") == "acme"
    assert normalize_entity("Google LLC") == "google"
    assert normalize_entity("  John   Doe,  ") == "john doe"

    # Distinct entities do not collide
    assert normalize_entity("Acme Corp") != normalize_entity("Beta Corp")
    assert normalize_entity("John Smith") != normalize_entity("Jane Smith")


def test_haversine_distance() -> None:
    """Verify haversine distance calculation."""

    # Same point -> 0 km
    assert haversine_km(12.9716, 77.5946, 12.9716, 77.5946) == pytest.approx(0.0, abs=1e-3)
    # Bangalore MG Road to Cubbon Park (~1.5 km)
    dist = haversine_km(12.9756, 77.6066, 12.9763, 77.5929)
    assert 1.0 < dist < 2.0


def test_entity_convergence_across_two_files() -> None:
    """Correlate matching normalized entities appearing across 2 distinct files."""

    file1 = MosaicFilePayload(
        filename="contract.pdf",
        scan=_sample_scan(
            "contract.pdf",
            findings=[
                Finding(entity_type="ORGANIZATION", text="Acme Corp.", confidence=0.9, priority="low"),
                Finding(entity_type="PERSON", text="Alice Smith", confidence=0.85, priority="low"),
            ],
        ),
    )
    file2 = MosaicFilePayload(
        filename="invoice.pdf",
        scan=_sample_scan(
            "invoice.pdf",
            findings=[
                Finding(entity_type="ORG", text="acme llc", confidence=0.95, priority="low"),
                Finding(entity_type="PERSON", text="Bob Jones", confidence=0.85, priority="low"),
            ],
        ),
    )

    result = build_mosaic_report([file1, file2])
    assert len(result.convergences) == 1
    conv = result.convergences[0]
    assert conv.entity_type == "ORG"
    assert set(conv.source_files) == {"contract.pdf", "invoice.pdf"}
    assert "Acme" in conv.representative_text
    assert result.mosaic_score > 0.0


def test_geo_proximity_convergence_within_threshold() -> None:
    """Flag files within 2.0 km of each other as a geo proximity convergence."""

    # Two locations ~0.5 km apart
    file1 = MosaicFilePayload(
        filename="photo1.jpg",
        scan=_sample_scan("photo1.jpg", gps={"lat": 12.9716, "lon": 77.5946}),
    )
    file2 = MosaicFilePayload(
        filename="photo2.jpg",
        scan=_sample_scan("photo2.jpg", gps={"lat": 12.9750, "lon": 77.5970}),
    )

    result = build_mosaic_report([file1, file2])
    assert len(result.convergences) == 1
    geo_conv = result.convergences[0]
    assert geo_conv.entity_type == "LOCATION_PROXIMITY"
    assert geo_conv.priority == "high"
    assert "photo1.jpg" in geo_conv.source_files
    assert "photo2.jpg" in geo_conv.source_files


def test_geo_divergence_beyond_threshold() -> None:
    """Do not flag files that are far apart geographically."""

    # Bangalore to Delhi (~1700 km apart)
    file1 = MosaicFilePayload(
        filename="bangalore.jpg",
        scan=_sample_scan("bangalore.jpg", gps={"lat": 12.9716, "lon": 77.5946}),
    )
    file2 = MosaicFilePayload(
        filename="delhi.jpg",
        scan=_sample_scan("delhi.jpg", gps={"lat": 28.7041, "lon": 77.1025}),
    )

    result = build_mosaic_report([file1, file2])
    assert len(result.convergences) == 0
    assert result.mosaic_score == 0.0


def test_no_convergence_when_files_share_nothing() -> None:
    """Files with completely disjoint entities yield zero convergences."""

    file1 = MosaicFilePayload(
        filename="file_a.pdf",
        scan=_sample_scan(
            "file_a.pdf",
            findings=[Finding(entity_type="PERSON", text="Alice Green", confidence=0.9, priority="low")],
        ),
    )
    file2 = MosaicFilePayload(
        filename="file_b.pdf",
        scan=_sample_scan(
            "file_b.pdf",
            findings=[Finding(entity_type="PERSON", text="Zack Brown", confidence=0.9, priority="low")],
        ),
    )

    result = build_mosaic_report([file1, file2])
    assert len(result.convergences) == 0
    assert result.mosaic_score == 0.0
    assert result.file_count == 2


def test_vlm_observation_correlates_with_baseline_text() -> None:
    """Correlate an entity in Layer A text with an entity extracted from Layer B VLM observation text."""

    file_doc = MosaicFilePayload(
        filename="resume.pdf",
        scan=_sample_scan(
            "resume.pdf",
            findings=[Finding(entity_type="ORG", text="Stark Industries", confidence=0.9, priority="low")],
        ),
    )
    file_photo = MosaicFilePayload(
        filename="badge.png",
        scan=_sample_scan("badge.png"),
        adversarial=AdversarialResponse(
            filename="badge.png",
            vlm_analysis=VLMAnalysis(
                model_used="qwen2.5vl:7b",
                observations=[
                    Observation(
                        clue_type="badge",
                        description="Subject is wearing an access badge with a Stark Industries logo",
                        possible_inference="Employed by Stark Industries",
                        confidence=0.92,
                    )
                ],
                identity_risk_level="high",
            ),
        ),
    )

    result = build_mosaic_report([file_doc, file_photo])
    assert len(result.convergences) == 1
    conv = result.convergences[0]
    assert conv.entity_type == "ORG"
    assert "Stark" in conv.representative_text
    assert set(conv.source_files) == {"resume.pdf", "badge.png"}
    assert "appears in resume.pdf" in conv.explanation
    assert "is inferred from visual observations in badge.png" in conv.explanation


def test_mosaic_endpoint_validation_requires_two_files() -> None:
    """POST /scan/mosaic rejects requests with fewer than 2 files with HTTP 400."""

    # 0 files
    res0 = client.post("/scan/mosaic", json={"files": []})
    assert res0.status_code == 400
    assert "at least 2" in res0.json()["detail"]

    # 1 file
    res1 = client.post(
        "/scan/mosaic",
        json={"files": [{"filename": "f1.pdf", "scan": _sample_scan("f1.pdf").model_dump()}]},
    )
    assert res1.status_code == 400
    assert "at least 2" in res1.json()["detail"]


def test_mosaic_endpoint_success() -> None:
    """POST /scan/mosaic successfully processes valid 2-file payloads."""

    f1 = _sample_scan(
        "doc1.pdf",
        findings=[Finding(entity_type="EMAIL_ADDRESS", text="alice@example.com", confidence=0.9, priority="medium")],
    )
    f2 = _sample_scan(
        "doc2.pdf",
        findings=[Finding(entity_type="EMAIL_ADDRESS", text="alice@example.com", confidence=0.9, priority="medium")],
    )

    response = client.post(
        "/scan/mosaic",
        json={
            "files": [
                {"filename": "doc1.pdf", "scan": f1.model_dump()},
                {"filename": "doc2.pdf", "scan": f2.model_dump()},
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["file_count"] == 2
    assert len(data["convergences"]) == 1
    assert data["convergences"][0]["entity_type"] == "EMAIL_ADDRESS"
    assert data["convergences"][0]["representative_text"] == "alice@example.com"
    assert data["convergences"][0]["priority"] == "medium"
    assert data["mosaic_score"] == 4.0  # 2.0 (medium) * 2 files
    assert "possible_associations" in data


def test_possible_association_single_person_and_org() -> None:
    """A batch with 1 distinct PERSON in file A and 1 ORG in file B yields 0 convergences and 1 association."""

    file_a = MosaicFilePayload(
        filename="bio.pdf",
        scan=_sample_scan(
            "bio.pdf",
            findings=[Finding(entity_type="PERSON", text="Jane Doe", confidence=0.9, priority="low")],
        ),
    )
    file_b = MosaicFilePayload(
        filename="org_chart.pdf",
        scan=_sample_scan(
            "org_chart.pdf",
            findings=[Finding(entity_type="ORG", text="Globex Corp", confidence=0.95, priority="low")],
        ),
    )

    result = build_mosaic_report([file_a, file_b])
    # Zero convergences because no entity is repeated across files
    assert len(result.convergences) == 0
    # Mosaic score must stay 0.0 (associations do NOT affect the score)
    assert result.mosaic_score == 0.0

    # Exactly 1 possible association
    assert len(result.possible_associations) == 1
    assoc = result.possible_associations[0]
    assert assoc.person_text == "Jane Doe"
    assert "Globex" in assoc.org_text
    assert assoc.org_filename == "org_chart.pdf"
    assert assoc.confidence_label == "low"
    assert "Jane Doe is the only identified individual in this batch" in assoc.explanation
    assert "suggesting a possible association" in assoc.explanation


def test_ambiguity_guard_zero_associations_when_multiple_people() -> None:
    """Ambiguity guard: when 2 distinct people exist in the batch, zero associations are emitted."""

    file_a = MosaicFilePayload(
        filename="person1.pdf",
        scan=_sample_scan(
            "person1.pdf",
            findings=[Finding(entity_type="PERSON", text="Alice Green", confidence=0.9, priority="low")],
        ),
    )
    file_b = MosaicFilePayload(
        filename="person2.pdf",
        scan=_sample_scan(
            "person2.pdf",
            findings=[
                Finding(entity_type="PERSON", text="Bob Brown", confidence=0.9, priority="low"),
                Finding(entity_type="ORG", text="Acme Corp", confidence=0.9, priority="low"),
            ],
        ),
    )

    result = build_mosaic_report([file_a, file_b])
    assert len(result.possible_associations) == 0


def test_ambiguity_guard_zero_associations_when_no_people() -> None:
    """Ambiguity guard: when no PERSON entities exist in the batch, zero associations are emitted."""

    file_a = MosaicFilePayload(
        filename="memo.pdf",
        scan=_sample_scan(
            "memo.pdf",
            findings=[Finding(entity_type="ORG", text="Acme Corp", confidence=0.9, priority="low")],
        ),
    )
    file_b = MosaicFilePayload(
        filename="locations.pdf",
        scan=_sample_scan(
            "locations.pdf",
            findings=[Finding(entity_type="LOCATION", text="Bangalore", confidence=0.9, priority="low")],
        ),
    )

    result = build_mosaic_report([file_a, file_b])
    assert len(result.possible_associations) == 0

