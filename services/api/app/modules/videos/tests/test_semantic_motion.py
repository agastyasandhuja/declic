import json

import pytest

from app.modules.videos import pipeline
from app.modules.videos.models import Brief, InstallmentExample, Storyboard

FIXTURES = pipeline.ROOT / "fixtures/learning"


def raw(name):
    return json.loads((FIXTURES / name).read_text())


def biology():
    return (
        Brief.model_validate(raw("revised-enzyme-brief.json")),
        Storyboard.model_validate(raw("revised-enzyme-animation.json")),
    )


def payments():
    return (
        Brief.model_validate(raw("new-installments-brief.json")),
        Storyboard.model_validate(raw("new-installments-animation.json")),
    )


def test_biology_authored_mechanisms_do_not_require_unrelated_nasa_images():
    brief, board = biology()
    board.validate_for(brief, require_engagement=True)
    assert not board.image_requests
    assert len({s.space_mode for s in board.shots}) == 7


def test_astronomy_still_requires_image_evidence():
    brief = Brief.model_validate(raw("revised-cosmic-web-brief.json"))
    board = Storyboard.model_validate(raw("revised-space_explainer.json"))
    board.image_requests = []
    for shot in board.shots:
        shot.asset_ids = []
        if shot.kind == "image":
            shot.kind = "kinetic"
    with pytest.raises(ValueError, match="NASA"):
        board.validate_for(brief)


def test_one_astronomy_scene_does_not_inherit_biology_image_exemption():
    brief, board = biology()
    board.shots[-1].space_mode = "galaxy"
    with pytest.raises(ValueError, match="NASA"):
        board.validate_for(brief)


def test_payment_motion_uses_the_validated_numeric_example_without_stock_images():
    brief, board = payments()
    board.validate_for(brief, require_engagement=True)
    example = brief.installment_example
    assert example.unit_price * example.purchases == 300
    assert example.unit_price * example.purchases / example.installments == 75


def test_payment_story_cannot_repeat_a_scene_with_only_camera_variation():
    brief, board = payments()
    for i, shot in enumerate(board.shots):
        shot.motion_scene = ["price_tag", "split_payment", "receipt"][i % 3]
    with pytest.raises(ValueError, match="four distinct"):
        board.validate_for(brief)


def test_adjacent_payment_repetition_is_rejected_even_with_many_other_scenes():
    brief, board = payments()
    board.shots[1].motion_scene = board.shots[0].motion_scene
    with pytest.raises(ValueError, match="Adjacent|adjacent"):
        board.validate_for(brief)


@pytest.mark.parametrize("field,value", [("motion_scene", "ticket_purchase"), ("kind", "kinetic")])
def test_payment_story_rejects_an_unrelated_or_invisible_scene(field, value):
    brief, board = payments()
    setattr(board.shots[0], field, value)
    with pytest.raises(ValueError, match="supported motion scenes"):
        board.validate_for(brief)


def test_payment_scenes_cannot_invent_a_numeric_example():
    brief, board = payments()
    brief.installment_example = None
    with pytest.raises(ValueError, match="validated installment example"):
        board.validate_for(brief)


@pytest.mark.parametrize("field,value", [("headline", "$1 total"), ("labels", ["$1 total"])])
def test_payment_numbers_cannot_be_overridden_with_model_text(field, value):
    brief, board = payments()
    setattr(board.shots[0], field, value)
    with pytest.raises(ValueError, match="trusted numbers"):
        board.validate_for(brief)


def test_supported_spatial_scene_cannot_be_silently_used_in_photo_format():
    brief, board = biology()
    brief.format_id = "visual_explainer"
    with pytest.raises(ValueError, match="Space scenes require"):
        board.validate_for(brief)


@pytest.mark.parametrize(
    "field,value",
    [
        ("unit_price", True),
        ("unit_price", "100"),
        ("unit_price", 100.0),
        ("unit_price", 3),
        ("unit_price", 10004),
        ("unit_price", 101),
        ("installments", 1),
        ("installments", 5),
        ("installments", 13),
        ("installments", False),
        ("purchases", 0),
        ("purchases", 4),
        ("purchases", 6),
        ("purchases", 2.5),
    ],
)
def test_payment_example_rejects_unrenderable_or_coerced_values(field, value):
    example = {"unit_price": 100, "installments": 4, "purchases": 3}
    example[field] = value
    with pytest.raises(ValueError):
        InstallmentExample.model_validate(example)


@pytest.mark.parametrize("installments,purchases", [(2, 1), (4, 3)])
def test_payment_example_accepts_supported_layout_boundaries(installments, purchases):
    example = InstallmentExample(
        unit_price=100, installments=installments, purchases=purchases
    )
    assert example.unit_price % example.installments == 0


@pytest.mark.parametrize("sides", [[True, 4], ["3", 4], [3.0, 4], [0, 4], [10, 4], [3], [3, 4, 5]])
def test_geometry_brief_checks_strict_bounds_before_generation(sides):
    brief = raw("pythagorean-math-brief.json")
    brief["pythagorean_sides"] = sides
    with pytest.raises(ValueError):
        Brief.model_validate(brief)


@pytest.mark.parametrize(
    "brief_name,board_name",
    [
        ("revised-enzyme-brief.json", "revised-enzyme-animation.json"),
        ("new-installments-brief.json", "new-installments-animation.json"),
    ],
)
def test_fixture_pipeline_selects_semantically_matching_storyboard(
    monkeypatch, tmp_path, brief_name, board_name
):
    brief = Brief.model_validate(raw(brief_name))
    expected = raw(board_name)["segments"][0]["spoken_text"]

    class ReachedNarration(Exception):
        pass

    def inspect_segment(segment, *args, **kwargs):
        assert segment.spoken_text == expected
        raise ReachedNarration

    monkeypatch.setattr(pipeline, "synthesize", inspect_segment)
    monkeypatch.setattr(
        pipeline,
        "generation_recipe",
        lambda **kwargs: {
            "background_mode": "auto",
            "claude": "fixture",
            "system_prompt": "fixture",
            "engagement_policy": "fixture",
            "prompts": {f"{brief.format_id}/reference-prompt.txt": "fixture"},
        },
    )
    with pytest.raises(ReachedNarration):
        pipeline.generate(brief, tmp_path, fixture=True, render_video=False)
