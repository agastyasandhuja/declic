"""Stage original script and live aligned voice. Reference media never leaves this host."""
import json
import math
import subprocess
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from app.modules.videos.generation.providers import ElevenLabs
from app.modules.videos.narration.service import synthesize
from app.modules.videos.narration.timing import alignment_words, vtt
from models import Story

ROOT = Path(__file__).resolve().parents[4]
LOCAL = ROOT / '.local/election-story'

def main():
    load_dotenv(ROOT / '.env')
    load_dotenv(ROOT / 'services/api/.env')
    story = Story.model_validate_json(Path(__file__).with_name('storyboard.json').read_text()).model_dump(mode='json')
    assets = LOCAL / 'pack' / story['id'] / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    provider = ElevenLabs()
    brief = SimpleNamespace(installment_example=None, format_id='analogy_story',
        presentation='voxel_audition', scope='shared_generic', owner_user_id=None)
    segments, words, cursor = [], [], 0
    for i, beat in enumerate(story['beats']):
        segment = SimpleNamespace(spoken_text=beat['text'], speaker_role='narrator')
        audio, meta = synthesize(segment, brief, provider, story['voice']['id'], LOCAL / 'audio-cache')
        name = f'speech-{i}.wav'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(audio), '-af',
            'loudnorm=I=-18:TP=-2:LRA=7', '-ar', '48000', '-ac', '1', str(assets/name)],
            check=True, timeout=90)
        start = math.ceil(cursor * 30) / 30
        end = start + meta['duration'] + beat['pause']
        segments.append(dict(beat, start=start, end=end, duration=meta['duration'], audio=name))
        words.extend(alignment_words(meta['alignment'], meta['duration'], start))
        cursor = end
        print(f'{i:02} {beat["scene"]}: {start:.2f}–{end:.2f}s', flush=True)
    frames = math.ceil(cursor*30)
    if not 30 <= frames/30 <= 60:
        raise ValueError(f'Edit script: duration is {frames/30}s')
    lesson = dict(story, segments=segments, words=words, frames=frames, duration=frames/30,
        narration_source='live_elevenlabs', narration_model=provider.model,
        visual_source='original_procedural_threejs_3d', script_source='authored',
        disclosure='Fictional candidates and three equal-weight example states; not a real election result or U.S. map. Rules checked against National Archives on 2026-11-14.')
    (assets.parent/'lesson.json').write_text(json.dumps(lesson, indent=2))
    captions = [dict(start=w['start'], end=w['end'], words=[w]) for w in words]
    (assets.parent/'captions.vtt').write_text(vtt(captions))
    print(f'Total: {frames/30:.2f}s; {len(words)} aligned words')

if __name__ == '__main__':
    main()
