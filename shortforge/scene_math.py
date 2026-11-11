"""Pure reusable roof and solar mounting geometry (metres, Z-up).

This module deliberately has no Blender dependencies so physical alignment
can be unit tested in CI before running expensive PC preview renders.
"""
from __future__ import annotations
import math

ROOF_RUN = 1.68
ROOF_RISE = 0.76
ROOF_EAVE = 2.96
ROOF_RIDGE = ROOF_EAVE + ROOF_RISE
ROOF_PITCH = math.atan2(ROOF_RISE, ROOF_RUN)


def roof_height(local_x: float) -> float:
    """Top-surface centreline for a symmetric gable with its ridge at x=0."""
    return ROOF_RIDGE - abs(local_x) * (ROOF_RISE / ROOF_RUN)


def roof_surface_point(
    x: float,
    y: float,
    u: float,
    v: float,
    pitch: float = ROOF_PITCH,
    offset: float = .06,
) -> tuple[float, float, float]:
    """Local pitched-panel point, offset normally away from the roof.

    x,y: panel centre; u moves across pitch, v along the roof length.
    The right roof slope descends when x increases.
    """
    return (
        x + u * math.cos(pitch) + offset * math.sin(pitch),
        y + v,
        roof_height(x) - u * math.sin(pitch) + offset * math.cos(pitch),
    )
