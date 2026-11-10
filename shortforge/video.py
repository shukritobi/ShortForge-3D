"""FFmpeg assembly and ffprobe validation. All processing stays on the user's PC."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
from .audio import require_program, probe_duration
from .captions import write_captions
from .contract import validate_storyboard, WIDTH, HEIGHT, FPS, SECONDS


def compose(story: dict, output: str | Path, *, ffmpeg="ffmpeg") -> Path:
    validate_storyboard(story)
    out = Path(output).resolve()
    frames = out/"frames"
    wav = out/"audio"/"narration.wav"
    missing = [i for i in range(1, FPS*SECONDS+1) if not (frames/f"frame_{i:06d}.png").is_file()]
    if missing:
        raise FileNotFoundError(f"missing {len(missing)} Blender frames; first missing frame: {missing[0]:06d}")
    if not wav.exists():
        raise FileNotFoundError(f"narration not found: {wav}")
    ffmpeg = require_program(ffmpeg)
    _,ass = write_captions(story,out/"captions")
    video = out/"draft.mp4"
    # libass takes a POSIX/escaped filter path; run with the working directory
    # set to the captions folder so Windows drive colons are never parsed as filters.
    ass_filter = "ass=captions.ass"
    subprocess.run(
        [ffmpeg,"-hide_banner","-loglevel","error","-y",
         "-framerate",str(FPS),"-start_number","1",
         "-i",str(frames/"frame_%06d.png"),
         "-i",str(wav),
         "-filter_complex",f"[0:v]{ass_filter}[sub]",
         "-map","[sub]","-map","1:a:0",
         "-c:v","libx264","-preset","veryfast","-crf","22",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
         "-t",str(SECONDS),"-movflags","+faststart",str(video)],
        cwd=str(out/"captions"),check=True,
    )
    return video


def inspect_video(path: str | Path, *, ffprobe="ffprobe") -> dict:
    r = subprocess.run(
        [require_program(ffprobe),"-v","error","-show_streams","-show_format",
         "-of","json",str(path)],
        text=True,capture_output=True,check=True,
    )
    info = json.loads(r.stdout)
    streams = info.get("streams",[])
    v = next((s for s in streams if s.get("codec_type")=="video"),None)
    a = next((s for s in streams if s.get("codec_type")=="audio"),None)
    if not v or not a:
        raise RuntimeError("video must contain video and audio streams")
    duration = float(info["format"]["duration"])
    ratio = v.get("avg_frame_rate","0/1")
    n,d = (int(x) for x in ratio.split("/"))
    fps = n/d if d else 0
    checks = {
        "duration_ok": abs(duration-SECONDS) <= .35,
        "resolution_ok": (v["width"],v["height"]) == (WIDTH,HEIGHT),
        "fps_ok": abs(fps-FPS) < .05,
        "audio_present": True,
    }
    if not all(checks.values()):
        raise RuntimeError(f"output QA failed: {checks}; duration={duration:.3f}, fps={fps:.2f}")
    return {"duration":duration,"fps":fps,"width":v["width"],"height":v["height"],**checks}
