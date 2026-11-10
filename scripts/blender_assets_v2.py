"""Reusable Blender 4.x procedural asset kit for ShortForge scene templates.

Units are meters, z-up. Assets register stable semantic targets independent of
narration text. No arbitrary user-provided Python or expression evaluation.
"""
from __future__ import annotations
import math

import bpy
from mathutils import Vector
from shortforge.scene_math import (
    ROOF_RUN, ROOF_RISE, ROOF_EAVE, ROOF_RIDGE, ROOF_PITCH,
    roof_height, roof_surface_point,
)

def gable(name, x, y, mat):
    """Fill the front and rear triangular walls beneath a pitched roof."""
    v=[(x-1.5,y-1.35,2.8), (x+1.5,y-1.35,2.8),
       (x,y-1.35,ROOF_RIDGE-.05),
       (x-1.5,y+1.35,2.8), (x+1.5,y+1.35,2.8),
       (x,y+1.35,ROOF_RIDGE-.05)]
    faces=[(0,1,2),(3,5,4),(0,3,4,1),(0,2,5,3),(1,4,5,2)]
    mesh=bpy.data.meshes.new("sf2_gable")
    mesh.from_pydata(v,[],faces)
    mesh.update()
    obj=bpy.data.objects.new("sf_"+name,mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    return obj



def material(name, rgb, *, metallic=0.0, roughness=0.6, emission=0.0):
    key="SF2_"+name
    obj=bpy.data.materials.get(key)
    if obj:
        return obj
    obj=bpy.data.materials.new(key)
    obj.diffuse_color=(*rgb,1)
    obj.use_nodes=True
    bsdf=obj.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*rgb,1)
    bsdf.inputs["Metallic"].default_value=metallic
    bsdf.inputs["Roughness"].default_value=roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value=(*rgb,1)
        bsdf.inputs["Emission Strength"].default_value=emission
    return obj


