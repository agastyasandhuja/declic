import json
import wave

import pytest

from app.modules.videos import pipeline
from app.modules.videos.engagement import timing_issues
from app.modules.videos.models import Brief, Storyboard


def fixture(fmt="visual_explainer"):
    brief = Brief.model_validate_json(
        (pipeline.ROOT / "fixtures/learning/linked-list-brief.json").read_text()
    ).model_copy(update={"format_id": fmt})
    board = Storyboard.model_validate_json(
        (pipeline.ROOT / f"fixtures/learning/{fmt}.json").read_text()
    )
    return brief, board


@pytest.mark.parametrize("fmt", ["visual_explainer", "dialogue_gameplay"])
def test_new_fixtures_have_grounded_closed_loop_and_recall(fmt):
    brief, board = fixture(fmt)
    board.validate_for(brief, require_engagement=True)


@pytest.mark.parametrize("failure", ["missing", "order", "unknown", "ungrounded", "late_trace"])
def test_reject_broken_teaching_structure(failure):
    brief, board = fixture()
    if failure == "missing":
        board.teaching_beats.pop()
    elif failure == "order":
        board.teaching_beats[2].segment_id = "feedback"
    elif failure == "unknown":
        board.teaching_beats[1].segment_id = "missing_segment"
    elif failure == "ungrounded":
        board.segments[-1].fact_ids = []
    else:
        board.events[-1].cue.segment_id = "feedback"
        board.events[-1].cue.phrase = "The original next node"
    with pytest.raises(ValueError):
        board.validate_for(brief, require_engagement=True)


def test_legacy_artifact_readable_but_not_accepted_as_new_generation():
    brief, board = fixture()
    board.teaching_beats = []
    board.validate_for(brief)
    with pytest.raises(ValueError, match="teaching beats"):
        board.validate_for(brief, require_engagement=True)


def test_measured_slow_opening_is_rejected_even_for_short_script():
    assert timing_issues(
        [
            {"speech_end": 4.2},
            {"speech_end": 10.0},
        ]
    ) == [
        "Shorten the hook to finish within 3.5 seconds of measured speech",
        "Finish asking the prediction within 9 seconds; keep it concise",
    ]


@pytest.mark.parametrize("fmt", ["visual_explainer", "dialogue_gameplay"])
def test_preparation_inserts_real_silence_and_shifts_cues(monkeypatch, tmp_path, fmt):
    brief, board = fixture(fmt)
    monkeypatch.setenv("VIDEO_BACKGROUND_MODE", "concept_only")
    source = tmp_path / "fake-speech.wav"

    def speech(segment, *args):
        duration = len(segment.spoken_text.split()) / 3
        with wave.open(str(source), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(48000)
            audio.writeframes(b"\x01\x00" * round(duration * 48000))
        n = len(segment.spoken_text)
        return source, {
            "duration": duration,
            "envelope": [0.1],
            "alignment": {
                "characters": list(segment.spoken_text),
                "character_start_times_seconds": [i * duration / n for i in range(n)],
                "character_end_times_seconds": [(i + 1) * duration / n for i in range(n)],
            },
        }

    monkeypatch.setattr(pipeline, "synthesize", speech)
    # Fake FFmpeg only: verify timeline/PCM generation, not a playable render.
    commands = []
    monkeypatch.setattr(pipeline, "run", lambda command, **kw: commands.append(command))
    manifest = pipeline.generate(brief, tmp_path / "run", fixture=True, render_video=False)
    lesson = json.loads((tmp_path / "run/pack/lesson.json").read_text())
    beats = lesson["teaching_beats"]
    for i, seconds in [(1, 2), (3, 3)]:
        assert beats[i]["end"] - beats[i]["speech_end"] == pytest.approx(seconds)
        segment_index = next(
            j
            for j, s in enumerate(board.segments)
            if s.segment_id == board.teaching_beats[i].segment_id
        )
        path = tmp_path / f"run/pack/assets/pause-{segment_index}.wav"
        with wave.open(str(path)) as audio:
            assert audio.getnframes() / audio.getframerate() == seconds
            assert not any(audio.readframes(audio.getnframes()))
    assert lesson["segments"][2]["start"] == pytest.approx(beats[1]["end"])
    assert lesson["segments"][-1]["start"] == pytest.approx(beats[3]["end"])
    assert lesson["events"][0]["time"] >= beats[1]["end"]
    assert lesson["events"][-1]["time"] < beats[3]["start"]
    # A previous explanation must not share a caption with the recall question,
    # even when both use the same narrator with no silence between them.
    assert all(len({w["segment_id"] for w in g["words"]}) == 1 for g in lesson["captions"])
    recall_groups = [
        g
        for g in lesson["captions"]
        if g["start"] >= beats[3]["start"] and g["start"] < beats[3]["speech_end"]
    ]
    assert recall_groups and all(
        w["segment_id"] == "recall" for g in recall_groups for w in g["words"]
    )
    assert lesson["background"] is None
    assert "pause-1.wav" in (tmp_path / "run/audio-inputs.txt").read_text()
    assert manifest["teaching_checks"]["learning_uplift"] == "unmeasured"
    assert commands


def test_background_experiment_and_policy_invalidate_generation_cache(monkeypatch):
    brief, _ = fixture()
    monkeypatch.setenv("VIDEO_BACKGROUND_MODE", "concept_only")
    coherent = pipeline.generation_recipe(fixture=True)
    monkeypatch.setenv("VIDEO_BACKGROUND_MODE", "gameplay")
    gameplay = pipeline.generation_recipe(fixture=True)
    assert brief.generation_key(coherent) != brief.generation_key(gameplay)
    assert "system_prompt" in coherent and "engagement_policy" in coherent
    monkeypatch.setenv("VIDEO_BACKGROUND_MODE", "not_a_mode")
    with pytest.raises(ValueError, match="BACKGROUND_MODE"):
        pipeline.generation_recipe()
