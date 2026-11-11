"""Reusable topic packs: stories are data, not topic-specific Blender source.

All action targets are resolved against a small, vetted scene registry.
A future asset package can add mechanisms without editing the compositor.
"""
from __future__ import annotations
from copy import deepcopy
from .story_v2 import SCENE_TEMPLATES, DURATIONS, validate_story_v2


# Each line is a concise, original piece of factual narration.
# target/action/camera specify the actual camera and model behavior.
WATER = [
("A city needs clean water at every tap, every hour.", "neighbourhood","appear","establish"),
("One small pump can serve a home, but demand keeps growing.", "pump","appear","detail"),
("Now many families open their taps at the same time.", "faucet","appear","detail"),
("Water pressure begins to fall across the nearby streets.", "branch","highlight","section"),
("A larger pump moves more water, but demand still fluctuates.", "pump","pulse","detail"),
("During quiet hours, that extra capacity often sits unused.", "pump","highlight","detail"),
("The system needs somewhere to store water between busy periods.", "reservoir","appear","overhead"),
("So engineers build a storage tank above the surrounding homes.", "tower","assemble","establish"),
("Strong columns carry the enormous weight of the elevated tank.", "tower","highlight","detail"),
("Braces help resist side forces, including the push of wind.", "tower","pulse","detail"),
("A pipe brings treated water up into the tank.", "main","appear","section"),
("Pumps fill the tank when supply and demand allow it.", "tank","flow","detail"),
("The tank stores water high above the streets below.", "tank","highlight","establish"),
("That height matters, because gravity creates useful pressure.", "tower","highlight","section"),
("Water can then descend through a large distribution main.", "main","flow","follow"),
("The main runs underground along the roads of the neighbourhood.", "ground","cutaway","section"),
("Smaller service pipes branch off toward each house.", "branch","appear","section"),
("Each branch connects to a household plumbing system.", "faucet","flow","detail"),
("The elevated supply helps smooth rapid changes in water demand.", "tank","pulse","detail"),
("Control valves can isolate a section for maintenance.", "branch","highlight","detail"),
("Sensors tell operators when the tank needs refilling.", "tank","pulse","detail"),
("A pump switches on again as the stored level drops.", "pump","pulse","detail"),
("This storage also adds resilience during short interruptions.", "tank","highlight","reveal"),
("And that is how one water tower helps supply a neighbourhood.", "neighbourhood","highlight","reveal"),
]
SOLAR = [
("Your roof receives sunlight through much of the daytime.", "sun","appear","establish"),
("But sunlight alone cannot run the lights inside your home.", "house","appear","detail"),
("So you mount solar panels across a suitable roof surface.", "panels","assemble","overhead"),
("Each panel contains many small photovoltaic cells.", "panels","highlight","detail"),
("Light arriving at the cells can drive an electric current.", "sun","flow","follow"),
("The panels produce direct current, often called DC.", "panels","pulse","detail"),
("Household appliances usually expect alternating current, or AC.", "house","highlight","detail"),
("So the panel wiring feeds electricity toward an inverter.", "inverter","appear","follow"),
("The inverter converts DC into usable alternating current.", "inverter","pulse","detail"),
("Safety switches and protective devices guard the electrical circuits.", "inverter","highlight","detail"),
("That output can power lights, fans and other household loads.", "lights","appear","detail"),
("On a bright day, production may exceed what you use.", "meter","pulse","detail"),
("Some systems export surplus electricity to the local grid.", "grid","flow","section"),
("Other systems send part of that energy into a battery.", "battery","appear","detail"),
("A compatible battery stores energy for use at another time.", "battery","pulse","detail"),
("When clouds arrive, the panels generate less electricity.", "sun","highlight","establish"),
("The home may then draw from the battery or grid.", "grid","highlight","follow"),
("A meter measures electricity flowing between home and network.", "meter","appear","detail"),
("Monitoring software tracks generation and household consumption.", "meter","pulse","detail"),
("Panel angle and shade strongly influence the daily output.", "panels","highlight","overhead"),
("Mounts must withstand wind and weather.", "panels","highlight","detail"),
("The inverter and wiring require proper professional installation.", "inverter","highlight","detail"),
("Solar needs backup after sunset.", "battery","highlight","reveal"),
("Together these parts turn daylight into useful household electricity.", "house","highlight","reveal"),
]
from .rainwater_pack import RAINWATER, DETAILS
from .solar_explainer import SOLAR_MECHANISMS, SOLAR_EXTRA, SOLAR_SHOTS
PACKS = {
    "rainwater": {"title":"How a Home Harvests Rainwater",
                  "aliases":("rainwater","rain harvesting"),"beats":RAINWATER,"details":DETAILS},
    "water_distribution": {
        "title":"How a Water Tower Supplies a Neighbourhood",
        "aliases":("water tower","water distribution","water supply"),
        "beats":WATER
    },
    "solar_home": {
        "title":"How Solar Panels Power a Home",
        "aliases":("solar","solar panel","photovoltaic","solar energy"),
        "beats":SOLAR
    }
}


def resolve_topic(topic: str) -> str:
    value = topic.casefold().strip()
    for key, pack in PACKS.items():
        if value == key or any(alias in value for alias in pack["aliases"]):
            return key
    raise ValueError("No scene pack for this topic yet. Available: " +
                     ", ".join(sorted(PACKS)) + ". Register a scene/action pack first.")


