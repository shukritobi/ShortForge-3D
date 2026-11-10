"""Phase 2 story contract for reusable, multi-topic 3D videos.

Version 1 stays untouched. Version 2 is intentionally explicit and allowlisted:
untrusted AI scripts cannot inject Python, assets, paths or Blender expressions.
"""
from __future__ import annotations
import math
import re

DURATIONS = (60, 75, 90, 120, 180)
SCENE_TEMPLATES = {
    "water_distribution": frozenset({"neighbourhood", "pump", "tower", "tank", "main",
                                      "branch", "faucet", "reservoir", "ground"}),
    "solar_home": frozenset({"house", "sun", "panels", "inverter", "battery",
                            "meter", "grid", "lights", "ground"}),
}
CAMERAS = frozenset({"establish", "detail", "section", "follow", "overhead", "reveal"})
ACTION_TYPES = frozenset({"appear", "assemble", "highlight", "flow", "pulse", "cutaway"})
BEAT_KEYS = frozenset({"id", "start", "end", "problem", "solution",
                       "narration", "camera", "actions"})
ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


class StoryV2Error(ValueError):
    pass


def total_frames(story: dict) -> int:
    return int(story["duration"] * story["fps"])


def validate_story_v2(story: dict) -> dict:
    if not isinstance(story, dict) or story.get("version") != 2:
        raise StoryV2Error("expected version 2 storyboard object")
    duration = story.get("duration")
    if type(duration) is not int or duration not in DURATIONS:
        raise StoryV2Error(f"duration must be one of {DURATIONS} seconds")
    if story.get("fps") != 24 or story.get("resolution") != [720, 1280]:
        raise StoryV2Error("phase 2 exports require 24 FPS, portrait 720x1280")
    scene = story.get("scene_template")
    if not isinstance(scene, str) or scene not in SCENE_TEMPLATES:
        raise StoryV2Error(f"scene_template must be registered: {sorted(SCENE_TEMPLATES)}")
    title = story.get("title")
    if not isinstance(title, str) or not (3 <= len(title.strip()) <= 180):
        raise StoryV2Error("invalid title")
    beats = story.get("beats")
    if not isinstance(beats, list) or not (8 <= len(beats) <= 40):
        raise StoryV2Error("expected 8 to 40 beats")
    seen = set()
    cursor = 0.0
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict) or not BEAT_KEYS.issubset(beat):
            raise StoryV2Error(f"beat {index}: missing fields")
        key = beat["id"]
        if not isinstance(key, str) or not ID_RE.fullmatch(key) or key in seen:
            raise StoryV2Error(f"beat {index}: duplicate or unsafe ID")
        seen.add(key)
        start, end = beat["start"], beat["end"]
        if any(type(t) not in (float, int) or not math.isfinite(t) for t in (start, end)):
            raise StoryV2Error(f"beat {key}: invalid time")
        if abs(start-cursor) > 0.0001 or end-start < 2.5 or end > duration+.0001:
            raise StoryV2Error(f"beat {key}: non-contiguous or too short")
        cursor = end
        for field in ("problem", "solution", "narration"):
            value = beat[field]
            if not isinstance(value, str) or not value.strip() or len(value) > 700:
                raise StoryV2Error(f"beat {key}: invalid {field}")
        if len(beat["narration"].split()) > (end-start)*3.3:
            raise StoryV2Error(f"beat {key}: too many words for its timeline")
        if not isinstance(beat["camera"], str) or beat["camera"] not in CAMERAS:
            raise StoryV2Error(f"beat {key}: unknown camera")
        actions = beat["actions"]
        if not isinstance(actions, list) or not actions or len(actions) > 5:
            raise StoryV2Error(f"beat {key}: expected 1-5 actions")
        for a in actions:
            if not isinstance(a, dict) or set(a) != {"type", "target"}:
                raise StoryV2Error(f"beat {key}: unsafe action fields")
            if (not isinstance(a["type"], str) or
                not isinstance(a["target"], str) or
                a["type"] not in ACTION_TYPES or
                a["target"] not in SCENE_TEMPLATES[scene]):
                raise StoryV2Error(f"beat {key}: unregistered action or target")
    if abs(cursor-duration) > 0.0001:
        raise StoryV2Error("last beat must end at video duration")
    return story
