"""Procedural suburban set, service equipment and enlarged PV teaching models."""

import math
import random

import bpy
from mathutils import Vector

from blender_assets_v2 import cube, cylinder, material, pipe, sphere
from shortforge.scene_math import ROOF_PITCH, roof_height, roof_surface_point


def _area(scene, name, position, target, power, size, color):
    light=bpy.data.lights.new(name,"AREA")
    light.energy=power
    light.shape="DISK"
    light.size=size
    light.color=color
    light.use_shadow_jitter=True
    obj=bpy.data.objects.new(name,light)
    scene.collection.objects.link(obj)
    obj.location=position
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def solar_lighting(scene, sun, key):
    """Daylight for the street, with soft keys aimed at the equipment and cutaways."""
    scene.eevee.use_raytracing=False
    sun.data.energy=1.55
    sun.data.angle=.19
    key.data.energy=2350
    key.data.use_shadow_jitter=True
    _area(scene,"Service wall softbox",(5.8,-2.0,4.7),(1.6,.75,1.6),490,4.0,(.88,.94,1))
    _area(scene,"Side yard bounce",(4.0,5.6,5.3),(2.55,2.05,1),300,5.0,(.90,.96,1))
    _area(scene,"Porch bounce",(-1.0,-4.9,3.5),(-.73,-.45,2.1),185,3.4,(1,.93,.84))
    _area(scene,"Cell stage softbox",(25,-3.8,3.8),(25,0,1),245,3.6,(.93,.97,1))
    _area(scene,"Diode stage softbox",(31,-3.4,3.1),(30,0,.85),340,3.8,(1,.96,.90))

    tree=scene.world.node_tree
    nodes,links=tree.nodes,tree.links
    sky=nodes.get("Background")
    sky.inputs["Strength"].default_value=.80
    coords=nodes.new("ShaderNodeTexCoord")
    split=nodes.new("ShaderNodeSeparateXYZ")
    links.new(coords.outputs["Normal"],split.inputs[0])
    height=nodes.new("ShaderNodeMath")
    height.operation="ABSOLUTE"
    links.new(split.outputs["Z"],height.inputs[0])
    gradient=nodes.new("ShaderNodeValToRGB")
    gradient.color_ramp.elements[0].color=(.36,.60,.94,1)
    gradient.color_ramp.elements[1].position=.52
    gradient.color_ramp.elements[1].color=(.032,.23,.63,1)
    links.new(height.outputs[0],gradient.inputs["Fac"])
    stretch=nodes.new("ShaderNodeVectorMath")
    stretch.operation="MULTIPLY"
    stretch.inputs[1].default_value=(2.1,2.1,6.8)
    links.new(coords.outputs["Normal"],stretch.inputs[0])
    clouds=nodes.new("ShaderNodeTexNoise")
    clouds.inputs["Scale"].default_value=3.2
    clouds.inputs["Detail"].default_value=3.0
    links.new(stretch.outputs["Vector"],clouds.inputs["Vector"])
    cover=nodes.new("ShaderNodeValToRGB")
    cover.color_ramp.elements[0].position=.55
    cover.color_ramp.elements[1].position=.70
    cover.color_ramp.interpolation="EASE"
    links.new(clouds.outputs["Fac"],cover.inputs["Fac"])
    mix=nodes.new("ShaderNodeMixRGB")
    mix.inputs[2].default_value=(1.72,1.77,1.84,1)
    links.new(cover.outputs["Color"],mix.inputs[0])
    links.new(gradient.outputs["Color"],mix.inputs[1])
    links.new(mix.outputs[0],sky.inputs["Color"])
    ambient=nodes.new("ShaderNodeBackground")
    ambient.inputs["Color"].default_value=(.46,.65,.85,1)
    ambient.inputs["Strength"].default_value=.36
    light_path=nodes.new("ShaderNodeLightPath")
    background=nodes.new("ShaderNodeMixShader")
    links.new(light_path.outputs["Is Camera Ray"],background.inputs[0])
    links.new(ambient.outputs[0],background.inputs[1])
    links.new(sky.outputs[0],background.inputs[2])
    links.new(background.outputs[0],nodes.get("World Output").inputs["Surface"])