def build_story(topic: str, duration: int = 90, *, fps=24, profile="draft",
                audience="general", complexity="standard") -> dict:
    if type(duration) is not int or not 40<=duration<=240:
        raise ValueError("Built-in scripts cover 40-240 seconds; author a manual storyboard for longer timelines")
    ident = resolve_topic(topic)
    pack = PACKS[ident]
    if ident == "solar_home":
        return detailed_solar_story(duration, fps, profile, audience, complexity)
    steps = pack["beats"]
    if duration>120:
        from .topic_details import SOLAR_DETAILS,WATER_DETAILS
        details=pack.get("details") or (SOLAR_DETAILS if ident=="solar_home" else WATER_DETAILS)
        steps=[item for step,detail in zip(steps,details)
               for item in (step,(detail,*step[1:]))]
    count = min(len(steps),max(10,round(duration/5)))
    # Even sampling retains introduction and conclusion for shorter versions.
    indices = [round(i*(len(steps)-1)/(count-1)) for i in range(count)]
    # Explanatory cutaways are structural narrative events, never optional
    # samples. Keep them even when shortening a pack.
    mandatory={i for i,s in enumerate(steps) if s[2]=="cutaway"}
    for required in sorted(mandatory-set(indices)):
        candidate=min((i for i in indices[1:-1] if i not in mandatory),key=lambda i:abs(i-required))
        indices[indices.index(candidate)]=required
    indices.sort()
    if len(set(indices)) != len(indices):
        raise AssertionError("topic pack does not contain enough unique steps")
    beats=[]
    for i,index in enumerate(indices):
        line,target,action,camera=steps[index]
        start=round(i*duration/count,5)
        end=round((i+1)*duration/count,5)
        beats.append({
            "id":f"beat_{i+1:02d}", "start":start, "end":end,
            "problem":line, "solution":f"Visual demonstration: {action} {target}",
            "narration":line, "camera":camera,
            "actions":[{"type":action,"target":target}],
            "scene_id":ident,"required_assets":[target],"transition":"smooth",
            "sfx":[],"validation_rules":["subject_visible","portrait_safe"]
        })
    return validate_story_v2({
        "version":2, "title":pack["title"], "duration":duration,
        "fps":fps, "resolution":{"preview":[360,640],"draft":[720,1280],"final":[1080,1920]}[profile],
        "audience":audience,"complexity":complexity,
        "scene_template":ident, "beats":beats
    })


def detailed_solar_story(duration, fps, profile, audience, complexity):
    # Short versions use concise lines but retain the three-part PV explanation.
    compact = (
        "Those silver lines on a solar cell collect current.",
        "Rails leave space for air beneath the modules.",
        "Under the metal grid sits a thin silicon cell.",
        "Absorbed light frees electrons and leaves holes.",
        "The junction field drives the charges toward opposite sides.",
        "Connect cells in series and their voltages add.",
        "A shadow can limit current in an entire series group.",
        "A bypass diode routes current around that group.",
        "The inverter tracks peak power and converts direct current.",
        "Breakers protect the circuits that supply the house.",
        "The meter tracks power entering and leaving the property.",
        "Blackout backup needs safe grid isolation.",
    )
    steps = list(SOLAR_MECHANISMS)
    if duration < 50:
        quick = ("Silver fingers collect the current.","Rails leave an air gap.",
                 "Silicon sits beneath the front grid.","Photons free electrons and leave holes.",
                 "The junction separates the charges.","Series cells add their voltages.",
                 "Shade can limit a whole group.","A diode bypasses that group.",
                 "The inverter tracks power and converts it.","Breakers protect separate household circuits.",
                 "The meter tracks imports and exports.","Blackout backup needs safe grid isolation.")
        steps = [(line,*step[1:]) for line,step in zip(quick,steps)]
    elif duration < 65:
        steps = [(line, *step[1:]) for line, step in zip(compact, steps)]
    elif duration < 100:
        shorter = [step[0].split(". ",1)[0].rstrip(".")+"." for step in steps]
        used = sum(len(line.split()) for line in shorter)
        budget = int(2.08*(duration-2.6))
        for i in (3,4,7,6,8,9,10,11,2,5,1,0):
            count = len(steps[i][0].split())
            extra = count-len(shorter[i].split())
            if used+extra<=budget and count<=duration/len(steps)*3.3:
                shorter[i]=steps[i][0]
                used+=extra
        steps = [(line,*step[1:]) for line,step in zip(shorter,steps)]
    elif duration > 130:
        added = min(12, round((duration-120)/9))
        indices = {round(i*11/max(1,added-1)) for i in range(added)}
        steps = [item for i, step in enumerate(steps)
                 for item in ([step,(SOLAR_EXTRA[i],"pv_cell" if step[1]=="pv_light" else step[1],
                                      "highlight",*step[3:])] if i in indices else [step])]
    beats = []
    for index, (line, target, action, camera, label) in enumerate(steps):
        start, end = (round(duration*i/len(steps), 5) for i in (index,index+1))
        actions = [{"type":action,"target":target}]
        if index == 0:
            actions.append({"type":"appear","target":"panels"})
        if target == "distribution":
            actions.append({"type":"appear","target":"lights"})
        beats.append({"id":f"beat_{index+1:02d}","start":start,"end":end,
                      "problem":label,"solution":line,"narration":line,"camera":camera,
                      "actions":actions,"callout":label})
        if 100 <= duration <= 130 and SOLAR_SHOTS[index]:
            beats[-1]["shot_cues"] = [{"at":at,"target":subject,"camera":mode}
                                     for at,subject,mode in SOLAR_SHOTS[index]]
    return validate_story_v2({"version":2,"title":"Inside a Solar-Powered Home",
        "duration":duration,"fps":fps,"resolution":{"preview":[360,640],"draft":[720,1280],"final":[1080,1920]}[profile],
        "audience":audience,"complexity":complexity,"scene_template":"solar_home",
        "narration_timing":"native","beats":beats})
