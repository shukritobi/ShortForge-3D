"""Retiming from measured speech, with bounded pace and stable beat IDs."""
import copy
from .contract import validate_storyboard


def retime_from_report(story,report,max_speed=1.25):
    result=copy.deepcopy(story)
    durations={row["beat"]:row["spoken_audio_sec"] for row in report["beats"]}
    lengths=[durations.get(b["id"]) for b in result["beats"]]
    if any(not isinstance(x,(int,float)) or x<=0 for x in lengths):
        raise ValueError("Complete measured speech is required")
    minimum=[max(2.5,x/max_speed+.2) for x in lengths]
    if sum(minimum)>story["duration"]:
        raise ValueError("Narration needs rewriting; it cannot fit within the safe speed limit")
    natural=[max(2.5,x+.2) for x in lengths]
    base=natural if sum(natural)<=story["duration"] else minimum
    slack=story["duration"]-sum(base)
    cursor=0
    for index,beat in enumerate(result["beats"]):
        beat["start"]=round(cursor,5)
        cursor+=base[index]+slack/len(base)
        beat["end"]=round(cursor,5)
    result["beats"][-1]["end"]=story["duration"]
    return validate_storyboard(result)
