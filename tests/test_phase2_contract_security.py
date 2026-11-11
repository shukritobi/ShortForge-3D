"""Untrusted nested JSON must cause contract errors, not Python crashes."""
from copy import deepcopy
import pytest
from shortforge.story_v2 import StoryV2Error, validate_story_v2
from shortforge.topic_packs import build_story


@pytest.mark.parametrize("field,value",[
    ("scene_template",{"path":"../../"}),
    ("scene_template",["solar_home"]),
])
def test_malformed_template_type(field,value):
    story=deepcopy(build_story("solar",90))
    story[field]=value
    with pytest.raises(StoryV2Error,match="scene_template"):
        validate_story_v2(story)


def test_malformed_camera_type():
    story=deepcopy(build_story("solar",90))
    story["beats"][0]["camera"]=["establish"]
    with pytest.raises(StoryV2Error,match="camera"):
        validate_story_v2(story)


def test_malformed_nested_action_type():
    story=deepcopy(build_story("solar",90))
    story["beats"][0]["actions"]=[{"type":{"__class__":"exec"},"target":"house"}]
    with pytest.raises(StoryV2Error,match="unregistered"):
        validate_story_v2(story)
