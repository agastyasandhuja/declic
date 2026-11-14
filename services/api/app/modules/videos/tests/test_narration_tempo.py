import shutil
import wave

import pytest

from app.modules.videos.media import run
from app.modules.videos.models import Brief, Segment
from app.modules.videos.narration.service import synthesize
from app.modules.videos.narration.timing import alignment_words
from app.modules.videos.pipeline import ROOT, generation_recipe


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg/ffprobe required"
)
def test_real_audio_tempo_alignment_and_cache_remain_consistent(tmp_path, monkeypatch):
    class LocalAudioProvider:
        model = "test-tone-with-known-alignment"
        calls = 0

        def synthesize(self, text, voice_id, output):
            self.calls += 1
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=1.8:sample_rate=48000",
                    "-c:a",
                    "libmp3lame",
                    output,
                ]
            )
            return {
                "alignment": {
                    "characters": list(text),
                    "character_start_times_seconds": [
                        0.1 + i * 1.55 / len(text) for i in range(len(text))
                    ],
                    "character_end_times_seconds": [
                        0.1 + (i + 1) * 1.55 / len(text) for i in range(len(text))
                    ],
                },
                "normalized_alignment": None,
            }

    segment = Segment(
        segment_id="tempo_test",
        speaker_role="narrator",
        spoken_text="Clear words",
        fact_ids=[],
    )
    provider = LocalAudioProvider()
    records = {}
    for fixture, speed in [
        ("revised-finance-brief.json", 1.0),
        ("revised-linked-list-brief.json", 1.08),
        ("new-installments-brief.json", 1.12),
        ("revised-enzyme-brief.json", 1.12),
    ]:
        brief = Brief.model_validate_json((ROOT / "fixtures/learning" / fixture).read_text())
        audio, metadata = synthesize(segment, brief, provider, "test-voice", tmp_path)
        with wave.open(str(audio)) as wav:
            actual_duration = wav.getnframes() / wav.getframerate()
            assert wav.getframerate() == 48000
            assert wav.getnchannels() == 1

        assert actual_duration == pytest.approx(metadata["duration"], abs=0.00001)
        assert actual_duration == pytest.approx(1.8 / speed, abs=0.04)
        words = alignment_words(metadata["alignment"], actual_duration)
        assert [word["text"] for word in words] == ["Clear", "words"]
        assert all(0 <= word["start"] < word["end"] <= actual_duration for word in words)
        assert words[-1]["end"] == pytest.approx(1.65 / speed)
        # The recorded provider response remains original; only playback timing changes.
        assert metadata["raw_response_alignment"]["alignment"]["character_end_times_seconds"][
            -1
        ] == pytest.approx(1.65)
        assert max(metadata["envelope"]) > 0.001

        original_bytes, original_stat, calls = audio.read_bytes(), audio.stat(), provider.calls
        cached_audio, cached_metadata = synthesize(segment, brief, provider, "test-voice", tmp_path)
        assert provider.calls == calls
        assert cached_audio == audio
        assert cached_audio.read_bytes() == original_bytes
        assert cached_audio.stat().st_mtime_ns == original_stat.st_mtime_ns
        assert cached_metadata == metadata
        records[fixture] = (audio, actual_duration)

    plain = records["revised-finance-brief.json"]
    dialogue = records["revised-linked-list-brief.json"]
    semantic = records["new-installments-brief.json"]
    assert plain[1] > dialogue[1] > semantic[1]
    assert len({plain[0], dialogue[0], semantic[0]}) == 3
    # Same scope, voice, words and editorial speed may safely share the audio cache.
    assert semantic == records["revised-enzyme-brief.json"]
    assert provider.calls == 3
    # Editing an instant clone keeps its ID; its old audio must not be reused.
    brief = Brief.model_validate_json(
        (ROOT / "fixtures/learning/revised-finance-brief.json").read_text()
    )
    original_generation_key = brief.generation_key(generation_recipe())
    monkeypatch.setenv("ELEVENLABS_NARRATOR_VOICE_REVISION", "new-authorized-samples")
    assert brief.generation_key(generation_recipe()) != original_generation_key
    revised_audio, revised_metadata = synthesize(segment, brief, provider, "test-voice", tmp_path)
    assert provider.calls == 4
    assert revised_audio != plain[0]
    assert revised_metadata["recipe"]["voice_revision"] == "new-authorized-samples"
    cached_audio, cached_metadata = synthesize(segment, brief, provider, "test-voice", tmp_path)
    assert provider.calls == 4
    assert (cached_audio, cached_metadata) == (revised_audio, revised_metadata)
