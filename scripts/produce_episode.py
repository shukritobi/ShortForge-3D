"""Measure, preview or render the authored ShortForge season locally."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shortforge.episode_story import EPISODES, build_episodes
from verify_production import verify


def share(project, slug, destination):
    destination.mkdir(parents=True, exist_ok=True)
    index=list(EPISODES).index(slug)+1
    name=f"{index:02d} - {slug.removeprefix('episode_').replace('_',' ').title()}"
    for source,target in ((project/"draft.mp4",destination/f"{name}.mp4"),
                          (project/"production_quality.json",destination/"checks"/f"{name}.json")):
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix(target.suffix+".part")
        shutil.copy2(source,temporary)
        temporary.replace(target)


def execute(stage, slug, story, project, blender, review_dir):
    planned=project/"authored_storyboard.json"
    measured=project/"storyboard.json"
    cli=[sys.executable,"-m","shortforge.cli"]
    if stage=="voice":
        command=[sys.executable,str(ROOT/"scripts"/"measure_narration.py"),
                 str(planned),"--out",str(project),"--extend-to-fit","--compact"]
    elif stage=="preview":
        story=json.loads(measured.read_text(encoding="utf-8")) if measured.is_file() else story
        frames=[1+round((b["start"]+(b["end"]-b["start"])*.42)*story["fps"]) for b in story["beats"]]
        command=[*cli,"render",str(measured if measured.is_file() else planned),
                 "--out",str(project/"preview"),"--blender",blender,
                 "--preview-frames",",".join(map(str,frames))]
    else:
        if not measured.is_file():
            print(f"{slug}: measure narration first",flush=True)
            return False
        command=[*cli,"run",str(measured),"--out",str(project),"--blender",blender]
    log=project/f"{stage}.log"
    print(f"{stage}: {slug} | {log}",flush=True)
    with log.open("w",encoding="utf-8") as stream:
        result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:
        return False
    if stage=="render":
        timing=json.loads((project/"audio"/"timing_report.json").read_text(encoding="utf-8"))
        if timing["status"]!="passed" or any(row["speed_adjustment"]!=1.07 for row in timing["beats"]):
            raise RuntimeError(f"{slug}: narration speed or fit check failed")
        verify(project,json.loads(measured.read_text(encoding="utf-8")))
        if review_dir:
            share(project,slug,review_dir)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("voice", "preview", "render", "complete"))
    parser.add_argument("--episode", choices=EPISODES, action="append")
    parser.add_argument("--out", type=Path, default=ROOT / "output" / "season_one")
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--review-dir",type=Path,help="copy verified MP4s and quality reports here")
    args = parser.parse_args()
    authored = build_episodes()
    failures = []
    for slug in args.episode or authored:
        project = (args.out / slug.removeprefix("episode_")).resolve()
        project.mkdir(parents=True, exist_ok=True)
        planned = project / "authored_storyboard.json"
        planned.write_text(json.dumps(authored[slug], indent=2) + "\n", encoding="utf-8")
        stages=("voice","preview","render") if args.stage=="complete" else (args.stage,)
        for stage in stages:
            try:
                passed=execute(stage,slug,authored[slug],project,args.blender,args.review_dir)
            except (OSError,RuntimeError,ValueError) as error:
                print(f"{stage}: {slug} | {error}",flush=True)
                passed=False
            if not passed:
                failures.append(slug)
                break
    if failures:
        raise SystemExit(f"{args.stage} failed for {', '.join(failures)}")


if __name__ == "__main__":
    main()
