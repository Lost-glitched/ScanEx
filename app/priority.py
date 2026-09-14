# Arnav Sahu
# 24BCE2976

"""Priority mapping for detected entity types."""

from typing import Literal

Priority = Literal["low", "medium", "high"]

HIGH = {
    "FIN_BANK_ACCOUNT_NUMBER", "FIN_AADHAAR", "FIN_PAN_CARD",
    "FIN_IFSC_CODE", "FIN_UPI_ID", "FIN_CVV_NEAR_CARD",
    "CREDIT_CARD", "US_SSN", "US_BANK_NUMBER", "US_PASSPORT",
    "IBAN_CODE", "MEDICAL_LICENSE",
}

MEDIUM = {
    "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION", "IP_ADDRESS",
    "US_DRIVER_LICENSE", "DATE_TIME", "NRP",
}

PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def priority_for_entity(entity_type: str) -> Priority:
    """Map an entity type string to a priority level."""

    if entity_type in HIGH:
        return "high"
    if entity_type in MEDIUM:
        return "medium"
    return "low"  # PERSON, ORG, generic/uncategorized entities


def max_priority(*priorities: Priority) -> Priority:
    """Return the highest priority from the given values."""

    if "high" in priorities:
        return "high"
    if "medium" in priorities:
        return "medium"
    return "low"
