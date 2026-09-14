# Arnav Sahu
# 24BCE2976

"""Presidio recognizers for Indian and context-sensitive financial data."""

import re

from presidio_analyzer import Pattern, PatternRecognizer


def _aadhaar_checksum(value: str) -> bool:
    """Validate an Aadhaar number with the Verhoeff checksum."""

    digits = re.sub(r"\s", "", value)
    if len(digits) != 12 or not digits.isdigit() or len(set(digits)) == 1:
        return False
    multiplication = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
    )
    permutation = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
    )
    checksum = 0
    for position, digit in enumerate(reversed(digits)):
        checksum = multiplication[checksum][permutation[position % 8][int(digit)]]
    return checksum == 0


class AadhaarRecognizer(PatternRecognizer):
    """Recognize formatted or unformatted Aadhaar values after checksum validation."""

    def __init__(self) -> None:
        super().__init__(supported_entity="FIN_AADHAAR", patterns=[Pattern("aadhaar", r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", 0.95)])

    def validate_result(self, pattern_text: str) -> bool:
        """Reject generic twelve-digit values that fail the Aadhaar checksum."""

        return _aadhaar_checksum(pattern_text)


def build_financial_recognizers() -> list[PatternRecognizer]:
    """Build all custom financial recognizers used by the baseline pass."""

    return [
        PatternRecognizer("FIN_PAN_CARD", patterns=[Pattern("pan", r"\b[A-Z]{5}\d{4}[A-Z]\b", 0.95)]),
        AadhaarRecognizer(),
        PatternRecognizer("FIN_IFSC_CODE", patterns=[Pattern("ifsc", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 0.9)]),
        PatternRecognizer(
            "FIN_BANK_ACCOUNT_NUMBER",
            patterns=[Pattern("account", r"\b\d{9,18}\b", 0.7)],
            context=["account", "a/c", "iban", "bank", "hdfc", "icici", "sbi", "axis", "kotak"],
        ),
        PatternRecognizer("FIN_UPI_ID", patterns=[Pattern("upi", r"(?i)\b[\w.\-]+@(?:okhdfcbank|okicici|oksbi|ybl|paytm|upi|ibl|axl|apl)\b", 0.95)]),
    ]