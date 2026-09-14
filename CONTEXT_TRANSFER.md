# ExposureScan Context Transfer

Updated: 2026-09-14

## Repository State

- Workspace: `C:\dev\exposurescan`
- Branch: `main`
- Remote: `https://github.com/Lost-glitched/ScanEx.git`
- Working tree: clean
- `main` is synchronized with `origin/main`
- Latest commit: `0fa1eff Fix forensic findings and optimize image scans`

Recent commits:

- `0fa1eff` Fix forensic findings and optimize image scans
- `97c5a2f` Fix VLM response validation and truncation
- `56bf63a` Wire ScanX frontend and document local development
- `b545dbe` Merge main into layer-b; fix spaCy model default to stay offline

## Project Structure

### Backend

- `app/main.py`: FastAPI app, `/scan/baseline`, `/scan/adversarial` router registration, CORS, 25 MB baseline upload limit.
- `app/scan.py`: Layer A dispatcher, content sniffing, Presidio analysis, masking, spaCy offline model guard, bank-account context filtering, span deduplication.
- `app/extractors/image.py`: EXIF/GPS/device/timestamp extraction.
- `app/extractors/docx.py`: DOCX properties, hidden text, tracked-change authors, comments.
- `app/extractors/xlsx.py`: workbook properties, hidden/very-hidden sheets, defined names, comments.
- `app/extractors/pptx.py`: presentation properties, speaker notes, hidden slides.
- `app/extractors/pdf.py`: PDF metadata, incremental updates, redaction recovery.
- `app/recognizers/financial.py`: PAN, Aadhaar, IFSC, bank account, UPI recognizers.
- `app/vlm.py`: local Ollama VLM orchestration and prompt.
- `app/geolocation.py`: local GeoCLIP inference.
- `app/adversarial.py`: concurrent VLM/GeoCLIP orchestration.
- `app/adversarial_router.py`: `/scan/adversarial` endpoint.

### Frontend

- `frontend/src/api/scanClient.ts`: typed baseline/adversarial API client.
- `frontend/src/types.ts`: backend-aligned TypeScript response types.
- `frontend/src/App.tsx`: real staged files, scan results, local review state.
- `frontend/src/components/ScreenUpload.tsx`: real browser file selection/drop.
- `frontend/src/components/ScreenPipeline.tsx`: per-file scan flow, counts, engine cards, response logs.
- `frontend/src/components/ScreenAudit.tsx`: baseline and adversarial findings list.
- `frontend/src/components/AuditReportModal.tsx`: local JSON export of actual session responses; already included adversarial data.
- `run-dev.bat`: starts backend and frontend in separate Windows terminals.

## Important Constraints

- Fully offline backend: no cloud APIs.
- Ollama must remain local-only (`localhost`, `127.0.0.1`, or `::1`).
- spaCy defaults to locally installed `en_core_web_trf`; missing models raise immediately instead of auto-downloading.
- Do not modify VLM/GeoCLIP model choice or fallback order without explicit instruction.
- Current diagnostic state intentionally has no adversarial timeouts:
  - `asyncio.wait_for` is not active in `app/vlm.py` or `app/adversarial_router.py`.
  - `AbortController` is not active in the frontend client.
  - `ADVERSARIAL_PRIMARY_TIMEOUT_SECONDS` and `ADVERSARIAL_FALLBACK_TIMEOUT_SECONDS` remain defined but unused.
  - Preserve the comments: `# TEMP: timeouts removed for diagnosis, see fix-adversarial-latency-prompt.md.`
- Do not touch `app/main.py` unless explicitly requested.
- `AuditReportModal.tsx` already exports adversarial data and should not be changed casually.

## Current VLM Behavior

- `_call_model()` validates raw Ollama output with `VLMPayload`, then attaches `model_used` to create `VLMAnalysis`.
- Ollama uses `options={"num_predict": VLM_NUM_PREDICT}` with `VLM_NUM_PREDICT = 768`.
- Oversized images are resized in memory to a maximum long side of 1024px before VLM calls.
- Timing logs use Uvicorn's console logger:
  - VLM model timing
  - GeoCLIP timing
  - total adversarial scan timing
- JSON decode failures log only the first 2000 response characters at DEBUG level.

## Manual Scan Results

Temporary generated fixtures were used because no local camera photos were available. They were created under the system temp directory and were not committed.

- `photo-large.png`: original `3000x2000`, `23,239 B`; resized `1024x683`, `4,171 B`; Qwen `15.8s`; GeoCLIP `22.1s`; total `22.2s`; HTTP total `22.71s`.
- `photo-medium.jpg`: original `2048x1536`, `50,558 B`; resized `1024x768`, `13,166 B`; Qwen `4.4s`; GeoCLIP `13.3s`; total `13.4s`; HTTP total `13.39s`.
- `photo-small.jpg`: original `800x600`, `8,886 B`; unchanged dimensions; output `8,887 B`; Qwen `4.6s`; GeoCLIP `13.5s`; total `13.5s`; HTTP total `13.53s`.

All three returned HTTP 200, Qwen succeeded, Moondream fallback was not used, and GeoCLIP returned no above-threshold location for the generated fixtures.

During the large-image request, `ollama ps` showed:

```text
NAME            ID              SIZE    PROCESSOR    CONTEXT    UNTIL
qwen2.5vl:7b    5ced39dfa4ba    5.5 GB  100% GPU     4096       4 minutes from now
```

## Test Status

Latest command:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

Result:

```text
24 passed, 1 skipped, 4 warnings
```

The skipped test is `test_adversarial_route_times_out_gracefully`, intentionally skipped because adversarial request timeouts are disabled for the diagnostic phase.

Frontend validation previously passed:

```powershell
cd frontend
npm run lint
npm run build
```

## Phase 2 / Deferred Backend Work

- Persist finding resolution/redaction endpoint.
- Commit-to-ingestion endpoint.
- Server-backed audit report endpoint.
- Scan history endpoint and UI.
- Authentication and authorization.
- True request cancellation for the frontend Cancel Scan button.
- Adversarial latency optimization beyond the current 1024px downscale and `num_predict=768` tuning.
- Investigate any future malformed/truncated Ollama output if it recurs.
- GeoCLIP remains the slowest component in manual tests and has not been optimized or time-boxed.

## Safe Resume Commands

```powershell
cd C:\dev\exposurescan
.\venv\Scripts\python.exe -m pytest -q
cd frontend
npm run lint
npm run build
```

Run both local services from the repository root:

```powershell
.\run-dev.bat
```

Do not commit or push automatically when resuming unless explicitly requested.
