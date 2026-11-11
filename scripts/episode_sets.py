"""Practical cutaway sets for the ten authored home-science episodes."""
import math
import random

import bpy
from mathutils import Vector

from blender_assets_v2 import cube, cylinder, material, pipe, sphere
from solar_neighbourhood import _area, detailed_house
from shortforge.episode_story import TARGETS


def finish(name, rgb, **options):
    return material("episode_"+name, rgb, **options)


class Set:
    def __init__(self, kit):
        self.kit = kit
        kit.instant_reveal = True
        kit.camera_directions = {}
        kit.camera_minimum = {}
        kit.shot_only = set(TARGETS)
        kit.cut_targets = set(TARGETS)
        kit.beat_animations = {}
        kit.extra_flows = {}
        kit.flow_colors = {}
        self.slate = finish("slate",(.052,.080,.123),roughness=.72)
        self.white = finish("ivory",(.78,.82,.78))
        self.ink = finish("ink",(.025,.060,.091),roughness=.63)
        self.steel = finish("steel",(.31,.40,.46),metallic=.45)
        self.teal = finish("teal",(.047,.36,.36),roughness=.48)
        self.blue = finish("water",(.038,.33,.67),roughness=.28)
        self.ice = finish("cool",(.17,.63,.87),emission=.24)
        self.orange = finish("warm",(.92,.31,.055),emission=.15)
        self.gold = finish("copper",(.70,.28,.058),metallic=.43)
        self.grass = finish("grass",(.13,.31,.075))
        self.soil = finish("soil",(.23,.112,.045))
        self.glass = finish("glass_edge",(.24,.56,.64),roughness=.28,metallic=.25)
        kit.colors.update(white=self.white,dark=self.ink,roof=self.slate,concrete=self.steel,
                          door=finish("door",(.31,.12,.044)),door_panel=finish("door_panel",(.47,.21,.09)),
                          brass=self.gold,glass=self.glass)
        kit.put("ground",cube("episode_floor",(0,1,-.145),(36,36,.19),self.slate))
        scene=bpy.context.scene
        _area(scene,"Episode broad key",(3,-6,7),(0,0,.8),670,5,(.91,.96,1))
        _area(scene,"Episode soft edge",(-4,4,5),(0,0,1),390,4,(1,.88,.72))

    def start(self, target, direction=(2,-10,4), minimum=2.8):
        self.target = target
        self.objects = []
        self.kit.camera_directions[target] = direction
        self.kit.camera_minimum[target] = minimum
        self.motions = []

    def close(self, subjects=None):
        self.kit.put(self.target,*self.objects)
        self.kit.subjects[self.target] = subjects or self.objects[:]
        if self.motions:
            motions=self.motions
            def play(start,end,fps):
                for apply in motions:
                    apply(start,end,fps)
            self.kit.beat_animations[self.target] = play

    def box(self,name,p,d,mat,**kwargs):
        obj=cube(name,p,d,mat,**kwargs)
        self.objects.append(obj)
        return obj

    def ball(self,name,p,r,mat,scale=(1,1,1)):
        obj=sphere(name,p,r,mat)
        obj.scale=scale
        self.objects.append(obj)
        return obj

    def cyl(self,name,p,r,d,mat):
        obj=cylinder(name,p,r,d,mat)
        self.objects.append(obj)
        return obj

    def line(self,name,points,mat,r=.025):
        obj=pipe(name,points,mat,r)
        self.objects.append(obj)
        return obj

    def label(self,text,p,size=.15,mat=None):
        font=bpy.data.curves.new(text,"FONT")
        font.body=text
        font.size=size
        font.align_x="CENTER"
        font.align_y="CENTER"
        font.materials.append(mat or self.white)
        obj=bpy.data.objects.new(text,font)
        bpy.context.collection.objects.link(obj)
        obj.location=p
        obj.rotation_euler=(math.pi/2,0,0)
        self.objects.append(obj)
        return obj

    def motion(self,obj,prop,values):
        def key(start,end,fps):
            for fraction,value in values:
                at=start+round((end-start)*fraction)
                setattr(obj,prop,value)
                obj.keyframe_insert(data_path=prop,frame=at)
        self.motions.append(key)

    def arrows(self,points,color=(.14,.77,1),*,guide=None):
        if guide:
            self.line("route_guide",points,guide,.014)
        if self.target in self.kit.paths:
            self.kit.extra_flows.setdefault(self.target,[]).append((points,color))
        else:
            self.kit.paths[self.target]=points
            self.kit.flow_colors[self.target]=color

    def house(self,name,x,y,scale=1,mat=None):
        parts=detailed_house(self.kit,name,x,y,mat or finish(name,(.62,.47,.33)))
        if scale!=1:
            centre=Vector((x,y,0))
            for obj in parts:
                obj.location=centre+(obj.location-centre)*scale
                obj.scale*=scale
        self.objects.extend(parts)
        return parts


