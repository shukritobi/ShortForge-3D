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
    assert "run" in d.command_for(p,"full")
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
