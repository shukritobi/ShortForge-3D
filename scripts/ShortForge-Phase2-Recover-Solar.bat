@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"
echo =====================================================
echo SHORTFORGE PHASE 2 - RECOVER SOLAR PREVIEW
echo Recover the six frames from the earlier failed CLI audit.
echo NO BLENDER RERENDER / NO QWEN / NO YOUTUBE PUBLISHING
echo =====================================================
if not exist "%PY%" (
 echo [ERROR] ShortForge Python environment missing: %PY%
 pause
 exit /b 1
)
pushd "%REPO%"
git fetch origin feat/phase2-multitopic-longform-engine
if errorlevel 1 (popd & pause & exit /b 2)
git checkout feat/phase2-multitopic-longform-engine
if errorlevel 1 (popd & pause & exit /b 3)
git pull --ff-only origin feat/phase2-multitopic-longform-engine
if errorlevel 1 (popd & pause & exit /b 4)
echo Validating existing 120s Solar Home scene manifest and six PNGs...
"%PY%" scripts\phase2_runner.py --topic solar --duration 120 --mode recover-preview --drive "%DRIVE%."
set "RESULT=!ERRORLEVEL!"
popd
if "!RESULT!"=="0" (
  echo [OK] Recovered contact sheet and six frames synced to Drive.
  if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
) else (
  echo [ERROR] Recovery failed; files remain on your PC unchanged.
  echo Check the error above before rerunning a full preview.
)
pause
exit /b !RESULT!
