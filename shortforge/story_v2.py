"""Phase 2 story contract for reusable, multi-topic 3D videos.

Version 1 stays untouched. Version 2 is intentionally explicit and allowlisted:
untrusted AI scripts cannot inject Python, assets, paths or Blender expressions.
"""
from __future__ import annotations
import math
import re
from .episode_story import EPISODES, TARGETS

DURATIONS = (60, 75, 90, 120, 180)
SCENE_TEMPLATES = {
    "rainwater": frozenset({"ground","house","gutter","downpipe","filter","diverter",
                           "inlet","tank","overflow","outlet","pump","garden"}),
    "water_distribution": frozenset({"neighbourhood", "pump", "tower", "tank", "main",
                                      "branch", "faucet", "reservoir", "ground"}),
    "solar_home": frozenset({"house", "sun", "panels", "inverter", "battery",
                            "meter", "grid", "lights", "ground", "distribution",
                            "pv_cell", "pv_light", "pv_carriers", "pv_shade", "pv_bypass"}),
    **{episode:frozenset(TARGETS) for episode in EPISODES},
}
CAMERAS = frozenset({"establish", "detail", "section", "follow", "overhead", "reveal"})
SHOT_SUBJECTS = {"solar_home": frozenset({"pv_contacts", "roof_rails", "pv_junction",
                                           "bypass_diode", "breaker_detail", "porch_fixture",
                                           "meter_detail", "battery_detail"})}
ACTION_TYPES = frozenset({"appear", "assemble", "highlight", "flow", "pulse", "cutaway",
                          "disappear","move","rotate","scale","explode","reassemble"})
BEAT_KEYS = frozenset({"id", "start", "end", "problem", "solution",
                       "narration", "camera", "actions"})
ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


class StoryV2Error(ValueError):
    pass


def total_frames(story: dict) -> int:
    return int(story["duration"] * story["fps"])


