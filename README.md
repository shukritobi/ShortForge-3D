# ShortForge 3D

## Phase 2: reusable long-form 3D videos (stacked PR)

Phase 2 adds a **second storyboard/renderer generation**, keeping the proven
40-second water-tower pipeline as a working baseline. It supports **60, 75,
90, 120 and 180 second** videos with registered mechanism-based scene packs,
starting with water distribution and rooftop solar energy. Both use shared
parametric houses, materials, cameras, object animation, TTS, captions,
resume-aware frames and FFmpeg composition.

The new renderer and profiles need their **first real PC preview** and should
not be treated as production-quality visuals until reviewed. Other topics
require registered, vetted scene and action packs; unsupported topics are
rejected rather than depicted inaccurately.

Read [Phase 2 setup and limits](docs/PHASE2.md). Create an example with:

```powershell
shortforge plan --engine library --topic "solar panels" --duration 120 --output output/solar_home_story.json
shortforge validate output/solar_home_story.json
```

For a six-frame Blender preview use the provided
`scripts/ShortForge-Phase2-Preview.bat` launcher. No YouTube publishing.

---

 | Phase 1

Local-first, original, procedural **educational YouTube Shorts**. This implementation
builds a continuous stylized 3D water-tower neighbourhood in Blender, narrates
eight problem/solution beats with **offline Qwen3-TTS or Kokoro**, creates readable
captions, and produces a **40-second, 720×1280, 24 FPS draft MP4** with FFmpeg.

**Status:** Windows Blender 4.5.2 has successfully rendered six local preview
frames; the new visibility/camera fixes and full narrated 960-frame run still need an on-PC visual review. The pipeline is deliberately
local-only: **NO YouTube upload or publishing code**, no paid API, no cloud rendering.

## First video

**How a Water Tower Supplies an Entire Neighbourhood**

The 3D scene is persistent, not separate generated AI clips. Houses, pumping
station, elevated storage, water mains, branching service pipes and animated
water markers appear progressively while the camera switches between seven
registered presets. AI-produced scripts can only select registered scene actions.

### Prerequisites (Windows PC)

- Python 3.10+ (tested with Python 3.11/3.13 for pure-Python stages)
- Blender 4.5 LTS with its executable on PATH (or supply an absolute path)
- FFmpeg and ffprobe on PATH
- Dedicated `.venv-tts` with **Qwen3-TTS 0.6B CustomVoice** (recommended),
  or Kokoro-82M as a lightweight alternative. See [setup](docs/TTS_SETUP.md)
- Optional: Ollama running locally for AI storyboard generation
- Optional: Node 20+ for Remotion compositor

Nothing requires commercial voice APIs, paid image generators or cloud services.
Model downloads, electricity and storage still have real costs.

### First: diagnose Blender on your PC

If your previous preview failed with required local executable not found: blender,
run the new local-only diagnostic utility first:

    python scripts/pc_agent.py doctor
    python scripts/pc_agent.py preview

It auto-detects normal Blender installations and writes detailed JSON reports in
output/diagnostics. To specify a custom Blender installation:

    python scripts/pc_agent.py preview --blender "D:\\Apps\\Blender\\blender.exe"

You can also run shortforge doctor or a reviewed JSON task in jobs/preview.json.
See docs/PC_AGENT.md for full instructions and privacy notes. The runner never
opens a port, uploads your logs, or executes arbitrary commands.

### Updated visual review: six Blender keyframes

The water tower has been rebuilt with connected legs/braces, explicit
keyframed pre-appearance hiding, a cutaway tank, exposed underground trench,
pitched-roof houses and improved final-reveal camera framing.
Run this **before** a full render (no Piper required):

```powershell
python scripts/pc_agent.py review
```

This creates `output/water_tower/contact_sheet.png`, six individual
`preview_XXXX.png` stills, `preview.png` for the existing Drive launcher, and
`scene_manifest.json` for structural checks. See [visual QA guide](docs/SCENE_REBUILD.md).

### Produce the FIRST full video on your Windows PC

The complete 40-second video can be generated **now**, first as a technical
silent draft using Blender + FFmpeg already installed:

```powershell
python scripts/pc_agent.py full --tts none
```

