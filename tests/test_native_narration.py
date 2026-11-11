import copy
import json
import subprocess

import pytest

from shortforge import audio
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
