# Acceptance evidence — 10 November 2026

Overall: **partially verified; review build, not publication approved**.
All paths below are relative to `C:\Users\User\ShortForge-3D`.

| Criterion | Status | Evidence / remaining work |
|---|---|---|
| Phase 1 preserved | Verified | 40s existing MP4 passes ffprobe; fresh Blender frame 480 in `output/phase1_compatibility`; legacy tests pass |
| Shared multi-topic pipeline | Verified | Solar, water distribution, rainwater use `blender_v2.py` and the shared kit/actions |
| Solar roof, rails and equipment | Verified | Real Blender 4.5.2, 13 mechanical-contact checks in `output/solar_corrected/audit/geometry_audit.json`, six extra viewpoints and story previews inspected |
| Water actual Blender output | Verified | Six refreshed frames and contact sheet in `output/water_v2_review` |
| 120-second solar MP4 | Verified | `output/solar_corrected/draft.mp4`: 120.000s, 720×1280, 24 FPS, 2880 frames, AAC audio, complete FFmpeg decode, no black segments |
| Natural synchronized narration | Partially verified | Local Qwen CUDA, all 24 solar beats fit at ≤1.35×; 90s cache-only narration passed. Human listening approval remains open |
| Captions | Partially verified | Actual caption frames inspected; safe wrapping, voiced-window timing and silence exclusion tested. No phoneme/ASR forced word alignment |
| Third topic | Verified for preview | Distinct 90s rainwater pack with real tank cutaway; contact sheet in `output/rainwater_review`; narrated full rainwater video not generated |
| Configurable timeline/profiles | Partially verified | Any built-in 40–240s, manual 20–3600s, 24/30 FPS, preview/draft/final configuration tests; final-profile smoke evidence added below when run |
| Long-form 180s narration | Pending verification | Distinct 36-beat script; measured timing run in `output/solar_180_timing` |
| Reusable asset/action metadata | Partially verified | 23 registered entries; instance IDs, metres, versions, dimensions and dependencies; reusable primitives. No standalone Blender asset-browser package |
| Resume / cache invalidation | Verified | Unit tests plus real replay: 2880 existing PNGs validated and zero frame timestamps changed; corrupt PNG rejection; late camera edits invalidate subsequent shots |
| Caption-only composition | Verified | FFmpeg recomposition completed with all 2880 frame timestamps unchanged, no Blender or TTS invocation |
| Fine-grained asset invalidation | Not implemented | Global geometry source edits invalidate all shots; shot/camera edits propagate conservatively from their first affected beat |
| Diagnostics and resource monitoring | Verified | JSON reports, full decode/loudness logs, partial-run 125 telemetry samples; GPU max 4466 MB / 64°C during observed full-render interval |
| SFX library | Partially verified | Six original procedural sounds and opt-in mixing; deterministic/quiet-level tests. Default solar deliverable uses narration only |
| Local dashboard | Partially verified | Browser-created project and unapproved render rejection; backend approval, history and failure recovery tests. Full browser-to-video job still needs a separate acceptance run |
| One-click workflow | Verified components | `ShortForge-Studio.bat`, `ShortForge-Verify.bat`, existing launchers retained; underlying CLI and dashboard tested |
| Drive review organization | Pending final bundle | Existing sync succeeded for initial corrected preview; final multi-topic bundle and launchers packaged at delivery |
| Tests / CI / PR | Pending final CI | 126 local Python tests, compileall and Remotion TypeScript passed; see delivery commit/check links |
| Human publication approval | Blocked on review | User must review the full video/audio; publishing endpoints do not exist |

## Measured solar output

- Draft SHA256 before/after equivalent composition is recorded in
  `production_quality.json`; refresh this report after any composition change.
- EBU R128 measured **−16.9 LUFS**, **−1.3 dBFS true peak**, 6 LU range.
- GPU average 50.55%, peak 89%; system RAM peak 41% in the observed interval.
  Telemetry began partway through the render, so it is not a full-job benchmark.
- Nominal Eevee rendering was approximately 0.22–0.24 seconds per frame in logs.
- The full MP4 passed machine decoding. That is not a claim that a human watched
  every frame or listened to the complete voice track.

## Remaining scope

The dashboard exposes scene/action editing through validated JSON, not a visual
drag-and-drop asset editor. Camera override vectors, true mechanism-specific
simulations, automatic scene-level technical assertions, and exact word alignment
are not complete. Current camera fitting protects the settled active subject;
smooth transitions and background objects still need editorial review.

These limits are explicit rather than hidden behind green tests. Do not label
the entire autonomous directive complete or merge/publish on this evidence alone.
