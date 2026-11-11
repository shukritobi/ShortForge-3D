# Work handoff — 11 November 2026

Checkout: `C:\Users\User\ShortForge-3D`; branch
`feat/phase2-multitopic-longform-engine`; PR #2 remains stacked on unmerged PR #1.
Starting remote was 8acb352. No merging or YouTube publication is authorized.

Actual machine: Blender 4.5.2 LTS, FFmpeg 7.1.1, RTX 4070 SUPER 12 GB,
Qwen inference on cuda:0. Main venv Python 3.14; isolated TTS runtime retained.

## Current direction

- Start from `examples/solar_neighbourhood_112s_v2.json` and
  `output/solar_energy`. The user liked the previous cut's direction and asked
  for slightly faster, consistent narration, quieter openings, clearer
  camera-to-narration timing, and a coherent, detailed neighbourhood.
- The director cut uses one pitch-preserving 1.07× adjustment across all 12
  cached Qwen takes. Fill gaps with a relevant explanation and adjust shot
  lengths to the voice. Avoid per-beat speed changes. The opening hiss was
  present in the raw first take, near 7.8 kHz. A 1.11-second trim applies only
  to the fingerprinted WAV. In a 7–8.5 kHz check, the old burst measured
  −33.2 dBFS and the revised first 150 ms measured −83.2 dBFS.
- Build a visual for the precise mechanism, then land the camera on it when
  the narration names it. The current edit uses the roof contacts and rail
  gap, the silicon layers and junction, a diode around a shaded group, and
  separate shots for the breaker bank, porch fixture, meter and battery.
  Check foreground obstructions at the actual camera angle.
- Reuse the hero house's door and window openings, wall trim, roof and
  proportions across neighbouring houses. Vary the siding, planting, lawn
  tufts and chimney placement. Keep electrical hardware spatially separate
  from the porch light. See `docs/SOLAR_PRODUCTION.md`.
- The daylight cut adds a blue sky, clouds, a deeper tree line, siding and
  roof relief, a roof leaf and readable electrical labels. Use large soft
  lights to keep the narrated subject legible while preserving the shadow
  edges that show depth. The full movie uses EEVEE with ray tracing off.
  `output/solar_daylight_comparison` includes a Cycles OptiX still of the
  breaker shot. The 112-second daylight movie passed full decode and
  black-frame checks. Its narration WAV matches the preceding cut.
- The next solar revision adds a soft glow and slight flutter to packets
  moving along the photon, carrier, diode and grid routes. The model shows
  motion on the route while the hardware stays fixed. The route is schematic.
  Camera review found the old roof edit had an overhead insert at 6.96 seconds
  and another cut at 7.96 seconds. The new cut goes directly to the rails.
  Electrical close-ups start with their hardware in place. The trees have
  irregular clusters of foliage and visible branches.
- Use this solar cut as the series benchmark. Keep the subject well lit, make
  camera changes serve the spoken explanation, and give moving energy or fluid
  a visible path. Use readable close-ups, physically separate overlapping
  parts, and check the opening for noise. The final review exports are vertical
  720 × 1280 at 24 fps. The episode sets use 32 EEVEE samples after a
  side-by-side check of the compost wide shot and thermometer close-up
  against 64 samples. The solar export retains its 64-sample settings.
- `docs/EPISODE_SCRIPTS.md` contains all ten voiceover drafts with five
  timed picture beats and primary references per topic. The 51–56 second
  runtimes are editorial targets. Measure the final narration before
  locking shots.
- Build, voice and render the ten registered scenes with
  `scripts/produce_episode.py complete`. This command reuses Qwen takes,
  sets each episode to its measured voice plus short pauses, renders five
  stills, then checks the full MP4. Use `--episode episode_compost` to rerun
  only one episode. The working projects are in `output/season_one`, and
  passing exports can go to the Drive review folder `outbox/season_one`.
- `docs/TOPIC_BACKLOG.md` holds ten researched pitches with hooks, visual beats
  and source links. Start with the compost-bin comparison, then home wind and
  the sink trap. Open with a visible contradiction, use a cutaway to explain
  the mechanism, then change one variable and return to the opening image.

## Previous checkpoint

`scripts/solar_neighbourhood.py` has the detailed house,
separate porch light and service wall, street actors and enlarged PV stage.
See `docs/SOLAR_PRODUCTION.md`. New example `examples/solar_neighbourhood_120s_v2.json`
is the measured 249-word, 12-shot script. All 12 raw Qwen takes match the fitted
PCM prefixes byte-for-byte. The detailed draft renders in `output/solar_detail_narration`;
the prior solar builds remain separate. Progress is in `output/solar_detail_full.log`.
If interrupted, resume using the same measured storyboard and output directory.
Drive root has three current launchers and `START HERE.txt`; the ten superseded
files are under `Archive/Previous top-level files/20261111-101215`.

Implemented: solar rail normal contact and meter placement corrections,
camera bounds fitting, contrast and shadows, colour rather than scale highlights,
FPS-aware animation/export, arbitrary duration contracts, longer distinct scripts,
rainwater pack, safe shared transform actions, shot/resume cache, waveform-assisted
captions, shared Qwen cache, local dashboard, original SFX, review launchers.

Hardening checkpoint: 132 Python tests, 13 Blender contact checks and 119 visual
samples. `output/solar_hardened` holds the 120s edit, reviewed cue timings,
standalone soundtrack and diagnostic JSON. It reused 2,880 PNGs and the original
Qwen WAV. `output/solar_corrected` is the baseline. Final AAC matched 208 scripted
words with cached Whisper medium.

Studio QA project `output/dashboard_projects/6a5190a51905` passed a 20s browser
workflow. The interrupted run had 142 frame files. Retry reused 140, regenerated
the damaged and uncommitted files, and completed 480 frames. Its old log is in
`history/20261111T011911-e6e89b`. See `docs/ACCEPTANCE.md` and Drive `outbox/latest`.

Important limitations: waveform estimates are not exact forced word alignment;
global asset source edits invalidate all render shots; construction-grade engineering
and human listening approval are not claimed. Do not confuse a green CI with
visual acceptance. `output/solar_corrected` contains the verified 120-second run.
