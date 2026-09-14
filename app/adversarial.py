# Arnav Sahu
# 24BCE2976

"""Concurrent orchestration for the independent adversarial scan layer."""

import asyncio
import logging
import time
from typing import Any

from app import geolocation, vlm

LOGGER = logging.getLogger("uvicorn.error")
LOGGER.setLevel(logging.INFO)


async def run_adversarial_scan(image: bytes) -> dict[str, Any]:
    """Run local VLM and GeoCLIP analysis concurrently with graceful degradation."""

    started_at = time.perf_counter()
    try:
        vlm_task = vlm.analyze_with_fallback(image)
        geo_task = asyncio.to_thread(geolocation.infer_geolocation, image)
        vlm_result, geo_result = await asyncio.gather(vlm_task, geo_task, return_exceptions=True)
        errors: list[str] = []
        analysis = None
        location = None
        if isinstance(vlm_result, Exception):
            LOGGER.exception("Adversarial VLM orchestration failed", exc_info=vlm_result)
            errors.append("VLM analysis failed.")
        else:
            analysis, error = vlm_result
            if error:
                errors.append(error)
        if isinstance(geo_result, Exception):
            LOGGER.exception("GeoCLIP inference failed", exc_info=geo_result)
            errors.append("Geolocation inference failed.")
        else:
            location = geo_result
        severity_flags: list[str] = []
        if analysis and analysis.identity_risk_level == "high":
            severity_flags.append("high_identity_risk")
        if location is not None:
            severity_flags.append("geolocation_inferred")
        return {"vlm_analysis": analysis, "geolocation": location, "severity_flags": severity_flags, "error": " ".join(errors) if errors else None}
    finally:
        LOGGER.info("run_adversarial_scan took %.1fs", time.perf_counter() - started_at)