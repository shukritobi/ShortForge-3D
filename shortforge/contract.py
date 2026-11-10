"""Strict untrusted storyboard contract. Blender receives only allowlisted actions."""
from __future__ import annotations
import json
import math
from pathlib import Path

FPS = 24
WIDTH, HEIGHT = 720, 1280
SECONDS = 40
ACTION_TYPES = frozenset({
    "show_house", "show_houses", "show_pump", "show_tower",
    "fill_tank", "show_pipes", "flow_water", "show_all",
})
CAMERAS = frozenset({"wide", "houses", "pump", "tower", "cutaway", "distribution", "reveal"})
REQUIRED_BEAT_KEYS = {"id", "start", "end", "problem", "solution", "narration", "camera", "actions"}
MAX_BEATS = 16


class StoryboardError(ValueError):
    pass


def validate_storyboard(data: dict) -> dict:
    if not isinstance(data, dict):
        raise StoryboardError("storyboard must be an object")
    if data.get("version") == 2:
        from .story_v2 import validate_story_v2
        return validate_story_v2(data)
    if data.get("version") != 1:
        raise StoryboardError("unsupported storyboard version")
    if data.get("duration") != SECONDS or data.get("fps") != FPS:
        raise StoryboardError(f"draft must be exactly {SECONDS}s at {FPS}fps")
    if data.get("resolution") != [WIDTH, HEIGHT]:
        raise StoryboardError(f"draft resolution must be {WIDTH}x{HEIGHT}")
    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 180:
        raise StoryboardError("invalid title")
    beats = data.get("beats")
    if not isinstance(beats, list) or not 2 <= len(beats) <= MAX_BEATS:
        raise StoryboardError("invalid beat count")
    previous_end = 0.0
    ids = set()
    for i, beat in enumerate(beats):
        if not isinstance(beat, dict) or not REQUIRED_BEAT_KEYS.issubset(beat):
            raise StoryboardError(f"beat {i}: missing fields")
        if not isinstance(beat["id"], str) or beat["id"] in ids:
            raise StoryboardError(f"beat {i}: duplicate/invalid id")
        ids.add(beat["id"])
        start, end = beat["start"], beat["end"]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in (start, end)):
            raise StoryboardError(f"beat {i}: invalid timing")
        if abs(start - previous_end) > 1e-6 or end <= start or end > SECONDS:
            raise StoryboardError(f"beat {i}: timeline must be contiguous")
        previous_end = end
        for key in ("problem", "solution", "narration"):
            if not isinstance(beat[key], str) or not beat[key].strip() or len(beat[key]) > 800:
                raise StoryboardError(f"beat {i}: invalid {key}")
        if beat["camera"] not in CAMERAS:
            raise StoryboardError(f"beat {i}: unknown camera preset")
        if not isinstance(beat["actions"], list) or not beat["actions"]:
            raise StoryboardError(f"beat {i}: no actions")
        for action in beat["actions"]:
            if not isinstance(action, str) or action not in ACTION_TYPES:
                raise StoryboardError(f"beat {i}: unsupported action {action!r}")
    if abs(previous_end - SECONDS) > 1e-6:
        raise StoryboardError(f"story must end at exactly {SECONDS}s")
    return data


def load_storyboard(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_storyboard(data)


def narration(data: dict) -> str:
    validate_storyboard(data)
    return " ".join(beat["narration"].strip() for beat in data["beats"]) + "\n"


def word_count(data: dict) -> int:
    return len(narration(data).split())
