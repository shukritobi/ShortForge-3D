"""One-click local review bundle: tests -> Blender keyframes -> narration diagnostics.

Outputs are synced only to the user-selected local Google Drive folder, never
transmitted to a remote server. Full 960-frame render is an explicit mode.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shortforge.telemetry import Sampler, iso_now

OUTPUT = ROOT / "output"
STEPS = ("tests", "review", "audio")
REVIEW_FILES = (
    "contact_sheet.png", "preview.png", "scene_manifest.json",
    "preview_0120.png", "preview_0240.png", "preview_0480.png",
    "preview_0576.png", "preview_0720.png", "preview_0936.png",
)


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def copy_if(source: Path, destination: Path):
    if source.is_file() and source.stat().st_size:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return source.stat().st_size
    return None


def redacted_tail(path: Path, limit=35):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    # Suppress possible tokens accidentally printed by dependencies.
    import re
    value = "\n".join(lines[-limit:])
    for regex in (r"hf_[A-Za-z0-9]{12,}", r"gh[pousr]_[A-Za-z0-9_]{12,}",
                  r"sk-[A-Za-z0-9_-]{16,}"):
        value = re.sub(regex, "[REDACTED]", value)
    return value.splitlines()


def execute(stage, argv, directory: Path, sampler: Sampler):
    stdout, stderr = directory / f"{stage}.stdout.log", directory / f"{stage}.stderr.log"
    begin = time.monotonic()
    with stdout.open("w", encoding="utf-8") as so, stderr.open("w", encoding="utf-8") as se:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=so, stderr=se)
        print(f"[{stage}] PID={process.pid}; logs: {stdout.name}", flush=True)
        while True:
            sampler.sample(stage=stage, log_file=stdout)
            try:
                code = process.wait(timeout=2)
                break
            except subprocess.TimeoutExpired:
                pass
            except KeyboardInterrupt:
                process.terminate()
                raise
        sampler.sample(stage=stage, log_file=stdout, force=True)
    return {
        "stage":stage, "exit_code":code,
        "duration_sec":round(time.monotonic()-begin,2),
        "stdout_tail":redacted_tail(stdout,20),
        "stderr_tail":redacted_tail(stderr,20),
    }


def metrics_for_tts(audio_dir: Path):
    report = audio_dir / "timing_report.json"
    if report.is_file():
        try:
            return json.loads(report.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    return None


def latest_git_sha():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def resolve_drive(path: Path | str | None):
    """Locate the existing Drive workspace; never create a fake new root.

    Windows batch syntax ending in backslash before a closing quote can pass
    a stray quote to Python. Normalize that and inspect actual folder layout.
    """
    candidates = []
    if path:
        raw = str(path).strip().strip('"').strip("'")
        if raw:
            candidates.append(Path(raw).expanduser())
    if os.environ.get("SHORTFORGE_DRIVE"):
        candidates.append(Path(os.environ["SHORTFORGE_DRIVE"].strip().strip('"')).expanduser())
    if os.name == "nt":
        for disk in ("G", "H", "D", "C"):
            candidates.append(Path(f"{disk}:/My Drive/ChatGPT ShortForge 3D"))
    checked = []
    for candidate in candidates:
        try:
            root = candidate.resolve()
            checked.append(str(root))
            if root.is_dir() and (root / "outbox").is_dir():
                return root, checked
        except OSError:
            checked.append(str(candidate))
    return None, checked


def sync_latest_run(drive: Path | str | None, *, run_id: str | None = None,
                    output_root: Path | None = None) -> dict:
    """Recover local reports without rerunning TTS, Blender or tests."""
    root = (output_root or OUTPUT) / "review_runs"
    if not root.is_dir():
        return {"status": "failed", "reason": "No local review_runs directory"}
    if run_id is not None:
        selected = (root / run_id).resolve()
        if not selected.is_relative_to(root.resolve()) or not selected.is_dir():
            return {"status": "failed", "reason": "Unknown run ID"}
    else:
        entries = [p for p in root.iterdir()
                   if p.is_dir() and (p / "run_manifest.json").is_file()]
        if not entries:
            return {"status": "failed", "reason": "No local run manifests found"}
        selected = max(entries, key=lambda p: p.stat().st_mtime)
    if not (selected / "run_manifest.json").is_file():
        return {"status": "failed", "reason": "Run manifest missing", "run": str(selected)}
    result = sync_bundle(selected, drive)
    return {"run_id": selected.name, **result}


def sync_bundle(run: Path, drive: Path | str | None):
    resolved, inspected = resolve_drive(drive)
    if resolved is None:
        return {"status": "sync_failed",
                "reason": "Drive workspace/outbox not found",
                "configured": str(drive) if drive else None,
                "inspected": inspected[-8:],
                "local_run": str(run)}
    drive = resolved
    latest = drive / "outbox" / "latest"
    history = drive / "outbox" / "runs" / run.name
    # Never delete old reviews; keep full per-run logs and small visual/audio assets.
    try:
        latest.mkdir(parents=True, exist_ok=True)
        history.mkdir(parents=True, exist_ok=True)
        # Move the previous latest artefacts aside rather than mixing old video
        # files with a new failed narration attempt. Nothing is deleted.
        archive = drive / "outbox" / "archive" / (stamp() + "-" + os.urandom(2).hex())
        for prior in list(latest.iterdir()):
            archive.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(prior), str(archive / prior.name))
            except OSError:
                pass  # Locked file stays in place; the new run manifest remains authoritative.
        synced = []
        for item in run.iterdir():
            if item.is_file():
                for target in (history / item.name, latest / item.name):
                    if copy_if(item, target) is not None:
                        synced.append(target.name)
            elif item.is_dir() and item.name in ("diagnostics", "voice_samples"):
                for src in item.rglob("*"):
                    if src.is_file():
                        rel = src.relative_to(run)
                        for parent in (history, latest):
                            copy_if(src, parent / rel)
        (latest / "CURRENT_RUN.txt").write_text(
            run.name + "\nFull logs: outbox/runs/" + run.name + "\n",
            encoding="utf-8")
        return {"status":"synced","history":str(history),"latest":str(latest),
                "files":sorted(set(synced))}
    except OSError as exc:
        return {"status":"sync_failed","error":str(exc),"run":str(run)}


def run(*, drive:Path | None, full:bool=False, audio:bool=True) -> int:
    OUTPUT.mkdir(exist_ok=True)
    folder=OUTPUT / "review_runs" / (stamp() + "-" + os.urandom(3).hex())
    folder.mkdir(parents=True)
    sampler=Sampler(folder / "system_samples.jsonl")
    results=[]
    py = sys.executable
    stage_times={}
    water = OUTPUT / "water_tower"
    water.mkdir(exist_ok=True)
    commands=[
        ("tests", [py, "-m", "pytest", "-q"]),
        ("review", [py, "scripts/pc_agent.py", "review"]),
    ]
    if audio:
        commands.append(("audio", [py, "scripts/pc_agent.py", "audio", "--tts", "qwen", "--speaker", "Ryan"]))
    if full:
        commands.append(("full", [py, "scripts/pc_agent.py", "full", "--tts", "qwen", "--speaker", "Ryan"]))
    print("ShortForge review run:", folder.name, flush=True)
    print("Steps:", ", ".join(x[0] for x in commands),flush=True)
    had_failure=False
    for stage, cmd in commands:
        # A failed 5-second narration should not trigger 960-frame Blender rendering.
        if stage == "full" and had_failure:
            results.append({"stage":"full","status":"skipped","reason":"Previous QA stage failed"})
            break
        # Run review even if audio has issues; isolate quality failures.
        result=execute(stage,cmd,folder,sampler)
        stage_times[stage]=result["duration_sec"]
        result["status"]="ok" if result["exit_code"]==0 else "failed"
        results.append(result)
        if result["status"]!="ok":
            had_failure=True
            if stage=="tests":
                break
    review_ok = any(x["stage"]=="review" and x["status"]=="ok" for x in results)
    if review_ok:
        for file in REVIEW_FILES:
            copy_if(water / file, folder / file)
    if full:
        for file in ("draft.mp4","quality.json"):
            if any(r["stage"]=="full" and r["status"]=="ok" for r in results):
                copy_if(water / file, folder / file)
    audio_dir=water/"audio"
    audio_ran = any(x["stage"]=="audio" for x in results)
    if audio and audio_ran:
        # Share narrated audio only after a successful audio QA.
        audio_ok=any(x["stage"]=="audio" and x["status"]=="ok" for x in results)
        if audio_ok:
            for f in ("narration.wav","voice_manifest.json"):
                copy_if(audio_dir / f, folder / f)
        for f in ("timing_report.json","tts_metrics.jsonl"):
            copy_if(audio_dir / f, folder / f)
        # Never attach raw samples from a previous attempt that had no current
        # Qwen beat event. Worker cache hits are explicitly logged too.
        metrics_file = audio_dir / "tts_metrics.jsonl"
        current_beats = set()
        if metrics_file.is_file():
            for line in metrics_file.read_text(encoding="utf-8",errors="replace").splitlines():
                try:
                    event = json.loads(line)
                    if event.get("event") in ("beat_generated","beat_cached"):
                        current_beats.add(str(event.get("beat")))
                except ValueError:
                    pass
        for i, beat in enumerate(range(1,9)):
            if f"{beat:02d}" in current_beats:
                copy_if(audio_dir/"beats"/f"beat_{i:02d}_raw.wav",
                        folder/"voice_samples"/f"beat_{i:02d}_raw.wav")
    # Copy latest pc_agent diagnostics after each phase, not just the last run.
    diagn=OUTPUT/"diagnostics"
    if diagn.exists():
        for result in results:
            phase=result["stage"]
            entries=sorted((p for p in diagn.iterdir() if p.is_dir() and ("-"+phase+"-") in p.name),
                           key=lambda p:p.stat().st_mtime,reverse=True)
            if entries:
                for name in ("doctor.json","summary.json","events.jsonl","stdout.log","stderr.log"):
                    copy_if(entries[0]/name, folder/"diagnostics"/phase/name)
    performance=sampler.report(stage_times=stage_times)
    performance["tts_timing"]=metrics_for_tts(audio_dir) if audio else None
    timing=performance["tts_timing"] or {}
    if timing.get("failed_count",0):
        performance["patterns"].append({
            "kind":"tts_beats_outside_timeline", "severity":"error",
            "failed_count":timing["failed_count"],
            "advice":"Review generated voice samples and edit beat text/timing. Never time-stretch > 1.7x."
        })
    (folder/"performance_report.json").write_text(json.dumps(performance,indent=2)+"\n",encoding="utf-8")
    (folder/"lag_patterns.json").write_text(json.dumps(performance["patterns"],indent=2)+"\n",encoding="utf-8")
    status="needs_review" if had_failure else "ready_for_review"
    output={
        "schema_version":2,"run_id":folder.name,
        "created_utc":iso_now(),"git_sha":latest_git_sha(),
        "status":status,"mode":"full" if full else "review",
        "stages":results,
        "generated":{k:(folder/k).is_file() for k in ("contact_sheet.png","timing_report.json","narration.wav","draft.mp4")},
        "youtube_publishing":False,
    }
    (folder/"run_manifest.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    msg=[
        "SHORTFORGE REVIEW BUNDLE: "+folder.name,
        "Status: "+status,
        "Git commit: "+str(output["git_sha"]),
        "Steps: "+", ".join(f"{s['stage']}={s['status']}" for s in results),
        "Inspect contact_sheet.png, timing_report.json, performance_report.json,",
        "system_samples.jsonl and diagnostics/. Audio may fail QA before MP4 generation.",
        "No YouTube publishing.",
    ]
    (folder/"READ_ME_FIRST.txt").write_text("\n".join(msg)+"\n",encoding="utf-8")
    saved=sync_bundle(folder,drive)
    print(json.dumps({"run_id":folder.name,"status":status,"drive":saved},indent=2),flush=True)
    if saved.get("status") != "synced":
        print("[SYNC ERROR] Review was saved locally, but Drive was not updated. "
              "Run --sync-latest after checking your Drive mount.", flush=True)
        return 2
    return 1 if had_failure else 0


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--drive",type=Path)
    p.add_argument("--full",action="store_true",
                   help="after tests/review/audio QA, generate a full 960-frame draft")
    p.add_argument("--skip-audio",action="store_true")
    p.add_argument("--sync-latest",action="store_true",
                   help="sync an existing local run without regenerating anything")
    p.add_argument("--run-id",type=str,help="optional exact local run folder for recovery")
    args=p.parse_args()
    if args.run_id and not args.sync_latest:
        p.error("--run-id requires --sync-latest")
    if args.sync_latest:
        saved=sync_latest_run(args.drive,run_id=args.run_id)
        print(json.dumps(saved,indent=2),flush=True)
        return 0 if saved.get("status") == "synced" else 2
    return run(drive=args.drive,full=args.full,audio=not args.skip_audio)


if __name__=="__main__":
    raise SystemExit(main())
