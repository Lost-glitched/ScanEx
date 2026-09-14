rem Arnav Sahu
rem 24BCE2976
@echo off
setlocal

start "ScanEx Backend" cmd /k "cd /d ""%~dp0"" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "ScanX Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo Backend and frontend terminals started.
echo Backend: http://127.0.0.1:8000
endlocal
