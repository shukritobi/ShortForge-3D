import copy
import hashlib
import json
import subprocess

import pytest

from shortforge import audio
from shortforge.render_cache import shot_keys
from shortforge.story_v2 import StoryV2Error, validate_story_v2
from shortforge.topic_packs import build_story
from shortforge.timing import retime_from_report


def test_native_timing_extends_instead_of_speeding_up():
    story=build_story("solar",120)
    report={"beats":[{"beat":b["id"],"spoken_audio_sec":11} for b in story["beats"]]}
    with pytest.raises(ValueError,match="Shorten lines or extend"):
        retime_from_report(story,report)
    adjusted=retime_from_report(story,report,extend=True)
    assert adjusted["duration"]>120
    assert all(b["end"]-b["start"]>=11.2 for b in adjusted["beats"])
    assert [b["narration"] for b in adjusted["beats"]]==[b["narration"] for b in story["beats"]]


def test_native_audio_never_uses_atempo(tmp_path,monkeypatch):
    story=build_story("solar",120)
    beats=tmp_path/"beats"
    beats.mkdir()
    for i in range(len(story["beats"])):
        (beats/f"beat_{i:02d}_raw.wav").write_bytes(b"x"*200)
    monkeypatch.setattr(audio,"voice_python",lambda *a:"python")
    monkeypatch.setattr(audio,"require_program",lambda name:name)
    monkeypatch.setattr(audio,"probe_duration",lambda path,*a:120 if path.name=="narration.wav" else 6)
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd,0)
    monkeypatch.setattr(audio.subprocess,"run",run)
    audio.create_audio(story,tmp_path)
    filters=[cmd[cmd.index("-af")+1] for cmd in calls if "-af" in cmd]
    assert len(filters)==len(story["beats"])
    assert all("atempo" not in f for f in filters)
    report=json.loads((tmp_path/"timing_report.json").read_text())
    assert all(b["speed_adjustment"]==1 for b in report["beats"])


def test_script_has_mechanism_details_and_macro_targets():
    story=build_story("solar",120)
    lines=" ".join(b["narration"] for b in story["beats"])
    assert all(word in lines for word in ("electron","hole","junction","bypass","voltage","isolate"))
    targets={a["target"] for b in story["beats"] for a in b["actions"]}
    assert {"pv_cell","pv_light","pv_carriers","pv_bypass","distribution"}<=targets


def test_uniform_pace_only_trims_the_reviewed_take(tmp_path,monkeypatch):
    story=build_story("solar",120)
    story.update(narration_timing="uniform",narration_rate=1.07)
    pcm=b"x"*200
    fingerprint=hashlib.sha256(pcm).hexdigest()
    for beat in story["beats"][:2]:
        beat.update(voice_trim_start=1.11,voice_trim_sha256=fingerprint)
    beats=tmp_path/"beats"
    beats.mkdir()
    for i in range(len(story["beats"])):
        (beats/f"beat_{i:02d}_raw.wav").write_bytes(pcm if i==0 else b"y"*200)
    monkeypatch.setattr(audio,"voice_python",lambda *a:"python")
    monkeypatch.setattr(audio,"require_program",lambda name:name)
    monkeypatch.setattr(audio,"probe_duration",lambda path,*a:120 if path.name=="narration.wav" else 9)
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd,0)
    monkeypatch.setattr(audio.subprocess,"run",run)
    audio.create_audio(story,tmp_path)
    filters=[cmd[cmd.index("-af")+1] for cmd in calls if "-af" in cmd]
    assert all(f.count("atempo=1.070000")==1 for f in filters)
    assert "atrim=start=1.110000" in filters[0]
    assert all("atrim=start=" not in f for f in filters[1:])
    report=json.loads((tmp_path/"timing_report.json").read_text())
    assert [b["reviewed_trim_matched"] for b in report["beats"][:2]]==[True,False]
    measured=retime_from_report(story,report)
    first,second=measured["beats"][:2]
    assert (second["end"]-second["start"])-(first["end"]-first["start"])==pytest.approx(1.11/1.07,abs=1e-4)


def test_shot_cues_are_allowlisted_and_invalidate_cached_frames():
    story=build_story("solar",120)
    changed=copy.deepcopy(story)
    changed["beats"][9]["shot_cues"][1]["at"]=.65
    validate_story_v2(changed)
    original_keys=shot_keys(story,"renderer")
    changed_keys=shot_keys(changed,"renderer")
    assert original_keys[:9]==changed_keys[:9]
    assert original_keys[9:]!=changed_keys[9:]
    changed["beats"][9]["shot_cues"][1]["target"]="unknown_asset"
    with pytest.raises(StoryV2Error,match="invalid shot cue"):
        validate_story_v2(changed)
    changed["beats"][9]["shot_cues"][1].update(at=.0001,target="porch_fixture")
    with pytest.raises(StoryV2Error,match="separate frames"):
        validate_story_v2(changed)
