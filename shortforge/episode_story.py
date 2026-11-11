"""Authored five-shot ShortForge episodes and their camera subjects."""
from pathlib import Path
import re

EPISODES = {
    "episode_compost": ("Same scraps", "Inside both bins", "Air spaces", "The warm core", "Loose or compact?"),
    "episode_wind": ("Which rotor wins?", "Wind over the ridge", "Inside the wake", "Power over time", "Where would you measure?"),
    "episode_trap": ("A clue under the sink", "Water stays in the bend", "The water seal", "The seal dries out", "A refill closes the gap"),
    "episode_heat_pump": ("Hot water, cool exhaust", "Heat leaves the air", "The refrigerant gets hotter", "Heat enters the tank", "Follow the heat"),
    "episode_rain_garden": ("A puddle on purpose", "Same rain, different paths", "Water soaks in", "The overflow route", "After the rain"),
    "episode_induction": ("Where does the heat start?", "A field through glass", "Currents heat the pan", "The base makes a difference", "Heat moves back to the glass"),
    "episode_low_e": ("Which window loses more heat?", "Heat crosses the gap", "The invisible coating", "Sunlight is a second question", "Two window ratings"),
    "episode_ventilation": ("One more window", "Warm air leaves high", "Cooler air enters low", "A breeze changes the route", "Trace the whole path"),
    "episode_siphon": ("Water climbs first", "The outlet is lower", "A full column of water", "Lift the outlet", "Follow the water again"),
    "episode_cool_roof": ("A hot roof and a cool room", "Reflect or absorb", "The roof gives off heat", "Follow heat into the attic", "Surface and room temperatures"),
}
TARGETS = ("opening", "reveal", "mechanism", "experiment", "payoff")
SOURCE = Path(__file__).resolve().parents[1] / "docs" / "EPISODE_SCRIPTS.md"
ROWS = re.compile(r"^\| (\d+)–(\d+)s \| ([^|]+) \| ([^|]+) \|$", re.M)


def build_episodes():
    from .story_v2 import validate_story_v2
    sections = SOURCE.read_text(encoding="utf-8").split("\n## ")[1:]
    if len(sections) != len(EPISODES):
        raise ValueError("Episode scripts and registered scenes disagree")
    stories = {}
    for (scene, labels), section in zip(EPISODES.items(), sections):
        rows = ROWS.findall(section)
        if len(rows) != len(TARGETS):
            raise ValueError(f"{scene} needs five authored voiceover beats")
        title = section.splitlines()[0].split(". ", 1)[1]
        beats = []
        for i, (target, label, (start, end, narration, _)) in enumerate(zip(TARGETS, labels, rows), 1):
            beats.append({
                "id":f"beat_{i:02d}","start":int(start),"end":int(end),
                "problem":label,"solution":narration,"narration":narration,"callout":label,
                "camera":"detail","actions":[{"type":"flow","target":target}],
            })
        stories[scene] = validate_story_v2({
            "version":2,"title":title,"duration":beats[-1]["end"],"fps":24,"resolution":[720,1280],
            "scene_template":scene,"narration_timing":"uniform","narration_rate":1.07,"beats":beats,
        })
    return stories
