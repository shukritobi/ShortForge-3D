"""Blender 4.5+ background renderer for one persistent water-tower neighbourhood.

Usage:
blender -b --python scripts/blender_water_tower.py -- --storyboard examples/water_tower_40s.json --out output/water_tower
Or append --preview-frame 480 to render a single still.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

# This script runs inside Blender's bundled Python. Never run AI-generated Python.
import bpy
from mathutils import Vector

ACTIONS = {"show_house", "show_houses", "show_pump", "show_tower", "fill_tank", "show_pipes", "flow_water", "show_all"}
FPS = 24
MATERIALS = {}


def material(name, color, roughness=0.8):
    if name in MATERIALS:
        return MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    MATERIALS[name] = mat
    return mat


def apply_material(obj, mat):
    obj.data.materials.append(mat)
    return obj


def box(name, location, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return apply_material(obj, mat)


def cylinder(name, location, radius, height, mat, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=height, location=location)
    obj = bpy.context.object
    obj.name = name
    return apply_material(obj, mat)


def pipe(name, a, b, radius, mat):
    start, end = Vector(a), Vector(b)
    midpoint = (start + end) * 0.5
    obj = cylinder(name, midpoint, radius, (end - start).length, mat, 16)
    obj.rotation_euler = (end - start).to_track_quat("Z", "Y").to_euler()
    return obj


def sphere(name, loc, radius, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius, location=loc)
    obj = bpy.context.object
    return apply_material(obj, mat)


def appear(obj, start, end):
    """Grow an existing scene component in place; preserve object identity."""
    original = obj.scale.copy()
    for when, factor in ((0, 0.001), (start, 0.001), (end, 1.0)):
        obj.scale = original * factor
        obj.keyframe_insert(data_path="scale", frame=round(when * FPS) + 1)
    obj.scale = original


def appear_group(group, start, end):
    for obj in group:
        appear(obj, start, end)


def ground():
    grass = material("grass", (0.27, 0.53, 0.25))
    soil = material("earth_section", (0.59, 0.35, 0.19))
    box("soil_cross_section", (0, 0, -0.65), (18, 12, 1.2), soil)
    box("grass_top", (0, 0, -0.03), (18.1, 12.1, 0.12), grass)
    for x, y, s in [(-7,4,.8), (-5,5,1), (6,4,.9), (7,-1,.7)]:
        trunk = material("trunk", (0.32, 0.19, 0.09))
        foliage = material("foliage", (0.15, 0.39, 0.15))
        cylinder("tree_trunk", (x,y,0.75*s), .11*s, 1.5*s, trunk, 10)
        bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=.65*s, radius2=0, depth=1.8*s, location=(x,y,2.0*s))
        apply_material(bpy.context.object, foliage)


def house(i, x, y):
    wall = material("warm_wall", (0.87, 0.83, 0.69))
    roofmat = material("terracotta_roof", (0.58, 0.23, 0.16))
    windows = material("blue_windows", (0.36, 0.62, 0.77), .2)
    door = material("front_door", (0.42, 0.3, 0.21))
    parts = [
        box(f"house_{i}_body", (x,y,0.85), (1.6,1.25,1.7), wall),
        box(f"house_{i}_roof", (x,y,1.98), (1.9,1.5,.5), roofmat),
        box(f"house_{i}_window", (x-.33,y-.636,1.05), (.35,.05,.42), windows),
        box(f"house_{i}_door", (x+.35,y-.641,.44), (.37,.055,.87), door),
    ]
    return parts


def pump_station():
    metal = material("pump_metal", (.74, .69, .36))
    trim = material("dark_metal", (.13, .19, .24))
    return [
        box("pump_station_base", (-6,2,0.55), (2,1.7,1.1), metal),
        box("pump_station_motor", (-6,2,1.22), (1,1,.3), trim),
        cylinder("pump_housing", (-6,2,1.55), .42, .48, trim),
    ]


def tower():
    steel = material("water_tower_steel", (.66,.72,.75))
    blue = material("stored_water", (.12,.58,.89), .15)
    parts = []
    for x in (-.78,.78):
        for y in (2.0,3.56):
            parts.append(pipe("tower_support", (x,y,.12),(x,y,5.25), .105, steel))
    parts.extend([
        cylinder("tank_base", (0,2.78,5.55), 1.55, .18, steel),
        cylinder("tank_body", (0,2.78,6.47), 1.52, 1.6, steel),
        cylinder("tank_upper_rim", (0,2.78,7.32), 1.57, .16, steel),
        cylinder("water_visible_upper_disk", (0,2.78,7.412), 1.42, .09, blue),
    ])
    return parts


def water_fill():
    blue = material("animated_water", (.1,.48,.85), .1)
    fill = cylinder("tank_water_filling", (0,2.78,6.05), 1.42, .75, blue)
    # The filling water is highlighted as a visible ring above tank body.
    surface = cylinder("visible_water_level", (0,2.78,7.52), 1.35, .035, blue)
    return [fill, surface]


def distribution():
    bluepipe = material("distribution_pipes", (.16,.51,.68))
    # These are exposed in a cutaway zone so they stay legible even in the wide shot.
    segments = [
        pipe("tank_downpipe", (0,2.78,5.1),(0,2.78,.18),.125,bluepipe),
        pipe("water_main", (-7,0,.18),(7,0,.18),.14,bluepipe),
        pipe("tower_main_link", (0,2.78,.18),(0,0,.18),.13,bluepipe),
    ]
    homes = [(-6,-2),(-3,-2),(0,-2),(3,-2),(6,-2),(-4,3),(4,3)]
    for i,(x,y) in enumerate(homes):
        segments.append(pipe(f"service_{i}", (x,0,.18),(x,y,.18),.065,bluepipe))
        segments.append(pipe(f"riser_{i}", (x,y,.18),(x,y,.7),.052,bluepipe))
    return segments


def flow_particles():
    water = material("flow_highlight", (.08,.79,1.0), .05)
    particles = []
    # One continuous 3D path from the tower into the distribution main.
    route = [(0,2.78,4.9),(0,2.78,.32),(0,0,.32),(-6,0,.32),(-6,-2,.32)]
    for idx in range(9):
        dot = sphere(f"flow_marker_{idx}", route[0], .10, water)
        # Make flow markers tiny until distribution begins.
        dot.scale = (.001,)*3
        dot.keyframe_insert(data_path="scale", frame=1)
        dot.keyframe_insert(data_path="scale", frame=round(25*FPS))
        dot.scale = (1,1,1)
        dot.keyframe_insert(data_path="scale", frame=round((25.1+idx*.25)*FPS)+1)
        for repeat in range(2):
            start = 25.1+idx*.42+repeat*5
            for waypoint, pos in enumerate(route):
                when = min(start + waypoint*.9, 39.9)
                dot.location = pos
                dot.keyframe_insert(data_path="location", frame=round(when*FPS)+1)
        particles.append(dot)
    return particles


POSITIONS = {
    "wide": ((14,-20,13),(0,0,2.7)),
    "houses": ((-4,-13,7),(-5,-1,1)),
    "pump": ((-12,-10,8),(-5,2,1.2)),
    "tower": ((9,-11,10),(0,2.5,5.0)),
    "cutaway": ((11,-15,6),(0,.1,.1)),
    "distribution": ((5,-13,8),(0,-.6,.3)),
    "reveal": ((13,-19,13),(0,1,3)),
}


def animate_camera(beats):
    bpy.ops.object.camera_add(location=POSITIONS["wide"][0])
    camera = bpy.context.object
    camera.name = "ShortForge_Animated_Camera"
    bpy.context.scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 13.8
    for beat in beats:
        pos, target = POSITIONS[beat["camera"]]
        at_frame = round(beat["start"]*FPS)+1
        camera.location = pos
        camera.rotation_euler = (Vector(target)-Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = 12.0 if beat["camera"] in ("tower","cutaway","pump") else 14.8
        camera.keyframe_insert(data_path="location", frame=at_frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=at_frame)
        camera.data.keyframe_insert(data_path="ortho_scale", frame=at_frame)
    # Hold final camera until the last frame.
    camera.keyframe_insert(data_path="location",frame=960)


def lighting():
    world = bpy.context.scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.53,.69,.88,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .8
    bpy.ops.object.light_add(type="SUN", location=(2,-4,12))
    bpy.context.object.data.energy = 2.1
    bpy.context.object.rotation_euler = (math.radians(25),math.radians(-24),math.radians(-25))


def run(storyboard, output, preview_frame=None):
    assert storyboard["duration"] == 40 and storyboard["fps"] == FPS
    assert storyboard["resolution"] == [720,1280]
    previous = 0
    for beat in storyboard["beats"]:
        assert beat["start"] == previous and beat["camera"] in POSITIONS
        assert beat["actions"] and set(beat["actions"]) <= ACTIONS
        previous = beat["end"]
    assert previous == 40

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    MATERIALS.clear()
    ground()
    homes = [(-6,-2),(-3,-2),(0,-2),(3,-2),(6,-2),(-4,3),(4,3)]
    home_models = [house(i,*home) for i,home in enumerate(homes)]
    appear_group(home_models[0], 0.1, 3.0)
    for i in range(1,len(home_models)):
        appear_group(home_models[i], 4.0+(i-1)*.55, 4.6+(i-1)*.55)
    appear_group(pump_station(),9,12)
    appear_group(tower(),19,23)
    for obj in water_fill():
        appear(obj,23,25)
    appear_group(distribution(),25,31.5)
    flow_particles()
    animate_camera(storyboard["beats"])
    lighting()

    scene = bpy.context.scene
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1280
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = 960
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    output = Path(output)
    frames = output / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str((frames / "frame_######").resolve())
    if preview_frame:
        if not 1 <= preview_frame <= 960:
            raise ValueError("preview frame must be 1..960")
        scene.frame_set(preview_frame)
        scene.render.filepath = str((output/"preview.png").resolve())
        bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)


def parse_args():
    a = sys.argv
    a = a[a.index("--")+1:] if "--" in a else []
    p = argparse.ArgumentParser()
    p.add_argument("--storyboard",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--preview-frame",type=int)
    return p.parse_args(a)


if __name__ == "__main__":
    args = parse_args()
    with open(args.storyboard, encoding="utf-8") as handle:
        run(json.load(handle), args.out, args.preview_frame)
