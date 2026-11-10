"""ShortForge water-tower procedural 3D scene (Blender 4.5 LTS / 5.x).

Persistent deterministic low-poly neighbourhood with a properly connected
tower, anchored build animations and an exposed below-grade pipe trench.
No generated/remote Python is executed; storyboard is validated input data.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

FPS = 24
DURATION = 40
WIDTH = 720
HEIGHT = 1280
ACTIONS = {
    "show_house", "show_houses", "show_pump", "show_tower",
    "fill_tank", "show_pipes", "flow_water", "show_all",
}
CAMERAS = {
    # (location, point of interest, orthographic scale)
    "houses": ((-8.0, -12.5, 6.5), (-3.2, -0.2, 1.1), 7.8),
    "wide": ((12.0, -20.0, 11.5), (-0.1, 0.2, 2.1), 16.8),
    "pump": ((-11.0, -9.0, 7.5), (-6.2, 2.65, 1.1), 8.0),
    "tower": ((8.5, -12.0, 9.8), (3.05, 2.55, 4.25), 9.5),
    "cutaway": ((8.2, -12.5, 5.4), (0.8, -2.15, 0.3), 10.2),
    "distribution": ((6.0, -12.0, 6.5), (0.0, -2.1, 0.35), 10.8),
    "reveal": ((11.0, -17.5, 10.3), (0.35, 0.35, 2.65), 15.3),
}
HOMES = [
    (-5.0, -0.25), (-2.1, -0.25), (0.8, -0.25), (5.4, -0.25),
    (-4.6, 3.25), (-1.75, 3.15), (0.6, 4.0),
]
TOWER_CENTRE = (3.35, 3.05)
TANK_BOTTOM = 5.65
TANK_TOP = 7.92
PIPE_DEPTH = -0.55
TRENCH_Y = -2.92

MATS = {}
COUNTS = {"support_legs": 0, "diagonal_braces": 0, "service_branches": 0}


def f(time_s):
    return round(time_s * FPS) + 1


def mat(name, rgb, roughness=0.75, metallic=0.0):
    if name in MATS:
        return MATS[name]
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    MATS[name] = material
    return material


def assign(obj, material):
    obj.data.materials.append(material)
    return obj


def cube(name, center, dimensions, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return assign(obj, material)


def cyl(name, center, radius, height, material, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=height, location=center)
    obj = bpy.context.object
    obj.name = name
    return assign(obj, material)


def ball(name, center, radius, material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=16, ring_count=8, radius=radius, location=center)
    obj = bpy.context.object
    obj.name = name
    return assign(obj, material)


def beam(name, point_a, point_b, radius, material, vertices=12):
    a = Vector(point_a)
    b = Vector(point_b)
    vector = b - a
    if vector.length < 0.001:
        raise ValueError("beam endpoints must be distinct")
    obj = cyl(name, (a+b)*0.5, radius, vector.length, material, vertices)
    obj.rotation_euler = vector.to_track_quat("Z", "Y").to_euler()
    return obj


def show(obj, t0, t1, *, from_offset=(0, 0, -0.7)):
    """Slide a complete solid into position; never scale it around its centre."""
    final = obj.location.copy()
    shift = Vector(from_offset)
    obj.location = final + shift
    obj.scale = (0.85, 0.85, 0.85)
    obj.keyframe_insert("location", frame=f(t0))
    obj.keyframe_insert("scale", frame=f(t0))
    obj.location = final
    obj.scale = (1, 1, 1)
    obj.keyframe_insert("location", frame=f(t1))
    obj.keyframe_insert("scale", frame=f(t1))
    obj.location = final


def grow_beam(obj, a, b, t0, t1):
    """Grow beam from the physically connected first endpoint."""
    a, b = Vector(a), Vector(b)
    midpoint = (a+b)*0.5
    obj.location = a.copy()
    obj.scale = (1.0, 1.0, 0.001)
    obj.keyframe_insert("location", frame=f(t0))
    obj.keyframe_insert("scale", frame=f(t0))
    obj.location = midpoint
    obj.scale = (1.0, 1.0, 1.0)
    obj.keyframe_insert("location", frame=f(t1))
    obj.keyframe_insert("scale", frame=f(t1))
    obj.location = midpoint


def mesh_obj(name, vertices, faces, material):
    """Use a local mesh pivot so installation animation cannot drift toward world origin."""
    centre = sum((Vector(v) for v in vertices), Vector()) / len(vertices)
    local_vertices = [tuple(Vector(v) - centre) for v in vertices]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(local_vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = centre
    bpy.context.collection.objects.link(obj)
    return assign(obj, material)


def roof(name, x, y, z, width, depth, peak_height, material):
    """A real connected pitched roof rather than one oversized floating block."""
    hw, hd = width/2, depth/2
    verts = [
        (x-hw,y-hd,z), (x+hw,y-hd,z), (x,y-hd,z+peak_height),
        (x-hw,y+hd,z), (x+hw,y+hd,z), (x,y+hd,z+peak_height),
    ]
    faces = [(0,2,5,3), (2,1,4,5), (0,1,2), (3,5,4), (0,3,4,1)]
    return mesh_obj(name, verts, faces, material)


def environment():
    """Two surface strips expose a real excavated trench at the front."""
    grass = mat("meadow_grass", (0.35,0.56,0.37))
    soil = mat("warm_earth", (0.52,0.35,0.23))
    subsoil = mat("cutaway_sandstone", (0.68,0.47,0.30))
    road = mat("street_asphalt", (0.37,0.42,0.45))
    gravel = mat("trench_floor", (0.63,0.56,0.47))
    line = mat("road_lines", (0.94,0.85,0.56))
    # The trench is open between y=-3.75 and -2.10. It exposes buried pipes.
    cube("soil_section_core", (0, 0, -1.25), (17.5, 12.5, 1.15), soil)
    cube("rear_surface", (0, 1.65, -0.05), (17.6, 7.55, 0.10), grass)
    cube("front_surface", (0, -5.0, -0.05), (17.6, 2.45, 0.10), grass)
    cube("exposed_trench_floor", (0, TRENCH_Y, -0.83), (17.45, 1.65, 0.11), gravel)
    cube("rear_soil_face", (0, -2.07, -0.48), (17.45, 0.16, 0.83), subsoil)
    cube("front_soil_face", (0, -3.78, -0.48), (17.45, 0.16, 0.83), subsoil)
    # Back road is behind the house frontage, never covering the exposed trench.
    cube("road", (0, 1.52, 0.019), (16.7, 0.84, 0.05), road)
    for x in (-6,-3,0,3,6):
        cube("street_marker", (x, 1.53, .052), (.78,.065,.01), line)
    # Footpaths make the row read as a suburb rather than loose boxes.
    concrete = mat("walkway", (0.67,0.68,0.65))
    cube("front_walk", (0,-1.53,.009), (17,.25,.045), concrete)
    for x,y in HOMES:
        cube("house_footpath", (x, y-1.00, .02), (.48,.55,.052), concrete)
    # Three dimensional side strips and small stone layers improve cutaway depth.
    stone = mat("embedded_stones", (0.43,0.39,0.33))
    for i in range(25):
        x = -8.1 + (i % 13) * 1.35
        y = -2.12 if i < 13 else -3.73
        cube("trench_geology_stone", (x,y,-.58), (.45,.035,.095), stone)
    trees = [
        (-7.2,4.6,.86),(-6.6,.15,.63),(-3.4,5.1,.75),
        (1.0,5.5,.55),(6.6,4.1,.68),(7.6,.15,.52),
    ]
    bark = mat("tree_trunks",(0.39,0.26,0.16))
    leaves = mat("tree_leaves",(0.18,0.45,0.23))
    leaves2 = mat("shrub_green",(0.31,0.56,0.25))
    for i,(x,y,s) in enumerate(trees):
        cyl("tree_trunk_%02d"%i, (x,y,.65*s), .15*s, 1.28*s, bark, 9)
        # clustered canopies: readable from distant portrait camera
        ball("tree_canopy_%02d"%i,(x,y,1.67*s), .68*s, leaves)
        ball("tree_canopy_side_%02d"%i,(x-.34*s,y,1.55*s), .43*s, leaves2)
    for i,(x,y) in enumerate([
        (-7.5,-.85), (-3.6,-.9), (1.8,-.9),(7.4,-.8),
        (-5.8,4.4),(-.7,4.7),(6.6,3.9),
    ]):
        ball("ground_shrub_%02d"%i,(x,y,.25), .31, leaves2)


def house(i, x, y, start, end):
    palette = [
        (0.91,0.85,0.70), (0.72,0.84,0.81), (0.88,0.79,0.71),
        (0.78,0.84,0.90), (0.89,0.84,0.75), (0.89,0.80,0.81), (0.83,0.90,0.77)
    ]
    walls = mat("wall_%02d"%i,palette[i])
    roofmat = mat("tile_roof",(0.62,0.31,0.24))
    white = mat("white_trim",(0.9,0.91,0.86))
    glass = mat("window_glass",(0.25,0.52,0.71), .22)
    door = mat("door_wood",(0.40,0.28,0.19))
    base = mat("stone_base",(0.53,0.53,0.49))
    objs = [
        cube("house_%02d_foundation"%i,(x,y,.14),(1.93,1.73,.28),base),
        cube("house_%02d_walls"%i,(x,y,.98),(1.85,1.65,1.62),walls),
        roof("house_%02d_pitched_roof"%i,x,y,1.85,2.15,1.96,.64,roofmat),
        cube("house_%02d_door"%i,(x+.34,y-.844,.46),(.39,.06,.86),door),
        cube("house_%02d_doorstep"%i,(x+.34,y-1.0,.08),(.55,.32,.13),base),
        cube("house_%02d_window"%i,(x-.40,y-.847,1.08),(.52,.07,.52),glass),
        cube("house_%02d_window_lintel"%i,(x-.40,y-.88,1.39),(.60,.085,.07),white),
        cube("house_%02d_window_sill"%i,(x-.40,y-.89,.77),(.62,.09,.07),white),
    ]
    for j,obj in enumerate(objs):
        show(obj, start+min(j*.12,(end-start)*.55), end)
    return objs


def pumping_station(start, end):
    gold = mat("utility_yellow",(0.87,.62,.24))
    dark = mat("pump_steel",(0.17,.28,.31), metallic=.55)
    light = mat("pump_facade",(0.74,.77,.72))
    x,y = -6.55,2.75
    parts = [
        cube("pump_concrete_plinth",(x,y,.20),(2.05,1.82,.39),light),
        cube("pump_enclosure",(x,y,1.06),(1.8,1.55,1.4),gold),
        cube("pump_service_hatch",(x,y-.795,1.02),(.72,.05,.82),dark),
        cyl("pump_drive_motor",(x+.10,y,1.91),.50,.34,dark),
        cyl("pump_lid",(x+.10,y,2.12),.55,.09,light),
    ]
    for idx,obj in enumerate(parts):
        show(obj,start + idx*.2,end-.2)
    return parts


def cutaway_shell():
    """Tank wall with an open 105-degree near-side wedge: water remains visible."""
    cx,cy=TOWER_CENTRE
    inner,outer=1.47,1.62
    bottom,top=TANK_BOTTOM,TANK_TOP
    angles=[math.radians(-35 + 250*i/40) for i in range(41)]
    v=[]
    for a in angles:
        ca,sa=math.cos(a),math.sin(a)
        v.extend([
            (cx+outer*ca,cy+outer*sa,bottom),
            (cx+outer*ca,cy+outer*sa,top),
            (cx+inner*ca,cy+inner*sa,bottom),
            (cx+inner*ca,cy+inner*sa,top),
        ])
    faces=[]
    for i in range(len(angles)-1):
        k=i*4
        faces.extend([
            (k,k+4,k+5,k+1),         # outer
            (k+2,k+3,k+7,k+6),       # inner
            (k+1,k+5,k+7,k+3),       # top edge
            (k,k+2,k+6,k+4),         # lower edge
        ])
    last=(len(angles)-1)*4
    faces.extend([(0,1,3,2),(last,last+2,last+3,last+1)])
    return mesh_obj("tank_cutaway_shell",v,faces,mat("tank_blue_enamel",(0.23,.43,.56),.35,.55))


def tower(start,end):
    cx,cy=TOWER_CENTRE
    steel=mat("tower_support_steel",(0.33,.39,.41),.48,.60)
    accent=mat("tower_strut_dark",(0.19,.27,.31),.55,.65)
    concrete=mat("tower_footings",(0.71,.73,.68))
    shell_mat=mat("tank_dish",(0.22,.42,.54),.42,.50)
    parts=[]
    feet=[]
    for x_sign in (-1,1):
        for y_sign in (-1,1):
            bottom=(cx+x_sign*.98,cy+y_sign*.98,.32)
            top=(cx+x_sign*.74,cy+y_sign*.74,5.62)
            feet.append((bottom,top))
            pad=cube("tower_anchor_footing",(bottom[0],bottom[1],.20),(.67,.67,.4),concrete)
            show(pad,start,start+.32)
            parts.append(pad)
    for i,(a,b) in enumerate(feet):
        leg=beam("tower_primary_leg_%d"%i,a,b,.185,steel,14)
        grow_beam(leg,a,b,start+.15,start+2.0)
        COUNTS["support_legs"]+=1
        parts.append(leg)
    # Cross-braces are attached to the primary legs; never float as isolated rods.
    t=start+1.10
    for y_sign in (-1,1):
        for z0,z1 in ((.85,2.65),(2.65,4.5)):
            a=(cx-.94,cy+y_sign*.94,z0)
            b=(cx+.94,cy+y_sign*.94,z1)
            c=(cx+.94,cy+y_sign*.94,z0)
            d=(cx-.94,cy+y_sign*.94,z1)
            for aa,bb in ((a,b),(c,d)):
                obj=beam("tower_cross_brace",aa,bb,.071,accent,10)
                grow_beam(obj,aa,bb,t,t+.60)
                parts.append(obj)
                COUNTS["diagonal_braces"]+=1
            t+=.22
    # Tank seat is assembled only after legs have reached the top.
    lower=cyl("tank_bottom_dish",(cx,cy,5.65),1.66,.28,shell_mat,48)
    show(lower,start+2.1,start+2.65)
    parts.append(lower)
    shell=cutaway_shell()
    show(shell,start+2.60,start+3.75,from_offset=(0,0,-1.35))
    parts.append(shell)
    # Rim and maintenance catwalk have a clear mechanical connection to the tank.
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=10,
                                    location=(cx,cy,TANK_TOP),
                                    major_radius=1.57, minor_radius=.08)
    rim=assign(bpy.context.object,accent)
    rim.name="tank_continuous_top_rim"
    show(rim,start+3.40,start+4.05)
    parts.append(rim)
    # External pipe feeds the tank from the pump, visibly tied to the tower.
    down_bottom=(cx+.26,cy-.95,-.38)
    down_top=(cx+.26,cy-.95,7.40)
    riser=beam("tower_water_riser",down_bottom,down_top,.145,
               mat("water_supply_pipe",(.13,.62,.80),.3,.3),20)
    grow_beam(riser,down_bottom,down_top,start+2.25,start+4.1)
    parts.append(riser)
    return parts


def tank_water(fill_start,fill_end,recharge_start):
    """Visible water inside the open-front tank, anchored at the bottom."""
    cx,cy=TOWER_CENTRE
    blue=mat("water_volume",(0.10,.59,.85),.16,.05)
    water=cyl("visible_tank_water",(cx,cy,TANK_BOTTOM+.06),1.44,1.8,blue,48)
    surface=cyl("water_surface_disc",(cx,cy,TANK_BOTTOM+.10),1.45,.055,
                mat("water_surface",(0.23,.77,.98),.12),48)
    for when,height in (
        (0,.012),(fill_start,.012),(fill_end,1.68),
        (32.0,1.58),(recharge_start,1.32),(DURATION,1.60),
    ):
        water.scale.z=max(.01,height/1.8)
        water.location.z=TANK_BOTTOM+height*.5+.02
        water.keyframe_insert("scale",frame=f(when))
        water.keyframe_insert("location",frame=f(when))
        surface.location.z=TANK_BOTTOM+height+.02
        surface.scale=(.001,.001,.001) if height<.05 else (1,1,1)
        surface.keyframe_insert("location",frame=f(when))
        surface.keyframe_insert("scale",frame=f(when))
    return [water,surface]


def distribution(start,end):
    blue=mat("underground_blue_main",(0.11,.58,.81),.30,.35)
    cyan=mat("service_pipe_cyan",(0.21,.79,.90),.26)
    cx,cy=TOWER_CENTRE
    parts=[]
    # Road-front open trench holds the visible main at a realistic below-grade height.
    a=(-7.65,TRENCH_Y,PIPE_DEPTH)
    b=(7.50,TRENCH_Y,PIPE_DEPTH)
    main=beam("exposed_distribution_main",a,b,.16,blue,20)
    grow_beam(main,a,b,start,start+3.0)
    parts.append(main)
    # Vertical supply pipe attaches to riser and then goes through soil into the trench.
    a=(cx+.26,cy-.95,-.38)
    b=(cx+.26,TRENCH_Y,PIPE_DEPTH)
    link=beam("tower_link_to_trench",a,b,.13,blue,18)
    grow_beam(link,a,b,start+.5,start+3.0)
    parts.append(link)
    for i,(x,y) in enumerate(HOMES):
        # Underground branch attached directly to the visible water main.
        a=(x,TRENCH_Y,PIPE_DEPTH)
        b=(x,y-1.03,PIPE_DEPTH)
        branch=beam("branch_to_house_%d"%i,a,b,.083,cyan,12)
        grow_beam(branch,a,b,start+1.0+i*.22,min(end,start+4.9+i*.17))
        parts.append(branch)
        riser_a=(x,y-1.03,PIPE_DEPTH)
        riser_b=(x,y-1.03,.70)
        service=beam("home_service_riser_%d"%i,riser_a,riser_b,.066,blue,12)
        grow_beam(service,riser_a,riser_b,start+2.0+i*.30,min(end,start+5.1+i*.17))
        parts.append(service)
        COUNTS["service_branches"]+=1
    return parts


def particles(start):
    mat_water=mat("moving_water_pulses",(0.06,.87,1.0),.08)
    cx,cy=TOWER_CENTRE
    # Flow remains within the physical downpipe/main/branch path, no teleporting.
    paths=[]
    for x,y in HOMES[:5]:
        paths.append([
            (cx+.26,cy-.95,5.35),(cx+.26,cy-.95,-.38),
            (cx+.26,TRENCH_Y,PIPE_DEPTH),(x,TRENCH_Y,PIPE_DEPTH),
            (x,y-1.03,PIPE_DEPTH),(x,y-1.03,.65),
        ])
    for index,path in enumerate(paths):
        for duplicate in (0,1):
            dot=ball("water_pulse_%d_%d"%(index,duplicate),path[0],.14,mat_water)
            arrival=start+1.0+index*.25+duplicate*2.6
            dot.scale=(.001,.001,.001)
            dot.keyframe_insert("scale",frame=f(0))
            dot.keyframe_insert("scale",frame=f(arrival))
            dot.scale=(1,1,1)
            dot.keyframe_insert("scale",frame=f(arrival+.10))
            for j,waypoint in enumerate(path):
                moment=min(39.2,arrival+j*.70)
                dot.location=waypoint
                dot.keyframe_insert("location",frame=f(moment))
            # Stop and disappear at the fixture instead of teleporting back.
            dot.scale=(.001,.001,.001)
            dot.keyframe_insert("scale",frame=f(min(39.8,arrival+4.8)))


def camera_animation(beats):
    first=CAMERAS[beats[0]["camera"]]
    bpy.ops.object.camera_add(location=first[0])
    obj=bpy.context.object
    obj.name="ShortForge_portrait_story_camera"
    bpy.context.scene.camera=obj
    obj.data.type="ORTHO"
    obj.data.ortho_scale=first[2]
    for i,beat in enumerate(beats):
        position,target,scale=CAMERAS[beat["camera"]]
        start=f(beat["start"])
        # Hold previous framing at the transition boundary, then settle in 0.5s.
        if i>0:
            obj.keyframe_insert("location",frame=start)
            obj.keyframe_insert("rotation_euler",frame=start)
            obj.data.keyframe_insert("ortho_scale",frame=start)
        obj.location=position
        obj.rotation_euler=(Vector(target)-Vector(position)).to_track_quat("-Z","Y").to_euler()
        obj.data.ortho_scale=scale
        obj.keyframe_insert("location",frame=(start if i==0 else min(960,start+12)))
        obj.keyframe_insert("rotation_euler",frame=(start if i==0 else min(960,start+12)))
        obj.data.keyframe_insert("ortho_scale",frame=(start if i==0 else min(960,start+12)))
    obj.keyframe_insert("location",frame=960)
    obj.keyframe_insert("rotation_euler",frame=960)
    obj.data.keyframe_insert("ortho_scale",frame=960)
    return obj


def world_and_lights():
    sky=bpy.context.scene.world
    sky.use_nodes=True
    background=sky.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value=(.53,.69,.85,1)
    background.inputs["Strength"].default_value=.78
    bpy.ops.object.light_add(type="SUN",location=(1,-4,12))
    sun=bpy.context.object
    sun.name="warm_directional_sun"
    sun.data.energy=2.2
    sun.data.angle=math.radians(8)
    sun.rotation_euler=(math.radians(28),math.radians(-28),math.radians(-30))
    bpy.ops.object.light_add(type="AREA",location=(0,-5,11))
    fill=bpy.context.object
    fill.name="large_soft_fill"
    fill.data.energy=1250
    fill.data.shape="DISK"
    fill.data.size=13


def times(beats,name):
    for b in beats:
        if name in b["actions"]:
            return float(b["start"]),float(b["end"])
    raise ValueError("Water-tower story missing required action: " + name)


def validate(data):
    if not isinstance(data,dict) or data.get("duration")!=DURATION or data.get("fps")!=FPS:
        raise ValueError("Expected 40-second 24 FPS storyboard")
    if data.get("resolution") != [WIDTH,HEIGHT]:
        raise ValueError("Expected 720x1280 draft")
    beats=data.get("beats")
    if not isinstance(beats,list) or len(beats)<5:
        raise ValueError("Invalid beats")
    cursor=0
    all_actions=set()
    for b in beats:
        if float(b["start"])!=cursor or b["end"]<=b["start"]:
            raise ValueError("Timeline not contiguous")
        cursor=float(b["end"])
        if b["camera"] not in CAMERAS or not set(b["actions"])<=ACTIONS:
            raise ValueError("Unknown storyboard camera/action")
        all_actions.update(b["actions"])
    if cursor!=DURATION or not ACTIONS.issubset(all_actions):
        raise ValueError("Water-tower storyboard missing required visual actions")


def build(data):
    validate(data)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    MATS.clear()
    for k in COUNTS:
        COUNTS[k]=0
    environment()
    beats=data["beats"]
    t0,t1=times(beats,"show_house")
    house(0,*HOMES[0],t0+.25,t1-.5)
    a,b=times(beats,"show_houses")
    for i,(x,y) in enumerate(HOMES[1:],start=1):
        offset=(i-1)*.56
        house(i,x,y,a+offset,a+min(offset+1.25,b-a-.2))
    a,b=times(beats,"show_pump")
    pumping_station(a+.2,b-.65)
    a,b=times(beats,"show_tower")
    tower(a,b)
    w0,w1=times(beats,"fill_tank")
    # Begin fill only after shell + connected supports are assembled.
    tank_water(max(w0+4.05,w1-1.7),w1-.05,37.0)
    a,b=times(beats,"show_pipes")
    distribution(a+.1,b-.3)
    particles(a+.4)
    camera_animation(beats)
    world_and_lights()


def report(output):
    out={
        "engine":"blender",
        "blender_version":list(bpy.app.version),
        "resolution":[WIDTH,HEIGHT],
        "fps":FPS,
        "duration_seconds":DURATION,
        "frame_count":FPS*DURATION,
        "tower_centre":TOWER_CENTRE,
        "tank_height":[TANK_BOTTOM,TANK_TOP],
        "exposed_trench":{"y":TRENCH_Y,"pipe_depth":PIPE_DEPTH},
        "structural_counts":dict(COUNTS),
        "tank_to_support_connection":{"top_support_z":5.62,"tank_bottom_z":TANK_BOTTOM,"max_gap_m":.05},
        "scene_objects":len(bpy.data.objects),
        "cameras":{name:{"target":v[1],"ortho_scale":v[2]} for name,v in CAMERAS.items()},
        "preview_frames_recommended":[120,240,480,576,720,888],
    }
    path=output/"scene_manifest.json"
    path.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")


def render(data, output, preview_frame=None, preview_frames=None):
    build(data)
    scene=bpy.context.scene
    scene.render.engine = ("BLENDER_EEVEE" if bpy.app.version >= (5,0,0)
                           else "BLENDER_EEVEE_NEXT")
    scene.render.resolution_x=WIDTH
    scene.render.resolution_y=HEIGHT
    scene.render.resolution_percentage=100
    scene.render.fps=FPS
    scene.frame_start=1
    scene.frame_end=FPS*DURATION
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.film_transparent=False
    scene.render.filepath=str((output/"frames"/"frame_######").resolve())
    output.mkdir(parents=True,exist_ok=True)
    report(output)
    if preview_frames is not None:
        if not preview_frames:
            raise ValueError("Preview frame list empty")
        for frame in preview_frames:
            if frame<1 or frame>FPS*DURATION:
                raise ValueError("Invalid preview frame " + str(frame))
            scene.frame_set(frame)
            scene.render.filepath=str((output/("preview_%04d.png"%frame)).resolve())
            bpy.ops.render.render(write_still=True)
        # Launcher compatibility: preview.png is the latest rendered keyframe.
        scene.render.filepath=str((output/"preview.png").resolve())
        scene.frame_set(preview_frames[-1])
        bpy.ops.render.render(write_still=True)
        return
    if preview_frame is not None:
        if not 1<=preview_frame<=FPS*DURATION:
            raise ValueError("Invalid preview frame")
        scene.frame_set(preview_frame)
        scene.render.filepath=str((output/"preview.png").resolve())
        bpy.ops.render.render(write_still=True)
        return
    (output/"frames").mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str((output/"frames"/"frame_######").resolve())
    bpy.ops.render.render(animation=True)


def args():
    items=sys.argv
    items=items[items.index("--")+1:] if "--" in items else []
    parser=argparse.ArgumentParser()
    parser.add_argument("--storyboard",required=True)
    parser.add_argument("--out",required=True)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--preview-frame",type=int)
    mode.add_argument("--preview-frames",type=str,
                      help="comma-separated keyframes e.g. 120,240,480,576,720,888")
    return parser.parse_args(items)


if __name__=="__main__":
    a=args()
    data=json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    review=[int(x) for x in a.preview_frames.split(",")] if a.preview_frames else None
    render(data,Path(a.out).resolve(),a.preview_frame,review)