def compost(s):
    scraps=[finish("carrot",(.75,.24,.055)),finish("greens",(.20,.35,.056)),
            finish("peels",(.53,.36,.075)),finish("leaves",(.36,.17,.052))]
    for index,target in enumerate(TARGETS):
        s.start(target,((1.6,-9,6.5),(.3,-11,4),(.65,-10,3),(-2,-9,3.2),(1.5,-9,6.7))[index])
        if index==4:
            for x in (-.89,.89):
                s.box("sample_tray",(x,0,.16),(1.56,1.08,.19),s.teal)
                if x<0:
                    s.ball("compact_clump",(x,0,.35),.43,s.soil,(1.26,.74,.53))
                rng=random.Random(400+(x>0))
                for j in range(38):
                    s.ball("sample_scrap",(x+rng.uniform(-.53,.53),rng.uniform(-.33,.33),
                                          rng.uniform(.46,.57) if x<0 else rng.uniform(.26,.39)),
                           rng.uniform(.035,.10),rng.choice(scraps),(.8,1.36,.53))
                s.label("COMPACT" if x<0 else "LOOSE",(x,-.56,.14),.13)
            s.close()
            continue
        for x in (-1.1,1.1):
            wet=x<0
            s.box("bin_base",(x,0,.16),(1.54,1.13,.29),s.ink)
            for dx in (-.73,.73):
                s.box("moulded_bin_side",(x+dx,0,1),(.11,1.12,1.5),s.teal)
            s.box("bin_back",(x,.52,1),(1.48,.11,1.5),s.teal)
            if index==0:
                s.box("bin_front",(x,-.52,.98),(1.49,.09,1.49),s.teal)
            for z in (.37,.65,.93,1.21,1.49):
                s.box("reinforcing_rib",(x,.461,z),(1.39,.035,.042),s.ink)
            lid=s.box("bin_lid",(x,0,1.78),(1.59,1.19,.12),s.teal)
            if index==0:
                def lift(a,b,fps,obj=lid,centre=x):
                    hinge=.54
                    for phase,angle in ((0,0),(.48,-1.22),(1,-1.22)):
                        obj.location=(centre,hinge-.54*math.cos(angle),1.78-.54*math.sin(angle))
                        obj.rotation_euler.x=angle
                        for prop in ("location","rotation_euler"):
                            obj.keyframe_insert(data_path=prop,frame=a+round((b-a)*phase))
                s.motions.append(lift)
            else:
                lid.location.y=.68
                lid.location.z=1.96
                lid.rotation_euler.x=-1.25
            rng=random.Random(106+index+(x>0))
            if wet:
                s.box("compacted_scrap_mat",(x,0,.69),(1.24,.86,.60),s.soil)
            for j in range(50 if wet else 93):
                px,py=rng.uniform(-.53,.53),rng.uniform(-.34,.37)
                mound=.92-.38*abs(px)-.34*abs(py)
                z=rng.uniform(.97,1.035) if wet else rng.uniform(.34,mound)
                obj=s.ball("vegetable_peel",(x+px,py,z),
                           rng.uniform(.05,.15),rng.choice(scraps),(.95,1.32,.32 if wet else .52))
                obj.rotation_euler.z=rng.uniform(0,math.tau)
            if not wet:
                for j in range(8):
                    cx,cy=x+rng.uniform(-.41,.41),rng.uniform(-.26,.27)
                    z=rng.uniform(.47,.72)
                    s.line("coarse_stalk",[(cx-.15,cy,z),(cx,cy+.07,z+.06),(cx+.17,cy+.11,z+.09)],
                           s.soil,.025)
            s.label("COMPACT" if wet else "LOOSE",(x,-.57,.16),.12)
        if index==2:
            for x in (1.1,-1.1):
                route=[(x,-.70,1.56),(x,-.58,1.36),(x+.24,-.59,1.12)]
                if x>0:
                    route.extend([(x-.25,-.59,.80),(x+.20,-.59,.47)])
                s.arrows(route,guide=s.ice)
        if index==3:
            s.line("thermometer_stem",[(1.09,-.56,.71),(1.09,-.56,1.78)],s.white,.044)
            red=s.line("temperature_column",[(1.09,-.62,.71),(1.09,-.62,1.73)],s.orange,.023)
            s.motion(red,"scale",[(0,(1,1,.65)),(.58,(1,1,1)),(1,(1,1,1))])
            s.label("ACTIVE CORE",(1.12,-.56,2.23),.12)
        if index==3:
            s.close([o for o in s.objects if o.location.x>.36])
        else:
            s.close()


