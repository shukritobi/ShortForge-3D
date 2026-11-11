"""One-command, multi-topic real Blender verification and Drive handoff."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shortforge.topic_packs import build_story
from shortforge.telemetry import Sampler
from scripts.one_click_review import OUTPUT,execute,sync_bundle,stamp,copy_if


def main():
    run=OUTPUT/"review_runs"/(stamp()+"-production-verification")
    run.mkdir(parents=True)
    sampler=Sampler(run/"system_samples.jsonl")
    results=[]
    tests=execute("tests",[sys.executable,"-m","pytest","-q"],run,sampler)
    results.append(tests)
    if tests["exit_code"]==0:
        for topic,duration in (("solar_home",120),("water_distribution",90),("rainwater",90)):
            project=OUTPUT/"projects"/topic/f"{duration}s"
            project.mkdir(parents=True,exist_ok=True)
            story=project/"storyboard.json"
            if not story.exists():story.write_text(json.dumps(build_story(topic,duration),indent=2))
            data=json.loads(story.read_text())
            count=data["duration"]*data["fps"]
            numbers=",".join(str(round(count*i/7)) for i in range(1,7))
            result=execute(topic,[sys.executable,"-m","shortforge.cli","render",str(story),"--out",str(project),
                                  "--preview-frames",numbers],run,sampler)
            results.append(result)
            if result["exit_code"]==0:
                copy_if(project/"contact_sheet.png",run/f"{topic}_contact_sheet.png")
                for name in ("storyboard.json","scene_manifest.json"):
                    copy_if(project/name,run/"diagnostics"/topic/name)
    (run/"run_manifest.json").write_text(json.dumps({"stages":results,"youtube_publishing":False,
        "status":"ready_for_visual_review" if all(r["exit_code"]==0 for r in results) else "failed"},indent=2))
    (run/"performance_report.json").write_text(json.dumps(sampler.report(),indent=2))
    sync_result=sync_bundle(run,None)
    print(json.dumps(sync_result,indent=2))
    return int(sync_result["status"]!="synced" or any(r["exit_code"] for r in results))


if __name__=="__main__":raise SystemExit(main())
