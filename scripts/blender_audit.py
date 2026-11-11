"""Real evaluated Blender contacts and six additional assembly viewpoints."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_v2 import configure_scene, animate, camera_pose, frame
from blender_assets_v2 import Kit
from shortforge.contract import load_storyboard
from shortforge.scene_math import ROOF_PITCH
import math


def audit(story_path,out):
    story=load_storyboard(story_path)
    out=out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    scene,cam=configure_scene(story)
    kit=Kit().build(story["scene_template"])
    bpy.context.view_layer.update()
    animate(story,kit,cam,scene)
    scene.frame_set(scene.frame_end)
    bpy.context.view_layer.update()
    checks={}
    if story["scene_template"]=="solar_home":
        normal=Vector((math.sin(ROOF_PITCH),0,math.cos(ROOF_PITCH)))
        roof=bpy.data.objects["sf_solar_main_roofR"]
        for col in range(2):
            for row in range(3):
                panel=bpy.data.objects[f"sf_pv_{col}_{row}"]
                for du in (-20,20):
                    rail=bpy.data.objects[f"sf_pv_mount_{col}_{row}_{du}"]
                    lower=(rail.location-roof.location).dot(normal)-(.17+.055)/2
                    upper=(panel.location-rail.location).dot(normal)-.055
                    checks[f"rail_{col}_{row}_{du}"]={"roof_gap_m":round(lower,6),
                        "panel_gap_m":round(upper,6),"passed":abs(lower)<.002 and abs(upper)<.002}
        meter=bpy.data.objects["sf_energy_meter"]
        checks["meter_wall"]={"passed":abs(meter.location.x-.08-1.5)<.001}
        def bounds(obj):
            points=[obj.matrix_world @ Vector(p) for p in obj.bound_box]
            return tuple(min(p[i] for p in points) for i in range(3)),tuple(max(p[i] for p in points) for i in range(3))
        lamp=bpy.data.objects["sf_porch_light_shade"]
        for other in (meter,bpy.data.objects["sf_panel_backbox"],bpy.data.objects["sf_inverter"]):
            a0,a1=bounds(lamp)
            b0,b1=bounds(other)
            intersects=all(min(a1[i],b1[i])-max(a0[i],b0[i])>.001 for i in range(3))
            checks["lamp_clear_of_"+other.name]={"passed":not intersects}
        for label,point in (("door",(-.735,-.265,1.1)),("window",(.645,-.265,1.575))):
            structural=[o for o in kit.groups["house"] if any(t in o.name for t in ("pier","header","apron"))]
            blocked=[]
            for obj in structural:
                low,high=bounds(obj)
                if all(low[i]+.001<point[i]<high[i]-.001 for i in range(3)):
                    blocked.append(obj.name)
            checks[label+"_true_wall_opening"]={"passed":not blocked,"wall_solids_in_opening":blocked}
    cam.animation_data_clear()
    centre=Vector((0,1,1.9))
    for i,offset in enumerate(((7,-10,6),(-7,-10,6),(7,10,6),(-7,10,6),(.1,-.1,12),(8,-5,2.5)),1):
        camera_pose(cam,centre+Vector(offset),centre,scene.frame_end)
        scene.render.filepath=str(out/f"audit_{i:02d}.png")
        bpy.ops.render.render(write_still=True)
    result={"blender":bpy.app.version_string,"topic":story["scene_template"],"checks":checks,
            "passed":all(c["passed"] for c in checks.values()),"views":6}
    (out/"geometry_audit.json").write_text(json.dumps(result,indent=2))
    if not result["passed"]:
        raise RuntimeError("Mechanical contact audit failed")


if __name__=="__main__":
    args=sys.argv[sys.argv.index("--")+1:]
    audit(Path(args[0]),Path(args[1]))
