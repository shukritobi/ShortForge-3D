# Detailed solar workflow

## Build the explanation before the camera sequence

The solar pack starts with the current-collector lines, then moves from roof
mounting to a magnified silicon cell. It explains electron–hole generation,
separation by the junction field, series current limits, bypass diodes, maximum
power tracking and the difference between energy storage and blackout backup.

The enlarged cell is a schematic teaching model. Its layer thicknesses,
particles and mounting plinth are enlarged for visibility. A hole represents
the absence of an electron. It is not another physical particle inside silicon.
The diode path represents bypassing a group, not a separate diode on every cell.

Technical references used for the script:

- [DOE photovoltaic cell basics](https://www.energy.gov/cmei/systems/solar-photovoltaic-cell-basics)
- [DOE performance and efficiency](https://www.energy.gov/cmei/systems/solar-photovoltaic-performance-and-efficiency-basics)
- [DOE system design](https://www.energy.gov/cmei/systems/solar-photovoltaic-system-design-basics)
- [NREL shading testbed](https://docs.nrel.gov/docs/fy16osti/62471.pdf)

## Native narration comes first

1. Create a Solar project in Studio and choose a target duration.
2. Select **Check narration**. Qwen speaks the script at its recorded pace.
3. The fitter assigns each shot its measured take duration and a short pause.
   If the takes exceed the target, the timeline extends rather than compressing
   speech. Shorten the script if the duration must be exact.
4. Generate the preview from that timed storyboard, inspect it, then approve.
5. Render the video. Unchanged voice samples remain cached.

New solar storyboards use `narration_timing: native`. Their fitting filters
contain no `atempo`. `scripts/verify_native_voice.py PROJECT` compares every
fitted spoken PCM prefix against its raw take. The measured 120-second example
has 249 words and 12 distinct shots. Raw speech totals 117.20 seconds, leaving
2.80 seconds for pauses across the timeline.

Earlier storyboards retain their legacy timing policy so historical projects
and tests remain reproducible. To migrate one, set `narration_timing` to
`native`, run narration measurement, and review the resulting timeline.

## Model review

`scripts/solar_neighbourhood.py` owns the detailed set. It reuses the common
primitives and existing roof-plane equations. The house wall is built around
clear door and window openings, with recessed infill and separate jambs,
casings, sill and threshold. Roof ends meet the underside of the pitched slabs.

The porch lamp is on the front facade. The inverter, breaker panel and meter
are on the side service wall. The supported battery is in the side yard.
This separates the luminaire from the electrical enclosures and improves
equipment readability. Wall-panel interiors are explanatory dead fronts.
These models are not installation instructions or clearance specifications.

The street has consistent setbacks, driveways, a sidewalk, gardens, varied
trees, a moving car and a coasting cyclist. Background objects remain separate
from the semantic hero-house camera bounds. Mechanism stages use explicit
editorial cuts, avoiding a camera flight through the gap between sets.

Check the six story frames and the additional audit angles before full renders.
The Blender audit measures 12 panel/rail contacts, meter attachment, three
lamp clearances and the two true facade openings. Materials and the set can
change without rewriting the narrative/action dispatcher.

## Folder layout

The shared Drive root contains the current Studio launcher, the latest-review
launcher, the verification launcher and `START HERE.txt`. Older top-level
launchers and notes are in `Archive/Previous top-level files`, with original
paths and hashes in each timestamped archive's manifest. Frame caches remain
on the workstation SSD.
