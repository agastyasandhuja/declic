"""Original quiet action foley; no downloaded soundtrack."""
import array
import json
import math
import random
import wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
PACK=ROOT/'.local/election-story/pack/election-college'
if __name__=='__main__':
 lesson=json.loads((PACK/'lesson.json').read_text());rate=48000
 samples=array.array('h',[0])*round(lesson['duration']*rate);rng=random.Random(16)
 for s in lesson['segments']:
  times=[s['start']+(s['end']-s['start'])*q for q in ([.55] if s['scene']=='ballot' else [.4,.65] if s['scene'] in ['narrow','landslide','electoral'] else [])]
  for t in times:
   start=round(t*rate)
   for i in range(int(.15*rate)):
    age=i/rate;v=.045*math.sin(2*math.pi*460*age)*math.exp(-40*age)+.018*rng.uniform(-1,1)*math.exp(-50*age)
    samples[start+i]+=int(v*32767)
 with wave.open(str(PACK/'assets/ambience.wav'),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(samples.tobytes())
 print('Original paper/token foley prepared')
