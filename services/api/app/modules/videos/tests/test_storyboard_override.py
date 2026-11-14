"""An explicitly authored storyboard still passes the normal factual review gates."""

import json
from unittest.mock import Mock

import pytest

from app.modules.videos import pipeline
from app.modules.videos.generation.providers import ProviderError
from app.modules.videos.models import Brief, ContentReview, Storyboard, digest


def fixture_json(name):
    return json.loads((pipeline.ROOT / "fixtures/learning" / name).read_text())


@pytest.fixture
def guarded_generation(monkeypatch):
    # Replace both paid providers and all downstream side effects. A regression
    # must fail locally, never purchase speech or start a render during this test.
    claude = Mock(spec=["review", "storyboard", "review_render", "usage"])
    claude.storyboard.side_effect = AssertionError("Author override regenerated the script")
    eleven = Mock(spec=["synthesize"])
    tts = Mock(side_effect=AssertionError("Rejected author edit reached speech generation"))
    renderer = Mock(side_effect=AssertionError("Rejected author edit reached renderer"))
    monkeypatch.setattr(pipeline, "Claude", Mock(return_value=claude))
    monkeypatch.setattr(pipeline, "ElevenLabs", Mock(return_value=eleven))
    monkeypatch.setattr(pipeline, "synthesize", tts)
    monkeypatch.setattr(pipeline, "render", renderer)
    for role in ("NARRATOR", "PETER", "STEWIE"):
        monkeypatch.setenv(f"ELEVENLABS_{role}_VOICE_ID", "test-voice")
    # The source-media hashes are unrelated to this gate; avoid hashing hundreds
    # of megabytes of local gameplay when exercising the rejection path.
    monkeypatch.setattr(
        pipeline,
        "generation_recipe",
        lambda **_: {
            "claude": "test-model",
            "background_mode": "concept_only",
            "prompts": {
                "visual_explainer/reference-prompt.txt": "test-prompt",
                "dialogue_gameplay/reference-prompt.txt": "test-prompt",
            },
            "system_prompt": "test-system",
            "engagement_policy": "test-policy",
        },
    )
    return claude, eleven, tts, renderer


def assert_no_generation(guarded_generation):
    claude, eleven, tts, renderer = guarded_generation
    claude.storyboard.assert_not_called()
    claude.review_render.assert_not_called()
    eleven.synthesize.assert_not_called()
    tts.assert_not_called()
    renderer.assert_not_called()


@pytest.mark.parametrize("where", ["segment", "shot"])
def test_authored_unknown_fact_rejected_before_review_speech_or_render(
    guarded_generation, tmp_path, where
):
    brief = Brief.model_validate(fixture_json("new-installments-brief.json"))
    authored = fixture_json("new-installments-animation.json")
    if where == "segment":
        authored["segments"][0]["fact_ids"] = ["invented-fact"]
    else:
        authored["shots"][0]["fact_ids"] = ["invented-fact"]
    with pytest.raises(ValueError, match="invented fact|unapproved fact"):
        pipeline.generate(brief, tmp_path, storyboard_override=authored)
    guarded_generation[0].review.assert_not_called()
    assert_no_generation(guarded_generation)
    assert not (tmp_path / "storyboard.json").exists()


@pytest.mark.parametrize("passed", [False, True])
def test_authored_board_cannot_reach_speech_when_live_content_review_has_issues(
    guarded_generation, tmp_path, passed
):
    brief = Brief.model_validate(fixture_json("new-installments-brief.json"))
    authored = fixture_json("new-installments-animation.json")
    original = Storyboard.model_validate(authored).validate_for(brief, require_engagement=True)
    # The fact ID remains real, but it cannot authorize an invented assertion.
    authored["segments"][0]["spoken_text"] = "These headphones are guaranteed to make you rich."
    edited = Storyboard.model_validate(authored).validate_for(brief, require_engagement=True)
    (tmp_path / "content-review.json").write_text(
        json.dumps(
            {"passed": True, "issues": [], "storyboard_digest": digest(original.model_dump())}
        )
    )
    claude = guarded_generation[0]
    claude.review.return_value = ContentReview(
        passed=passed, issues=["Guaranteed wealth is not an approved fact"]
    )
    stages = []
    with pytest.raises(ProviderError, match="CONTENT_REVIEW_REQUIRED"):
        pipeline.generate(brief, tmp_path, storyboard_override=authored, stage=stages.append)
    claude.review.assert_called_once()
    assert claude.review.call_args.args[1].model_dump() == edited.model_dump()
    assert_no_generation(guarded_generation)
    assert "voicing" not in stages and "rendering" not in stages
    saved = json.loads((tmp_path / "content-review.json").read_text())
    assert saved["storyboard_digest"] == digest(edited.model_dump())
    assert saved["issues"] == ["Guaranteed wealth is not an approved fact"]
    assert not (tmp_path / "pack").exists()


@pytest.mark.parametrize(
    "field,value", [("headline", "Always leave"), ("labels", ["Always leave"])]
)
def test_authored_decision_motion_cannot_hide_extra_text_from_the_renderer(
    guarded_generation, tmp_path, field, value
):
    brief = Brief.model_validate(fixture_json("new-sunk-cost-brief.json"))
    authored = fixture_json("new-sunk-cost-dialogue.json")
    Storyboard.model_validate(authored).validate_for(brief, require_engagement=True)
    authored["shots"][0][field] = value
    with pytest.raises(ValueError, match="Authored motion scenes"):
        pipeline.generate(brief, tmp_path, storyboard_override=authored)
    guarded_generation[0].review.assert_not_called()
    assert_no_generation(guarded_generation)


def test_unchanged_authored_script_needs_review_when_approved_fact_statements_change(
    guarded_generation, tmp_path
):
    raw_brief = fixture_json("new-installments-brief.json")
    authored = fixture_json("new-installments-animation.json")
    board = Storyboard.model_validate(authored)
    # The IDs still match, but the evidence those IDs refer to has changed.
    raw_brief["approved_facts"][0]["statement"] = (
        "This example now uses two equal $50 installments for a $100 purchase."
    )
    brief = Brief.model_validate(raw_brief)
    board.validate_for(brief, require_engagement=True)
    (tmp_path / "content-review.json").write_text(
        json.dumps({"passed": True, "issues": [], "storyboard_digest": digest(board.model_dump())})
    )
    claude = guarded_generation[0]
    claude.review.return_value = ContentReview(
        passed=False, issues=["Narration contradicts the revised approved fact"]
    )
    with pytest.raises(ProviderError, match="CONTENT_REVIEW_REQUIRED"):
        pipeline.generate(brief, tmp_path, storyboard_override=authored)
    claude.review.assert_called_once()
    assert claude.review.call_args.args[0].approved_facts[0].statement.endswith("$100 purchase.")
    assert_no_generation(guarded_generation)
