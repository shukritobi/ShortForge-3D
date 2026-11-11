"""Generate narration, then fit the storyboard to actual speech without resynthesis."""
import argparse
import json
import math
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shortforge.audio import create_audio
from shortforge.contract import load_storyboard
from shortforge.timing import retime_from_report
from shortforge.studio_lock import studio_job_slot


def main():
    p=argparse.ArgumentParser()
    p.add_argument("story",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--extend-to-fit",action="store_true",help="extend a native-speed timeline if speech exceeds its budget")
    p.add_argument("--compact",action="store_true",help="set the timeline from measured speech and short pauses")
    a=p.parse_args()
    story=load_storyboard(a.story)
    report=a.out/"audio"/"timing_report.json"
    try:create_audio(story,a.out/"audio")
    except RuntimeError:
        if not report.is_file():raise
        failed=True
    else:failed=False
    if failed or story.get("narration_timing") in ("native","uniform"):
        measured=json.loads(report.read_text())
        (a.out/"storyboard_before_timing.json").write_bytes(a.story.read_bytes())
        if a.compact and story.get("narration_timing") in ("native","uniform"):
            takes=[b["spoken_audio_sec"] for b in measured["beats"]]
            if all(take is not None for take in takes):
                rate=story.get("narration_rate",1)
                story["duration"]=max(20,math.ceil(sum(
                    max(2.5,(take-row.get("trim_start_sec",0))/rate+.36)
                    for take,row in zip(takes,measured["beats"]))))
        story=retime_from_report(story,measured,extend=a.extend_to_fit)
        create_audio(story,a.out/"audio")
    target=a.out/"storyboard.json"
    temp=target.with_suffix(".timed.tmp")
    temp.write_text(json.dumps(story,indent=2),encoding="utf-8")
    for attempt in range(5):
        try:
            temp.replace(target)
            break
        except PermissionError:
            if attempt==4:raise
            time.sleep(.025*(attempt+1))
    print("Measured narration passed; render using",a.out/"storyboard.json")


if __name__=="__main__":
    with studio_job_slot():
        main()
