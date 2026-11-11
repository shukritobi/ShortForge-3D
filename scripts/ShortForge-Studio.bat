@echo off
setlocal
cd /d "%USERPROFILE%\ShortForge-3D"
if not exist ".venv\Scripts\python.exe" (
  echo ShortForge Python environment is missing. See docs\PRODUCTION.md.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" -m shortforge.dashboard
pause
