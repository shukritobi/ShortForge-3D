"""Guard missing source frames and avoid silently creating a partial video."""
import pytest
from shortforge.director import template_storyboard
from shortforge.video import compose


def test_compose_rejects_incomplete_png_sequence(tmp_path):
    story = template_storyboard("water tower")
    frames = tmp_path / "frames"
    frames.mkdir()
    (frames/"frame_000001.png").write_bytes(b"placeholder")
    with pytest.raises(FileNotFoundError, match="missing 959 Blender frames"):
        compose(story,tmp_path)