def cube(name, position, size, mat, *, tilt=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj=bpy.context.object
    obj.name="sf_"+name
    obj.dimensions=size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler[1]=tilt
    obj.data.materials.append(mat)
    if obj.type=="MESH":
        bevel=obj.modifiers.new("Edge highlights", "BEVEL")
        bevel.width=min(.045, min(size)/10)
        bevel.segments=2
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def cylinder(name, position, radius, depth, mat, *, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=position)
    obj=bpy.context.object
    obj.name="sf_"+name
    obj.data.materials.append(mat)
    return obj


def sphere(name, position, radius, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=radius,
                                         location=position)
    obj=bpy.context.object
    obj.name="sf_"+name
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return obj


def pipe(name, points, mat, thickness=.075):
    curve=bpy.data.curves.new("sf_pipe_curve", type="CURVE")
    curve.dimensions="3D"
    curve.resolution_u=2
    curve.bevel_depth=thickness
    curve.bevel_resolution=3
    spline=curve.splines.new("POLY")
    spline.points.add(len(points)-1)
    for control,xyz in zip(spline.points,points):
        control.co=(*xyz,1)
    obj=bpy.data.objects.new("sf_"+name,curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


class Kit:
    def __init__(self):
        self.groups={}
        self.paths={}
        self.focus={}
        self.cutaway_covers=[]
        self.colors={
            "ground": material("grass",(.32,.49,.31)),
            "soil": material("soil",(.45,.29,.19)),
            "sky": material("sky",(.54,.72,.87)),
            "walls": material("plaster",(.84,.79,.68)),
            "roof": material("roof",(.63,.25,.2)),
            "dark": material("steel",(.18,.25,.3),metallic=.55),
            "white": material("trim",(.91,.91,.86)),
            "blue": material("water",(.06,.50,.83),roughness=.2),
            "glass": material("windows",(.2,.59,.72),roughness=.18),
            "sun": material("sunlight",(.98,.72,.12),emission=1.5),
            "panels": material("solar",(.045,.13,.24),metallic=.3),
            "cable": material("electric",(.97,.67,.10),emission=.6),
            "battery": material("storage",(.27,.57,.48)),
            "road": material("asphalt",(.34,.37,.38)),
        }

    def put(self, name, *objects):
        self.groups.setdefault(name,[]).extend(objects)
        return objects

    def scene_ground(self, *, cutaway=False):
        if cutaway:
            # Exposed trench is physically open, not a flat texture pretending
            # to show buried pipes. Its cover disappears at the cutaway beat.
            self.put("ground",
                cube("earth_north",(0,5.2,-1.3),(34,16.6,2.5),self.colors["soil"]),
                cube("grass_north",(0,5.2,-.025),(34,16.6,.07),self.colors["ground"]),
                cube("earth_south",(0,-9.25,-1.3),(34,8.5,2.5),self.colors["soil"]),
                cube("grass_south",(0,-9.25,-.025),(34,8.5,.07),self.colors["ground"]))
            cover=cube("trench_grass_cover",(0,-4.05,-.04),
                       (34,1.9,.085),self.colors["ground"])
            self.put("ground",cover)
            self.cutaway_covers.append(cover)
        else:
            self.put("ground",cube("earth", (0,0,-1.3), (34,27,2.5), self.colors["soil"]))
            self.put("ground",cube("grass_top", (0,0,-.025), (34,27,.07), self.colors["ground"]))
        self.put("ground",cube("road", (0,-7.2,.02), (34,3.4,.055), self.colors["road"]))
        for x in range(-14,15,4):
            self.put("ground",cube("lane_"+str(x),(x,-7.2,.056),(1.65,.08,.009),self.colors["white"]))
        for i,xyz in enumerate(((-11,6,1.2),(-9,8,1.5),(9,9,1.1),(11,6,1.3))):
            stem=cylinder(f"tree_stem_{i}",(xyz[0],xyz[1],.65),.13,1.3,self.colors["dark"])
            leaves=sphere(f"tree_canopy_{i}",(xyz[0],xyz[1],xyz[2]+.4),1.05,self.colors["ground"])
            self.put("ground",stem,leaves)

    def house(self, name, x,y, *, tint=None):
        walls=self.colors["walls"] if tint is None else material(name+"walls",tint)
        a=[
            cube(name+"_walls",(x,y,1.4),(3.0,2.7,2.8),walls),
            # Left slope rises to ridge; right slope descends to the eave.
            # This corrects the inverted valley-roof geometry in the first preview.
            cube(name+"_roofL",(x-.84,y,3.34),(1.84,3.10,.17),
                 self.colors["roof"],tilt=-ROOF_PITCH),
            cube(name+"_roofR",(x+.84,y,3.34),(1.84,3.10,.17),
                 self.colors["roof"],tilt=ROOF_PITCH),
            cube(name+"_ridge",(x,y,ROOF_RIDGE+.02),(.13,3.16,.10),self.colors["roof"]),
            gable(name+"_gable",x,y,walls),
            cube(name+"_door",(x-.55,y-1.36,.95),(.65,.06,1.7),self.colors["dark"]),
            cube(name+"_window",(x+.60,y-1.38,1.8),(.75,.08,.78),self.colors["glass"]),
        ]
        return a

    def water(self):
        self.scene_ground(cutaway=True)
        for i,(x,y) in enumerate(((-11,4),(-7,4),(-3,4),(-11,-2),(-7,-2),(-3,-2))):
            self.put("neighbourhood",*self.house(f"water_home_{i}",x,y,
                      tint=(.80+.012*i,.76,.66+.014*i)))
        self.put("reservoir",cube("storage_lake",(-11,10,-.0),(7,3.5,.12),self.colors["blue"]))
        self.put("pump",cube("pump_base",(1.4,2,.4),(2,1.6,.8),self.colors["dark"]),
                 cylinder("pump_motor",(1.4,2,.96),.55,.45,self.colors["blue"]))
        self.put("tower",*[
            cylinder(f"tower_leg_{i}",(4+dx,3+dy,3.1),.20,6.2,self.colors["dark"])
            for i,(dx,dy) in enumerate(((-1.15,-1.15),(1.15,-1.15),(-1.15,1.15),(1.15,1.15)))
        ])
        for i,((x1,y1),(x2,y2)) in enumerate([
            ((2.85,1.85),(5.15,4.15)),((5.15,1.85),(2.85,4.15))
        ]):
            self.put("tower",pipe(f"brace_{i}",[(x1,y1,1.4),(x2,y2,5.1)],
                                   self.colors["dark"],.10))
        self.put("tank",cylinder("tank_shell",(4,3,7.1),1.7,2.1,self.colors["blue"]),
                 cylinder("tank_lid",(4,3,8.19),1.79,.16,self.colors["white"]),
                 cylinder("tank_base",(4,3,6.05),1.60,.16,self.colors["dark"]))
        self.put("main",pipe("rising_pipe",[(1.4,2,.7),(4,2,.7),(4,2,6.8)],
                             self.colors["blue"],.13),
                 pipe("distribution_main",[(4,3,1),(4,-4,-.2),(-13,-4,-.2)],
                      self.colors["blue"],.15))
        self.paths["main"]=[(4,3,7.1),(4,3,1),(4,-4,-.2),(-13,-4,-.2)]
        branch_objs=[]
        for i,x in enumerate((-11,-7,-3)):
            branch_objs.append(pipe(f"branch_{i}",[(x,-4,-.2),(x,1,-.2),(x,2.5,.25)],
                                    self.colors["blue"],.075))
        self.put("branch",*branch_objs)
        self.paths["branch"]=[(-11,-4,-.2),(-11,1,-.2),(-11,2.5,.25)]
        self.put("faucet",cube("tap_body",(-11,1,1),(.45,.4,.35),self.colors["white"]),
                 pipe("tap_spout",[(-11,1,1.4),(-11,1.6,1.4),(-11,1.6,1.05)],self.colors["dark"],.055))
        self.paths["faucet"]=[(-11,1,1.4),(-11,1.6,1.4),(-11,1.6,1.05)]

    def solar(self):
        """One electrically connected and mechanically plausible rooftop system.

        All coordinates are metres and local to the main house centre.
        Visible model parts stay registered to the storyboard's semantic targets.
        """
        self.scene_ground()
        self.put("house",*self.house("solar_main",0,1.0))
        for i,(dx,dy) in enumerate(((-8,5),(-11,2),(9,6))):
            self.put("house",*self.house(f"nearby_{i}",dx,dy,
                         tint=(.79,.78,.68+.025*i)))

        # Two columns by three rows, flush with the right gable roof.
        # Pitched panels and concealed rails have the same roof angle.
        panel_assets=[]
        for col,local_x in enumerate((.48,1.17)):
            for row,local_y in enumerate((-.82,0,.82)):
                centre_y=1.0+local_y
                centre_z=roof_height(local_x)+.18
                panel_assets.append(cube(
                    f"pv_{col}_{row}",(local_x,centre_y,centre_z),
                    (.69,.72,.055),self.colors["panels"],tilt=ROOF_PITCH))
                # Two thin silver standoff rails on the upper roof surface.
                for du in (-.20,.20):
                    px,p_y,p_z=roof_surface_point(local_x,centre_y,du,0,offset=.105)
                    panel_assets.append(cube(
                        f"pv_mount_{col}_{row}_{int(du*100)}",(px,p_y,p_z),
                        (.065,.69,.055),self.colors["dark"],tilt=ROOF_PITCH))
                # Subtle cell divisions, following the physical roof normal.
                for u in (-.12,.12):
                    p0=roof_surface_point(local_x,centre_y,u,-.34,offset=.216)
                    p1=roof_surface_point(local_x,centre_y,u,.34,offset=.216)
                    panel_assets.append(pipe(f"pv_cell_line_u_{col}_{row}_{int(u*100)}",
                                             [p0,p1],self.colors["glass"],.006))
                for v in (-.16,.16):
                    p0=roof_surface_point(local_x,centre_y,-.30,v,offset=.216)
                    p1=roof_surface_point(local_x,centre_y,.30,v,offset=.216)
                    panel_assets.append(pipe(f"pv_cell_line_v_{col}_{row}_{int(v*100)}",
                                             [p0,p1],self.colors["glass"],.006))
        self.put("panels",*panel_assets)

        # Sun is a small environmental cue, not a giant disc behind the roof.
        self.put("sun",sphere("sun_ball",(-5.3,4.2,9.2),.65,self.colors["sun"]))

        # Distinct visible wire routes: DC roof -> wall-mounted inverter,
        # AC inverter -> meter -> home, and optional battery / grid interfaces.
        self.put("inverter",
                 cube("inverter",(1.64,-.20,1.62),(.28,.70,1.03),
                      self.colors["white"]),
                 cube("inverter_status",(1.792,-.40,1.82),(.018,.20,.16),
                      self.colors["battery"]),
                 pipe("dc_conduit",[(1.30,.20,3.20),(1.58,.20,2.97),
                                    (1.58,-.20,2.40),(1.58,-.20,2.11)],
                      self.colors["dark"],.035))

        self.put("meter",
                 cube("energy_meter",(.92,-1.41,1.70),(.44,.16,.65),
                      self.colors["white"]),
                 cube("meter_screen",(.92,-1.505,1.79),(.24,.025,.18),
                      self.colors["glass"]),
                 pipe("ac_wall_conduit",[(1.66,-.22,1.50),(1.60,-1.43,1.50),
                                          (1.15,-1.43,1.50)],
                      self.colors["dark"],.032))

        # Storage is placed on a pad at grade, with a physical DC cable.
        self.put("battery",
                 cube("storage_pad",(2.16,-.45,.09),(1.0,.90,.18),
                      self.colors["white"]),
                 cube("battery_enclosure",(2.16,-.45,.81),(.69,.60,1.25),
                      self.colors["battery"]),
                 cube("battery_indicator",(2.16,-.77,1.08),(.20,.018,.12),
                      self.colors["glass"]),
                 pipe("battery_conduit",[(1.72,-.25,1.22),(1.88,-.25,1.22),
                                          (1.88,-.45,1.22),(1.88,-.45,.80)],
                      self.colors["dark"],.030))

        # Low-contrast utility connection, no unexplained luminous diagonal.
        self.put("grid",
                 pipe("power_pole",[(7,-2,0),(7,-2,5.0)],
                      self.colors["dark"],.11),
                 pipe("service_drop",[(7,-2,4.50),(5,-2,3.80),
                                      (2.8,-1.6,2.8),(1.45,-1.43,1.7)],
                      self.colors["dark"],.028))
        self.put("lights",
                 sphere("window_lamp",(.62,-1.435,1.78),.12,self.colors["sun"]))

        # Particle flow routes deliberately match actual cable endpoints.
        self.paths["sun"]=[(-5.3,4.2,9.2),(.85,1.0,3.5)]
        self.paths["panels"]=[(1.30,.20,3.20),(1.58,.20,2.97),
                               (1.58,-.20,2.40),(1.58,-.20,2.11)]
        self.paths["battery"]=[(1.72,-.25,1.22),(1.88,-.25,1.22),
                                (1.88,-.45,.80),(2.16,-.45,.81)]
        self.paths["grid"]=[(1.45,-1.43,1.7),(2.8,-1.6,2.8),
                             (5,-2,3.80),(7,-2,4.50)]
        self.paths["inverter"]=self.paths["panels"]
        self.paths["lights"]=[(1.15,-1.43,1.50),(.62,-1.435,1.78)]

        # Stable semantic camera anchors, not averages across unrelated houses.
        self.focus.update({
            "sun":(.0,1.0,3.25),"house":(.0,1.0,2.0),
            "panels":(.82,1.0,3.35),"inverter":(1.0,-.55,1.75),
            "battery":(1.4,-.6,1.35),"meter":(.65,-.9,1.8),
            "grid":(2.9,-1.1,2.4),"lights":(.55,-.9,1.75),
            "ground":(0,1.0,.5),
        })

    def build(self, scene_template):
        if scene_template=="water_distribution":
            self.water()
        elif scene_template=="solar_home":
            self.solar()
        else:
            raise ValueError("Unregistered template "+str(scene_template))
        return self
