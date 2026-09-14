# ScanX frontend

This React/Vite frontend is wired to the local ScanEx FastAPI backend. It does not ship sample scan data or call a cloud API.

## Run both servers locally

From the repository root, the Windows helper starts both terminals:

```powershell
.\run-dev.bat
```

From the repository root, start the backend:

```powershell
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

`VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`. Set it in `.env.local` when the backend uses another local URL. The Vite app runs on the port printed by `npm run dev`.

## Phase 2 backend backlog

- [ ] `POST /scan/{scan_id}/findings/{finding_id}/resolve` - persist a requested redaction or resolution and return the updated finding; currently `ScreenAudit` stores review state locally only.
- [ ] `POST /scan/{scan_id}/commit` - commit a verified scan to the ingestion pipeline and return a commit identifier; currently disabled because no backend endpoint exists.
- [ ] `GET /scans/{scan_id}/report` - generate a server-backed audit report; current export is a local JSON download of responses from this browser session.
- [ ] `GET /scans` - list prior scans and statuses; current UI has no scan history because the backend has no persistence endpoint.
- [ ] Authentication and authorization - add an auth contract for scan access, finding changes, exports, and commits; the current backend has no auth.