def _surface_relief(finish, *, siding=False):
    tree=finish.node_tree
    nodes,links=tree.nodes,tree.links
    geometry=nodes.new("ShaderNodeNewGeometry")
    position=geometry.outputs["Position"]
    if siding:
        split=nodes.new("ShaderNodeSeparateXYZ")
        links.new(position,split.inputs[0])
        scale=nodes.new("ShaderNodeMath")
        scale.operation="MULTIPLY"
        scale.inputs[1].default_value=5.6
        links.new(split.outputs["Z"],scale.inputs[0])
        period=nodes.new("ShaderNodeMath")
        period.operation="FRACT"
        links.new(scale.outputs[0],period.inputs[0])
        edge=nodes.new("ShaderNodeValToRGB")
        edge.color_ramp.elements[1].position=.09
        links.new(period.outputs[0],edge.inputs["Fac"])
        height=edge.outputs["Color"]
    else:
        noise=nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value=52
        links.new(position,noise.inputs["Vector"])
        height=noise.outputs["Fac"]
    bump=nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=.38
    bump.inputs["Distance"].default_value=.012 if siding else .006
    links.new(height,bump.inputs["Height"])
    links.new(bump.outputs["Normal"],nodes.get("Principled BSDF").inputs["Normal"])


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
    _surface_relief(siding,siding=True)
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


def _chimney(kit, name, x, y):
    brick=material("solar_chimney_brick",(.32,.12,.073),roughness=.86)
    local_x=-.83
    base=roof_height(local_x)+.085/math.cos(ROOF_PITCH)
    px=x+local_x
    return [cube(name+"_flashing",(px,y,base),(.45,.42,.042),kit.colors["steel"],tilt=-ROOF_PITCH),
            cube(name+"_shaft",(px,y,base+.27),(.32,.30,.64),brick),
            cube(name+"_cap",(px,y,base+.61),(.39,.37,.066),kit.colors["concrete"]),
            cube(name+"_flue",(px,y,base+.66),(.17,.15,.048),kit.colors["dark"])]


def _grass_patch(kit, name, centre, size, seed):
    rng=random.Random(seed)
    vertices=[]
    faces=[]
    for _ in range(round(720*size[0]*size[1])):
        x=centre[0]+rng.uniform(-size[0]/2,size[0]/2)
        y=centre[1]+rng.uniform(-size[1]/2,size[1]/2)
        h=rng.uniform(.028,.083)
        dx,dy=(rng.uniform(-.019,.019) for _ in range(2))
        k=len(vertices)
        vertices.extend(((x-.004,y,.012),(x+.004,y,.012),(x+dx,y+dy,.012+h)))
        faces.append((k,k+1,k+2))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    blade=material("solar_grass_blades",(.074,.24,.039),roughness=.96)
    mesh.materials.append(blade)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    kit.put("ground",obj)


