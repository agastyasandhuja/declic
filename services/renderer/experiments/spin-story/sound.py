"""Original quiet action foley; no downloaded soundtrack."""
import array
import json
import math
import random
import wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
PACK=ROOT/'.local/spin-story/pack/spinning-chair'
if __name__=='__main__':
 lesson=json.loads((PACK/'lesson.json').read_text());rate=48000
 samples=array.array('h',[0])*round(lesson['duration']*rate);rng=random.Random(5)
 for time in [.55,lesson['segments'][8]['start']+.9]:
  start=round(time*rate)
  for j in range(12000):
   age=j/rate;v=.025*rng.uniform(-1,1)*math.exp(-15*age)+.025*math.sin(2*math.pi*180*age)*math.exp(-22*age)
   samples[start+j]=round(v*32767)
 with wave.open(str(PACK/'assets/ambience.wav'),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(samples.tobytes())
 print('Original chair/contact foley prepared')
