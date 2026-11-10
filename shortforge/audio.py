"""Offline Piper narration, rendered beat-by-beat to preserve storyboard timing."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
import wave

from .contract import validate_storyboard


def require_program(name: str) -> str:
    binary = shutil.which(name)
    if not binary:
        raise RuntimeError(f"required local executable not found: {name}")
    return binary


def probe_duration(path: Path, ffprobe: str = "ffprobe") -> float:
    r = subprocess.run(
        [require_program(ffprobe),"-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(path)],
        text=True, capture_output=True,check=True,
    )
    return float(r.stdout.strip())


def create_audio(story: dict, output: str | Path, *, model: str, piper="piper", ffmpeg="ffmpeg", ffprobe="ffprobe") -> Path:
    """Requires a downloaded Piper English .onnx model + neighboring .json config."""
    validate_storyboard(story)
    model_path = Path(model).resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"Piper voice model missing: {model_path}")
    if not Path(str(model_path)+".json").is_file():
        raise FileNotFoundError(f"Piper model config missing: {model_path}.json")
    piper = require_program(piper)
    ffmpeg = require_program(ffmpeg)
    out = Path(output)
    out.mkdir(parents=True,exist_ok=True)
    beats_dir = out/"beats"
    beats_dir.mkdir(parents=True,exist_ok=True)
    processed = []
    for index, beat in enumerate(story["beats"]):
        raw = beats_dir / f"beat_{index:02d}_raw.wav"
        adjusted = beats_dir / f"beat_{index:02d}.wav"
        subprocess.run(
            [piper,"--model",str(model_path),"--output_file",str(raw)],
            input=beat["narration"]+"\n",text=True,check=True,
            stdout=subprocess.DEVNULL,
        )
        duration = probe_duration(raw,ffprobe)
        allotted = beat["end"]-beat["start"]
        target = allotted-.12
        speed = duration/target
        if not .7 <= speed <= 1.4:
            raise RuntimeError(
                f"Beat {beat['id']} narration lasts {duration:.1f}s for {allotted:.1f}s; "
                "rewrite it or select another voice instead of extreme time stretching"
            )
        subprocess.run(
            [ffmpeg,"-hide_banner","-loglevel","error","-y","-i",str(raw),
             "-af",f"atempo={speed:.6f},apad,atrim=duration={allotted:.6f},asetpts=PTS-STARTPTS",
             "-ar","24000","-ac","1","-c:a","pcm_s16le",str(adjusted)],
            check=True,
        )
        processed.append(adjusted)
    # The concat demuxer requires identical channel/rate/codecs, enforced above.
    listing = beats_dir/"concat.txt"
    listing.write_text("".join("file '"+f.resolve().as_posix().replace("'","'\\''")+"'\n" for f in processed),encoding="utf-8")
    narration = out/"narration.wav"
    subprocess.run(
        [ffmpeg,"-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
         "-i",str(listing),"-c:a","pcm_s16le",str(narration)],check=True,
    )
    actual = probe_duration(narration,ffprobe)
    if abs(actual-40) > .12:
        raise RuntimeError(f"audio duration {actual:.3f}s, expected 40s")
    return narration
