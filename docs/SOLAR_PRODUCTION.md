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

## Measure narration before cutting the shots

1. Create a Solar project in Studio and choose a target duration.
2. Select **Check narration** to measure the actual Qwen takes.
3. The fitter assigns each beat the measured take duration at the chosen rate
   plus a short pause. Shorten or add meaningful script lines for a fixed
   duration. Studio can extend the timeline when the speech needs more room.
4. Generate the preview from that timed storyboard, inspect it, then approve.
5. Render the video. Unchanged voice samples remain cached.

Generated solar storyboards default to `narration_timing: native`.
`scripts/verify_native_voice.py PROJECT` compares their fitted spoken PCM
prefixes against the raw takes. For the current director cut, start with
`examples/solar_neighbourhood_112s_v2.json`. It applies one pitch-preserving
`narration_rate: 1.07` across all 12 takes. Use that pace as the starting point
for subsequent reviews. The raw takes remain cached. The 120-second example
preserves the original native-speed edit.

The first raw take had a high-frequency burst around 7.8 kHz before speech.
The director cut removes 1.11 seconds from that exact WAV and uses a 15 ms
fade-in. The storyboard stores the WAV fingerprint so a fresh take is safe
from an old trim. Check the source and rendered opening independently when
the voice, model, or first line changes.

For the full solar script, `shot_cues` gives each beat a short list of
allowlisted camera subjects and positions within the beat. After measuring
the audio, check these cuts against the spoken terms. The current edit moves
from the roof to the metal grid, then to the mounting gap and silicon junction.
The equipment sequence lands on the inverter, breaker bank, porch diffuser,
meter and battery. The bypass scene reveals the diode first and then shows its
path around the central shaded group.

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

The four neighbours reuse the main house's facade openings, trim and gable
construction. Siding, setbacks, gardens, three flashed chimneys and scattered
blade meshes add variation. The car and cyclist share the street scale.
Background houses stay outside the main camera bounds. The two PV demonstration
models sit on a small separate set, clear of the street.

The daylight revision uses a procedural sky and cloud background, a deeper
tree line, siding and roof relief, and a leaf mesh on the shaded cell. Large
area lights fill the service wall, porch and side yard. Separate lights cover
the silicon and diode demonstration sets. Check lighting on the subject's face
and retain enough contrast to distinguish its edges, labels and neighbouring
parts. The meter and breaker labels are part of the 3D models.

The full cut uses Blender 4.5.2 EEVEE with its ray-tracing option off. A Cycles
OptiX still of the same breaker shot provides a reference for the additional
bounce lighting. The side-by-side image includes the previous cut, daylight
EEVEE and the Cycles still. Use `output/solar_daylight` for the current movie
and `output/solar_daylight_comparison` for that comparison.

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
