"""Narration pipeline: Qwen3-TTS (primary), Kokoro (fallback), or explicit silence.

TTS models live in a separate .venv-tts, loaded once for all 8 beats.
No Windows SAPI, no cloud TTS API, no paid services.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .contract import validate_storyboard

ROOT = Path(__file__).resolve().parents[1]


def require_program(name: str) -> str:
    """Accept a specific executable path or look it up on PATH."""
    p = Path(name)
    if p.is_file():
        return str(p.resolve())
    binary = shutil.which(name)
    if not binary:
        raise RuntimeError(f"required local executable not found: {name}")
    return binary


def probe_duration(path: Path, ffprobe: str = "ffprobe") -> float:
    run = subprocess.run(
        [require_program(ffprobe), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True, capture_output=True, check=True
    )
    return float(run.stdout.strip())


def voice_python(provider: str, override: str | None = None) -> str:
    if override:
        return require_program(override)
    binary = ROOT / ".venv-tts" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not binary.is_file():
        raise RuntimeError(
            "High-quality TTS runtime missing: " + str(binary) +
            ". See docs/TTS_SETUP.md for the one-time local install."
        )
    return str(binary.resolve())


def create_silent_audio(output: str | Path, *, ffmpeg="ffmpeg") -> Path:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "narration.wav"
    subprocess.run([
        require_program(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", "40", "-c:a", "pcm_s16le", str(path)
    ], check=True)
    return path


def create_audio(story: dict, output: str | Path, *, provider="qwen",
                 voice="Ryan", model_id: str | None = None,
                 python: str | None = None,
                 ffmpeg="ffmpeg", ffprobe="ffprobe") -> Path:
    """Run external TTS worker once, fit audio per beat, produce 40-second WAV.

    First successful Qwen/Kokoro run downloads open model weights into the HF
    cache. Later synthesis is local; no API keys or usage fees are required.
    """
    validate_storyboard(story)
    if provider not in {"qwen", "kokoro"}:
        raise ValueError("provider must be qwen or kokoro")
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    beats_dir = out / "beats"
    beats_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = require_program(ffmpeg)
    runtime = voice_python(provider, python)
    story_path = out / "tts_input.json"
    story_path.write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cmd = [
        runtime, "-u", str(ROOT / "scripts" / "tts_generate.py"),
        "--storyboard", str(story_path),
        "--output", str(beats_dir),
        "--provider", provider, "--voice", voice
    ]
    if model_id:
        cmd += ["--model-id", model_id]
    # Generate and cache all beats in one inference process: prevents 8x model loads.
    subprocess.run(cmd, check=True, cwd=str(ROOT))

    adjusted = []
    for index, beat in enumerate(story["beats"]):
        raw = beats_dir / f"beat_{index:02d}_raw.wav"
        target = beats_dir / f"beat_{index:02d}.wav"
        if not raw.is_file() or raw.stat().st_size < 100:
            raise RuntimeError(f"TTS failed to create beat {beat['id']} audio")
        duration = probe_duration(raw, ffprobe)
        allotted = beat["end"] - beat["start"]
        tempo = duration / max(.5, allotted-.15)
        # Reject extreme speedups; the script should be edited instead.
        if not .65 <= tempo <= 1.7:
            raise RuntimeError(
                f"Beat {beat['id']} voice {duration:.2f}s does not fit "
                f"its {allotted:.2f}s shot (tempo={tempo:.2f}). "
                "Shorten the script or adjust the voice pacing before a full render."
            )
        subprocess.run([
            ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(raw),
            "-af", f"atempo={tempo:.6f},apad,atrim=duration={allotted:.6f},asetpts=PTS-STARTPTS",
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(target)
        ], check=True)
        adjusted.append(target)
    listing = beats_dir / "concat.txt"
    listing.write_text("".join(
        "file '" + path.resolve().as_posix().replace("'", "'\\''") + "'\n"
        for path in adjusted
    ), encoding="utf-8")
    output_file = out / "narration.wav"
    subprocess.run([
        ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c:a", "pcm_s16le", str(output_file)
    ], check=True)
    actual = probe_duration(output_file, ffprobe)
    if abs(actual-40) > .15:
        raise RuntimeError(f"Narration duration {actual:.3f}s, expected 40s")
    (out / "voice_manifest.json").write_text(
        json.dumps({
            "provider": provider, "voice": voice,
            "model_id": model_id or (
                "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice" if provider == "qwen"
                else "hexgrad/Kokoro-82M"),
            "duration": round(actual,3),
            "beats": len(adjusted),
            "engine": "local_tts"
        }, indent=2) + "\n", encoding="utf-8"
    )
    return output_file
