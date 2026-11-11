# Work handoff — 11 November 2026

Checkout: `C:\Users\User\ShortForge-3D`; branch
`feat/phase2-multitopic-longform-engine`; PR #2 remains stacked on unmerged PR #1.
Starting remote was 8acb352. No merging or YouTube publication is authorized.

Actual machine: Blender 4.5.2 LTS, FFmpeg 7.1.1, RTX 4070 SUPER 12 GB,
Qwen inference on cuda:0. Main venv Python 3.14; isolated TTS runtime retained.

Current revision: `scripts/solar_neighbourhood.py` has the detailed house,
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
