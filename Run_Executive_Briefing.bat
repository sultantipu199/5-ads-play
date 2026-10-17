@echo off
title Agency Engine - Executive Briefing
cd /d "%~dp0"

echo ========================================================
echo   Generating Executive Briefing for B-Fashion Explore
echo ========================================================
echo.

.\.venv\Scripts\python.exe -m agency_engine.cli brief --client b_fashion_explore --dry-run

echo.
echo ========================================================
pause
