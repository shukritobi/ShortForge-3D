# Phase 1 engineering notes

## Narrative contract

A storyboard has exactly eight current reference beats covering 0..40s without gaps.
Each beat contains: an original narration, a problem, a physical solution, a
camera preset, and an array of allowlisted scene actions.

The Python contract validates the AI output **before** launching Blender.
The Blender entrypoint repeats the most important checks inside Blender's
separate Python runtime. Only static functions are executed, no downloaded
scripts.

## Visual pipeline

- Persistent orthographic low-poly neighbourhood
- Stage 1: original house
- Stage 2: six additional homes
- Stage 3: pumping station
- Stage 4: context for fluctuating demand
- Stage 5: steel tower and elevated tank
- Stage 6: water mains and visible flow markers
- Stage 7: distribution to service risers
- Stage 8: overview payoff shot

Draft: 720×1280 at 24 FPS, exactly 960 PNG frames.
Use --preview-frame 480 first to inspect composition, material readability,
occlusion and whether tank and pipes are visible.

## Audio and captions

Piper creates one WAV per story beat. FFmpeg gently rate-adjusts it to the
beat duration and pads/trims each beat exactly. A duration overrun beyond
accepted stretch limits causes a visible error, not an incomplete silent clip.

Captions are divided into short phrases with weighted timing inside each
beat. They require a human preview because they are *not* forced alignment.
FFmpeg/libass burns captions into the draft, while the Remotion example can
read the same JSON. Both systems are local.

## Files and review

Run quality checks before approving any video. A quality.json with SHA256
is created next to the draft. No upload or publication exists in this phase.
The output folder is .gitignored; do not commit models, credentials, or videos.

## Follow-on milestones

1. Visual review of a real Blender preview still and complete 40s render
2. Exact word alignment with Faster Whisper
3. Reusable procedural scene-action plugins for new topics
4. Local web dashboard, persistent SQLite task queue, resumes/retries
5. Manual approval of a final 1080p master
6. Only then add an explicitly gated YouTube publisher
