@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox\latest" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"

echo ====================================================
echo SHORTFORGE 3D - SIX-FRAME REVIEW
 echo ====================================================
if not exist "%PY%" (
  echo [ERROR] ShortForge virtual environment not found: %PY%
  pause
  exit /b 1
)
if not exist "%DRIVE%outbox\latest" (
  echo [WARNING] Google Drive workspace not found at %DRIVE%
  echo Render can still proceed. Outputs stay in %REPO%\output\water_tower
)

pushd "%REPO%"
set "BRANCH="
for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if /I not "!BRANCH!"=="feat/phase1-local-water-tower-pipeline" (
  echo [ERROR] Expected feature branch. Run: git checkout feat/phase1-local-water-tower-pipeline
  popd
  pause
  exit /b 2
)
echo [1/3] Updating working feature branch (fast-forward only)...
git pull --ff-only origin feat/phase1-local-water-tower-pipeline
if errorlevel 1 (
  echo [ERROR] Git pull failed. Working files were not overwritten.
  popd
  pause
  exit /b 2
)
echo [2/3] Rendering six review keyframes...
"%PY%" scripts\pc_agent.py review
set "RESULT=!ERRORLEVEL!"
popd

echo [3/3] Copying review outputs and diagnostics...
if exist "%DRIVE%outbox\latest" (
  if "!RESULT!"=="0" (
    for %%F in (contact_sheet.png preview.png scene_manifest.json preview_0120.png preview_0240.png preview_0480.png preview_0576.png preview_0720.png preview_0888.png) do (
      if exist "%REPO%\output\water_tower\%%F" copy /Y "%REPO%\output\water_tower\%%F" "%DRIVE%outbox\latest\%%F" >nul
    )
  )
  set "LASTRUN="
  for /f "delims=" %%D in ('dir /b /ad /o-d "%REPO%\output\diagnostics" 2^>nul') do (
    if not defined LASTRUN set "LASTRUN=%%D"
  )
  if defined LASTRUN (
    for %%F in (doctor.json summary.json events.jsonl stdout.log stderr.log) do (
      if exist "%REPO%\output\diagnostics\!LASTRUN!\%%F" copy /Y "%REPO%\output\diagnostics\!LASTRUN!\%%F" "%DRIVE%outbox\latest\%%F" >nul
    )
  )
  >"%DRIVE%outbox\latest\LAST_SYNC.txt" echo ShortForge 3D review sync at %DATE% %TIME%
  >>"%DRIVE%outbox\latest\LAST_SYNC.txt" echo Latest task result: !RESULT!
)
if not "!RESULT!"=="0" (
  echo [ERROR] Review failed. Check outbox\latest\summary.json and stderr.log.
) else (
  echo [OK] Review created: %REPO%\output\water_tower\contact_sheet.png
  if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
)
pause
exit /b !RESULT!
