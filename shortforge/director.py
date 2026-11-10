"""Offline template plus optional local Ollama story planning. No remote APIs."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.request import Request, urlopen
from .contract import validate_storyboard

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = ROOT / "examples" / "water_tower_40s.json"

SYSTEM_PROMPT = """
You write ORIGINAL English educational micro-documentaries in second person.
A story builds one persistent 3D scene by repeating:
simple idea -> new problem -> physical solution -> next problem.
Return exactly ONE JSON object (no markdown) with these fields:
version=1, title, duration=40, fps=24, resolution=[720,1280], beats.
beats must have id (unique string), start, end, problem, solution,
narration (1-2 plain English sentences), camera and actions.
Times cover 0 to 40 with no gaps. Use 7-10 beats.
Only permitted cameras: wide, houses, pump, tower, cutaway, distribution, reveal.
Only permitted actions: show_house, show_houses, show_pump, show_tower,
fill_tank, show_pipes, flow_water, show_all.
Create roughly 95-115 words of narration for 40 seconds.
Avoid invented facts, precise claims without evidence, unsafe advice,
and any references to existing channels or their scripts.
This animation registry only depicts water supply infrastructure.
Do not try to animate other topics until matching action plugins exist.
"""


def template_storyboard(topic: str) -> dict:
    if topic.casefold().strip() not in {
        "how a water tower supplies an entire neighbourhood",
        "water tower", "water tower supplies an entire neighborhood",
    }:
        raise ValueError("template engine currently supports only the water-tower reference")
    return validate_storyboard(json.loads(SAMPLE_PATH.read_text(encoding="utf-8")))


def ollama_storyboard(topic: str, *, model: str = "qwen3:8b", url: str = "http://127.0.0.1:11434") -> dict:
    """Local model must return the same allowlisted structure; no arbitrary scripts."""
    if "water tower" not in topic.casefold():
        raise ValueError("registered Blender actions currently support water-tower topics only")
    payload = json.dumps({
        "model": model, "stream": False, "format": "json",
        "options": {"temperature": 0.35},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Write a 40-second storyboard for: {topic}. Finish with a construction payoff."},
        ],
    }).encode("utf-8")
    request = Request(
        url.rstrip("/") + "/api/chat", data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.load(response)
    except Exception as exc:
        raise RuntimeError(f"local Ollama request failed: {exc}") from exc
    content = result.get("message", {}).get("content", "")
    # Some reasoning models emit a textual preamble; reject rather than executing it.
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Ollama did not return clean JSON; regenerate the storyboard") from exc
    return validate_storyboard(data)
