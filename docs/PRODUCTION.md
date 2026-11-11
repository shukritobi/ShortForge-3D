# Local production workflow

Run `scripts/ShortForge-Studio.bat`. The server listens only on
`http://127.0.0.1:8765`. It uses the existing Python CLI, one active GPU job,
and no publishing endpoint. Stop the console with Ctrl+C when finished.

1. Create a solar, water-distribution or rainwater project; choose seconds,
   24/30 FPS, and preview (360×640), draft (720×1280) or final (1080×1920).
2. Edit the storyboard JSON if necessary. Only registered scenes, targets,
   action types and numeric parameters are executable. Save validates it.
3. Generate the six-frame preview. Inspect construction, contacts and framing.
4. Approve that revision, then check Qwen narration. Listen to the WAV samples.
5. Render the video. Select **Silent technical export** for a quick test without
   voice synthesis. A changed storyboard or source revision invalidates approval.
6. Recompose captions without Blender. Review the MP4 before any external use.

`scripts/ShortForge-Verify.bat` runs tests and previews all three topics and
syncs a timestamped review bundle to the existing Drive workspace. Existing
project storyboards are preserved; manual edits are not overwritten.

## Runtime contracts

- Built-in scripts support **any integer 40–240 seconds**, using distinct
  additional narration beyond 120 seconds. Manual v2 timelines support
  20–3600 seconds, up to 720 beats. This is not arbitrary-topic generation:
  unfamiliar topics require a registered geometry and narrative pack.
- Final resolution and 30 FPS are implemented; acceptance distinguishes
  configuration tests from actual rendered-output tests.
- Primary narration remains local Qwen. No system-voice fallback. Model samples
  share immutable content/voice keys under `output/voice_cache` across projects.
- `scripts/measure_narration.py STORY --out PROJECT` retains original timing,
  measures Qwen speech, and redistributes beat windows within the same duration
  when needed. It refuses material that cannot fit at at most 1.25× speed.
- Regular v2 audio QA rejects more than 1.35× compression. Phase 1 retains its
  prior 1.7× compatibility threshold. Speech is never slowed to fill a long beat.
- Captions use the fitted waveform's voiced windows and textual weighting.
  This improves silence boundaries but **is not forced word alignment**.
  Human listening and subtitle review remain required.

## Shared engine and extensions

`scripts/blender_assets_v2.py` supplies procedural primitives, houses, ground,
roads, vegetation and connected pipe routes. `scripts/blender_v2.py` owns
visibility, construction, flow, colour emphasis, camera motion and rendering.
`scripts/blender_actions.py` adds move, rotate, scale, disappear, explode and
reassemble. Transform vectors are validated; rotations use degrees and moves
use metres. Scene manifests record stable object IDs, categories, units,
versions, dimensions and dependencies. `assets/catalog.json` indexes sources.

Solar-specific: roof-mounted panels/rails, inverter, meter, storage and cables.
Water-specific: elevated tank/supports and a buried distribution cutaway.
Rainwater-specific: gutters, downpipe, debris screen, first-flush branch, covered
tank/cutaway, overflow, garden pump and outlet. All use the same renderer;
rainwater introduces no topic conditional in animation dispatch.

The tank cutaway is explanatory, not a fabrication drawing. Models remain
stylized and are not construction documents. The registry is a source catalog,
not an exported standalone Blender asset-browser package.

## Caching and recovery

Each shot hashes visual actions and cameras, render settings, Blender version
and geometry/animation source. Earlier persistent construction/camera changes
invalidate later shots conservatively. Narration/caption/SFX edits do not.
Shared model-source edits currently invalidate all shots: per-asset dependency
fingerprints are a future refinement, not claimed here.

Frames are accepted only after PNG chunk CRC, dimensions and pixel-stream checks.
Interrupted jobs resume verified frames. Replaced frames move to `cache_archive`;
historical renders are not deleted. `render_state_v2.json` is atomically replaced.
Dashboard job failures preserve logs and release the job slot. After restart,
an unfinished job appears as interrupted. Retry once the previous process exits.
Studio checks for a current visual receipt before recomposing captions and checks
the resulting video before marking a job passed.

## Sound and diagnostics

`shortforge/sfx.py` creates original deterministic assembly, water, electric,
transition, impact and ambient effects. Add a beat cue such as
`{"name":"electric","offset":0.2,"gain_db":-30}`. Effects mix under normalized
narration and a final limiter. Default storyboards leave effects opt-in.
The reviewed solar example uses four quiet cues. It also uses top-screen
`callout` labels to identify DC, AC, storage and the grid.

To use the reviewed solar timing with its matching existing soundtrack, run
`shortforge compose STORY --out PROJECT --caption-timing TIMING.json`.
The cue text must match the storyboard and every cue must stay within its beat.
Recheck timing whenever the narration or voice changes.

`scripts/blender_audit.py`, executed by Blender, measures solar contacts and
renders six additional assembly angles. `scripts/verify_production.py PROJECT STORY`
checks actual streams, frame count, full decode, black segments and loudness;
it never sets human listening approval. `--monitor LOG` samples an active render.
Use `python -m shortforge.cli check VIDEO --storyboard STORY` to check an export
against its configured duration, resolution and frame rate.

Drive receives review artifacts only; large frame caches stay on the local SSD.
`outbox/latest` is the current review bundle and previous runs are archived by
the existing sync helper. Keep launchers in `Launchers`, reports in `Reviews`,
and use `Approved Videos` only after a human review.
