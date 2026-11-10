@echo off
setlocal
cd /d "%USERPROFILE%\ShortForge-3D"
".venv\Scripts\python.exe" scripts\production_review.py
if errorlevel 1 echo Verification failed. Diagnostics remain in output\review_runs.
pause
