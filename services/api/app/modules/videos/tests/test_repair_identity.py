"""Internal timing/frame repair must retain the enqueued publication identity.

Providers, narration, renderer and storage are synthetic. This test executes the
real recursive orchestration and exact-manifest publication checks, not media QA.
"""

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.modules.videos import motion_review, pipeline
from app.modules.videos.media import sha256
from app.modules.videos.models import Brief, ContentReview, RenderReview, Storyboard, digest
from app.modules.videos.publication import publish_private_demo
from app.modules.videos.repository import LocalVideoRepository


@pytest.mark.parametrize("repair", ["duration", "frame", "duration_then_frame"])
@pytest.mark.parametrize("editorial", [None, "Keep the two-year comparison explicit."])
def test_automatic_repair_keeps_queued_recipe_through_publication(
    monkeypatch, tmp_path, repair, editorial
):
    brief = Brief.model_validate_json(
        (pipeline.ROOT / "fixtures/learning/revised-finance-brief.json").read_text()
    ).model_copy(update={"scope": "private", "owner_user_id": "synthetic-owner"})
    original = Storyboard.model_validate_json(
        (pipeline.ROOT / "fixtures/learning/revised-visual_explainer.json").read_text()
    ).validate_for(brief, require_engagement=True)
    recipe = {
        "claude": "synthetic-model",
        "background_mode": "concept_only",
        "prompts": {"visual_explainer/reference-prompt.txt": "synthetic-prompt"},
        "system_prompt": "synthetic-system",
        "engagement_policy": "synthetic-policy",
        "renderer_source": "synthetic-renderer",
        "voice_disclosure": "Synthetic test speech",
    }
    queued_recipe = deepcopy(recipe)
    if editorial:
        queued_recipe["editorial_feedback"] = digest(editorial)
    recipe_calls = []

    def generate_recipe(**kwargs):
        recipe_calls.append(kwargs)
        return deepcopy(recipe)

    monkeypatch.setattr(pipeline, "generation_recipe", generate_recipe)
    monkeypatch.setenv("ELEVENLABS_NARRATOR_VOICE_ID", "synthetic-voice")
    boards = []

    class Claude:
        model = "synthetic-model"
        usage = []
        reviews = 0

        def storyboard(self, *args):
            board = original.model_copy(deep=True)
            if boards:
                # An actual script edit, not merely replaying an identical board.
                board.segments[
                    0
                ].spoken_text = (
                    "Same rate, two years. Why does one account finish ten dollars ahead?"
                )
            boards.append(board)
            return board

        def review(self, *args):
            return ContentReview(passed=True, issues=[])

        def review_render(self, *args):
            self.reviews += 1
            if "frame" in repair and self.reviews == 1:
                return RenderReview(
                    passed=False,
                    issues=["Shorten the comparison label."],
                    repair_scope="storyboard",
                )
            return RenderReview(passed=True, issues=[])

    claude = Claude()
    monkeypatch.setattr(pipeline, "Claude", lambda **kwargs: claude)
    monkeypatch.setattr(pipeline, "ElevenLabs", lambda: SimpleNamespace())
    source = tmp_path / "synthetic.wav"
    source.write_bytes(b"synthetic audio; never played")
    speech_calls = []

    def speech(segment, *args):
        first_pass = len(speech_calls) < len(original.segments)
        duration = 1.0 if repair.startswith("duration") and first_pass else 4.5
        speech_calls.append(segment.segment_id)
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
    monkeypatch.setattr(
        pipeline, "run", lambda command, **kwargs: command[-1].write_bytes(b"synthetic narration")
    )
    monkeypatch.setattr(pipeline, "stage_images", lambda *args, **kwargs: {})

    def render(pack, output, preview, **kwargs):
        output.mkdir(parents=True, exist_ok=True)
        (output / "frame-01.png").write_bytes(b"synthetic frame")
        (output / "frame-index.json").write_text(json.dumps([{"file": "frame-01.png"}]))
        if kwargs.get("stills_only"):
            return {}
        (output / "lesson.mp4").write_bytes(b"synthetic media; never played")
        report = {
            "media_checks": "passed",
            "duration_seconds": 36.3,
            "sha256": sha256(output / "lesson.mp4"),
        }
        (output / "quality.json").write_text(json.dumps(report))
        return report

    monkeypatch.setattr(pipeline, "render", render)
    monkeypatch.setattr(motion_review, "stage_motion_review", lambda *args: {"synthetic": True})
    work = tmp_path / "work"
    repository = LocalVideoRepository(tmp_path / "jobs.db")
    queued_key = brief.generation_key(queued_recipe)
    repository.enqueue(queued_key, brief.owner_user_id, brief.model_dump(), queued_recipe)
    job = repository.claim()
    manifest = pipeline.generate(brief, work, storyboard_feedback=editorial)
    assert len(recipe_calls) == 1  # Internal repairs cannot recompute a new recipe.
    assert len(boards) >= 2
    assert manifest["storyboard_digest"] != digest(original.model_dump())
    assert manifest["generation_key"] == queued_key
    assert manifest["recipe"] == queued_recipe
    assert json.loads((work / "request.json").read_text())["generation_key"] == queued_key
    budget = json.loads((work / "budgets.json").read_text())
    assert budget["duration_repairs"] == int(repair.startswith("duration"))
    assert budget["scene_repairs"] == int("frame" in repair)
    storage = SimpleNamespace(
        verify_private_bucket=lambda: None,
        put=lambda key, file: {"key": key, "sha256": sha256(file), "size": file.stat().st_size},
    )
    published = publish_private_demo(repository, storage, job, brief, work, manifest)
    assert published["generation_key"] == queued_key
    assert repository.get(job["job_id"], brief.owner_user_id)["state"] == "succeeded"
    assert published["quality_checks"]["human_review"] == "pending"
