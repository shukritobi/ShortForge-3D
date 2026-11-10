"""Offline waveform-assisted caption timing; not phoneme/ASR forced alignment."""
import array
import math
import wave
from pathlib import Path


def voiced_windows(path):
    with wave.open(str(path),"rb") as wav:
        if wav.getsampwidth()!=2 or wav.getnchannels()!=1:
            raise ValueError("alignment requires mono PCM16 WAV")
        rate=wav.getframerate()
        samples=array.array("h",wav.readframes(wav.getnframes()))
    block=max(1,rate//50)
    rms=[math.sqrt(sum(s*s for s in samples[i:i+block])/max(1,len(samples[i:i+block])))
         for i in range(0,len(samples),block)]
    threshold=max(80,max(rms,default=0)*.035)
    active=[i for i,x in enumerate(rms) if x>threshold]
    if not active:
        raise ValueError("no audible speech for captions")
    return [(i*block/rate,min(len(samples),(i+1)*block)/rate) for i in active]


def aligned_cues(story,audio_dir,words_per_cue=3):
    result=[]
    for index,beat in enumerate(story["beats"]):
        windows=voiced_windows(Path(audio_dir)/"beats"/f"beat_{index:02d}.wav")
        words=beat["narration"].split()
        chunks=[words[i:i+words_per_cue] for i in range(0,len(words),words_per_cue)]
        weights=[sum(max(1,len(w)) for w in c) for c in chunks]
        cursor=0
        for chunk,weight in zip(chunks,weights):
            first=min(len(windows)-1,math.ceil(cursor/sum(weights)*len(windows)))
            cursor+=weight
            last=min(len(windows)-1,max(first,math.ceil(cursor/sum(weights)*len(windows))-1))
            result.append({"start":round(beat["start"]+windows[first][0],3),
                           "end":round(min(beat["end"],beat["start"]+windows[last][1]),3),
                           "text":" ".join(chunk),"beat_id":beat["id"],
                           "alignment":"waveform_assisted_estimate"})
    return result
