"""Verify that fitting only pads a take, without altering its spoken samples."""
import argparse
import json
from pathlib import Path
import wave


def verify(project):
    story=json.loads((project/"storyboard.json").read_text(encoding="utf-8"))
    rows=[]
    for index,beat in enumerate(story["beats"]):
        folder=project/"audio"/"beats"
        with wave.open(str(folder/f"beat_{index:02d}_raw.wav"),"rb") as raw:
            raw_frames=raw.getnframes()
            data=raw.readframes(raw_frames)
            raw_format=(raw.getframerate(),raw.getnchannels(),raw.getsampwidth())
        with wave.open(str(folder/f"beat_{index:02d}.wav"),"rb") as fitted:
            fitted_format=(fitted.getframerate(),fitted.getnchannels(),fitted.getsampwidth())
            prefix=fitted.readframes(raw_frames)
        rows.append({"beat":beat["id"],"sample_format":raw_format,
                     "spoken_pcm_unchanged":data==prefix and raw_format==fitted_format})
    passed=all(row["spoken_pcm_unchanged"] for row in rows)
    report={"policy":story.get("narration_timing"),"passed":passed,"beats":rows}
    (project/"native_voice_verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    if not passed:
        raise RuntimeError("One or more fitted takes changed their spoken samples")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("project",type=Path)
    args=parser.parse_args()
    report=verify(args.project)
    print(f"Verified {len(report['beats'])} native takes: spoken PCM unchanged")
