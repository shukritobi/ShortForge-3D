"""ShortForge CLI: phase-one local 40-second production pipeline.

No publishing commands are implemented by design.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from .contract import load_storyboard, narration, word_count
from .director import template_storyboard, ollama_storyboard
from .captions import write_captions
from .audio import create_audio, require_program
from .pc_agent import find_blender
from .video import compose, inspect_video

ROOT = Path(__file__).resolve().parents[1]
BLENDER_SCRIPT = ROOT/"scripts"/"blender_water_tower.py"
DEFAULT_STORY = ROOT/"examples"/"water_tower_40s.json"


def render(storyboard: Path, output: Path, *, blender="blender", preview_frame=None):
    executable = find_blender(blender)
    if not executable:
        raise RuntimeError("Blender not detected. Run: python scripts/pc_agent.py doctor; or pass --blender with the full blender.exe path")
    command = [executable,"-b","--python",str(BLENDER_SCRIPT),
               "--","--storyboard",str(storyboard.resolve()),"--out",str(output.resolve())]
    if preview_frame is not None:
        command.extend(["--preview-frame",str(preview_frame)])
    subprocess.run(command,check=True)


def parser():
    p = argparse.ArgumentParser(prog="shortforge",description="Local-first educational 3D Shorts factory")
    sub = p.add_subparsers(dest="command",required=True)
    d = sub.add_parser("doctor",help="detect and probe local Blender and video tools")
    d.add_argument("--blender")
    d.add_argument("--voice")
    plan = sub.add_parser("plan",help="generate a validated storyboard")
    plan.add_argument("--topic",default="How a water tower supplies an entire neighbourhood")
    plan.add_argument("--engine",choices=["template","ollama"],default="template")
    plan.add_argument("--model",default="qwen3:8b")
    plan.add_argument("--ollama-url",default="http://127.0.0.1:11434")
    plan.add_argument("--output",type=Path,default=Path("output/storyboard.json"))
    v = sub.add_parser("validate")
    v.add_argument("storyboard",type=Path)
    cap = sub.add_parser("captions")
    cap.add_argument("storyboard",type=Path)
    cap.add_argument("--out",type=Path,default=Path("output/water_tower/captions"))
    r = sub.add_parser("render")
    r.add_argument("storyboard",type=Path)
    r.add_argument("--out",type=Path,default=Path("output/water_tower"))
    r.add_argument("--blender",default="blender")
    r.add_argument("--preview-frame",type=int)
    a = sub.add_parser("audio")
    a.add_argument("storyboard",type=Path)
    a.add_argument("--out",type=Path,default=Path("output/water_tower"))
    a.add_argument("--voice",required=True,help="local Piper .onnx voice file")
    a.add_argument("--piper",default="piper")
    a.add_argument("--ffmpeg",default="ffmpeg")
    a.add_argument("--ffprobe",default="ffprobe")
    c = sub.add_parser("compose")
    c.add_argument("storyboard",type=Path)
    c.add_argument("--out",type=Path,default=Path("output/water_tower"))
    c.add_argument("--ffmpeg",default="ffmpeg")
    q = sub.add_parser("check")
    q.add_argument("video",type=Path)
    q.add_argument("--ffprobe",default="ffprobe")
    run = sub.add_parser("run",help="render, speak, caption, compose and QA one short")
    run.add_argument("storyboard",type=Path,nargs="?",default=DEFAULT_STORY)
    run.add_argument("--out",type=Path,default=Path("output/water_tower"))
    run.add_argument("--voice",help="local Piper English .onnx voice file")
    run.add_argument("--blender",default="blender")
    run.add_argument("--piper",default="piper")
    run.add_argument("--ffmpeg",default="ffmpeg")
    run.add_argument("--ffprobe",default="ffprobe")
    run.add_argument("--preview-frame",type=int,help="only render one still; skip narration/assembly")
    run.add_argument("--dry-run",action="store_true",help="validate assets/story and print planned stages without invoking renderers")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.command == "doctor":
        from .pc_agent import main as pc_main
        options = ["doctor"]
        if args.blender:
            options += ["--blender",args.blender]
        if args.voice:
            options += ["--voice",args.voice]
        return pc_main(options)
    if args.command == "plan":
        story = (template_storyboard(args.topic) if args.engine == "template"
                 else ollama_storyboard(args.topic,model=args.model,url=args.ollama_url))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(story,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(f"Storyboard saved: {args.output} ({word_count(story)} words)")
        return
    if args.command == "check":
        print(json.dumps(inspect_video(args.video,ffprobe=args.ffprobe),indent=2))
        return
    story = load_storyboard(args.storyboard)
    if args.command == "validate":
        print(f"Valid: {story['title']} | {len(story['beats'])} beats | 40s | {word_count(story)} words")
        return
    if args.command == "captions":
        print(write_captions(story,args.out))
        return
    if args.command == "render":
        render(args.storyboard,args.out,blender=args.blender,preview_frame=args.preview_frame)
        return
    if args.command == "audio":
        print(create_audio(story,args.out/"audio",model=args.voice,
                           piper=args.piper,ffmpeg=args.ffmpeg,ffprobe=args.ffprobe))
        return
    if args.command == "compose":
        print(compose(story,args.out,ffmpeg=args.ffmpeg))
        return
    if args.command == "run":
        write_captions(story,args.out/"captions")
        if args.dry_run:
            print(json.dumps({
                "status":"validated_only", "title":story["title"],
                "frames":960, "draft_resolution":"720x1280", "duration":40,
                "requires":["Blender","Piper English model","FFmpeg","ffprobe"],
                "stages":["render","audio","captions","compose","check"],
                "note":"no video generated in dry-run mode; no YouTube publishing",
            },indent=2))
            return
        render(args.storyboard,args.out,blender=args.blender,preview_frame=args.preview_frame)
        if args.preview_frame is not None:
            print(f"Preview still rendered: {args.out/'preview.png'}")
            return
        if not args.voice:
            raise SystemExit("full run requires --voice /path/to/english.onnx")
        create_audio(story,args.out/"audio",model=args.voice,
                     piper=args.piper,ffmpeg=args.ffmpeg,ffprobe=args.ffprobe)
        target=compose(story,args.out,ffmpeg=args.ffmpeg)
        report=inspect_video(target,ffprobe=args.ffprobe)
        report["sha256"]=hashlib.sha256(target.read_bytes()).hexdigest()
        (args.out/"quality.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(f"Draft ready for manual review: {target}")
        print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
