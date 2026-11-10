"""Narration pacing and cache-only model skip regression tests."""
from __future__ import annotations
import importlib.util
from pathlib import Path
from shortforge.contract import load_storyboard


def tts_worker():
    p=Path(__file__).resolve().parents[1]/"scripts"/"tts_generate.py"
    spec=importlib.util.spec_from_file_location("shortforge_tts_cache_perf", p)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reference_narration_has_a_spoken_time_budget():
    story=load_storyboard(Path(__file__).resolve().parents[1]/
                          "examples"/"water_tower_40s.json")
    assert 65 <= sum(len(b["narration"].split()) for b in story["beats"]) <= 85
    for b in story["beats"]:
        words=len(b["narration"].split())
        assert words <= 2.5 * (b["end"] - b["start"]), f"Beat {b['id']} too dense"


def test_qwen_cache_only_mode_skips_loading_model(tmp_path,monkeypatch):
    module=tts_worker()
    story={"beats":[{"id":"01","narration":"Hello."}]}
    monkeypatch.setattr(module,"sample_saved",lambda *args,**kwargs: True)
    calls=[]
    monkeypatch.setattr(module,"log_metric",lambda *args,**kwargs:calls.append(kwargs))
    # This test environment does not need PyTorch or qwen_tts because the
    # pure cache-only branch should return before either is imported.
    module.render_qwen(story,tmp_path,"Qwen/demo","Ryan")
    assert calls[0]["event"] == "all_beats_cached"
    assert calls[1]["event"] == "beat_cached"
