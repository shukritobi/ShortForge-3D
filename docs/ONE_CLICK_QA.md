# ShortForge: one-click performance review and quality gate

The local PC is the worker; there is no persistent remote shell or listener.
ChatGPT can read results synced into the existing Drive folder when you ask for
review. No live PC connection or automatic message to ChatGPT is claimed.

## Run after each approved GitHub update

Double-click 00 - Run ShortForge Review.bat in the ShortForge Drive root.

The launcher:
1. Checks the feature branch; runs git pull --ff-only (never force resets).
2. Runs pytest, 6 Blender keyframes and the Qwen narration timing test.
3. Saves logs, raw voice samples, telemetry and QA status on success or failure.
4. Archives the previous Drive outbox/latest into outbox/archive/timestamp.
5. Copies the new review to outbox/latest and outbox/runs/unique-run-id.
6. Leaves YouTube publishing disabled.

Say "Check ShortForge latest run" here after Drive finishes syncing.

## Review package

READ_ME_FIRST.txt: run and results
run_manifest.json: source Git SHA, phases, timings, status, output manifest
contact_sheet.png + preview_XXXX.png: six keyframes
scene_manifest.json: mesh components, camera presets, counts
timing_report.json: each spoken audio duration vs storyboard beat
tts_metrics.jsonl: model load time, synthesis time, RTF, CUDA flag, cache hits
voice_samples/beat_XX_raw.wav: raw audio even if pacing fails
system_samples.jsonl: three-second CPU/RAM/GPU time series
performance_report.json and lag_patterns.json: pattern findings and stage times
diagnostics/stage/*: pc_agent logs and doctor files
draft.mp4 and quality.json: only in explicit full-video mode after all gates pass

Important: GPU synthesis latency and finished spoken-audio duration differ.
A spoken clip measuring 12.64 seconds for a 5-second shot needs script
revision, bounded generation analysis, or voice pacing work. CUDA reduces
compute time; it does not automatically shorten the spoken recording.

## Optional one-time GPU installation

On the screenshot, torch 2.15.0+cpu reported CUDA False.
Double-click 04 - Enable NVIDIA Qwen GPU.bat once. It installs matching
torch and torchaudio 2.11.0 CUDA 12.8 wheels into isolated .venv-tts.
It uses only the official PyTorch index, does not touch system Python,
and verifies CUDA before reporting success. This can download large wheels.

If setup fails, use the current PyTorch installer for your Windows+Python
configuration: https://pytorch.org/get-started/locally/

## Generating full 40-second MP4

Once contact-sheet and raw audio quality are acceptable, double-click
03 - Generate Draft Video.bat. It rechecks tests, visuals and narration
before starting 960-frame Blender/FFmpeg encoding, then syncs the MP4.
No YouTube upload.

## Interpreting lag patterns

GPU idle <8% can be normal during CPU work; compare with pipeline stage.
Thirty seconds without new stdout is a suspected stall, not proof of a hang.
RTF = synthesis processing seconds / generated spoken audio seconds.
Speech fit = generated spoken audio seconds / assigned beat seconds.
System memory near 90% is a warning to reduce competing workloads.
The sampled metrics are system-level, not guaranteed process-only values.
