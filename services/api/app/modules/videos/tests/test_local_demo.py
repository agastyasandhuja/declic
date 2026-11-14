import copy

import pytest
from pydantic import ValidationError

from app.modules.videos.local_demo import Batch, Lesson, Scene


def sample():
    return {
        "lesson_id": "demo_test",
        "course_id": "demo_cs210",
        "objective_id": "demo_heap",
        "title": "A min heap",
        "learning_goal": "Explain heap order",
        "format_style": "graphic",
        "approved_facts": [
            {"fact_id": "f1", "statement": "Parents are at most their children."},
            {"fact_id": "f2", "statement": "A heap is a complete binary tree."},
        ],
        "segments": [
            {
                "speaker_role": "narrator",
                "spoken_text": "Watch the smaller value move.",
                "fact_ids": ["f1"],
            }
            for _ in range(6)
        ],
        "quizzes": [
            {
                "prompt": "Which relation holds?",
                "options": ["a", "b", "c", "d"],
                "correct_index": 0,
                "explanation": "The parent does not exceed a child.",
            }
        ],
        "visual_plan": [
            {
                "kind": "tree",
                "nodes": [
                    {"id": "a", "label": "", "value": "2", "x": 0.5, "y": 0.2},
                    {
                        "id": "b",
                        "label": "",
                        "value": "5",
                        "x": 0.3,
                        "y": 0.6,
                        "to_x": 0.5,
                        "to_y": 0.2,
                    },
                ],
                "edges": [{"source": "a", "target": "b"}],
            }
            for _ in range(6)
        ],
    }


def test_local_generic_lesson_keeps_exact_states_and_quiz():
    lesson = Lesson.model_validate(sample())
    assert lesson.visual_plan[0].nodes[1].to_y == 0.2
    assert lesson.quizzes[0].correct_index == 0
    assert lesson.segments[0].fact_ids == ["f1"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.update(owner_user_id="private-user"),
        lambda s: s["segments"][0].update(fact_ids=["unknown"]),
        lambda s: s["visual_plan"][0]["nodes"][0].update(x=5),
        lambda s: s["visual_plan"][0]["nodes"][0].update(x=float("nan")),
        lambda s: s["visual_plan"][0]["edges"][0].update(target="unknown"),
        lambda s: s["visual_plan"][0]["nodes"][0].update(code="fetch(secret)"),
        lambda s: s["visual_plan"].pop(),
        lambda s: s["quizzes"][0].update(correct_index=4),
        lambda s: s.update(format_style="dialogue"),
    ],
)
def test_local_import_rejects_unsafe_or_ungrounded_spec(mutate):
    data = copy.deepcopy(sample())
    mutate(data)
    with pytest.raises(ValidationError):
        Lesson.model_validate(data)


def test_batch_identity_and_matrix_dimensions():
    with pytest.raises(ValidationError):
        Batch.model_validate({"lessons": [sample(), sample()]})
    scene = Scene(kind="matrix", matrix_a=[[1, 2], [3, 4]], matrix_b=[[2, 0], [1, 2]])
    assert scene.matrix_a[0] == [1, 2]
    with pytest.raises(ValidationError):
        Scene(kind="matrix", matrix_a=[[1, 2]], matrix_b=[[1, 2], [3, 4]])


def test_committed_demo_has_six_lessons_per_course_and_48_questions():
    from collections import Counter
    from pathlib import Path

    path = Path(__file__).resolve().parents[6] / "fixtures/learning/demo-library/lessons.json"
    batch = Batch.model_validate_json(path.read_text())
    assert len(batch.lessons) == 24
    assert Counter(lesson.course_id for lesson in batch.lessons) == {
        "demo_cs210": 6,
        "demo_acc233": 6,
        "demo_his110": 6,
        "demo_math235": 6,
    }
    assert sum(len(lesson.quizzes) for lesson in batch.lessons) == 48


def test_demo_eigenvector_motion_preserves_exact_axis_scale():
    from pathlib import Path

    path = Path(__file__).resolve().parents[6] / "fixtures/learning/demo-library/lessons.json"
    batch = Batch.model_validate_json(path.read_text())
    lesson = next(item for item in batch.lessons if item.lesson_id == "demo_math235_eigenvectors")
    for scene in lesson.visual_plan:
        nodes = {node.id: node for node in scene.nodes}
        origin, first, second = nodes["origin"], nodes["e1"], nodes["e2"]
        assert (first.to_x - origin.x) / (first.x - origin.x) == pytest.approx(2)
        assert (second.to_y - origin.y) / (second.y - origin.y) == pytest.approx(3)


def test_demo_determinant_geometry_has_sixfold_area_and_zero_collapse():
    from pathlib import Path

    path = Path(__file__).resolve().parents[6] / "fixtures/learning/demo-library/lessons.json"
    batch = Batch.model_validate_json(path.read_text())
    lesson = next(item for item in batch.lessons if item.lesson_id == "demo_math235_determinant")

    def area(nodes, final=False):
        points = [
            (
                n.to_x if final and n.to_x is not None else n.x,
                n.to_y if final and n.to_y is not None else n.y,
            )
            for n in nodes
        ]
        return (
            abs(
                sum(
                    a[0] * b[1] - b[0] * a[1]
                    for a, b in zip(points, points[1:] + points[:1], strict=True)
                )
            )
            / 2
        )

    for index, scene in enumerate(lesson.visual_plan):
        expected = 0 if index == 6 else 6
        assert area(scene.nodes, True) / area(scene.nodes) == pytest.approx(expected)
