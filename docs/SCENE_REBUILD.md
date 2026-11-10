# ShortForge 3D: Water Tower Scene Rebuild (Phase 1 visual QA)

## What changed
The original preview showed isolated discs floating in the sky, thin near-invisible
supports, overly simple box houses, an overextended camera view and piping
buried under/behind a single terrain slab.

The new deterministic renderer uses:
- 4 substantial slanted load-bearing legs with ground footings
- 8 connected X-braces on the tower's visible sides
- an anchored bottom dish and a real curved tank wall with near-side cutaway
- water volume and surface animated with a fixed bottom datum
- a water riser physically connected to the elevated storage
- pitched roofs, door/window reveals, plinths, sidewalks, trees and road details
- 7 service branch networks linked to a below-grade distribution main
- an open excavation strip so blue mains can be seen without transparent soil
- shot-specific portrait camera framing and 0.5-second camera movements

All geometry is built in a single persistent Blender scene. The title,
narration, 8-beat / 40s timeline and action allowlist remain unchanged.

## Run the six-frame visual QA

From the existing local project (on feature branch, after git pull):

    python scripts/pc_agent.py review

The PC agent runs Blender once and exports:
- output/water_tower/preview_0120.png (5.0s, early neighbourhood)
- output/water_tower/preview_0240.png (10.0s, pumping station)
- output/water_tower/preview_0480.png (20.0s, connected tower supports growing)
- output/water_tower/preview_0576.png (24.0s, tank shell and water)
- output/water_tower/preview_0720.png (30.0s, underground pipe cutaway)
- output/water_tower/preview_0888.png (37.0s, distribution/payoff)
- output/water_tower/contact_sheet.png (3-column review montage, FFmpeg)
- output/water_tower/preview.png (latest frame for legacy launcher)
- output/water_tower/scene_manifest.json (component count and geometry audit)

You can instead call:

    shortforge render examples/water_tower_40s.json --out output/water_tower --preview-frames 120,240,480,576,720,888

The PC agent logs stderr/stdout and diagnostic JSON under output/diagnostics.
YouTube upload remains out of scope. Piper is not needed for visual QA.

## Review criteria
1. At 20s, the supports should grow from the ground, with no floating tank parts.
2. At 24s, the cutaway shell should sit on the dish and the water should be visible.
3. At 30s, the blue main must be clearly within the exposed below-grade trench.
4. Service branches lead from the main to the houses.
5. Zoom/framing should convey one construction mechanism at a time.
6. The closing view should show a coherent neighbourhood and tower.

Scene manifest assertions run after Blender and reject 3 missing support-related
categories, disconnected tank height and above-ground main pipes. This is a
structural check, not visual image analysis. Real Blender frame quality still
needs review on Windows.

## Next tasks after the review
- Inspect screenshot montage and adjust exact shot framing/material contrast.
- Fix any actual Blender 4.5 rendering failures shown in PC agent logs.
- Once visual QA passes, install Piper English and render 960 frames.

## Google Drive one-click launcher

Copy `scripts/ShortForge-Review.bat` to `G:\My Drive\ChatGPT ShortForge 3D` (a
copy is provided there). Double-click it to fast-forward the feature branch,
render the six review stills and sync `contact_sheet.png`, `scene_manifest.json`,
`preview.png`, all six numbered preview stills, and diagnostic logs to
`outbox/latest`. It refuses to update the wrong branch. No video publishing.
