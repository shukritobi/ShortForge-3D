# ShortForge 3D Master Plan
Version: 0.2 (10 November 2026)
Status: Architecture contract; only explicitly labelled components are implemented.

## Product vision
A local-first educational 3D video studio which turns a checked problem-solution
storyboard into a reproducible, stylized animated mechanism. Starting use case:
40-second water-tower explainer on the existing Windows/RTX workstation.

**Primary engineering principle:** Story, assets, actions, cameras, materials,
audio, and output must be INDEPENDENT versioned components. Improving the tank
mesh must not require rewriting the script. Replacing the narrator must not
cause a new Blender render.

## Long-term repository layout
    shortforge/
      director/         # script generation, beat validator, fact check and research
      library/          # catalog, resolver, integrity and provenance
      scheduler/        # local GPU exclusivity, resume, retries and render cache
      qc/               # golden stills, camera framing, geometry audit, audio QA
      publisher/        # future approval-only upload, NOT enabled in phase 1
    engines/
      blender/
        assets/         # reusable parametric geometry builders
        actions/        # user-editable typed parameters, registered animation routines
        shaders/        # shared stylized PBR material templates
        cameras/        # portrait shot vocabulary and look-at rules
        rigs/           # vehicles, characters, machines, pumps and cranes
    assets/
      catalog.json      # implemented seed asset catalog
      models/           # glb / blend / obj exports in versioned packs
      materials/        # PBR texture sets, shader presets
      environments/     # roads, cities, landscapes, soil cutaways
      effects/          # water flow, excavation dust, assembly and arrows
      voices/           # licensed voice presets only, not giant pretrained weights
      sound/            # original/licensed SFX with provenance
    stories/
      water_tower/
        storyboard.json
        project.lock.json  # exact source revisions, asset versions, engine hashes
        source_notes.json  # evidence for technical claims
        reviews/           # feedback + reference golden stills
    output/               # ignored: renders/logs/multi-GB audio and frame sequences

Current repository does NOT yet implement the generalized subfolders above.
The assets/catalog.json seed documents entities still physically defined in
scripts/blender_water_tower.py. Migrate them without breaking that script.

## Asset metadata
Each asset must have:
- Stable ID (e.g. model.water_tower / action.fill_tank) and semver.
- Source path and generation method: procedural, authored Blender, imported GLB.
- Exact scale, units (meters for Blender), pivot, bounds, coordinate convention.
- Public parameter schema: dimensions, material slots, angles, LOD, detail settings.
- Dependencies (other assets/actions), minimum engine version.
- License + attribution + original source/provenance; hash for external assets.
- Status (prototype, validated, deprecated) and reproducibility seed.
- Preview thumbnail, 360-degree turntable, 3 canonical orthographic views.

## Animation-action interface
Design a typed action contract; AI can only invoke names in the registry.
    action: assemble_asset
    target_id: water_tower_01
    input: model.water_tower@1.0.0
    start_sec: 19.0
    end_sec: 23.0
    parameters: {method: "ground_to_top", easing: "smooth"}
    preconditions: [foundation_exists]
    postconditions: [support_top_reaches_tank_bottom]

Planned action primitives:
- reveal / hide / assemble / disassemble / translate / rotate / scale-from-anchor
- excavation / retaining_wall / formwork / reinforcement / pour_concrete
- pipe_route / valve_toggle / flow_volume / fill_tank / water_surface
- gravity_arrow / dimension_callout / show_pressure / material_swap
- camera_orbit / camera_track / camera_cutaway / camera_dolly
- character_walk / vehicle_drive / machine_cycle / infographic_pointer

All actions must support scrub/reverse and produce consistent animation at a
specified absolute frame. Use dependency graphs and keyframe state, never
random accumulating per-frame mutations.

## Parametric 3D models, not video hallucinations
Start with a reusable kit: seven house styles, four roof types, road, curb,
landscape/trees, terrain sections, pump, pipe elbow/Tee, valves, tanks,
tower bracing, stair/ladder, maintenance railing, characters and camera rigs.
Model variations share common attachments and pivot anchors. Reject disconnected
geometry (as our water tower originally demonstrated). When borrowing third-party
Blender/SketchUp/GLB assets, store provenance and ensure redistribution rights.

