"""Add the verified sample to the existing local gallery without altering feedback."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
LOCAL=ROOT/'.local/voxel-story'
GALLERY=ROOT/'.local/format-audition'

if __name__=='__main__':
    sid='commons-lake';source=LOCAL/'output'/sid
    lesson=json.loads((LOCAL/'pack'/sid/'lesson.json').read_text())
    report=json.loads((source/'technical-report.json').read_text())
    assert report['automatic_technical_checks']=='passed'
    registry=json.loads((GALLERY/'registry.json').read_text())
    prior=next((x for x in registry if x['id']==sid),None)
    number=prior['number'] if prior else max(x['number'] for x in registry)+1
    dest=GALLERY/'output'/sid;dest.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.is_file() and p.name!='render-original.mp4':shutil.copyfile(p,dest/p.name)
    pack=GALLERY/'pack'/sid;pack.mkdir(parents=True,exist_ok=True)
    for name in ['lesson.json','captions.vtt']:shutil.copyfile(LOCAL/'pack'/sid/name,pack/name)
    entry=dict(number=number,id=sid,name='3D voxel story · Revised acting',title=lesson['title'],duration=lesson['duration'],
        grammar='Empty dinner bucket → open lake → extra catches → depletion → monitored limits → recovery.',
        limitation='Revised task-facing bodies, hand-attached rods, casting/reeling, dry-bank walks and camera staging. Original 3D models; illustrative fish population and compressed time. Pending your review.',
        credits='Brian via ElevenLabs; original procedural models, textures and water sounds. Three.js MIT. FAO and Ostrom sources accompany the file.',
        contact_frames=[1,3,9,11,13,21],poster_frame=9)
    registry=[entry]+[x for x in registry if x['id']!=sid]
    (GALLERY/'registry.json').write_text(json.dumps(registry,indent=2))
    subprocess.run(['python3',str(ROOT/'services/renderer/experiments/format-audition/gallery.py')],check=True,timeout=90)
    page=GALLERY/'index.html'
    page.write_text(page.read_text().replace('These are 2D / 2.5D format auditions.',
        'These are mixed 2D, 2.5D and 3D format auditions; the shared-lake sample uses actual 3D geometry.'))
    print(f'Sample {number}: http://127.0.0.1:8787/#{sid}')
