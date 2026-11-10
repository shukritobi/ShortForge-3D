"""Export quality regressions for local FFmpeg composition."""
from pathlib import Path


def test_encoder_target_preserves_more_detail_and_normalizes_voice():
    root=Path(__file__).resolve().parents[1]
    source=(root/"shortforge"/"video.py").read_text(encoding="utf-8")
    assert '"-preset","medium","-crf","18"' in source
    assert "loudnorm=I=-16:TP=-1.5:LRA=9[aud]" in source
    assert '"-map","[aud]"' in source