def rotor(s,x,y,z,tower,rate):
    s.line("mast",[(x,y,tower),(x,y,z)],s.steel,.061)
    s.box("nacelle",(x,y,z),(.23,.38,.19),s.ink)
    spin=bpy.data.objects.new("Rotor assembly",None)
    bpy.context.collection.objects.link(spin)
    spin.location=(x,y-.22,z)
    bpy.context.view_layer.update()
    hub=s.ball("hub",(x,y-.25,z),.105,s.steel)
    parts=[hub]
    for i in range(3):
        angle=i*math.tau/3
        blade=s.box("tapered_rotor_blade",(x+.35*math.sin(angle),y-.25,z+.35*math.cos(angle)),
                    (.106,.038,.60),s.white,tilt=angle)
        parts.append(blade)
    for part in parts:
        part.parent=spin
        part.matrix_parent_inverse=spin.matrix_world.inverted()
    def turn(start,end,fps):
        for frame,value in ((start,0),(end,math.tau*rate*(end-start)/fps)):
            spin.rotation_euler.y=value
            spin.keyframe_insert(data_path="rotation_euler",frame=frame)
        for curve in spin.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation="LINEAR"
    s.motions.append(turn)


def wind(s):
    for i,target in enumerate(TARGETS):
        s.start(target,((1.7,-11,4.5),(1.6,-9,2.3),(-2.8,-9,4),(.25,-11,1.75),(3,-9,5.4))[i])
        if i==3:
            for x,label,color,values in ((-1.27,"ROOF",s.orange,(.45,.85,.31,.70,.24,.55)),
                                          (1.27,"CLEARER FLOW",s.ice,(.73,.76,.70,.81,.72,.78))):
                s.box("power_board",(x,0,1.22),(2.38,.14,2.35),s.ink)
                for row in range(3):
                    s.line("graph_grid",[(x-1.05,-.08,.72+row*.4),(x+1.05,-.08,.72+row*.4)],s.steel,.008)
                s.line("power_trace",[(x-1+num*.40,-.108,.70+height) for num,height in enumerate(values)],color,.024)
                s.label(label,(x,-.11,2.21),.15)
                s.label("POWER",(x,-.11,1.90),.12)
                bar=s.box("energy_total",(x,-.10,.38),(1.68 if x>0 else 1.05,.10,.16),color)
                s.motion(bar,"scale",[(0,(.07,1,1)),(1,(1,1,1))])
                s.label("ENERGY",(x,-.11,.13),.10)
        else:
            s.house("wind_house",-1.25,.25,.64)
            s.box("yard_model",(0,.24,.035),(5.2,3.1,.14),s.grass)
            rotor(s,-1.24,.21,3.12,2.35,1.48 if i%2 else 1.07)
            rotor(s,1.63,.51,3.34,.10,1.04)
            if i in (1,2,4):
                for z in (2.58,2.82,3.07):
                    s.arrows([(-2.5,-.6,z),(-1.6,-.6,z+.27),(-.73,-.55,z-.18),
                              (-.37,-.60,z+.12),(.13,-.58,z-.24)],guide=s.ice)
                s.arrows([(.51,-.32,3.39),(1.63,-.32,3.39),(2.62,-.32,3.39)],guide=s.ice)
        s.close()


