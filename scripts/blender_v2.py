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
from blender_assets_v2 import Kit, material, sphere


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


def set_camera_motion(scene, cam, kit, beat, previous_at):
    target=beat["actions"][0]["target"]
    anchor=weighted_point(kit.groups.get(target, []))
    modes={
        "establish":Vector((11,-24,13)),
        "detail":Vector((4,-9,5)),
        "section":Vector((4,-17,7)),
        "follow":Vector((9,-13,5.5)),
        "overhead":Vector((.3,-3,23)),
        "reveal":Vector((12,-30,16)),
    }
    mode=beat["camera"]
    offset=modes[mode]
    if target=="ground":
        anchor=Vector((0,-3,0))
    if mode=="section":
        anchor.z=max(anchor.z,0.1)
    start=frame(beat["start"])
    end=frame(beat["end"])-1
    arrive=min(end,start+max(8,int((end-start)*.35)))
    camera_pose(cam,cam.location.copy(),anchor,start)
    camera_pose(cam,anchor+offset,anchor,arrive)
    camera_pose(cam,anchor+offset+Vector((.35,0,.15)),anchor,end)


def animate_appear(objects, at, fps, *, pulse=False):
    for obj in objects:
        # Avoid replaying construction when this same target is highlighted
        # again in later beats; only the first reveal performs assembly.
        if obj.get("sf2_is_visible"):
            if pulse:
                base=Vector(obj.scale)
                at_mid=at+max(5,int(.24*fps))
                obj.scale=base
                obj.keyframe_insert(data_path="scale",frame=at)
                obj.scale=base*1.05
                obj.keyframe_insert(data_path="scale",frame=at_mid)
                obj.scale=base
                obj.keyframe_insert(data_path="scale",frame=at_mid+max(6,int(.25*fps)))
            continue
        obj["sf2_is_visible"]=True
        final=Vector(obj.scale)
        original=Vector(obj.location)
        visibility(obj,at)
        if at>1:
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


def flow_dots(kit, target, begin, end):
    route=kit.paths.get(target)
    if not route:
        return
    mat=material("flow_blue" if target in ("main","branch","faucet","tank")
                 else "flow_yellow",(.15,.79,.98) if target in ("main","branch","faucet","tank")
                 else (.99,.79,.16),emission=1.4)
    for i in range(5):
        dot=sphere(f"{target}_flow_{begin}_{i}",route[0],.135,mat)
        start=begin+i*4
        stop=max(start+2,end-1)
        visibility(dot,start,stop)
        for j in range(18):
            f=start+int((stop-start)*j/17)
            dot.location=path_position(route,j/17)
            dot.keyframe_insert(data_path="location",frame=f)


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
    scene.render.film_transparent=False
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.color_depth="8"
    scene.render.film_transparent=False
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value=(.51,.66,.8,1)
    bg.inputs["Strength"].default_value=.75
    scene.view_settings.view_transform="AgX"
    bpy.ops.object.light_add(type="AREA",location=(-6,-9,14))
    lamp=bpy.context.object
    lamp.name="sf2_sun_area"
    lamp.data.energy=2600
    lamp.data.shape="DISK"
    lamp.data.size=14
    lamp.rotation_euler=(Vector((0,0,0))-lamp.location).to_track_quat("-Z","Y").to_euler()
    bpy.ops.object.camera_add(location=(12,-25,15))
    cam=bpy.context.object
    cam.name="sf2_portrait_camera"
    cam.data.lens=30
    scene.camera=cam
    camera_pose(cam,cam.location,Vector((0,0,2)),1)
    return scene,cam


def animate(story,kit,cam,scene):
    for name,objects in kit.groups.items():
        if name=="ground":
            continue
        for obj in objects:
            obj["sf2_is_visible"]=False
            obj.hide_render=True
            obj.hide_viewport=True
            obj.keyframe_insert(data_path="hide_render",frame=1)
            obj.keyframe_insert(data_path="hide_viewport",frame=1)
    for beat in story["beats"]:
        start=frame(beat["start"])
        end=frame(beat["end"])-1
        set_camera_motion(scene,cam,kit,beat,start)
        for action in beat["actions"]:
            typ,target=action["type"],action["target"]
            objects=kit.groups[target]
            animate_appear(objects,start,story["fps"],
                           pulse=typ in ("pulse","highlight"))
            if typ=="flow":
                flow_dots(kit,target,start,end)
            if typ=="cutaway":
                # Section camera makes the cross-section/pipe interface visible.
                # Terrain remains undistorted; full mesh booleans are not needed.
                pass
    scene.frame_set(1)


def fingerprint(story):
    h=hashlib.sha256()
    h.update(json.dumps(story,sort_keys=True).encode("utf-8"))
    for path in (Path(__file__),ROOT/"scripts"/"blender_assets_v2.py"):
        h.update(path.read_bytes())
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
        "renderer":"blender_v2","fingerprint":fingerprint(story),
    }
    (output/"scene_manifest.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    return data


def render(story,out,preview_frames=None,start=None,end=None):
    scene,cam=configure_scene(story)
    kit=Kit().build(story["scene_template"])
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
    meta={"fingerprint":manifest["fingerprint"],"frames":scene.frame_end,
          "scene_template":story["scene_template"]}
    if state.is_file():
        previous=json.loads(state.read_text(encoding="utf-8"))
        if previous != meta:
            raise RuntimeError("Render cache contains a different scene or script; choose a fresh --out folder")
    elif list(frames.glob("frame_*.png")):
        raise RuntimeError("Untracked frames found; refuse unsafe stale-frame reuse. Choose a fresh --out")
    state.write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    start=max(1,start or 1)
    end=min(scene.frame_end,end or scene.frame_end)
    for f in range(start,end+1):
        target=frames/f"frame_{f:06d}.png"
        if target.is_file() and target.stat().st_size>100:
            continue
        scene.frame_set(f)
        scene.render.filepath=str(target)
        bpy.ops.render.render(write_still=True)
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
