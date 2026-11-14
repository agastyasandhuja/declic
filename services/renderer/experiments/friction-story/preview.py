"""Stage the verified cartoon as sample 20 in the existing local review gallery."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
LOCAL=ROOT/'.local/friction-story'
GALLERY=ROOT/'.local/format-audition'

if __name__=='__main__':
    source=LOCAL/'output/friction-story'
    report=json.loads((source/'technical-report.json').read_text())
    assert report['automatic_technical_checks']=='passed'
    lesson=json.loads((LOCAL/'pack/friction-story/lesson.json').read_text())
    frames=[0,*[f for s in lesson['segments'] for f in (round((s['start']+.6)*30),round((s['start']+s['end'])/2*30))],lesson['frames']-1]
    for i,f in enumerate(frames):
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(min(f,lesson['frames']-1)/30),
                        '-i',str(source/'lesson.mp4'),'-frames:v','1',str(source/f'frame-{i}.png')],
                       check=True,capture_output=True,timeout=30)
    (source/'frame-index.json').write_text(json.dumps(frames))
    target=GALLERY/'output/friction-story';target.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.is_file() and p.suffix in ('.png','.mp4','.json'):
            shutil.copyfile(p,target/p.name)
    pack=GALLERY/'pack/friction-story';pack.mkdir(parents=True,exist_ok=True)
    for name in ('lesson.json','captions.vtt'):
        shutil.copyfile(LOCAL/'pack/friction-story'/name,pack/name)
    registry=json.loads((GALLERY/'registry.json').read_text())
    entry=dict(number=20,id='friction-story',name='NEW · Cartoon story / three voices',
               title='Zero Grip Zone',duration=lesson['duration'],
               grammar='Sneaker shark → friction vanishes → brake failure → foam crash → static traction + centripetal force.',
               limitation='Original layered 2D cartoon, 11 shots. College-mechanics extension: turning-force limit and speed squared. Candidate awaiting your review.',
               credits='Opus story and casting with editorial revisions; Laura, Charlie and Callum via live ElevenLabs; original animated artwork and sound effects.',
               contact_frames=[0,6,10,12,16,20])
    registry=[entry]+[x for x in registry if x['id']!='friction-story']
    (GALLERY/'registry.json').write_text(json.dumps(registry,indent=2))
    subprocess.run(['python3',str(ROOT/'services/renderer/experiments/format-audition/gallery.py')],check=True,timeout=90)
    print('Sample 20 staged: http://127.0.0.1:8787/#friction-story')
