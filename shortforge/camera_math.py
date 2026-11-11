"""Perspective fitting independent of Blender; coordinates are camera-local metres."""
import math


def fit_distance(points, tan_x, tan_y, safe_x=.82, safe_y=.66):
    """Points (right, up, towards camera) relative to subject centre."""
    if not points or min(tan_x, tan_y, safe_x, safe_y) <= 0:
        raise ValueError("positive frustum and nonempty bounds required")
    return max(1.0, max(z + max(abs(x)/(tan_x*safe_x),
                               abs(y)/(tan_y*safe_y)) for x,y,z in points))
