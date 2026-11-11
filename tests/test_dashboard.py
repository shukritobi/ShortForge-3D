import json
from pathlib import Path
import pytest
from shortforge import dashboard as d


@pytest.fixture
def project(tmp_path,monkeypatch):
    monkeypatch.setattr(d,"PROJECTS",tmp_path)
    monkeypatch.setattr(d,"ACTIVE",None)
    ident=d.mutate({"action":"create","topic":"solar","duration":120})["id"]
    return ident,d.project_path(ident)


def test_full_render_requires_current_preview_approval(project):
    ident,p=project
    with pytest.raises(ValueError,match="Approve"):d.command_for(p,"full")
    with pytest.raises(ValueError,match="preview"):d.mutate({"action":"approve","id":ident})
    d.write_json(p/"preview_review.json",{"revision":d.revision(p)})
    d.mutate({"action":"approve","id":ident})
    with pytest.raises(ValueError,match="Check narration first"):
        d.command_for(p,"full")
    assert "run" in d.command_for(p,"full",tts="none")
    story=json.loads((p/"storyboard.json").read_text())
    story["beats"][0]["narration"]="A revised introduction."
    d.mutate({"action":"save","id":ident,"story":story})
    with pytest.raises(ValueError,match="Approve"):d.command_for(p,"full")
    assert list((p/"history").glob("*/storyboard.json"))


@pytest.mark.parametrize("ident",["../private","C:/secret","","x"*12,None])
def test_dashboard_rejects_paths(ident):
    with pytest.raises(ValueError):d.project_path(ident)


def test_active_job_blocks_edits_and_parallel_render(project,monkeypatch):
    ident,p=project
    monkeypatch.setattr(d,"ACTIVE",ident)
    with pytest.raises(ValueError,match="already active"):
        d.mutate({"action":"preview","id":ident})


def test_failed_job_releases_gpu_and_preserves_logs(project,monkeypatch):
    ident,p=project
    monkeypatch.setattr(d,"ACTIVE",ident)
    def fail(*args,**kwargs):raise OSError("missing executable")
    monkeypatch.setattr(d.subprocess,"Popen",fail)
    d.worker(p,"preview",["missing"])
    assert d.ACTIVE is None
    report=json.loads((p/"job.json").read_text())
    assert report["status"]=="failed"
    assert "missing executable" in report["error"]
    assert list((p/"history").glob("*/job.log"))


def test_windows_sharing_violation_retries_atomic_replace(tmp_path, monkeypatch):
    replace=Path.replace
    attempts=[]
    def sharing_violation_once(path, dest):
        attempts.append(path)
        if len(attempts)==1:
            raise PermissionError("destination temporarily open")
        return replace(path,dest)
    monkeypatch.setattr(Path,"replace",sharing_violation_once)
    path=tmp_path/"job.json"
    d.write_json(path,{"status":"passed"})
    assert d.read_json(path)=={"status":"passed"}
    assert len(attempts)==2


def test_success_exit_without_fresh_preview_cannot_be_approved(project, monkeypatch):
    ident,p=project
    (p/"contact_sheet.png").write_bytes(b"old preview")
    d.write_json(p/"preview_review.json",{"revision":d.revision(p)})
    d.mutate({"action":"approve","id":ident})
    class Finished:
        returncode=0
        def poll(self):return 0
    monkeypatch.setattr(d.subprocess,"Popen",lambda *args,**kwargs:Finished())
    d.worker(p,"preview",["mock"])
    assert d.read_json(p/"job.json")["status"]=="failed"
    with pytest.raises(ValueError,match="Approve"):d.command_for(p,"full")


def test_compose_receipt_ignores_audio_but_rejects_visual_changes(project):
    ident,p=project
    story=d.read_json(p/"storyboard.json")
    d.write_json(p/"rendered_visuals.json",d.visual_keys(story))
    story["voice"]="different"
    story["beats"][0].update(narration="Changed subtitle wording",callout="Sunlight",
                             sfx=[{"name":"electric","gain_db":-32}])
    d.mutate({"action":"save","id":ident,"story":story})
    assert "compose" in d.command_for(p,"compose")
    last=story["beats"][-1]
    last["camera"]="section" if last["camera"]!="section" else "overhead"
    d.mutate({"action":"save","id":ident,"story":story})
    with pytest.raises(ValueError,match="visual revision"):d.command_for(p,"compose")


def test_gpu_lock_prevents_another_process_slot(tmp_path, monkeypatch):
    from shortforge.studio_lock import studio_job_slot
    monkeypatch.setenv("SHORTFORGE_STUDIO_JOB_LOCK",str(tmp_path/"gpu.lock"))
    with studio_job_slot():
        with pytest.raises(RuntimeError,match="still running"),studio_job_slot():
            pytest.fail("second lock acquired")
    with studio_job_slot():
        pass
