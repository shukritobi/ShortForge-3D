"""Long narration failures must preserve raw clips and timing diagnostics."""
from pathlib import Path
import importlib.util
import json
from shortforge.library import load_catalog


def load_runner():
    path=Path(__file__).resolve().parents[1]/"scripts"/"phase2_runner.py"
    spec=importlib.util.spec_from_file_location("phase2_runner_audio_test",path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_audio_samples_and_timing_preserved_on_failed_full(tmp_path):
    runner=load_runner()
    src=tmp_path/"output"
    (src/"audio"/"beats").mkdir(parents=True)
    (src/"audio"/"timing_report.json").write_text('{"status":"needs_review"}')
    (src/"audio"/"tts_metrics.jsonl").write_text('{"event":"beat_generated"}')
    (src/"audio"/"beats"/"beat_00_raw.wav").write_bytes(b"RIFF" * 100)
    story=tmp_path/"story.json"
    story.write_text("{}")
    target=tmp_path/"review"
    target.mkdir()
    runner.collect(target,src,story,[],full=False)
    assert (target/"timing_report.json").is_file()
    assert (target/"voice_samples"/"beat_00_raw.wav").is_file()


def test_asset_catalog_registers_both_mechanism_packs():
    entries=load_catalog()["entries"]
    ids={x["id"] for x in entries}
    assert "model.water_tower_v2" in ids
    assert "model.solar_array" in ids
    assert "action.flow_v2" in ids
