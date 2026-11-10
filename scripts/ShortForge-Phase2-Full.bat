@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%USERPROFILE%\ShortForge-3D"
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"
if not exist "%PY%" (echo [ERROR] ShortForge .venv not found. & pause & exit /b 1)
pushd "%ROOT%"
git fetch origin feat/phase2-multitopic-longform-engine
if errorlevel 1 (popd & pause & exit /b 2)
git checkout feat/phase2-multitopic-longform-engine
if errorlevel 1 (popd & pause & exit /b 3)
git pull --ff-only origin feat/phase2-multitopic-longform-engine
if errorlevel 1 (popd & pause & exit /b 4)
echo ===============================================
echo SHORTFORGE PHASE 2 LONG-FORM VIDEO
echo Only run after preview visual approval.
echo 1. Water Tower 90 seconds
echo 2. Solar Home 120 seconds
echo 3. Solar Home 180 seconds
echo 0. Exit
echo ===============================================
choice /c 1230 /n /m "Choose topic: "
set "OPTION=!ERRORLEVEL!"
if "!OPTION!"=="4" (popd & exit /b 0)
set "TOPIC=water tower"
set "SECONDS=90"
if "!OPTION!"=="2" (set "TOPIC=solar" & set "SECONDS=120")
if "!OPTION!"=="3" (set "TOPIC=solar" & set "SECONDS=180")
echo This runs GPU narration and !SECONDS!*24 Blender frames. No YouTube upload.
choice /c YN /n /m "Proceed? (Y/N): "
if errorlevel 2 (popd & exit /b 0)
"%PY%" scripts\phase2_runner.py --topic "!TOPIC!" --duration !SECONDS! --mode full --tts qwen --drive "%DRIVE%."
set "CODE=!ERRORLEVEL!"
popd
if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
if not "!CODE!"=="0" echo [REVIEW NEEDED] Open outbox/latest/run_manifest.json.
pause
exit /b !CODE!
