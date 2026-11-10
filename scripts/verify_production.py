"""Actual-file verification and optional monitoring of an already-running job."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shortforge.video import inspect_video
from shortforge.telemetry import Sampler


def verify(project,story):
    video=project/"draft.mp4"
    report=inspect_video(video,expected_duration=story["duration"],expected_fps=story["fps"],
                         expected_resolution=story["resolution"])
    run=subprocess.run(["ffmpeg","-hide_banner","-i",str(video),"-vf",
        "blackdetect=d=0.15:pix_th=0.05","-af","ebur128=peak=true","-f","null","-"],
        capture_output=True,text=True)
    (project/"decode_loudness.log").write_text(run.stderr,encoding="utf-8")
    report.update(full_decode_passed=run.returncode==0,
                  black_segments=[line for line in run.stderr.splitlines() if "black_start:" in line],
                  sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
                  human_listening_approval=False,
                  caption_alignment="waveform-assisted estimate; not forced word alignment")
    (project/"production_quality.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if run.returncode or report["black_segments"]:raise RuntimeError("Decode/black-frame QA failed")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("project",type=Path)
    parser.add_argument("story",type=Path)
    parser.add_argument("--monitor",type=Path,help="Watch existing render log until quality.json exists (30m cap)")
    args=parser.parse_args()
    if args.monitor:
        sampler=Sampler(args.project/"production_samples.jsonl")
        start=time.time()
        while not (args.project/"quality.json").exists() and time.time()-start<1800:
            sampler.sample(stage="full_render",log_file=args.monitor)
            time.sleep(3)
        (args.project/"performance_report.json").write_text(json.dumps(sampler.report(
            stage_times={"observed_render_sec":time.time()-start}),indent=2))
    verify(args.project,json.loads(args.story.read_text(encoding="utf-8")))
