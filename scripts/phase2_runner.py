"""Phase 2 multi-topic on-PC review/full production with Drive handoff.

No listener, cloud GPU, uploads to YouTube or arbitrary code execution.
Only built-in scene templates are executable. Large Blender frames stay on SSD.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shortforge.topic_packs import build_story, resolve_topic
from shortforge.story_v2 import DURATIONS, total_frames
from shortforge.telemetry import Sampler, iso_now
from scripts.one_click_review import (
    OUTPUT, copy_if, execute, latest_git_sha, stamp, sync_bundle
)


def preview_frames(duration:int,fps:int=24)->list[int]:
    maximum=duration*fps
    return [max(1,round(maximum*i/7)) for i in range(1,7)]


def project_folder(topic:str,duration:int)->Path:
    ident=resolve_topic(topic)
    return OUTPUT/"projects"/ident/f"{duration}s"


def collect(run:Path,project:Path,story:Path,frame_nums:list[int],*,full:bool):
    copy_if(story,run/"storyboard.json")
    for name in ("contact_sheet.png","scene_manifest.json","render_state_v2.json"):
        copy_if(project/name,run/name)
    for n in frame_nums:
        copy_if(project/f"preview_{n:04d}.png",run/f"preview_{n:04d}.png")
    # Always preserve audio diagnostics even when a long narration beat fails:
    # failure evidence must be accessible without repeating expensive GPU TTS.
    for name in ("voice_manifest.json","timing_report.json","tts_metrics.jsonl"):
        copy_if(project/"audio"/name,run/name)
    raw=project/"audio"/"beats"
    if raw.is_dir():
        for sample in raw.glob("beat_*_raw.wav"):
            copy_if(sample,run/"voice_samples"/sample.name)
    if full:
        for name in ("draft.mp4","quality.json"):
            copy_if(project/name,run/name)


def run_phase2(topic:str,duration:int,*,mode:str="preview",
               tts:str="qwen",drive:Path|None=None)->int:
    if mode not in ("preview","full"):
        raise ValueError("mode must be preview or full")
    if tts not in ("qwen","kokoro","none"):
        raise ValueError("unsupported narration engine")
    story=build_story(topic,duration)
    folder=project_folder(topic,duration)
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/"storyboard.json"
    path.write_text(json.dumps(story,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    run_id=stamp()+"-phase2-"+resolve_topic(topic)+"-"+mode
    run=OUTPUT/"review_runs"/run_id
    # Use a run-specific suffix if launched twice in one second.
    if run.exists():
        import uuid
        run=OUTPUT/"review_runs"/(run_id+"-"+uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    sampler=Sampler(run/"system_samples.jsonl")
    numbers=preview_frames(duration)
    py=sys.executable
    stages=[
        ("tests",[py,"-m","pytest","-q"]),
        ("validate",[py,"-m","shortforge.cli","validate",str(path)]),
        ("preview",[py,"-m","shortforge.cli","render",str(path),
                    "--out",str(folder),"--preview-frames",",".join(map(str,numbers))]),
    ]
    if mode=="full":
        stages.append((
            "full",[py,"-m","shortforge.cli","run",str(path),
                    "--out",str(folder),"--tts",tts]
        ))
    results=[]
    start=time.monotonic()
    for name,command in stages:
        result=execute(name,command,run,sampler)
        result["status"]="ok" if result["exit_code"]==0 else "failed"
        results.append(result)
        if result["status"]=="failed":
            break
    full_success=bool(mode=="full" and len(results)==len(stages) and
                      results[-1]["status"]=="ok")
    preview_success=any(x["stage"]=="preview" and x["status"]=="ok" for x in results)
    if preview_success:
        collect(run,folder,path,numbers,full=full_success)
    elif path.is_file():
        copy_if(path,run/"storyboard.json")
    performance=sampler.report(stage_times={x["stage"]:x["duration_sec"] for x in results})
    (run/"performance_report.json").write_text(json.dumps(performance,indent=2)+"\n",encoding="utf-8")
    outcome="ready_for_review" if len(results)==len(stages) and all(x["status"]=="ok" for x in results) else "needs_review"
    record={
        "schema_version":2, "run_id":run.name, "created_utc":iso_now(),
        "git_sha":latest_git_sha(), "status":outcome, "mode":"phase2_"+mode,
        "topic":resolve_topic(topic), "duration":duration,
        "frame_count":total_frames(story), "tts":tts if mode=="full" else "not_run",
        "stages":results,"elapsed_sec":round(time.monotonic()-start,2),
        "draft_mp4_generated":full_success and (run/"draft.mp4").is_file(),
        "youtube_publishing":False
    }
    (run/"run_manifest.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    (run/"READ_ME_FIRST.txt").write_text(
        f"SHORTFORGE PHASE 2: {record['topic']} / {duration}s\n"
        f"Result: {outcome}; Mode: {mode}; Frames: {record['frame_count']}\n"
        f"Stages: "+", ".join(f"{s['stage']}={s['status']}" for s in results)+"\n"
        "This run was performed locally. No YouTube publishing.\n",
        encoding="utf-8"
    )
    sync=sync_bundle(run,drive)
    print(json.dumps({"project":str(folder),"run":run.name,
                      "status":outcome,"drive":sync},indent=2),flush=True)
    if sync.get("status")!="synced":
        return 2
    return 0 if outcome=="ready_for_review" else 1


def main():
    p=argparse.ArgumentParser(description="Local multi-topic 3D production review")
    p.add_argument("--topic",required=True,help="water_tower or solar_home")
    p.add_argument("--duration",type=int,choices=DURATIONS,default=90)
    p.add_argument("--mode",choices=["preview","full"],default="preview")
    p.add_argument("--tts",choices=["qwen","kokoro","none"],default="qwen")
    p.add_argument("--drive",type=Path)
    a=p.parse_args()
    return run_phase2(a.topic,a.duration,mode=a.mode,tts=a.tts,drive=a.drive)


if __name__=="__main__":
    raise SystemExit(main())
