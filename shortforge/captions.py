"""Deterministic beat-constrained captions (no cloud transcription required).

For Piper audio, each beat is separately fitted to its timeline window.
Within each beat, token timings are estimated by text length. They are NOT
speech-recognition word alignment and should be reviewed in the draft.
"""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
from .contract import validate_storyboard


def cues(story: dict, words_per_cue: int = 3) -> list[dict]:
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


def safe_ass_caption(text: str, max_chars: int = 22) -> str:
    """Wrap cues to fit portrait-safe margins, without chopping text edges.

    Splits between words (not characters) and intentionally rejects cues
    demanding >2 subtitle lines. The caller can shorten its cue grouping.
    """
    words = text.split()
    lines = []
    current = []
    for word in words:
        prospective = " ".join([*current,word])
        if current and len(prospective) > max_chars:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if len(lines) > 2 or any(len(line) > max_chars for line in lines):
        raise ValueError(f"Caption too long for portrait frame: {text!r}")
    return r"\N".join(escape_ass(line) for line in lines)


def checked_timing(story, timing):
    """Allow alternate timing for the same words within their own beats."""
    expected = cues(story)
    if not isinstance(timing, list) or len(timing) != len(expected):
        raise ValueError("Caption timing must include every storyboard cue")
    beats = {beat["id"]: beat for beat in story["beats"]}
    previous_end = 0
    result = []
    for cue, source in zip(timing, expected):
        if not isinstance(cue, dict) or any(cue.get(k) != source[k] for k in ("text", "beat_id")):
            raise ValueError("Caption timing text does not match the storyboard")
        beat = beats[source["beat_id"]]
        start, end = cue.get("start"), cue.get("end")
        if (not all(type(t) in (int, float) and math.isfinite(t) for t in (start, end)) or
                not max(previous_end, beat["start"]) <= start < end <= beat["end"] or
                round(start*100) >= round(end*100)):
            raise ValueError(f"Invalid caption timing for {beat['id']}")
        result.append({**source,"start":start,"end":end,"alignment":"external_review_timing"})
        previous_end = end
    return result


def write_captions(story: dict, dest: str | Path, *, audio_dir=None, timing=None) -> tuple[Path,Path]:
    dest = Path(dest)
    dest.mkdir(parents=True,exist_ok=True)
    if timing is not None:
        items=checked_timing(story,timing)
    elif audio_dir is not None:
        from .alignment import aligned_cues
        items=aligned_cues(story,audio_dir)
    else:
        items = cues(story)
    json_path = dest/"captions.json"
    json_path.write_text(json.dumps(items,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    # ASS coordinates use the 720 x 1280 reference frame.
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,1,2,76,76,205,1
Style: Callout,Arial,35,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,3,9,0,8,65,65,128,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 0,{ass_time(x['start'])},{ass_time(x['end'])},Default,,0,0,0,,{safe_ass_caption(x['text'])}" for x in items]
    for beat in story["beats"]:
        if beat.get("callout"):
            events.append(f"Dialogue: 1,{ass_time(beat['start']+.6)},{ass_time(beat['end']-.2)},"
                          f"Callout,,0,0,0,,{safe_ass_caption(beat['callout'],28)}")
    ass_path = dest/"captions.ass"
    ass_path.write_text(header+"\n".join(events)+"\n",encoding="utf-8")
    return json_path, ass_path
