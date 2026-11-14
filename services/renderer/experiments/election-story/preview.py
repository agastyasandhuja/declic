"""Stage the two requested template trials while retaining existing sample IDs/feedback."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
GALLERY=ROOT/'.local/format-audition'
SAMPLES=[
 ('election-story','election-college','3D + 2D · Presidential elections',
  'Victory confetti → electors → three states → popular/electoral reversal.',
  'Fictional candidates and equal-weight states, not a real map/result. U.S. Electoral College rules checked against the National Archives. Authored 3D rig plus 2D diagrams; pending your review.',
  'Roger via ElevenLabs; Codex-authored geometry and original animation; shared voxel rig/captions. Three.js MIT.',[1,4,14,20,26,29],29),
 ('spin-story','spinning-chair','2D cartoon · Angular momentum',
  'One push → tuck → faster spin → extend → slower spin → floor brakes.',
  'Continuous integrated rotation and connected limbs. Normalized illustrative inertia model, not measured biomechanics. OpenStax/SFU factual basis; pending your review.',
  'Charlie via ElevenLabs; Codex-authored vector art, motion and original quiet foley; shared white captions.',[0,8,11,17,23,29],11),
]

if __name__=='__main__':
 registry=json.loads((GALLERY/'registry.json').read_text());entries=[]
 next_number=max(x['number'] for x in registry)+1
 for folder,sid,name,grammar,limitation,credits,frames,poster in SAMPLES:
  base=ROOT/'.local'/folder;source=base/'output'/sid
  report=json.loads((source/'technical-report.json').read_text())
  if report['automatic_technical_checks']!='passed':raise ValueError('Unverified export')
  lesson=json.loads((base/'pack'/sid/'lesson.json').read_text())
  prior=next((x for x in registry if x['id']==sid),None)
  number=prior['number'] if prior else next_number
  if not prior:next_number+=1
  dest=GALLERY/'output'/sid;dest.mkdir(parents=True,exist_ok=True)
  for p in source.iterdir():
   if p.is_file() and p.name!='render-original.mp4':shutil.copyfile(p,dest/p.name)
  pack=GALLERY/'pack'/sid;pack.mkdir(parents=True,exist_ok=True)
  for n in ['lesson.json','captions.vtt']:shutil.copyfile(base/'pack'/sid/n,pack/n)
  entries.append(dict(id=sid,number=number,name=name,title=lesson['title'],duration=lesson['duration'],grammar=grammar,limitation=limitation,credits=credits,contact_frames=frames,poster_frame=poster))
 ids={e['id'] for e in entries};registry=entries+[x for x in registry if x['id'] not in ids]
 (GALLERY/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
 subprocess.run(['python3',str(ROOT/'services/renderer/experiments/format-audition/gallery.py')],check=True,timeout=90)
 page=GALLERY/'index.html';page.write_text(page.read_text().replace('These are 2D / 2.5D format auditions.','These are mixed 2D, 2.5D and 3D auditions; the lake and election samples use actual 3D geometry.'))
 for e in entries:print(f"Sample {e['number']}: http://127.0.0.1:8787/#{e['id']}")
