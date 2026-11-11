"""Original deterministic procedural effects; no third-party recordings."""
import array
import math
import random
import wave
from pathlib import Path

NAMES={"assembly","water","electric","transition","impact","ambient"}


def effect(name,rate=24000):
    if name not in NAMES:raise ValueError("Unregistered sound")
    rng=random.Random(name)
    duration={"assembly":.25,"water":.8,"electric":.35,"transition":.35,"impact":.18,"ambient":2}[name]
    result=[]
    smoothed=0
    for i in range(int(duration*rate)):
        t=i/rate
        envelope=math.sin(math.pi*t/duration)**2
        smoothed=.9*smoothed+.1*rng.uniform(-1,1)
        if name=="electric":value=math.sin(2*math.pi*(440*t+160*t*t))*.55
        elif name=="impact":value=math.sin(2*math.pi*95*t)*math.exp(-20*t)
        elif name=="assembly":value=(smoothed+math.sin(2*math.pi*800*t)*.2)*math.exp(-8*t)
        else:value=smoothed*2
        result.append(value*envelope)
    return result


def mix_effects(story,path):
    rate=24000
    track=array.array("f",[0])*(story["duration"]*rate)
    for beat in story["beats"]:
        for cue in beat.get("sfx",[]):
            gain=10**(cue.get("gain_db",-30)/20)
            start=round((beat["start"]+cue.get("offset",0))*rate)
            for i,value in enumerate(effect(cue["name"],rate)):
                if start+i<len(track):track[start+i]+=value*gain
    pcm=array.array("h",(round(max(-1,min(1,x))*32767) for x in track))
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as wav:
        wav.setparams((1,2,rate,0,"NONE","not compressed"));wav.writeframes(pcm.tobytes())
    return path
