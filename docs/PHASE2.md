# ShortForge Phase 2: reusable long-form procedural videos

Windows Blender 4.5.2 has rendered all three packs. The review bundle includes
a narrated 120-second solar draft and a native 1080×1920/30 FPS rainwater demo.
See [acceptance evidence](ACCEPTANCE.md) for the remaining listening check.

## Supported profiles

- Built-in storyboards cover 40–240 seconds. Custom v2 timelines cover 20–3600 seconds.
- 360×640 preview, 720×1280 draft, and 1080×1920 final at 24 or 30 FPS.
- Storyboard version 2 accepts 8–720 contiguous problem-solution beats.
- Existing 40-second water tower version 1 stays functional.
- Blender frame count equals duration × frame rate.
- Qwen3-TTS or Kokoro English narration; ASS captions; FFmpeg H264/AAC.
- Google Drive review bundle, no YouTube upload.

## Currently registered topics

1. Water distribution and water tower (water_distribution pack):
   24 original mechanism steps, houses, pump, elevated water tank,
   underground main, service branches and taps.
2. Rooftop photovoltaic system (solar_home pack):
   24 original mechanism steps, house, roof panels, sun, inverter,
   home battery, grid connection, electricity meter and lighting.
3. Rainwater harvesting (rainwater pack): gutter, first flush, covered tank,
   cutaway, overflow, pump and outlet.

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

The cache checks shot keys, Blender version, model sources and PNG integrity.
Resume reuses valid frames and regenerates affected or corrupt frames. Audio,
caption and SFX edits leave the visual keys unchanged.

## Important limitations / acceptance gates

- GitHub CI validates Python and script syntax, not Blender's actual render.
- New topic packs require visual testing on the Windows Blender workstation.
- Inspect a six-frame preview for each new project. The solar review sampled
  all 24 beats and 23 transition boundaries.
- Long-form English voice must pass all beat duration and loudness QA before
  rendering thousands of frames. A 180-second video needs more spoken detail
  than a 40-second Short; inspect intentional pauses.
- Existing PC one-click review launcher targets the Phase 1 water tower.
  Use the new Phase 2 launcher for topic selection.
- Studio supports preview, approval, rendering, logs and retry. The existing
  effects are original procedural audio. See the [Studio guide](PRODUCTION.md).

## Solar preview recovery (10 November 2026)

The first Phase 2 Solar Home 120s PC preview rendered all six PNGs in Blender
4.5.2, but the CLI incorrectly tried to print the legacy water tower's
\`manifest["structural_counts"]\` key. The v2 manifest uses
\`assets\` and \`object_count\`. The new version-aware CLI printer fixes it.

To avoid another Blender render, run:

    08 - Recover Phase2 Solar Preview.bat

in the shared Drive root. It updates the Phase 2 branch, verifies the existing
storyboard and scene manifest, checks all six PNGs, assembles a contact sheet
with FFmpeg and syncs a **new recovery review bundle** into
\`outbox/latest\`. No Qwen narration, Blender rerender or YouTube upload.

Alternatively in PowerShell:

    .\\.venv\\Scripts\\python.exe scripts\\phase2_runner.py --topic solar --duration 120 --mode recover-preview --drive "G:\\My Drive\\ChatGPT ShortForge 3D"

Historical render provenance is preserved: the recovered images were generated
before the current source update. They still require human visual review.
Future failures after Blender produces some frames preserve those images in
the diagnostic review bundle instead of discarding them.
