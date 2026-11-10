@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "DRIVE=%~dp0"
if not exist "%DRIVE%outbox\latest" set "DRIVE=G:\My Drive\ChatGPT ShortForge 3D\"
if not exist "%PY%" (
 echo [ERROR] ShortForge virtual environment missing at %PY%.
 pause
 exit /b 1
)
pushd "%REPO%"
for /f "delims=" %%B in ('git branch --show-current') do set "BRANCH=%%B"
if /I not "!BRANCH!"=="feat/phase1-local-water-tower-pipeline" (
 echo [ERROR] Expected feature branch. Switch to feat/phase1-local-water-tower-pipeline.
 popd
 pause
 exit /b 2
)
echo [1/3] Updating ShortForge source (fast-forward only)...
git pull --ff-only origin feat/phase1-local-water-tower-pipeline
if errorlevel 1 (
 echo [ERROR] Git pull failed. Check git status without forcing local changes.
 popd
 pause
 exit /b 3
)
echo.
echo SHORTFORGE 3D - Local 40 second draft
echo [1] Qwen3-TTS English narration (Ryan) - needs .venv-tts
echo [2] Kokoro English narration (af_heart) - needs .venv-tts
echo [3] Silent technical MP4 - no TTS installation required
echo [0] Exit
choice /c 1230 /n /m "Choose one: "
set "PICK=!ERRORLEVEL!"
if "!PICK!"=="4" (popd & exit /b 0)
set "TTS=none"
set "SPEAKER="
if "!PICK!"=="1" set "TTS=qwen"
if "!PICK!"=="1" set "SPEAKER=Ryan"
if "!PICK!"=="2" set "TTS=kokoro"
if "!PICK!"=="2" set "SPEAKER=af_heart"
echo [2/3] Running Blender/FFmpeg pipeline on this PC...
if defined SPEAKER (
 "%PY%" scripts\pc_agent.py full --tts !TTS! --speaker !SPEAKER!
) else (
 "%PY%" scripts\pc_agent.py full --tts none
)
set "RESULT=!ERRORLEVEL!"
popd
echo [3/3] Syncing latest draft and diagnostics...
if exist "%DRIVE%outbox\latest" (
 if "!RESULT!"=="0" (
  for %%F in (draft.mp4 quality.json scene_manifest.json contact_sheet.png preview.png) do (
    if exist "%REPO%\output\water_tower\%%F" copy /Y "%REPO%\output\water_tower\%%F" "%DRIVE%outbox\latest\%%F" >nul
  )
  if exist "%REPO%\output\water_tower\audio\voice_manifest.json" copy /Y "%REPO%\output\water_tower\audio\voice_manifest.json" "%DRIVE%outbox\latest\voice_manifest.json" >nul
  if exist "%REPO%\output\water_tower\captions\captions.json" copy /Y "%REPO%\output\water_tower\captions\captions.json" "%DRIVE%outbox\latest\captions.json" >nul
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
 >"%DRIVE%outbox\latest\LAST_SYNC.txt" echo ShortForge draft sync at %DATE% %TIME% Result !RESULT!
)
if not "!RESULT!"=="0" (
 echo [ERROR] Check output\diagnostics latest summary.json on your PC.
) else (
 echo [OK] Video: %REPO%\output\water_tower\draft.mp4
 if exist "%DRIVE%outbox\latest" start "" "%DRIVE%outbox\latest"
)
pause
exit /b !RESULT!