def trap(s):
    bend=[(-.83,0,2.15),(-.83,0,.67)]
    bend.extend((-.515+.315*math.cos(angle),0,.67-.315*math.sin(angle))
                for angle in (math.pi*(1-j/16) for j in range(1,17)))
    bend.extend([(-.20,0,1.04),(-.16,0,1.15),(-.08,0,1.22),(.03,0,1.25),(1.64,0,1.25)])
    for i,target in enumerate(TARGETS):
        s.start(target,((2.3,-10,6),(.9,-10,2),(.38,-10,.85),(-1.1,-10,1.9),(.55,-10,2.9))[i])
        for x,width in ((-1.51,.78),(-.06,.78)):
            s.box("vanity_counter",(x,0,2.27),(width,.98,.15),s.white)
        for y in (-.415,.415):
            s.box("sink_counter_edge",(-.78,y,2.27),(.76,.15,.15),s.white)
        for j in range(7):
            ring=[(-.80+(.14+j*.039)*math.cos(k*math.tau/56),-.06+(.12+j*.034)*math.sin(k*math.tau/56),
                   2.12+j*.024) for k in range(57)]
            s.line("shaped_sink_bowl",ring,s.white,.024)
        s.cyl("drain_strainer",(-.80,-.06,2.11),.16,.033,s.steel)
        s.line("faucet",[(-.8,.35,2.35),(-.8,.35,2.71),(-.8,.04,2.71),(-.8,.04,2.59)],s.steel,.044)
        for x in (-1.87,.29):
            s.box("vanity_leg",(x,.25,1.07),(.08,.12,2.09),s.gold)
        s.line("clear_trap_outline",bend,s.glass,.138)
        opening=[(x,-.125,z) for x,_,z in bend]
        s.line("trap_cutaway_opening",opening,s.ink,.073)
        water=[(-.83,-.185,.64),(-.68,-.185,.40),(-.43,-.185,.37),(-.21,-.185,.54),(-.21,-.185,.70)]
        if i!=3:
            s.line("water_seal",water,s.blue,.074)
            for x in (-.83,-.21):
                s.ball("water_meniscus",(x,-.198,.66),.085,s.ice,(1,.5,.35))
        if i in (2,3,4):
            air=[(1.54,-.194,1.25),(.01,-.194,1.25),(-.20,-.194,1.02),(-.20,-.194,.75)]
            if i==3:
                air.extend([(-.23,-.194,.52),(-.49,-.194,.35),(-.75,-.194,.48),(-.83,-.194,1.85)])
            s.arrows(air,(.95,.57,.20))
        else:
            s.arrows([(-.8,-.19,2.55),(-.82,-.19,1.24),*water],guide=None)
        if i==0:
            s.close()
        else:
            # Frame the pipe, with the sink dropping to context in the lower-angle cutaways.
            subject=s.box("trap_camera_bounds",(.15,-.14,1.06),(3.1,.03,1.63),s.ink)
            s.objects.remove(subject)
            subject.hide_render=True
            s.close([subject])


def helix(cx,cy,z,r,loops,rise):
    return [(cx+r*math.cos(2*math.pi*loops*i/120),cy+r*math.sin(2*math.pi*loops*i/120),
             z+rise*i/120) for i in range(121)]


def heat_pump(s):
    for i,target in enumerate(TARGETS):
        s.start(target,((2,-10,4.1),(-1.4,-10,4.8),(2,-10,3),(.8,-10,2.7),(3,-10,4.4))[i])
        s.cyl("tank_base",(0,0,.12),.68,.20,s.ink)
        if i in (0,4):
            s.cyl("insulated_water_tank",(0,0,1.15),.63,2.03,s.white)
        else:
            s.cyl("tank_cutaway_water",(0,0,1.12),.56,1.87,s.blue)
            s.line("heat_exchanger",helix(0,0,.42,.59,5,1.33),s.gold,.035)
        s.cyl("top_housing",(0,0,2.44),.65,.36,s.ink)
        focus=[]
        for n in range(7):
            focus.append(s.box("exhaust_grille",(-.34+n*.113,-.585,2.41),(.038,.082,.116),s.steel))
        motor=s.cyl("compressor",(.24,-.33,2.80),.23,.31,s.steel)
        for n in range(8):
            s.box("evaporator_fin",(-.59+n*.075,-.15,2.66),(.023,.28,.31),s.steel)
        s.box("control_display",(-.24,-.60,2.52),(.34,.049,.08),s.teal)
        s.line("hot_copper_line",[(.24,-.38,2.92),(.82,-.39,2.91),(.82,-.39,1.52),(.49,-.40,1.52)],s.gold,.045)
        s.line("tank_outlet",[(.48,.19,2.15),(1.03,.18,2.15),(1.03,.18,2.78),(1.65,.18,2.78)],s.steel,.058)
        s.label("HEAT PUMP",(-.24,-.63,2.52),.069)
        s.arrows([(-1.82,-.47,2.42),(-1.10,-.66,2.42),(-.54,-.69,2.42)],guide=s.ice)
        if i>=2:
            s.arrows([(.25,-.46,2.92),(.87,-.47,2.91),(.87,-.47,1.52),(.54,-.45,1.52)],
                     (1,.40,.08),guide=s.orange)
        if i in (1,2):
            bounds=s.box("heat_pump_camera_bounds",(-.32,-.28,2.60),(2.66,.22,.97),s.ink)
            s.objects.remove(bounds)
            bounds.hide_render=True
            s.close([bounds,*focus,motor])
        else:
            s.close()


