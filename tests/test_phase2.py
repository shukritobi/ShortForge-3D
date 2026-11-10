"""Phase 2 multi-topic long-form production contract regression tests."""
from __future__ import annotations
import ast
import copy
import importlib.util
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest
from shortforge.contract import load_storyboard, validate_storyboard
from shortforge.story_v2 import DURATIONS, StoryV2Error, total_frames
from shortforge.topic_packs import build_story
from shortforge.scene_validation import validate_scene_manifest
from shortforge.captions import cues, write_captions

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("topic", ["water tower","solar home"])
@pytest.mark.parametrize("duration", DURATIONS)
def test_registered_topics_generate_length_profile(topic,duration):
    s=build_story(topic,duration)
    assert validate_storyboard(s) is s
    assert total_frames(s)==duration*24
    assert s["beats"][0]["start"]==0
    assert s["beats"][-1]["end"]==duration
    assert len(s["beats"])>=10


@pytest.mark.parametrize("filename,seconds",[
    ("water_tower_90s_v2.json",90),
    ("solar_home_120s_v2.json",120),
    ("solar_home_180s_v2.json",180)])
def test_real_example_storyboards(filename,seconds):
    s=load_storyboard(ROOT/"examples"/filename)
    assert s["duration"]==seconds
    assert s["version"]==2
    assert all(b["actions"][0]["target"] for b in s["beats"])


def test_unregistered_topic_is_not_faked():
    with pytest.raises(ValueError,match="No scene pack"):
        build_story("How a rocket lands on Mars",120)


def test_injection_and_bad_timing_rejected():
    s=build_story("solar",90)
    s["beats"][0]["actions"][0]["python"]="__import__('os').system('whoami')"
    with pytest.raises(StoryV2Error,match="unsafe action"):
        validate_storyboard(s)
    s=build_story("solar",90)
    s["beats"][0]["actions"]=[{"type":"exec","target":"house"}]
    with pytest.raises(StoryV2Error,match="unregistered"):
        validate_storyboard(s)
    s=build_story("solar",90)
    s["beats"][3]["start"]+=.5
    with pytest.raises(StoryV2Error,match="contiguous"):
        validate_storyboard(s)


def test_legacy_40_second_story_unchanged():
    s=load_storyboard(ROOT/"examples"/"water_tower_40s.json")
    assert s["version"]==1 and s["duration"]==40


def test_captions_support_three_minutes(tmp_path):
    s=build_story("solar",180)
    assert cues(s)[-1]["end"]==180
    _,path=write_captions(s,tmp_path)
    assert "0:03:00.00" in path.read_text(encoding="utf-8")


def test_v2_manifest_checks_target_counts(tmp_path):
    s=build_story("solar",120)
    targets={a["target"] for beat in s["beats"] for a in beat["actions"]}
    data={"schema_version":2,"scene_template":"solar_home","duration":120,
          "fps":24,"resolution":[720,1280],"frame_count":2880,
          "object_count":90,"action_count":24,"assets":{k:1 for k in targets}}
    p=tmp_path/"manifest.json"
    p.write_text(json.dumps(data),encoding="utf-8")
    assert validate_scene_manifest(p,story=s)==data
    data["assets"][next(iter(targets))]=0
    p.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError,match="Missing scene asset"):
        validate_scene_manifest(p,story=s)


def test_phase2_blender_sources_compile_without_bpy():
    for name in ("blender_assets_v2.py","blender_v2.py","phase2_runner.py"):
        ast.parse((ROOT/"scripts"/name).read_text(encoding="utf-8"))


def test_preview_frames_match_length():
    p=ROOT/"scripts"/"phase2_runner.py"
    spec=importlib.util.spec_from_file_location("phase2_unit",p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.preview_frames(180))==6
    assert max(mod.preview_frames(180))<=4320
    assert mod.preview_frames(90)!=mod.preview_frames(180)


def test_silent_audio_uses_requested_duration(monkeypatch,tmp_path):
    from shortforge import audio
    calls=[]
    monkeypatch.setattr(audio,"require_program",lambda x:x)
    monkeypatch.setattr(audio.subprocess,"run",lambda cmd,**kw:(calls.append(cmd),CompletedProcess(cmd,0))[1])
    audio.create_silent_audio(tmp_path,duration=120)
    assert calls[0][calls[0].index("-t")+1]=="120"


def test_inspect_video_accepts_expected_duration(monkeypatch,tmp_path):
    from shortforge import video
    data={"streams":[{"codec_type":"video","width":720,"height":1280,"avg_frame_rate":"24/1"},
                     {"codec_type":"audio"}],"format":{"duration":"120.0"}}
    monkeypatch.setattr(video,"require_program",lambda x:x)
    monkeypatch.setattr(video.subprocess,"run",lambda *a,**kw:
                        CompletedProcess(a,0,stdout=json.dumps(data)))
    assert video.inspect_video(tmp_path/"draft.mp4",expected_duration=120)["duration_ok"]
    with pytest.raises(RuntimeError,match="output QA failed"):
        video.inspect_video(tmp_path/"draft.mp4",expected_duration=40)
