"""Low-overhead, dependency-free system telemetry for local ShortForge jobs.

Sampling runs only during user-invoked tasks. No sockets or telemetry upload.
Unknown CPU/GPU metrics are null, never invented zeros.
"""
from __future__ import annotations
from datetime import datetime, timezone
import ctypes
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import time


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _windows_cpu_ticks():
    if os.name != "nt":
        return None
    from ctypes import wintypes
    idle, kernel, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
    if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
        return None
    def ticks(f):
        return (f.dwHighDateTime << 32) | f.dwLowDateTime
    return ticks(idle), ticks(kernel), ticks(user)


def _windows_memory():
    if os.name != "nt":
        return None
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return {"ram_used_pct": status.dwMemoryLoad,
            "ram_available_gb": round(status.ullAvailPhys / 2**30, 2)}


def _gpu():
    binary = shutil.which("nvidia-smi")
    if not binary:
        return None
    fields = ("utilization.gpu", "memory.used", "memory.total", "temperature.gpu", "power.draw")
    try:
        proc = subprocess.run(
            [binary, "--query-gpu=" + ",".join(fields), "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=5, check=False,
        )
        if proc.returncode:
            return None
        first = proc.stdout.splitlines()[0].split(",")
        parsed = []
        for v in first:
            try:
                parsed.append(float(v.strip()))
            except ValueError:
                parsed.append(None)
        return {
            "gpu_util_pct": parsed[0], "gpu_mem_used_mb": parsed[1],
            "gpu_mem_total_mb": parsed[2], "gpu_temp_c": parsed[3],
            "gpu_power_w": parsed[4],
        }
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


class Sampler:
    def __init__(self, path: Path, interval_sec: float = 3):
        self.path = path
        self.interval_sec = max(1.0, interval_sec)
        self.previous_ticks = None
        self.previous_time = None
        self.last_log_size = None
        self.last_log_progress = None
        self.samples = []

    def sample(self, *, stage: str, log_file: Path | None = None, force=False):
        current = time.monotonic()
        if not force and self.previous_time is not None and current - self.previous_time < self.interval_sec:
            return
        ticks = _windows_cpu_ticks()
        cpu_pct = None
        if ticks is not None and self.previous_ticks is not None:
            idle = ticks[0] - self.previous_ticks[0]
            total = (ticks[1] - self.previous_ticks[1]) + (ticks[2] - self.previous_ticks[2])
            cpu_pct = round(max(0, min(100, (total - idle) * 100 / total)), 1) if total > 0 else None
        self.previous_ticks, self.previous_time = ticks, current
        mem = _windows_memory() or {}
        gpu = _gpu() or {}
        size = None
        if log_file and log_file.exists():
            try:
                size = log_file.stat().st_size
            except OSError:
                pass
        if size != self.last_log_size:
            self.last_log_progress = current
        self.last_log_size = size
        sample = {
            "timestamp_utc": iso_now(), "stage": stage,
            "elapsed_no_new_stdout_sec": round(current - self.last_log_progress, 1)
                 if self.last_log_progress is not None else None,
            "stdout_bytes": size,
            "cpu_system_pct": cpu_pct,
            **mem, **gpu,
        }
        self.samples.append(sample)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(sample) + "\n")

    def report(self, *, stage_times: dict | None = None) -> dict:
        data = {}
        for key in ("cpu_system_pct", "ram_used_pct", "gpu_util_pct", "gpu_mem_used_mb",
                    "gpu_temp_c", "gpu_power_w"):
            vals = [v[key] for v in self.samples if isinstance(v.get(key), (int, float))]
            if vals:
                data[key] = {"min": round(min(vals), 2), "mean": round(statistics.mean(vals), 2),
                             "max": round(max(vals), 2), "samples": len(vals)}
            else:
                data[key] = None
        patterns = []
        if data["gpu_util_pct"] is None:
            patterns.append({"kind":"gpu_telemetry_unavailable","severity":"info",
                             "advice":"NVIDIA metrics could not be sampled. Inspect nvidia-smi and PATH."})
        elif data["gpu_util_pct"]["mean"] < 8:
            patterns.append({"kind":"gpu_mostly_idle","severity":"info",
                             "advice":"Check whether Qwen PyTorch has CUDA enabled; Blender Eevee may also be CPU/IO-limited."})
        stall_samples = [s for s in self.samples
                         if s["elapsed_no_new_stdout_sec"] is not None
                         and s["elapsed_no_new_stdout_sec"] >= 30]
        if stall_samples:
            patterns.append({"kind":"stdout_idle_30s","severity":"warning",
                             "samples":len(stall_samples),
                             "advice":"Long gap in log output; may be model loading or frame processing, not necessarily a hang."})
        if data["ram_used_pct"] and data["ram_used_pct"]["max"] > 90:
            patterns.append({"kind":"high_ram_usage","severity":"warning",
                             "advice":"Close memory-heavy applications or reduce parallel workloads."})
        return {
            "schema_version":1, "sampling_interval_seconds": self.interval_sec,
            "sample_count":len(self.samples), "stage_seconds": stage_times or {},
            "metrics":data, "patterns":patterns,
            "note":"System-level samples. CPU-only TTS latency and spoken-audio length are different measurements."
        }
