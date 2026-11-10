@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"
echo =====================================================
echo ShortForge - RECOVER LATEST REVIEW (NO RERENDER)
echo =====================================================
if not exist "%PY%" (
 echo [ERROR] Main ShortForge Python missing: %PY%
 pause
 exit /b 1
)
pushd "%REPO%"
echo Updating source safely...
git pull --ff-only origin feat/phase1-local-water-tower-pipeline
if errorlevel 1 (popd & pause & exit /b 2)
echo Recovering latest local review bundle...
"%PY%" scripts\one_click_review.py --drive "%DRIVE%." --sync-latest
set "RESULT=!ERRORLEVEL!"
popd
if "!RESULT!"=="0" (
 echo [OK] Run recovered without Blender or Qwen execution.
 if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
) else (
 echo [ERROR] Recovery failed. Review the error above.
)
pause
exit /b !RESULT!
