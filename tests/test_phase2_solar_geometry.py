"""Solar Phase 2 regression: fitted roof, stable camera and connected wiring."""
from __future__ import annotations
import ast
import math
from pathlib import Path
from shortforge.scene_math import (
    ROOF_EAVE, ROOF_RIDGE, ROOF_PITCH, roof_height, roof_surface_point,
)

ROOT=Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT/path).read_text(encoding="utf-8")


def test_gable_ridge_is_highest_and_eave_is_lower():
    assert ROOF_RIDGE > ROOF_EAVE
    assert roof_height(0)==ROOF_RIDGE
    assert math.isclose(roof_height(1.68),ROOF_EAVE,abs_tol=1e-9)
    assert roof_height(.48) > roof_height(1.17)


def test_panel_offset_follows_the_pitched_roof():
    for centre_x in (.48,1.17):
        upper=roof_surface_point(centre_x,1.0,.30,0,offset=.216)
        lower=roof_surface_point(centre_x,1.0,-.30,0,offset=.216)
        assert upper[0]>lower[0]
        assert upper[2]<lower[2]
        # distance above the same local roof plane stays constant
        assert math.isclose(
            upper[2]-(roof_height(centre_x)-.30*math.sin(ROOF_PITCH)),
            .216*math.cos(ROOF_PITCH),abs_tol=1e-9)


def test_solar_panels_are_attached_not_level_or_inverse_sloped():
    s=source(Path("scripts/blender_assets_v2.py"))
    ast.parse(s)
    assert 'tilt=-ROOF_PITCH' in s  # left plane
    assert 'tilt=ROOF_PITCH' in s   # right plane and PV modules
    assert 'roof_height(local_x)+.18' in s
    assert "pv_mount_" in s
    assert "pv_cell_line_u_" in s
    assert "pv_cell_line_v_" in s


def test_connected_solar_wiring_and_focused_camera():
    assets=source(Path("scripts/blender_assets_v2.py"))
    animation=source(Path("scripts/blender_v2.py"))
    ast.parse(animation)
    for token in ("dc_conduit","ac_wall_conduit","battery_conduit",
                  "service_drop","energy_meter","battery_enclosure"):
        assert token in assets
    assert '"house":(.0,1.0,2.0)' in assets
    assert "kit.focus[target]" in animation
    assert "kit.last_camera_focus=anchor.copy()" in animation
    assert 'cam.data.lens=26' in animation
