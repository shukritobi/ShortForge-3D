@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"
if not exist "%PY%" (
 echo [ERROR] Main Python environment missing.
 pause
 exit /b 1
)
pushd "%REPO%"
set "BRANCH="
for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if /I not "!BRANCH!"=="feat/phase1-local-water-tower-pipeline" (
 echo [ERROR] Switch to the feature branch first.
 popd
 pause
 exit /b 2
)
git pull --ff-only origin feat/phase1-local-water-tower-pipeline
if errorlevel 1 (popd & pause & exit /b 3)
echo Running all QA checks and, only if successful, rendering 960 frames.
"%PY%" scripts\one_click_review.py --drive "%DRIVE%" --full
set "RESULT=!ERRORLEVEL!"
popd
if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
if "!RESULT!"=="0" (
 echo [OK] Full draft synced to review. No automatic YouTube upload.
) else (
 echo [REVIEW NEEDED] Full render was gated or failed. Diagnostic bundle was saved.
)
pause
exit /b !RESULT!
