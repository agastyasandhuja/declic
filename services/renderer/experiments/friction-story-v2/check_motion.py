"""Inspect encoded frames for locked-wheel coasting and an accelerating phone fall."""
import hashlib
import json
import math
import subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]
LOCAL=ROOT/'.local/friction-story-v2'
OUT=LOCAL/'output/friction-straight'

def grab(at,name):
    p=OUT/f'{name}.png'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(at),'-i',str(OUT/'lesson.mp4'),
                    '-frames:v','1',str(p)],check=True,capture_output=True,timeout=30)
    return Image.open(p).convert('RGB')

if __name__=='__main__':
    lesson=json.loads((LOCAL/'pack/friction-straight/lesson.json').read_text())
    scenes={s['scene']:s for s in lesson['segments']}
    cx=[];wheels=[]
    for i,t in enumerate((.5,.9,1.3)):
        im=grab(scenes['cars']['start']+t,f'car-motion-{i}')
        pixels=[x for y in range(750,910) for x in range(0,430)
                if (lambda r,g,b:r>145 and 40<g<160 and 30<b<130)(*im.getpixel((x,y)))]
        assert len(pixels)>2000
        cx.append(sum(pixels)/len(pixels))
        x=round(115+t*100-104);y=906
        wheels.append(im.crop((x-27,y-27,x+28,y+28)))
    delta=[]
    for y in range(55):
        for x in range(55):
            if math.hypot(x-27,y-27)<25:
                delta.extend(abs(a-b) for a,b in zip(wheels[0].getpixel((x,y)),wheels[-1].getpixel((x,y))))
    wheel_change=sum(delta)/len(delta)
    shifts=[cx[i+1]-cx[i] for i in (0,1)]
    assert all(34<x<46 for x in shifts), shifts
    assert wheel_change<15,wheel_change
    phone_y=[]
    for i,t in enumerate((.8,1.1,1.4)):
        im=grab(scenes['phone']['start']+t,f'phone-motion-{i}')
        ys=[y for y in range(350,1000) for x in range(220,490)
            if (lambda r,g,b:r<100 and g<125 and b<145)(*im.getpixel((x,y)))]
        assert len(ys)>1000
        phone_y.append((min(ys)+max(ys))/2)
    drops=[phone_y[i+1]-phone_y[i] for i in (0,1)]
    assert drops[0]>20 and drops[1]>drops[0]+20,(phone_y,drops)
    voices={s['voice_id'] for s in lesson['segments']}
    assert voices=={'TX3LPaxmHKxFdv7VOQHJ','CwhRBWXzGAHq8TQ4Fs17'}
    report=dict(sha256=hashlib.sha256((OUT/'lesson.mp4').read_bytes()).hexdigest(),
      car_translation_pixels=[round(x,2) for x in shifts],locked_wheel_pixel_delta=round(wheel_change,2),
      phone_center_y=phone_y,phone_drops_in_equal_intervals=drops,male_stock_voices=['Liam','Roger'],
      result='passed',scope='Encoded pre-impact coast and phone fall only; subjective animation quality remains for user review.')
    (OUT/'motion-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
