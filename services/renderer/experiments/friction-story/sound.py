"""Original procedural cartoon foley and a quiet plucked ostinato; no borrowed audio."""
import array
import json
import math
import random
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'.local/friction-story'
RATE=48000

def save(path, samples):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(RATE)
        f.writeframes(array.array('h',(round(max(-1,min(1,x))*32767) for x in samples)).tobytes())

if __name__=='__main__':
    lesson=json.loads((OUT/'pack/friction-story/lesson.json').read_text())
    assets=OUT/'pack/friction-story/assets'
    sounds={}
    rng=random.Random(147)
    # Keep the bed far below speech; drop it for the explanatory closeups.
    samples=[0.0]*math.ceil(lesson['duration']*RATE)
    for step in range(math.ceil(lesson['duration']/.375)):
        at=step*.375
        scene=next((s['scene'] for s in lesson['segments'] if s['start']<=at<s['end']),'')
        gain=.018 if scene in ['why','shoe','tire','restore'] else .034
        note=[196,0,293.665,0,246.942,0,329.628,293.665][step%8]
        if not note: continue
        for j in range(int(.30*RATE)):
            idx=round(at*RATE)+j
            if idx>=len(samples):break
            t=j/RATE; env=(1-math.exp(-t*180))*math.exp(-t*18)
            samples[idx]+=gain*env*(math.sin(2*math.pi*note*t)+.3*math.sin(4*math.pi*note*t))
    save(assets/'music.wav',samples)
    for name,duration in [('click',.15),('slide',.8),('boing',.65),('pop',.25),('grip',.28)]:
        samples=[];phase=0
        for i in range(int(duration*RATE)):
            t=i/RATE; u=t/duration
            if name=='click': freq=850-650*u; v=math.sin(phase)*math.exp(-u*12)*.28
            elif name=='slide': freq=600-440*u; v=(.6*math.sin(phase)+.15*rng.uniform(-1,1))*math.sin(math.pi*u)*.17
            elif name=='boing':freq=120+220*math.exp(-u*4)*(1+.3*math.sin(u*18));v=math.sin(phase)*math.exp(-u*4)*.32
            elif name=='grip':freq=1200-600*u;v=math.sin(phase)*math.sin(math.pi*u)**2*.16
            else: freq=900-600*u;v=math.sin(phase)*math.exp(-u*8)*.2
            phase+=2*math.pi*freq/RATE;samples.append(v)
        save(assets/f'{name}.wav',samples)
    print('Created original music and five foley cues')
