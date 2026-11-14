"""Three restrained original contact sounds, without music or borrowed meme audio."""
import array
import math
import random
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
ASSETS=ROOT/'.local/friction-story-v2/pack/friction-straight/assets'

if __name__=='__main__':
    rng=random.Random(21)
    for name,freq,duration,gain in [('impact',82,.28,.22),('tap',710,.09,.14),('mat',105,.19,.18)]:
        samples=[]
        for i in range(round(48000*duration)):
            t=i/48000;u=t/duration;envelope=(1-math.exp(-t*1100))*math.exp(-u*8)
            sample=gain*envelope*(.75*math.sin(2*math.pi*freq*t)+.25*rng.uniform(-1,1))
            samples.append(round(sample*32767))
        with wave.open(str(ASSETS/f'{name}.wav'),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
            f.writeframes(array.array('h',samples).tobytes())
    print('Created three original low-level contact sounds')
