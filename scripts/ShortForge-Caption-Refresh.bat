@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"
echo ========================================================
echo SHORTFORGE - FIX CAPTIONS / RECOMPOSE WITHOUT BLENDER
echo ========================================================
if not exist "%PY%" (echo [ERROR] Python venv missing. & pause & exit /b 1)
pushd "%REPO%"
for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if /I not "!BRANCH!"=="feat/phase1-local-water-tower-pipeline" (
 echo [ERROR] Switch to ShortForge feature branch first.
 popd & pause & exit /b 2
)
git pull --ff-only origin feat/phase1-local-water-tower-pipeline
if errorlevel 1 (popd & pause & exit /b 3)
"%PY%" -m pytest -q
if errorlevel 1 (
 echo [ERROR] Unit tests failed. No video overwritten.
 popd & pause & exit /b 4
)
"%PY%" scripts\recompose_review.py --drive "%DRIVE%."
set "RESULT=!ERRORLEVEL!"
popd
if "!RESULT!"=="0" (
 echo [OK] New draft and quality JSON synced. No Blender/Qwen rerun.
 if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
) else echo [ERROR] Caption recomposition or sync failed. Check output above.
pause
exit /b !RESULT!
