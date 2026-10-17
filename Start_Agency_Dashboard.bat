@echo off
title Omnichannel Agency Engine Dashboard
cd /d "%~dp0"

echo ========================================================
echo   Launching Omnichannel Autonomous Agency Dashboard
echo   Connected to: B-Fashion Explore (act_2665580250239749)
echo ========================================================
echo.

start "" "http://localhost:8000"
.\.venv\Scripts\uvicorn.exe agency_engine.web.app:app --host 127.0.0.1 --port 8000 --reload

pause
