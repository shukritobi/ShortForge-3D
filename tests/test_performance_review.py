"""One-click review synchronization and narration timing quality tests."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest
from shortforge import audio
from shortforge.telemetry import Sampler


def load_review_module():
    file = Path(__file__).resolve().parents[1] / "scripts" / "one_click_review.py"
    spec = importlib.util.spec_from_file_location("one_click_review", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_telemetry_report_empty_samples(tmp_path):
    sampler = Sampler(tmp_path / "samples.jsonl")
    data = sampler.report()
    assert data["sample_count"] == 0
    assert data["metrics"]["gpu_util_pct"] is None
    assert data["patterns"][0]["kind"] == "gpu_telemetry_unavailable"


def test_telemetry_writes_timed_samples(tmp_path, monkeypatch):
    import shortforge.telemetry as t
    monkeypatch.setattr(t, "_gpu", lambda: {"gpu_util_pct": 25, "gpu_mem_used_mb": 500})
    monkeypatch.setattr(t, "_windows_memory", lambda: {"ram_used_pct": 50})
    monkeypatch.setattr(t, "_windows_cpu_ticks", lambda: None)
    sampler = Sampler(tmp_path / "system.jsonl")
    sampler.sample(stage="audio", force=True)
    assert json.loads((tmp_path / "system.jsonl").read_text())["gpu_util_pct"] == 25
    assert sampler.report()["metrics"]["gpu_util_pct"]["max"] == 25


def test_one_click_archives_old_latest(tmp_path):
    module = load_review_module()
    root = tmp_path / "drive"
    (root / "outbox" / "latest").mkdir(parents=True)
    (root / "outbox" / "latest" / "old.log").write_text("old", encoding="utf-8")
    run = tmp_path / "run-123"
    run.mkdir()
    (run / "run_manifest.json").write_text('{"status":"ready_for_review"}', encoding="utf-8")
    status = module.sync_bundle(run, root)
    assert status["status"] == "synced"
    assert (root / "outbox" / "latest" / "run_manifest.json").is_file()
    assert list((root / "outbox" / "archive").rglob("old.log"))


def test_beat_timing_report_survives_failure(monkeypatch, tmp_path):
    from shortforge.contract import load_storyboard
    story = load_storyboard(Path(__file__).resolve().parents[1] / "examples" / "water_tower_40s.json")
    monkeypatch.setattr(audio, "voice_python", lambda provider, override=None: "mock-python")
    monkeypatch.setattr(audio, "require_program", lambda binary: binary)
    monkeypatch.setattr(audio, "probe_duration", lambda p, ffprobe="ffprobe":
                        12.64 if "beat_02" in str(p) else 3.0)
    def fake_subprocess(command, *args, **kwargs):
        if command[0] == "mock-python":
            path = Path(command[command.index("--output") + 1])
            path.mkdir(parents=True, exist_ok=True)
            for i in range(8):
                (path / f"beat_{i:02d}_raw.wav").write_bytes(b"RIFF" * 120)
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(audio.subprocess, "run", fake_subprocess)
    with pytest.raises(RuntimeError, match="timing_report.json"):
        audio.create_audio(story, tmp_path / "audio")
    report = json.loads((tmp_path / "audio" / "timing_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "needs_review"
    assert report["beats"][2]["spoken_audio_sec"] == 12.64
    assert report["failed_count"] >= 1


def test_pc_agent_accepts_audio_task():
    from shortforge.pc_agent import validate_job
    assert validate_job({"version":1,"task":"audio","tts":"qwen"})["task"] == "audio"
