"""Parse the external Blender entrypoint without having bpy installed."""
import ast
from pathlib import Path


def test_blender_script_python_syntax():
    script = Path(__file__).resolve().parents[1]/"scripts"/"blender_water_tower.py"
    ast.parse(script.read_text(encoding="utf-8"))
    assert "bpy.ops.render.render(animation=True)" in script.read_text(encoding="utf-8")
