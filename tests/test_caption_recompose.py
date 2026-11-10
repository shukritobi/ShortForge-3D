"""Caption-only mode should not invoke Blender or Qwen."""
from pathlib import Path
import ast


def test_caption_only_script_is_valid_python():
    root=Path(__file__).resolve().parents[1]
    source=(root/"scripts"/"recompose_review.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "from shortforge.video import compose,inspect_video" in source
    assert "sync_bundle(folder,drive)" in source
    assert "create_audio(" not in source
    assert "render(" not in source


def test_caption_recompose_launcher_has_one_click_guards():
    root=Path(__file__).resolve().parents[1]
    data=(root/"scripts"/"ShortForge-Caption-Refresh.bat").read_text(encoding="utf-8")
    assert "git pull --ff-only" in data
    assert "-m pytest -q" in data
    assert "recompose_review.py" in data
    assert '\"%DRIVE%.\"' in data
