"""Guard missing source frames and avoid silently creating a partial video."""
import json
import pytest
from shortforge.director import template_storyboard
from shortforge import video
from shortforge.video import compose


def test_compose_rejects_incomplete_png_sequence(tmp_path):
    story = template_storyboard("water tower")
    frames = tmp_path / "frames"
    frames.mkdir()
    (frames/"frame_000001.png").write_bytes(b"placeholder")
    with pytest.raises(FileNotFoundError, match="missing 959 Blender frames"):
        compose(story,tmp_path)


def test_silent_recompose_ignores_old_beat_waveforms(tmp_path, monkeypatch):
    story={"fps":1,"duration":1,"beats":[]}
    frames=tmp_path/"frames"
    frames.mkdir()
    (frames/"frame_000001.png").touch()
    audio=tmp_path/"audio"
    (audio/"beats").mkdir(parents=True)
    (audio/"narration.wav").touch()
    (audio/"beats"/"beat_00.wav").touch()
    (audio/"voice_manifest.json").write_text(json.dumps({"provider":"none"}))
    monkeypatch.setattr(video,"validate_storyboard",lambda value: value)
    monkeypatch.setattr(video,"require_program",lambda value: value)
    monkeypatch.setattr(video.subprocess,"run",lambda *args, **kwargs: None)

    def write_captions(story, folder, *, audio_dir):
        assert audio_dir is None
        return folder/"captions.json", folder/"captions.ass"

    monkeypatch.setattr(video,"write_captions",write_captions)
    assert compose(story,tmp_path)==tmp_path/"draft.mp4"
