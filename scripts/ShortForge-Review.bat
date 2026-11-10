@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"
echo ======================================================
echo ShortForge 3D - ONE-CLICK REVIEW AND PERFORMANCE LOGS
echo ======================================================
if not exist "%PY%" (
  echo [ERROR] Virtual environment missing at %PY%
  pause
  exit /b 1
)
pushd "%REPO%"
set "BRANCH="
for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if /I not "!BRANCH!"=="feat/phase1-local-water-tower-pipeline" (
  echo [ERROR] Expected working branch feat/phase1-local-water-tower-pipeline
  popd
  pause
  exit /b 2
)
echo Updating source, fast-forward only; your local changes will not be overwritten.
git pull --ff-only origin feat/phase1-local-water-tower-pipeline
if errorlevel 1 (
  echo [ERROR] Git pull failed; inspect git status. No force/reset was used.
  popd
  pause
  exit /b 3
)
echo Running tests, Blender keyframe review, and Qwen audio diagnostics.
echo Original and fresh logs are preserved; Drive latest will point to this run.
"%PY%" scripts\one_click_review.py --drive "%DRIVE%."
set "RESULT=!ERRORLEVEL!"
popd
if "!RESULT!"=="0" (
  echo [OK] Review package created and synced to %DRIVE%outbox\latest
) else (
  echo [REVIEW NEEDED] One or more checks failed. The available results and
  echo full timing/performance diagnostic bundle have still been synced.
)
if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
pause
exit /b !RESULT!
