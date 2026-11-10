import json
import ast
from pathlib import Path

import pytest
from shortforge.scene_validation import validate_scene_manifest
from shortforge.cli import parser
from shortforge.pc_agent import validate_job


def manifest():
    return {
        "resolution": [720,1280], "fps":24, "frame_count":960,
        "structural_counts":{"support_legs":4,"diagonal_braces":8,"service_branches":7},
        "tank_to_support_connection":{"top_support_z":5.62,"tank_bottom_z":5.65,"max_gap_m":.05},
        "exposed_trench":{"pipe_depth":-.55,"y":-2.92},
        "scene_objects":140,
    }


def test_scene_passes_geometry_contract(tmp_path):
    p=tmp_path/"scene_manifest.json"
    p.write_text(json.dumps(manifest()),encoding="utf-8")
    assert validate_scene_manifest(p)["structural_counts"]["support_legs"]==4


@pytest.mark.parametrize("field,value",[
    ("support_legs",3),("diagonal_braces",7),("service_branches",6),
])
def test_scene_rejects_missing_structure(tmp_path,field,value):
    data=manifest()
    data["structural_counts"][field]=value
    p=tmp_path/"scene_manifest.json"
    p.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError, match="Incomplete"):
        validate_scene_manifest(p)


def test_scene_rejects_floating_tank(tmp_path):
    data=manifest()
    data["tank_to_support_connection"]["top_support_z"]=4.8
    p=tmp_path/"scene_manifest.json"
    p.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError, match="disconnected"):
        validate_scene_manifest(p)


def test_scene_rejects_above_ground_pipe(tmp_path):
    data=manifest()
    data["exposed_trench"]["pipe_depth"]=.4
    p=tmp_path/"scene_manifest.json"
    p.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError, match="below grade"):
        validate_scene_manifest(p)


def test_3d_script_is_python_and_has_required_primitives():
    text=(Path(__file__).resolve().parents[1]/"scripts"/"blender_water_tower.py").read_text(encoding="utf-8")
    ast.parse(text)
    for marker in ("def grow_beam(", "def cutaway_shell(", "def roof(", "def distribution(", "def camera_animation("):
        assert marker in text
    assert "scene_manifest.json" in text


def test_cli_preview_frames_and_agent_review_allowlist():
    arguments=parser().parse_args(["render","examples/water_tower_40s.json",
                                   "--preview-frames","120,240,480,576,720,888"])
    assert arguments.preview_frames=="120,240,480,576,720,888"
    assert validate_job({"version":1,"task":"review","out":"output/water_tower"})["task"]=="review"


def test_preview_modes_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        parser().parse_args(["render","examples/water_tower_40s.json",
                             "--preview-frame","480",
                             "--preview-frames","240,576"])
