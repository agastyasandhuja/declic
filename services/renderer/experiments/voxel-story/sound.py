"""Quiet original water texture and synchronized fishing splashes; no borrowed soundtrack."""
import array
import json
import math
import random
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
PACK=ROOT/'.local/voxel-story/pack/commons-lake'
if __name__=='__main__':
    lesson=json.loads((PACK/'lesson.json').read_text())
    rate=48000
    samples=array.array('h',[0])*round(lesson['duration']*rate)
    rng=random.Random(502)
    events=[]
    for s in lesson['segments']:
        if s['scene'] in ['access','subtract','extra','deplete','restore']:
            events.extend(s['start']+(s['end']-s['start'])*q for q in [.35,.65])
    events=[(round(t*rate),.22) for t in events]
    last=0
    for i in range(len(samples)):
        t=i/rate
        last=last*.95+rng.uniform(-1,1)*.05
        v=.017*last*(.6+.4*math.sin(t*1.8)**2)
        for start,duration in events:
            age=(i-start)/rate
            if 0<=age<duration:
                v+=.12*rng.uniform(-1,1)*math.exp(-age*22)+.04*math.sin(2*math.pi*(350-age*700)*age)*math.exp(-age*18)
        samples[i]=round(max(-.9,min(.9,v))*32767)
    with wave.open(str(PACK/'assets/ambience.wav'),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(samples.tobytes())
    print('Original quiet lake ambience and splash cues prepared')
