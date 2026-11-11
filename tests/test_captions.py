from shortforge.director import template_storyboard
from shortforge.captions import cues,ass_time,escape_ass,write_captions


def test_captions_cover_all_beats(tmp_path):
    story=template_storyboard("water tower")
    chunks=cues(story)
    assert chunks[0]["start"] == 0
    assert chunks[-1]["end"] == 40
    assert all(chunk["start"] < chunk["end"] for chunk in chunks)
    assert all(abs(a["end"]-b["start"]) < .002 for a,b in zip(chunks,chunks[1:]))
    json_path,ass_path=write_captions(story,tmp_path)
    assert "Dialogue: 0" in ass_path.read_text()
    assert json_path.exists()


def test_ass_escapes_control_characters():
    assert escape_ass(r"hello {bad}\world") == "hello badworld"
    assert ass_time(40) == "0:00:40.00"


def test_reviewed_caption_timing_rejects_cross_beat_and_stale_words():
    import copy
    import pytest
    from shortforge.captions import checked_timing, cues
    from shortforge.topic_packs import build_story

    story=build_story("solar",120)
    timing=cues(story)
    assert checked_timing(story,timing)[0]["alignment"]=="external_review_timing"
    bad=copy.deepcopy(timing)
    bad[0]["end"]=story["beats"][0]["end"]+.1
    with pytest.raises(ValueError,match="Invalid caption timing"):
        checked_timing(story,bad)
    bad=copy.deepcopy(timing)
    bad[0]["text"]="Previously spoken words"
    with pytest.raises(ValueError,match="does not match"):
        checked_timing(story,bad)
