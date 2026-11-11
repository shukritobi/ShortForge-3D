"""Retiming from measured speech, with bounded pace and stable beat IDs."""
import copy
import math
from .contract import validate_storyboard


def retime_from_report(story,report,max_speed=1.25,*,extend=False):
    result=copy.deepcopy(story)
    measured={row["beat"]:row for row in report["beats"]}
    lengths=[measured.get(b["id"],{}).get("spoken_audio_sec") for b in result["beats"]]
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in lengths):
        raise ValueError("Complete measured speech is required")
    fixed=story.get("narration_timing") in ("native","uniform")
    if fixed:
        max_speed=story.get("narration_rate",1.0)
        lengths=[length-measured[beat["id"]].get("trim_start_sec",0)
                 for length,beat in zip(lengths,story["beats"])]
        if min(lengths)<=0:
            raise ValueError("Voice lead-in trim would remove a whole take")
    minimum=[max(2.5,x/max_speed+.22) for x in lengths]
    if sum(minimum)>story["duration"]:
        if fixed and extend:
            result["duration"]=math.ceil(sum(minimum))
        else:
            raise ValueError(f"Narration needs rewriting or at least {math.ceil(sum(minimum))}s. Shorten lines or extend the timeline.")
    natural=[max(2.5,x+.22) for x in lengths]
    base=natural if not fixed and sum(natural)<=result["duration"] else minimum
    slack=result["duration"]-sum(base)
    cursor=0
    for index,beat in enumerate(result["beats"]):
        beat["start"]=round(cursor,5)
        cursor+=base[index]+slack/len(base)
        beat["end"]=round(cursor,5)
    result["beats"][-1]["end"]=result["duration"]
    return validate_storyboard(result)
