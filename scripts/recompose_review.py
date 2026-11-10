"""Caption/encoding review without re-running Blender's 960 frames or Qwen.

Requires existing output/water_tower/frames and audio/narration.wav.
Writes a new review run and syncs it via the existing guarded Drive path.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shortforge.contract import load_storyboard
from shortforge.video import compose,inspect_video
from scripts.one_click_review import copy_if, iso_now, latest_git_sha, stamp, sync_bundle

def recompose(*, drive:Path|None, storyboard:Path|None=None, out:Path|None=None)->int:
    source=(storyboard or ROOT/"examples"/"water_tower_40s.json").resolve()
    dest=(out or ROOT/"output"/"water_tower").resolve()
    frames=dest/"frames"
    audio=dest/"audio"/"narration.wav"
    for key in ("frame_000001.png","frame_000960.png"):
        if not (frames/key).is_file():
            raise FileNotFoundError(f"Missing Blender frames: {frames/key}. Generate a full draft first.")
    if not audio.is_file():
        raise FileNotFoundError(f"Missing narration: {audio}")
    begin=time.perf_counter()
    story=load_storyboard(source)
    video=compose(story,dest)
    report=inspect_video(video)
    report["sha256"]=hashlib.sha256(video.read_bytes()).hexdigest()
    report["recompose_only"]=True
    report["storyboard"]=source.name
    (dest/"quality.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    elapsed=round(time.perf_counter()-begin,2)
    folder=ROOT/"output"/"review_runs"/(stamp()+"-caption-"+__import__("os").urandom(3).hex())
    folder.mkdir(parents=True)
    for file in ("draft.mp4","quality.json","scene_manifest.json","contact_sheet.png"):
        copy_if(dest/file,folder/file)
    for file in ("captions.ass","captions.json"):
        copy_if(dest/"captions"/file,folder/file)
    manifest={
        "schema_version":2, "run_id":folder.name,
        "created_utc":iso_now(),"git_sha":latest_git_sha(),
        "status":"ready_for_review", "mode":"caption_recompose",
        "stages":[{"stage":"recompose","status":"ok","exit_code":0,
                   "duration_sec":elapsed}],
        "generated":{"draft.mp4":True,"quality.json":True,
                     "captions.ass":(folder/"captions.ass").exists()},
        "youtube_publishing":False,
        "note":"Only captions and FFmpeg recomposed; no Blender frames or narration regenerated."
    }
    (folder/"run_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    (folder/"READ_ME_FIRST.txt").write_text(
        f"ShortForge caption revision: {folder.name}\n"
        f"FFmpeg recompose {elapsed}s. Blender and Qwen skipped.\n"
        "Review newly wrapped captions in draft.mp4, especially near 30s.\n"
        "No YouTube publishing.\n",encoding="utf-8"
    )
    result=sync_bundle(folder,drive)
    print(json.dumps({"recomposition_seconds":elapsed,"video":str(video),
                      "quality":report,"sync":result},indent=2),flush=True)
    return 0 if result.get("status")=="synced" else 2


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--drive",type=Path)
    p.add_argument("--storyboard",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    return recompose(drive=a.drive,storyboard=a.storyboard,out=a.out)


if __name__=="__main__":
    raise SystemExit(main())
