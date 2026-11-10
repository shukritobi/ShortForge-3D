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
