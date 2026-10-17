@echo off
title Agency Engine - Quick Audit
cd /d "%~dp0"

echo ========================================================
echo   Running Autonomous Audit for B-Fashion Explore
echo ========================================================
echo.

.\.venv\Scripts\python.exe -m agency_engine.cli audit --client b_fashion_explore --mode read_only

echo.
echo ========================================================
pause