def validate_story_v2(story: dict) -> dict:
    if not isinstance(story, dict) or story.get("version") != 2:
        raise StoryV2Error("expected version 2 storyboard object")
    duration = story.get("duration")
    if type(duration) is not int or not 20 <= duration <= 3600:
        raise StoryV2Error("duration must be an integer from 20 to 3600 seconds")
    if type(story.get("fps")) is not int or story["fps"] not in (24,30):
        raise StoryV2Error("fps must be 24 or 30")
    if story.get("resolution") not in ([360,640],[720,1280],[1080,1920]):
        raise StoryV2Error("unsupported portrait resolution")
    policy=story.get("narration_timing", "legacy")
    if policy not in ("legacy", "native", "uniform"):
        raise StoryV2Error("narration_timing must be legacy, native or uniform")
    rate=story.get("narration_rate",1.0)
    if type(rate) not in (float,int) or not 1<=rate<=1.20 or (rate!=1 and policy!="uniform"):
        raise StoryV2Error("narration_rate must be 1.0–1.20 and use uniform timing above 1.0")
    scene = story.get("scene_template")
    if not isinstance(scene, str) or scene not in SCENE_TEMPLATES:
        raise StoryV2Error(f"scene_template must be registered: {sorted(SCENE_TEMPLATES)}")
    title = story.get("title")
    if not isinstance(title, str) or not (3 <= len(title.strip()) <= 180):
        raise StoryV2Error("invalid title")
    beats = story.get("beats")
    minimum=5 if scene in EPISODES else 8
    if not isinstance(beats, list) or not (minimum <= len(beats) <= 720):
        raise StoryV2Error(f"expected {minimum} to 720 beats")
    seen = set()
    cursor = 0.0
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict) or not BEAT_KEYS.issubset(beat):
            raise StoryV2Error(f"beat {index}: missing fields")
        key = beat["id"]
        if not isinstance(key, str) or not ID_RE.fullmatch(key) or key in seen:
            raise StoryV2Error(f"beat {index}: duplicate or unsafe ID")
        seen.add(key)
        start, end = beat["start"], beat["end"]
        if any(type(t) not in (float, int) or not math.isfinite(t) for t in (start, end)):
            raise StoryV2Error(f"beat {key}: invalid time")
        if abs(start-cursor) > 0.0001 or end-start < 2.5 or end > duration+.0001:
            raise StoryV2Error(f"beat {key}: non-contiguous or too short")
        cursor = end
        trim=beat.get("voice_trim_start",0)
        if type(trim) not in (float,int) or not 0<=trim<=2 or (trim and policy not in ("native","uniform")):
            raise StoryV2Error(f"beat {key}: invalid voice lead-in trim")
        if trim and not re.fullmatch(r"[a-f0-9]{64}",str(beat.get("voice_trim_sha256",""))):
            raise StoryV2Error(f"beat {key}: voice lead-in trim requires the reviewed WAV fingerprint")
        shots=beat.get("shot_cues",[])
        if not isinstance(shots,list) or len(shots)>5:
            raise StoryV2Error(f"beat {key}: invalid shot cues")
        previous=-1
        previous_frame=round(start*story["fps"])-1
        for shot in shots:
            if not isinstance(shot,dict) or set(shot)!={"at","target","camera"}:
                raise StoryV2Error(f"beat {key}: unsafe shot cue")
            at,target,view=shot["at"],shot["target"],shot["camera"]
            if (type(at) not in (int,float) or not 0<=at<=.9 or at<=previous or
                not isinstance(target,str) or target not in SCENE_TEMPLATES[scene]|SHOT_SUBJECTS.get(scene,frozenset()) or
                not isinstance(view,str) or view not in CAMERAS):
                raise StoryV2Error(f"beat {key}: invalid shot cue target, camera or position")
            cut_frame=round((start+at*(end-start))*story["fps"])
            if cut_frame<=previous_frame or (at and cut_frame==round(start*story["fps"])):
                raise StoryV2Error(f"beat {key}: shot cues must occupy separate frames")
            previous_frame=cut_frame
            previous=at
        callout=beat.get("callout")
        if callout is not None and (not isinstance(callout,str) or not callout.strip() or
                                    len(callout)>42 or any(ord(c)<32 for c in callout)):
            raise StoryV2Error(f"beat {key}: invalid callout")
        sounds=beat.get("sfx",[])
        if not isinstance(sounds,list) or len(sounds)>5:
            raise StoryV2Error(f"beat {key}: invalid SFX list")
        from .sfx import NAMES
        for cue in sounds:
            if (not isinstance(cue,dict) or set(cue)-{"name","offset","gain_db"} or
                not isinstance(cue.get("name"),str) or cue["name"] not in NAMES):
                raise StoryV2Error(f"beat {key}: unregistered sound")
            for field,default,lo,hi in (("offset",0,0,end-start),("gain_db",-30,-60,-18)):
                value=cue.get(field,default)
                if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:
                    raise StoryV2Error(f"beat {key}: invalid sound {field}")
        for field in ("problem", "solution", "narration"):
            value = beat[field]
            if not isinstance(value, str) or not value.strip() or len(value) > 700:
                raise StoryV2Error(f"beat {key}: invalid {field}")
        if len(beat["narration"].split()) > (end-start)*3.3:
            raise StoryV2Error(f"beat {key}: too many words for its timeline")
        if not isinstance(beat["camera"], str) or beat["camera"] not in CAMERAS:
            raise StoryV2Error(f"beat {key}: unknown camera")
        actions = beat["actions"]
        if not isinstance(actions, list) or not actions or len(actions) > 5:
            raise StoryV2Error(f"beat {key}: expected 1-5 actions")
        for a in actions:
            if not isinstance(a, dict) or not {"type","target"}.issubset(a) or set(a)-{"type","target","params"}:
                raise StoryV2Error(f"beat {key}: unsafe action fields")
            if (not isinstance(a["type"], str) or
                not isinstance(a["target"], str) or
                a["type"] not in ACTION_TYPES or
                a["target"] not in SCENE_TEMPLATES[scene]):
                raise StoryV2Error(f"beat {key}: unregistered action or target")
            params=a.get("params",{})
            if not isinstance(params,dict) or set(params)-{"vector","seconds","amount"}:
                raise StoryV2Error(f"beat {key}: unsafe action parameters")
            for field,value in params.items():
                values=value if field=="vector" else [value]
                if not isinstance(values,list) or (field=="vector" and len(values)!=3):
                    raise StoryV2Error(f"beat {key}: expected three-component vector")
                if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>100 for v in values):
                    raise StoryV2Error(f"beat {key}: invalid numeric action parameter")
            if "seconds" in params and not 0<params["seconds"]<=end-start:
                raise StoryV2Error(f"beat {key}: action duration outside beat")
            if a["type"] in ("move","rotate","scale") and "vector" not in params:
                raise StoryV2Error(f"beat {key}: transform needs vector")
            if a["type"]=="scale" and min(params["vector"])<=0:
                raise StoryV2Error(f"beat {key}: scale must be positive")
    if abs(cursor-duration) > 0.0001:
        raise StoryV2Error("last beat must end at video duration")
    return story
