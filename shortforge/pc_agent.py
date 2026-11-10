"""Opt-in local ShortForge PC diagnostics and allowlisted task runner.

No remote connection, no network listener, no arbitrary shell commands or uploads.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
CONFIG = ROOT / ".shortforge.local.json"
ALLOWED = {"doctor", "preview", "tests", "full"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def find_blender(explicit: str | None = None) -> str | None:
    """Find standard Windows installs, registry App Paths, or a portable executable."""
    choices: list[str] = []
    if explicit and explicit != "blender":
        choices.append(explicit)
    if CONFIG.is_file():
        try:
            saved = json.loads(CONFIG.read_text(encoding="utf-8"))
            if isinstance(saved.get("blender"), str):
                choices.append(saved["blender"])
        except (ValueError, OSError, AttributeError):
            pass
    if os.environ.get("SHORTFORGE_BLENDER"):
        choices.append(os.environ["SHORTFORGE_BLENDER"])
    found = shutil.which("blender")
    if found:
        choices.append(found)
    installed: list[Path] = []
    for env in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if not base:
            continue
        p = Path(base)
        for directory in (p / "Blender Foundation", p / "Programs" / "Blender Foundation"):
            if directory.is_dir():
                installed.extend(directory.glob("Blender*/blender.exe"))
                installed.append(directory / "Blender" / "blender.exe")
        if "ProgramFiles" in env:
            installed.append(p / "Steam" / "steamapps" / "common" / "Blender" / "blender.exe")
    installed.extend((ROOT / "tools" / "blender").glob("*/blender.exe"))
    if os.name == "nt":
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\blender.exe") as k:
                        value, _ = winreg.QueryValueEx(k, "")
                        choices.append(str(value).strip('"'))
                except OSError:
                    pass
        except ImportError:
            pass
    # Prefer explicitly configured/PATH locations, else newest version folder.
    choices.extend(str(p) for p in sorted(installed, key=lambda p: str(p.parent).casefold(), reverse=True))
    for candidate in choices:
        p = Path(candidate).expanduser()
        if p.is_file():
            return str(p.resolve())
    return None


def probe(command: list[str], timeout: int = 30) -> dict:
    try:
        p = subprocess.run(command, capture_output=True, text=True, errors="replace",
                           timeout=timeout, check=False)
        return {"ok": p.returncode == 0, "returncode": p.returncode,
                "stdout_tail": p.stdout[-1500:], "stderr_tail": p.stderr[-1500:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def doctor(blender_override: str | None = None, voice: str | None = None) -> dict:
    """Local diagnostic report. Never includes secrets or complete environment variables."""
    executable = find_blender(blender_override)
    result = {
        "timestamp_utc": now(),
        "platform": {"system": platform.system(), "release": platform.release(),
                     "architecture": platform.machine()},
        "python_version": platform.python_version(),
        "tools": {},
        "disk_free_gb": round(shutil.disk_usage(ROOT).free / (1024**3), 1),
    }
    for name in ("blender", "ffmpeg", "ffprobe", "piper", "git", "nvidia-smi"):
        path = executable if name == "blender" else shutil.which(name)
        detail = {"found": bool(path), "path": path}
        if path:
            if name == "blender":
                detail["version"] = probe([path, "--version"], 20)
                detail["headless"] = probe([
                    path, "--background", "--factory-startup",
                    "--python-exit-code", "7", "--python-expr",
                    "import bpy; print('SHORTFORGE_BLENDER_OK', bpy.app.version_string)"
                ], 90)
                detail["headless_ok"] = (
                    detail["headless"].get("ok", False) and
                    "SHORTFORGE_BLENDER_OK" in detail["headless"].get("stdout_tail", "")
                )
            elif name == "nvidia-smi":
                detail["gpu"] = probe(
                    [path, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], 15)
            else:
                detail["version"] = probe(
                    [path, "-version" if name in ("ffmpeg", "ffprobe") else "--version"], 15)
        result["tools"][name] = detail
    model = Path(voice).expanduser() if voice else None
    result["voice_model"] = {
        "provided": bool(model),
        "onnx_exists": bool(model and model.is_file()),
        "config_exists": bool(model and Path(str(model) + ".json").is_file())
    }
    tools = result["tools"]
    result["ready_preview"] = bool(tools["blender"].get("headless_ok"))
    result["ready_full"] = bool(
        result["ready_preview"] and
        all(tools[n]["found"] for n in ("piper", "ffmpeg", "ffprobe")) and
        result["voice_model"]["onnx_exists"] and result["voice_model"]["config_exists"]
    )
    hints = []
    if not executable:
        hints.append("Blender not found. Install Blender 4.5 LTS or pass --blender with the full blender.exe path.")
    elif not result["ready_preview"]:
        hints.append("Blender found but failed headless probe. Inspect tools.blender.headless.")
    if not tools["ffmpeg"]["found"] or not tools["ffprobe"]["found"]:
        hints.append("FFmpeg/ffprobe not found. Add their bin directory to PATH before full rendering.")
    if not tools["piper"]["found"]:
        hints.append("Piper CLI not found. It is only required for the full narrated video.")
    if not model:
        hints.append("Full rendering needs --voice path/to/english.onnx and its .onnx.json config.")
    result["hints"] = hints
    return result


def scoped_path(base: Path, path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    if not p.is_relative_to(base.resolve()):
        raise ValueError(f"Path outside permitted folder: {p}")
    return p


def validate_job(job: dict) -> dict:
    if not isinstance(job, dict) or job.get("version") != 1 or job.get("task") not in ALLOWED:
        raise ValueError("Expected a version 1 doctor/preview/tests/full job")
    if set(job) - {"version", "task", "blender", "voice", "storyboard", "out", "preview_frame"}:
        raise ValueError("Unsupported job fields; shell commands are forbidden")
    if "storyboard" in job:
        scoped_path(ROOT / "examples", job["storyboard"])
    if "out" in job:
        scoped_path(OUTPUT, job["out"])
    if "preview_frame" in job and (
        type(job["preview_frame"]) is not int or not 1 <= job["preview_frame"] <= 960
    ):
        raise ValueError("preview_frame must be an integer from 1 to 960")
    return job


def event(path: Path, action: str, **data) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp_utc": now(), "event": action, **data}) + "\n")


def tail(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 32768))
        return f.read().decode("utf-8", errors="replace").splitlines()[-25:]


def run_task(task: str, *, blender: str | None = None, voice: str | None = None,
             storyboard: str = "examples/water_tower_40s.json",
             out: str = "output/water_tower", preview_frame: int = 480) -> tuple[dict, Path]:
    validate_job({"version": 1, "task": task, "storyboard": storyboard,
                  "out": out, "preview_frame": preview_frame})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logdir = OUTPUT / "diagnostics" / (stamp + "-" + task + "-" + uuid.uuid4().hex[:6])
    logdir.mkdir(parents=True, exist_ok=False)
    events = logdir / "events.jsonl"
    event(events, "started", task=task)
    information = doctor(blender, voice)
    (logdir / "doctor.json").write_text(json.dumps(information, indent=2) + "\n", encoding="utf-8")
    command = None
    target = None
    error = None
    code = None
    if task == "tests":
        command = [sys.executable, "-m", "pytest", "-q"]
    elif task == "preview":
        if not information["ready_preview"]:
            error = "Blender not ready for headless rendering. Open doctor.json."
        else:
            target = scoped_path(OUTPUT, out) / "preview.png"
            command = [sys.executable, "-m", "shortforge.cli", "render",
                       str(scoped_path(ROOT / "examples", storyboard)),
                       "--out", str(target.parent),
                       "--blender", information["tools"]["blender"]["path"],
                       "--preview-frame", str(preview_frame)]
    elif task == "full":
        if not information["ready_full"]:
            error = "Missing full-render prerequisites. Open doctor.json."
        else:
            target = scoped_path(OUTPUT, out) / "draft.mp4"
            command = [sys.executable, "-m", "shortforge.cli", "run",
                       str(scoped_path(ROOT / "examples", storyboard)),
                       "--out", str(target.parent),
                       "--blender", information["tools"]["blender"]["path"],
                       "--voice", str(Path(voice).expanduser().resolve())]
    if command:
        event(events, "process_start", argv=command)
        print("Running task:", task, "\nWriting logs to:", logdir, flush=True)
        try:
            with (logdir / "stdout.log").open("w", encoding="utf-8") as stdout:
                with (logdir / "stderr.log").open("w", encoding="utf-8") as stderr:
                    process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
                    try:
                        code = process.wait()
                    except KeyboardInterrupt:
                        process.terminate()
                        try:
                            process.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        raise
            if code != 0:
                error = "Subprocess failed with exit code " + str(code)
            elif target and (not target.is_file() or target.stat().st_size == 0):
                error = "Expected output missing: " + str(target)
        except (OSError, KeyboardInterrupt) as exc:
            error = type(exc).__name__ + ": " + str(exc)
        event(events, "process_end", exit_code=code, error=error)
    status = ("failed" if error else
              "needs_setup" if task == "doctor" and not information["ready_preview"] else "ok")
    summary = {
        "timestamp_utc": now(), "task": task, "status": status,
        "exit_code": code, "error": error,
        "ready_preview": information["ready_preview"],
        "ready_full": information["ready_full"],
        "blender": information["tools"]["blender"]["path"],
        "generated_file": str(target) if target and target.is_file() else None,
        "diagnostics_directory": str(logdir),
        "stdout_tail": tail(logdir / "stdout.log"),
        "stderr_tail": tail(logdir / "stderr.log"),
        "hints": information["hints"],
        "note": "Local-only. Review logs before sharing; paths can contain account names.",
    }
    (logdir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    event(events, "finished", status=status)
    return summary, logdir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local ShortForge diagnostics and safe task runner")
    sub = parser.add_subparsers(dest="task", required=True)
    for name in ("doctor", "preview", "tests", "full"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--blender")
        cmd.add_argument("--voice")
        if name in ("preview", "full"):
            cmd.add_argument("--storyboard", default="examples/water_tower_40s.json")
            cmd.add_argument("--out", default="output/water_tower")
        if name == "preview":
            cmd.add_argument("--frame", type=int, default=480)
    job_cmd = sub.add_parser("job")
    job_cmd.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    if args.task == "job":
        data = validate_job(json.loads(args.manifest.read_text(encoding="utf-8")))
        task = data["task"]
        options = {"blender": data.get("blender"), "voice": data.get("voice"),
                   "storyboard": data.get("storyboard", "examples/water_tower_40s.json"),
                   "out": data.get("out", "output/water_tower"),
                   "preview_frame": data.get("preview_frame", 480)}
    else:
        task = args.task
        options = {"blender": args.blender, "voice": args.voice,
                   "storyboard": getattr(args, "storyboard", "examples/water_tower_40s.json"),
                   "out": getattr(args, "out", "output/water_tower"),
                   "preview_frame": getattr(args, "frame", 480)}
    try:
        summary, folder = run_task(task, **options)
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({k: summary[k] for k in (
        "task", "status", "ready_preview", "ready_full", "error", "blender",
        "generated_file", "diagnostics_directory")}, indent=2))
    print("Detailed JSON log:", folder / "summary.json")
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
