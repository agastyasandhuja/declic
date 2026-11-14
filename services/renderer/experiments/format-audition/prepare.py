"""Prepare a private audition pack with the existing live narration adapter."""
import concurrent.futures
import json
import math
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from catalog import SAMPLES
from app.modules.videos.generation.providers import ElevenLabs
from app.modules.videos.narration.service import synthesize
from app.modules.videos.narration.timing import alignment_words, caption_groups, vtt

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / ".local/format-audition"


def prepare(spec):
    folder = OUT / "pack" / spec["id"]
    assets = folder / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    provider = ElevenLabs()
    voice = os.environ["ELEVENLABS_NARRATOR_VOICE_ID"]
    brief = SimpleNamespace(installment_example=None, format_id="visual_explainer",
                            presentation="audition", scope="shared_generic", owner_user_id=None)
    segments, words, now = [], [], 0.0
    for i, line in enumerate(spec["lines"]):
        segment = SimpleNamespace(spoken_text=line, speaker_role="narrator")
        audio, meta = synthesize(segment, brief, provider, voice, OUT / "audio-cache")
        name = f"speech-{i}.wav"
        shutil.copyfile(audio, assets / name)
        start_frame = math.ceil(now * 30)
        start = start_frame / 30
        # Hold the actual prediction before beginning the next scene or its answer.
        pause = 1.6 if (spec["id"], i) in {("predict", 0), ("timeline", 2)} else 0.18
        end = start + meta["duration"] + pause
        segments.append(dict(start=start, end=end, duration=meta["duration"],
                             audio=name, label=spec["labels"][i], text=line))
        aligned = alignment_words(meta["alignment"], meta["duration"], start)
        words.extend(dict(w, segment_id=str(i)) for w in aligned)
        now = end
    pack = dict(spec, segments=segments, captions=caption_groups(words),
                frames=math.ceil(now * 30), duration=math.ceil(now * 30)/30,
                narration_model=provider.model, narration_source="live_elevenlabs",
                script_source="authored_synthetic", visual_source="authored_remotion_svg")
    (folder / "lesson.json").write_text(json.dumps(pack, indent=2))
    (folder / "captions.vtt").write_text(vtt(pack["captions"]))
    print(f'{spec["number"]:02} {spec["id"]}: {pack["duration"]:.1f}s', flush=True)
    provider.client.close()
    return {k: v for k, v in pack.items() if k not in {"captions", "segments"}}


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "services/api/.env")
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        registry = list(executor.map(prepare, SAMPLES))
    (OUT / "registry.json").write_text(json.dumps(registry, indent=2))
