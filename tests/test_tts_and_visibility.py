import ast
from pathlib import Path
import pytest
from shortforge.audio import voice_python, create_audio


def test_isolated_tts_missing_has_actionable_error(tmp_path, monkeypatch):
    from shortforge import audio
    monkeypatch.setattr(audio, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="TTS_SETUP"):
        voice_python("qwen")


def test_voice_provider_is_explicit():
    from shortforge.director import template_storyboard
    with pytest.raises(ValueError, match="qwen or kokoro"):
        create_audio(template_storyboard("water tower"), "output/x", provider="sapi")


def test_tts_worker_statically_parses():
    root=Path(__file__).resolve().parents[1]
    src=(root/"scripts"/"tts_generate.py").read_text(encoding="utf-8")
    ast.parse(src)
    assert "generate_custom_voice" in src
    assert "KPipeline" in src
    assert "System.Speech" not in src


def test_3d_visibility_keyframes_exist():
    root=Path(__file__).resolve().parents[1]
    src=(root/"scripts"/"blender_water_tower.py").read_text(encoding="utf-8")
    ast.parse(src)
    assert "def reveal_at(" in src
    assert 'data_path="hide_render"' in src
    assert 'data_path="hide_viewport"' in src
    assert "reveal_at(obj, t0)" in src
    assert "preview_frames_recommended" in src
    assert "720,936" in src
