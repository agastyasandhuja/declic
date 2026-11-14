import json

from app.modules.videos import motion_review
from app.modules.videos.media import probe, run


def test_every_authored_shot_gets_a_complete_action_review_window():
    shots = [{"start": i * 3, "end": (i + 1) * 3} for i in range(11)]
    windows = motion_review.inspection_windows({"frames": 990, "segments": shots})
    for shot in shots:
        assert any(w["start"] == shot["start"] and w["end"] == shot["end"] for w in windows)


def test_inspection_includes_whole_reuse_cycles_and_geometry_rearrangement():
    windows = motion_review.inspection_windows(
        {
            "frame_count": 900,
            "shots": [
                {"start": 0, "end": 10},
                {"start": 10, "end": 14.8, "space_mode": "enzyme_reuse"},
                {"start": 14.8, "end": 30},
            ],
        }
    )
    cycle = next(window for window in windows if window["purpose"] == "reaction_cycles")
    assert cycle["start"] == 10 and cycle["end"] == 14.8
    # Start/middle/end stills can all fall in empty reset intervals; the clip
    # contains both actual encounters in between those samples.
    windows = motion_review.inspection_windows(
        {
            "frame_count": 660,
            "math": {
                "kind": "pythagorean_rearrangement",
                "stages": [{"kind": "rearrange", "start": 9, "end": 14}],
            },
        }
    )
    assert any(w["start"] == 9 and w["end"] == 14 for w in windows)
    assert all(0 <= w["start"] < w["end"] <= 22 for w in windows)


def test_real_motion_clips_preserve_audio_and_cache_without_reencoding(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=270x480:rate=30:duration=3",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=3",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-threads",
            "2",
            "-c:a",
            "aac",
            "-shortest",
            output / "lesson.mp4",
        ],
        timeout=30,
    )
    lesson = {"frame_count": 90}
    result = motion_review.stage_motion_review(tmp_path, lesson)
    assert result["paid_model_calls"] == 0
    assert result["status"] == "inspection_artifacts_only"
    for item in result["clips"]:
        media = probe(output / "motion-review" / item["file"])
        assert abs(float(media["format"]["duration"]) - (item["end"] - item["start"])) < 0.1
        assert {s["codec_type"] for s in media["streams"]} == {"video", "audio"}
        assert (output / "motion-review" / item["strip"]).stat().st_size > 1000
    monkeypatch.setattr(
        motion_review,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("Unchanged inspection must not re-encode")
        ),
    )
    assert motion_review.stage_motion_review(tmp_path, lesson) == result
    index = json.loads((output / "motion-review/index.json").read_text())
    assert index["source_video_sha256"] == result["source_video_sha256"]
