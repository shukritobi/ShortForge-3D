# First 40-second local production run

## 1. Update the Windows checkout
    cd C:\Users\User\ShortForge-3D
    git checkout feat/phase1-local-water-tower-pipeline
    git pull --ff-only origin feat/phase1-local-water-tower-pipeline

## 2. Run baseline tests and verify visuals
    .\.venv\Scripts\python.exe -m pytest -q
    .\.venv\Scripts\python.exe scripts/pc_agent.py review

Review contact_sheet.png and all six numbered preview frames:
frames 120, 240, 480, 576, 720 and 936 (the final frame is 39s,
not the beginning of the final reveal at 37s).

Expected fixes: no floating tank before 19s, anchored support build, tank
assembly completed by 25s, pipe flow at 30s, full water tower in final shot.
Still compare with screenshots. Green CI is not a visual pass.

## 3. Install Qwen3-TTS
Read docs/TTS_SETUP.md and use an isolated .venv-tts. The system does NOT
use Windows Speech, Piper as the default, cloud subscriptions or paid APIs.

## 4. Narrated 40-second draft
    .\.venv\Scripts\python.exe scripts/pc_agent.py full --tts qwen --speaker Ryan

A separate technical-only silent draft can be made NOW using:
    .\.venv\Scripts\python.exe scripts/pc_agent.py full --tts none

Outputs:
    output/water_tower/draft.mp4
    output/water_tower/quality.json
    output/water_tower/scene_manifest.json
    output/water_tower/audio/narration.wav
    output/water_tower/audio/voice_manifest.json
    output/diagnostics/<timestamp>-full-*/summary.json

The renderer executes on your PC and creates 960 PNG frames. The video is
assembled by FFmpeg into H.264 720x1280 at 24 FPS, 40 seconds.

## 5. Sync and review
The separate one-click ShortForge-Video.bat launcher copies draft.mp4,
quality.json, manifest, captions and the latest diagnostic logs to
G:\My Drive\ChatGPT ShortForge 3D\outbox\latest.
Do not automatically publish to YouTube. Keep the Git checkout and large frame
sequence on a local SSD instead of the Drive sync folder.

## If anything fails
Read and share ONLY the reviewed summary.json and doctor.json first.
The raw log may contain local paths and usernames. The audio step runs before
3D rendering to prevent wasting a 960-frame render on a TTS setup error.
