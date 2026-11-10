"""Loopback-only, single-GPU job dashboard over the existing CLI.

No cloud service, publication route, arbitrary shell command or external file access.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import mimetypes
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

ROOT=Path(__file__).resolve().parents[1]
PROJECTS=ROOT/"output"/"dashboard_projects"
LOCK=threading.Lock()
ACTIVE=None


def write_json(path,value):
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(value,indent=2),encoding="utf-8")
    temp.replace(path)


def project_path(ident):
    if not isinstance(ident,str) or not re.fullmatch(r"[a-f0-9]{12}",ident):
        raise ValueError("Invalid project ID")
    p=PROJECTS/ident
    if not (p/"storyboard.json").is_file():
        raise ValueError("Project not found")
    return p


def revision(p):
    h=hashlib.sha256((p/"storyboard.json").read_bytes())
    for folder in (ROOT/"shortforge",ROOT/"scripts"):
        for source in sorted(folder.glob("*.py")):
            h.update(source.read_bytes())
    return h.hexdigest()


def command_for(p,stage):
    story=json.loads((p/"storyboard.json").read_text(encoding="utf-8"))
    command=[sys.executable,"-u","-m","shortforge.cli"]
    if stage=="preview":
        count=story["duration"]*story["fps"]
        return command+["render",str(p/"storyboard.json"),"--out",str(p),"--preview-frames",
                        ",".join(str(round(count*i/7)) for i in range(1,7))]
    if stage not in ("audio","full","compose"):
        raise ValueError("Unknown stage")
    if stage=="full":
        approval=p/"approval.json"
        if not approval.is_file() or json.loads(approval.read_text()).get("revision")!=revision(p):
            raise ValueError("Approve the current preview before full rendering")
    return command+[("run" if stage=="full" else stage),str(p/"storyboard.json"),"--out",str(p)]


def worker(p,stage,command):
    global ACTIVE
    started=time.time()
    run=p/"history"/(time.strftime("%Y%m%dT%H%M%S",time.gmtime())+"-"+uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    sampler=Sampler(run/"system_samples.jsonl")
    record={"stage":stage,"status":"running","started":started,"run":run.name,"revision":revision(p)}
    write_json(p/"job.json",record)
    try:
        with (run/"job.log").open("w",encoding="utf-8") as log:
            child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            while child.poll() is None:
                sampler.sample(stage=stage,log_file=run/"job.log")
                time.sleep(2)
        record.update(status="passed" if child.returncode==0 else "failed",exit_code=child.returncode)
        for pattern in ("preview_*.png","contact_sheet.png","draft.mp4","scene_manifest.json","quality.json"):
            for artifact in p.glob(pattern):shutil.copy2(artifact,run/artifact.name)
        if stage=="preview" and child.returncode==0:
            write_json(p/"preview_review.json",{"revision":record["revision"],"status":"awaiting_review"})
    except Exception as exc:
        record.update(status="failed",error=str(exc))
    finally:
        record["elapsed_sec"]=round(time.time()-started,2)
        write_json(run/"job.json",record)
        write_json(p/"job.json",record)
        write_json(run/"performance.json",sampler.report(stage_times={stage:record["elapsed_sec"]}))
        with LOCK:ACTIVE=None


def mutate(data):
    global ACTIVE
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
            command=command_for(p,action)
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
                job=json.loads((p/"job.json").read_text()) if (p/"job.json").exists() else {}
                if job.get("status")=="running" and ACTIVE!=p.name:job["status"]="interrupted"
                log=p/"history"/job.get("run","missing")/"job.log"
                tail=""
                if log.is_file():
                    with log.open("rb") as stream:
                        stream.seek(max(0,log.stat().st_size-12000));tail=stream.read().decode("utf-8",errors="replace")
                projects.append({"id":p.name,"story":json.loads((p/"storyboard.json").read_text()),
                                 "job":job,"log":tail,"files":[str(f.relative_to(p)).replace("\\","/")
                                      for f in p.rglob("*") if f.is_file() and f.suffix in (".json",".mp4",".png")
                                      and "frames" not in f.parts and "cache_archive" not in f.parts]})
            return self.reply({"topics":list(PACKS),"projects":projects,"active":ACTIVE})
        target=ROOT/"apps"/"dashboard"/"index.html" if path=="/" else (PROJECTS/path.removeprefix("/files/"))
        if path!="/" and (not path.startswith("/files/") or not target.resolve().is_relative_to(PROJECTS.resolve())):
            return self.reply({"error":"Not found"},404)
        if not target.is_file():return self.reply({"error":"Not found"},404)
        self.send_response(200)
        self.send_header("Content-Type",mimetypes.guess_type(target)[0] or "application/octet-stream")
        self.send_header("Content-Length",str(target.stat().st_size))
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        with target.open("rb") as stream:
            while chunk:=stream.read(1024*1024):
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
