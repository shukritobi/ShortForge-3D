"""Loopback-only, single-GPU job dashboard over the existing CLI.

No cloud service, publication route, arbitrary shell command or external file access.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,unquote
from .contract import validate_storyboard
from .topic_packs import PACKS,build_story
from .telemetry import Sampler
from .video import inspect_video
from .render_cache import renderer_sources, shot_keys

ROOT=Path(__file__).resolve().parents[1]
PROJECTS=ROOT/"output"/"dashboard_projects"
LOCK=threading.Lock()
IO_LOCK=threading.Lock()
ACTIVE=None


def write_json(path,value):
    with IO_LOCK:
        temp=path.with_suffix(".tmp")
        temp.write_text(json.dumps(value,indent=2),encoding="utf-8")
        for attempt in range(5):
            try:
                temp.replace(path)
                return
            except PermissionError:
                if attempt==4:raise
                time.sleep(.025*(attempt+1))


def read_json(path):
    with IO_LOCK:
        return json.loads(path.read_text(encoding="utf-8"))


def project_path(ident):
    if not isinstance(ident,str) or not re.fullmatch(r"[a-f0-9]{12}",ident):
        raise ValueError("Invalid project ID")
    p=PROJECTS/ident
    if p.resolve().parent!=PROJECTS.resolve() or not (p/"storyboard.json").is_file():
        raise ValueError("Project not found")
    return p


def revision(p):
    h=hashlib.sha256((p/"storyboard.json").read_bytes())
    for folder in (ROOT/"shortforge",ROOT/"scripts"):
        for source in sorted(folder.glob("*.py")):
            h.update(source.read_bytes())
    return h.hexdigest()


def visual_keys(story):
    # Match the model dependencies fingerprinted by Blender. Audio and
    # subtitle-only changes do not invalidate the studio's visual receipt.
    source=hashlib.sha256()
    for path in renderer_sources(story["scene_template"]):
        source.update((ROOT/path).read_bytes())
    return shot_keys(story,source.hexdigest())


def command_for(p,stage,tts="qwen"):
    story=json.loads((p/"storyboard.json").read_text(encoding="utf-8"))
    command=[sys.executable,"-u","-m","shortforge.cli"]
    if stage=="preview":
        count=story["duration"]*story["fps"]
        return command+["render",str(p/"storyboard.json"),"--out",str(p),"--preview-frames",
                        ",".join(str(round(count*i/7)) for i in range(1,7))]
    if stage not in ("audio","full","compose"):
        raise ValueError("Unknown stage")
    if tts not in ("qwen","none"):
        raise ValueError("Choose Qwen narration or a silent technical export")
    policy=story.get("narration_timing")
    if stage=="audio" and tts=="qwen" and policy in ("native","uniform"):
        return [sys.executable,"-u",str(ROOT/"scripts"/"measure_narration.py"),str(p/"storyboard.json"),
                "--out",str(p),"--extend-to-fit"]
    if stage=="full":
        approval=p/"approval.json"
        if not approval.is_file() or json.loads(approval.read_text()).get("revision")!=revision(p):
            raise ValueError("Approve the current preview before full rendering")
        if tts=="qwen" and policy in ("native","uniform"):
            voice=p/"audio"/"voice_manifest.json"
            measured=p/"audio"/"tts_input.json"
            if (not voice.is_file() or not measured.is_file() or
                read_json(voice).get("timing_policy")!=policy or read_json(measured)!=story):
                raise ValueError("Check narration first to fit shots to the natural voice, then preview and approve the timed storyboard")
    if stage=="compose":
        receipt=p/"rendered_visuals.json"
        if not receipt.is_file() or read_json(receipt)!=visual_keys(story):
            raise ValueError("Render this visual revision before recomposing captions")
    command += [("run" if stage=="full" else stage),str(p/"storyboard.json"),"--out",str(p)]
    if stage in ("audio","full"):
        command += ["--tts",tts]
    return command


def worker(p,stage,command):
    global ACTIVE
    started=time.time()
    run=p/"history"/(time.strftime("%Y%m%dT%H%M%S",time.gmtime())+"-"+uuid.uuid4().hex[:6])
    sampler=Sampler(run/"system_samples.jsonl")
    record={"stage":stage,"status":"running","started":started,"run":run.name}
    try:
        run.mkdir(parents=True)
        record["revision"]=revision(p)
        write_json(p/"job.json",record)
        story=json.loads((p/"storyboard.json").read_text(encoding="utf-8"))
        artifact={"preview":"contact_sheet.png","full":"draft.mp4","compose":"draft.mp4"}.get(stage)
        output=p/artifact if artifact else None
        old_timestamp=output.stat().st_mtime_ns if output and output.is_file() else None
        if stage=="preview":
            write_json(p/"preview_review.json",{"status":"generating"})
            write_json(p/"approval.json",{"decision":"preview_pending"})
        if stage=="full":
            write_json(p/"rendered_visuals.json",None)
        with (run/"job.log").open("w",encoding="utf-8") as log:
            env={**os.environ,"SHORTFORGE_STUDIO_JOB_LOCK":str(PROJECTS/".gpu.lock")}
            child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env)
            while child.poll() is None:
                sampler.sample(stage=stage,log_file=run/"job.log")
                time.sleep(2)
        record.update(status="passed" if child.returncode==0 else "failed",exit_code=child.returncode)
        if child.returncode==0 and output:
            if not output.is_file() or output.stat().st_mtime_ns==old_timestamp:
                raise RuntimeError(f"Job did not produce a fresh {artifact}")
            if stage in ("full","compose"):
                inspect_video(output,expected_duration=story["duration"],expected_fps=story["fps"],
                              expected_resolution=story["resolution"])
            if stage=="full":
                write_json(p/"rendered_visuals.json",visual_keys(story))
        for pattern in ("preview_*.png","contact_sheet.png","draft.mp4","scene_manifest.json","quality.json"):
            for artifact in p.glob(pattern):shutil.copy2(artifact,run/artifact.name)
        if stage=="preview" and child.returncode==0:
            write_json(p/"preview_review.json",{"revision":record["revision"],"status":"awaiting_review"})
    except Exception as exc:
        record.update(status="failed",error=str(exc))
    finally:
        record["elapsed_sec"]=round(time.time()-started,2)
        try:
            write_json(p/"job.json",record)
            if run.is_dir():
                write_json(run/"job.json",record)
                write_json(run/"performance.json",sampler.report(stage_times={stage:record["elapsed_sec"]}))
        finally:
            with LOCK:ACTIVE=None


def mutate(data):
    global ACTIVE
    if not isinstance(data,dict):
        raise ValueError("Expected a JSON object")
    action=data.get("action")
    if action=="create":
        story=build_story(data.get("topic","solar_home"),int(data.get("duration",120)),
                          fps=int(data.get("fps",24)),profile=data.get("profile","draft"))
        ident=uuid.uuid4().hex[:12]
        p=PROJECTS/ident
        p.mkdir(parents=True)
        write_json(p/"storyboard.json",story)
        return {"id":ident}
    p=project_path(data.get("id"))
    with LOCK:
        if ACTIVE is not None:
            raise ValueError("One GPU job is already active; wait before editing or launching")
        if action=="save":
            story=validate_storyboard(data["story"])
            history=p/"history"/str(time.time_ns())
            history.mkdir(parents=True)
            (history/"storyboard.json").write_bytes((p/"storyboard.json").read_bytes())
            write_json(p/"storyboard.json",story)
        elif action in ("approve","reject"):
            review=p/"preview_review.json"
            if not review.is_file() or json.loads(review.read_text()).get("revision")!=revision(p):
                raise ValueError("Generate a preview of this revision first")
            write_json(p/"approval.json",{"revision":revision(p) if action=="approve" else None,
                                         "decision":action,"time":time.time()})
        elif action in ("preview","audio","full","compose"):
            command=command_for(p,action,data.get("tts","qwen"))
            ACTIVE=p.name
            threading.Thread(target=worker,args=(p,action,command),daemon=True).start()
        else:
            raise ValueError("Unknown action")
    return {"ok":True}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def reply(self,value,status=200):
        body=json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        host=self.headers.get("Host","")
        allowed={f"127.0.0.1:{self.server.server_port}",f"localhost:{self.server.server_port}"}
        origin=self.headers.get("Origin")
        return host in allowed and (not origin or origin in {"http://"+h for h in allowed})

    def do_POST(self):
        if not self.local_request():return self.reply({"error":"Local origin required"},403)
        if urlparse(self.path).path!="/api":return self.reply({"error":"Not found"},404)
        try:
            size=int(self.headers.get("Content-Length",0))
            if not 0<size<=1000000:raise ValueError("Invalid request size")
            self.reply(mutate(json.loads(self.rfile.read(size))))
        except (ValueError,KeyError,TypeError,OSError) as exc:self.reply({"error":str(exc)},400)

    def do_GET(self):
        if not self.local_request():return self.reply({"error":"Local host required"},403)
        path=unquote(urlparse(self.path).path)
        if path=="/api":
            projects=[]
            for p in sorted(PROJECTS.glob("*"),key=lambda p:p.stat().st_mtime,reverse=True):
                if not (p/"storyboard.json").is_file():continue
                job=read_json(p/"job.json") if (p/"job.json").exists() else {}
                if job.get("status")=="running" and ACTIVE!=p.name:job["status"]="interrupted"
                log=p/"history"/job.get("run","missing")/"job.log"
                tail=""
                if log.is_file():
                    with log.open("rb") as stream:
                        stream.seek(max(0,log.stat().st_size-12000));tail=stream.read().decode("utf-8",errors="replace")
                projects.append({"id":p.name,"story":read_json(p/"storyboard.json"),
                                 "job":job,"log":tail,"files":[str(f.relative_to(p)).replace("\\","/")
                                      for f in p.rglob("*") if f.is_file() and f.suffix in (".json",".mp4",".png")
                                      and "frames" not in f.parts and "cache_archive" not in f.parts]})
            return self.reply({"topics":list(PACKS),"projects":projects,"active":ACTIVE})
        if path=="/":
            target=ROOT/"apps"/"dashboard"/"index.html"
        else:
            match=re.fullmatch(r"/files/([a-f0-9]{12})/(.+)",path)
            if not match:
                return self.reply({"error":"Not found"},404)
            try:
                project=project_path(match[1]).resolve()
                target=(project/match[2]).resolve()
            except (ValueError,OSError):
                return self.reply({"error":"Not found"},404)
            if not target.is_relative_to(project) or target.suffix.lower() not in {".json",".png",".mp4",".log"}:
                return self.reply({"error":"Not found"},404)
        if not target.is_file():return self.reply({"error":"Not found"},404)
        size=target.stat().st_size
        start,end=0,size-1
        request_range=self.headers.get("Range") if target.suffix==".mp4" else None
        if request_range:
            match=re.fullmatch(r"bytes=(\d{1,20})-(\d{0,20})",request_range)
            if match:
                start=int(match[1])
                end=min(end,int(match[2])) if match[2] else end
            if not match or start>end:
                self.send_response(416)
                self.send_header("Content-Range",f"bytes */{size}")
                self.end_headers()
                return
        self.send_response(206 if request_range else 200)
        if target.suffix==".mp4":self.send_header("Accept-Ranges","bytes")
        if request_range:self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
        self.send_header("Content-Type",mimetypes.guess_type(target)[0] or "application/octet-stream")
        self.send_header("Content-Length",str(end-start+1))
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        with target.open("rb") as stream:
            stream.seek(start)
            while stream.tell()<=end and (chunk:=stream.read(min(1024*1024,end-stream.tell()+1))):
                try:self.wfile.write(chunk)
                except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):break


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    PROJECTS.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",args.port),Handler)
    print(f"ShortForge local review: http://127.0.0.1:{args.port}",flush=True)
    server.serve_forever()


if __name__=="__main__":main()
