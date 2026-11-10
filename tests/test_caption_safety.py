from shortforge.director import template_storyboard
from shortforge.captions import cues, safe_ass_caption, write_captions
from pathlib import Path
import pytest


def test_long_caption_wraps_within_two_lines():
    line=safe_ass_caption("pushing water through underground")
    assert r"\N" in line
    assert all(len(x) <= 22 for x in line.split(r"\N"))


def test_caption_rejects_unfittable_phrase():
    with pytest.raises(ValueError,match="too long"):
        safe_ass_caption("supercalifragilisticexpialidocious")


def test_reference_story_all_cues_fit_portrait(tmp_path):
    path=Path(__file__).resolve().parents[1] / "examples" / "water_tower_40s.json"
    from shortforge.contract import load_storyboard
    story=load_storyboard(path)
    cues_list=cues(story)
    assert len(cues_list)>20
    for cue in cues_list:
        text=safe_ass_caption(cue["text"])
        assert len(text.split(r"\N")) <= 2
    _,ass=write_captions(story,tmp_path)
    data=ass.read_text(encoding="utf-8")
    assert "WrapStyle: 0" in data
    assert "Arial,48" in data
    assert r"\N" in data
    assert "MarginV" in data
