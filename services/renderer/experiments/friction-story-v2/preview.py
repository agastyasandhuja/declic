"""Stage the verified cartoon as sample 21 in the existing local review gallery."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
LOCAL=ROOT/'.local/friction-story-v2'
GALLERY=ROOT/'.local/format-audition'

if __name__=='__main__':
    source=LOCAL/'output/friction-straight'
    report=json.loads((source/'technical-report.json').read_text())
    assert report['automatic_technical_checks']=='passed'
    lesson=json.loads((LOCAL/'pack/friction-straight/lesson.json').read_text())
    frames=[0,*[f for s in lesson['segments'] for f in (round((s['start']+.6)*30),round((s['start']+s['end'])/2*30))],lesson['frames']-1]
    for i,f in enumerate(frames):
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(min(f,lesson['frames']-1)/30),
                        '-i',str(source/'lesson.mp4'),'-frames:v','1',str(source/f'frame-{i}.png')],
                       check=True,capture_output=True,timeout=30)
    (source/'frame-index.json').write_text(json.dumps(frames))
    target=GALLERY/'output/friction-straight';target.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.is_file() and p.suffix in ('.png','.mp4','.json'):
            shutil.copyfile(p,target/p.name)
    pack=GALLERY/'pack/friction-straight';pack.mkdir(parents=True,exist_ok=True)
    for name in ('lesson.json','captions.vtt'):
        shutil.copyfile(LOCAL/'pack/friction-straight'/name,pack/name)
    registry=json.loads((GALLERY/'registry.json').read_text())
    entry=dict(number=21,id='friction-straight',name='V2 · Everyday examples / male voices',
               title='What if friction disappeared?',duration=lesson['duration'],
               grammar='Cars crash → mom and dog slip → phone falls → gym mishap → visual explanation.',
               limitation='Revised to your feedback: direct story, male voices, captions and essential diagram notation only. Original 2D animation; still a candidate for your review.',
               credits='Liam narrates; Roger delivers the short gym reaction. Live ElevenLabs voices, original animated artwork and three quiet contact sounds.',
               contact_frames=[2,6,8,12,16,22],poster_frame=6)
    registry=[entry]+[x for x in registry if x['id']!='friction-straight']
    for item in registry:
        if item['id']=='friction-story':
            item['name']='V1 · Cartoon story / three voices'
            item['limitation']='First attempt; user requested a simpler story, improved animation, male voices and far less text. See revised sample 21. Not an approved template.'
    (GALLERY/'registry.json').write_text(json.dumps(registry,indent=2))
    subprocess.run(['python3',str(ROOT/'services/renderer/experiments/format-audition/gallery.py')],check=True,timeout=90)
    shutil.copyfile(target/'contact.jpg',source/'contact.jpg')
    print('Sample 21 staged: http://127.0.0.1:8787/#friction-straight')