Build a bounded, seedable procedural variation engine for house colors, roof
materials, trees and layout positions while preserving exact pipe connections.

## Story and research
A problem-solution beat has: claim, why the problem occurs, implemented solution,
required mechanism, narration, duration, actions, camera, SFX, and evidence links.
The director must fact-check claims and reject unsupported precise measurements.
Scripts should be ORIGINAL; don't reproduce creator scripts or imply equivalence.

Default 40-second profile: 8 beats, ~90-110 English words, 24 FPS draft.
Future profiles: 60/75/90-second explainers, localization and different voices.
No scene renderer should depend directly on the LLM prompt wording.

## Visual regression and automatic improvement
For each validated mechanism record at least 8 golden frames including
pre-appearance, during assembly, after assembly, cutaway, and final reveal.
Acceptance checks:
- invisible components before birth frame (keyframed hide_render/visibility)
- mesh collision/interpenetration and floating-part tolerances
- minimum pipe thickness in rendered pixels
- no objects outside camera safe region for captions
- framing includes principal subject in closing shot
- material palette contrast; lighting/ambient shadow visibility
- complete source frame range (960/960), ffprobe 40s, video/audio streams
- manually annotated feedback per frame with issue severity

Every change rerenders golden frames first. Keep a dated accepted baseline and
compare pixel/feature differences; intentional changes require human approval.

## Reproducibility, caching, and records
For each run create a project.lock.json and run_manifest.json capturing:
storyboard hash; asset IDs+versions+content hashes; camera preset versions;
action library commit SHA; Blender version; render settings; random seed;
TTS provider/checkpoint revision/voice/synthesis settings; audio and captions
timestamps; ffmpeg/Remotion versions; quality test results; approvals.

Artifact fingerprint = SHA256(storyboard + asset lock + action versions +
camera preset versions + Blender version + render settings + seed).
Unchanged shots reuse rendered frames; voice/script-only changes invalidate
audio/captions/composite but do NOT invalidate 3D geometry if timing unaffected.
Never copy unverified stale outputs to latest.

## GPU and job management
Single Windows workstation: one GPU-intensive worker at a time.
Stages: script -> fact check -> lock assets -> generate narration -> render
golden stills -> approve -> render 960 frames -> compose -> QA -> archive.
Use SQLite queue first; later add a dashboard and optional durable worker.
Store caches and intermediate frames on a local fast SSD; sync MP4,
contact sheets, JSON reports and small preview artifacts to Drive. Avoid
syncing thousands of PNG frames by default.

## Rollout phases (gated; no invented completion dates)
0. **Current** Blender water tower visibility, anchored assembly, six-frame QA.
1. **Current** Isolated local Qwen3-TTS 0.6B, Kokoro alternative, WAV + FFmpeg.
2. **Next** Lock one reproducible end-to-end 40-second water-tower draft,
   review captions/audio/visuals, save goldens and a complete run manifest.
3. Extract water-tower and 7 houses as standalone parametrized asset builders.
4. Introduce action registry with schemas, dependencies, and property edits.
5. New scenes: household water well, swimming pool, fireplace (one at a time);
   measure reuse vs scene-specific manual coding.
6. Build storyboard web dashboard, visual editor, job queue, progress/log viewer.
7. Create self-hosted library viewer: tag search, thumbnails, version compare,
   before/after rerender, variant presets and approved asset releases.
8. Expand to 20+ vetted mechanisms, batch jobs and reusable storytelling kits.
9. Only after final-video approval flow and quotas: optional YouTube publishing.

## Definition of done: library V1
- At least 20 validated reusable model assets, 10 typed animation actions,
  7 camera presets, 1 material style pack, 1 captions pack and 2 narration voices.
- Every reusable asset has provenance, unit test, visible golden frames and semver.
- A second distinct Short can be generated without modifying the core renderer.
- A revised asset triggers an explicit preview/review rather than silently
  changing previously approved outputs.
