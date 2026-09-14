# Arnav Sahu
# 24BCE2976

"""EXIF extraction for image files."""

from io import BytesIO

import exifread

from app.models import ExtractionResult


def _decimal(values: object, reference: object) -> float:
    """Convert EXIF degrees/minutes/seconds into signed decimal degrees."""

    parts = [float(item.num) / float(item.den) for item in values.values]
    result = parts[0] + parts[1] / 60 + parts[2] / 3600
    return -result if str(reference) in {"S", "W"} else result


def extract(content: bytes) -> ExtractionResult:
    """Extract GPS, device, time, and editing-history EXIF tags."""

    result = ExtractionResult()
    tags = exifread.process_file(BytesIO(content), details=False)
    result.text = " ".join(str(value) for value in tags.values())
    make = tags.get("Image Make")
    model = tags.get("Image Model")
    result.metadata.device = " ".join(str(value) for value in (make, model) if value) or None
    timestamp = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
    result.metadata.timestamps = {"created": str(timestamp) if timestamp else None, "modified": None}
    software = tags.get("Image Software") or tags.get("EXIF Software")
    if software:
        result.metadata.hidden_content.append({"type": "editing_history", "location": "EXIF Software", "summary": str(software)})
    latitude = tags.get("GPS GPSLatitude")
    longitude = tags.get("GPS GPSLongitude")
    if latitude and longitude:
        result.metadata.gps = {"lat": _decimal(latitude, tags.get("GPS GPSLatitudeRef", "N")), "lon": _decimal(longitude, tags.get("GPS GPSLongitudeRef", "E"))}
    elif tags:
        result.metadata.hidden_content.append({"type": "gps_absent_exif_intact", "location": "EXIF", "summary": "EXIF metadata is present but GPS tags are absent; location data may have been stripped."})
        result.severity_flags.append("gps_absent_exif_intact")
    return result