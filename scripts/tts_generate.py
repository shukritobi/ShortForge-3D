"""Offline-after-download narration worker for a dedicated .venv-tts.

Run via the main ShortForge CLI, not directly. Loads one TTS checkpoint for the
entire script rather than loading the model for every beat.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from shortforge.contract import load_storyboard


def log_metric(output, **fields):
    path = output.parent / "tts_metrics.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"time":time.time(), **fields}) + "\n")


def cache_key(beat, model_id, voice, provider):
    h = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    value = json.dumps([beat["narration"],model_id,voice,provider,h],sort_keys=True)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sample_saved(output, index, beat, model_id, voice, provider):
    target = output / f"beat_{index:02d}_raw.wav"
    meta = output / f"beat_{index:02d}_cache.json"
    if not target.is_file() or not meta.is_file() or target.stat().st_size < 100:
        return False
    try:
        stored = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return stored.get("key") == cache_key(beat,model_id,voice,provider)


def save_sample(output, index, beat, model_id, voice, provider, wav, rate):
    import soundfile as sf
    target = output / f"beat_{index:02d}_raw.wav"
    sf.write(str(target), wav, rate)
    (output / f"beat_{index:02d}_cache.json").write_text(
        json.dumps({"key":cache_key(beat,model_id,voice,provider),
                    "duration_sec":round(len(wav)/rate,3),"sample_rate":rate},indent=2)+"\n",
        encoding="utf-8"
    )
    return len(wav) / rate


def resolve_voice(voice, supported):
    """Qwen reports lowercase speaker names; accept display-case user choices."""
    if not supported:
        return voice
    by_casefold = {name.casefold(): name for name in supported}
    canonical = by_casefold.get(voice.casefold())
    if not canonical:
        raise ValueError(f"Voice {voice!r} unavailable. Model speakers: {supported}")
    return canonical


def render_qwen(story, output, model_id, voice):
    # User-visible speaker names can be capitalized; official Qwen speaker
    # identifiers are lowercase. Check all voice caches before any model load.
    voice = voice.casefold()
    if all(sample_saved(output, index, beat, model_id, voice, "qwen")
           for index, beat in enumerate(story["beats"])):
        log_metric(output, event="all_beats_cached", provider="qwen",
                   beats=len(story["beats"]), model_load_skipped=True)
        for beat in story["beats"]:
            log_metric(output, event="beat_cached", beat=beat["id"],
                       device="not_loaded")
        print("All Qwen beats cached; model load and GPU inference skipped.", flush=True)
        return
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"ShortForge TTS loading {model_id} on {device}", flush=True)
    if device == "cpu":
        print("WARNING: CPU-only Qwen narration may be slow.",flush=True)
    model_start = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        model_id, device_map=device,
        dtype=torch.bfloat16 if device != "cpu" else torch.float32,
        attn_implementation="sdpa",  # no FlashAttention build needed on Windows
    )
    log_metric(output, event="model_loaded", provider="qwen",
               seconds=round(time.perf_counter()-model_start,2),
               device=device, cuda=torch.cuda.is_available(), model_id=model_id)
    speakers = model.get_supported_speakers()
    voice = resolve_voice(voice, speakers)
    for index, beat in enumerate(story["beats"]):
        if sample_saved(output,index,beat,model_id,voice,"qwen"):
            log_metric(output,event="beat_cached",beat=beat["id"],device=device)
            print(f"Reusing unchanged beat {beat['id']} cached audio",flush=True)
            continue
        print(f"Synthesizing {index+1}/{len(story['beats'])}: {beat['id']}", flush=True)
        start = time.perf_counter()
        # A hard codec-token budget prevents unbounded open-ended generation.
        # This is NOT an audio time-stretch: every output must pass timing QA.
        max_tokens = max(100, min(260, int((beat["end"] - beat["start"]) * 17 + 35)))
        wavs, sr = model.generate_custom_voice(
            text=beat["narration"], language="English", speaker=voice,
            max_new_tokens=max_tokens
        )
        elapsed=time.perf_counter()-start
        if not wavs:
            raise RuntimeError(f"Model produced no audio for beat {beat['id']}")
        duration=save_sample(output,index,beat,model_id,voice,"qwen",wavs[0],sr)
        allocated=round(torch.cuda.max_memory_allocated()/2**20,1) if device.startswith("cuda") else None
        log_metric(output,event="beat_generated",beat=beat["id"],
                   seconds=round(elapsed,2),audio_seconds=round(duration,3),
                   real_time_factor=round(elapsed/max(duration,.01),2),
                   max_new_tokens=max_tokens,cuda_alloc_peak_mb=allocated,
                   words=len(beat["narration"].split()),device=device)
        print(f"Beat {beat['id']}: audio={duration:.2f}s, synthesis={elapsed:.2f}s, "
              f"RTF={elapsed/max(duration,.01):.2f}x, token_budget={max_tokens}",flush=True)


def render_kokoro(story, output, model_id, voice):
    import numpy as np
    import soundfile as sf
    import torch
    from kokoro import KPipeline
    if not voice.startswith(("af_", "am_", "bf_", "bm_")):
        raise ValueError("Kokoro voice should start with af_, am_, bf_ or bm_")
    lang = "b" if voice.startswith(("bf_", "bm_")) else "a"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_start = time.perf_counter()
    pipeline = KPipeline(lang_code=lang, repo_id=model_id, device=device)
    log_metric(output,event="model_loaded",provider="kokoro",
               seconds=round(time.perf_counter()-model_start,2),device=device)
    print(f"ShortForge Kokoro loaded on {device}", flush=True)
    for index, beat in enumerate(story["beats"]):
        if sample_saved(output,index,beat,model_id,voice,"kokoro"):
            log_metric(output,event="beat_cached",beat=beat["id"],device=device)
            continue
        started = time.perf_counter()
        segments = []
        for result in pipeline(beat["narration"], voice=voice, speed=1.0):
            if result.audio is not None:
                segments.append(result.audio.detach().cpu().numpy())
        if not segments:
            raise RuntimeError(f"Kokoro produced no audio for beat {beat['id']}")
        wav = np.concatenate(segments).astype("float32")
        duration = save_sample(output,index,beat,model_id,voice,"kokoro",wav,24000)
        elapsed = time.perf_counter()-started
        log_metric(output,event="beat_generated",beat=beat["id"],device=device,
                   seconds=round(elapsed,2),audio_seconds=round(duration,3),
                   real_time_factor=round(elapsed/max(duration,.01),2),
                   words=len(beat["narration"].split()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=["qwen", "kokoro"], required=True)
    parser.add_argument("--voice", default="Ryan")
    parser.add_argument("--model-id", default=None)
    args = parser.parse_args()
    story = load_storyboard(args.storyboard)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output.parent / "tts_metrics.jsonl").unlink(missing_ok=True)
    model_id = args.model_id or (
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice" if args.provider == "qwen"
        else "hexgrad/Kokoro-82M")
    if args.provider == "qwen":
        render_qwen(story, args.output, model_id, args.voice)
    else:
        render_kokoro(story, args.output, model_id, args.voice)
    print("ShortForge narration beat synthesis completed.", flush=True)


if __name__ == "__main__":
    main()
