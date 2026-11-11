"""Regression tests for Phase 2's successful Blender render / failed CLI audit."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from shortforge import cli
from shortforge.topic_packs import build_story


ROOT=Path(__file__).resolve().parents[1]


def runner_module():
    path=ROOT/"scripts"/"phase2_runner.py"
    spec=importlib.util.spec_from_file_location("phase2_recovery_regressions",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_v2_scene_audit_has_no_legacy_structural_counts(monkeypatch,tmp_path,capsys):
    storyboard=tmp_path/"story.json"
    storyboard.write_text(json.dumps(build_story("solar",120)),encoding="utf-8")
    monkeypatch.setattr(cli,"find_blender",lambda explicit:"blender.exe")
    calls=[]
    monkeypatch.setattr(cli.subprocess,"run",lambda command,**kwargs:calls.append(command))
    monkeypatch.setattr(cli,"validate_scene_manifest",lambda *args,**kwargs:{
        "scene_template":"solar_home","assets":{"house":5,"panels":6},
        "object_count":93,"frame_count":2880
    })
    monkeypatch.setattr(cli,"_contact_sheet",lambda *args:calls.append("contact_sheet"))
    cli.render(storyboard,tmp_path,preview_frames=[411,823,1234,1646,2057,2469])
    assert "Phase 2 scene audit passed" in capsys.readouterr().out
    assert "contact_sheet" in calls
    assert "blender_v2.py" in " ".join(map(str,calls[0]))


def test_cli_v1_still_reports_structural_counts(monkeypatch,tmp_path,capsys):
    storyboard=ROOT/"examples"/"water_tower_40s.json"
    monkeypatch.setattr(cli,"find_blender",lambda explicit:"blender.exe")
    monkeypatch.setattr(cli.subprocess,"run",lambda *args,**kwargs:None)
    monkeypatch.setattr(cli,"validate_scene_manifest",lambda *args,**kwargs:{
        "structural_counts":{"support_legs":4}
    })
    cli.render(storyboard,tmp_path,preview_frame=120)
    assert "Phase 1 scene audit passed" in capsys.readouterr().out


def test_recover_six_existing_images_without_blender(tmp_path,monkeypatch):
    mod=runner_module()
    story=build_story("solar",120)
    project=tmp_path/"project"
    project.mkdir()
    (project/"storyboard.json").write_text(json.dumps(story),encoding="utf-8")
    all_targets={a["target"] for beat in story["beats"] for a in beat["actions"]}
    manifest={
        "schema_version":2,"scene_template":"solar_home",
        "duration":120,"fps":24,"resolution":[720,1280],
        "frame_count":2880,"object_count":99,
        "action_count":len(story["beats"]),
        "assets":{k:1 for k in all_targets},
        "fingerprint":"f"*64
    }
    (project/"scene_manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    nums=mod.preview_frames(120)
    for n in nums:
        (project/f"preview_{n:04d}.png").write_bytes(b"PNG"+b"x"*120)
    assert mod.verify_existing_preview(project,story,nums)==manifest
    # No Blender or narration should be invoked during recovery.
    monkeypatch.setattr(mod,"OUTPUT",tmp_path/"out")
    monkeypatch.setattr(mod,"_contact_sheet",
                        lambda project,nums:(project/"contact_sheet.png").write_bytes(b"PNG"+b"x"*120))
    monkeypatch.setattr(mod,"latest_git_sha",lambda:"previous-new-sha")
    copied=[]
    monkeypatch.setattr(mod,"sync_bundle",lambda folder,drive:
                        (copied.append(folder),{"status":"synced"})[1])
    assert mod.recover_preview("solar",120,drive=None,project=project)==0
    run=copied[0]
    assert (run/"contact_sheet.png").is_file()
    assert all((run/f"preview_{n:04d}.png").is_file() for n in nums)
    record=json.loads((run/"run_manifest.json").read_text(encoding="utf-8"))
    assert record["status"]=="ready_for_visual_review"
    assert record["blender_rerendered"] is False
    assert record["tts_ran"] is False


def test_recover_refuses_missing_frame(tmp_path):
    mod=runner_module()
    story=build_story("solar",120)
    project=tmp_path
    (project/"scene_manifest.json").write_text(json.dumps({
        "schema_version":2,"scene_template":"solar_home",
        "duration":120,"fps":24,"resolution":[720,1280],
        "frame_count":2880,"object_count":99,
        "action_count":len(story["beats"]),
        "assets":{a["target"]:1 for b in story["beats"] for a in b["actions"]},
        "fingerprint":"f"*64
    }),encoding="utf-8")
    with pytest.raises(FileNotFoundError,match="images missing"):
        mod.verify_existing_preview(project,story,mod.preview_frames(120))
