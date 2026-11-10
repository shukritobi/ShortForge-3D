# ShortForge Phase 2: reusable long-form procedural videos

Status: code and tests committed on phase2 branch. Real Windows Blender
preview and full scene verification are REQUIRED before approval.

## Supported profiles

- 60, 75, 90, 120, 180 seconds; 720x1280, 24 FPS.
- Storyboard version 2 with 8-40 contiguous problem-solution beats.
- Existing 40-second water tower version 1 stays functional.
- Blender frames: 1,440 / 1,800 / 2,160 / 2,880 / 4,320.
- Qwen3-TTS or Kokoro English narration; ASS captions; FFmpeg H264/AAC.
- Google Drive review bundle, no YouTube upload.

## Currently registered topics

1. Water distribution and water tower (water_distribution pack):
   24 original mechanism steps, houses, pump, elevated water tank,
   underground main, service branches and taps.
2. Rooftop photovoltaic system (solar_home pack):
   24 original mechanism steps, house, roof panels, sun, inverter,
   home battery, grid connection, electricity meter and lighting.

A user-provided topic outside registered mechanism packs is rejected rather
than rendered with misleading water-tower assets. More topics can be added by
registering their scene template, asset groups and mechanisms. Future
director support for Ollama must validate its action outputs against the
registered pack; it is not yet implemented for v2.

## Architecture

Story prompt -> topic registry -> validated v2 beats and actions
    -> reusable parametric Blender kit (meters, Z-up)
    -> action/camera timeline -> per-frame render cache and 6 preview stills
    -> local narration -> timeline-specific voice fit
    -> deterministic captions -> FFmpeg -> ffprobe QA -> Drive review.

Phase 1 remains available on its original branch and in the existing
40-second example. Phase 2 is on a stacked branch based on the current
unmerged Phase 1 PR.

## Quick start in Windows PowerShell

    cd C:\Users\User\ShortForge-3D
    git fetch origin
    git checkout feat/phase2-multitopic-longform-engine
    git pull --ff-only origin feat/phase2-multitopic-longform-engine
    .\.venv\Scripts\python.exe -m pytest -q

Create or validate registered storyboards:

    shortforge plan --engine library --topic "solar panels" --duration 120 --output output/projects/solar_home/120s/storyboard.json
    shortforge validate examples/solar_home_120s_v2.json
    shortforge validate examples/water_tower_90s_v2.json

Start with a six-still review, not thousands of frames:

    .\.venv\Scripts\python.exe scripts/phase2_runner.py --topic "solar" --duration 120 --mode preview --drive "G:\My Drive\ChatGPT ShortForge 3D"

Only after visual review authorizes a full render:

    .\.venv\Scripts\python.exe scripts/phase2_runner.py --topic "solar" --duration 120 --mode full --tts qwen --drive "G:\My Drive\ChatGPT ShortForge 3D"

The storyboard and outputs remain in
output/projects/solar_home/120s/.

Render caching uses the actual storyboard, Blender engine source and asset
source hash. A conflicting fingerprint refuses to reuse existing frames.
Successful runs resume missing frame numbers instead of rendering all frames
again. Use a new output directory to change an existing approved scene.

## Important limitations / acceptance gates

- GitHub CI validates Python and script syntax, not Blender's actual render.
- New topic packs require visual testing on the Windows Blender workstation.
- Camera framing, geometry, flow particles and material fidelity are not
  yet approved for the new packs. The six-frame contact sheet is mandatory.
- Long-form English voice must pass all beat duration and loudness QA before
  rendering thousands of frames. A 180-second video needs more spoken detail
  than a 40-second Short; inspect intentional pauses.
- Existing PC one-click review launcher targets the Phase 1 water tower.
  Use the new Phase 2 launcher for topic selection.
- Web dashboard, general AI-directed geometric invention, automatically
  licensed external assets, sound effects and YouTube publishing remain
  subsequent milestones, not features claimed as completed.

## Next assets/actions

Extract modular roof variants, street kits, parametric pipe elbows, valves,
water-flow loops, control panels, weather and sun-angle rigs. Give each stable
IDs, units, pivot transforms, dependencies, license and golden preview.
Then implement typed parameter schemas, render-by-shot invalidation,
frame/image comparisons, multiple camera shot presets and approval dashboard.
