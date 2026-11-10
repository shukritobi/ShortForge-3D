"""Recovery works without rerunning expensive Blender or narration stages."""
import importlib.util
import json
from pathlib import Path


def review_module():
    path=Path(__file__).resolve().parents[1]/"scripts"/"one_click_review.py"
    spec=importlib.util.spec_from_file_location("review_sync_recovery",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_drive_path_stray_quote_recovers(tmp_path):
    mod=review_module()
    drive=tmp_path/"ChatGPT ShortForge 3D"
    (drive/"outbox").mkdir(parents=True)
    actual,checked=mod.resolve_drive('"' + str(drive) + '/"')
    assert actual == drive.resolve()
    assert checked


def test_recover_latest_without_rerender(tmp_path):
    mod=review_module()
    root=tmp_path/"output"
    run=root/"review_runs"/"20261110T063157-f0bfeb"
    run.mkdir(parents=True)
    (run/"run_manifest.json").write_text(json.dumps({"status":"needs_review"}))
    (run/"timing_report.json").write_text(json.dumps({"failed_count":1}))
    drive=tmp_path/"Drive"/"ChatGPT ShortForge 3D"
    (drive/"outbox"/"latest").mkdir(parents=True)
    synced=mod.sync_latest_run(str(drive)+'/',output_root=root)
    assert synced["status"] == "synced"
    assert (drive/"outbox"/"latest"/"run_manifest.json").exists()
    assert (drive/"outbox"/"latest"/"timing_report.json").exists()


def test_recovery_rejects_outside_local_run(tmp_path):
    mod=review_module()
    result=mod.sync_latest_run(None, run_id="../outside",output_root=tmp_path)
    assert result["status"]=="failed"


def test_missing_drive_is_explicit_error(tmp_path):
    mod=review_module()
    run=tmp_path/"review"
    run.mkdir()
    (run/"run_manifest.json").write_text("{}")
    result=mod.sync_bundle(run,tmp_path/"missing")
    assert result["status"]=="sync_failed"
    assert result["local_run"] == str(run)