def rain_drops(s, count):
    rng=random.Random(51+count)
    for _ in range(count):
        x=rng.uniform(-2.85,2.85)
        y=rng.uniform(-1.61,.39)
        top=rng.uniform(2.25,3.48)
        bottom=.12 if y<-.5 else 1.87
        obj=s.line("rain_streak",[(x,y,top),(x+.022,y,top-.15)],s.ice,.007)
        phase=rng.uniform(0,.8)
        def fall(start,end,fps,drop=obj,h=top-bottom,phase=phase):
            period=round(fps*.64)
            for first in range(start-round(period*phase),end+1,period):
                for f,z in ((first,0),(first+period-1,-h)):
                    drop.location.z=z
                    drop.keyframe_insert(data_path="location",frame=f)
            for curve in drop.animation_data.action.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation="LINEAR"
        s.motions.append(fall)


def rain_garden(s):
    for i,target in enumerate(TARGETS):
        s.start(target,((1.8,-10,5),(2.4,-10,6.9),(1,-10,3),(-1.1,-10,4),(1.8,-10,5.2))[i])
        if i in (0,1,4):
            for x in (-1.5,1.5):
                s.house("rain_house",x,.53,.64)
                s.box("garden_plot",(x,.40,.025),(2.78,4.2,.15),s.grass)
                s.line("downspout",[(x+.85,-.03,1.91),(x+.99,-.03,1.91),
                                    (x+.99,-.03,.28),(x+.99,-.57,.20)],s.steel,.041)
                route=[(x+.99,-.12,1.90),(x+.99,-.12,.28),(x+.93,-.62,.16)]
                if x<0:
                    route.extend([(x+.72,-1.2,.14),(x+.59,-1.68,.13)])
                    s.box("curb_drain",(x+.56,-1.68,.11),(.49,.24,.08),s.ink)
                    for n in range(5):
                        s.box("grate",(x+.39+n*.084,-1.68,.158),(.029,.21,.018),s.steel)
                else:
                    route.extend([(x+.58,-.84,.15),(x+.28,-1.05,.15)])
                    pool=s.ball("rain_garden_pool",(x+.18,-1.17,.127),.54,s.blue,(1.12,.66,.07))
                    if i==4:
                        s.motion(pool,"scale",[(0,(1.12,.66,.07)),(1,(.36,.25,.03))])
                    for n in range(7):
                        angle=n*math.tau/7
                        cx=x+.18+.55*math.cos(angle)
                        cy=-1.17+.35*math.sin(angle)
                        s.line("rushes",[(cx,cy,.13),(cx+.06,cy,.33),(cx+.09,cy,.48)],s.grass,.023)
                s.arrows(route,guide=s.ice)
                s.label("STREET DRAIN" if x<0 else "RAIN GARDEN",(x,-1.84,.28),.14)
            subjects=s.objects[:]
            if i!=4:
                rain_drops(s,32 if i==0 else 23)
        else:
            s.box("soil_section",(0,0,.59),(4.2,1.25,1.15),s.soil)
            for j,z in enumerate((.24,.54,.87)):
                s.box("soil_strata",(0,-.639,z),(4.18,.038,.10),
                      finish(f"soil_band_{j}",(.30+j*.07,.157+j*.03,.077+j*.018)))
            s.box("turf_left",(-1.40,0,1.20),(1.42,1.26,.10),s.grass)
            s.box("turf_right",(1.40,0,1.20),(1.42,1.26,.10),s.grass)
            s.box("ponded_water",(0,0,1.16),(1.42,1.24,.09),s.blue)
            for x in (-.57,-.28,.28,.57):
                s.line("root_crown",[(x,.08,1.14),(x+.06,.07,1.45),(x-.025,.08,1.61)],s.grass,.037)
                s.line("root_section",[(x,-.655,1.12),(x-.06,-.653,.92),(x+.11,-.655,.70)],s.gold,.014)
                s.arrows([(x,-.68,1.18),(x+.045,-.68,.93),(x-.045,-.68,.61),(x+.04,-.68,.28)],
                         guide=s.ice)
            if i==3:
                s.line("overflow_channel",[(.48,0,1.24),(.79,0,1.24),(1.21,0,1.29),(2.11,0,1.29)],s.steel,.082)
                s.arrows([(.24,-.14,1.28),(.83,-.14,1.31),(1.29,-.14,1.38),(2.25,-.15,1.39)],guide=s.ice)
                s.label("OVERFLOW",(1.45,-.64,1.55),.13)
        s.close(subjects if i in (0,1,4) else None)


