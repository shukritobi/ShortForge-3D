import json
from pathlib import Path

import pytest
from shortforge import pc_agent


def test_explicit_blender_path(tmp_path):
    fake = tmp_path / "blender.exe"
    fake.write_text("stub", encoding="utf-8")
    assert Path(pc_agent.find_blender(str(fake))) == fake.resolve()


def test_job_manifest_allowlist():
    job = json.loads((pc_agent.ROOT / "jobs" / "preview.json").read_text(encoding="utf-8"))
    assert pc_agent.validate_job(job)["task"] == "preview"


@pytest.mark.parametrize("job", [
    {"version":1, "task":"shell", "command":"powershell"},
    {"version":1, "task":"preview", "out":"../outside"},
    {"version":1, "task":"preview", "storyboard":"../../outside.json"},
    {"version":1, "task":"preview", "preview_frame":-1},
    {"version":1, "task":"preview", "powershell":"echo bad"},
])
def test_reject_unknown_or_outside_tasks(job):
    with pytest.raises(ValueError):
        pc_agent.validate_job(job)


def test_missing_blender_writes_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setattr(pc_agent, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(pc_agent, "find_blender", lambda arg=None: None)
    monkeypatch.setattr(pc_agent, "probe", lambda *a, **k: {"ok": False})
    summary, folder = pc_agent.run_task("doctor", out=str(tmp_path / "output" / "water_tower"))
    assert summary["status"] == "needs_setup"
    assert (folder / "doctor.json").is_file()
    assert (folder / "events.jsonl").is_file()
    assert (folder / "summary.json").is_file()


def test_preview_missing_blender_does_not_spawn(tmp_path, monkeypatch):
    monkeypatch.setattr(pc_agent, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(pc_agent, "find_blender", lambda arg=None: None)
    summary, _ = pc_agent.run_task("preview", out=str(tmp_path / "output" / "water_tower"))
    assert summary["status"] == "failed"
    assert summary["error"].startswith("Blender not ready")
