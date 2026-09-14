# ScanEx

ScanEx is a local backend and frontend for forensic file scanning. Layer A extracts metadata, hidden content, PII, financial identifiers, and recoverable PDF redactions. Layer B adds offline Ollama VLM analysis and local GeoCLIP inference for images.

## Supported files

- JPEG and PNG images
- HEIC containers are recognized, but EXIF extraction is reported as unsupported without a HEIF decoder
- DOCX documents
- XLSX spreadsheets, including hidden and very-hidden sheets
- PPTX presentations, including speaker notes and hidden slides
- PDFs, including metadata, incremental-update, and redaction-failure checks

## Backend install

```powershell
pip install -r requirements.txt
```

The backend requires the `en_core_web_trf` spaCy model to already be installed locally. ScanEx never downloads models at request time:

```powershell
python -m spacy download en_core_web_trf
```

## Run locally

Set `SPACY_MODEL` only when selecting another model that is already installed locally. Missing models fail clearly rather than triggering a network download.

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000` and interactive docs are at `/docs`.

## Frontend

The ScanEx frontend lives in `frontend/` and calls the backend through `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`.

Run both servers in separate terminals:

```powershell
run-dev.bat
```

Or start them manually:

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

The frontend supports the real baseline and adversarial scan endpoints. Resolve, commit, scan history, authentication, and server-backed report export remain Phase 2 capabilities; see [frontend/README.md](frontend/README.md).

## Baseline scan

```powershell
curl.exe -X POST http://127.0.0.1:8000/scan/baseline `
  -F "file=@path\to\evidence.pdf"
```

The endpoint returns a strict baseline result containing metadata, general PII findings, masked financial findings, redaction failures, and severity flags. Financial values are kept unmasked only inside the server-side scan operation; dashboard-facing responses mask them.

Uploads larger than 25 MB are rejected with HTTP 413.

Unsupported or content-mismatched files return HTTP 415. Corrupt or password-protected supported files return HTTP 200 with an `error` field so this layer can act as the system fallback.

## Tests

```powershell
python -m pytest -q
```

The tests cover generated real JPEG, DOCX, XLSX, and PDF fixtures, financial masking, checksum-aware Aadhaar detection, unsupported files, and graceful corruption handling.