def _lawn_texture(finish):
    tree=finish.node_tree
    shader=tree.nodes.get("Principled BSDF")
    noise=tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=56
    ramp=tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position=.25
    ramp.color_ramp.elements[0].color=(.091,.212,.044,1)
    ramp.color_ramp.elements[1].position=.78
    ramp.color_ramp.elements[1].color=(.143,.287,.072,1)
    tree.links.new(noise.outputs["Fac"],ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"],shader.inputs["Base Color"])


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
    _lawn_texture(kit.colors["ground"])
    _surface_relief(kit.colors["roof"])
    kit.scene_ground()
    kit.put("ground",cube("distant_lawn",(-2,4,-.14),(102,88,.09),kit.colors["ground"]))
    for i,(x,y,h) in enumerate(((-18,10,3.2),(-14,14,4.6),(-9,11,3.8),
                               (-4,14,4.2),(1,14,4.6),(7,12,3.6),(13,14,4.3),(16,10,3.1))):
        kit.put("ground",*_plant(kit,f"background_tree_{i}",x,y,h))
    concrete=kit.colors["concrete"]
    kit.put("ground",cube("solar_sidewalk",(0,-4.98,.065),(33,1.03,.13),concrete),
            cube("solar_curb",(0,-5.49,.065),(33,.11,.13),kit.colors["white"]))
    for i,x in enumerate((-9,-4.6,4.6,9)):
        kit.put("ground",cube(f"driveway_{i}",(x,-2.68,.03),(1.25,4.5,.055),concrete))
    for i,(x,y,h) in enumerate(((-3.25,.5,1.8),(-6.8,-2.6,1.25),(3.55,3.05,1.55),(6,-2.6,1.4),(-5.9,4.1,2.3),(6.3,4.5,2.35))):
        kit.put("ground",*_plant(kit,f"street_tree_{i}",x,y,h))
    for i,(x,y,tint) in enumerate(((-5.15,1.8,(.47,.62,.57)),(5.35,2.1,(.66,.42,.31)),
                                   (-10,2.4,(.58,.63,.72)),(10.2,2.7,(.57,.52,.38)))):
        name=f"neighbour_{i}"
        kit.put("ground",*detailed_house(kit,name,x,y,material(name+"_siding",tint)))
        if i in (0,2,3):
            kit.put("ground",*_chimney(kit,name+"_chimney",x,y+.44))
        kit.put("ground",cube(name+"_stoop",(x-.735,y-1.49,.075),(1.15,.57,.15),concrete),
                cube(name+"_walk",(x-.735,(y-1.77-4.46)/2,.032),(.69,y-1.77+4.46,.055),concrete))
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
    for i,(x,y,count) in enumerate(((-4.62,.03,4),(5.96,.28,5),(-9.4,.59,4))):
        kit.put("ground",cube(f"neighbour_bed_{i}",(x,y,.034),(1.03,.48,.065),garden))
        for shrub in range(count):
            kit.put("ground",sphere(f"neighbour_shrub_{i}_{shrub}",
                                    (x-.37+shrub*.18,y,.14),.11,kit.colors["leaf_dark"]))
    for i,(x,y,w,d) in enumerate(((.75,-1.65,1.04,.75),(-2,-2.0,.69,1.85),
                                   (-4.05,-.85,.73,1.0),(6.65,-1.38,1.05,1.38))):
        _grass_patch(kit,f"grass_tufts_{i}",(x,y),(w,d),400+i)

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


def _wall_label(name, text, position, size, finish):
    font=bpy.data.curves.new(name,"FONT")
    font.body=text
    font.size=size
    font.align_x="CENTER"
    font.align_y="CENTER"
    font.materials.append(finish)
    obj=bpy.data.objects.new(name,font)
    bpy.context.collection.objects.link(obj)
    obj.location=position
    obj.rotation_euler=(math.pi/2,0,math.pi/2)
    return obj


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
    kit.put("inverter",_wall_label("inverter_readout","DC / AC",(1.82,-.03,1.835),.029,trim))

    kit.put("distribution",cube("panel_backbox",(1.585,.72,1.56),(.17,.51,.71),alloy),
            cube("panel_deadfront",(1.682,.72,1.56),(.045,.47,.66),dark),
            cube("panel_directory",(1.711,.72,1.785),(.015,.35,.09),trim),
            pipe("inverter_to_panel",[(1.61,.13,1.10),(1.55,.13,.94),(1.55,.72,.94),(1.58,.72,1.20)],dark,.025))
    kit.put("distribution",_wall_label("panel_title","CIRCUITS",(1.72,.72,1.785),.036,dark))
    circuit_names=(("LIGHTS","OUTLETS"),("KITCHEN","COOLING"),
                   ("WATER HEAT","GARAGE"),("LAUNDRY","SPARE"))
    for row in range(4):
        for col in range(2):
            y=.60+col*.24
            z=1.66-row*.093
            kit.put("distribution",cube("breaker_body",(1.713,y,z),(.044,.17,.072),trim),
                    cube("breaker_toggle",(1.743,y,z+.012),(.036,.066,.029),dark),
                    cube("breaker_index",(1.741,y-.062,z),(.014,.021,.042),screen),
                    _wall_label(f"breaker_label_{row}_{col}",circuit_names[row][col],
                                (1.736,y+.016,z-.019),.013,dark))

    kit.put("meter",cube("energy_meter",(1.58,1.56,1.57),(.16,.32,.49),alloy),
            cube("meter_face",(1.669,1.56,1.62),(.033,.27,.29),dark),
            cube("meter_screen",(1.692,1.56,1.663),(.020,.185,.083),screen),
            pipe("ac_wall_conduit",[(1.59,.94,1.35),(1.55,1.10,1.19),(1.55,1.56,1.19),(1.58,1.56,1.325)],dark,.024))
    kit.put("meter",_wall_label("meter_register","IN / OUT",(1.703,1.56,1.674),.024,trim),
            _wall_label("meter_units","kWh",(1.703,1.56,1.646),.018,trim))

    service=[(1.59,1.56,1.80),(1.56,1.56,2.85),(4.75,-.62,3.58),(7,-2,4.5)]
    kit.put("grid",pipe("power_pole",[(7,-2,0),(7,-2,5)],kit.colors["bark"],.105),
            pipe("service_drop",service,dark,.023),
            cube("pole_crossarm",(7,-2,4.52),(.74,.10,.10),dark))
    kit.put("battery",cube("storage_pad",(2.55,2.05,.075),(.99,.86,.15),kit.colors["concrete"]),
            cube("battery_enclosure",(2.55,2.05,.765),(.68,.55,1.23),kit.colors["battery"]),
            cube("battery_seam",(2.55,1.767,.85),(.59,.022,.035),dark),
            cube("battery_status",(2.55,1.761,1.08),(.18,.025,.12),screen),
            pipe("battery_conduit",[(1.62,-.19,1.10),(1.82,-.19,.30),(1.82,2.05,.30),(2.23,2.05,.48)],dark,.026))
    for i in range(4):
        kit.put("battery",cube(f"battery_charge_bar_{i}",(2.49+i*.04,1.745,1.07),
                               (.027,.011,.048),kit.colors["white"] if i<3 else dark))

    # A separate porch luminaire on the front wall, away from the service wall.
    kit.put("lights",cube("porch_light_mount",(-.735,-.371,2.36),(.26,.042,.15),dark),
            cube("porch_light_shade",(-.735,-.451,2.32),(.27,.144,.10),dark),
            cube("porch_light_diffuser",(-.735,-.451,2.26),(.205,.104,.028),kit.colors["sun"]))
    kit.paths.update(inverter=dc,panels=dc,grid=service,
                     battery=[(1.62,-.19,1.10),(1.82,-.19,.30),(1.82,2.05,.30),(2.23,2.05,.48)])
    kit.subjects["inverter"]=kit.groups["inverter"][:4]
    kit.subjects["distribution"]=kit.groups["distribution"][:3]+kit.groups["lights"]
    kit.subjects["meter"]=kit.groups["meter"][:3]
    kit.subjects.update(breaker_detail=[o for o in kit.groups["distribution"] if o.type=="MESH"],
                        porch_fixture=kit.groups["lights"]+[
                            o for o in kit.groups["house"] if "door_head" in o.name],
                        meter_detail=kit.groups["meter"][:3],battery_detail=kit.groups["battery"][:4])
    kit.camera_directions={"inverter":(7,-3.4,2.8),"breaker_detail":(8,-2,2),
                           "porch_fixture":(1,-8,2.3),"meter_detail":(9,-2,2),
                           "battery_detail":(.7,-6,5)}
    kit.camera_minimum={"inverter":2.1,"breaker_detail":1.65,"porch_fixture":1.65,
                        "meter_detail":1.5,"battery_detail":2.4}


def _roof_leaf(kit):
    finish=material("pv_leaf_olive",(.16,.19,.035),roughness=.84)
    vein=material("pv_leaf_vein",(.28,.24,.081),roughness=.82)
    outline=[(0,-.145),(.046,-.115),(.036,-.094),(.075,-.07),(.061,-.048),
             (.092,-.012),(.074,.007),(.083,.04),(.062,.053),(.062,.087),
             (.035,.095),(.022,.126),(0,.158),(-.026,.122),(-.043,.101),
             (-.04,.074),(-.071,.057),(-.062,.035),(-.084,.003),
             (-.065,-.015),(-.072,-.051),(-.049,-.062),(-.05,-.096)]
    def point(u,v,offset):
        return roof_surface_point(1.17,.18,u+.25*v,v-.19*u,offset=offset)
    vertices=[point(u,v,.211) for u,v in outline]+[point(0,0,.233)]
    centre=len(outline)
    faces=[(i,(i+1)%centre,centre) for i in range(centre)]
    mesh=bpy.data.meshes.new("roof_leaf")
    mesh.from_pydata(vertices,[],faces)
    mesh.materials.append(finish)
    leaf=bpy.data.objects.new("sf_roof_leaf",mesh)
    bpy.context.collection.objects.link(leaf)
    kit.put("pv_shade",leaf,pipe("leaf_midrib",[
        point(0,-.179,.215),point(0,0,.236),point(0,.143,.215)],vein,.003))


def cell_stage(kit):
    """Separate enlarged set. Dots are schematic carriers, not literal sizes."""
    x=25.0
    slate=material("pv_display_stage",(.034,.052,.075),roughness=.72)
    silicon_a=material("pv_silicon_top",(.033,.22,.42),roughness=.48)
    silicon_b=material("pv_silicon_bottom",(.35,.10,.19),roughness=.49)
    coating=material("pv_front_surface",(.038,.097,.16),roughness=.33)
    metal=kit.colors["steel"]
    kit.put("ground",cube("pv_studio_base",(x+2.5,1,-.14),(17,18,.15),slate))
    kit.put("ground",cube("pv_studio_backdrop",(x+2.5,5,2.85),(17,.24,6),slate))
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
    _roof_leaf(kit)
    # The diode spans the shaded series group, while the other groups remain in circuit.
    bx=x+5
    module=cube("bypass_module_frame",(bx,0,.81),(2.74,1.08,.13),metal)
    groups=[]
    for group in range(3):
        cx=bx+(group-1)*.88
        for cell in range(3):
            groups.append(cube(f"bypass_group_{group}_cell_{cell}",(cx+(cell-1)*.257,0,.90),
                               (.244,.88,.045),slate if group==1 else silicon_a))
        groups.append(pipe(f"bypass_group_bus_{group}",[(cx-.37,-.38,.93),(cx+.37,-.38,.93)],metal,.012))
    bypass=[(bx-.43,-.38,.94),(bx-.43,-.66,.94),(bx-.43,-.68,.60),
            (bx+.43,-.68,.60),(bx+.43,-.66,.94),(bx+.43,-.38,.94)]
    kit.put("pv_bypass",pipe("macro_bypass_wire",bypass,kit.colors["brass"],.023),
            cube("macro_bypass_diode",(bx,-.68,.60),(.26,.105,.098),kit.colors["dark"]),
            cube("macro_diode_band",(bx+.076,-.68,.60),(.031,.108,.10),kit.colors["white"]),
            module,*groups)
    kit.paths.update(pv_light=[(x-.60,-.73,2.01),(x-.29,-.65,1.20),(x-.14,-.665,.96)],
                     pv_carriers=[(x-.14,-.665,.96),(x+.59,-.666,1.12)],pv_bypass=bypass)
    kit.extra_flows={"pv_carriers": [([(x-.14,-.671,.96),(x-.64,-.674,.74)],(.97,.18,.21))]}
    kit.flow_colors={"pv_carriers":(.13,.78,1.0),"pv_bypass":(.96,.59,.09)}
    kit.cut_targets={"pv_cell","pv_light","pv_carriers","pv_bypass"}
    kit.shot_only={"pv_light","pv_carriers","pv_shade","pv_bypass"}
    for target in kit.cut_targets:
        kit.subjects[target]=(kit.groups["pv_cell"]+kit.groups[target]
                              if target in {"pv_light","pv_carriers"} else kit.groups[target])
    kit.subjects["pv_shade"]=kit.groups["panels"]
    kit.subjects["pv_junction"]=[o for o in kit.groups["pv_cell"] if "silicon" in o.name or "junction" in o.name]
    kit.subjects["bypass_diode"]=kit.groups["pv_bypass"][:3]
    kit.camera_directions.update(pv_junction=(1.5,-8,2.4),pv_bypass=(.7,-7,4),bypass_diode=(.4,-8,4))
    kit.camera_minimum.update(pv_junction=1.7,bypass_diode=2.1)
    kit.cut_targets.update({"pv_junction","bypass_diode"})