For **high-quality English narration**, install Qwen3-TTS in `.venv-tts`
(see [TTS setup](docs/TTS_SETUP.md)) and run:

```powershell
python scripts/pc_agent.py full --tts qwen --speaker Ryan
```

The script generates narration before rendering 960 frames. No Windows
built-in text-to-speech is used. A second launcher, `scripts/ShortForge-Video.bat`,
offers Qwen, Kokoro and explicit silent mode and copies the resulting MP4
and quality JSON to your Google Drive review folder. **No YouTube publishing.**

See [master plan](docs/MASTER_PLAN.md), [library catalog](assets/catalog.json)
and [render playbook](docs/RENDER_PLAYBOOK.md).

### Quick start

On Windows PowerShell:

```powershell
git clone https://github.com/shukritobi/ShortForge-3D.git
cd ShortForge-3D
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m pytest -q
shortforge plan --topic "water tower" --output output/storyboard.json
shortforge validate output/storyboard.json
shortforge run output/storyboard.json --out output/water_tower --dry-run
```

Preview a single frame before committing to a 960-frame render:

```powershell
shortforge render output/storyboard.json --out output/water_tower --preview-frame 480
```

Render and assemble a full **40-second narrated draft**, once Qwen3-TTS is installed:

```powershell
shortforge run output/storyboard.json --out output/water_tower --tts qwen --voice Ryan
```

You can override Blender, ffmpeg, ffprobe, TTS voice and the isolated
TTS Python path using CLI flags. Full runs may take considerable time depending on GPU settings.

### Outputs

```text
output/water_tower/
  preview.png                   # optional single-frame check
  frames/frame_000001.png ...   # 960 Blender PNG frames
  audio/narration.wav           # Qwen/Kokoro voice, precisely 40 seconds
  audio/beats/*.wav             # individually duration-fitted beat narration
  audio/voice_manifest.json    # TTS provider/model/voice settings
  captions/captions.json       # beat-constrained caption cues for Remotion
  captions/captions.ass        # burn-in captions (FFmpeg)
  draft.mp4                     # 720x1280, 24fps, AAC + H.264
  quality.json                  # duration/resolution/audio checks + SHA256
```

This phase uses **beat-relative caption timings** derived from the fitted
narration segments, not verified phoneme or word-level alignment. Preview
captions before distributing. In a future phase, Faster Whisper can align
individual words to real audio.

### Optional local AI director

The template storyboard is deterministic and is the recommended first test.
For AI generation, start Ollama locally and download a supported model:

```powershell
ollama pull qwen3:8b
shortforge plan --engine ollama --model qwen3:8b --topic "How a water tower supplies an entire neighbourhood" --output output/ollama_story.json
shortforge validate output/ollama_story.json
```

The AI director **cannot execute arbitrary Python** or invent new 3D actions.
Only the water-tower scene-action vocabulary is implemented; adding a fireplace,
pool or canal requires new geometry/animation plugins. Manually fact-check all
generated historical, engineering and safety assertions before publication.

### Remotion alternative

The default production path uses zero-dependency Python orchestration and
FFmpeg burn-in subtitles. See [apps/compositor/README.md](apps/compositor/README.md)
for the optional TypeScript/Remotion compositor consuming the same captions JSON.

### Quality gates

- Exact 40-second contiguous storyboard and bounded beat count.
- Action and camera allowlist; **no eval or user-defined code execution**.
- Each narration beat fits its visual allocation without extreme time stretching.
- Captions remain within each corresponding beat.
- ffprobe checks video resolution, FPS, duration, and presence of an audio stream.
- Final SHA256 recorded for subsequent human approval workflows.
- GitHub Actions run Python tests, syntax validation and compositor type checking.

### Production limitations

This is the *first* production slice, not a generalized AI-to-any-3D-video engine.
Blender + FFmpeg are needed for a technical silent MP4; a dedicated local
Qwen3-TTS or Kokoro environment enables the actual narrated Short. A persistent dashboard, job queue, exact word alignment, fact-checking
agent, batch rendering and YouTube approval/upload workflow are later milestones.

**Publishing is deliberately disabled in Phase 1.**
