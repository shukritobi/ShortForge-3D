"""Validate Blender-produced scene_manifest.json before accepting a render."""
import json
from pathlib import Path

EXPECTED = {"support_legs": 4, "diagonal_braces": 8, "service_branches": 7}


def validate_scene_manifest(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
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
