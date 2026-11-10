"""Deterministic beat-constrained captions (no cloud transcription required).

For Piper audio, each beat is separately fitted to its timeline window.
Within each beat, token timings are estimated by text length. They are NOT
speech-recognition word alignment and should be reviewed in the draft.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from .contract import validate_storyboard


def cues(story: dict, words_per_cue: int = 4) -> list[dict]:
    validate_storyboard(story)
    result = []
    for beat in story["beats"]:
        words = beat["narration"].split()
        chunks = [words[i:i+words_per_cue] for i in range(0,len(words),words_per_cue)]
        weights = [max(1,len("".join(chunk))) for chunk in chunks]
        total = sum(weights)
        cursor = float(beat["start"])
        for i,(chunk,weight) in enumerate(zip(chunks,weights)):
            end = (beat["end"] if i == len(chunks)-1 else cursor + (beat["end"]-beat["start"])*weight/total)
            # Subsequent chunks share this beat's original total duration.
            # Maintain absolute position using cumulative weights instead.
            consumed = sum(weights[:i+1])
            end = float(beat["start"]) + (beat["end"]-beat["start"])*consumed/total
            result.append({"start":round(cursor,3),"end":round(end,3),"text":" ".join(chunk),"beat_id":beat["id"]})
            cursor = end
    return result


def ass_time(seconds: float) -> str:
    centis = round(seconds*100)
    hours,rest = divmod(centis,360000)
    minutes,rest = divmod(rest,6000)
    secs,cs = divmod(rest,100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def escape_ass(text: str) -> str:
    return re.sub(r"[{}]", "", text).replace("\\","").replace("\n"," ")


def write_captions(story: dict, dest: str | Path) -> tuple[Path,Path]:
    dest = Path(dest)
    dest.mkdir(parents=True,exist_ok=True)
    items = cues(story)
    json_path = dest/"captions.json"
    json_path.write_text(json.dumps(items,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    # ASS coordinates use the 720 x 1280 reference frame.
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,54,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,1,2,60,60,205,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 0,{ass_time(x['start'])},{ass_time(x['end'])},Default,,0,0,0,,{escape_ass(x['text'])}" for x in items]
    ass_path = dest/"captions.ass"
    ass_path.write_text(header+"\n".join(events)+"\n",encoding="utf-8")
    return json_path, ass_path
