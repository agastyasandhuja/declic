"""Check the actual encoded brake shot: translating car, stationary wheel spokes."""
import hashlib
import json
import math
import subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'.local/friction-story/output/friction-story'

def frame(at,name):
    path=OUT/name
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(at),'-i',str(OUT/'lesson.mp4'),
                    '-frames:v','1',str(path)],check=True,capture_output=True,timeout=30)
    return Image.open(path).convert('RGB')

if __name__=='__main__':
    lesson=json.loads((ROOT/'.local/friction-story/pack/friction-story/lesson.json').read_text())
    segment=next(s for s in lesson['segments'] if s['scene']=='car')
    times=[segment['start']+1.3,segment['start']+2.5]
    pictures=[frame(t,f'motion-{i}.png') for i,t in enumerate(times)]
    centers=[];crops=[]
    for im,t in zip(pictures,times):
        # Yellow car body only; exclude the sun, caption strip, and driver inset.
        points=[x for y in range(650,870) for x in range(70,690)
                if (lambda r,g,b:r>245 and 210<g<240 and 105<b<155)(*im.getpixel((x,y)))]
        assert len(points)>1500,'Missing yellow car in encoded brake shot'
        centers.append(sum(points)/len(points))
        u=(t-segment['start'])/(segment['end']-segment['start'])
        wx=round((470+u*140-166*1.28)*2/3);wy=round((1290-7*1.28)*2/3)
        crops.append(im.crop((wx-34,wy-34,wx+35,wy+35)))
    translation=centers[1]-centers[0]
    expected=140*(times[1]-times[0])/(segment['end']-segment['start'])*2/3
    # Quantization/anti-aliasing tolerance; full wheel-relative spoke image comparison.
    differences=[]
    for y in range(69):
        for x in range(69):
            if math.hypot(x-34,y-34)>31: continue
            differences.extend(abs(a-b) for a,b in zip(crops[0].getpixel((x,y)),crops[1].getpixel((x,y))))
    delta=sum(differences)/len(differences)
    assert abs(translation-expected)<8,(translation,expected)
    assert delta<18, f'Locked wheel spokes changed unexpectedly: {delta}'
    assert len({s['voice_id'] for s in lesson['segments']})==3
    report=dict(sha256=hashlib.sha256((OUT/'lesson.mp4').read_bytes()).hexdigest(),
      actual_car_translation_pixels=round(translation,2),expected_translation_pixels=round(expected,2),
      wheel_relative_mean_pixel_delta=round(delta,2),locked_wheel_while_car_moves=True,
      distinct_voice_ids=3,scope='Encoded brake shot and cast identities only; not a global physics proof or subjective audio review.')
    (OUT/'motion-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
