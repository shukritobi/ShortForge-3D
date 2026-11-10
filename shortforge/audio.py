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


def create_silent_audio(output: str | Path, *, duration: float = 40, ffmpeg="ffmpeg") -> Path:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "narration.wav"
    subprocess.run([
        require_program(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(duration), "-c:a", "pcm_s16le", str(path)
    ], check=True)
    return path


def create_audio(story: dict, output: str | Path, *, provider="qwen",
                 voice="Ryan", model_id: str | None = None,
                 python: str | None = None,
                 ffmpeg="ffmpeg", ffprobe="ffprobe") -> Path:
    """Run external TTS worker once, fit audio per beat, produce story-length WAV.

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
    # Never confuse yesterday's failed timing report or narration with this run.
    for name in ("timing_report.json", "voice_manifest.json"):
        (out / name).unlink(missing_ok=True)
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
    # Share immutable text/voice samples across projects and durations without
    # making tests or external output folders write into the user's cache.
    shared=ROOT/"output"/"voice_cache" if out.is_relative_to(ROOT/"output") else None
    if shared:
        from scripts.tts_generate import cache_key
        selected_model=model_id or ("Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice" if provider=="qwen" else "hexgrad/Kokoro-82M")
        shared.mkdir(parents=True,exist_ok=True)
        keys=[cache_key(b,selected_model,voice.casefold() if provider=="qwen" else voice,provider) for b in story["beats"]]
        for index,key in enumerate(keys):
            raw=beats_dir/f"beat_{index:02d}_raw.wav"
            meta=beats_dir/f"beat_{index:02d}_cache.json"
            cached=shared/(key+".wav")
            if cached.is_file() and (shared/(key+".json")).is_file():
                if not meta.is_file() or json.loads(meta.read_text()).get("key")!=key:
                    shutil.copy2(cached,raw)
                    shutil.copy2(shared/(key+".json"),meta)
    # Generate and cache all beats in one inference process: prevents 8x model loads.
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    if shared:
        for index,key in enumerate(keys):
            raw=beats_dir/f"beat_{index:02d}_raw.wav"
            meta=beats_dir/f"beat_{index:02d}_cache.json"
            if raw.is_file() and meta.is_file() and json.loads(meta.read_text()).get("key")==key:
                shutil.copy2(raw,shared/(key+".wav"))
                shutil.copy2(meta,shared/(key+".json"))

    # Validate the *whole* narration first; always produce a useful timing
    # report even when an individual beat fails to fit. CPU synthesis latency
    # and spoken audio duration are deliberately reported separately.
    rows = []
    for index, beat in enumerate(story["beats"]):
        raw = beats_dir / f"beat_{index:02d}_raw.wav"
        allotted = beat["end"] - beat["start"]
        duration = probe_duration(raw, ffprobe) if raw.is_file() and raw.stat().st_size > 100 else None
        natural_tempo = duration / max(.5, allotted-.15) if duration is not None else None
        # Avoid unnatural slow speech in long scenes: speak at native speed,
        # then let the scene breathe with silence at its tail.
        tempo = max(1.0, natural_tempo) if natural_tempo is not None else None
        limit=1.35 if story.get("version")==2 else 1.7
        ok = tempo is not None and tempo <= limit
        rows.append({
            "beat": beat["id"], "start_sec": beat["start"],
            "end_sec": beat["end"], "word_count": len(beat["narration"].split()),
            "spoken_audio_sec": round(duration,3) if duration is not None else None,
            "target_sec": allotted,
            "speed_adjustment": round(tempo,3) if tempo is not None else None,
            "status": "fits" if ok else ("missing_audio" if tempo is None else "needs_rewrite_or_regeneration"),
            "raw_file": raw.name,
        })
    problems = [x for x in rows if x["status"] != "fits"]
    timing_report = {
        "schema_version": 1, "provider": provider, "voice": voice,
        "status": "needs_review" if problems else "passed",
        "beats": rows, "failed_count": len(problems),
        "total_generated_speech_sec": round(sum(x["spoken_audio_sec"] or 0 for x in rows),3),
        "total_storyboard_sec": story["duration"],
        "message": f"Audio length is not synthesis computation time. Maximum speed is {limit}x.",
    }
    (out / "timing_report.json").write_text(json.dumps(timing_report,indent=2)+"\n",encoding="utf-8")
    if problems:
        first = problems[0]
        raise RuntimeError(
            f"Beat {first['beat']} spoken audio {first['spoken_audio_sec']}s "
            f"cannot fit {first['target_sec']}s (tempo {first['speed_adjustment']}). "
            f"See {out / 'timing_report.json'} and raw voice samples before rendering."
        )

    adjusted = []
    for index, beat in enumerate(story["beats"]):
        raw = beats_dir / f"beat_{index:02d}_raw.wav"
        target = beats_dir / f"beat_{index:02d}.wav"
        allotted = beat["end"] - beat["start"]
        tempo = rows[index]["speed_adjustment"]
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
    if abs(actual-story["duration"]) > .15:
        raise RuntimeError(f"Narration duration {actual:.3f}s, expected {story['duration']}s")
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
