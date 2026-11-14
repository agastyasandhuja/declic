import json
import wave
from pathlib import Path

from ..media import atomic_json, probe, run, sha256
from ..models import digest
from .timing import alignment_words


def synthesize(segment, brief, provider, voice_id, cache: Path, fixture=False):
    identity = {
        "text": segment.spoken_text,
        "voice": voice_id,
        "model": getattr(provider, "model", "fixture-say"),
        "scope": brief.scope,
        "owner": brief.owner_user_id,
        "settings": "v1",
        "fixture": fixture,
    }
    key = digest(identity)
    folder = cache / key
    folder.mkdir(parents=True, exist_ok=True)
    metadata, audio = folder / "audio.json", folder / "audio.wav"
    if metadata.exists() and audio.exists():
        saved = json.loads(metadata.read_text())
        if saved["sha256"] == sha256(audio):
            return audio, saved
    if fixture:
        # Local fake only: macOS speech + estimated alignment, never labeled ElevenLabs.
        raw = folder / "fixture.aiff"
        run(["say", "-v", voice_id, "-r", "160", "-o", raw, segment.spoken_text])
    else:
        raw = folder / "provider.mp3"
        response = provider.synthesize(segment.spoken_text, voice_id, raw)
    run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-ac", "1", "-ar", "48000", audio])
    duration = float(probe(audio)["format"]["duration"])
    if not 0.2 < duration < 40:
        raise ValueError("Invalid speech duration")
    if fixture:
        length = len(segment.spoken_text)
        alignment = {
            "characters": list(segment.spoken_text),
            "character_start_times_seconds": [i * duration / length for i in range(length)],
            "character_end_times_seconds": [(i + 1) * duration / length for i in range(length)],
        }
        response = {"alignment": alignment, "normalized_alignment": None}
    else:
        alignment = response["alignment"]
        # Never zip normalized speech against original character positions.
        if not alignment or "".join(alignment.get("characters", [])) != segment.spoken_text:
            raise ValueError(
                "Raw alignment does not map exactly to frozen speech; explicit pronunciation needed"
            )
    alignment_words(alignment, duration)
    with wave.open(str(audio)) as w:
        import array

        samples = array.array("h", w.readframes(w.getnframes()))
    envelope = [
        round(max((abs(v) for v in samples[i : i + 1600]), default=0) / 32768, 4)
        for i in range(0, len(samples), 1600)
    ]
    if max(envelope, default=0) < 0.001:
        raise ValueError("Empty/silent speech")
    saved = {
        "duration": duration,
        "alignment": alignment,
        "raw_response_alignment": response,
        "sha256": sha256(audio),
        "recipe": identity,
        "envelope": envelope,
        "alignment_source": "estimated_fixture" if fixture else "elevenlabs_raw",
    }
    atomic_json(metadata, saved)
    return audio, saved
