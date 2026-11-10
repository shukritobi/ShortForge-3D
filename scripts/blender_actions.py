"""Allowlisted transform actions shared by every registered scene pack."""
from mathutils import Vector
import math


def transform_action(objects,action,start,end,fps):
    kind=action["type"]
    params=action.get("params",{})
    stop=min(end,start+round(params.get("seconds",1)*fps))
    if kind=="disappear":
        for obj in objects:
            obj.hide_render=False
            obj.keyframe_insert(data_path="hide_render",frame=max(1,start-1))
            obj.hide_render=True
            obj.keyframe_insert(data_path="hide_render",frame=start)
            obj["sf2_is_visible"]=False
        return
    if kind not in ("move","rotate","scale","explode","reassemble"):
        return
    centre=sum((o.location for o in objects),Vector())/max(1,len(objects))
    for obj in objects:
        prop="rotation_euler" if kind=="rotate" else "scale" if kind=="scale" else "location"
        initial=getattr(obj,prop).copy()
        obj.keyframe_insert(data_path=prop,frame=start)
        vector=Vector(params.get("vector",(0,0,0)))
        if kind=="rotate":
            value=Vector(initial)+vector*(math.pi/180)
        elif kind=="scale":
            value=Vector(tuple(initial[i]*vector[i] for i in range(3)))
        elif kind=="explode":
            obj["sf_assembly_origin"]=tuple(initial)
            direction=initial-centre
            value=initial+(direction.normalized() if direction.length else Vector((0,0,1)))*params.get("amount",.5)
        elif kind=="reassemble":
            value=Vector(obj.get("sf_assembly_origin",initial))
        else:
            value=initial+vector
        setattr(obj,prop,value)
        obj.keyframe_insert(data_path=prop,frame=stop)