def induction(s):
    for i,target in enumerate(TARGETS):
        s.start(target,((2.3,-8,6.2),(1.7,-10,4.1),(-1.6,-10,4.7),(.6,-9,7),(3,-9,5))[i])
        for x in ((-1.13,1.13) if i==3 else (0,)):
            s.box("cooktop_body",(x,0,.27),(2.03,1.71,.37),s.ink)
            glass=s.box("ceramic_surface",(x,0,.477),(1.98,1.66,.052),s.ink)
            height=1.24 if i in (1,2) else .56
            back=.39 if i in (1,2) else 0
            if i in (1,2):
                glass.location=(x,.31,.83)
                for radius in (.19,.27,.35,.43,.52,.61):
                    s.line("inductor_winding",helix(x,-.17,.49,radius,1,0),s.gold,.025)
            pan=s.cyl("pan_base",(x,back,height),.64,.105,s.steel if x<=0 else s.gold)
            s.line("pan_rim",helix(x,back,height+.13,.613,1,0),s.ink,.049)
            s.cyl("water_surface",(x,back,height+.08),.59,.055,s.blue)
            handle=s.line("pan_handle",[(x+.54,back+.07,height+.055),(x+.85,back+.12,height+.15),(x+1.06,back+.13,height+.15)],s.ink,.078)
            if i in (0,2,3,4) and x<=0:
                for j in range(13):
                    angle=j*2.39996
                    r=.05+.037*j
                    bx,by=x+r*math.cos(angle),back+r*math.sin(angle)
                    bubble=s.ball("boiling_bubble",(bx,by,height+.115),.036,s.ice)
                    if i!=4:
                        s.motion(bubble,"location",[(0,(bx,by,height+.11)),(.52,(bx,by,height+.17)),(1,(bx,by,height+.12))])
            if i==3:
                s.label("COMPATIBLE" if x<0 else "OTHER BASE",(x,-.88,.51),.13)
            if i in (1,2):
                for dx in (-.42,0,.42):
                    s.arrows([(x+dx,-.48,.56),(x+dx,-.39,.82),(x+dx,-.23,1.21)],(1,.39,.08),guide=s.orange)
            if i==4:
                for obj in (pan,handle,*[part for part in s.objects if "pan_rim" in part.name or "water_surface" in part.name or "boiling_bubble" in part.name]):
                    pos=obj.location.copy()
                    s.motion(obj,"location",[(0,pos),(.44,pos+Vector((.66,0,.34))),(1,pos+Vector((.95,.05,.37)))])
                for radius in (.31,.43,.53):
                    s.line("residual_warmth",helix(x,0,.51,radius,1,0),s.orange,.021)
        s.close()


def window_frame(s,x,y,z,coated):
    for dx in (-.81,.81):
        s.box("jamb",(x+dx,y,z),(.105,.22,1.82),s.white)
    for dz in (-.87,.87):
        s.box("window_head_sill",(x,y,z+dz),(1.72,.22,.105),s.white)
    for depth in (-.065,.065):
        for dx in (-.73,.73):
            s.box("glazing_edge",(x+dx,y+depth,z),(.034,.025,1.59),s.glass)
        for dz in (-.79,.79):
            s.box("glass_spacer",(x,y+depth,z+dz),(1.47,.025,.034),s.steel)
    s.box("inner_pane",(x,y+.055,z),(1.45,.019,1.57),s.glass if coated else s.steel)
    s.box("centre_mullion",(x,y-.075,z),(.055,.09,1.61),s.white)
    s.box("window_transom",(x,y-.075,z),(1.5,.09,.055),s.white)


