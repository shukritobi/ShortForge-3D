"""Offline-after-download narration worker for a dedicated .venv-tts.

Run via the main ShortForge CLI, not directly. Loads one TTS checkpoint for the
entire script rather than loading the model for every beat.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from shortforge.contract import load_storyboard


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
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"ShortForge TTS loading {model_id} on {device}", flush=True)
    if device == "cpu":
        print("WARNING: CPU-only Qwen narration may be slow.",flush=True)
    model = Qwen3TTSModel.from_pretrained(
        model_id, device_map=device,
        dtype=torch.bfloat16 if device != "cpu" else torch.float32,
        attn_implementation="sdpa",  # no FlashAttention build needed on Windows
    )
    speakers = model.get_supported_speakers()
    voice = resolve_voice(voice, speakers)
    for index, beat in enumerate(story["beats"]):
        print(f"Synthesizing {index+1}/{len(story['beats'])}: {beat['id']}", flush=True)
        wavs, sr = model.generate_custom_voice(
            text=beat["narration"], language="English", speaker=voice,
        )
        if not wavs:
            raise RuntimeError(f"Model produced no audio for beat {beat['id']}")
        sf.write(str(output / f"beat_{index:02d}_raw.wav"), wavs[0], sr)


def render_kokoro(story, output, model_id, voice):
    import numpy as np
    import soundfile as sf
    import torch
    from kokoro import KPipeline
    if not voice.startswith(("af_", "am_", "bf_", "bm_")):
        raise ValueError("Kokoro voice should start with af_, am_, bf_ or bm_")
    lang = "b" if voice.startswith(("bf_", "bm_")) else "a"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipeline = KPipeline(lang_code=lang, repo_id=model_id, device=device)
    print(f"ShortForge Kokoro loaded on {device}", flush=True)
    for index, beat in enumerate(story["beats"]):
        segments = []
        for result in pipeline(beat["narration"], voice=voice, speed=1.0):
            if result.audio is not None:
                segments.append(result.audio.detach().cpu().numpy())
        if not segments:
            raise RuntimeError(f"Kokoro produced no audio for beat {beat['id']}")
        sf.write(str(output / f"beat_{index:02d}_raw.wav"),
                 np.concatenate(segments).astype("float32"), 24000)


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
