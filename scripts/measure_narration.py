"""Generate narration, then fit the storyboard to actual speech without resynthesis."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shortforge.audio import create_audio
from shortforge.contract import load_storyboard
from shortforge.timing import retime_from_report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("story",type=Path)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    story=load_storyboard(a.story)
    try:create_audio(story,a.out/"audio")
    except RuntimeError:
        report=a.out/"audio"/"timing_report.json"
        if not report.is_file():raise
        story=retime_from_report(story,json.loads(report.read_text()))
        (a.out/"storyboard_before_timing.json").write_bytes(a.story.read_bytes())
        (a.out/"storyboard.json").write_text(json.dumps(story,indent=2))
        create_audio(story,a.out/"audio")
    else:
        (a.out/"storyboard.json").write_text(json.dumps(story,indent=2))
    print("Measured narration passed; render using",a.out/"storyboard.json")