def low_e(s):
    for i,target in enumerate(TARGETS):
        s.start(target,((2,-10,3.1),(1,-10,2.8),(5.8,-10,3.6),(-2,-10,4.2),(1,-10,3.2))[i])
        if i==2:
            for n,y in enumerate((-.63,0,.63)):
                s.box("separated_glazing",(0,y,1.24),(2.02,.065,1.71),s.glass if n!=1 else s.teal)
                for z in (.37,2.11):
                    s.box("pane_edge",(0,y,z),(2.1,.081,.055),s.steel)
            s.label("LOW-E SURFACE",(0,-.75,2.37),.17)
            for x in (-.58,0,.58):
                s.arrows([(x,-1.10,.85),(x,-.72,1.18),(x,-.93,1.47)],(1,.40,.09),guide=s.orange)
        else:
            for x in (-1.10,1.10):
                window_frame(s,x,0,1.36,x>0)
                if i>=1:
                    for j in range(3):
                        z=.93+j*.29
                        if x>0 and i==1:
                            route=[(x-.52,-.40,z),(x-.26,-.20,z),(x+.21,-.40,z+.10)]
                        elif i==3 and x>0:
                            route=[(x-.52,-.40,z+.25),(x-.21,-.19,z),(x+.20,-.39,z+.18)]
                        else:
                            route=[(x-.56,-.37,z),(x,-.28,z+.12),(x+.56,-.17,z+.24)]
                        s.arrows(route,(1,.71,.22) if i==3 else (1,.44,.10),
                                 guide=s.gold if i==3 else s.orange)
                if i==4:
                    s.label("U-FACTOR" if x<0 else "SOLAR HEAT GAIN",(x,-.20,.27),.15)
        s.close()


def ventilation(s):
    for i,target in enumerate(TARGETS):
        s.start(target,((1.4,-11,3.25),(-1.6,-10,3.0),(1.8,-10,2.5),(-2.3,-10,3.7),(.4,-11,3.0))[i])
        s.box("foundation",(0,0,.07),(4.40,2.22,.12),s.steel)
        s.box("back_wall",(0,1.04,1.62),(4.28,.18,3.12),s.white)
        s.box("middle_floor",(-.60,0,1.55),(3.03,2.17,.14),s.steel)
        for x in (-2.10,2.10):
            for z in (.36,1.50,2.08,3.06):
                s.box("vent_wall_section",(x,0,z),(.15,2.16,.54),s.white)
        for x,sign in ((-.99,-1),(.99,1)):
            s.box("sloping_roof",(x,0,3.50),(2.39,2.28,.14),s.slate,tilt=sign*.36)
        for n in range(9):
            h=.16*(n+1)
            s.box("stair_tread",(-.07+n*.19,.47,h/2),(.21,.68,h),s.gold)
        for x,z,shade in ((-2.12,.89,s.ice),(2.12,2.55,s.orange)):
            s.line("window_opening",[(x,-1.10,z-.30),(x,-1.10,z+.30)],shade,.032)
        route=[(-2.53,-.43,.88),(-1.93,-.48,.88),(-.95,-.48,.91),(.18,-.46,1.08),
               (1.17,-.48,1.28),(1.42,-.48,2.35),(2.12,-.45,2.55),(2.56,-.45,2.55)]
        if i==0:
            pane=s.box("upstairs_window_sash",(2.12,-.25,2.55),(.075,.79,.57),s.glass)
            s.motion(pane,"location",[(0,(2.12,-.25,2.55)),(.7,(2.12,-.25,3.11)),(1,(2.12,-.25,3.11))])
        if i!=0:
            if i==1:
                route=route[3:]
            elif i==3:
                route=[(2.60,-.50,2.55),(1.94,-.47,2.55),(1.32,-.47,2.39),
                       (1.20,-.49,1.24),(-.43,-.49,1.07),(-2.51,-.46,.89)]
            s.arrows(route,guide=s.ice)
        if i==1 or i==2:
            s.label("COOLER OUTSIDE",(-1.1,-1.10,.23),.125)
            s.label("WARM AIR RISES",(1.06,-1.10,2.98),.125)
        s.close()


