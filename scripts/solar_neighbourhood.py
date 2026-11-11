"""Procedural suburban set, service equipment and enlarged PV teaching models."""

import math

import bpy

from blender_assets_v2 import cube, cylinder, material, pipe, sphere
from shortforge.scene_math import ROOF_PITCH, roof_height, roof_surface_point


def _box_span(name, x0, x1, y, z0, z1, depth, finish):
    return cube(name, ((x0+x1)/2,y,(z0+z1)/2), (x1-x0,depth,z1-z0), finish)


def _roof_end(name, x, y, finish):
    """End-wall profile terminates at the underside of the two roof slopes."""
    shape = [(-1.5,2.8),(1.5,2.8),(1.5,roof_height(1.5)-.085/math.cos(ROOF_PITCH)),
             (0,roof_height(0)-.085/math.cos(ROOF_PITCH)),
             (-1.5,roof_height(1.5)-.085/math.cos(ROOF_PITCH))]
    vertices = [(x+u,y+d,z) for d in (-.085,.085) for u,z in shape]
    faces = [(0,1,2,3,4),(9,8,7,6,5)]+[(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.materials.append(finish)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def detailed_house(kit, name, x, y, siding):
    """Build the wall around the clear openings, then fit frames and infill."""
    trim=kit.colors["white"]
    dark=kit.colors["dark"]
    roof=kit.colors["roof"]
    front=y-1.265
    door=(-1.20,-.27,.13,2.10)
    window=(.12,1.17,.98,2.17)
    parts=[]

    def facade(part, lo, hi, bottom, top):
        parts.append(_box_span(name+part,x+lo,x+hi,front,bottom,top,.17,siding))

    facade("_pier_left",-1.50,door[0],.12,2.80)
    facade("_pier_centre",door[1],window[0],.12,2.80)
    facade("_pier_right",window[1],1.50,.12,2.80)
    facade("_door_header",door[0],door[1],door[3],2.80)
    facade("_window_header",window[0],window[1],window[3],2.80)
    facade("_window_apron",window[0],window[1],.12,window[2])

    def box(part, pos, dims, finish, **kwargs):
        parts.append(cube(name+part,(x+pos[0],y+pos[1],pos[2]),dims,finish,**kwargs))

    box("_slab",(0,0,.065),(3.08,2.78,.13),kit.colors["concrete"])
    box("_rear_wall",(0,1.265,1.46),(3,.17,2.68),siding)
    for side,sign in (("L",-1),("R",1)):
        box("_side"+side,(sign*1.415,0,1.55),(.17,2.36,2.86),siding)
        box("_roof"+side,(sign*.84,0,3.34),(1.84,3.10,.17),roof,tilt=sign*ROOF_PITCH)
        box("_bargeboard"+side,(sign*.84,-1.565,3.315),(1.87,.065,.12),trim,tilt=sign*ROOF_PITCH)
    box("_ridge",(0,0,3.74),(.13,3.16,.10),roof)
    parts.extend(_roof_end(name+"_gable_"+str(i),x,front_y,siding)
                 for i,front_y in enumerate((front,y+1.265)))

    for label,(left,right,bottom,top) in (("door",door),("window",window)):
        for edge in (left+.038,right-.038):
            box(f"_{label}_jamb",(edge,-1.31,(bottom+top)/2),(.076,.15,top-bottom),trim)
        box(f"_{label}_head",((left+right)/2,-1.31,top-.038),(right-left,.15,.076),trim)
    box("_door_leaf",(-.735,-1.28,1.077),(.772,.058,1.876),kit.colors["door"])
    for z in (.62,1.48):
        box("_door_inset",(-.735,-1.318,z),(.55,.019,.59),kit.colors["door_panel"])
    box("_door_pull",(-.46,-1.346,1.08),(.035,.046,.18),kit.colors["brass"])
    box("_threshold",(-.735,-1.37,.135),(.87,.19,.045),dark)
    box("_window_sill",(.645,-1.36,1.0),(1.10,.25,.075),trim)
    box("_glazing",(.645,-1.275,1.575),(.898,.035,1.04),kit.colors["glass"])
    box("_window_mullion",(.645,-1.32,1.576),(.055,.105,1.12),trim)
    box("_window_transom",(.645,-1.32,1.69),(.91,.105,.052),trim)
    return parts


def _plant(kit, name, x, y, height):
    trunk=cylinder(name+"_trunk",(x,y,height*.34),height*.033,height*.68,kit.colors["bark"])
    leaves=[]
    for i,(dx,dy,z,r) in enumerate(((0,0,.8,.34),(.15,.02,.66,.27),(-.16,.05,.72,.26),(.03,-.16,.78,.25))):
        leaves.append(sphere(f"{name}_{i}",(x+height*dx,y+height*dy,height*z),height*r,
                             kit.colors["leaf"] if i%2 else kit.colors["leaf_dark"]))
    return [trunk,*leaves]


def _ride(kit, name, parts, start, finish, first, last):
    rig=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(rig)
    for part in parts:
        part.parent=rig
    for point,key in ((start,first),(finish,last)):
        rig.location=point
        rig.keyframe_insert(data_path="location",frame=key)
    if rig.animation_data and rig.animation_data.action:
        for curve in rig.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation="LINEAR"
    kit.put("ground",*parts)


def _wheel(kit, name, x, y, z, radius, width):
    tire=cylinder(name+"_tire",(x,y,z),radius,width,kit.colors["rubber"],vertices=24)
    hub=cylinder(name+"_hub",(x,y,z),radius*.62,width+.012,kit.colors["steel"],vertices=20)
    for obj in (tire,hub):
        obj.rotation_euler.x=math.pi/2
    return [tire,hub]


def street(kit):
    kit.colors.update({
        "roof": material("solar_graphite_roof",(.11,.145,.18),roughness=.73),
        "white": material("solar_ivory_trim",(.75,.68,.55),roughness=.56),
        "glass": material("solar_blue_glazing",(.026,.11,.17),metallic=.23,roughness=.21),
        "concrete": material("solar_concrete",(.40,.36,.30),roughness=.84),
        "door": material("solar_oak_door",(.28,.095,.042),roughness=.55),
        "door_panel": material("solar_oak_infill",(.37,.14,.061),roughness=.53),
        "brass": material("solar_brass",(.63,.32,.082),metallic=.65,roughness=.3),
        "bark": material("solar_bark",(.13,.066,.027),roughness=.91),
        "leaf": material("solar_leaf",(.18,.39,.05),roughness=.82),
        "leaf_dark": material("solar_leaf_dark",(.057,.22,.042),roughness=.82),
        "rubber": material("solar_tyre",(.018,.022,.026),roughness=.9),
        "steel": material("solar_brushed_alloy",(.36,.43,.49),metallic=.66,roughness=.32),
        "ground": material("solar_lawn",(.125,.29,.069),roughness=.92),
        "road": material("solar_asphalt",(.070,.082,.091),roughness=.89),
        "panels": material("solar_deep_pv",(.017,.055,.14),metallic=.24,roughness=.29),
    })
    kit.scene_ground()
    concrete=kit.colors["concrete"]
    kit.put("ground",cube("solar_sidewalk",(0,-4.98,.065),(33,1.03,.13),concrete),
            cube("solar_curb",(0,-5.49,.065),(33,.11,.13),kit.colors["white"]))
    for i,x in enumerate((-9,-4.6,4.6,9)):
        kit.put("ground",cube(f"driveway_{i}",(x,-2.68,.03),(1.25,4.5,.055),concrete))
    for i,(x,y,h) in enumerate(((-3.25,.5,1.8),(-6.8,-2.6,1.25),(3.35,.8,1.55),(6,-2.6,1.4),(-5.9,4.1,2.3),(6.3,4.5,2.35))):
        kit.put("ground",*_plant(kit,f"street_tree_{i}",x,y,h))
    for i,(x,y,tint) in enumerate(((-5.15,1.8,(.47,.62,.57)),(5.35,2.1,(.66,.42,.31)),
                                   (-10,2.4,(.58,.63,.72)),(10.2,2.7,(.57,.52,.38)))):
        kit.put("ground",*kit.house(f"neighbour_{i}",x,y,tint=tint))
    kit.put("house",*detailed_house(kit,"solar_main",0,1,material("solar_warm_siding",(.68,.49,.30))))
    kit.subjects["house"]=list(kit.groups["house"])
    path=cube("solar_front_walk",(-.73,-2.52,.037),(.87,4.4,.06),concrete)
    kit.put("ground",path,cube("solar_entry_stoop",(-.73,-.49,.075),(1.22,.57,.15),concrete))
    framing=[]
    for side in (-3.4,3.4):
        marker=cube("nearby_lane_dash",(side,-7.2,.058),(.65,.08,.012),kit.colors["white"])
        kit.put("ground",marker)
        framing.append(marker)
    kit.establish_subjects={"house":kit.subjects["house"]+[path,*framing]}
    garden=material("solar_mulch",(.16,.071,.029),roughness=.95)
    kit.put("ground",cube("solar_front_bed",(.83,-.91,.048),(1.06,.55,.075),garden))
    for i in range(5):
        kit.put("ground",sphere(f"front_shrub_{i}",(.42+i*.20,-.93,.14),.12,kit.colors["leaf_dark"]))

    car=material("solar_car_paint",(.48,.065,.03),metallic=.35,roughness=.33)
    body=[cube("car_body",(0,0,.28),(1.74,.75,.29),car),
          cube("car_cabin",(-.10,0,.51),(.89,.65,.25),kit.colors["glass"]),
          cube("car_roof",(-.10,0,.643),(.86,.62,.042),car)]
    for x in (-.55,.55):
        for y in (-.37,.37):
            body.extend(_wheel(kit,"car",x,y,.155,.152,.09))
    scene=bpy.context.scene
    _ride(kit,"solar_car",body,(-11,-6.4,.05),(12,-6.4,.05),1,scene.render.fps*12)

    bike=material("solar_bicycle_teal",(.025,.48,.40),metallic=.2,roughness=.4)
    rider=material("solar_rider_jacket",(.14,.22,.67))
    skin=material("solar_rider_skin",(.49,.25,.12))
    parts=_wheel(kit,"bike_front",.34,0,.23,.22,.044)+_wheel(kit,"bike_rear",-.34,0,.23,.22,.044)
    parts.extend((pipe("bike_frame",[(-.34,0,.23),(-.10,0,.51),(.05,0,.23),(-.34,0,.23),
                                     (.24,0,.51),(.05,0,.23),(-.10,0,.51)],bike,.025),
                  pipe("bike_fork",[(.34,0,.23),(.24,0,.51),(.21,0,.63)],bike,.024),
                  cube("bike_seat",(-.10,0,.54),(.18,.105,.04),kit.colors["rubber"]),
                  pipe("cyclist_torso",[(-.12,0,.59),(.01,0,.87)],rider,.09),
                  pipe("cyclist_arms",[(.01,0,.84),(.15,-.11,.72),(.22,-.10,.61)],rider,.035),
                  pipe("cyclist_legs",[(-.12,0,.58),(.13,-.075,.39),(.03,-.08,.25)],kit.colors["dark"],.051),
                  sphere("cyclist_head",(.07,0,.963),.079,skin),
                  sphere("cyclist_helmet",(.064,0,1.01),.083,kit.colors["white"])))
    _ride(kit,"solar_cyclist",parts,(-7,-4.95,.13),(10,-4.95,.13),1,scene.render.fps*11)


def electrical(kit):
    alloy,trim,dark=(kit.colors[k] for k in ("steel","white","dark"))
    screen=material("solar_display",(.024,.24,.25),roughness=.35,emission=.25)
    dc=[(1.30,.20,3.20),(1.56,.20,2.99),(1.57,-.03,2.47),(1.57,-.03,2.12)]
    kit.put("inverter",cube("inverter",(1.64,-.03,1.62),(.28,.54,1.0),trim),
            cube("inverter_mount",(1.515,-.03,1.62),(.03,.59,1.04),alloy),
            cube("inverter_control",(1.79,-.03,1.80),(.022,.35,.23),dark),
            cube("inverter_screen",(1.808,-.03,1.836),(.018,.20,.07),screen),
            pipe("dc_conduit",dc,dark,.029))
    for i in range(6):
        kit.put("inverter",cube("inverter_vent",(1.788,-.215+i*.074,1.38),(.018,.033,.20),dark))
    for y in (-.19,.13):
        kit.put("inverter",cylinder("inverter_gland",(1.62,y,1.10),.052,.091,dark))

    kit.put("distribution",cube("panel_backbox",(1.585,.72,1.56),(.17,.51,.71),alloy),
            cube("panel_deadfront",(1.682,.72,1.56),(.045,.47,.66),dark),
            cube("panel_directory",(1.711,.72,1.785),(.015,.35,.09),trim),
            pipe("inverter_to_panel",[(1.61,.13,1.10),(1.55,.13,.94),(1.55,.72,.94),(1.58,.72,1.20)],dark,.025))
    for row in range(4):
        for col in range(2):
            y=.60+col*.24
            z=1.66-row*.093
            kit.put("distribution",cube("breaker_body",(1.713,y,z),(.044,.17,.072),trim),
                    cube("breaker_toggle",(1.743,y,z+.012),(.036,.066,.029),dark),
                    cube("breaker_index",(1.741,y-.062,z),(.014,.021,.042),screen))

    kit.put("meter",cube("energy_meter",(1.58,1.56,1.57),(.16,.32,.49),alloy),
            cube("meter_face",(1.669,1.56,1.62),(.033,.27,.29),dark),
            cube("meter_screen",(1.692,1.56,1.663),(.020,.185,.083),screen),
            pipe("ac_wall_conduit",[(1.59,.94,1.35),(1.55,1.10,1.19),(1.55,1.56,1.19),(1.58,1.56,1.325)],dark,.024))

    service=[(1.59,1.56,1.80),(1.56,1.56,2.85),(4.75,-.62,3.58),(7,-2,4.5)]
    kit.put("grid",pipe("power_pole",[(7,-2,0),(7,-2,5)],kit.colors["bark"],.105),
            pipe("service_drop",service,dark,.023),
            cube("pole_crossarm",(7,-2,4.52),(.74,.10,.10),dark))
    kit.put("battery",cube("storage_pad",(2.55,2.05,.075),(.99,.86,.15),kit.colors["concrete"]),
            cube("battery_enclosure",(2.55,2.05,.765),(.68,.55,1.23),kit.colors["battery"]),
            cube("battery_seam",(2.55,1.767,.85),(.59,.022,.035),dark),
            cube("battery_status",(2.55,1.761,1.08),(.18,.025,.12),screen),
            pipe("battery_conduit",[(1.62,-.19,1.10),(1.82,-.19,.30),(1.82,2.05,.30),(2.23,2.05,.48)],dark,.026))

    # A separate porch luminaire on the front wall, away from the service wall.
    kit.put("lights",cube("porch_light_mount",(-.735,-.371,2.36),(.26,.042,.15),dark),
            cube("porch_light_shade",(-.735,-.451,2.32),(.27,.144,.10),dark),
            cube("porch_light_diffuser",(-.735,-.451,2.26),(.205,.104,.028),kit.colors["sun"]))
    kit.paths.update(inverter=dc,panels=dc,grid=service,
                     battery=[(1.62,-.19,1.10),(1.82,-.19,.30),(1.82,2.05,.30),(2.23,2.05,.48)])
    kit.subjects["inverter"]=kit.groups["inverter"][:4]
    kit.subjects["distribution"]=kit.groups["distribution"][:3]+kit.groups["lights"]
    kit.subjects["meter"]=kit.groups["meter"][:3]


def cell_stage(kit):
    """Separate enlarged set. Dots are schematic carriers, not literal sizes."""
    x=25.0
    slate=material("pv_display_stage",(.034,.052,.075),roughness=.72)
    silicon_a=material("pv_silicon_top",(.033,.22,.42),roughness=.48)
    silicon_b=material("pv_silicon_bottom",(.35,.10,.19),roughness=.49)
    coating=material("pv_front_surface",(.038,.097,.16),roughness=.33)
    metal=kit.colors["steel"]
    kit.put("ground",cube("pv_studio_base",(x,1,-.14),(60,60,.15),slate))
    kit.put("ground",cube("pv_studio_backdrop",(x,5,2.85),(9,.24,6),slate))
    bpy.ops.object.light_add(type="AREA",location=(x-2,-3,6))
    light=bpy.context.object
    light.name="pv_studio_key"
    light.data.energy=450
    light.data.size=4
    from mathutils import Vector
    light.rotation_euler=(Vector((x,0,1))-light.location).to_track_quat("-Z","Y").to_euler()
    kit.put("pv_cell",cube("pv_display_plinth",(x,0,.30),(2.15,1.46,.60),slate))
    for name,z,dims,finish in (("rear_contact",.64,(1.95,1.29,.075),metal),
                                ("silicon_lower",.81,(1.91,1.24,.27),silicon_b),
                                ("junction",.960,(1.91,1.25,.035),kit.colors["white"]),
                                ("silicon_upper",1.064,(1.91,1.24,.17),silicon_a),
                                ("front_coating",1.165,(1.91,1.24,.032),coating)):
        kit.put("pv_cell",cube("pv_macro_"+name,(x,0,z),dims,finish))
    for name,z in (("n-type silicon",1.05),("p-type silicon",.80)):
        font=bpy.data.curves.new(name,"FONT")
        font.body=name
        font.size=.105
        font.align_x="CENTER"
        obj=bpy.data.objects.new(name,font)
        bpy.context.collection.objects.link(obj)
        obj.location=(x,-.633,z)
        obj.rotation_euler=(math.pi/2,0,0)
        font.materials.append(kit.colors["white"])
        kit.put("pv_cell",obj)
    for i in range(11):
        kit.put("pv_cell",cube("pv_macro_finger",(x-.85+i*.17,0,1.19),(.014,1.19,.019),metal))
    for y in (-.30,.30):
        kit.put("pv_cell",cube("pv_macro_busbar",(x,y,1.21),(1.87,.061,.026),metal))
    kit.put("pv_light",pipe("macro_light_guide",[(x-.60,-.73,2.01),(x-.29,-.65,1.20)],kit.colors["sun"],.019))
    kit.put("pv_carriers",pipe("macro_electron_guide",[(x-.14,-.665,.96),(x+.59,-.666,1.12)],silicon_a,.017))
    kit.put("pv_shade",cube("pv_shadow_patch",roof_surface_point(1.17,.18,0,0,offset=.205),(.26,.36,.018),slate,tilt=ROOF_PITCH))
    bypass=[(x-.92,-.68,.52),(x-.92,-.77,.31),(x+.89,-.77,.31),(x+.89,-.68,.52)]
    kit.put("pv_bypass",pipe("macro_bypass_wire",bypass,kit.colors["brass"],.023),
            cube("macro_bypass_diode",(x,-.77,.31),(.31,.11,.098),kit.colors["dark"]),
            cube("macro_diode_band",(x+.087,-.77,.31),(.044,.113,.10),kit.colors["white"]))
    kit.paths.update(pv_light=[(x-.60,-.73,2.01),(x-.29,-.65,1.20),(x-.14,-.665,.96)],
                     pv_carriers=[(x-.14,-.665,.96),(x+.59,-.666,1.12)],pv_bypass=bypass)
    kit.extra_flows={"pv_carriers": [([(x-.14,-.671,.96),(x-.64,-.674,.74)],(.97,.18,.21))]}
    kit.flow_colors={"pv_carriers":(.13,.78,1.0),"pv_bypass":(.96,.59,.09)}
    kit.cut_targets={"pv_cell","pv_light","pv_carriers","pv_bypass"}
    kit.shot_only={"pv_light","pv_carriers","pv_shade","pv_bypass"}
    for target in kit.cut_targets:
        kit.subjects[target]=kit.groups["pv_cell"]+kit.groups[target] if target!="pv_cell" else kit.groups["pv_cell"]
    kit.subjects["pv_shade"]=kit.groups["panels"]
