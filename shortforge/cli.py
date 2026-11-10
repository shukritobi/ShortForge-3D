"""ShortForge CLI: phase-one local 40-second production pipeline.

No publishing commands are implemented by design.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import shutil
from .contract import load_storyboard, narration, word_count
from .director import template_storyboard, ollama_storyboard
from .captions import write_captions
from .audio import create_audio, create_silent_audio, require_program
from .pc_agent import find_blender
from .video import compose, inspect_video
from .scene_validation import validate_scene_manifest

ROOT = Path(__file__).resolve().parents[1]
BLENDER_SCRIPT = ROOT/"scripts"/"blender_water_tower.py"
DEFAULT_STORY = ROOT/"examples"/"water_tower_40s.json"


def render(storyboard: Path, output: Path, *, blender="blender", preview_frame=None, preview_frames=None):
    executable = find_blender(blender)
    if not executable:
        raise RuntimeError("Blender not detected. Run: python scripts/pc_agent.py doctor; or pass --blender with the full blender.exe path")
    if preview_frame is not None and preview_frames is not None:
        raise ValueError("Choose either --preview-frame or --preview-frames")
    if preview_frames is not None and (not 2 <= len(preview_frames) <= 6 or
                                       len(set(preview_frames)) != len(preview_frames) or
                                       any(not 1 <= x <= 960 for x in preview_frames)):
        raise ValueError("Expected 2-6 distinct review frames between 1 and 960")
    command = [executable,"-b","--python",str(BLENDER_SCRIPT),
               "--","--storyboard",str(storyboard.resolve()),"--out",str(output.resolve())]
    if preview_frame is not None:
        command.extend(["--preview-frame",str(preview_frame)])
    if preview_frames is not None:
        command.extend(["--preview-frames",",".join(map(str,preview_frames))])
    subprocess.run(command,check=True)
    manifest = validate_scene_manifest(output / "scene_manifest.json")
    print("Scene audit passed:", manifest["structural_counts"])
    if preview_frames is not None:
        _contact_sheet(output, preview_frames)


def _contact_sheet(output: Path, frames: list[int]) -> None:
    """Create a light portrait-friendly review contact sheet using existing FFmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("FFmpeg not found; review frames rendered individually, no contact sheet.")
        return
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for number in frames:
        command.extend(["-i",str((output/("preview_%04d.png" % number)).resolve())])
    cells = [f"[{i}:v]scale=360:640[v{i}]" for i in range(len(frames))]
    chain = "".join(f"[v{i}]" for i in range(len(frames)))
    layouts = "|".join(f"{(i%3)*360}_{(i//3)*640}" for i in range(len(frames)))
    filters = ";".join(cells) + ";" + chain + f"xstack=inputs={len(frames)}:layout={layouts}:fill=black[out]"
    command.extend(["-filter_complex",filters,"-map","[out]",
                    "-frames:v","1",str((output/"contact_sheet.png").resolve())])
    try:
        subprocess.run(command,check=True)
        print("Review contact sheet:", output/"contact_sheet.png")
    except (OSError, subprocess.CalledProcessError) as exc:
        print("Contact sheet failed (individual preview frames remain available):",exc)


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
    preview_opts = r.add_mutually_exclusive_group()
    preview_opts.add_argument("--preview-frame",type=int)
    preview_opts.add_argument("--preview-frames",type=str,
                              help="2-6 comma-separated frame numbers, e.g. 120,240,480,576,720,936")
    a = sub.add_parser("audio")
    a.add_argument("storyboard",type=Path)
    a.add_argument("--out",type=Path,default=Path("output/water_tower"))
    a.add_argument("--tts",choices=["qwen","kokoro","none"],default="qwen")
    a.add_argument("--voice",default=None,help="Qwen speaker (Ryan/Aiden), or Kokoro voice (am_adam/af_heart)")
    a.add_argument("--model-id",help="optional local model path or Hugging Face model ID")
    a.add_argument("--tts-python",help="Python in isolated .venv-tts")
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
    run.add_argument("--tts",choices=["qwen","kokoro","none"],default="qwen",
                     help="Qwen3-TTS (default), Kokoro, or explicit silent technical draft")
    run.add_argument("--voice",default=None,help="Qwen speaker or Kokoro voice")
    run.add_argument("--model-id",help="optional model path or Hugging Face ID")
    run.add_argument("--tts-python",help="Python in dedicated .venv-tts environment")
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
        review = None
        if args.preview_frames:
            try:
                review = [int(part) for part in args.preview_frames.split(",")]
            except ValueError as exc:
                raise SystemExit("--preview-frames must contain comma-separated integers") from exc
        render(args.storyboard,args.out,blender=args.blender,
               preview_frame=args.preview_frame,preview_frames=review)
        return
    if args.command == "audio":
        if args.tts == "none":
            sound = create_silent_audio(args.out/"audio",ffmpeg=args.ffmpeg)
        else:
            sound = create_audio(story,args.out/"audio",provider=args.tts,
                                 voice=args.voice or ("Ryan" if args.tts=="qwen" else "af_heart"),
                                 model_id=args.model_id,python=args.tts_python,
                                 ffmpeg=args.ffmpeg,ffprobe=args.ffprobe)
        print(sound)
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
                "requires":["Blender","FFmpeg","ffprobe","isolated Qwen3-TTS or Kokoro runtime (unless --tts none)"],
                "stages":["render","audio","captions","compose","check"],
                "note":"no video generated in dry-run mode; no YouTube publishing",
            },indent=2))
            return
        if args.preview_frame is not None:
            render(args.storyboard,args.out,blender=args.blender,preview_frame=args.preview_frame)
            print(f"Preview still rendered: {args.out/'preview.png'}")
            return
        # TTS preflight and synthesis happen BEFORE costly 960-frame render.
        if args.tts == "none":
            create_silent_audio(args.out/"audio",ffmpeg=args.ffmpeg)
            print("Explicit silent mode: preview only, no human narration.",flush=True)
        else:
            create_audio(story,args.out/"audio",provider=args.tts,
                         voice=args.voice or ("Ryan" if args.tts=="qwen" else "af_heart"),
                         model_id=args.model_id,python=args.tts_python,
                         ffmpeg=args.ffmpeg,ffprobe=args.ffprobe)
        print("Audio ready. Starting 960-frame Blender render.",flush=True)
        render(args.storyboard,args.out,blender=args.blender)
        target=compose(story,args.out,ffmpeg=args.ffmpeg)
        report=inspect_video(target,ffprobe=args.ffprobe)
        report["sha256"]=hashlib.sha256(target.read_bytes()).hexdigest()
        report["narration_provider"]=args.tts
        (args.out/"quality.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(f"Draft ready for manual review: {target}")
        print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
