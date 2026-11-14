import json

import pytest

from app.modules.videos.models import Brief, Storyboard
from app.modules.videos.pipeline import ROOT

BRIEFS = {
    "dialogue_gameplay": "reference-linked-list",
    "visual_explainer": "reference-leatherback",
    "space_explainer": "reference-cosmic-web",
}


def load(fmt):
    root = ROOT / "fixtures/learning"
    brief = Brief.model_validate_json((root / f"{BRIEFS[fmt]}-brief.json").read_text())
    brief = brief.model_copy(update={"format_id": fmt})
    board = Storyboard.model_validate_json((root / f"reference-{fmt}.json").read_text())
    return brief, board


@pytest.mark.parametrize("fmt", BRIEFS)
def test_reference_boards_preserve_source_coverage_and_scene_contract(fmt):
    brief, board = load(fmt)
    board.validate_for(brief, require_engagement=True)
    assert not board.teaching_beats
    assert [s.segment_id for s in board.shots] == [s.segment_id for s in board.segments]
    if fmt != "dialogue_gameplay":
        assert brief.trace_kind == "none" and board.events == []


def test_trace_cannot_reuse_or_reorder_spoken_cues():
    brief, board = load("dialogue_gameplay")
    board.events[2].cue = board.events[1].cue.model_copy()
    with pytest.raises(ValueError, match="strictly later"):
        board.validate_for(brief)


def test_reference_shots_reject_unresolved_image_and_hidden_trace():
    brief, board = load("dialogue_gameplay")
    board.shots[0].asset_ids = ["unknown"]
    with pytest.raises(ValueError, match="unknown image"):
        board.validate_for(brief)
    board.shots[0].asset_ids = []
    event_segment = board.events[1].cue.segment_id
    shot = next(s for s in board.shots if s.segment_id == event_segment)
    shot.kind = "kinetic"
    with pytest.raises(ValueError, match="trusted diagram"):
        board.validate_for(brief)


def test_space_requires_spatial_progression_not_star_wallpaper():
    brief, board = load("space_explainer")
    for shot in board.shots:
        shot.space_mode = "starfield"
    with pytest.raises(ValueError, match="two space modes"):
        board.validate_for(brief)


def test_presentation_and_subject_trace_change_generation_identity():
    brief, _ = load("dialogue_gameplay")
    assert brief.generation_key({}) != brief.model_copy(
        update={"presentation": "guided_v1"}
    ).generation_key({})
    assert brief.generation_key({}) != brief.model_copy(
        update={"trace_kind": "none"}
    ).generation_key({})


def test_runtime_learning_schemas_are_current():
    for model in (Brief, Storyboard):
        exported = ROOT / f"contracts/schemas/learning/{model.__name__}.schema.json"
        assert json.loads(exported.read_text()) == model.model_json_schema()


def test_default_reference_linked_list_has_a_narrator_fixture():
    root = ROOT / "fixtures/learning"
    brief = Brief.model_validate_json((root / "reference-linked-list-brief.json").read_text())
    board = Storyboard.model_validate_json(
        (root / "reference-linked-list-visual_explainer.json").read_text()
    )
    board.validate_for(brief, require_engagement=True)
    assert {s.speaker_role for s in board.segments} == {"narrator"}


def test_reject_immediately_repeated_closing_sentence():
    brief, board = load("space_explainer")
    board.segments[
        -1
    ].spoken_text = (
        "The animation is illustrative, not to scale. A vast pattern, shaped by gravity."
    )
    with pytest.raises(ValueError, match="repeated narration"):
        board.validate_for(brief)


def test_v3_rejects_photo_recycling_even_with_varied_cameras():
    brief, board = load("visual_explainer")
    brief = brief.model_copy(update={"presentation": "reference_v3"})
    with pytest.raises(ValueError, match="four distinct"):
        board.validate_for(brief)


def test_v3_rejects_space_camera_only_variety():
    brief, board = load("space_explainer")
    brief = brief.model_copy(update={"presentation": "reference_v3"})
    modes = ["galaxy", "cosmic_web"]
    for i, shot in enumerate(board.shots):
        if shot.kind == "space":
            shot.space_mode = modes[i % 2]
    with pytest.raises(ValueError, match="four genuinely"):
        board.validate_for(brief)
