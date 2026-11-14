"""Freeze the approved story and synthesize independently cast, aligned dialogue."""
import json
import math
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from dotenv import load_dotenv
from app.modules.videos.generation.providers import ElevenLabs
from app.modules.videos.narration.service import synthesize
from app.modules.videos.narration.timing import alignment_words, caption_groups, vtt

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT/'.local/friction-story'

if __name__ == '__main__':
    load_dotenv(ROOT/'.env'); load_dotenv(ROOT/'services/api/.env')
    plan=json.loads(Path(__file__).with_name('storyboard.json').read_text())
    assets=OUT/'pack/friction-story/assets'; assets.mkdir(parents=True,exist_ok=True)
    cast={c['role']:c for c in plan['cast']}
    provider=ElevenLabs()
    brief=SimpleNamespace(installment_example=None,format_id='analogy_story',
                          presentation='story_audition',scope='shared_generic',owner_user_id=None)
    segments=[]; words=[]; cursor=0
    for i,b in enumerate(plan['beats']):
        seg=SimpleNamespace(spoken_text=b['text'],speaker_role=b['speaker'])
        audio,meta=synthesize(seg,brief,provider,cast[b['speaker']]['voice_id'],OUT/'audio-cache')
        name=f'speech-{i}.wav'; dest=assets/name
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(audio),'-af','loudnorm=I=-18:TP=-2:LRA=7',
                        '-ar','48000','-ac','1',str(dest)],check=True,timeout=90)
        start=math.ceil(cursor*30)/30
        # Small headroom around the visual switch and the foam-box impact.
        hold=max(b['pause_after'], .24)
        end=start+meta['duration']+hold
        envelope=meta.get('amplitude_envelope',meta.get('envelope',[]))
        segments.append(dict(b,start=start,end=end,duration=meta['duration'],audio=name,
                             voice_name=cast[b['speaker']]['name'],voice_id=cast[b['speaker']]['voice_id'],
                             envelope=envelope))
        words.extend(dict(w,segment_id=str(i),speaker=b['speaker']) for w in alignment_words(meta['alignment'],meta['duration'],start))
        cursor=end
        print(f'{i:02} {b["scene"]}: {start:.2f}–{end:.2f}s | {cast[b["speaker"]]["name"]}',flush=True)
    pack=dict(id='friction-story',number=20,title=plan['title'],segments=segments,
      captions=caption_groups(words),frames=math.ceil(cursor*30),duration=math.ceil(cursor*30)/30,
      cast=plan['cast'],narration_model=provider.model,narration_source='live_elevenlabs',
      script_source='claude-opus-5-5_with_editorial_revision',visual_source='authored_layered_remotion_cartoon',
      premise='Only shoe-ground and tire-road friction disappear. Gravity and contact forces remain. Short scene neglects air drag.',
      evidence=['https://openstax.org/books/university-physics-volume-1/pages/6-2-friction',
                'https://openstax.org/books/university-physics-volume-1/pages/6-3-centripetal-force'])
    assert 30 <= pack['duration'] <= 60, f'Script needs editing: {pack["duration"]} seconds'
    (assets.parent/'lesson.json').write_text(json.dumps(pack,indent=2))
    (assets.parent/'captions.vtt').write_text(vtt(pack['captions']))
    (OUT/'registry.json').write_text(json.dumps([dict(id='friction-story',number=20,title=plan['title'])],indent=2))
    print(f'Total: {pack["duration"]:.2f}s; three distinct live voices')
