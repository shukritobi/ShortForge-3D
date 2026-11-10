import copy
import json
import math
import struct
import wave
import zlib
from pathlib import Path
import pytest
from shortforge.topic_packs import build_story
from shortforge.story_v2 import validate_story_v2,StoryV2Error
from shortforge.render_cache import shot_keys,valid_png
from shortforge.camera_math import fit_distance
from shortforge.alignment import voiced_windows,aligned_cues


@pytest.mark.parametrize("duration",[40,57,90,120,137,180,240])
def test_arbitrary_timeline_and_extended_content(duration):
    s=build_story("solar",duration,fps=30,profile="final")
    assert validate_story_v2(s)==s
    assert s["beats"][-1]["end"]==duration
    assert s["resolution"]==[1080,1920]
    if duration>120:
        assert len(s["beats"])>24
        assert len(set(b["narration"] for b in s["beats"]))==len(s["beats"])


@pytest.mark.parametrize("duration",[40,90,120,180])
def test_third_topic_keeps_cutaway(duration):
    s=build_story("rainwater",duration)
    assert any(a["type"]=="cutaway" for b in s["beats"] for a in b["actions"])
    assert {a["target"] for b in s["beats"] for a in b["actions"]}<={
        "house","gutter","downpipe","filter","diverter","inlet","tank","overflow","outlet","pump","garden"}


def test_cache_narration_recompose_and_late_camera_edit():
    s=build_story("solar",120)
    original=shot_keys(s,"engine1")
    s["beats"][0]["narration"]="Changed voice script"
    assert shot_keys(s,"engine1")==original
    s["beats"][8]["camera"]="section"
    changed=shot_keys(s,"engine1")
    assert changed[:8]==original[:8]
    assert all(a!=b for a,b in zip(changed[8:],original[8:]))
    assert all(a!=b for a,b in zip(changed,shot_keys(s,"engine2")))


def png():
    def chunk(kind,data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data))
    return (b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,2,0,0,0))+
            chunk(b"IDAT",zlib.compress(b"\0\xff\0\0"))+chunk(b"IEND",b""))


def test_resume_rejects_truncated_or_wrong_size_frame(tmp_path):
    p=tmp_path/"frame.png"
    p.write_bytes(png())
    assert valid_png(p,(1,1))
    assert not valid_png(p,(720,1280))
    p.write_bytes(png()[:-10])
    assert not valid_png(p,(1,1))


def test_portrait_fit_projects_every_corner_inside_safe_area():
    points=[(x,y,z) for x in (-4,4) for y in (-2,2) for z in (-1,1)]
    d=fit_distance(points,.3,.6)
    assert all(abs(x)/(d-z)/.3<=.8200001 and abs(y)/(d-z)/.6<=.6600001 for x,y,z in points)


@pytest.mark.parametrize("params",[{"vector":[0,float("nan"),1]},{"vector":[0,1]},
                                   {"python":"bad"},{"seconds":999,"vector":[1,2,3]}])
def test_transform_parameters_reject_unsafe_values(params):
    s=build_story("solar",120)
    s["beats"][0]["actions"][0]={"type":"move","target":"house","params":params}
    with pytest.raises(StoryV2Error):validate_story_v2(s)


def test_waveform_captions_exclude_leading_and_trailing_silence(tmp_path):
    p=tmp_path/"beats"
    p.mkdir()
    samples=[0]*2400+[int(7000*math.sin(i*.1)) for i in range(12000)]+[0]*9600
    with wave.open(str(p/"beat_00.wav"),"wb") as w:
        w.setparams((1,2,24000,0,"NONE","not compressed"))
        w.writeframes(struct.pack("<"+"h"*len(samples),*samples))
    items=aligned_cues({"beats":[{"id":"a","start":0,"end":1,"narration":"One two three four five"}]},tmp_path)
    assert items[0]["start"]>=.1
    assert items[-1]["end"]<=.61
    assert items[0]["end"]<=items[1]["start"]


def test_measured_timing_redistributes_windows_without_changing_text():
    from shortforge.timing import retime_from_report
    s=build_story("solar",120)
    report={"beats":[{"beat":b["id"],"spoken_audio_sec":7 if i==0 else 3}
                     for i,b in enumerate(s["beats"])]}
    adjusted=retime_from_report(s,report)
    assert adjusted["beats"][0]["end"]>7
    assert adjusted["beats"][-1]["end"]==120
    assert [b["narration"] for b in adjusted["beats"]]==[b["narration"] for b in s["beats"]]
    for row in report["beats"]:row["spoken_audio_sec"]=20
    with pytest.raises(ValueError,match="rewriting"):retime_from_report(s,report)


def test_original_sfx_are_deterministic_and_quiet(tmp_path):
    from shortforge.sfx import effect,mix_effects,NAMES
    for name in NAMES:
        assert effect(name)==effect(name)
    s=build_story("solar",40)
    s["beats"][0]["sfx"]=[{"name":"electric","gain_db":-30}]
    validate_story_v2(s)
    path=mix_effects(s,tmp_path/"sfx.wav")
    with wave.open(str(path),"rb") as w:
        assert w.getnframes()==40*24000
        raw=w.readframes(w.getnframes())
    import array
    assert max(abs(v) for v in array.array("h",raw))<1200
