"""Real cutaway support, not merely camera angle changes."""
from pathlib import Path


def test_water_asset_builder_contains_excavation():
    root=Path(__file__).resolve().parents[1]
    source=(root/"scripts"/"blender_assets_v2.py").read_text(encoding="utf-8")
    assert "self.cutaway_covers" in source
    assert 'cube("earth_north"' in source
    assert 'cube("earth_south"' in source
    assert 'cube("trench_grass_cover"' in source


def test_cutaway_action_keyframes_cover_visibility():
    root=Path(__file__).resolve().parents[1]
    source=(root/"scripts"/"blender_v2.py").read_text(encoding="utf-8")
    assert 'for cover in kit.cutaway_covers:' in source
    assert 'cover.keyframe_insert(data_path="hide_render",frame=start)' in source
