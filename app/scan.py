# Arnav Sahu
# 24BCE2976

"""Content sniffing, extraction dispatch, Presidio analysis, and masking."""

import re
import os
from io import BytesIO
from zipfile import BadZipFile, ZipFile

import spacy
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SpacyNlpEngine

from app.extractors import docx, image, pdf, pptx, xlsx
from app.models import ExtractionResult, Finding, ScanResponse
from app.recognizers.financial import build_financial_recognizers


def sniff_content_type(content: bytes) -> str | None:
    """Identify a supported type from magic bytes and valid container contents."""

    detected: str | None = None
    if content.startswith(b"%PDF"):
        detected = "pdf"
    elif content.startswith(b"\xff\xd8\xff"):
        detected = "image"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "image"
    elif len(content) > 12 and content[4:8] == b"ftyp" and content[8:12] in {b"heic", b"heix", b"mif1", b"hevc"}:
        detected = "image"
    elif content.startswith(b"PK"):
        try:
            with ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
            if "word/document.xml" in names:
                detected = "docx"
            elif "xl/workbook.xml" in names:
                detected = "xlsx"
            elif "ppt/presentation.xml" in names:
                detected = "pptx"
        except BadZipFile:
            detected = None
    return detected


def sniff_type(content: bytes, filename: str) -> str | None:
    """Identify a supported type when both content and extension agree."""

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    detected = sniff_content_type(content)
    supported_extensions = {"jpg": "image", "jpeg": "image", "png": "image", "heic": "image", "docx": "docx", "xlsx": "xlsx", "pptx": "pptx", "pdf": "pdf"}
    return detected if detected and supported_extensions.get(extension) == detected else None


_ANALYZER: AnalyzerEngine | None = None


def _analyzer() -> AnalyzerEngine:
    """Create the standalone Presidio analyzer once, using the local spaCy model."""

    global _ANALYZER
    if _ANALYZER is None:
        model_name = os.getenv("SPACY_MODEL", "en_core_web_trf")
        if not spacy.util.is_package(model_name):
            raise RuntimeError(f"spaCy model '{model_name}' is not installed locally. ExposureScan runs fully offline and will not auto-download models. Install it first with: python -m spacy download {model_name}")
        nlp_engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": model_name}])
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers()
        for recognizer in build_financial_recognizers():
            registry.add_recognizer(recognizer)
        _ANALYZER = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
    return _ANALYZER


def _financial_entity_type(text: str) -> str | None:
    """Return the custom financial entity matching an analyzer finding."""

    for recognizer in build_financial_recognizers():
        for pattern in recognizer.patterns:
            if re.fullmatch(pattern.regex, text) and recognizer.validate_result(text) is not False:
                return recognizer.supported_entities[0]
    return None


def _findings(result: ExtractionResult) -> tuple[list[Finding], list[Finding]]:
    """Run NER and custom recognizers, including context-aware CVV detection."""

    raw_analyzer_results = _analyzer().analyze(text=result.text, language="en")
    analyzer_results_by_span: dict[tuple[int, int], object] = {}
    for item in raw_analyzer_results:
        span = (item.start, item.end)
        current = analyzer_results_by_span.get(span)
        if current is None or item.score > current.score:
            analyzer_results_by_span[span] = item
    analyzer_results = analyzer_results_by_span.values()
    pii: list[Finding] = []
    financial: list[Finding] = []
    for item in analyzer_results:
        finding = Finding(entity_type=item.entity_type, text=result.text[item.start:item.end], confidence=float(item.score))
        financial_entity = _financial_entity_type(finding.text)
        if financial_entity:
            if financial_entity == "FIN_BANK_ACCOUNT_NUMBER":
                nearby = result.text[max(0, item.start - 40):min(len(result.text), item.end + 40)]
                if not re.search(r"\b(?:account|a/c|iban|bank|hdfc|icici|sbi|axis|kotak)\b", nearby, re.IGNORECASE):
                    continue
            financial.append(finding.model_copy(update={"entity_type": financial_entity}))
        else:
            pii.append(finding)
    cards = [item for item in analyzer_results if item.entity_type == "CREDIT_CARD"]
    for card in cards:
        nearby = result.text[max(0, card.end - 8):min(len(result.text), card.end + 8)]
        match = re.search(r"(?:cvv|cvc|security\s+code)\D{0,5}(\d{3,4})", nearby, re.IGNORECASE)
        if match:
            financial.append(Finding(entity_type="FIN_CVV_NEAR_CARD", text=match.group(1), confidence=0.9))
    return pii, financial


def mask_financial_text(text: str) -> str:
    """Mask a financial match for dashboard display while preserving its shape."""

    compact = re.sub(r"\s+", "", text)
    if len(compact) <= 4:
        return "X" * max(0, len(compact) - 2) + compact[-2:]
    masked = "X" * (len(compact) - 4) + compact[-4:]
    groups = []
    while masked:
        groups.append(masked[:4])
        masked = masked[4:]
    return " ".join(groups)


def scan_bytes(content: bytes, filename: str) -> ScanResponse:
    """Scan one supported file and return a public response with masked finance findings."""

    file_type = sniff_type(content, filename)
    if not file_type:
        raise ValueError("Unsupported or renamed file: extension and file content do not identify a supported type.")
    extractor = {"image": image.extract, "docx": docx.extract, "xlsx": xlsx.extract, "pptx": pptx.extract, "pdf": pdf.extract}[file_type]
    result = extractor(content)
    pii, financial = _findings(result)
    severity_flags = list(dict.fromkeys(result.severity_flags + (["financial"] if financial else [])))
    public_financial = [finding.model_copy(update={"text": mask_financial_text(finding.text)}) for finding in financial]
    return ScanResponse(filename=filename, file_type=file_type, metadata=result.metadata, pii_findings=pii, financial_findings=public_financial, redaction_failures=result.redaction_failures, severity_flags=severity_flags)