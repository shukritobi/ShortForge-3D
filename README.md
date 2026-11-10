# ShortForge 3D | Phase 1

Local-first, original, procedural **educational YouTube Shorts**. This implementation
builds a continuous stylized 3D water-tower neighbourhood in Blender, narrates
eight problem/solution beats with **offline English Piper TTS**, creates readable
captions, and produces a **40-second, 720×1280, 24 FPS draft MP4** with FFmpeg.

**Status:** Working source pipeline and testable contracts. A full Blender render
has not been benchmarked on the author's machine. The pipeline is deliberately
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
- Piper TTS executable plus **one locally downloaded English ONNX voice model**
  and its adjacent .onnx.json configuration. See https://github.com/OHF-Voice/piper1-gpl
- Optional: Ollama running locally for AI storyboard generation
- Optional: Node 20+ for Remotion compositor

Nothing requires commercial voice APIs, paid image generators or cloud services.
Model downloads, electricity and storage still have real costs.

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

Render and assemble a full **40-second narrated draft**, using a Piper
model already downloaded on your PC:

```powershell
shortforge run output/storyboard.json --out output/water_tower --voice "C:\Voices\en_US-lessac-medium.onnx"
```

You can override Blender, Piper, ffmpeg and ffprobe binary locations using
CLI flags. Full runs may take considerable time depending on GPU settings.

### Outputs

```text
output/water_tower/
  preview.png                   # optional single-frame check
  frames/frame_000001.png ...   # 960 Blender PNG frames
  audio/narration.wav           # Piper voice, precisely 40 seconds
  audio/beats/*.wav             # individually duration-fitted beat narration
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
Blender and Piper must be installed on the Windows workstation to render a full
video. A persistent dashboard, job queue, exact word alignment, fact-checking
agent, batch rendering and YouTube approval/upload workflow are later milestones.

**Publishing is deliberately disabled in Phase 1.**
