from collections import Counter
from datetime import timedelta

from app.modules.recommendations.engine import exam_urgency, select_study, slot


def test_progressive_density_and_bounded_inventory_debt():
    counts = []
    for active_seconds in [0, 180, 360, 700]:
        debt, count = 0, 0
        for _ in range(100):
            study, debt = slot(debt, active_seconds, True)
            count += study
        counts.append(count)
    assert counts == [10, 20, 35, 50]
    debt = 0
    for _ in range(10000):
        _, debt = slot(debt, 700, False)
    assert debt <= 1
    study, debt = slot(debt, 700, True)
    assert study
    assert not slot(debt, 700, True)[0]


def test_three_course_fairness_with_20_4_2_variants(catalog, clock):
    history = []
    chosen = []
    for _ in range(60):
        selection = select_study(
            user_id="user_demo_01",
            objectives=catalog.objectives,
            variants=catalog.variants,
            learning={},
            history=history,
            now=clock(),
        )
        assert selection is not None
        record = {
            "course_id": selection.objective.course_id,
            "objective_id": selection.objective.objective_id,
            "video_id": selection.variant.video_id,
            "format_id": selection.variant.format_id,
            "teaching_approach": selection.variant.teaching_approach,
        }
        history.append(record)
        chosen.append(record)
    counts = Counter(r["course_id"] for r in chosen)
    assert max(counts.values()) - min(counts.values()) <= 2
    for start in range(len(chosen) - 9):
        assert max(Counter(r["course_id"] for r in chosen[start : start + 10]).values()) <= 4
    assert all(a["video_id"] != b["video_id"] for a, b in zip(chosen, chosen[1:], strict=False))


def test_exam_urgency_requires_scope_and_date_evidence(catalog, clock):
    objective = catalog.objectives[0]
    assert exam_urgency(objective, clock()) > 0
    for changes in [
        dict(assessment_scope_status="unknown"),
        dict(assessment_evidence_status="inferred"),
        dict(assessment_timestamp=None, assessment_date=None),
        dict(assessment_timestamp=clock() - timedelta(days=1)),
    ]:
        assert exam_urgency(objective.model_copy(update=changes), clock()) == 0
    date_only = catalog.objectives[1].model_copy(update={"assessment_date": clock().date()})
    assert exam_urgency(date_only, clock()) == 1


def test_private_unready_expired_and_incompatible_assets_are_excluded(catalog, clock):
    objective = catalog.objectives[0]
    base = catalog.variants[0]
    for changes in [
        dict(status="rendering"),
        dict(scope="private", owner_user_id="another-user"),
        dict(language="fr"),
        dict(duration_seconds=90),
        dict(playback=base.playback.model_copy(update={"expires_at": clock()})),
    ]:
        result = select_study(
            user_id="user_demo_01",
            objectives=[objective],
            variants=[base.model_copy(update=changes)],
            learning={},
            history=[],
            now=clock(),
        )
        assert result is None


def test_wrong_answer_prefers_new_approach_and_known_weak_prerequisite_defers(catalog, clock):
    objective = catalog.objectives[0]
    first = catalog.variants[0]
    history = [
        dict(
            course_id=objective.course_id,
            objective_id=objective.objective_id,
            video_id=first.video_id,
            teaching_approach=first.teaching_approach,
            format_id=first.format_id,
        ),
        dict(video_id="intervening-entertainment"),
    ]
    state = {"mastery_estimate": 0.325, "incorrect_count": 1, "next_review_at": clock().isoformat()}
    selected = select_study(
        user_id="user_demo_01",
        objectives=[objective],
        variants=catalog.variants,
        learning={objective.objective_id: state},
        history=history,
        now=clock(),
    )
    assert selected.variant.teaching_approach != first.teaching_approach
    assert "quiz_weakness" in selected.reasons
    assert (
        select_study(
            user_id="user_demo_01",
            objectives=[
                objective.model_copy(
                    update={
                        "prerequisite_objective_ids": ["prereq"],
                    }
                )
            ],
            variants=catalog.variants,
            learning={"prereq": {"mastery_estimate": 0.2}},
            history=[],
            now=clock(),
        )
        is None
    )
