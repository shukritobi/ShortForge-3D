import copy

import pytest

from shortforge.episode_story import TARGETS, build_episodes
from shortforge.story_v2 import StoryV2Error, validate_story_v2
from shortforge.topic_packs import build_story


def test_authored_season_is_registered_with_fixed_pace():
    stories=build_episodes()
    assert len(stories)==10
    for slug,story in stories.items():
        assert story["scene_template"]==slug
        assert story["resolution"]==[720,1280]
        assert story["narration_timing"]=="uniform" and story["narration_rate"]==1.07
        assert tuple(beat["actions"][0]["target"] for beat in story["beats"])==TARGETS
    invalid=copy.deepcopy(stories["episode_compost"])
    invalid["beats"][2]["actions"][0]["target"]="pv_carriers"
    with pytest.raises(StoryV2Error,match="unregistered action or target"):
        validate_story_v2(invalid)


def test_five_beat_exception_only_applies_to_authored_episode_templates():
    story=build_story("solar",120)
    story["beats"]=story["beats"][:5]
    story["beats"][-1]["end"]=120
    with pytest.raises(StoryV2Error,match="expected 8"):
        validate_story_v2(story)
