# Acceptance evidence — 11 November 2026

The detailed solar revision uses `output/solar_detail_narration` and the
measured storyboard in `examples/solar_neighbourhood_120s_v2.json`. Its model
passed 18 Blender checks, including both facade openings and separate light
and equipment clearances. The 120-second, 249-word script uses 12 native Qwen
takes. Each fitted spoken PCM prefix matched its raw take byte-for-byte.
Studio's narration job also reused all cached takes and saved the timed shots.
See [the detailed solar workflow](SOLAR_PRODUCTION.md).

The following table records the earlier Phase 2 hardening release. Its media
and acceptance evidence remain available in their original output folders.

Overall: **PARTIAL**. Technical and sampled visual checks passed. Human
listening and final subtitle sign-off remain open.
All paths below are relative to `C:\Users\User\ShortForge-3D`.

| Final gate | Status | Current evidence |
|---|---|---|
| Code | PASS | 132 Python tests, compileall and Remotion typechecking. CI is linked on PR #2 |
| Geometry and sampled visuals | PASS | 13 Blender contact checks, matching renderer fingerprint, 119 frame samples covering 24 beats and 23 transition boundaries |
| Audio and captions | PARTIAL | Final AAC matched all 208 scripted words with offline ASR. −16.9 LUFS, −1.4 dBFS true peak, 0.54s minimum measured beat-end padding. 15 cues shifted by more than 0.3s. Human listening and exact word timing remain open |
| Video | PASS | `output/solar_hardened/draft.mp4` decoded through all 2,880 frames at 720×1280/24 FPS, with zero black segments. All 2,880 original PNGs and the narration WAV were reused |
| Studio and recovery | PASS | Browser-created, edited, previewed and approved 20s project. Restart surfaced interruption. Retry reused 140 of 142 existing frames and regenerated the damaged and uncommitted frames. Browser loaded the validated 480-frame MP4. An unchanged repeat rewrote zero frames |
| Delivery | PASS | Google Drive `outbox/latest` contains the revised solar draft, soundtrack, review reports, three topic artifacts and a Studio sample. PR #2 remains stacked on Phase 1 |

`output/solar_hardened` contains `visual_review.json`, `audio_review.json`,
`caption_review.json`, `review_contact_sheet.png` and `production_quality.json`.
The untouched baseline remains in `output/solar_corrected`. The sunlight dots
and cloud-cover shot remain stylized. The cloud effect is explained by a label.

| Criterion | Status | Evidence / remaining work |
|---|---|---|
| Phase 1 preserved | Verified | 40s existing MP4 passes ffprobe; fresh Blender frame 480 in `output/phase1_compatibility`; legacy tests pass |
| Shared multi-topic pipeline | Verified | Solar, water distribution, rainwater use `blender_v2.py` and the shared kit/actions |
| Solar roof, rails and equipment | Verified | Real Blender 4.5.2, 13 mechanical-contact checks in `output/solar_corrected/audit/geometry_audit.json`, six extra viewpoints and story previews inspected |
| Water actual Blender output | Verified | Six refreshed frames and contact sheet in `output/water_v2_review` |
| 120-second solar MP4 | Verified | `output/solar_hardened/draft.mp4`: 120.000s, 720×1280, 24 FPS, 2880 frames, AAC audio, complete FFmpeg decode, no black segments |
| Natural synchronized narration | Partially verified | Local Qwen CUDA, all 24 solar beats fit at ≤1.35×; 90s cache-only narration passed. Human listening approval remains open |
| Captions | Partially verified | Actual caption frames inspected; safe wrapping, voiced-window timing and silence exclusion tested. No phoneme/ASR forced word alignment |
| Third topic | Verified | Distinct 90s rainwater pack with real tank cutaway and a complete silent 20s demonstration. See `output/rainwater_review` and `output/rainwater_final_demo/draft.mp4` |
| Configurable timeline/profiles | Verified | Built-in 40–240s and manual 20–3600s contracts. Rendered 720×1280 at 24 FPS and 1080×1920 at 30 FPS, with 600 frames and full decode for the latter |
| Long-form 180s narration | Verified for timing | All 36 Qwen beats passed after retiming, with a maximum adjustment of 1.14×. See `output/solar_180_timing/audio/timing_report.json` and its retimed storyboard |
| Reusable asset/action metadata | Partially verified | 23 registered entries; instance IDs, metres, versions, dimensions and dependencies; reusable primitives. No standalone Blender asset-browser package |
| Resume / cache invalidation | Verified | Unit tests plus real replay: 2880 existing PNGs validated and zero frame timestamps changed; corrupt PNG rejection; late camera edits invalidate subsequent shots |
| Caption-only composition | Verified | FFmpeg recomposition completed with all 2880 frame timestamps unchanged, no Blender or TTS invocation |
| Fine-grained asset invalidation | Not implemented | Global geometry source edits invalidate all shots; shot/camera edits propagate conservatively from their first affected beat |
| Diagnostics and resource monitoring | Verified | JSON reports, full decode/loudness logs, partial-run 125 telemetry samples; GPU max 4466 MB / 64°C during observed full-render interval |
| SFX library | Verified for this export | Six original sounds measured. Four quiet assembly and electrical cues in the reviewed solar draft. Effects-only track peak −38.2 dBFS |
| Local dashboard | Verified | Full browser/server workflow passed for a 20-second silent technical job, including restart, retry and playback metadata |
| One-click workflow | Verified components | The verification runner produced all three contact sheets and synced them to Drive. The Studio server and browser interface were exercised |
| Drive review organization | Verified | The three-topic verification run synced to `outbox/runs/20261111T005725Z-production-verification`; `outbox/latest` is the current review location |
| Tests / CI / PR | Verified | 132 local Python tests, compileall and Remotion TypeScript. CI and the stacked base are visible in PR #2 |
| Human publication approval | Blocked on review | User must review the full video/audio; publishing endpoints do not exist |

## Measured solar output

- Draft SHA256 before/after equivalent composition is recorded in
  `production_quality.json`; refresh this report after any composition change.
- EBU R128 measured **−16.9 LUFS**, **−1.4 dBFS true peak**, 5.9 LU range.
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
