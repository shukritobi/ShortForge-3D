"""Registered, topic-independent Blender 4.5 renderer for ShortForge v2.

CLI entry: blender -b --python scripts/blender_v2.py -- --storyboard X --out Y
Only vetted scene templates and action types are accepted by story_v2.
Asset builders live in blender_assets_v2.py; this engine owns animations,
camera choreography, caching and deterministic frame output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shortforge.contract import load_storyboard
from shortforge.story_v2 import total_frames
from shortforge.camera_math import fit_distance
from shortforge.render_cache import renderer_sources, shot_keys, valid_png
from blender_assets_v2 import Kit, material, sphere
from blender_actions import transform_action


def frame(seconds, fps=24):
    return 1+int(round(seconds*fps))


def visibility(obj, start, end=None):
    """Objects cannot render before their first registered appearance."""
    show=max(1,start)
    if show>1:
        obj.hide_render=True
        obj.hide_viewport=True
        obj.keyframe_insert(data_path="hide_render",frame=1)
        obj.keyframe_insert(data_path="hide_viewport",frame=1)
        obj.keyframe_insert(data_path="hide_render",frame=show-1)
        obj.keyframe_insert(data_path="hide_viewport",frame=show-1)
    obj.hide_render=False
    obj.hide_viewport=False
    obj.keyframe_insert(data_path="hide_render",frame=show)
    obj.keyframe_insert(data_path="hide_viewport",frame=show)
    if end is not None:
        obj.keyframe_insert(data_path="hide_render",frame=end)
        obj.keyframe_insert(data_path="hide_viewport",frame=end)
        obj.hide_render=True
        obj.hide_viewport=True
        obj.keyframe_insert(data_path="hide_render",frame=end+1)
        obj.keyframe_insert(data_path="hide_viewport",frame=end+1)


def weighted_point(objects):
    if not objects:
        return Vector((0,0,2))
    # Bounding-box centers are more stable for grouped architecture than
    # object origins (pipe curves often have origin at the world's zero).
    pts=[]
    for obj in objects:
        if obj.type=="MESH":
            for corner in obj.bound_box:
                pts.append(obj.matrix_world @ Vector(corner))
        else:
            pts.append(obj.location.copy())
    if not pts:
        return Vector((0,0,2))
    return sum(pts,Vector())/len(pts)


def camera_pose(cam, position, focus, at):
    cam.location=position
    direction=Vector(focus)-Vector(position)
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    cam.keyframe_insert(data_path="location",frame=at)
    cam.keyframe_insert(data_path="rotation_euler",frame=at)


def set_camera_motion(scene, cam, kit, beat, previous_at, *, hard_cut=False):
    target=beat["actions"][0]["target"]
    # A focus target is an explicit subject, not an average of multiple
    # unrelated buildings or world-origin curve objects.
    anchor=(Vector(kit.focus[target]) if target in kit.focus else
            weighted_point(kit.groups.get(target, [])))
    modes={
        "establish":Vector((7,-15,8.5)),
        "detail":Vector((3.4,-7.5,4.1)),
        "section":Vector((4,-10,5.2)),
        "follow":Vector((5,-10,5.3)),
        "overhead":Vector((.7,-2.8,13)),
        "reveal":Vector((6.5,-13.5,8.2)),
    }
    mode=beat["camera"]
    offset=Vector(getattr(kit,"camera_directions",{}).get(target,modes[mode]))
    objects=kit.subjects.get(target,kit.groups.get(target,[]))
    if mode=="establish":
        objects=getattr(kit,"establish_subjects",{}).get(target,objects)
    if target in ("sun","lights","ground") and "house" in kit.subjects:
        objects=kit.subjects["house"]
    corners=[obj.matrix_world @ Vector(p) for obj in objects
             if obj.type in ("MESH","CURVE") for p in obj.bound_box]
    if corners:
        low=Vector(tuple(min(p[i] for p in corners) for i in range(3)))
        high=Vector(tuple(max(p[i] for p in corners) for i in range(3)))
        anchor=(low+high)*.5
        towards=offset.normalized()
        right=Vector((0,0,1)).cross(towards).normalized()
        up=towards.cross(right).normalized()
        relative=[p-anchor for p in corners]
        tan_y=cam.data.sensor_height/(2*cam.data.lens)
        tan_x=tan_y*scene.render.resolution_x/scene.render.resolution_y
        distance=fit_distance([(p.dot(right),p.dot(up),p.dot(towards)) for p in relative],tan_x,tan_y)
        minimum=getattr(kit,"camera_minimum",{}).get(target,3.8)
        offset=towards*max(distance,minimum)
    if target=="ground" and target not in kit.focus:
        anchor=Vector((0,-3,0))
    if mode=="section":
        anchor.z=max(anchor.z,0.1)
    start=frame(beat["start"],scene.render.fps)
    end=frame(beat["end"],scene.render.fps)-1
    arrive=min(end,start+max(8,int((end-start)*.35)))
    # Preserve the prior look-at on each shot's opening frame so the
    # rotation interpolates smoothly instead of snapping to a new target.
    previous_focus=getattr(kit,"last_camera_focus",None)
    cut_targets=getattr(kit,"cut_targets",set())
    cut = hard_cut or target in cut_targets or getattr(kit,"last_camera_target",None) in cut_targets
    if previous_focus is None:
        previous_focus=anchor
    camera_pose(cam,anchor+offset if cut else cam.location.copy(),anchor if cut else previous_focus,start)
    camera_pose(cam,anchor+offset,anchor,arrive)
    camera_pose(cam,anchor+offset+Vector((.25,0,.08)),anchor,end)
    kit.last_camera_focus=anchor.copy()
    kit.last_camera_target=target
    if cut:
        # Avoid interpolating across the empty space between the main set and
        # a magnified mechanism stage. The last key of the preceding shot holds.
        for curve in cam.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                if round(key.co.x)==start-1:
                    key.interpolation="CONSTANT"


def animate_appear(objects, at, fps, *, pulse=False, assemble=True):
    for obj in objects:
        # Avoid replaying construction when this same target is highlighted
        # again in later beats; only the first reveal performs assembly.
        if obj.get("sf2_is_visible"):
            if pulse:
                # Colour emphasis preserves physical contacts (scaling each
                # component separately detached rails and conduit terminals).
                if obj.data.materials:
                    if not obj.get("sf_highlight_material"):
                        obj.data.materials[0]=obj.data.materials[0].copy()
                        obj["sf_highlight_material"]=True
                    node=obj.data.materials[0].node_tree.nodes.get("Principled BSDF")
                    strength=node.inputs["Emission Strength"]
                    node.inputs["Emission Color"].default_value=(.1,.35,.6,1)
                    for f,value in ((at,0),(at+int(.3*fps),.35),(at+int(.7*fps),0)):
                        strength.default_value=value
                        strength.keyframe_insert(data_path="default_value",frame=f)
            continue
        obj["sf2_is_visible"]=True
        final=Vector(obj.scale)
        original=Vector(obj.location)
        visibility(obj,at)
        if at>1 and assemble:
            obj.scale=final*.08
            obj.location=original+Vector((0,0,-.45))
            obj.keyframe_insert(data_path="scale",frame=at)
            obj.keyframe_insert(data_path="location",frame=at)
            obj.scale=final
            obj.location=original
            obj.keyframe_insert(data_path="scale",frame=at+int(.55*fps))
            obj.keyframe_insert(data_path="location",frame=at+int(.55*fps))


def path_position(points, u):
    """Sample route using segment lengths for roughly uniform dot movement."""
    vec=[Vector(p) for p in points]
    lengths=[(b-a).length for a,b in zip(vec,vec[1:])]
    total=sum(lengths)
    if total<=0:
        return vec[0]
    d=min(max(u,0),1)*total
    for a,b,l in zip(vec,vec[1:],lengths):
        if d<=l:
            return a.lerp(b,d/max(l,1e-9))
        d-=l
    return vec[-1]


def flow_dots(kit, target, begin, end, route=None, color=None):
    route=route or kit.paths.get(target)
    if not route:
        return
    water=getattr(kit,"medium",None)=="water"
    color=color or getattr(kit,"flow_colors",{}).get(target) or ((.15,.79,.98) if water else (.99,.79,.16))
    if target in getattr(kit,"energy_flows",{}):
        energy_pulses(target,route,color,begin,end,kit.energy_flows[target])
        return
    mat=material("flow_"+"_".join(str(c) for c in color),color,emission=1.4)
    for i in range(5):
        dot=sphere(f"{target}_flow_{begin}_{i}",route[0],.065 if water else .045,mat)
        start=begin+i*4
        stop=max(start+2,end-1)
        visibility(dot,start,stop)
        for j in range(18):
            f=start+int((stop-start)*j/17)
            dot.location=path_position(route,j/17)
            dot.keyframe_insert(data_path="location",frame=f)


def energy_pulses(target, route, color, begin, end, radius):
    """Soft packets travel on the route with a small flicker and side-to-side drift."""
    fps=bpy.context.scene.render.fps
    span=max(1,end-begin)
    length=sum((Vector(b)-Vector(a)).length for a,b in zip(route,route[1:]))
    travel=min(span,max(round(1.1*fps),round(length/2.2*fps)))
    separation=max(round(.32*fps),travel//4)
    for start in range(begin,end-travel+1,separation):
        for trail in range(3):
            size=radius*(1-.22*trail)
            glow=material(f"charge_{color}_{trail}",color,emission=(4.2,2.9,2.0)[trail])
            bead=sphere(f"{target}_pulse_{start}_{trail}",route[0],size,glow)
            first=start+trail*2
            last=min(end,first+travel)
            visibility(bead,first,last)
            samples=sorted({first,last,*range(first,last,3)})
            for f in samples:
                u=(f-first)/travel
                point=path_position(route,u)
                tangent=path_position(route,min(1,u+.01))-path_position(route,max(0,u-.01))
                side=tangent.cross(Vector((0,0,1)))
                if side.length<.0001:
                    side=Vector((1,0,0))
                fade=min(1,(f-first+1)/4,(last-f+1)/4)
                phase=(f-first)*2*math.pi*2.5/fps
                bead.location=point+side.normalized()*(size*.18*math.sin(phase))
                bead.scale=(fade*(1+.11*math.sin(phase)),)*3
                bead.keyframe_insert(data_path="location",frame=f)
                bead.keyframe_insert(data_path="scale",frame=f)


def configure_scene(story):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.render.resolution_x=story["resolution"][0]
    scene.render.resolution_y=story["resolution"][1]
    scene.render.resolution_percentage=100
    scene.frame_start=1
    scene.frame_end=total_frames(story)
    scene.render.fps=story["fps"]
    scene.render.film_transparent=False
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.color_depth="8"
    scene.render.film_transparent=False
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value=(.46,.65,.85,1)
    bg.inputs["Strength"].default_value=.30
    scene.view_settings.view_transform="AgX"
    scene.view_settings.look="AgX - Medium High Contrast"
    bpy.ops.object.light_add(type="SUN",location=(0,0,10))
    sun=bpy.context.object
    sun.rotation_euler=(.45,-.5,-.4)
    sun.data.energy=2.0
    sun.data.angle=.12
    bpy.ops.object.light_add(type="AREA",location=(-6,-9,14))
    lamp=bpy.context.object
    lamp.name="sf2_sun_area"
    lamp.data.energy=2850
    lamp.data.shape="DISK"
    lamp.data.size=9
    lamp.rotation_euler=(Vector((0,0,0))-lamp.location).to_track_quat("-Z","Y").to_euler()
    if story["scene_template"]=="solar_home":
        from solar_neighbourhood import solar_lighting
        solar_lighting(scene,sun,lamp)
        scene.use_nodes=True
        nodes=scene.node_tree.nodes
        glare=nodes.new("CompositorNodeGlare")
        glare.glare_type="FOG_GLOW"
        glare.inputs["Threshold"].default_value=1.9
        glare.inputs["Strength"].default_value=.28
        glare.inputs["Size"].default_value=.18
        links=scene.node_tree.links
        links.new(nodes.get("Render Layers").outputs["Image"],glare.inputs["Image"])
        links.new(glare.outputs["Image"],nodes.get("Composite").inputs["Image"])
    bpy.ops.object.camera_add(location=(12,-25,15))
    cam=bpy.context.object
    cam.name="sf2_portrait_camera"
    cam.data.lens=26
    cam.data.sensor_fit="VERTICAL"
    cam.data.sensor_height=32
    scene.camera=cam
    camera_pose(cam,cam.location,Vector((0,0,2)),1)
    return scene,cam


def animate(story,kit,cam,scene):
    for name,objects in kit.groups.items():
        if name=="ground":
            for obj in objects:
                obj["sf2_is_visible"]=True
            continue
        for obj in objects:
            obj["sf2_is_visible"]=False
            obj.hide_render=True
            obj.hide_viewport=True
            obj.keyframe_insert(data_path="hide_render",frame=1)
            obj.keyframe_insert(data_path="hide_viewport",frame=1)
    for beat in story["beats"]:
        start=frame(beat["start"],story["fps"])
        end=frame(beat["end"],story["fps"])-1
        cues=beat.get("shot_cues",[])
        if not cues:
            set_camera_motion(scene,cam,kit,beat,start)
        else:
            length=beat["end"]-beat["start"]
            opening={"at":0,"target":beat["actions"][0]["target"],"camera":beat["camera"]}
            shots=cues if cues[0]["at"]==0 else [opening,*cues]
            for index,shot in enumerate(shots):
                until=shots[index+1]["at"] if index+1<len(shots) else 1
                segment={"start":beat["start"]+shot["at"]*length,
                         "end":beat["start"]+until*length,"camera":shot["camera"],
                         "actions":[{"target":shot["target"]}]}
                set_camera_motion(scene,cam,kit,segment,start,hard_cut=True)
        for action in beat["actions"]:
            typ,target=action["type"],action["target"]
            settle=not getattr(kit,"instant_reveal",False) or typ=="assemble"
            for dependency in kit.dependencies.get(target,[]):
                animate_appear(kit.groups[dependency],start,story["fps"],assemble=settle)
            objects=kit.groups[target]
            animate_appear(objects,start,story["fps"],
                           pulse=typ in ("pulse","highlight"),assemble=settle)
            transform_action(objects,action,start,end,story["fps"])
            if typ=="flow":
                flow_dots(kit,target,start,end)
                for route,color in getattr(kit,"extra_flows",{}).get(target,[]):
                    flow_dots(kit,target,start,end,route=route,color=color)
            animate_subject=getattr(kit,"beat_animations",{}).get(target)
            if animate_subject:
                animate_subject(start,end,story["fps"])
            if target in getattr(kit,"shot_only",set()):
                for obj in objects:
                    for at,hidden in ((start,False),(end+1,True)):
                        obj.hide_render=hidden
                        obj.keyframe_insert(data_path="hide_render",frame=at)
            if typ=="cutaway":
                # Open the previously capped excavation for a readable
                # underground cross-section. Only authorized cover objects
                # are affected; housing and structural assets stay intact.
                for cover in kit.cutaway_covers:
                    cover.hide_render=False
                    cover.hide_viewport=False
                    cover.keyframe_insert(data_path="hide_render",frame=max(1,start-1))
                    cover.keyframe_insert(data_path="hide_viewport",frame=max(1,start-1))
                    cover.hide_render=True
                    cover.hide_viewport=True
                    cover.keyframe_insert(data_path="hide_render",frame=start)
                    cover.keyframe_insert(data_path="hide_viewport",frame=start)
    scene.frame_set(1)


def fingerprint(story, *, scene_template=None):
    h=hashlib.sha256()
    h.update(json.dumps(story,sort_keys=True).encode("utf-8"))
    for path in renderer_sources(scene_template or story["scene_template"]):
        h.update((ROOT/path).read_bytes())
    h.update(bpy.app.version_string.encode("utf-8"))
    return h.hexdigest()


def emit_scene_manifest(scene,story,kit,output):
    data={
        "schema_version":2,"title":story["title"],"scene_template":story["scene_template"],
        "duration":story["duration"],"fps":story["fps"],
        "frame_count":total_frames(story),"resolution":story["resolution"],
        "assets":{k:len(v) for k,v in kit.groups.items()},
        "object_count":len(bpy.data.objects),"action_count":sum(len(b["actions"]) for b in story["beats"]),
        "camera_presets":list(dict.fromkeys(b["camera"] for b in story["beats"])),
        "renderer":"blender_v2","engine":scene.render.engine,
        "eevee_raytracing":scene.eevee.use_raytracing,"fingerprint":fingerprint(story),
        "asset_instances":[{"id":obj.name,"category":group,"units":"metres",
                            "version":"0.2.0","dimensions":list(obj.dimensions),
                            "dependencies":kit.dependencies.get(group,[])}
                           for group,objects in kit.groups.items() for obj in objects],
    }
    (output/"scene_manifest.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    return data


def render(story,out,preview_frames=None,start=None,end=None):
    scene,cam=configure_scene(story)
    kit=Kit().build(story["scene_template"])
    scene.frame_set(1)
    bpy.context.view_layer.update()
    animate(story,kit,cam,scene)
    manifest=emit_scene_manifest(scene,story,kit,out)
    if preview_frames is not None:
        for f in preview_frames:
            if not 1<=f<=scene.frame_end:
                raise ValueError(f"preview frame outside 1..{scene.frame_end}")
            scene.frame_set(f)
            scene.render.filepath=str(out/(f"preview_{f:04d}.png"))
            bpy.ops.render.render(write_still=True)
            print(f"SHORTFORGE_PREVIEW {f}/{scene.frame_end}",flush=True)
        if len(preview_frames)==1:
            # Legacy GUI assumes preview.png for a single-frame request.
            import shutil
            shutil.copy2(out/f"preview_{preview_frames[0]:04d}.png",out/"preview.png")
        return
    frames=out/"frames"
    frames.mkdir(parents=True,exist_ok=True)
    state=out/"render_state_v2.json"
    keys=shot_keys(story,fingerprint({},scene_template=story["scene_template"]))
    previous=json.loads(state.read_text(encoding="utf-8")) if state.is_file() else {}
    records=previous.get("verified_frames",{})
    meta={"fingerprint":manifest["fingerprint"],"frames":scene.frame_end,
          "scene_template":story["scene_template"],"verified_frames":records}
    def save_state():
        temp=state.with_suffix(".tmp")
        temp.write_text(json.dumps(meta)+"\n",encoding="utf-8")
        temp.replace(state)
    save_state()
    start=max(1,start or 1)
    end=min(scene.frame_end,end or scene.frame_end)
    for f in range(start,end+1):
        target=frames/f"frame_{f:06d}.png"
        index=next(i for i,b in enumerate(story["beats"]) if f<=frame(b["end"],story["fps"])-1)
        key=keys[index]
        if records.get(str(f))==key and valid_png(target,story["resolution"]):
            continue
        if target.exists():
            archive=out/"cache_archive"/str(time.time_ns())
            archive.mkdir(parents=True)
            target.replace(archive/target.name)
        scene.frame_set(f)
        scene.render.filepath=str(target)
        bpy.ops.render.render(write_still=True)
        if not valid_png(target,story["resolution"]):
            raise RuntimeError(f"Invalid rendered PNG: {target}")
        records[str(f)]=key
        save_state()
        if f%24==0 or f==end:
            print(f"SHORTFORGE_RENDER frame={f}/{scene.frame_end}",flush=True)


def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--storyboard",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    m=p.add_mutually_exclusive_group()
    m.add_argument("--preview-frame",type=int)
    m.add_argument("--preview-frames",type=str)
    p.add_argument("--start-frame",type=int)
    p.add_argument("--end-frame",type=int)
    args=p.parse_args(argv)
    story=load_storyboard(args.storyboard)
    if story["version"]!=2:
        raise ValueError("Blender v2 requires storyboard version 2")
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    frames=([args.preview_frame] if args.preview_frame is not None else
            [int(x) for x in args.preview_frames.split(",")] if args.preview_frames else None)
    render(story,out,preview_frames=frames,start=args.start_frame,end=args.end_frame)


if __name__=="__main__":
    main()
