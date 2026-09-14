# ExposureScan

ExposureScan Layer A is a standalone FastAPI baseline forensic scanner. It extracts metadata, hidden content, PII, financial identifiers, and recoverable PDF redactions without using VLMs, embeddings, or external vision models.

## Supported files

- JPEG, PNG, and HEIC images
- DOCX documents
- XLSX spreadsheets, including hidden and very-hidden sheets
- PPTX presentations, including speaker notes and hidden slides
- PDFs, including metadata, incremental-update, and redaction-failure checks

## Run locally

The project expects the dependencies listed in the project environment, including spaCy's `en_core_web_trf` model.

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000` and interactive docs are at `/docs`.

## Baseline scan

```powershell
curl.exe -X POST http://127.0.0.1:8000/scan/baseline `
  -F "file=@path\to\evidence.pdf"
```

The endpoint returns a strict baseline result containing metadata, general PII findings, masked financial findings, redaction failures, and severity flags. Financial values are kept unmasked only inside the server-side scan operation; dashboard-facing responses mask them.

Unsupported or content-mismatched files return HTTP 415. Corrupt or password-protected supported files return HTTP 200 with an `error` field so this layer can act as the system fallback.

## Tests

```powershell
python -m pytest -q
```

The tests cover generated real JPEG, DOCX, XLSX, and PDF fixtures, financial masking, checksum-aware Aadhaar detection, unsupported files, and graceful corruption handling.