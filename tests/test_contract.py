import copy
import json
import pytest
from shortforge.contract import StoryboardError, validate_storyboard, word_count
from shortforge.director import template_storyboard


def sample():
    return template_storyboard("water tower")


def test_reference_story_is_40_seconds_with_allowed_actions():
    s = sample()
    assert validate_storyboard(s) is s
    assert len(s["beats"]) == 8
    assert s["beats"][0]["start"] == 0
    assert s["beats"][-1]["end"] == 40
    assert 65 <= word_count(s) <= 85  # narratable at natural Qwen pace in 40s


def test_rejects_timeline_gap():
    s = copy.deepcopy(sample())
    s["beats"][3]["start"] = 14.5
    with pytest.raises(StoryboardError, match="contiguous"):
        validate_storyboard(s)


def test_rejects_arbitrary_python():
    s = copy.deepcopy(sample())
    s["beats"][2]["actions"].append("__import__('os').system('whoami')")
    with pytest.raises(StoryboardError, match="unsupported action"):
        validate_storyboard(s)


def test_rejects_nonfinite_time():
    s = copy.deepcopy(sample())
    s["beats"][0]["end"] = float("nan")
    with pytest.raises(StoryboardError, match="invalid timing"):
        validate_storyboard(s)


def test_rejects_unknown_camera():
    s = copy.deepcopy(sample())
    s["beats"][1]["camera"] = "exec_python"
    with pytest.raises(StoryboardError, match="camera"):
        validate_storyboard(s)


def test_template_rejects_other_topics():
    with pytest.raises(ValueError, match="water-tower"):
        template_storyboard("how to build a fireplace")