def siphon(s):
    for i,target in enumerate(TARGETS):
        s.start(target,((1,-10,3.2),(1.6,-10,2.8),(-1.8,-10,3.4),(.15,-10,2.4),(1,-10,3.2))[i])
        for x,level in ((-1.28,1.38),(1.27,.47)):
            s.box("vessel_base",(x,0,.11),(1.46,1.13,.17),s.glass)
            s.box("vessel_back",(x,.54,.82),(1.45,.09,1.52),s.glass)
            for dx in (-.69,.69):
                s.box("vessel_end",(x+dx,0,.82),(.07,1.15,1.52),s.glass)
            s.box("vessel_water",(x,0,(.2+level)/2),(1.31,1.04,level-.2),s.blue)
        crest=[(-1.34,-.11,.72),(-1.34,-.11,1.96),(-1.14,-.11,2.35),
               (-.83,-.11,2.51),(-.12,-.11,2.51),(.25,-.11,2.35),(.49,-.11,1.87)]
        outlet=(.88,-.11,.65)
        tube=[*crest,outlet]
        outer=s.line("clear_tube_outer",tube,s.glass,.075)
        column=s.line("water_column",[(x,y-.049,z) for x,y,z in tube],s.blue,.040)
        if i!=3:
            s.arrows([(x,y-.089,z) for x,y,z in tube])
        if i in (1,2,3):
            s.line("source_level",[(-1.90,-.62,1.38),(1.77,-.62,1.38)],s.white,.012)
            s.label("SOURCE LEVEL",(-1.24,-.64,1.53),.12)
            if i!=3:
                s.line("outlet_level",[(.51,-.62,.65),(1.81,-.62,.65)],s.ice,.012)
            mark=s.label("OUTLET",(.95,-.65,outlet[2]+.14),.12)
            if i==3:
                def lift(start,end,fps):
                    for phase,z in ((0,.65),(.36,1.38),(.70,1.38),(1,.65)):
                        frame=start+round((end-start)*phase)
                        for obj in (outer,column):
                            point=obj.data.splines[0].points[-1]
                            point.co.z=z
                            point.keyframe_insert(data_path="co",frame=frame)
                        mark.location.z=z+.14
                        mark.keyframe_insert(data_path="location",frame=frame)
                s.motions.append(lift)
        s.close()


def cool_roof(s):
    pale=finish("reflective_roof",(.64,.67,.65),roughness=.77)
    for i,target in enumerate(TARGETS):
        s.start(target,((1.5,-10,4.3),(2.3,-10,6.2),(-2.2,-10,5.5),(.7,-10,3.0),(1.5,-10,4.3))[i])
        for x in (-1.48,1.48):
            if i==3:
                s.box("room_floor",(x,0,.12),(2.55,1.78,.17),s.steel)
                s.box("room_back",(x,.84,1.01),(2.54,.12,1.82),s.white)
                for side in (-1,1):
                    s.box("rafter_roof",(x+side*.67,0,2.57),(1.56,1.80,.15),s.slate,tilt=side*.43)
                s.box("ceiling",(x,0,1.85),(2.47,1.76,.10),s.white)
                if x>0:
                    for n in range(6):
                        s.box("insulation_batt",(x-.95+n*.38,0,1.99),(.34,1.65,.19),s.orange)
                s.label("INSULATED" if x>0 else "ATTIC",(x,-.95,1.49),.17)
                s.arrows([(x-.29,-.90,2.61),(x-.29,-.90,2.2),(x-.29,-.90,1.76 if x<0 else 1.99)],
                         (1,.34,.09),guide=s.orange)
            else:
                parts=s.house("roof_home",x,0,.73)
                for obj in parts:
                    if obj.name.removeprefix("sf_roof_home").split(".",1)[0] in {"_roofL","_roofR","_ridge"}:
                        if i in (0,4):
                            obj.data.materials[0]=s.orange if x<0 else s.ice
                        elif x>0:
                            obj.data.materials[0]=pale
                if i in (1,2):
                    for j in range(3):
                        z=2.4+j*.13
                        if i==1:
                            route=[(x-.8+j*.28,-.5,z+.66),(x-.5+j*.24,-.49,z)]
                            if x>0:
                                route.append((x-.22+j*.28,-.50,z+.58))
                        else:
                            route=[(x-.51+j*.27,-.51,z),(x-.45+j*.31,-.47,z+.53)]
                        s.arrows(route,(1,.49,.13),guide=s.orange)
                if i==4:
                    for title,z,value in (("ROOF SURFACE",3.02,.84 if x<0 else .48),
                                          ("ROOM",.30,.54 if x<0 else .47)):
                        s.box("temperature_card",(x,-1.14,z),(1.37,.045,.35),s.ink)
                        s.label(title,(x,-1.17,z+.07),.10)
                        s.box("relative_temperature",(x-.53+value*.56,-1.17,z-.073),(value*1.12,.045,.055),
                              s.orange if x<0 else s.ice)
        s.close()


BUILDERS = {
    "episode_compost": compost, "episode_wind": wind, "episode_trap": trap,
    "episode_heat_pump": heat_pump, "episode_rain_garden": rain_garden,
    "episode_induction": induction, "episode_low_e": low_e,
    "episode_ventilation": ventilation, "episode_siphon": siphon, "episode_cool_roof": cool_roof,
}


def build_episode(kit, scene_template):
    BUILDERS[scene_template](Set(kit))
