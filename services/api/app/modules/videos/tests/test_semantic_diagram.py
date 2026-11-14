"""Explicit arbitrary-topic diagrams preserve existing photo/trace safeguards."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.modules.videos.models import Brief, SemanticDiagramPlan, Storyboard
from app.modules.videos.pipeline import ROOT


def generic_visual():
    brief = Brief(
        brief_id="semantic",
        lesson_request_id="request",
        objective_id="objective",
        title="Opportunity cost",
        learning_goal="Compare forgone alternatives",
        subject="Economics",
        level="intro",
        notation="general",
        assumed_knowledge=[],
        must_cover=["fact"],
        must_not_claim=[],
        approved_facts=[
            {"fact_id": "fact", "statement": "Time spent on one option cannot be spent on another."}
        ],
        trace_kind="none",
        format_id="visual_explainer",
        teaching_approach="comparison",
        owner_user_id="alice",
        visual_strategy="semantic_diagram",
    )
    board = json.loads((ROOT / "fixtures/learning/reference-visual_explainer.json").read_text())
    board["image_requests"] = []
    for i, segment in enumerate(board["segments"]):
        segment["fact_ids"] = ["fact"]
        shot = board["shots"][i]
        shot.update(
            kind="diagram",
            headline="",
            labels=[],
            asset_ids=[],
            fact_ids=["fact"],
            motion_scene="none",
            diagram_demo="trace",
            semantic_diagram={
                "mode": "comparison" if i % 2 else "sequence",
                "nodes": [{"label": "Choose one option"}, {"label": "Forgone alternative"}],
                "edges": [] if i % 2 else [{"source": 0, "target": 1}],
            },
        )
    return brief, board


def test_abstract_topics_have_an_explicit_bounded_diagram_path_without_photo_search():
    brief, raw = generic_visual()
    board = Storyboard.model_validate(raw).validate_for(brief)
    assert len(board.shots) >= 6 and board.image_requests == []
    with pytest.raises(ValueError, match="explicit visual strategy"):
        board.validate_for(brief.model_copy(update={"visual_strategy": "existing"}))
    # Removing semantic payload does not silently weaken the older photo policy.
    for shot in raw["shots"]:
        shot.pop("semantic_diagram")
    with pytest.raises(ValueError, match="Photo explainer"):
        Storyboard.model_validate(raw).validate_for(
            brief.model_copy(update={"visual_strategy": "existing"})
        )


@pytest.mark.parametrize(
    "mode,edges",
    [
        ("comparison", [{"source": 0, "target": 1}]),
        ("sequence", [{"source": 1, "target": 0}]),
        ("sequence", [{"source": 0, "target": 3}]),
        ("cause_effect", [{"source": 0, "target": 0}]),
        ("cause_effect", [{"source": True, "target": 1}]),
    ],
)
def test_invented_or_unbounded_relationships_are_rejected(mode, edges):
    with pytest.raises(ValidationError):
        SemanticDiagramPlan.model_validate(
            {"mode": mode, "nodes": [{"label": "Cause"}, {"label": "Effect"}], "edges": edges}
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda raw: raw["shots"][0].update(asset_ids=["remote"]),
        lambda raw: raw["shots"][0].update(motion_scene="ticket_loss"),
        lambda raw: raw["shots"][0].update(labels=["Extra unsupported text"]),
        lambda raw: raw["shots"][0]["semantic_diagram"]["nodes"][0].update(label="x" * 25),
        lambda raw: raw["shots"][0]["semantic_diagram"]["nodes"][0].update(
            url="https://example.test/image"
        ),
    ],
)
def test_semantic_strategy_cannot_smuggle_other_scene_capabilities(change):
    brief, raw = generic_visual()
    raw = deepcopy(raw)
    change(raw)
    with pytest.raises(ValueError):
        Storyboard.model_validate(raw).validate_for(brief)


def test_semantic_strategy_cannot_override_specialized_format_or_repeat_one_slide():
    brief, raw = generic_visual()
    with pytest.raises(ValidationError, match="Semantic diagrams require"):
        Brief.model_validate({**brief.model_dump(), "format_id": "dialogue_gameplay"})
    for shot in raw["shots"]:
        shot["semantic_diagram"] = raw["shots"][0]["semantic_diagram"]
    with pytest.raises(ValueError, match="at least two different"):
        Storyboard.model_validate(raw).validate_for(brief)
