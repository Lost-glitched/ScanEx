# Arnav Sahu
# 24BCE2976

"""Offline GeoCLIP inference over in-memory image bytes."""

from io import BytesIO
from threading import Lock

import torch
from PIL import Image
from geoclip import GeoCLIP

GEOCLIP_CONFIDENCE_THRESHOLD = 0.15
_MODEL: GeoCLIP | None = None
_MODEL_LOCK = Lock()


def get_model() -> GeoCLIP:
    """Load and cache the locally installed GeoCLIP model on CPU."""

    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                _MODEL = GeoCLIP(from_pretrained=True).eval()
    return _MODEL


def infer_geolocation(image: bytes) -> dict[str, float] | None:
    """Return the top GeoCLIP coordinate only when confidence clears the threshold."""

    model = get_model()
    with Image.open(BytesIO(image)) as source:
        tensor = model.image_encoder.preprocess_image(source.convert("RGB")).to(model.logit_scale.device)
    with torch.no_grad():
        probabilities = model.forward(tensor, model.gps_gallery).softmax(dim=-1)
        top = torch.topk(probabilities, 1, dim=1)
    confidence = float(top.values[0, 0].detach().cpu())
    if confidence <= GEOCLIP_CONFIDENCE_THRESHOLD:
        return None
    coordinates = model.gps_gallery[top.indices[0, 0]].detach().cpu()
    return {"lat": float(coordinates[0]), "lon": float(coordinates[1]), "confidence": confidence}