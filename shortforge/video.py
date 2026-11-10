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
    duration = story["duration"]
    missing = [i for i in range(1, story["fps"]*duration+1) if not (frames/f"frame_{i:06d}.png").is_file()]
    if missing:
        raise FileNotFoundError(f"missing {len(missing)} Blender frames; first missing frame: {missing[0]:06d}")
    if not wav.exists():
        raise FileNotFoundError(f"narration not found: {wav}")
    ffmpeg = require_program(ffmpeg)
    aligned=out/"audio" if (out/"audio"/"beats"/"beat_00.wav").is_file() else None
    _,ass = write_captions(story,out/"captions",audio_dir=aligned)
    video = out/"draft.mp4"
    # libass takes a POSIX/escaped filter path; run with the working directory
    # set to the captions folder so Windows drive colons are never parsed as filters.
    ass_filter = "ass=captions.ass"
    effects=[]
    audio_filter="[1:a]loudnorm=I=-16:TP=-1.5:LRA=9[aud]"
    if any(b.get("sfx") for b in story["beats"]):
        from .sfx import mix_effects
        effects=["-i",str(mix_effects(story,out/"audio"/"sfx.wav"))]
        audio_filter=("[1:a]loudnorm=I=-16:TP=-1.5:LRA=9[voice];"
                      "[voice][2:a]amix=inputs=2:normalize=0,alimiter=limit=0.84:level=0[aud]")
    subprocess.run(
        [ffmpeg,"-hide_banner","-loglevel","error","-y",
         "-framerate",str(story["fps"]),"-start_number","1",
         "-i",str(frames/"frame_%06d.png"),
         "-i",str(wav),
         *effects,
         "-filter_complex",f"[0:v]{ass_filter}[sub];{audio_filter}",
         "-map","[sub]","-map","[aud]",
         "-c:v","libx264","-preset","medium","-crf","18",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
         "-t",str(duration),"-ar","48000","-movflags","+faststart",str(video)],
        cwd=str(out/"captions"),check=True,
    )
    return video


def inspect_video(path: str | Path, *, ffprobe="ffprobe",
                  expected_duration: float = SECONDS, expected_fps=FPS,
                  expected_resolution=(WIDTH,HEIGHT)) -> dict:
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
        "duration_ok": abs(duration-expected_duration) <= .35,
        "resolution_ok": (v["width"],v["height"]) == tuple(expected_resolution),
        "fps_ok": abs(fps-expected_fps) < .05,
        "frame_count_ok": int(v.get("nb_frames",round(duration*fps))) == round(expected_duration*expected_fps),
        "audio_present": True,
    }
    if not all(checks.values()):
        raise RuntimeError(f"output QA failed: {checks}; duration={duration:.3f}, fps={fps:.2f}")
    return {"duration":duration,"fps":fps,"width":v["width"],"height":v["height"],**checks}
