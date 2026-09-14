# Arnav Sahu
# 24BCE2976

"""Offline Ollama orchestration for adversarial image analysis."""

import asyncio
import json
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

import ollama
from pydantic import BaseModel, Field, ValidationError

LOGGER = logging.getLogger("uvicorn.error")
LOGGER.setLevel(logging.INFO)
OLLAMA_LOCAL_HOST = "http://localhost:11434"
PRIMARY_MODEL = "qwen2.5vl:7b"
FALLBACK_MODEL = "moondream:1.8b"
ADVERSARIAL_PRIMARY_TIMEOUT_SECONDS = 30.0
ADVERSARIAL_FALLBACK_TIMEOUT_SECONDS = 15.0

VLM_SYSTEM_PROMPT = """You are an OSINT (open-source intelligence) analyst helping a privacy audit
tool identify what a determined observer could infer about a person or
organization from a photo, beyond what is obviously visible. You are looking
for incidental, ambient details a normal viewer would skim past.

Examine the image and identify things like: visible ID badges, lanyards, or
name tags; uniforms or insignia; reflections in glasses, windows, screens, or
mirrors that reveal additional detail; documents, whiteboards, screens, or
notes visible in the background; vehicle plates or fleet markings; personal
items that suggest a role, employer, or affiliation; handwriting; any text
that reveals a name, company, or identifiable personal detail.

Do not guess or state any specific geographic location, country, city, or
coordinates, even if architecture, language, or visual style gives you a
hunch. Location inference is handled by a separate specialized system. If
you notice an element that could be a location clue (for example, text in a
specific script, or a distinctive regional style), you may note that a
location-relevant clue exists, but do not offer a location judgment yourself.

Only report things a careful human observer looking closely at the image
could plausibly notice. Do not invent or hallucinate details that are not
visibly present. If the image contains nothing notable beyond its obvious
subject, say so rather than fabricating findings.

Respond ONLY with JSON matching this schema, no markdown fences, no prose
outside the JSON object:
{
  "observations": [
    {
      "clue_type": string,
      "description": string,
      "possible_inference": string,
      "confidence": float between 0 and 1
    }
  ],
  "identity_risk_level": "low" | "medium" | "high"
}
"""


class Observation(BaseModel):
    """One model-observed privacy clue."""

    clue_type: str
    description: str
    possible_inference: str
    confidence: float = Field(ge=0.0, le=1.0)


class VLMPayload(BaseModel):
    """Raw shape returned by the model before server metadata is attached."""

    observations: list[Observation]
    identity_risk_level: str = Field(pattern="^(low|medium|high)$")


class VLMAnalysis(BaseModel):
    """Validated VLM analysis returned to the API."""

    model_used: str
    observations: list[Observation]
    identity_risk_level: str = Field(pattern="^(low|medium|high)$")


def _validate_local_ollama_host() -> None:
    """Reject configured Ollama hosts that are not local loopback addresses."""

    configured = os.getenv("OLLAMA_HOST", OLLAMA_LOCAL_HOST).strip()
    parsed = urlparse(configured if "://" in configured else f"http://{configured}")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("OLLAMA_HOST must point to localhost, 127.0.0.1, or ::1 for offline operation.")


_validate_local_ollama_host()
CLIENT = ollama.Client(host=OLLAMA_LOCAL_HOST)


def _response_content(response: Any) -> str:
    """Extract response text from Ollama response objects or test doubles."""

    if isinstance(response, dict):
        return str(response.get("message", {}).get("content", response.get("response", "")))
    message = getattr(response, "message", None)
    if message is not None:
        return str(getattr(message, "content", ""))
    return str(getattr(response, "response", ""))


def _call_model(model: str, image: bytes) -> VLMAnalysis:
    """Call one local Ollama vision model and validate its JSON response."""

    started_at = time.perf_counter()
    try:
        response = CLIENT.chat(model=model, messages=[{"role": "system", "content": VLM_SYSTEM_PROMPT}, {"role": "user", "content": "Analyze this image for incidental identity and privacy clues.", "images": [image]}], format="json", options={"num_predict": 2048})
        try:
            raw_content = _response_content(response)
            payload = json.loads(raw_content)
            parsed = VLMPayload.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            if isinstance(exc, json.JSONDecodeError):
                LOGGER.debug("Invalid JSON from %s (first 2000 chars): %s", model, raw_content[:2000])
            raise ValueError("Ollama returned invalid adversarial-analysis JSON.") from exc
        return VLMAnalysis(model_used=model, **parsed.model_dump())
    finally:
        LOGGER.info("%s took %.1fs", model, time.perf_counter() - started_at)


async def analyze_with_fallback(image: bytes) -> tuple[VLMAnalysis | None, str | None]:
    """Run Qwen first and fall back to Moondream on error."""

    errors: list[str] = []
    # TEMP: timeouts removed for diagnosis, see fix-adversarial-latency-prompt.md.
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            result = await asyncio.to_thread(_call_model, model, image)
            return result, None
        except Exception as exc:
            LOGGER.exception("Local Ollama model %s failed", model)
            errors.append(f"{model}: {type(exc).__name__}")
    return None, "All local VLM attempts failed (" + ", ".join(errors) + ")."