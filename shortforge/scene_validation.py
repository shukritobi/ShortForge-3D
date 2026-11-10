"""Validate Blender-produced scene_manifest.json before accepting a render."""
import json
from pathlib import Path

EXPECTED = {"support_legs": 4, "diagonal_braces": 8, "service_branches": 7}


def validate_scene_manifest(path: str | Path, *, story: dict | None = None) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if story is not None and story.get("version") == 2:
        expected_frames=story["duration"]*story["fps"]
        if (data.get("schema_version") != 2 or
            data.get("scene_template") != story["scene_template"] or
            data.get("duration") != story["duration"] or
            data.get("fps") != story["fps"] or
            data.get("resolution") != story["resolution"] or
            data.get("frame_count") != expected_frames):
            raise ValueError("v2 scene manifest does not match storyboard parameters")
        if data.get("object_count",0)<25 or data.get("action_count",0)<len(story["beats"]):
            raise ValueError("v2 scene is missing geometry or scheduled actions")
        asset_counts=data.get("assets",{})
        for beat in story["beats"]:
            for action in beat["actions"]:
                if asset_counts.get(action["target"],0)<1:
                    raise ValueError(f"Missing scene asset target: {action['target']}")
        return data
    if data.get("resolution") != [720, 1280] or data.get("fps") != 24 or data.get("frame_count") != 960:
        raise ValueError("Scene manifest does not match 40-second portrait draft contract")
    actual = data.get("structural_counts", {})
    for key, minimum in EXPECTED.items():
        if actual.get(key, 0) < minimum:
            raise ValueError(f"Incomplete tower/distribution geometry: expected {minimum} {key}, got {actual.get(key)}")
    tank = data.get("tank_to_support_connection", {})
    if abs(tank.get("top_support_z", 0) - tank.get("tank_bottom_z", 0)) > tank.get("max_gap_m", 0):
        raise ValueError("Tank bottom is disconnected from support structure")
    trench = data.get("exposed_trench", {})
    if trench.get("pipe_depth", 0) >= 0:
        raise ValueError("Underground main must remain below grade")
    if data.get("scene_objects",0) < 70:
        raise ValueError("Scene contains too few objects for the required environment")
    return data
