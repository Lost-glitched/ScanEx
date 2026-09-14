# Arnav Sahu
# 24BCE2976

"""Unit tests for the offline adversarial inference layer."""

import asyncio
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app import geolocation, vlm
from app.main import app

client = TestClient(app)


def _png_bytes() -> bytes:
    """Create a small valid PNG fixture entirely in memory."""

    stream = BytesIO()
    Image.new("RGB", (2, 2), "white").save(stream, "PNG")
    return stream.getvalue()


def _analysis(model: str, risk: str = "low") -> vlm.VLMAnalysis:
    """Create a validated mocked VLM analysis."""

    return vlm.VLMAnalysis(model_used=model, observations=[], identity_risk_level=risk)


def test_qwen_success_and_model_recorded(monkeypatch: object) -> None:
    """The primary local model is used when it succeeds."""

    async def fake_vlm(image: bytes) -> tuple[vlm.VLMAnalysis, None]:
        return _analysis(vlm.PRIMARY_MODEL, "high"), None

    monkeypatch.setattr(vlm, "analyze_with_fallback", fake_vlm)
    monkeypatch.setattr(geolocation, "infer_geolocation", lambda image: None)
    response = client.post("/scan/adversarial", files={"file": ("photo.png", _png_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["vlm_analysis"]["model_used"] == vlm.PRIMARY_MODEL
    assert response.json()["severity_flags"] == ["high_identity_risk"]


def test_primary_timeout_uses_fallback(monkeypatch: object) -> None:
    """A primary timeout causes the fallback model to be attempted."""

    calls: list[str] = []

    def fake_call(model: str, image: bytes) -> vlm.VLMAnalysis:
        calls.append(model)
        if model == vlm.PRIMARY_MODEL:
            raise asyncio.TimeoutError()
        return _analysis(model)

    monkeypatch.setattr(vlm, "_call_model", fake_call)
    result, error = asyncio.run(vlm.analyze_with_fallback(b"image"))
    assert result is not None and result.model_used == vlm.FALLBACK_MODEL
    assert error is None
    assert calls == [vlm.PRIMARY_MODEL, vlm.FALLBACK_MODEL]


def test_both_vlm_fail_returns_degraded_200(monkeypatch: object) -> None:
    """Two local VLM failures return HTTP 200 with a clear error."""

    async def fake_vlm(image: bytes) -> tuple[None, str]:
        return None, "All local VLM attempts failed."

    monkeypatch.setattr(vlm, "analyze_with_fallback", fake_vlm)
    monkeypatch.setattr(geolocation, "infer_geolocation", lambda image: None)
    response = client.post("/scan/adversarial", files={"file": ("photo.png", _png_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["vlm_analysis"] is None
    assert "failed" in response.json()["error"]


def test_geolocation_threshold(monkeypatch: object) -> None:
    """GeoCLIP results are retained only above the configured threshold."""

    monkeypatch.setattr(vlm, "analyze_with_fallback", lambda image: asyncio.sleep(0, result=(None, None)))
    monkeypatch.setattr(geolocation, "infer_geolocation", lambda image: None)
    response = client.post("/scan/adversarial", files={"file": ("photo.png", _png_bytes(), "image/png")})
    assert response.json()["geolocation"] is None
    location = {"lat": 12.0, "lon": 77.0, "confidence": geolocation.GEOCLIP_CONFIDENCE_THRESHOLD + 0.01}
    monkeypatch.setattr(geolocation, "infer_geolocation", lambda image: location)
    response = client.post("/scan/adversarial", files={"file": ("photo.png", _png_bytes(), "image/png")})
    assert response.json()["geolocation"] == location
    assert "geolocation_inferred" in response.json()["severity_flags"]


def test_ollama_connection_failure_does_not_crash(monkeypatch: object) -> None:
    """A connection refusal is represented as a degraded 200 response."""

    async def failed_vlm(image: bytes) -> tuple[None, str]:
        raise ConnectionError("connection refused")

    monkeypatch.setattr(vlm, "analyze_with_fallback", failed_vlm)
    monkeypatch.setattr(geolocation, "infer_geolocation", lambda image: None)
    response = client.post("/scan/adversarial", files={"file": ("photo.png", _png_bytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["vlm_analysis"] is None
    assert response.json()["error"] == "VLM analysis failed."


def test_unsupported_image_is_415() -> None:
    """Unsupported extensions and non-image content are rejected."""

    response = client.post("/scan/adversarial", files={"file": ("photo.txt", b"not image", "text/plain")})
    assert response.status_code == 415